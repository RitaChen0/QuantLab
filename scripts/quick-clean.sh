#!/bin/bash

# 快速清理緩存腳本（無交互）
# 適合日常開發使用

echo "🚀 快速清理緩存..."

cd "$(dirname "$0")/.."

# 停止服務
docker compose stop frontend >/dev/null 2>&1

# 清理緩存
rm -rf frontend/.nuxt frontend/.output frontend/node_modules/.vite frontend/node_modules/.cache 2>/dev/null
docker compose run --rm frontend sh -c "rm -rf .nuxt .output node_modules/.vite node_modules/.cache" >/dev/null 2>&1

# 重啟服務
docker compose up -d frontend >/dev/null 2>&1

echo "✅ 清理完成！服務已重啟"
echo "📝 訪問 http://localhost:3000/ 驗證"
