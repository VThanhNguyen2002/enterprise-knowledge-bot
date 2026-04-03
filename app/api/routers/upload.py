import os
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from app.core.limiter import limiter

router = APIRouter()

# Temporary staging area: files land here and the Celery worker cleans up after ingestion
TEMP_UPLOAD_DIR = os.getenv("TEMP_UPLOAD_DIR", "./temp_uploads")


@router.post("/upload/", status_code=202)
@limiter.limit("2/minute")
async def upload_document(request: Request, file: UploadFile = File(...)):
    """
    POST /upload/ — Async document ingestion (202 Accepted)

    Flow:
        1. Validate file type + size synchronously (instant feedback on bad input).
        2. Sanitise filename and save to TEMP_UPLOAD_DIR.
        3. Dispatch Celery task async_ingest_document — returns task_id immediately.
        4. Worker owns the file lifecycle: cleans up after ingestion success OR failure.

    Returns 202 Accepted with task_id for optional status polling.
    """
    # ── 1. Validate ───────────────────────────────────────────────────────────
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ upload file .txt")

    MAX_SIZE = 5 * 1024 * 1024  # 5 MB
    file_content = b""
    while chunk := await file.read(1024 * 1024):
        file_content += chunk
        if len(file_content) > MAX_SIZE:
            raise HTTPException(status_code=400, detail="Dung lượng file vượt quá 5MB.")

    if not file_content.strip():
        raise HTTPException(status_code=400, detail="File không có nội dung. Vui lòng kiểm tra lại.")

    # ── 2. Save to temp staging area ──────────────────────────────────────────
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in " ._-")
    temp_path = os.path.abspath(os.path.join(TEMP_UPLOAD_DIR, safe_filename))

    with open(temp_path, "wb") as f:
        f.write(file_content)

    # ── 3. Dispatch Celery background task ────────────────────────────────────
    try:
        from app.worker import async_ingest_document
        task = async_ingest_document.delay(temp_path)
    except Exception as e:
        # If Celery/Redis is unavailable, clean up and fail fast
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(
            status_code=503,
            detail=f"Task queue unavailable — file not queued: {e}",
        )

    # ── 4. Return 202 immediately ─────────────────────────────────────────────
    return JSONResponse(
        status_code=202,
        content={
            "status": "processing",
            "task_id": task.id,
            "filename": safe_filename,
            "message": f"File '{safe_filename}' submitted for background processing.",
        },
    )


# ── Task status polling endpoint ──────────────────────────────────────────────
@router.get("/upload/status/{task_id}")
async def get_upload_status(task_id: str):
    """
    GET /upload/status/{task_id}
    Poll the result of an async ingestion task.
    Returns: {"state": "PENDING"|"SUCCESS"|"FAILURE", "result": ...}
    """
    try:
        from app.worker import celery_app
        task = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "state": task.state,
            "result": task.result if task.state == "SUCCESS" else None,
            "error": str(task.result) if task.state == "FAILURE" else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))