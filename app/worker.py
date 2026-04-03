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
    default_retry_delay=10,          # Wait 10s before retry
    acks_late=True,
    queue="ingest",
)
def async_ingest_document(self, file_path: str) -> dict:
    """
    Async background task: ingest a document into ChromaDB.

    This task is the async counterpart of `rag_service.ingest_document()`.
    It decouples the upload HTTP response from the heavy embed+store operation.

    Args:
        file_path: Absolute path to the uploaded .txt file (saved to /app/data/).

    Returns:
        dict with keys: status, filename, chunks_stored, message.

    Raises:
        Retries up to 3 times on transient errors (network, ChromaDB lock).
        After max_retries, raises Reject to move task to dead-letter queue.
    """
    logger.info(f"[async_ingest_document] START — file: {file_path}")

    try:
        # ── Lazy import to avoid loading RAG service at worker startup ────────
        from app.services.rag_service import rag_service

        result_message = rag_service.ingest_document(file_path)

        logger.info(f"[async_ingest_document] SUCCESS — {result_message}")
        return {
            "status": "success",
            "filename": os.path.basename(file_path),
            "message": result_message,
        }

    except ValueError as ve:
        # Non-retryable: poisoned content, empty file, validation error
        logger.warning(f"[async_ingest_document] REJECTED (non-retryable): {ve}")
        raise self.reject(requeue=False)

    except FileNotFoundError as fnf:
        # Non-retryable: file was deleted before task ran
        logger.error(f"[async_ingest_document] FILE NOT FOUND: {fnf}")
        raise self.reject(requeue=False)

    except Exception as exc:
        # Retryable: transient DB errors, memory pressure, etc.
        logger.warning(
            f"[async_ingest_document] RETRY {self.request.retries + 1}"
            f"/{self.max_retries} — {exc}"
        )
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))


# ── TODO (Phase 1 → Phase 2): Add semantic cache invalidation task ─────────────
# @celery_app.task(name="app.worker.invalidate_semantic_cache")
# def invalidate_semantic_cache(filename: str):
#     """Flush cached LLM responses related to a specific document after re-ingestion."""
#     pass
