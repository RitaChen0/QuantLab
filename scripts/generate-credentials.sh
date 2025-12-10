#!/bin/bash
# QuantLab 安全憑證生成器
# 用途：為新部署環境生成強隨機憑證

set -e

echo "🔐 QuantLab 安全憑證生成器"
echo "============================================================"
echo ""
echo "此腳本將生成以下安全憑證："
echo "  • JWT_SECRET (64 字元隨機字串)"
echo "  • DB_PASSWORD (32 字元強密碼)"
echo "  • ENCRYPTION_KEY (Fernet 格式金鑰)"
echo ""
echo "============================================================"
echo ""

# 檢查 Docker 是否運行
if ! docker compose ps | grep -q "backend"; then
    echo "⚠️  Backend 服務未運行"
    echo "正在啟動 backend 服務..."
    docker compose up -d backend
    echo "等待服務就緒..."
    sleep 5
fi

# 使用 Python 生成憑證
echo "生成中..."
echo ""

docker compose exec -T backend python -m app.core.security_validator

echo ""
echo "============================================================"
echo ""
echo "📋 使用方法："
echo ""
echo "1. 複製上方生成的憑證"
echo "2. 編輯 .env 檔案：nano .env"
echo "3. 將對應的值貼上到 .env 檔案中"
echo "4. 儲存並關閉檔案"
echo "5. 重啟服務：docker compose restart"
echo ""
echo "⚠️  重要提醒："
echo "   • 請妥善保管這些憑證"
echo "   • 不要將 .env 檔案提交到 Git"
echo "   • 定期更換憑證（建議每 90 天）"
echo ""
echo "============================================================"
