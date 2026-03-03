"""
FastAPI Application Entry Point
Main application setup and startup
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
# from app.api import documents, chat

app = FastAPI(
    title="Enterprise Knowledge Bot API",
    description="RAG-based knowledge management system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
# app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/")
async def root():
    return {"message": "Enterprise Knowledge Bot API v1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
