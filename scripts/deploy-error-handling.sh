#!/bin/bash

# ================================================
# QuantLab 錯誤處理系統部署腳本
# ================================================
# 用途：一鍵部署增強的錯誤處理系統
# 使用：bash scripts/deploy-error-handling.sh
# ================================================

set -e

echo "============================================"
echo "🚀 部署 QuantLab 錯誤處理系統"
echo "============================================"
echo ""

# 檢查文件是否存在
echo "📋 檢查必要文件..."

FILES=(
    "backend/app/core/exceptions.py"
    "backend/app/main.py"
    "frontend/components/ErrorDisplay.vue"
    "frontend/composables/useErrorHandler.ts"
)

for file in "${FILES[@]}"; do
    if [ -f "/home/ubuntu/QuantLab/$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file 不存在"
        exit 1
    fi
done

echo ""
echo "✅ 所有必要文件已就位"
echo ""

# 檢查環境變數
echo "🔍 檢查環境變數..."

if grep -q "DEBUG=" /home/ubuntu/QuantLab/.env 2>/dev/null; then
    DEBUG_VALUE=$(grep "DEBUG=" /home/ubuntu/QuantLab/.env | cut -d'=' -f2)
    echo "  當前 DEBUG=$DEBUG_VALUE"

    if [ "$DEBUG_VALUE" = "True" ]; then
        echo "  ⚠️  開發環境：會顯示完整堆棧追蹤"
    else
        echo "  ✅ 生產環境：會隱藏敏感信息"
    fi
else
    echo "  ⚠️  未找到 DEBUG 設置，將使用預設值（True）"
fi

echo ""

# 重啟 Backend 服務
echo "🔄 重啟 Backend 服務..."
docker compose restart backend

echo ""
echo "⏳ 等待服務啟動（10 秒）..."
sleep 10

# 健康檢查
echo ""
echo "🏥 執行健康檢查..."

if curl -s http://localhost:8000/health > /dev/null; then
    echo "  ✅ Backend 服務正常運行"
else
    echo "  ❌ Backend 服務異常"
    echo "  提示：查看日誌 docker compose logs backend"
    exit 1
fi

# 測試錯誤處理
echo ""
echo "🧪 測試錯誤處理系統..."

if command -v python3 &> /dev/null; then
    # 檢查是否安裝 rich
    if python3 -c "import rich" 2>/dev/null; then
        echo ""
        python3 /home/ubuntu/QuantLab/backend/test_error_handling.py
    else
        echo "  ⚠️  未安裝 rich，跳過自動測試"
        echo "  提示：pip install rich"
        echo ""
        echo "  手動測試："
        echo "    curl -X POST http://localhost:8000/api/v1/backtest \\"
        echo "      -H 'Content-Type: application/json' \\"
        echo "      -d '{\"invalid\": \"data\"}'"
    fi
else
    echo "  ⚠️  未找到 python3，跳過自動測試"
fi

echo ""
echo "============================================"
echo "✨ 部署完成！"
echo "============================================"
echo ""
echo "📝 使用說明："
echo ""
echo "1. 後端錯誤會自動捕獲並格式化"
echo "2. 開發環境顯示完整堆棧追蹤"
echo "3. 生產環境隱藏敏感信息"
echo ""
echo "🎨 前端使用範例："
echo ""
echo "import { useErrorHandler } from '@/composables/useErrorHandler'"
echo "import ErrorDisplay from '@/components/ErrorDisplay.vue'"
echo ""
echo "const { handleError } = useErrorHandler()"
echo ""
echo "try {"
echo "  await \$fetch('/api/v1/backtest', { ... })"
echo "} catch (error) {"
echo "  handleError(error, { showDialog: true })"
echo "}"
echo ""
echo "📚 完整文檔："
echo "   /home/ubuntu/QuantLab/ENHANCED_ERROR_HANDLING_GUIDE.md"
echo ""
echo "🔗 測試 API："
echo "   http://localhost:8000/docs"
echo ""
echo "🎉 享受更好的錯誤調試體驗！"
echo ""
