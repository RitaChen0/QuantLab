"""
Uvicorn 日誌過濾器

用於過濾監控端點的訪問日誌
"""
import logging


class ExcludeHealthMetricsFilter(logging.Filter):
    """過濾 /health 和 /metrics 端點的訪問日誌"""

    def filter(self, record: logging.LogRecord) -> bool:
        """
        過濾日誌記錄

        Returns:
            False: 過濾掉（/health, /metrics）
            True: 保留日誌
        """
        message = record.getMessage()
        # 過濾 /health 和 /metrics 請求
        return not ('"/health ' in message or '"/metrics ' in message)
