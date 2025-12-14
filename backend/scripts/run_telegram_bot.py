#!/usr/bin/env python3
"""
Telegram Bot 長輪詢啟動腳本

使用方式：
    python scripts/run_telegram_bot.py

或在 Docker 中：
    docker compose exec backend python /app/scripts/run_telegram_bot.py
"""

import sys
import asyncio
from pathlib import Path

# 添加項目路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.telegram_bot_handler import run_telegram_bot
from loguru import logger


def main():
    """主函數"""
    logger.info("🚀 啟動 Telegram Bot 長輪詢服務...")

    try:
        asyncio.run(run_telegram_bot())
    except KeyboardInterrupt:
        logger.info("⏹️  Telegram Bot 服務已停止（用戶中斷）")
    except Exception as e:
        logger.error(f"❌ Telegram Bot 服務異常退出: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
