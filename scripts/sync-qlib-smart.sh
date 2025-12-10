#!/bin/bash
#
# Qlib 智慧同步腳本
# 自動判斷需要同步的日期範圍，只更新新增的數據
#
# 使用方式：
#   ./scripts/sync-qlib-smart.sh              # 同步所有股票
#   ./scripts/sync-qlib-smart.sh --test       # 測試模式（僅 10 檔）
#   ./scripts/sync-qlib-smart.sh --stock 2330 # 同步單一股票
#

# 預設參數
OUTPUT_DIR="/data/qlib/tw_stock_v2"
STOCKS="all"
LIMIT=""

# 解析參數
while [[ $# -gt 0 ]]; do
    case $1 in
        --test)
            LIMIT="--limit 10"
            echo "🧪 測試模式：僅同步 10 檔股票"
            shift
            ;;
        --stock)
            STOCKS="$2"
            echo "📊 同步指定股票：$STOCKS"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            echo "未知參數: $1"
            echo "使用方式: $0 [--test] [--stock STOCK_ID] [--output-dir DIR]"
            exit 1
            ;;
    esac
done

echo "════════════════════════════════════════════════════════════"
echo "Qlib 智慧同步"
echo "════════════════════════════════════════════════════════════"
echo "輸出目錄: $OUTPUT_DIR"
echo "股票範圍: $STOCKS"
echo ""

# 執行智慧同步（使用 v2 腳本）
docker compose exec backend python /app/scripts/export_to_qlib_v2.py \
  --output-dir "$OUTPUT_DIR" \
  --stocks "$STOCKS" \
  --smart \
  $LIMIT

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ 同步完成"
echo "════════════════════════════════════════════════════════════"
