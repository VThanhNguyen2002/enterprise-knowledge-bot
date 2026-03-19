from fastapi import APIRouter, HTTPException, Request
from app.schemas.request import QuestionRequest
from app.services.rag_service import rag_service
from app.core.limiter import limiter

router = APIRouter()

@router.post("/chat/")
@limiter.limit("5/minute")
async def chat_endpoint(request: Request, body: QuestionRequest):
    try:
        answer = rag_service.chat(body.question)
        return {"status": "success", "question": body.question, "answer": answer}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi hệ thống khi xử lý câu hỏi.")