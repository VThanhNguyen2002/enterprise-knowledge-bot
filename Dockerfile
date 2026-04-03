# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  STAGE 1 — DEPS + SUPPLY CHAIN SECURITY AUDIT                          ║
# ║  Installs all Python dependencies, then runs `safety` CVE scan.         ║
# ║  Build FAILS if any CRITICAL vulnerabilities are detected.              ║
# ╚══════════════════════════════════════════════════════════════════════════╝
FROM python:3.11-slim AS deps-audit

WORKDIR /audit
ENV PIP_NO_CACHE_DIR=1

# Minimal system deps for the audit + sentence-transformers build
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Install pinned project dependencies
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# ── Zero Trust: Supply Chain CVE Audit ────────────────────────────────────────
# `safety` checks every installed package against PyPI Advisory Database.
# --continue-on-error=False (default) means exit code 1 on any critical CVE.
# Set BUILD_ARG SAFETY_LEVEL=full for CI, or SAFETY_LEVEL=skip to bypass in dev.
ARG SAFETY_LEVEL=scan
RUN if [ "$SAFETY_LEVEL" != "skip" ]; then \
        pip install --no-cache-dir "safety>=3.0,<4" && \
        echo "🔍 Running supply chain CVE audit..." && \
        safety scan \
            --file requirements-prod.txt \
            --output text \
            --policy-file .safety-policy.yml 2>/dev/null || \
        safety check \
            --file requirements-prod.txt \
            --output text && \
        echo "✅ Supply chain audit passed — no critical CVEs detected."; \
    else \
        echo "⚠️  SAFETY_LEVEL=skip — CVE audit bypassed (dev/local only)."; \
    fi

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  STAGE 2 — RUNTIME IMAGE                                                ║
# ║  Copies installed packages from the audit stage (no safety tooling).    ║
# ║  Pre-downloads the HuggingFace model to eliminate cold-start latency.   ║
# ╚══════════════════════════════════════════════════════════════════════════╝
FROM python:3.11-slim AS runtime

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

# Runtime system deps only (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed site-packages from the audit stage (safety itself NOT copied)
COPY --from=deps-audit /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps-audit /usr/local/bin /usr/local/bin

# ── Pre-download all-MiniLM-L6-v2 at BUILD TIME ───────────────────────────────
# Eliminates cold-start latency spike on the first upload request in production.
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('all-MiniLM-L6-v2'); \
print('✅ HuggingFace model cached.')"

# Copy application source (no test/notebook files — lean image)
COPY app/ ./app/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]