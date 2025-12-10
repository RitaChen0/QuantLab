#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
# 使用 4 個 workers 提高並發處理能力
# 注意：--reload 與 --workers 不兼容，生產環境使用 workers
if [ "$ENVIRONMENT" = "production" ]; then
    echo "Starting in PRODUCTION mode with 4 workers..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
else
    echo "Starting in DEVELOPMENT mode with reload..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
