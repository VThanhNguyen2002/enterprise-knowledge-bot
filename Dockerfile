FROM python:3.11-slim AS builder

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    # Streamlit connects to FastAPI via localhost (same container)
    API_BASE_URL=http://localhost:8000

# System deps: gcc/g++ for ChromaDB/sentence-transformers, curl for health watchdog
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Install all dependencies (backend + frontend in one image)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Pre-download all-MiniLM-L6-v2 at BUILD TIME ──────────────────────────────
# Eliminates cold-start latency spike on first upload in production.
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('all-MiniLM-L6-v2'); \
print('✅ Model cached.')"

# Copy application source (backend + frontend + launcher)
COPY app/ ./app/
COPY app_ui/ ./app_ui/
COPY start.sh ./

RUN chmod +x start.sh

# Port 7860 = HuggingFace Spaces default public port (Streamlit)
# Port 8000 = FastAPI internal (not exposed to host — same container)
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# start.sh: boots Uvicorn (bg) + waits for /health + exec's Streamlit (fg)
CMD ["bash", "start.sh"]