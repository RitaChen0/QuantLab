# 外部訪問配置指南

本指南說明如何配置 QuantLab 讓其他設備（同一網絡或外部網絡）可以訪問。

## 快速開始

所有 localhost 配置現在都可以通過 `.env` 文件修改，不需要改動代碼！

## 配置步驟

### 1. 獲取你的 IP 地址

**Linux/macOS**：
```bash
# 獲取內網 IP
ip addr show | grep "inet " | grep -v 127.0.0.1
# 或
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Windows**：
```cmd
ipconfig | findstr IPv4
```

假設你的內網 IP 是 `192.168.1.100`

### 2. 修改 `.env` 文件

編輯 `.env` 文件中的以下三個配置：

```bash
# ----------------
# CORS
# ----------------
# 將 localhost 替換為你的 IP 地址
ALLOWED_ORIGINS=http://192.168.1.100:3000,http://192.168.1.100:8000

# ----------------
# Frontend
# ----------------
# 前端 API 連接地址
NUXT_PUBLIC_API_BASE=http://192.168.1.100:8000
NUXT_PUBLIC_WS_BASE=ws://192.168.1.100:8000
```

### 3. 重啟服務

```bash
docker compose down
docker compose up -d
```

### 4. 訪問應用

現在你可以從其他設備訪問：

- **前端**: http://192.168.1.100:3000
- **後端 API**: http://192.168.1.100:8000
- **API 文檔**: http://192.168.1.100:8000/docs

## 不同場景的配置範例

### 場景 1: 本機開發（默認）

```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
NUXT_PUBLIC_API_BASE=http://localhost:8000
NUXT_PUBLIC_WS_BASE=ws://localhost:8000
```

### 場景 2: 區域網訪問（同一 WiFi）

```bash
ALLOWED_ORIGINS=http://192.168.1.100:3000,http://192.168.1.100:8000
NUXT_PUBLIC_API_BASE=http://192.168.1.100:8000
NUXT_PUBLIC_WS_BASE=ws://192.168.1.100:8000
```

### 場景 3: 混合模式（本機 + 區域網）

```bash
# 逗號分隔多個來源
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,http://192.168.1.100:3000,http://192.168.1.100:8000
NUXT_PUBLIC_API_BASE=http://192.168.1.100:8000
NUXT_PUBLIC_WS_BASE=ws://192.168.1.100:8000
```

### 場景 4: 生產環境（使用域名）

```bash
ALLOWED_ORIGINS=https://quantlab.yourdomain.com,https://api.yourdomain.com
NUXT_PUBLIC_API_BASE=https://api.yourdomain.com
NUXT_PUBLIC_WS_BASE=wss://api.yourdomain.com
```

## 防火牆設定

如果無法從其他設備訪問，檢查防火牆設定：

### Linux (ufw)
```bash
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
```

### macOS
```bash
# 系統設定 > 網路 > 防火牆 > 防火牆選項
# 允許特定應用程式的連線
```

### Windows
```cmd
netsh advfirewall firewall add rule name="QuantLab Frontend" dir=in action=allow protocol=TCP localport=3000
netsh advfirewall firewall add rule name="QuantLab Backend" dir=in action=allow protocol=TCP localport=8000
```

## Docker Compose 端口映射

檢查 `docker-compose.yml` 中的端口映射（默認已正確配置）：

```yaml
backend:
  ports:
    - "8000:8000"  # 主機:容器

frontend:
  ports:
    - "3000:3000"  # 主機:容器
```

如果你想使用不同的端口（例如 80/443），修改主機端口：

```yaml
frontend:
  ports:
    - "80:3000"  # 從 80 端口訪問前端
```

相應修改 `.env`：
```bash
NUXT_PUBLIC_API_BASE=http://192.168.1.100:8000
```

## 常見問題

### Q: 修改後無法訪問？

1. 確認服務已重啟：`docker compose restart`
2. 檢查防火牆設定
3. 確認 IP 地址正確：`ip addr` 或 `ipconfig`
4. 檢查瀏覽器控制台是否有 CORS 錯誤

### Q: CORS 錯誤？

確保 `ALLOWED_ORIGINS` 包含你訪問的完整 URL（包括協議和端口）：
```bash
# 錯誤
ALLOWED_ORIGINS=192.168.1.100:3000

# 正確
ALLOWED_ORIGINS=http://192.168.1.100:3000
```

### Q: WebSocket 連接失敗？

檢查 `NUXT_PUBLIC_WS_BASE` 使用正確的協議：
- HTTP 使用 `ws://`
- HTTPS 使用 `wss://`

### Q: 如何恢復默認設定？

將 `.env` 中的配置改回 localhost：
```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
NUXT_PUBLIC_API_BASE=http://localhost:8000
NUXT_PUBLIC_WS_BASE=ws://localhost:8000
```

然後重啟服務：
```bash
docker compose restart
```

## 安全建議

1. **開發環境**：使用 HTTP + 區域網 IP 即可
2. **生產環境**：
   - 使用 HTTPS (Let's Encrypt 免費證書)
   - 配置反向代理（Nginx/Caddy）
   - 啟用防火牆限制訪問
   - 使用強密碼和 JWT_SECRET
   - 定期更新依賴套件

## 進階：使用 Nginx 反向代理

如果你想使用域名和 HTTPS，可以配置 Nginx：

```nginx
server {
    listen 80;
    server_name quantlab.yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 相關檔案

- `.env` - 主要配置檔案
- `.env.example` - 配置範例（含詳細註釋）
- `.env.development` - 開發環境配置
- `docker-compose.yml` - Docker 服務編排
- `backend/app/core/config.py` - 後端配置讀取邏輯
- `frontend/nuxt.config.ts` - 前端配置讀取邏輯
