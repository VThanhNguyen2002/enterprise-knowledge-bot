"""
app/worker.py — Celery Async Task Worker
=========================================
Architecture Layer : Infrastructure / Background Processing
Pattern            : Task Queue (Phase 1 of scalability-roadmap.md)

Purpose
-------
Offloads CPU/memory-heavy document ingestion from the FastAPI request cycle.
When a user uploads a file, the API returns immediately with a task_id,
and this worker processes the actual chunking + embedding + ChromaDB write
in the background.

Broker   : Redis (redis://redis:6379/0)
Backend  : Redis (result storage — same instance, DB 1)
Queue    : "ingest" (dedicated — isolated from future high-priority queues)

Running locally (dev)
---------------------
  # Start Redis first:
  docker run -d -p 6379:6379 redis:7-alpine

  # Start worker:
  PYTHONPATH=. celery -A app.worker.celery_app worker --loglevel=info -Q ingest

Running in Docker Compose
--------------------------
  docker compose up celery-worker   # Defined in docker-compose.yml

Scaling
-------
  # Scale to 4 concurrent worker processes:
  docker compose up --scale celery-worker=4 celery-worker
"""

import os
import logging
from celery import Celery
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# ── Celery Application Factory ─────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_RESULT_BACKEND = os.getenv("REDIS_RESULT_BACKEND", REDIS_URL.replace("/0", "/1"))

celery_app = Celery(
    "ekb_worker",
    broker=REDIS_URL,
    backend=REDIS_RESULT_BACKEND,
)

celery_app.conf.update(
    # Routing — all ingestion tasks go to the dedicated "ingest" queue
    task_routes={"app.worker.async_ingest_document": {"queue": "ingest"}},
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,             # Results kept for 1 hour
    worker_prefetch_multiplier=1,    # One task at a time per worker (memory safety)
    task_acks_late=True,             # Acknowledge AFTER success (prevents data loss on crash)
    timezone="Asia/Ho_Chi_Minh",
)


# ── Tasks ─────────────────────────────────────────────────────────────────────
@celery_app.task(
    bind=True,
    name="app.worker.async_ingest_document",
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
    queue="ingest",
)
def async_ingest_document(self, file_path: str) -> dict:
    """
    Async background task: ingest a document into ChromaDB.

    Guarantees:
        - temp file is ALWAYS deleted via try/finally (no disk leaks).
        - On retry: file is preserved until the final attempt.
        - On permanent failure: file is deleted on the last retry's finally block.

    Args:
        file_path: Absolute path to the temp file (saved by the upload router).

    Returns:
        dict with keys: status, filename, message.
    """
    filename = os.path.basename(file_path)
    logger.info(f"[async_ingest_document] START — {filename} (attempt {self.request.retries + 1})")

    is_final_attempt = self.request.retries >= self.max_retries
    cleanup_now = True   # default: clean up in finally

    try:
        # ── Lazy import: RAGService initialises HuggingFace model on first load ──
        from app.services.rag_service import rag_service

        result_message = rag_service.ingest_document(file_path)

        logger.info(f"[async_ingest_document] SUCCESS — {result_message}")
        return {
            "status": "success",
            "filename": filename,
            "message": result_message,
        }

    except ValueError as ve:
        # Non-retryable: poisoned content, empty file, validation error
        logger.warning(f"[async_ingest_document] REJECTED (non-retryable): {ve}")
        # cleanup_now=True → finally block deletes the file
        raise self.reject(requeue=False)

    except FileNotFoundError as fnf:
        # Non-retryable: temp file disappeared before task ran
        logger.error(f"[async_ingest_document] FILE NOT FOUND: {fnf}")
        cleanup_now = False   # Nothing to delete
        raise self.reject(requeue=False)

    except Exception as exc:
        # Retryable: transient ChromaDB lock, memory pressure, network hiccup
        if is_final_attempt:
            logger.error(f"[async_ingest_document] EXHAUSTED retries for {filename}: {exc}")
            # cleanup_now=True → finally block cleans up on last attempt
        else:
            logger.warning(
                f"[async_ingest_document] RETRY {self.request.retries + 1}"
                f"/{self.max_retries} in {10 * (2 ** self.request.retries)}s — {exc}"
            )
            cleanup_now = False  # Preserve file for next retry attempt
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))

    finally:
        # ── Guaranteed disk cleanup ────────────────────────────────────────────
        if cleanup_now and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"[async_ingest_document] Cleaned up temp file: {filename}")
            except OSError as rm_err:
                logger.warning(f"[async_ingest_document] Failed to delete temp file {filename}: {rm_err}")


# ── TODO (Phase 1 → Phase 2): Semantic cache invalidation ─────────────────────
# @celery_app.task(name="app.worker.invalidate_semantic_cache")
# def invalidate_semantic_cache(filename: str):
#     """Flush cached LLM responses for a document after re-ingestion."""
#     pass

