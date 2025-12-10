"""
安全驗證器 - 啟動時檢查弱憑證和不安全配置

在應用啟動時執行安全檢查，防止使用範例密碼和弱金鑰部署到生產環境。
"""

import re
import sys
from typing import List, Tuple, Optional
from loguru import logger


class SecurityValidationError(Exception):
    """安全驗證失敗錯誤"""
    pass


class SecurityValidator:
    """
    安全驗證器

    檢查項目：
    1. JWT Secret 強度
    2. 資料庫密碼強度
    3. 加密金鑰格式
    4. 環境變數中的範例值
    """

    # 不安全的範例值模式（不區分大小寫）
    EXAMPLE_PATTERNS = [
        r'your_.*_here',
        r'change.*this',
        r'example',
        r'test.*password',
        r'demo.*key',
        r'sample.*token',
        r'replace.*this',
        r'insert.*here',
        r'generate.*using.*command',
        r'use.*command.*above',
        r'put.*your.*here',
    ]

    # 弱密碼模式
    WEAK_PASSWORD_PATTERNS = [
        r'^password\d*$',
        r'^admin\d*$',
        r'^root\d*$',
        r'^quantlab\d*$',
        r'^123456',
        r'^qwerty',
        r'^abc123',
    ]

    # 最小長度要求
    MIN_JWT_SECRET_LENGTH = 32
    MIN_PASSWORD_LENGTH = 12
    MIN_ENCRYPTION_KEY_LENGTH = 32

    @staticmethod
    def is_example_value(value: str) -> bool:
        """
        檢查是否為範例值

        Args:
            value: 要檢查的值

        Returns:
            是否為範例值
        """
        if not value:
            return True

        value_lower = value.lower()

        for pattern in SecurityValidator.EXAMPLE_PATTERNS:
            if re.search(pattern, value_lower):
                return True

        return False

    @staticmethod
    def is_weak_password(password: str) -> bool:
        """
        檢查是否為弱密碼

        Args:
            password: 要檢查的密碼

        Returns:
            是否為弱密碼
        """
        if not password or len(password) < SecurityValidator.MIN_PASSWORD_LENGTH:
            return True

        password_lower = password.lower()

        for pattern in SecurityValidator.WEAK_PASSWORD_PATTERNS:
            if re.match(pattern, password_lower):
                return True

        # 檢查密碼複雜度
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)

        complexity_score = sum([has_upper, has_lower, has_digit, has_special])

        # 至少需要 3 種字元類型
        if complexity_score < 3:
            return True

        return False

    @staticmethod
    def validate_jwt_secret(jwt_secret: str) -> Tuple[bool, Optional[str]]:
        """
        驗證 JWT Secret

        Args:
            jwt_secret: JWT 密鑰

        Returns:
            (是否有效, 錯誤訊息)
        """
        if not jwt_secret:
            return False, "JWT_SECRET 未設定"

        if SecurityValidator.is_example_value(jwt_secret):
            return False, f"JWT_SECRET 使用範例值：{jwt_secret[:20]}..."

        if len(jwt_secret) < SecurityValidator.MIN_JWT_SECRET_LENGTH:
            return False, f"JWT_SECRET 長度不足（最少 {SecurityValidator.MIN_JWT_SECRET_LENGTH} 字元）"

        # 檢查是否只包含單一字元類型
        if jwt_secret.isalpha() or jwt_secret.isdigit():
            return False, "JWT_SECRET 太簡單（只包含字母或數字）"

        return True, None

    @staticmethod
    def validate_database_password(db_password: str) -> Tuple[bool, Optional[str]]:
        """
        驗證資料庫密碼

        Args:
            db_password: 資料庫密碼

        Returns:
            (是否有效, 錯誤訊息)
        """
        if not db_password:
            return False, "資料庫密碼未設定"

        if SecurityValidator.is_example_value(db_password):
            return False, f"資料庫密碼使用範例值：{db_password[:20]}..."

        if SecurityValidator.is_weak_password(db_password):
            return False, f"資料庫密碼太弱（長度需 >= {SecurityValidator.MIN_PASSWORD_LENGTH}，且包含大小寫字母、數字和特殊字元）"

        return True, None

    @staticmethod
    def validate_encryption_key(encryption_key: str) -> Tuple[bool, Optional[str]]:
        """
        驗證加密金鑰（Fernet 格式）

        Args:
            encryption_key: 加密金鑰

        Returns:
            (是否有效, 錯誤訊息)
        """
        if not encryption_key:
            # 加密金鑰是選填的
            return True, None

        if SecurityValidator.is_example_value(encryption_key):
            return False, f"加密金鑰使用範例值：{encryption_key[:20]}..."

        # Fernet 金鑰應該是 Base64 編碼的 32 bytes (44 字元)
        if len(encryption_key) < SecurityValidator.MIN_ENCRYPTION_KEY_LENGTH:
            return False, f"加密金鑰長度不足（最少 {SecurityValidator.MIN_ENCRYPTION_KEY_LENGTH} 字元）"

        # 檢查是否為有效的 Base64 格式（Fernet 金鑰應該是）
        # Base64 字元集：A-Z, a-z, 0-9, +, /, =
        if not re.match(r'^[A-Za-z0-9+/=]+$', encryption_key):
            logger.warning("加密金鑰格式不正確（應為 Base64 格式）")

        return True, None

    @staticmethod
    def validate_all(
        jwt_secret: str,
        db_password: str,
        encryption_key: str = "",
        environment: str = "development"
    ) -> Tuple[bool, List[str]]:
        """
        執行所有安全驗證

        Args:
            jwt_secret: JWT 密鑰
            db_password: 資料庫密碼
            encryption_key: 加密金鑰（選填）
            environment: 環境名稱（development/production）

        Returns:
            (是否通過驗證, 錯誤訊息列表)
        """
        errors = []

        # 驗證 JWT Secret
        valid, error = SecurityValidator.validate_jwt_secret(jwt_secret)
        if not valid:
            errors.append(f"🔴 JWT Secret: {error}")

        # 驗證資料庫密碼
        valid, error = SecurityValidator.validate_database_password(db_password)
        if not valid:
            errors.append(f"🔴 資料庫密碼: {error}")

        # 驗證加密金鑰（如果提供）
        if encryption_key:
            valid, error = SecurityValidator.validate_encryption_key(encryption_key)
            if not valid:
                errors.append(f"🔴 加密金鑰: {error}")

        # 生產環境必須通過所有檢查
        if environment.lower() == "production" and errors:
            return False, errors

        # 開發環境只警告
        if environment.lower() == "development" and errors:
            logger.warning("⚠️  開發環境偵測到弱憑證：")
            for error in errors:
                logger.warning(f"  {error}")
            logger.warning("⚠️  生產環境將拒絕啟動！請在部署前更換為強憑證。")
            return True, []  # 開發環境允許通過

        return True, []

    @staticmethod
    def validate_settings_on_startup(settings) -> None:
        """
        應用啟動時驗證設定

        Args:
            settings: Settings 物件

        Raises:
            SecurityValidationError: 如果驗證失敗（生產環境）
        """
        logger.info("🔒 執行安全驗證...")

        # 從 DATABASE_URL 提取密碼
        db_password = ""
        if settings.DATABASE_URL:
            # 格式：postgresql://user:password@host:port/database
            # 注意：密碼可能包含特殊字元（包括 @），所以使用 URL 解析
            try:
                from urllib.parse import urlparse
                parsed = urlparse(settings.DATABASE_URL)
                db_password = parsed.password or ""
            except Exception:
                # Fallback: 使用正則表達式（適用於簡單密碼）
                # 注意：這個正則無法處理密碼中包含 @ 的情況
                match = re.search(r'://[^:]+:([^@]+)@', settings.DATABASE_URL)
                if match:
                    db_password = match.group(1)

        # 執行驗證
        is_valid, errors = SecurityValidator.validate_all(
            jwt_secret=settings.JWT_SECRET,
            db_password=db_password,
            encryption_key=settings.ENCRYPTION_KEY,
            environment=settings.ENVIRONMENT
        )

        if not is_valid:
            error_msg = "安全驗證失敗！偵測到不安全的憑證配置：\n\n" + "\n".join(errors)
            error_msg += "\n\n❌ 生產環境拒絕啟動！"
            error_msg += "\n\n修復方法："
            error_msg += "\n1. 檢查 .env 檔案"
            error_msg += "\n2. 將所有範例值替換為強隨機字串"
            error_msg += "\n3. JWT_SECRET: 至少 32 字元的隨機字串"
            error_msg += "\n4. DB_PASSWORD: 至少 12 字元，包含大小寫、數字、特殊字元"
            error_msg += "\n5. ENCRYPTION_KEY: 使用以下命令生成："
            error_msg += "\n   python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""

            logger.error(error_msg)

            # 生產環境拒絕啟動
            if settings.ENVIRONMENT.lower() == "production":
                raise SecurityValidationError(error_msg)
        else:
            logger.info("✅ 安全驗證通過")

    @staticmethod
    def generate_secure_secret(length: int = 64) -> str:
        """
        生成安全的隨機密鑰

        Args:
            length: 金鑰長度

        Returns:
            Base64 編碼的隨機字串
        """
        import secrets
        import base64

        random_bytes = secrets.token_bytes(length)
        return base64.urlsafe_b64encode(random_bytes).decode('utf-8')[:length]

    @staticmethod
    def generate_fernet_key() -> str:
        """
        生成 Fernet 加密金鑰

        Returns:
            Fernet 金鑰（Base64 編碼）
        """
        try:
            from cryptography.fernet import Fernet
            return Fernet.generate_key().decode()
        except ImportError:
            logger.error("cryptography 套件未安裝，無法生成 Fernet 金鑰")
            return ""


# 命令列工具：生成安全憑證
if __name__ == "__main__":
    print("🔐 QuantLab 安全憑證生成器")
    print("=" * 60)
    print()

    print("JWT_SECRET (建議長度 64 字元):")
    print(SecurityValidator.generate_secure_secret(64))
    print()

    print("DB_PASSWORD (建議長度 32 字元，包含特殊字元):")
    print(SecurityValidator.generate_secure_secret(32))
    print()

    print("ENCRYPTION_KEY (Fernet 格式):")
    print(SecurityValidator.generate_fernet_key())
    print()

    print("=" * 60)
    print("✅ 將以上憑證複製到 .env 檔案中")
