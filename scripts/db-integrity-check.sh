#!/bin/bash
# 快速資料庫完整性檢查
#
# 使用方式:
#   bash scripts/db-integrity-check.sh          # 只檢查
#   bash scripts/db-integrity-check.sh --fix    # 檢查並修復

set -e

echo "=========================================="
echo "🏥 資料庫完整性檢查"
echo "=========================================="
echo ""

cd "$(dirname "$0")/.."

if [ "$1" == "--fix" ]; then
    echo "🔧 模式: 檢查並自動修復"
    docker compose exec backend python /app/scripts/check_database_integrity.py --check-all --fix-all
else
    echo "🔍 模式: 只檢查（不修復）"
    docker compose exec backend python /app/scripts/check_database_integrity.py --check-all
fi

echo ""
echo "=========================================="
echo "✅ 完成"
echo "=========================================="
