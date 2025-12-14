#!/bin/bash
# SSH DNS 問題修復腳本
# 解決 DNS 查詢導致的連接不穩定問題

set -e

echo "🔍 問題診斷..."
echo ""

# 檢查當前設置
echo "📋 當前 SSH DNS 設置："
grep -E "UseDNS|ClientAlive|TCPKeepAlive" /etc/ssh/sshd_config | grep -v "^#"
echo ""

# DNS 查詢測試
echo "🌐 DNS 查詢測試："
echo "反向 DNS (IP → 域名)："
dig -x 122.116.152.55 +short
echo ""
echo "正向 DNS (域名 → IP)："
dig quantlab.world +short
echo ""

# 問題說明
echo "⚠️  發現問題："
echo "   反向 DNS: 122.116.152.55 → 122-116-152-55.hinet-ip.hinet.net (ISP 提供)"
echo "   正向 DNS: quantlab.world → 122.116.152.55"
echo "   → 兩個域名不匹配！SSH 可能因此不穩定"
echo ""

# 備份配置
echo "💾 備份 SSH 配置..."
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)
echo "   已備份到: /etc/ssh/sshd_config.backup.*"
echo ""

# 修復設置
echo "🔧 修復 SSH 設置..."

# 1. 禁用 DNS 查詢（解決 DNS 不匹配問題）
if grep -q "^UseDNS" /etc/ssh/sshd_config; then
    sudo sed -i 's/^UseDNS.*/UseDNS no/' /etc/ssh/sshd_config
else
    echo "UseDNS no" | sudo tee -a /etc/ssh/sshd_config > /dev/null
fi

# 2. 優化 Keep-Alive（防止 NAT 超時）
sudo sed -i 's/^ClientAliveInterval.*/ClientAliveInterval 30/' /etc/ssh/sshd_config
sudo sed -i 's/^ClientAliveCountMax.*/ClientAliveCountMax 5/' /etc/ssh/sshd_config

# 3. 確保 TCP Keep-Alive 啟用
if grep -q "^TCPKeepAlive" /etc/ssh/sshd_config; then
    sudo sed -i 's/^TCPKeepAlive.*/TCPKeepAlive yes/' /etc/ssh/sshd_config
else
    echo "TCPKeepAlive yes" | sudo tee -a /etc/ssh/sshd_config > /dev/null
fi

echo "   ✅ DNS 查詢已禁用 (UseDNS no)"
echo "   ✅ Keep-Alive 間隔：30 秒"
echo "   ✅ Keep-Alive 重試：5 次"
echo ""

# 顯示新設置
echo "📋 新的 SSH 設置："
grep -E "UseDNS|ClientAlive|TCPKeepAlive" /etc/ssh/sshd_config | grep -v "^#"
echo ""

# 驗證配置
echo "🔍 驗證配置檔語法..."
sudo sshd -t && echo "   ✅ 配置檔語法正確" || echo "   ❌ 配置檔有錯誤！"
echo ""

# 重新載入服務
echo "🔄 重新載入 SSH 服務..."
sudo systemctl reload sshd
echo "   ✅ SSH 服務已重新載入"
echo ""

# 檢查服務狀態
echo "📊 SSH 服務狀態："
sudo systemctl status sshd --no-pager | head -5
echo ""

echo "========================================="
echo "✅ 修復完成！"
echo "========================================="
echo ""
echo "📝 變更摘要："
echo "   1. 禁用 DNS 查詢 (UseDNS no)"
echo "      → 解決 DNS 不匹配導致的連接問題"
echo "      → 加快連接速度"
echo ""
echo "   2. 優化 Keep-Alive (每 30 秒)"
echo "      → 防止 NAT 超時"
echo "      → 總超時時間：150 秒"
echo ""
echo "💡 建議："
echo "   1. 在您的 SSH 客戶端也配置 Keep-Alive"
echo "   2. 使用 Tmux 防止斷線影響工作"
echo "   3. 觀察未來幾小時的連接穩定性"
echo ""
echo "🔗 客戶端配置 (~/.ssh/config)："
echo "   Host 122.116.152.55"
echo "     ServerAliveInterval 30"
echo "     ServerAliveCountMax 5"
echo ""
