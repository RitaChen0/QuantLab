"""
Encryption utilities for sensitive data
"""

from typing import Optional
from cryptography.fernet import Fernet
from sqlalchemy import TypeDecorator, Text
from loguru import logger


class EncryptedText(TypeDecorator):
    """
    SQLAlchemy custom type for encrypted text fields.

    Uses Fernet (symmetric encryption) to encrypt/decrypt data at the database level.
    The encryption key must be configured in settings.ENCRYPTION_KEY.

    Usage:
        finlab_api_token = Column(EncryptedText(), nullable=True)
    """

    impl = Text
    cache_ok = True

    def __init__(self, *args, **kwargs):
        """Initialize the encrypted text type"""
        super().__init__(*args, **kwargs)
        self._cipher: Optional[Fernet] = None

    def _get_cipher(self) -> Fernet:
        """
        Lazy load the cipher to avoid circular imports.

        Returns:
            Fernet cipher instance
        """
        if self._cipher is None:
            from app.core.config import settings

            if not settings.ENCRYPTION_KEY:
                raise ValueError(
                    "ENCRYPTION_KEY not configured in settings. "
                    "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )

            try:
                self._cipher = Fernet(settings.ENCRYPTION_KEY.encode())
            except Exception as e:
                logger.error(f"Failed to initialize Fernet cipher: {str(e)}")
                raise ValueError(f"Invalid ENCRYPTION_KEY: {str(e)}")

        return self._cipher

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """
        Encrypt the value before storing in database.

        Args:
            value: Plain text value to encrypt
            dialect: SQLAlchemy dialect

        Returns:
            Encrypted value as string, or None if value is None
        """
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(f"EncryptedText requires str, got {type(value).__name__}")

        try:
            cipher = self._get_cipher()
            encrypted = cipher.encrypt(value.encode())
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt value: {str(e)}")
            raise

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """
        Decrypt the value after loading from database.

        Args:
            value: Encrypted value from database
            dialect: SQLAlchemy dialect

        Returns:
            Decrypted plain text value, or None if value is None
        """
        if value is None:
            return None

        try:
            cipher = self._get_cipher()
            decrypted = cipher.decrypt(value.encode())
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt value: {str(e)}")
            # Return None instead of raising to handle corrupted data gracefully
            return None


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        Base64-encoded encryption key as string

    Example:
        >>> key = generate_encryption_key()
        >>> print(f"ENCRYPTION_KEY={key}")
    """
    return Fernet.generate_key().decode('utf-8')


def test_encryption(key: str, test_value: str = "test_secret_123") -> bool:
    """
    Test if an encryption key works correctly.

    Args:
        key: Encryption key to test
        test_value: Test string to encrypt/decrypt

    Returns:
        True if encryption/decryption works, False otherwise
    """
    try:
        cipher = Fernet(key.encode())
        encrypted = cipher.encrypt(test_value.encode())
        decrypted = cipher.decrypt(encrypted).decode('utf-8')
        return decrypted == test_value
    except Exception as e:
        logger.error(f"Encryption test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Generate a new key when run directly
    print("=" * 60)
    print("Encryption Key Generator")
    print("=" * 60)
    print("\nGenerated encryption key:")
    key = generate_encryption_key()
    print(f"\nENCRYPTION_KEY={key}")
    print("\nAdd this to your .env file")
    print("\nTesting encryption...")
    if test_encryption(key):
        print("✅ Encryption test passed!")
    else:
        print("❌ Encryption test failed!")
    print("=" * 60)
