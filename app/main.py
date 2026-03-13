import os
import re
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.services.rag_service import rag_service

# Khởi tạo bộ giới hạn (Rate Limiter) dựa trên IP
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Enterprise Knowledge Bot API",
    description="RAG-based knowledge management system (Secured)",
    version="1.2.0"
)

# Đăng ký Limiter vào FastAPI
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === BẢO MẬT: Validation chống Prompt Injection ===
class QuestionRequest(BaseModel):
    question: str

    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        if len(v) > 2000:
            raise ValueError("Câu hỏi quá dài (tối đa 2000 ký tự).")
        
        # Danh sách đen các mẫu tấn công thao túng LLM
        dangerous_patterns = [
            r'(?i)ignore.*instructions?',
            r'(?i)system\s*prompt',
            r'(?i)bỏ\s*qua.*hướng\s*dẫn',
            r'(?i)quên.*đi',
            r'(?i)execute|system\(',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v):
                raise ValueError("Phát hiện nội dung không an toàn. Yêu cầu bị từ chối.")
        return v.strip()

@app.get("/")
async def root():
    return {"message": "Enterprise Knowledge Bot API v1.2.0 (Secured)"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# === BẢO MẬT: API Upload file thực tế có kiểm soát ===
@app.post("/upload/")
@limiter.limit("2/minute")
async def upload_document(request: Request, file: UploadFile = File(...)):
    # 1. Chặn file sai định dạng (Path Traversal defense)
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ upload file .txt")
    
    # 2. Đọc chunking để chặn file quá lớn gây sập RAM (OOM defense)
    MAX_SIZE = 5 * 1024 * 1024 # Giới hạn 5MB
    file_content = b""
    while chunk := await file.read(1024 * 1024):
        file_content += chunk
        if len(file_content) > MAX_SIZE:
            raise HTTPException(status_code=400, detail="Dung lượng file vượt quá 5MB.")

    # 3. Lưu file an toàn vào thư mục data
    os.makedirs("data", exist_ok=True)
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in " ._-")
    file_path = os.path.join("data", safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(file_content)

    # 4. Đưa vào RAG Service xử lý
    try:
        result = rag_service.ingest_document(file_path)
        return {"status": "success", "filename": safe_filename, "message": result}
    except Exception as e:
        # Xóa file lỗi để tránh rác hệ thống
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))

# === BẢO MẬT: Giới hạn 5 câu hỏi / phút / IP ===
@app.post("/chat/")
@limiter.limit("5/minute")
async def chat_endpoint(request: Request, body: QuestionRequest):
    try:
        answer = rag_service.chat(body.question)
        return {"status": "success", "question": body.question, "answer": answer}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi hệ thống khi xử lý câu hỏi.")