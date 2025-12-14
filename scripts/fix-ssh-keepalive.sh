#!/bin/bash
# SSH Keep-Alive 優化腳本
# 解決 NAT 超時導致的 SSH 斷線問題

set -e

echo "🔧 修復 SSH Keep-Alive 設定..."

# 備份原始配置
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ 已備份配置到: /etc/ssh/sshd_config.backup.*"

# 優化設定
echo "📝 修改 SSH 設定..."
sudo sed -i 's/^ClientAliveInterval.*/ClientAliveInterval 30/' /etc/ssh/sshd_config
sudo sed -i 's/^ClientAliveCountMax.*/ClientAliveCountMax 5/' /etc/ssh/sshd_config

# 顯示新設定
echo ""
echo "📋 新的 SSH Keep-Alive 設定："
grep -E "ClientAlive|TCPKeepAlive" /etc/ssh/sshd_config

# 重新載入 SSH 服務
echo ""
echo "🔄 重新載入 SSH 服務..."
sudo systemctl reload sshd

echo ""
echo "✅ 完成！新設定："
echo "   - 每 30 秒發送 keep-alive"
echo "   - 最多 5 次無響應"
echo "   - 總超時時間：150 秒（2.5 分鐘）"
echo ""
echo "💡 建議您在客戶端也設定 keep-alive："
echo "   ~/.ssh/config 加入："
echo "   Host 122.116.152.55"
echo "     ServerAliveInterval 30"
echo "     ServerAliveCountMax 5"
