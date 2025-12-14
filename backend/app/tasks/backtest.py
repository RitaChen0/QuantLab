"""
Celery 異步回測任務

提供完整的異步回測執行功能：
- 非阻塞執行
- 自動重試
- 進度追蹤
- 結果存儲
"""

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from fastapi import HTTPException
from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.backtest_engine import BacktestEngine
from app.services.qlib_backtest_engine import QlibBacktestEngine
from app.services.backtest_service import BacktestService
from app.models.backtest import BacktestStatus
from app.utils.logging import api_log
from app.utils.redis_lock import backtest_execution_lock
from app.utils.error_handler import get_safe_error_message
from app.utils.chart_generator import backtest_chart_generator
from loguru import logger
from datetime import datetime
from typing import Dict, Any
# from app.tasks.telegram_notifications import send_telegram_notification  # 暫時註解，等待 python-telegram-bot 安裝完成


@celery_app.task(
    bind=True,
    name="app.tasks.run_backtest_async",
    max_retries=3,
    default_retry_delay=300,  # 5 分鐘後重試
    acks_late=True,  # 確保任務不會丟失
    reject_on_worker_lost=True,
    time_limit=3600,  # 硬超時：60 分鐘
    soft_time_limit=3300,  # 軟超時：55 分鐘
)
def run_backtest_async(
    self: Task,
    backtest_id: int,
    user_id: int
) -> Dict[str, Any]:
    """
    異步執行回測任務

    Args:
        self: Celery Task 實例
        backtest_id: 回測 ID
        user_id: 使用者 ID

    Returns:
        回測結果字典

    Raises:
        Exception: 執行失敗時重試或標記為失敗
    """
    db = SessionLocal()

    try:
        logger.info(f"Celery task started: run_backtest_async(backtest_id={backtest_id}, user_id={user_id})")

        # 更新任務狀態為進行中
        self.update_state(
            state='PROGRESS',
            meta={
                'backtest_id': backtest_id,
                'current': 0,
                'total': 100,
                'status': 'Initializing...'
            }
        )

        service = BacktestService(db)

        # 1. 取得回測配置（先檢查是否存在，避免阻塞其他任務）
        try:
            backtest = service.get_backtest_with_result(backtest_id, user_id)
        except HTTPException as e:
            if e.status_code == 404:
                logger.warning(f"Backtest {backtest_id} not found for user {user_id}, skipping task")
                return {
                    "status": "not_found",
                    "backtest_id": backtest_id,
                    "message": "回測已被刪除，任務已取消"
                }
            # Re-raise other HTTP exceptions (like 403 Forbidden)
            raise

        # 2. 檢查狀態
        if backtest.status == BacktestStatus.COMPLETED:
            logger.warning(f"Backtest {backtest_id} already completed")
            return {
                "status": "already_completed",
                "backtest_id": backtest_id,
                "message": "此回測已完成"
            }

        if backtest.status == BacktestStatus.FAILED:
            logger.warning(f"Backtest {backtest_id} already failed, skipping retry")
            return {
                "status": "already_failed",
                "backtest_id": backtest_id,
                "message": "此回測已失敗，請建立新的回測"
            }

        # 3. 使用分佈式鎖防止重複執行（每用戶鎖）
        try:
            with backtest_execution_lock(backtest_id, user_id):
                # 更新狀態為執行中
                service.update_backtest_status(backtest_id, BacktestStatus.RUNNING)
                db.commit()

                logger.info(f"Starting backtest execution: {backtest_id}")

                # 更新進度
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'backtest_id': backtest_id,
                        'current': 10,
                        'total': 100,
                        'status': f'Loading data for {backtest.symbol}...'
                    }
                )

                # 4. 根據 engine_type 選擇回測引擎
                logger.info(f"Backtest engine_type: {backtest.engine_type}")

                if backtest.engine_type == 'qlib':
                    logger.info("Using Qlib backtest engine")
                    engine = QlibBacktestEngine(db)
                else:
                    logger.info("Using Backtrader backtest engine")
                    engine = BacktestEngine(db)

                # 5. 執行回測
                try:
                    # 更新進度
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'backtest_id': backtest_id,
                            'current': 30,
                            'total': 100,
                            'status': 'Running backtest...'
                        }
                    )

                    # 根據引擎類型調用不同的方法
                    if backtest.engine_type == 'qlib':
                        # Qlib 引擎使用異步方法
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        qlib_results = loop.run_until_complete(
                            engine.run_backtest(
                                strategy_code=backtest.strategy.code,
                                symbol=backtest.symbol,
                                start_date=backtest.start_date,
                                end_date=backtest.end_date,
                                initial_capital=float(backtest.initial_capital),
                                parameters=backtest.parameters or {}
                            )
                        )

                        loop.close()

                        # 轉換為標準格式
                        results = engine.convert_to_standard_result(qlib_results)
                    else:
                        # Backtrader 引擎使用同步方法
                        # 從 parameters 中提取回測配置參數
                        params = backtest.parameters or {}
                        backtest_config = params.get('backtest_config', {})

                        results = engine.run_backtest(
                            backtest_id=backtest.id,
                            strategy_code=backtest.strategy.code,
                            stock_id=backtest.symbol,
                            start_date=datetime.fromisoformat(backtest.start_date) if isinstance(backtest.start_date, str) else backtest.start_date,
                            end_date=datetime.fromisoformat(backtest.end_date) if isinstance(backtest.end_date, str) else backtest.end_date,
                            initial_cash=float(backtest.initial_capital),
                            commission=float(backtest_config.get('commission', 0.001425)),
                            tax=float(backtest_config.get('tax', 0.003)),
                            slippage=float(backtest_config.get('slippage', 0.0)),
                            position_size=backtest_config.get('position_size'),
                            max_position_pct=float(backtest_config.get('max_position_pct', 1.0)),
                            strategy_params=params.get('strategy_params', {}),
                            timeframe=backtest.timeframe
                        )

                    # 更新進度
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'backtest_id': backtest_id,
                            'current': 80,
                            'total': 100,
                            'status': 'Saving results...'
                        }
                    )

                    # 6. 儲存結果（統一使用 BacktestEngine 的 save_results）
                    if backtest.engine_type == 'qlib':
                        # Qlib 引擎已轉換為標準格式，直接使用 BacktestEngine 保存
                        bt_engine = BacktestEngine(db)
                        bt_engine.save_results(backtest.id, results)
                    else:
                        # Backtrader 引擎直接保存
                        engine.save_results(backtest.id, results)

                    db.commit()

                    # 7. 記錄成功日誌
                    api_log.log_operation(
                        "run_async",
                        "backtest",
                        backtest.id,
                        user_id,
                        success=True,
                        total_return=results['metrics']['total_return'],
                        total_trades=results['metrics']['total_trades']
                    )

                    logger.info(f"Backtest {backtest_id} completed successfully")

                    # 8. 發送 Telegram 通知（異步，不阻塞）
                    try:
                        # 構建通知消息
                        metrics = results['metrics']
                        total_return = metrics.get('total_return', 0)
                        total_trades = metrics.get('total_trades', 0)
                        win_rate = metrics.get('win_rate', 0)
                        sharpe_ratio = metrics.get('sharpe_ratio', 0)
                        max_drawdown = metrics.get('max_drawdown', 0)

                        notification_title = f"✅ 回測完成：{backtest.name}"
                        notification_message = f"""
<b>回測結果摘要</b>

📊 <b>績效指標</b>
• 總收益率：<b>{total_return:.2%}</b>
• 交易次數：{total_trades} 次
• 勝率：{win_rate:.2%}
• Sharpe 比率：{sharpe_ratio:.2f}
• 最大回撤：{max_drawdown:.2%}

⏰ 回測時間：{backtest.start_date.strftime('%Y-%m-%d')} ~ {backtest.end_date.strftime('%Y-%m-%d')}
💰 初始資金：${backtest.initial_capital:,.0f}

<a href="{settings.FRONTEND_URL}/backtest/{backtest_id}">📈 查看完整報告</a>
"""

                        # 生成權益曲線圖（如果有交易記錄）
                        chart_path = None
                        if results.get('trades') and len(results['trades']) > 0:
                            try:
                                chart_path = backtest_chart_generator.generate_equity_curve_from_trades(
                                    trades_data=results['trades'],
                                    initial_capital=float(backtest.initial_capital),
                                    backtest_id=backtest_id
                                )
                                logger.info(f"權益曲線圖已生成: {chart_path}")
                            except Exception as chart_error:
                                logger.warning(f"生成權益曲線圖失敗: {str(chart_error)}")

                        # 異步發送通知 (暫時註解，等待 python-telegram-bot 安裝完成)
                        # send_telegram_notification.delay(
                        #     user_id=user_id,
                        #     notification_type="backtest_completed",
                        #     title=notification_title,
                        #     message=notification_message,
                        #     image_path=chart_path,
                        #     related_object_type="backtest",
                        #     related_object_id=backtest_id
                        # )

                        # logger.info(f"Telegram notification queued for backtest {backtest_id}")

                    except Exception as e:
                        # 通知失敗不影響回測結果
                        logger.warning(f"Failed to queue Telegram notification: {str(e)}")

                    return {
                        "status": "success",
                        "backtest_id": backtest_id,
                        "metrics": results['metrics'],
                        "message": "回測執行成功"
                    }

                except ValueError as e:
                    # 回測執行失敗
                    logger.error(f"Backtest {backtest_id} execution failed: {str(e)}")

                    # 使用安全的錯誤訊息
                    safe_message = get_safe_error_message(e, context="回測執行")

                    # 更新狀態並記錄錯誤訊息
                    service.update_backtest_status(
                        backtest_id,
                        BacktestStatus.FAILED,
                        error_message=safe_message  # ✅ 將錯誤訊息寫入資料庫
                    )
                    db.commit()

                    api_log.log_operation(
                        "run_async",
                        "backtest",
                        backtest_id,
                        user_id,
                        success=False,
                        error=str(e)  # 日誌記錄完整錯誤
                    )

                    # 不重試資料錯誤，返回安全的錯誤訊息
                    return {
                        "status": "failed",
                        "backtest_id": backtest_id,
                        "error": safe_message,  # 用戶看到的安全訊息
                        "message": safe_message
                    }

        except SoftTimeLimitExceeded:
            # 軟超時 - 任務執行時間過長
            logger.warning(f"Backtest {backtest_id} exceeded soft time limit")

            # 標記為失敗
            try:
                fail_db = SessionLocal()
                try:
                    fail_service = BacktestService(fail_db)
                    fail_service.update_backtest_status(backtest_id, BacktestStatus.FAILED)
                    fail_db.commit()
                finally:
                    fail_db.close()
            except Exception as db_error:
                logger.error(f"Failed to update backtest status after timeout: {str(db_error)}")

            return {
                "status": "failed",
                "backtest_id": backtest_id,
                "error": "回測執行超時（超過 55 分鐘）",
                "message": "回測執行時間過長，已自動終止。請嘗試縮短回測時間範圍或優化策略代碼。"
            }

        except RuntimeError as e:
            # 鎖獲取失敗
            logger.warning(f"Failed to acquire lock for backtest {backtest_id}: {str(e)}")

            # 使用指數退避：1m, 2m, 4m, 8m, 16m
            retry_count = self.request.retries
            countdown = 60 * (2 ** retry_count)
            raise self.retry(exc=e, countdown=countdown, max_retries=5)

    except Exception as e:
        # 其他未預期錯誤
        logger.error(f"Unexpected error in backtest task {backtest_id}: {str(e)}", exc_info=True)

        # 標記為失敗 - 使用獨立的資料庫連接
        try:
            fail_db = SessionLocal()
            try:
                fail_service = BacktestService(fail_db)
                fail_service.update_backtest_status(backtest_id, BacktestStatus.FAILED)
                fail_db.commit()
            finally:
                fail_db.close()
        except Exception as db_error:
            logger.error(f"Failed to update backtest status: {str(db_error)}")

        # 使用指數退避：5m, 10m, 20m
        retry_count = self.request.retries
        countdown = 300 * (2 ** retry_count)
        raise self.retry(exc=e, countdown=countdown, max_retries=3)

    finally:
        db.close()


@celery_app.task(name="app.tasks.get_backtest_progress")
def get_backtest_progress(task_id: str) -> Dict[str, Any]:
    """
    查詢回測任務進度

    Args:
        task_id: Celery 任務 ID

    Returns:
        任務狀態和進度資訊
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    if result.state == 'PENDING':
        response = {
            'state': result.state,
            'status': 'Task is waiting...',
            'current': 0,
            'total': 100
        }
    elif result.state == 'PROGRESS':
        response = {
            'state': result.state,
            'current': result.info.get('current', 0),
            'total': result.info.get('total', 100),
            'status': result.info.get('status', ''),
            'backtest_id': result.info.get('backtest_id')
        }
    elif result.state == 'SUCCESS':
        response = {
            'state': result.state,
            'current': 100,
            'total': 100,
            'status': 'Completed!',
            'result': result.info
        }
    elif result.state == 'FAILURE':
        response = {
            'state': result.state,
            'current': 0,
            'total': 100,
            'status': str(result.info),
            'error': str(result.info)
        }
    else:
        response = {
            'state': result.state,
            'status': 'Unknown state'
        }

    return response
