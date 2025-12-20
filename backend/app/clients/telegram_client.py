"""
Telegram Bot Client

單例模式的 Telegram Bot 客戶端，用於發送通知消息。
"""

import asyncio
from typing import Optional
from pathlib import Path
from loguru import logger
from telegram import Bot
from telegram.error import TelegramError
from app.core.config import settings


class TelegramClient:
    """
    Telegram Bot 客戶端（單例模式）

    功能：
    - 發送文字消息（支持 HTML 格式）
    - 發送圖片消息（帶標題）
    - 異步執行，不阻塞主流程

    使用範例：
        client = TelegramClient()
        if client.is_available():
            asyncio.run(client.send_message(
                chat_id="123456789",
                text="<b>回測完成</b>\\n收益率：+15%",
                parse_mode="HTML"
            ))
    """

    _instance: Optional['TelegramClient'] = None
    _bot: Optional[Bot] = None
    _initialized: bool = False

    def __new__(cls):
        """單例模式：確保全局只有一個實例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化 Telegram Bot"""
        if self._initialized:
            return

        try:
            if not settings.TELEGRAM_BOT_TOKEN:
                logger.warning("⚠️  Telegram Bot Token not configured. Telegram notifications disabled.")
                self._initialized = False
                return

            # 創建 Bot 實例
            self._bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

            # 測試連接（異步）
            try:
                # 使用 asyncio 在同步上下文中運行異步代碼
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # 沒有事件循環，創建新的
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if loop.is_running():
                    # 如果事件循環正在運行，延遲驗證
                    logger.info("📱 Telegram Bot initialized (deferred validation - event loop running)")
                    self._initialized = True
                else:
                    # 如果沒有運行中的循環，直接運行
                    bot_info = loop.run_until_complete(self._bot.get_me())
                    logger.info(f"✅ Telegram Bot initialized: @{bot_info.username}")
                    self._initialized = True

            except (RuntimeError, TelegramError) as e:
                # 事件循環衝突或 Telegram API 錯誤，延遲驗證
                logger.warning(f"⚠️  Telegram Bot deferred initialization: {str(e)}")
                # 仍然標記為已初始化，實際使用時再驗證
                self._initialized = True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Telegram Bot: {str(e)}")
            self._initialized = False

    def is_available(self) -> bool:
        """
        檢查客戶端是否可用

        Returns:
            bool: 可用返回 True，否則返回 False
        """
        return self._initialized and self._bot is not None

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True
    ) -> Optional[int]:
        """
        發送文字消息

        Args:
            chat_id: Telegram Chat ID（用戶的 telegram_id）
            text: 消息內容（支持 HTML 格式）
            parse_mode: 解析模式（HTML 或 Markdown）
            disable_web_page_preview: 禁用網頁預覽

        Returns:
            int | None: 成功返回消息 ID，失敗返回 None
        """
        if not self.is_available():
            logger.warning("Telegram Bot not available. Message not sent.")
            return None

        try:
            message = await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview
            )
            logger.info(f"✅ Telegram message sent to {chat_id}: message_id={message.message_id}")
            return message.message_id

        except TelegramError as e:
            logger.error(f"❌ Failed to send Telegram message to {chat_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error sending Telegram message: {str(e)}")
            return None

    async def send_photo(
        self,
        chat_id: str,
        photo_path: str,
        caption: Optional[str] = None,
        parse_mode: str = "HTML"
    ) -> Optional[int]:
        """
        發送圖片消息

        Args:
            chat_id: Telegram Chat ID
            photo_path: 圖片文件路徑
            caption: 圖片標題（可選，支持 HTML）
            parse_mode: 解析模式（HTML 或 Markdown）

        Returns:
            int | None: 成功返回消息 ID，失敗返回 None
        """
        if not self.is_available():
            logger.warning("Telegram Bot not available. Photo not sent.")
            return None

        try:
            # 檢查文件是否存在
            photo_file = Path(photo_path)
            if not photo_file.exists():
                logger.error(f"❌ Photo file not found: {photo_path}")
                return None

            # 發送圖片
            with open(photo_path, 'rb') as photo:
                message = await self._bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode=parse_mode
                )

            logger.info(f"✅ Telegram photo sent to {chat_id}: message_id={message.message_id}")
            return message.message_id

        except TelegramError as e:
            logger.error(f"❌ Failed to send Telegram photo to {chat_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error sending Telegram photo: {str(e)}")
            return None

    async def get_bot_info(self) -> Optional[dict]:
        """
        獲取 Bot 信息

        Returns:
            dict | None: Bot 信息字典或 None
        """
        if not self.is_available():
            return None

        try:
            bot_info = await self._bot.get_me()
            return {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "can_join_groups": bot_info.can_join_groups,
                "can_read_all_group_messages": bot_info.can_read_all_group_messages
            }
        except Exception as e:
            logger.error(f"❌ Failed to get bot info: {str(e)}")
            return None


# Global singleton instance
telegram_client = TelegramClient()
