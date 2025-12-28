"""
策略實盤監控 Celery 任務

定時檢測 ACTIVE 策略的買賣信號並發送 Telegram 通知
"""

from celery import Task
from typing import List, Dict
from datetime import datetime
from loguru import logger

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.strategy_signal_detector import StrategySignalDetector
from app.tasks.telegram_notifications import send_telegram_notification
from app.utils.task_history import record_task_history


@celery_app.task(
    bind=True,
    name="app.tasks.monitor_active_strategies",
    max_retries=2,
    default_retry_delay=300,  # 5 分鐘後重試
    acks_late=True,
    time_limit=600,  # 硬超時：10 分鐘
    soft_time_limit=540,  # 軟超時：9 分鐘
)
@record_task_history
def monitor_active_strategies(
    self: Task,
    lookback_days: int = 60
) -> Dict:
    """
    監控所有 ACTIVE 狀態的策略，檢測買賣信號

    Args:
        self: Celery Task 實例
        lookback_days: 數據回溯天數

    Returns:
        {
            "total_strategies": int,
            "total_signals": int,
            "signals_sent": int,
            "signals_filtered": int,  # 重複信號數量
            "errors": List[str]
        }
    """
    db = SessionLocal()

    try:
        logger.info("📊 [STRATEGY_MONITOR] 開始監控 ACTIVE 策略...")

        # 創建信號檢測器
        detector = StrategySignalDetector(db)

        # 檢測所有 ACTIVE 策略的信號
        signals = detector.detect_signals_for_active_strategies(
            lookback_days=lookback_days
        )

        if not signals:
            logger.info("📊 [STRATEGY_MONITOR] 沒有檢測到任何信號")
            return {
                "total_strategies": 0,
                "total_signals": 0,
                "signals_sent": 0,
                "signals_filtered": 0,
                "errors": []
            }

        # 統計資訊
        total_signals = len(signals)
        signals_sent = 0
        signals_filtered = 0
        errors = []

        # 處理每個信號
        for signal in signals:
            try:
                # 檢查重複信號（15 分鐘內相同股票相同方向）
                is_duplicate = detector.is_duplicate_signal(
                    strategy_id=signal['strategy_id'],
                    stock_id=signal['stock_id'],
                    signal_type=signal['signal_type'],
                    minutes=15
                )

                if is_duplicate:
                    logger.info(
                        f"🔁 [STRATEGY_MONITOR] 過濾重複信號: "
                        f"{signal['stock_id']} {signal['signal_type']}"
                    )
                    signals_filtered += 1
                    continue

                # 保存信號到資料庫
                signal_record = detector.save_signal(signal)

                # 發送 Telegram 通知（只發送給策略擁有者）
                _send_signal_notification(signal)

                signals_sent += 1

                logger.info(
                    f"✅ [STRATEGY_MONITOR] 信號已發送給用戶 {signal['user_id']}: "
                    f"策略=[{signal['strategy_name']}] "
                    f"{signal['stock_id']} {signal['signal_type']} @ {signal.get('price', 'N/A')}"
                )

            except Exception as e:
                error_msg = f"處理信號失敗 ({signal['stock_id']}): {str(e)}"
                errors.append(error_msg)
                logger.error(f"❌ [STRATEGY_MONITOR] {error_msg}")
                continue

        logger.info(
            f"✅ [STRATEGY_MONITOR] 監控完成: "
            f"總信號={total_signals}, 已發送={signals_sent}, 已過濾={signals_filtered}"
        )

        return {
            "total_strategies": len(set(s['strategy_id'] for s in signals)),
            "total_signals": total_signals,
            "signals_sent": signals_sent,
            "signals_filtered": signals_filtered,
            "errors": errors
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f"❌ [STRATEGY_MONITOR] 監控任務失敗: {error_message}")

        # 重試機制
        if self.request.retries < self.max_retries:
            logger.info(
                f"🔄 [STRATEGY_MONITOR] 重試中... "
                f"(第 {self.request.retries + 1}/{self.max_retries} 次)"
            )
            raise self.retry(exc=e, countdown=self.default_retry_delay)

        # 達到最大重試次數
        return {
            "total_strategies": 0,
            "total_signals": 0,
            "signals_sent": 0,
            "signals_filtered": 0,
            "errors": [error_message]
        }

    finally:
        db.close()


def _send_signal_notification(signal: Dict) -> None:
    """
    發送信號通知到 Telegram（只發送給策略擁有者）

    Args:
        signal: 信號字典，必須包含:
            - user_id: 策略擁有者的用戶 ID
            - strategy_name: 策略名稱
            - stock_id: 股票代碼
            - signal_type: 信號類型 (BUY/SELL)
            - price: 價格
            - datetime: 時間
    """
    # 構建通知訊息
    signal_emoji = "🟢 買入" if signal['signal_type'] == 'BUY' else "🔴 賣出"

    price_str = f"NT$ {signal['price']:.2f}" if signal.get('price') else "N/A"

    message = f"""
<b>🔔 交易信號提醒</b>

<b>策略：</b>{signal['strategy_name']}
<b>股票：</b>{signal['stock_id']}
<b>信號：</b>{signal_emoji}
<b>價格：</b>{price_str}
<b>時間：</b>{signal['datetime'].strftime('%Y-%m-%d %H:%M:%S')}

<i>這是系統自動檢測的信號，請謹慎判斷後再決定是否交易。</i>
"""

    logger.debug(
        f"📤 [NOTIFICATION] 發送交易信號通知給用戶 {signal['user_id']}: "
        f"{signal['stock_id']} {signal['signal_type']}"
    )

    # 異步發送 Telegram 通知（只發送給策略擁有者）
    send_telegram_notification.apply_async(
        args=[
            signal['user_id'],  # 策略擁有者的用戶 ID
            'trading_signal',
            f"交易信號 - {signal['stock_id']} {signal_emoji}",
            message.strip()
        ],
        kwargs={
            'channels': ['telegram'],
            'related_object_type': 'strategy_signal',
            'related_object_id': signal.get('signal_id')
        }
    )


@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_old_signals",
    max_retries=1,
    acks_late=True,
    time_limit=300,
)
@record_task_history
def cleanup_old_signals(
    self: Task,
    days_to_keep: int = 30
) -> Dict:
    """
    清理舊的信號記錄（可選任務）

    Args:
        self: Celery Task 實例
        days_to_keep: 保留天數

    Returns:
        {
            "deleted_count": int
        }
    """
    from datetime import timedelta
    from app.models.strategy_signal import StrategySignal
    from app.utils.timezone_helpers import now_utc

    db = SessionLocal()

    try:
        cutoff_date = now_utc() - timedelta(days=days_to_keep)

        # 刪除舊記錄
        deleted = (
            db.query(StrategySignal)
            .filter(StrategySignal.detected_at < cutoff_date)
            .delete()
        )

        db.commit()

        logger.info(
            f"🗑️ [CLEANUP] 已清理 {deleted} 筆舊信號記錄 "
            f"(保留 {days_to_keep} 天)"
        )

        return {"deleted_count": deleted}

    except Exception as e:
        db.rollback()
        logger.error(f"❌ [CLEANUP] 清理舊信號失敗: {str(e)}")
        raise

    finally:
        db.close()
