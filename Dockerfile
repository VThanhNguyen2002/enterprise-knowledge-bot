FROM python:3.11-slim AS builder

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

# System deps required by ChromaDB & sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from pinned versions for full reproducibility
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# ── Pre-download all-MiniLM-L6-v2 at BUILD TIME ──────────────────────────────
# This eliminates the cold-start latency spike on the first upload request.
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('all-MiniLM-L6-v2'); \
print('✅ Model cached.')"

# Copy application source
COPY app/ ./app/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]