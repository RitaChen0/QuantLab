"""
交易时段配置模块

支持日盘、夜盘的配置化管理。

台股交易时段：
- 日盘（普通股票）：09:00-13:30
  - 上午盘：09:00-12:00
  - 下午盘：13:00-13:30

- 夜盘（期货）：15:00-次日05:00
  - 第一阶段：15:00-23:59
  - 第二阶段：00:00-05:00
"""

from datetime import time
from typing import List, Tuple
from pydantic import BaseModel


class TradingSession(BaseModel):
    """交易时段配置"""
    name: str
    start_time: time
    end_time: time
    description: str = ""

    def contains_time(self, hour: int, minute: int = 0) -> bool:
        """检查指定时间是否在交易时段内"""
        check_time = time(hour, minute)

        # 处理跨日情况（夜盘）
        if self.start_time > self.end_time:
            # 跨日：start_time 到 23:59:59 或 00:00:00 到 end_time
            return check_time >= self.start_time or check_time <= self.end_time
        else:
            # 同日：start_time 到 end_time
            return self.start_time <= check_time <= self.end_time


class TradingHoursConfig:
    """交易时段配置管理器"""

    # 日盘配置（台股现货）
    DAY_TRADING_SESSIONS = [
        TradingSession(
            name="上午盘",
            start_time=time(9, 0),
            end_time=time(12, 0),
            description="台股上午交易时段"
        ),
        TradingSession(
            name="下午盘",
            start_time=time(13, 0),
            end_time=time(13, 30),
            description="台股下午交易时段"
        )
    ]

    # 夜盘配置（期货）
    NIGHT_TRADING_SESSIONS = [
        TradingSession(
            name="夜盘第一阶段",
            start_time=time(15, 0),
            end_time=time(23, 59, 59),
            description="期货夜盘 15:00-23:59"
        ),
        TradingSession(
            name="夜盘第二阶段",
            start_time=time(0, 0),
            end_time=time(5, 0),
            description="期货夜盘 00:00-05:00"
        )
    ]

    @classmethod
    def is_day_trading_time(cls, hour: int, minute: int = 0) -> bool:
        """检查是否为日盘交易时间"""
        return any(
            session.contains_time(hour, minute)
            for session in cls.DAY_TRADING_SESSIONS
        )

    @classmethod
    def is_night_trading_time(cls, hour: int, minute: int = 0) -> bool:
        """检查是否为夜盘交易时间"""
        return any(
            session.contains_time(hour, minute)
            for session in cls.NIGHT_TRADING_SESSIONS
        )

    @classmethod
    def is_trading_time(cls, hour: int, minute: int = 0, include_night: bool = False) -> bool:
        """
        检查是否为交易时间

        Args:
            hour: 小时 (0-23)
            minute: 分钟 (0-59)
            include_night: 是否包含夜盘

        Returns:
            是否为交易时间
        """
        if cls.is_day_trading_time(hour, minute):
            return True

        if include_night and cls.is_night_trading_time(hour, minute):
            return True

        return False

    @classmethod
    def get_pandas_filter_expression(cls, include_night: bool = False) -> str:
        """
        获取 pandas DataFrame 的时间过滤表达式

        Args:
            include_night: 是否包含夜盘

        Returns:
            pandas boolean indexing 表达式字符串
        """
        # 日盘过滤条件
        day_conditions = []
        for session in cls.DAY_TRADING_SESSIONS:
            start_hour = session.start_time.hour
            start_minute = session.start_time.minute
            end_hour = session.end_time.hour
            end_minute = session.end_time.minute

            if start_hour == end_hour:
                # 同一小时内
                condition = (
                    f"((df['datetime'].dt.hour == {start_hour}) & "
                    f"(df['datetime'].dt.minute >= {start_minute}) & "
                    f"(df['datetime'].dt.minute <= {end_minute}))"
                )
            else:
                # 跨小时
                conditions_parts = []

                # 起始小时
                if start_minute > 0:
                    conditions_parts.append(
                        f"((df['datetime'].dt.hour == {start_hour}) & "
                        f"(df['datetime'].dt.minute >= {start_minute}))"
                    )
                else:
                    conditions_parts.append(f"(df['datetime'].dt.hour == {start_hour})")

                # 中间完整小时
                if end_hour - start_hour > 1:
                    conditions_parts.append(
                        f"((df['datetime'].dt.hour > {start_hour}) & "
                        f"(df['datetime'].dt.hour < {end_hour}))"
                    )

                # 结束小时
                if end_minute < 59:
                    conditions_parts.append(
                        f"((df['datetime'].dt.hour == {end_hour}) & "
                        f"(df['datetime'].dt.minute <= {end_minute}))"
                    )
                else:
                    conditions_parts.append(f"(df['datetime'].dt.hour == {end_hour})")

                condition = " | ".join(conditions_parts)

            day_conditions.append(f"({condition})")

        filter_expr = " | ".join(day_conditions)

        # 如果包含夜盘
        if include_night:
            night_conditions = []
            for session in cls.NIGHT_TRADING_SESSIONS:
                start_hour = session.start_time.hour
                end_hour = session.end_time.hour

                if start_hour > end_hour:
                    # 跨日
                    condition = (
                        f"((df['datetime'].dt.hour >= {start_hour}) | "
                        f"(df['datetime'].dt.hour <= {end_hour}))"
                    )
                else:
                    condition = (
                        f"((df['datetime'].dt.hour >= {start_hour}) & "
                        f"(df['datetime'].dt.hour <= {end_hour}))"
                    )

                night_conditions.append(f"({condition})")

            if night_conditions:
                filter_expr = f"({filter_expr}) | ({' | '.join(night_conditions)})"

        return filter_expr

    @classmethod
    def filter_dataframe(cls, df, datetime_column: str = 'datetime', include_night: bool = False):
        """
        过滤 DataFrame，保留交易时段内的数据

        Args:
            df: pandas DataFrame
            datetime_column: 时间列名
            include_night: 是否包含夜盘

        Returns:
            过滤后的 DataFrame
        """
        import pandas as pd

        # 确保时间列为 datetime 类型
        if not pd.api.types.is_datetime64_any_dtype(df[datetime_column]):
            df[datetime_column] = pd.to_datetime(df[datetime_column])

        # 构建过滤条件
        mask = df[datetime_column].apply(
            lambda dt: cls.is_trading_time(dt.hour, dt.minute, include_night)
        )

        return df[mask]


# 导出常用函数
is_day_trading_time = TradingHoursConfig.is_day_trading_time
is_night_trading_time = TradingHoursConfig.is_night_trading_time
is_trading_time = TradingHoursConfig.is_trading_time
filter_trading_hours = TradingHoursConfig.filter_dataframe
