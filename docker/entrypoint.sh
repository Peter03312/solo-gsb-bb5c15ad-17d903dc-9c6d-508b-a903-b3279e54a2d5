#!/usr/bin/env bash
set -euo pipefail

# Ensure storage directories exist (they also live on the mounted volume).
mkdir -p "${DATA_DIR}/media/audio" "${DATA_DIR}/media/transcripts"

# Tables are created on startup (Base.metadata.create_all in the app lifespan);
# this script is the single place for future one-off migrations/seed data.

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-1}"

echo "==> 口述史编年工作台启动于 http://0.0.0.0:${PORT} （数据目录 ${DATA_DIR}）"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers "${WORKERS}"
