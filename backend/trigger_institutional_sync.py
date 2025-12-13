#!/usr/bin/env python3
"""
直接觸發法人買賣超數據同步
"""
import sys
sys.path.insert(0, '/app')

from app.core.celery_app import celery_app
from app.tasks.institutional_investor_sync import sync_top_stocks_institutional
from loguru import logger

# 配置日誌
logger.add(sys.stdout, level="INFO")

logger.info("觸發法人買賣超數據同步任務...")

# 使用 apply_async 觸發異步任務
task = sync_top_stocks_institutional.apply_async(
    kwargs={
        'limit': 20,  # 同步 Top 20 股票
        'days': 365   # 同步最近 365 天
    },
    queue='data_sync'
)

logger.info(f"任務已創建: ID={task.id}, Queue=data_sync")
logger.info(f"任務狀態: {task.state}")

# 可選：等待任務完成（最多等待 10 分鐘）
logger.info("等待任務完成...")
try:
    result = task.get(timeout=600)  # 10 分鐘超時
    logger.info(f"任務完成! 結果: {result}")
except Exception as e:
    logger.error(f"任務執行出錯: {e}")
    logger.info(f"任務當前狀態: {task.state}")
    if task.failed():
        logger.error(f"任務失敗: {task.traceback}")
