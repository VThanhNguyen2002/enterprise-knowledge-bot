import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.limiter import limiter
from app.api.routers import health, upload, chat

logger = logging.getLogger(__name__)


# ── Security Headers Middleware ──────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects hardened HTTP security headers on every response."""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
        return response


# ── App Factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Enterprise Knowledge Bot API",
    description="RAG-based knowledge management system (Clean Architecture)",
    version="2.0.0"
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers (add before CORS so headers are always injected)
app.add_middleware(SecurityHeadersMiddleware)

# CORS — read allowed origins from env; default to localhost Streamlit only
_allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:8501"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Routers
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(chat.router)


# ── Startup: Pre-warm embeddings ──────────────────────────────────────────────
@app.on_event("startup")
async def pre_warm_embeddings():
    """
    Force HuggingFace model load before the first request arrives.
    Eliminates the cold-start latency spike on the initial upload.
    """
    from app.services.rag_service import rag_service
    _ = rag_service.embeddings
    logger.info("✅ Embeddings model pre-warmed and ready.")