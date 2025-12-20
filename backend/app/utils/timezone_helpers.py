"""
Timezone Helper Functions

Provides utilities for handling timezone conversions in QuantLab.

IMPORTANT: System-wide Timezone Strategy
----------------------------------------
- **Default**: All datetime fields use UTC (timezone-aware)
- **Exception**: stock_minute_prices table uses Taiwan time (timezone-naive)

This exception exists because:
1. The table contains 60M+ rows and is compressed by TimescaleDB
2. Changing the column type requires decompressing all chunks (several hours)
3. The data is already stored as Taiwan time and converting would be risky

For all other operations, use UTC timestamps.
"""

from datetime import datetime, timezone
import pytz

# Taiwan timezone constant
TAIWAN_TZ = pytz.timezone('Asia/Taipei')


def naive_taipei_to_utc(dt: datetime) -> datetime:
    """
    Convert a timezone-naive datetime (assumed to be Taiwan time) to UTC with timezone.

    Use this when reading from stock_minute_prices table.

    Args:
        dt: Naive datetime object (no tzinfo), assumed to be Taiwan time

    Returns:
        Timezone-aware datetime in UTC

    Example:
        >>> taipei_naive = datetime(2025, 12, 19, 15, 30, 0)  # Taiwan 15:30
        >>> utc_aware = naive_taipei_to_utc(taipei_naive)
        >>> print(utc_aware)
        2025-12-19 07:30:00+00:00  # UTC 07:30
    """
    if dt.tzinfo is not None:
        raise ValueError(f"Expected naive datetime, got timezone-aware: {dt}")

    # Localize to Taiwan timezone
    taipei_aware = TAIWAN_TZ.localize(dt)

    # Convert to UTC
    return taipei_aware.astimezone(timezone.utc)


def utc_to_naive_taipei(dt: datetime) -> datetime:
    """
    Convert a UTC datetime (timezone-aware) to naive Taiwan time.

    Use this when writing to stock_minute_prices table.

    Args:
        dt: Timezone-aware datetime in UTC

    Returns:
        Naive datetime in Taiwan time (no tzinfo)

    Example:
        >>> utc_aware = datetime(2025, 12, 19, 7, 30, 0, tzinfo=timezone.utc)
        >>> taipei_naive = utc_to_naive_taipei(utc_aware)
        >>> print(taipei_naive)
        2025-12-19 15:30:00  # Taiwan 15:30 (no timezone)
    """
    if dt.tzinfo is None:
        raise ValueError(f"Expected timezone-aware datetime, got naive: {dt}")

    # Convert to Taiwan timezone
    taipei_aware = dt.astimezone(TAIWAN_TZ)

    # Remove timezone info
    return taipei_aware.replace(tzinfo=None)


def now_taipei_naive() -> datetime:
    """
    Get current Taiwan time as naive datetime.

    Use this when inserting current time to stock_minute_prices.

    Returns:
        Naive datetime in Taiwan time

    Example:
        >>> now = now_taipei_naive()
        >>> print(now)
        2025-12-19 15:30:00  # Current Taiwan time (no timezone)
    """
    utc_now = datetime.now(timezone.utc)
    return utc_to_naive_taipei(utc_now)


def now_utc() -> datetime:
    """
    Get current UTC time (timezone-aware).

    Use this for all other datetime operations in the system.

    Returns:
        Timezone-aware datetime in UTC

    Example:
        >>> now = now_utc()
        >>> print(now)
        2025-12-19 07:30:00+00:00  # Current UTC time
    """
    return datetime.now(timezone.utc)


def today_taiwan() -> 'date':
    """
    Get current date in Taiwan timezone.

    Use this when you need today's date for Taiwan market data (stocks, options, futures).
    This ensures the date is based on Taiwan time, not UTC.

    Returns:
        date object representing today in Taiwan

    Example:
        >>> # When Taiwan time is 2025-12-21 01:00 but UTC is 2025-12-20 17:00
        >>> taiwan_date = today_taiwan()
        >>> print(taiwan_date)
        2025-12-21  # Correct Taiwan date
        >>>
        >>> # If you used UTC date instead:
        >>> utc_date = datetime.now(timezone.utc).date()
        >>> print(utc_date)
        2025-12-20  # Wrong for Taiwan market!
    """
    from datetime import date
    return now_taipei_naive().date()


def parse_datetime_safe(dt_input: datetime | str) -> datetime:
    """
    Parse datetime input and ensure it is timezone-aware (UTC).

    Handles both string inputs and datetime objects. If the input is naive,
    it assumes UTC timezone.

    Args:
        dt_input: Either a datetime object or an ISO 8601 string

    Returns:
        Timezone-aware datetime in UTC

    Raises:
        ValueError: If string cannot be parsed as datetime

    Example:
        >>> # String input with timezone
        >>> dt = parse_datetime_safe("2025-12-20T08:18:21+08:00")
        >>> print(dt)
        2025-12-20 00:18:21+00:00  # Converted to UTC

        >>> # String input without timezone (assumed UTC)
        >>> dt = parse_datetime_safe("2025-12-20T08:18:21")
        >>> print(dt)
        2025-12-20 08:18:21+00:00  # Assumed UTC

        >>> # Datetime input already timezone-aware
        >>> dt_aware = datetime(2025, 12, 20, 8, 18, 21, tzinfo=timezone.utc)
        >>> dt = parse_datetime_safe(dt_aware)
        >>> print(dt)
        2025-12-20 08:18:21+00:00  # Unchanged

        >>> # Datetime input naive (assumed UTC)
        >>> dt_naive = datetime(2025, 12, 20, 8, 18, 21)
        >>> dt = parse_datetime_safe(dt_naive)
        >>> print(dt)
        2025-12-20 08:18:21+00:00  # Added UTC timezone
    """
    # If string, parse it
    if isinstance(dt_input, str):
        dt = datetime.fromisoformat(dt_input)
    else:
        dt = dt_input

    # If naive, assume UTC
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    # If already timezone-aware, convert to UTC
    return dt.astimezone(timezone.utc)


# Example usage:
"""
from app.utils.timezone_helpers import (
    naive_taipei_to_utc,
    utc_to_naive_taipei,
    now_taipei_naive,
    now_utc,
    parse_datetime_safe,
    today_taiwan,
)

# 1. Reading from stock_minute_prices (convert Taiwan → UTC)
result = db.query(StockMinutePrice).first()
utc_time = naive_taipei_to_utc(result.datetime)  # Convert to UTC for processing

# 2. Writing to stock_minute_prices (convert UTC → Taiwan)
utc_now = now_utc()
record = StockMinutePrice(
    datetime=utc_to_naive_taipei(utc_now),  # Convert to Taiwan naive time
    ...
)

# Or simply use the helper
record = StockMinutePrice(
    datetime=now_taipei_naive(),  # Current Taiwan time
    ...
)

# 3. Parsing datetime from API/user input (ensure timezone-aware)
from_api = parse_datetime_safe(start_datetime)  # String or datetime → UTC aware
results = query.filter(StockPrice.date >= from_api).all()

# 4. Getting today's date for Taiwan market
taiwan_today = today_taiwan()  # date object in Taiwan timezone
stocks_today = query.filter(StockPrice.date == taiwan_today).all()

# 5. Recording timestamps (always use UTC)
task = RDAgentTask(
    created_at=now_utc(),  # Timezone-aware UTC
    ...
)
"""
