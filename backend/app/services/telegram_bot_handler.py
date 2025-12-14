"""
Telegram Bot 命令處理器

使用長輪詢（polling）模式接收和處理用戶命令。
"""

import asyncio
from typing import Optional
from loguru import logger
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.user import UserRepository
from app.schemas.user import UserUpdate
from app.utils.cache import cache


class TelegramBotHandler:
    """Telegram Bot 命令處理器"""

    def __init__(self):
        self.application: Optional[Application] = None
        self.is_running = False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        處理 /start 命令

        Args:
            update: Telegram 更新
            context: 上下文
        """
        await update.message.reply_text(
            "👋 歡迎使用 QuantLab Telegram 通知服務！\n\n"
            "📱 使用方法：\n"
            "1. 在 QuantLab 網站上生成綁定驗證碼\n"
            "2. 在此處發送：/bind 您的驗證碼\n"
            "3. 綁定成功後，您將收到回測完成通知\n\n"
            "❓ 需要幫助？發送 /help 查看完整說明"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        處理 /help 命令

        Args:
            update: Telegram 更新
            context: 上下文
        """
        help_text = """
📖 <b>QuantLab Telegram 通知服務說明</b>

🔗 <b>綁定帳號</b>
1. 登入 QuantLab 網站
2. 進入「帳號設定」→「Telegram 通知」
3. 點擊「生成驗證碼」
4. 在此處發送：/bind 您的驗證碼
5. 綁定成功後，系統會發送確認消息

📊 <b>可接收的通知</b>
• 回測完成通知（含績效摘要和圖表）
• RD-Agent 因子挖掘完成通知
• 市場提醒（即將推出）

⚙️ <b>通知設置</b>
• 在網站上可自訂通知偏好
• 設定靜默時段（夜間免打擾）
• 選擇是否包含圖表

🔓 <b>解除綁定</b>
在網站「帳號設定」中點擊「解除綁定」

❓ 更多問題？請訪問：{settings.FRONTEND_URL}/help
"""
        await update.message.reply_html(help_text)

    async def bind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        處理 /bind 命令

        格式：/bind ABC123

        Args:
            update: Telegram 更新
            context: 上下文
        """
        chat_id = str(update.effective_chat.id)
        user = update.effective_user

        # 檢查參數
        if not context.args or len(context.args) != 1:
            await update.message.reply_text(
                "❌ 驗證碼格式錯誤\n\n"
                "正確格式：/bind ABC123\n"
                "請在 QuantLab 網站上生成驗證碼後重試"
            )
            return

        verification_code = context.args[0].upper()

        # 查找驗證碼對應的用戶
        db = SessionLocal()

        try:
            # 從 Redis 查找驗證碼
            user_id = None
            for key in cache.redis.scan_iter("telegram:verification:*"):
                stored_code = cache.get(key.decode())
                if stored_code == verification_code:
                    # 提取 user_id
                    user_id = int(key.decode().split(":")[-1])
                    break

            if not user_id:
                await update.message.reply_text(
                    "❌ 驗證碼無效或已過期\n\n"
                    "請重新在 QuantLab 網站上生成驗證碼\n"
                    "驗證碼有效期：10 分鐘"
                )
                logger.warning(f"Invalid verification code: {verification_code}")
                return

            # 檢查是否已被其他用戶綁定
            user_repo = UserRepository()
            existing_user = db.query(
                db.query(user_repo.__class__).filter_by(telegram_id=chat_id).exists()
            ).scalar()

            if existing_user:
                await update.message.reply_text(
                    "⚠️ 此 Telegram 帳號已綁定到其他 QuantLab 帳號\n\n"
                    "如需重新綁定，請先在網站上解除舊綁定"
                )
                return

            # 更新用戶的 telegram_id
            quantlab_user = user_repo.get_by_id(db, user_id)

            if not quantlab_user:
                await update.message.reply_text(
                    "❌ 找不到對應的 QuantLab 帳號\n\n"
                    "請確認您已註冊 QuantLab 帳號"
                )
                return

            # 檢查是否已綁定
            if quantlab_user.telegram_id:
                await update.message.reply_text(
                    "⚠️ 您的 QuantLab 帳號已綁定其他 Telegram\n\n"
                    "如需更換，請先在網站上解除綁定"
                )
                return

            # 執行綁定
            user_update = UserUpdate(telegram_id=chat_id)
            user_repo.update(db, quantlab_user, user_update)

            # 刪除驗證碼
            redis_key = f"telegram:verification:{user_id}"
            cache.delete(redis_key)

            # 發送成功消息
            success_message = f"""
