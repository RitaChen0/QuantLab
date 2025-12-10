# QuantLab 安全文檔

本文檔整合了 QuantLab 的安全審計、修復記錄和監控指南。

## 目錄

- [安全概述](#安全概述)
- [已修復的安全問題](#已修復的安全問題)
- [安全最佳實踐](#安全最佳實踐)
- [安全監控](#安全監控)
- [定期安全檢查](#定期安全檢查)

---

## 安全概述

### 安全原則

QuantLab 遵循以下安全設計原則：

1. **最小權限原則**：用戶和服務只擁有必要的最小權限
2. **深度防禦**：多層安全控制，不依賴單一防護措施
3. **安全預設**：預設配置即為安全配置
4. **輸入驗證**：所有外部輸入都需驗證
5. **錯誤處理**：不洩漏敏感信息的錯誤訊息
6. **加密存儲**：敏感數據加密存儲
7. **審計日誌**：記錄所有重要操作

### 安全框架

- **認證**：JWT (JSON Web Token)
- **密碼加密**：bcrypt (cost factor 12)
- **API 安全**：速率限制、輸入驗證、CORS 控制
- **代碼安全**：AST 解析驗證、白名單/黑名單機制
- **網路安全**：HTTPS、防火牆、容器隔離

---

## 已修復的安全問題

### 1. 策略代碼注入防護

**問題**：用戶提交的策略代碼可能包含惡意代碼

**修復** (`app/services/strategy_service.py`)：
```python
import ast

def validate_strategy_code(code: str) -> None:
    """驗證策略代碼安全性"""

    # 1. 解析為 AST
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise HTTPException(400, f"語法錯誤: {str(e)}")

    # 2. 白名單模組
    ALLOWED_MODULES = {
        'backtrader', 'bt', 'pandas', 'pd', 'numpy', 'np',
        'talib', 'ta', 'datetime', 'qlib', 'lightgbm', 'sklearn'
    }

    # 3. 黑名單函數
    DANGEROUS_FUNCTIONS = {
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input', 'raw_input',
        'execfile', 'reload', 'vars', 'dir'
    }

    # 4. 黑名單屬性
    DANGEROUS_ATTRS = {
        '__globals__', '__code__', '__closure__',
        '__builtins__', '__dict__', '__class__'
    }

    # 5. 遍歷 AST 檢查
    for node in ast.walk(tree):
        # 檢查危險函數調用
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in DANGEROUS_FUNCTIONS:
                    raise HTTPException(400, f"禁止使用函數: {node.func.id}")

        # 檢查危險屬性訪問
        if isinstance(node, ast.Attribute):
            if node.attr in DANGEROUS_ATTRS:
                raise HTTPException(400, f"禁止訪問屬性: {node.attr}")
```

**狀態**：✅ 已修復並測試

### 2. 憑證安全存儲

**問題**：資料庫憑證可能硬編碼在代碼中

**修復**：
1. 所有憑證改用環境變數 (`.env`)
2. `.env.example` 不包含實際憑證
3. `.gitignore` 排除 `.env` 檔案
4. Docker secrets 用於生產環境

**最佳實踐**：
```bash
# .env（不提交到 Git）
DATABASE_URL=postgresql://user:password@host:5432/db
JWT_SECRET=strong_random_secret_here
FINLAB_API_TOKEN=your_token_here

# .env.example（提交到 Git）
DATABASE_URL=postgresql://user:password@localhost:5432/quantlab
JWT_SECRET=change_this_secret
FINLAB_API_TOKEN=your_token_here
```

**狀態**：✅ 已修復

### 3. Qlib 代碼執行隔離

**問題**：Qlib 策略執行可能訪問系統資源

**修復方案**：

**選項 1：Docker 隔離**（生產環境）
```yaml
# docker-compose.yml
services:
  backend:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - RDAGENT_ENABLE_DOCKER=true
```

**選項 2：沙箱執行**（開發環境）
```python
# 使用受限的執行環境
import subprocess
import tempfile

def execute_qlib_strategy(code: str):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as f:
        f.write(code)
        f.flush()

        # 使用 subprocess 執行，限制資源
        result = subprocess.run(
            ['python', f.name],
            timeout=60,  # 60 秒超時
            capture_output=True,
            env={'PYTHONPATH': '/app'}  # 限制環境變數
        )
```

**狀態**：✅ 已實作（預設 Docker 隔離關閉）

### 4. SQL 注入防護

**問題**：用戶輸入可能導致 SQL 注入

**修復**：全面使用 SQLAlchemy ORM 和參數化查詢

**安全範例**：
```python
# ✅ 正確：使用 ORM
user = db.query(User).filter(User.username == username).first()

# ✅ 正確：參數化查詢
result = db.execute(
    text("SELECT * FROM users WHERE username = :username"),
    {"username": username}
)

# ❌ 錯誤：字串拼接（SQL 注入風險）
query = f"SELECT * FROM users WHERE username = '{username}'"
```

**狀態**：✅ 已審查並修復

### 5. XSS 防護

**問題**：用戶輸入可能包含 XSS 腳本

**修復**：
1. Vue.js 自動轉義（預設行為）
2. 後端 API 返回 `Content-Type: application/json`
3. CSP (Content Security Policy) 標頭
4. 危險 HTML 使用 `v-html` 時需額外驗證

**狀態**：✅ 已實作

### 6. CORS 配置

**問題**：未限制跨域訪問

**修復** (`app/main.py`)：
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(','),  # 從 .env 讀取
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**配置**：
```bash
# .env
ALLOWED_ORIGINS=http://localhost:3000,http://192.168.1.100:3000
```

**狀態**：✅ 已實作

### 7. 速率限制

**問題**：API 未限制請求頻率，可能遭受 DDoS 攻擊

**修復** (`app/core/rate_limit.py`)：
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# 應用速率限制
@router.post("/")
@limiter.limit("10/hour")  # 每小時 10 次
async def create_strategy(...):
    pass
```

**當前限制**：
- 策略建立：10 requests/hour
- 策略更新：30 requests/hour
- 策略驗證：20 requests/minute
- 回測建立：10 requests/hour
- RD-Agent 因子挖掘：3 requests/hour

**狀態**：✅ 已實作

### 8. 密碼安全

**問題**：密碼雜湊演算法不夠強

**修復**：
- 使用 bcrypt (cost factor 12)
- 密碼最小長度：8 字元
- 建議使用強密碼（大小寫字母、數字、特殊字元）

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 雜湊密碼
hashed = pwd_context.hash(password)

# 驗證密碼
is_valid = pwd_context.verify(plain_password, hashed_password)
```

**狀態**：✅ 已實作

---

## 安全最佳實踐

### 環境變數管理

**開發環境**：
```bash
# 1. 複製範例檔案
cp .env.example .env

# 2. 生成強隨機密鑰
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. 填入實際憑證
vim .env
```

**生產環境**：
```bash
# 使用 Docker secrets
echo "strong_secret_here" | docker secret create jwt_secret -

# 在 docker-compose.yml 中引用
services:
  backend:
    secrets:
      - jwt_secret
```

### JWT Token 管理

**最佳實踐**：
1. **短期 Access Token**：30 分鐘有效期
2. **長期 Refresh Token**：7 天有效期
3. **Token 輪換**：使用 Refresh Token 獲取新的 Access Token
4. **安全儲存**：前端使用 localStorage（HTTPS only）
5. **登出處理**：清除客戶端 Token（後端可選黑名單）

### 代碼審查檢查清單

提交 Pull Request 時，確認：
- [ ] 無硬編碼憑證
- [ ] 無 SQL 注入風險
- [ ] 無 XSS 風險
- [ ] 用戶輸入已驗證
- [ ] 敏感操作有權限檢查
- [ ] 錯誤訊息不洩漏敏感信息
- [ ] 新增 API 有速率限制
- [ ] 新增功能有單元測試

---

## 安全監控

### 日誌監控

**關鍵事件記錄**：
```python
from app.utils.logging import api_log

# 記錄所有認證嘗試
api_log.log_operation("login", "auth", user_id, success=True/False)

# 記錄敏感操作
api_log.log_operation("delete", "strategy", strategy_id, user_id, success=True)

# 記錄異常訪問
logger.warning(f"Unauthorized access attempt: {request.url}")
```

**日誌查看**：
```bash
# 查看認證失敗
docker compose logs backend | grep "login.*success=False"

# 查看速率限制觸發
docker compose logs backend | grep "429"

# 查看異常錯誤
docker compose logs backend | grep -i "error\|exception"
```

### 異常檢測

**監控指標**：
1. **失敗登入次數**：短時間內多次失敗可能為暴力破解
2. **速率限制觸發**：頻繁觸發可能為 DDoS 攻擊
3. **異常 API 調用**：非正常時間或頻率的 API 調用
4. **策略代碼驗證失敗**：可能為惡意代碼提交嘗試

**告警機制**：
```python
# 示例：失敗登入告警
if failed_login_count > 5:
    send_alert(f"User {username} has {failed_login_count} failed logins")
    lock_account(username, duration=15*60)  # 鎖定 15 分鐘
```

### 定期安全掃描

```bash
# Python 依賴漏洞掃描
pip install safety
safety check -r backend/requirements.txt

# Node.js 依賴漏洞掃描
cd frontend
npm audit

# Docker 映像掃描
docker scan quantlab-backend:latest
```

---

## 定期安全檢查

### 每週檢查

- [ ] 查看異常登入記錄
- [ ] 檢查速率限制觸發情況
- [ ] 查看錯誤日誌異常模式
- [ ] 檢查未授權訪問嘗試

### 每月檢查

- [ ] 更新依賴套件（安全補丁）
- [ ] 審查新增功能的安全性
- [ ] 檢查 JWT Secret 是否需要輪換
- [ ] 驗證備份和恢復流程

### 每季檢查

- [ ] 完整安全審計
- [ ] 滲透測試（可選）
- [ ] 更新安全文檔
- [ ] 安全培訓和意識提升

---

## 事件響應

### 安全事件處理流程

1. **檢測**：透過監控系統發現異常
2. **評估**：判斷事件嚴重程度
3. **遏制**：立即採取措施限制影響
4. **根除**：移除威脅並修復漏洞
5. **恢復**：恢復正常運作
6. **總結**：記錄事件並改進流程

### 緊急聯絡

- **開發團隊**：[GitHub Issues](https://github.com/yourusername/quantlab/issues)
- **安全問題**：請私下聯繫（不公開）

---

## 相關文檔

- [CLAUDE.md](../CLAUDE.md) - 安全注意事項章節
- [README.md](../README.md) - 免責聲明
- [docs/GUIDES.md](./GUIDES.md) - 使用指南
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - Web 應用安全風險
