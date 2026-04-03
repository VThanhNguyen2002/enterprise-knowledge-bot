import os
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from app.services.rag_service import rag_service
from app.core.limiter import limiter

router = APIRouter()

@router.post("/upload/")
@limiter.limit("2/minute")
async def upload_document(request: Request, file: UploadFile = File(...)):
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ upload file .txt")
    
    MAX_SIZE = 5 * 1024 * 1024
    file_content = b""
    while chunk := await file.read(1024 * 1024):
        file_content += chunk
        if len(file_content) > MAX_SIZE:
            raise HTTPException(status_code=400, detail="Dung lượng file vượt quá 5MB.")

    os.makedirs("data", exist_ok=True)
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in " ._-")
    file_path = os.path.join("data", safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(file_content)

    try:
        result = rag_service.ingest_document(file_path)
        return {"status": "success", "filename": safe_filename, "message": result}
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))