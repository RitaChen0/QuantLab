"""
Clients package for third-party integrations
"""

from app.clients.telegram_client import TelegramClient, telegram_client

__all__ = ["TelegramClient", "telegram_client"]