✅ <b>綁定成功！</b>

🎉 您的 QuantLab 帳號已成功綁定 Telegram
👤 用戶名：{quantlab_user.username}
📧 Email：{quantlab_user.email}

📱 <b>接下來您將收到：</b>
• 回測完成通知
• RD-Agent 因子挖掘結果
• 系統重要提醒

⚙️ 通知設置：{settings.FRONTEND_URL}/account/telegram

祝您交易順利！📈
"""
            await update.message.reply_html(success_message)

            logger.info(
                f"✅ User {quantlab_user.username} (ID: {user_id}) "
                f"bound to Telegram chat {chat_id}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to bind Telegram: {str(e)}")
            await update.message.reply_text(
                "❌ 綁定失敗，請稍後再試\n\n"
                f"錯誤：{str(e)}"
            )

        finally:
            db.close()

    async def unbind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        處理 /unbind 命令

        Args:
            update: Telegram 更新
            context: 上下文
        """
        chat_id = str(update.effective_chat.id)
        db = SessionLocal()

        try:
            # 查找綁定的用戶
            user_repo = UserRepository()

            # 使用原生 SQLAlchemy 查詢
            from app.models.user import User
            quantlab_user = db.query(User).filter(User.telegram_id == chat_id).first()

            if not quantlab_user:
                await update.message.reply_text(
                    "⚠️ 未找到綁定的 QuantLab 帳號\n\n"
                    "您可能尚未綁定，或已經解除綁定"
                )
                return

            # 解除綁定
            user_update = UserUpdate(telegram_id=None)
            user_repo.update(db, quantlab_user, user_update)

            await update.message.reply_text(
                "✅ 解除綁定成功\n\n"
                "您將不再收到 QuantLab 的通知\n"
                "如需重新綁定，請在網站上生成新的驗證碼"
            )

            logger.info(
                f"✅ User {quantlab_user.username} (ID: {quantlab_user.id}) "
                f"unbound from Telegram chat {chat_id}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to unbind Telegram: {str(e)}")
            await update.message.reply_text(
                "❌ 解除綁定失敗，請稍後再試\n\n"
                f"錯誤：{str(e)}"
            )

        finally:
            db.close()

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """處理未知命令"""
        await update.message.reply_text(
            "❓ 未知命令\n\n"
            "可用命令：\n"
            "/start - 開始使用\n"
            "/help - 查看說明\n"
            "/bind 驗證碼 - 綁定帳號\n"
            "/unbind - 解除綁定"
        )

    async def start_polling(self):
        """啟動長輪詢"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN not configured")
            return

        try:
            # 創建 Application（增加超時設置）
            self.application = (
                Application.builder()
                .token(settings.TELEGRAM_BOT_TOKEN)
                .connect_timeout(30.0)
                .read_timeout(30.0)
                .write_timeout(30.0)
                .pool_timeout(30.0)
                .build()
            )

            # 註冊命令處理器
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("bind", self.bind_command))
            self.application.add_handler(CommandHandler("unbind", self.unbind_command))

            # 註冊未知命令處理器
            self.application.add_handler(
                MessageHandler(filters.COMMAND, self.unknown_command)
            )

            # 初始化並啟動輪詢
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)

            self.is_running = True
            logger.info("✅ Telegram Bot polling started")

            # 保持運行
            while self.is_running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ Failed to start Telegram Bot polling: {str(e)}")
            raise

        finally:
            await self.stop_polling()

    async def stop_polling(self):
        """停止長輪詢"""
        if self.application:
            try:
                self.is_running = False
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("✅ Telegram Bot polling stopped")
            except Exception as e:
                logger.error(f"❌ Failed to stop Telegram Bot polling: {str(e)}")


# 全局實例
telegram_bot_handler = TelegramBotHandler()


# 啟動函數（可在獨立進程或線程中運行）
async def run_telegram_bot():
    """運行 Telegram Bot 長輪詢"""
    await telegram_bot_handler.start_polling()


if __name__ == "__main__":
    # 直接運行此文件以啟動 Bot
    asyncio.run(run_telegram_bot())
