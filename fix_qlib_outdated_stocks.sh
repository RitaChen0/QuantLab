#!/bin/bash
# Qlib 舊數據清理與重新同步腳本
# 生成時間：2025-12-24

set -e

echo "========================================================================"
echo "  Qlib 分鐘線舊數據清理與重新同步"
echo "========================================================================"
echo ""

# 需要刪除並重新同步的活躍股票（有 PostgreSQL 數據）
ACTIVE_STOCKS_WITH_DATA=(
    "6706" "6715" "2743" "2752" "3597" "4558" "4580"
    "6491" "6527" "6592" "6642" "6690" "6697" "6698" "020023"
)

# 需要刪除的股票（活躍但無 PostgreSQL 分鐘線）
ACTIVE_NO_DATA=(
    "8497" "8480" "8913"
)

# 需要刪除的無效股票（不在 stocks 表中）
INVALID_STOCKS=(
    "mtx" "tx" "02001s"
)

echo "📋 清理計劃："
echo "  - ${#ACTIVE_STOCKS_WITH_DATA[@]} 檔活躍股票（將清除舊數據並重新同步）"
echo "  - ${#ACTIVE_NO_DATA[@]} 檔活躍股票（無分鐘線，僅清除）"
echo "  - ${#INVALID_STOCKS[@]} 檔無效股票（直接刪除）"
echo ""

# 詢問用戶確認
read -p "是否繼續？[y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消"
    exit 1
fi

echo ""
echo "========================================================================"
echo "階段 1/3：刪除無效股票的 Qlib 數據"
echo "========================================================================"

for stock in "${INVALID_STOCKS[@]}"; do
    echo "🗑️  刪除 $stock ..."
    docker compose exec backend rm -rf "/data/qlib/tw_stock_minute/features/$stock/" 2>/dev/null || true
done

echo "✅ 無效股票清理完成"
echo ""

echo "========================================================================"
echo "階段 2/3：清除活躍股票（無分鐘線）的舊 Qlib 數據"
echo "========================================================================"

for stock in "${ACTIVE_NO_DATA[@]}"; do
    echo "🗑️  刪除 $stock ..."
    docker compose exec backend rm -rf "/data/qlib/tw_stock_minute/features/$stock/" 2>/dev/null || true
done

echo "✅ 無分鐘線股票清理完成"
echo ""

echo "========================================================================"
echo "階段 3/3：清除並重新同步活躍股票（有 PostgreSQL 數據）"
echo "========================================================================"

# 計數器
total=${#ACTIVE_STOCKS_WITH_DATA[@]}
current=0
success=0
failed=0

for stock in "${ACTIVE_STOCKS_WITH_DATA[@]}"; do
    current=$((current + 1))
    echo ""
    echo "[$current/$total] 處理 $stock ..."

    # 刪除舊數據
    echo "  🗑️  刪除舊 Qlib 數據..."
    docker compose exec backend rm -rf "/data/qlib/tw_stock_minute/features/$stock/" 2>/dev/null || true

    # 重新同步（從 PostgreSQL 導出到 Qlib）
    echo "  📥 重新同步到 Qlib..."
    if docker compose exec -T backend python /app/scripts/export_minute_to_qlib.py \
        --output-dir /data/qlib/tw_stock_minute \
        --stocks "$stock" \
        --smart > /tmp/qlib_sync_${stock}.log 2>&1; then
        echo "  ✅ $stock 同步成功"
        success=$((success + 1))
    else
        echo "  ❌ $stock 同步失敗（詳見 /tmp/qlib_sync_${stock}.log）"
        failed=$((failed + 1))
    fi
done

echo ""
echo "========================================================================"
echo "  清理與同步完成"
echo "========================================================================"
echo "✅ 成功：$success 檔"
echo "❌ 失敗：$failed 檔"
echo "📊 總計：$total 檔"
echo ""

if [ $failed -gt 0 ]; then
    echo "⚠️  部分股票同步失敗，請檢查日誌："
    echo "   ls -lh /tmp/qlib_sync_*.log"
fi

echo ""
echo "🎯 建議後續動作："
echo "   1. 驗證修復結果：重新運行問題股票掃描"
echo "   2. 重啟 Celery 任務：docker compose restart celery-worker celery-beat"
echo ""
