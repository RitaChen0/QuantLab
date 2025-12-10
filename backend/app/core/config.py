"""
Application Configuration
Using Pydantic Settings for environment variable management
"""

from typing import List, Any
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from loguru import logger


class Settings(BaseSettings):
    """應用設定"""

    # Application
    APP_NAME: str = "QuantLab"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # User Quotas
    MAX_STRATEGIES_PER_USER: int = 50  # Maximum strategies per user
    MAX_BACKTESTS_PER_USER: int = 200  # Maximum backtests per user
    MAX_BACKTESTS_PER_STRATEGY: int = 50  # Maximum backtests per strategy

    # Request Limits (防止 DoS 攻擊)
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10 MB - 一般 API 請求
    MAX_FILE_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB - 檔案上傳
    MAX_STRATEGY_CODE_SIZE: int = 100 * 1024  # 100 KB - 策略代碼

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Cache Security - For signing cached data (防止 pickle 反序列化攻擊)
    CACHE_SIGNING_KEY: str = ""

    # Encryption - For encrypting sensitive data in database
    ENCRYPTION_KEY: str = ""

    # CORS - 從環境變數讀取，支援逗號分隔多個來源
    # 設為 Optional 讓 Pydantic 可以接受字串輸入
    ALLOWED_ORIGINS: Any = None

    @model_validator(mode='after')
    def parse_allowed_origins(self):
        """Parse ALLOWED_ORIGINS from comma-separated string or list"""
        if self.ALLOWED_ORIGINS is None:
            self.ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:8000"]
        elif isinstance(self.ALLOWED_ORIGINS, str):
            self.ALLOWED_ORIGINS = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
        elif not isinstance(self.ALLOWED_ORIGINS, list):
            self.ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:8000"]
        return self

    # FinLab
    FINLAB_API_TOKEN: str = ""
    FINLAB_API_BASE_URL: str = "https://api.finlab.tw"

    # OpenAI (Optional)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 2000

    # Anthropic (Optional)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"

    # Email (SMTP)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "QuantLab"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False

    # Frontend URL (for email verification links)
    FRONTEND_URL: str = "http://localhost:3000"

    # Celery
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # Broker APIs (Optional)
    SHIOAJI_API_KEY: str = ""
    SHIOAJI_SECRET_KEY: str = ""
    FUGLE_API_KEY: str = ""
    FUGLE_SECRET_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

    def validate_security(self) -> None:
        """
        驗證安全設定

        在應用啟動時檢查憑證安全性，防止使用範例密碼部署到生產環境。

        Raises:
            SecurityValidationError: 如果生產環境使用不安全的憑證
        """
        from app.core.security_validator import SecurityValidator
        SecurityValidator.validate_settings_on_startup(self)


# Create global settings instance
settings = Settings()

# 執行安全驗證（在導入時）
try:
    settings.validate_security()
except Exception as e:
    # 如果是 SecurityValidationError，應該在 validate_security() 中已經記錄
    # 這裡只是確保錯誤能被捕獲
    if "SecurityValidationError" in str(type(e)):
        logger.error("安全驗證失敗，應用無法啟動")
        raise
    else:
        # 其他錯誤也記錄但不阻止啟動（可能是開發環境問題）
        logger.warning(f"安全驗證時發生錯誤: {str(e)}")
