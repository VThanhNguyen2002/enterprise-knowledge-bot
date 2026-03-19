from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.limiter import limiter
from app.api.routers import health, upload, chat

app = FastAPI(
    title="Enterprise Knowledge Bot API",
    description="RAG-based knowledge management system (Clean Architecture)",
    version="2.0.0"
)

# Setup Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn các Routers vào App chính
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(chat.router)