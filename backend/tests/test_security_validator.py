"""
安全驗證器測試

驗證啟動時的憑證檢查功能是否正常工作。
"""

import pytest
from app.core.security_validator import SecurityValidator, SecurityValidationError


class TestSecurityValidator:
    """測試安全驗證器"""

    def test_detect_example_jwt_secret(self):
        """測試偵測範例 JWT Secret"""
        example_values = [
            "your_jwt_secret_key_change_this_in_production",
            "change_this_secret",
            "your_secret_here",
            "example_jwt_secret",
            "test_password_123",
        ]

        for value in example_values:
            assert SecurityValidator.is_example_value(value), \
                f"應該偵測到範例值：{value}"

    def test_detect_weak_password(self):
        """測試偵測弱密碼"""
        weak_passwords = [
            "password",
            "password123",
            "admin",
            "admin123",
            "root",
            "quantlab",
            "123456",
            "qwerty",
            "abc123",
            "short",  # 太短
            "alllowercase",  # 只有小寫
            "ALLUPPERCASE",  # 只有大寫
            "12345678901234",  # 只有數字
        ]

        for password in weak_passwords:
            assert SecurityValidator.is_weak_password(password), \
                f"應該偵測到弱密碼：{password}"

    def test_accept_strong_password(self):
        """測試接受強密碼"""
        strong_passwords = [
            "MyStr0ng!P@ssw0rd2024",
            "C0mpl3x$P@ssw0rd#2024",
            "S3cur3_P@ssw0rd!#123",
            "R@nd0m$ecret#K3y!987",
        ]

        for password in strong_passwords:
            assert not SecurityValidator.is_weak_password(password), \
                f"不應該偵測為弱密碼：{password}"

    def test_validate_jwt_secret_example_value(self):
        """測試 JWT Secret 範例值驗證"""
        is_valid, error = SecurityValidator.validate_jwt_secret(
            "your_jwt_secret_key_change_this_in_production"
        )

        assert not is_valid, "應該拒絕範例 JWT Secret"
        assert "範例值" in error, f"錯誤訊息應該提到範例值：{error}"

    def test_validate_jwt_secret_too_short(self):
        """測試 JWT Secret 長度不足"""
        is_valid, error = SecurityValidator.validate_jwt_secret("short_secret")

        assert not is_valid, "應該拒絕過短的 JWT Secret"
        assert "長度不足" in error, f"錯誤訊息應該提到長度：{error}"

    def test_validate_jwt_secret_too_simple(self):
        """測試 JWT Secret 過於簡單"""
        is_valid, error = SecurityValidator.validate_jwt_secret(
            "a" * 50  # 50 個 'a'
        )

        assert not is_valid, "應該拒絕過於簡單的 JWT Secret"
        assert "太簡單" in error, f"錯誤訊息應該提到簡單：{error}"

    def test_validate_jwt_secret_strong(self):
        """測試接受強 JWT Secret"""
        strong_secret = "My$tr0ng!JWT$ecret#2024_R@nd0m_K3y!ComplexEnough123"

        is_valid, error = SecurityValidator.validate_jwt_secret(strong_secret)

        assert is_valid, f"應該接受強 JWT Secret，錯誤：{error}"
        assert error is None, "強密鑰不應該有錯誤訊息"

    def test_validate_database_password_example_value(self):
        """測試資料庫密碼範例值"""
        is_valid, error = SecurityValidator.validate_database_password(
            "your_secure_password_here"
        )

        assert not is_valid, "應該拒絕範例資料庫密碼"
        assert "範例值" in error, f"錯誤訊息應該提到範例值：{error}"

    def test_validate_database_password_weak(self):
        """測試弱資料庫密碼"""
        weak_passwords = [
            "password123",
            "admin",
            "quantlab2024",
            "alllowercase",
        ]

        for password in weak_passwords:
            is_valid, error = SecurityValidator.validate_database_password(password)

            assert not is_valid, f"應該拒絕弱密碼：{password}"
            assert "太弱" in error, f"錯誤訊息應該提到弱密碼：{error}"

    def test_validate_database_password_strong(self):
        """測試接受強資料庫密碼"""
        strong_password = "MyD@tab@se!P@ssw0rd#2024"

        is_valid, error = SecurityValidator.validate_database_password(strong_password)

        assert is_valid, f"應該接受強資料庫密碼，錯誤：{error}"
        assert error is None, "強密碼不應該有錯誤訊息"

    def test_validate_encryption_key_example_value(self):
        """測試加密金鑰範例值"""
        is_valid, error = SecurityValidator.validate_encryption_key(
            "generate_a_new_key_using_command_above"
        )

        assert not is_valid, "應該拒絕範例加密金鑰"
        assert "範例值" in error, f"錯誤訊息應該提到範例值：{error}"

    def test_validate_encryption_key_empty(self):
        """測試空加密金鑰（允許）"""
        is_valid, error = SecurityValidator.validate_encryption_key("")

        assert is_valid, "應該允許空加密金鑰（選填欄位）"
        assert error is None, "空金鑰不應該有錯誤訊息"

    def test_validate_encryption_key_valid(self):
        """測試有效的 Fernet 加密金鑰"""
        from cryptography.fernet import Fernet

        fernet_key = Fernet.generate_key().decode()

        is_valid, error = SecurityValidator.validate_encryption_key(fernet_key)

        assert is_valid, f"應該接受有效的 Fernet 金鑰，錯誤：{error}"
        assert error is None, "有效金鑰不應該有錯誤訊息"

    def test_validate_all_production_with_weak_credentials(self):
        """測試生產環境拒絕弱憑證"""
        is_valid, errors = SecurityValidator.validate_all(
            jwt_secret="your_jwt_secret_key_change_this_in_production",
            db_password="your_secure_password_here",
            encryption_key="",
            environment="production"
        )

        assert not is_valid, "生產環境應該拒絕弱憑證"
        assert len(errors) > 0, "應該有錯誤訊息"
        assert any("JWT Secret" in error for error in errors), "應該包含 JWT Secret 錯誤"
        assert any("資料庫密碼" in error for error in errors), "應該包含資料庫密碼錯誤"

    def test_validate_all_development_with_weak_credentials(self):
        """測試開發環境允許弱憑證（但警告）"""
        is_valid, errors = SecurityValidator.validate_all(
            jwt_secret="your_jwt_secret_key_change_this_in_production",
            db_password="your_secure_password_here",
            encryption_key="",
            environment="development"
        )

        # 開發環境允許通過（但會在日誌中警告）
        assert is_valid, "開發環境應該允許弱憑證（會警告）"
        assert len(errors) == 0, "開發環境不應該返回錯誤（只警告）"

    def test_validate_all_production_with_strong_credentials(self):
        """測試生產環境接受強憑證"""
        is_valid, errors = SecurityValidator.validate_all(
            jwt_secret="My$tr0ng!JWT$ecret#2024_R@nd0m_K3y!ComplexEnough123",
            db_password="MyD@tab@se!P@ssw0rd#2024_Str0ng",
            encryption_key="",
            environment="production"
        )

        assert is_valid, f"生產環境應該接受強憑證，錯誤：{errors}"
        assert len(errors) == 0, "強憑證不應該有錯誤"

    def test_generate_secure_secret(self):
        """測試生成安全密鑰"""
        secret = SecurityValidator.generate_secure_secret(64)

        assert len(secret) == 64, "生成的密鑰長度應該正確"
        assert not SecurityValidator.is_example_value(secret), "生成的密鑰不應該是範例值"

        # 生成的密鑰應該是隨機的
        secret2 = SecurityValidator.generate_secure_secret(64)
        assert secret != secret2, "每次生成的密鑰應該不同"

    def test_generate_fernet_key(self):
        """測試生成 Fernet 金鑰"""
        key = SecurityValidator.generate_fernet_key()

        assert len(key) == 44, "Fernet 金鑰長度應該是 44 字元"
        assert key.endswith("="), "Fernet 金鑰應該以 = 結尾（Base64 padding）"

        # 驗證可以用於 Fernet 加密
        from cryptography.fernet import Fernet
        fernet = Fernet(key.encode())
        test_data = b"test data"
        encrypted = fernet.encrypt(test_data)
        decrypted = fernet.decrypt(encrypted)
        assert decrypted == test_data, "生成的金鑰應該可以用於加解密"

    def test_validate_settings_on_startup_production_fail(self):
        """測試生產環境啟動驗證失敗"""
        from unittest.mock import Mock

        # 建立模擬的 Settings 物件（弱憑證）
        mock_settings = Mock()
        mock_settings.DATABASE_URL = "postgresql://user:weak@localhost/db"
        mock_settings.JWT_SECRET = "your_jwt_secret_key_change_this_in_production"
        mock_settings.ENCRYPTION_KEY = ""
        mock_settings.ENVIRONMENT = "production"

        # 生產環境應該拋出異常
        with pytest.raises(SecurityValidationError) as exc_info:
            SecurityValidator.validate_settings_on_startup(mock_settings)

        assert "安全驗證失敗" in str(exc_info.value), "應該包含失敗訊息"

    def test_validate_settings_on_startup_development_pass(self):
        """測試開發環境啟動驗證通過（警告）"""
        from unittest.mock import Mock

        # 建立模擬的 Settings 物件（弱憑證）
        mock_settings = Mock()
        mock_settings.DATABASE_URL = "postgresql://user:weak@localhost/db"
        mock_settings.JWT_SECRET = "your_jwt_secret_key_change_this_in_production"
        mock_settings.ENCRYPTION_KEY = ""
        mock_settings.ENVIRONMENT = "development"

        # 開發環境應該通過（但會警告）
        # 不應該拋出異常
        SecurityValidator.validate_settings_on_startup(mock_settings)

    def test_validate_settings_on_startup_production_pass(self):
        """測試生產環境啟動驗證通過"""
        from unittest.mock import Mock

        # 建立模擬的 Settings 物件（強憑證）
        mock_settings = Mock()
        # 使用更長更複雜的密碼（確保有大小寫、數字、特殊字元）
        mock_settings.DATABASE_URL = "postgresql://user:MyD@tab@se!P@ssw0rd#2024Strong@localhost/db"
        mock_settings.JWT_SECRET = "My$tr0ng!JWT$ecret#2024_R@nd0m_K3y!ComplexEnough123"
        mock_settings.ENCRYPTION_KEY = ""
        mock_settings.ENVIRONMENT = "production"

        # 生產環境強憑證應該通過
        SecurityValidator.validate_settings_on_startup(mock_settings)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
