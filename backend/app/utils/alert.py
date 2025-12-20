"""
Alert notification system for QuantLab

Supports multiple notification channels:
- Logging (always enabled)
- File-based alerts (for monitoring)
- Future: Email, Slack, Telegram, etc.
"""
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from loguru import logger
import json


class AlertLevel:
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertManager:
    """
    Manages alert notifications across multiple channels

    Usage:
        alert = AlertManager()
        alert.send(
            level=AlertLevel.ERROR,
            title="Futures sync failed",
            message="Failed to sync TX futures data",
            details={"symbol": "TX", "error": "Connection timeout"}
        )
    """

    def __init__(self, alert_dir: str = "/tmp/quantlab_alerts"):
        """
        Initialize alert manager

        Args:
            alert_dir: Directory to store alert files
        """
        self.alert_dir = Path(alert_dir)
        self.alert_dir.mkdir(parents=True, exist_ok=True)

    def send(
        self,
        level: str,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None
    ):
        """
        Send an alert notification

        Args:
            level: Alert level (info, warning, error, critical)
            title: Alert title (short summary)
            message: Detailed message
            details: Additional details dictionary
            task_id: Optional task ID for tracking
        """
        timestamp = datetime.now(timezone.utc)

        # Create alert payload
        alert_data = {
            "level": level,
            "title": title,
            "message": message,
            "details": details or {},
            "task_id": task_id,
            "timestamp": timestamp.isoformat(),
        }

        # Log to logger
        log_message = f"[ALERT:{level.upper()}] {title} - {message}"
        if details:
            log_message += f" | Details: {details}"

        if level == AlertLevel.CRITICAL:
            logger.critical(log_message)
        elif level == AlertLevel.ERROR:
            logger.error(log_message)
        elif level == AlertLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # Write to alert file
        self._write_alert_file(timestamp, level, alert_data)

        # Future: Send to other channels (email, Slack, etc.)
        # self._send_email(alert_data)
        # self._send_slack(alert_data)

    def _write_alert_file(
        self,
        timestamp: datetime,
        level: str,
        alert_data: Dict[str, Any]
    ):
        """
        Write alert to file for monitoring systems

        Args:
            timestamp: Alert timestamp
            level: Alert level
            alert_data: Alert data dictionary
        """
        try:
            # Create filename with timestamp and level
            filename = f"{timestamp:%Y%m%d_%H%M%S}_{level}.json"
            filepath = self.alert_dir / filename

            # Write alert data as JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(alert_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"[ALERT] Wrote alert file: {filepath}")

        except Exception as e:
            logger.error(f"[ALERT] Failed to write alert file: {e}")

    def get_recent_alerts(
        self,
        level: Optional[str] = None,
        limit: int = 10
    ) -> list:
        """
        Get recent alerts

        Args:
            level: Filter by level (optional)
            limit: Maximum number of alerts to return

        Returns:
            List of alert data dictionaries
        """
        alerts = []

        try:
            # Get all alert files
            alert_files = sorted(
                self.alert_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            for alert_file in alert_files[:limit * 2]:  # Get extra in case of filtering
                try:
                    # Check level filter
                    if level and not alert_file.stem.endswith(f"_{level}"):
                        continue

                    # Read alert data
                    with open(alert_file, 'r', encoding='utf-8') as f:
                        alert_data = json.load(f)
                        alerts.append(alert_data)

                    if len(alerts) >= limit:
                        break

                except Exception as e:
                    logger.warning(f"[ALERT] Failed to read alert file {alert_file}: {e}")

        except Exception as e:
            logger.error(f"[ALERT] Failed to get recent alerts: {e}")

        return alerts

    def clear_old_alerts(self, days: int = 7):
        """
        Clear alert files older than specified days

        Args:
            days: Number of days to keep
        """
        try:
            import time

            cutoff_time = time.time() - (days * 86400)
            deleted_count = 0

            for alert_file in self.alert_dir.glob("*.json"):
                if alert_file.stat().st_mtime < cutoff_time:
                    alert_file.unlink()
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(f"[ALERT] Cleared {deleted_count} old alert files")

        except Exception as e:
            logger.error(f"[ALERT] Failed to clear old alerts: {e}")


# Global alert manager instance
_alert_manager = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def send_alert(
    level: str,
    title: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None
):
    """
    Convenience function to send an alert

    Args:
        level: Alert level (info, warning, error, critical)
        title: Alert title
        message: Detailed message
        details: Additional details
        task_id: Optional task ID
    """
    manager = get_alert_manager()
    manager.send(level, title, message, details, task_id)
