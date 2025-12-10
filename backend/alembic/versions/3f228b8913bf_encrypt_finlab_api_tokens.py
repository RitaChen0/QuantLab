"""encrypt_finlab_api_tokens

Revision ID: 3f228b8913bf
Revises: 4f097a9131f3
Create Date: 2025-12-03 13:53:40.988618

This migration encrypts existing plain text FinLab API tokens in the database.
It uses Fernet symmetric encryption to protect sensitive API credentials.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from cryptography.fernet import Fernet, InvalidToken
import os


# revision identifiers, used by Alembic.
revision: str = '3f228b8913bf'
down_revision: Union[str, None] = '4f097a9131f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def get_cipher():
    """Get Fernet cipher from environment variable"""
    encryption_key = os.getenv('ENCRYPTION_KEY')
    if not encryption_key:
        raise ValueError(
            "ENCRYPTION_KEY not found in environment. "
            "Please set it before running this migration."
        )
    return Fernet(encryption_key.encode())


def is_encrypted(cipher: Fernet, value: str) -> bool:
    """Check if a value is already encrypted"""
    if not value:
        return False
    try:
        cipher.decrypt(value.encode())
        return True
    except (InvalidToken, Exception):
        return False


def upgrade() -> None:
    """
    Encrypt all existing plain text FinLab API tokens.

    This migration:
    1. Retrieves all users with non-null finlab_api_token
    2. Checks if each token is already encrypted
    3. Encrypts plain text tokens using Fernet
    4. Updates the database with encrypted values
    """
    print("Starting migration: Encrypting FinLab API tokens...")

    try:
        cipher = get_cipher()
    except ValueError as e:
        print(f"⚠️  Warning: {str(e)}")
        print("⚠️  Skipping encryption. Please set ENCRYPTION_KEY and re-run migration.")
        return

    # Get database connection
    conn = op.get_bind()

    # Fetch all users with API tokens
    result = conn.execute(
        text("SELECT id, finlab_api_token FROM users WHERE finlab_api_token IS NOT NULL")
    )

    users = result.fetchall()
    encrypted_count = 0
    skipped_count = 0

    for user_id, token in users:
        if not token:
            continue

        # Check if already encrypted
        if is_encrypted(cipher, token):
            print(f"  User {user_id}: Token already encrypted, skipping")
            skipped_count += 1
            continue

        # Encrypt the plain text token
        try:
            encrypted_token = cipher.encrypt(token.encode()).decode('utf-8')

            # Update the database
            conn.execute(
                text("UPDATE users SET finlab_api_token = :token WHERE id = :user_id"),
                {"token": encrypted_token, "user_id": user_id}
            )

            print(f"  User {user_id}: Token encrypted successfully")
            encrypted_count += 1
        except Exception as e:
            print(f"  User {user_id}: Failed to encrypt token - {str(e)}")

    # Commit the transaction
    conn.commit()

    print(f"\n✅ Migration completed:")
    print(f"   - Encrypted: {encrypted_count} tokens")
    print(f"   - Skipped (already encrypted): {skipped_count} tokens")


def downgrade() -> None:
    """
    Decrypt all encrypted FinLab API tokens back to plain text.

    ⚠️  WARNING: This exposes sensitive API tokens as plain text in the database.
    Only use this for rollback purposes in development environments.
    """
    print("Starting rollback: Decrypting FinLab API tokens...")

    try:
        cipher = get_cipher()
    except ValueError as e:
        print(f"⚠️  Warning: {str(e)}")
        print("⚠️  Cannot decrypt without ENCRYPTION_KEY. Skipping rollback.")
        return

    # Get database connection
    conn = op.get_bind()

    # Fetch all users with API tokens
    result = conn.execute(
        text("SELECT id, finlab_api_token FROM users WHERE finlab_api_token IS NOT NULL")
    )

    users = result.fetchall()
    decrypted_count = 0
    skipped_count = 0

    for user_id, token in users:
        if not token:
            continue

        # Try to decrypt
        try:
            decrypted_token = cipher.decrypt(token.encode()).decode('utf-8')

            # Update the database with plain text
            conn.execute(
                text("UPDATE users SET finlab_api_token = :token WHERE id = :user_id"),
                {"token": decrypted_token, "user_id": user_id}
            )

            print(f"  User {user_id}: Token decrypted")
            decrypted_count += 1
        except InvalidToken:
            print(f"  User {user_id}: Token not encrypted or invalid, skipping")
            skipped_count += 1
        except Exception as e:
            print(f"  User {user_id}: Failed to decrypt token - {str(e)}")

    # Commit the transaction
    conn.commit()

    print(f"\n✅ Rollback completed:")
    print(f"   - Decrypted: {decrypted_count} tokens")
    print(f"   - Skipped: {skipped_count} tokens")
