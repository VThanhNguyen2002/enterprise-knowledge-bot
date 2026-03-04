from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.services.rag_service import rag_service

app = FastAPI(
    title="Enterprise Knowledge Bot API",
    description="RAG-based knowledge management system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Enterprise Knowledge Bot API v1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/upload-test/")
async def upload_test_document():
    file_path = "data/sample.txt"
    try:
        result = rag_service.ingest_document(file_path)
        return {"status": "success", "message": result}
    except Exception as e:
        # Bắt lỗi và trả về HTTP 400 chuẩn API
        raise HTTPException(status_code=400, detail=str(e))

class QuestionRequest(BaseModel):
    question: str

@app.post("/chat/")
async def chat_endpoint(request: QuestionRequest):
    try:
        answer = rag_service.chat(request.question)
        return {"status": "success", "question": request.question, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi khi truy vấn Bot.")