# 網絡連線問題診斷與修復指南

## 📋 問題症狀

- SSH (Port 22) 頻繁斷線，需要不斷重連
- 服務連線不穩定，有時很難連上
- 使用過程中突然失去連線

## 🔍 問題根源

**NAT 超時（Network Address Translation Timeout）**

當您在 NAT 後面（家用路由器、公司防火牆）連接到伺服器時：
1. 路由器會建立一個連接映射（您的內網 IP → 伺服器 IP）
2. 如果連接閒置太久（通常 90-120 秒），路由器會清除這個映射
3. 清除後，雙方都不知道連接已斷，導致超時

**原始 SSH 設定的問題**：
- ClientAliveInterval 60 秒（每 60 秒檢查一次）
- ClientAliveCountMax 3（最多 3 次無回應）
- 總超時：180 秒（3 分鐘）
- **問題**：60 秒間隔不夠頻繁，無法對抗短超時的 NAT

## 🛠️ 解決方案

### 1️⃣ 伺服器端優化（推薦）

執行修復腳本：

```bash
cd /home/ubuntu/QuantLab/scripts
./fix-ssh-keepalive.sh
```

這會將設定改為：
- ClientAliveInterval 30 秒（每 30 秒檢查一次）
- ClientAliveCountMax 5（最多 5 次無回應）
- 總超時：150 秒（2.5 分鐘）

### 2️⃣ 客戶端優化（強烈建議）

在您的電腦上編輯 SSH 配置：

**Windows (使用 PowerShell):**
```powershell
notepad $env:USERPROFILE\.ssh\config
```

**macOS/Linux:**
```bash
nano ~/.ssh/config
```

加入以下內容：
```
Host 122.116.152.55
    ServerAliveInterval 30
    ServerAliveCountMax 5
    TCPKeepAlive yes
```

或者使用通配符（適用所有主機）：
```
Host *
    ServerAliveInterval 30
    ServerAliveCountMax 5
    TCPKeepAlive yes
```

### 3️⃣ 使用 Tmux/Screen（終極方案）

即使 SSH 斷線，也能保持會話：

```bash
# 安裝 tmux
sudo apt install tmux -y

# 啟動新會話
tmux new -s work

# 斷線後重新連接
tmux attach -t work

# 常用快捷鍵
Ctrl+B D  # 分離會話（背景執行）
Ctrl+B C  # 建立新視窗
Ctrl+B N  # 切換到下一個視窗
```

## 📊 診斷工具

### 快速診斷

```bash
cd /home/ubuntu/QuantLab/scripts
./network-diagnosis.sh
```

這會檢查：
- 系統資源（CPU、內存、磁盤）
- Docker 容器狀態
- 網絡連接統計
- SSH 連接歷史
- 網絡延遲

### 手動檢查指令

```bash
# 檢查 SSH keep-alive 設定
grep ClientAlive /etc/ssh/sshd_config

# 檢查連接狀態
ss -s

# 檢查 TIME_WAIT 連接數
netstat -ant | grep TIME_WAIT | wc -l

# 檢查 SSH 日誌
journalctl -u ssh -n 20

# 測試網絡延遲
ping -c 5 8.8.8.8
```

## ⚡ 其他可能問題

### 1. TIME_WAIT 連接過多

如果 `netstat -ant | grep TIME_WAIT | wc -l` 超過 1000：

```bash
# 優化 TCP 設定
sudo sysctl -w net.ipv4.tcp_fin_timeout=30
sudo sysctl -w net.ipv4.tcp_tw_reuse=1

# 永久保存
echo "net.ipv4.tcp_fin_timeout=30" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_tw_reuse=1" | sudo tee -a /etc/sysctl.conf
```

### 2. 防火牆問題

檢查防火牆規則：

```bash
sudo ufw status
sudo iptables -L -n
```

### 3. Docker 網絡問題

重啟網絡：

```bash
cd /home/ubuntu/QuantLab
docker compose restart nginx frontend backend
```

## 📚 參考資料

- [SSH Keep-Alive 最佳實踐](https://www.ssh.com/academy/ssh/config)
- [NAT 超時問題解析](https://www.rfc-editor.org/rfc/rfc5382)
- [Linux TCP 優化](https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt)

## 🆘 仍然有問題？

如果執行上述步驟後仍有問題，可能需要：
1. 聯絡網路管理員（如果在公司網路）
2. 檢查路由器設定（如果在家用網路）
3. 考慮使用 VPN 或更換網路
4. 使用 Mosh 代替 SSH（https://mosh.org/）
