from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Enterprise Knowledge Bot API v2.0 (Clean Architecture)"}

@router.get("/health")
async def health_check():
    return {"status": "healthy"}