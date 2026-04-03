#!/usr/bin/env bash
# start.sh — Single-Container Process Bootstrap
# ===============================================
# Strategy: Run both FastAPI and Streamlit inside one container.
#
#   - FastAPI (Uvicorn)  → port 8000  — runs in BACKGROUND
#   - Streamlit          → port 7860  — runs in FOREGROUND (Docker tracks this PID)
#
# Why this works on free tiers (HuggingFace Spaces / Render):
#   • Only ONE container / ONE process group is required.
#   • Port 7860 is the default public port on HuggingFace Spaces.
#   • Streamlit communicates with FastAPI via localhost (same container network).
#   • If Uvicorn crashes, the health-check loop (below) will detect it.
#
# Production note: For a paid VPS, prefer the full docker-compose.yml stack
# (separate containers, Nginx, Redis, Gunicorn) for true isolation and scaling.

set -euo pipefail

echo "=========================================="
echo "  Enterprise Knowledge Bot — Starting up  "
echo "=========================================="

# ── 1. Ensure data directories exist ─────────────────────────────────────────
mkdir -p data temp_uploads
echo "✅ Data directories ready."

# ── 2. Start FastAPI backend in the background ────────────────────────────────
echo "⏳ Starting FastAPI backend on port 8000..."
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info \
    &

UVICORN_PID=$!
echo "   FastAPI PID: $UVICORN_PID"

# ── 3. Wait for backend to become healthy before starting Streamlit ────────────
echo "⏳ Waiting for backend health check..."
MAX_WAIT=60
ELAPSED=0
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        echo "❌ Backend failed to start within ${MAX_WAIT}s. Dumping logs..."
        # Give Uvicorn 2s to flush stderr before aborting
        sleep 2
        kill "$UVICORN_PID" 2>/dev/null || true
        exit 1
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    echo "   ...waiting (${ELAPSED}s)"
done
echo "✅ Backend is healthy!"

# ── 4. Background watchdog: restart Uvicorn if it crashes ─────────────────────
# Prevents the container from appearing healthy while the API is down.
(
    while true; do
        sleep 15
        if ! kill -0 "$UVICORN_PID" 2>/dev/null; then
            echo "⚠️  [watchdog] Uvicorn crashed — restarting..."
            uvicorn app.main:app \
                --host 0.0.0.0 \
                --port 8000 \
                --workers 1 \
                --log-level info \
                &
            UVICORN_PID=$!
            echo "   [watchdog] New FastAPI PID: $UVICORN_PID"
        fi
    done
) &

# ── 5. Start Streamlit in FOREGROUND on port 7860 ─────────────────────────────
# exec replaces this shell process — Streamlit becomes PID 1 equivalent.
# Docker will track this process for container lifecycle.
echo "⏳ Starting Streamlit frontend on port 7860..."
exec streamlit run app_ui/main_app.py \
    --server.port 7860 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --browser.gatherUsageStats false
