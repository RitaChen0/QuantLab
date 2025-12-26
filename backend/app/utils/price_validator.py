"""
價格數據驗證工具

提供通用的價格數據驗證邏輯，確保在源頭阻止無效數據插入資料庫。
與資料庫 CHECK 約束形成雙層防護。
"""

from typing import Dict, Optional, Tuple
from decimal import Decimal
from loguru import logger


class PriceValidationError(Exception):
    """價格驗證錯誤"""
    pass


class PriceValidator:
    """價格數據驗證器"""

    @staticmethod
    def validate_price_data(
        open: Optional[Decimal],
        high: Optional[Decimal],
        low: Optional[Decimal],
        close: Optional[Decimal],
        volume: Optional[int] = None,
        stock_id: Optional[str] = None,
        date: Optional[str] = None,
        allow_zero_placeholder: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        驗證價格數據的有效性

        Args:
            open: 開盤價
            high: 最高價
            low: 最低價
            close: 收盤價
            volume: 成交量（可選）
            stock_id: 股票代碼（用於日誌）
            date: 日期（用於日誌）
            allow_zero_placeholder: 是否允許全零的佔位記錄（預設 True）

        Returns:
            (is_valid, error_message) 元組
            - is_valid: True 表示有效，False 表示無效
            - error_message: 錯誤訊息（有效時為 None）

        驗證規則（與資料庫 CHECK 約束一致）：
        1. high >= low（最高價必須 >= 最低價）
        2. low <= close <= high（收盤價必須在最低和最高之間）
        3. open > 0 且 high > 0 且 low > 0 且 close > 0（必須為正數）
        4. 例外：允許全零的佔位記錄（如果 allow_zero_placeholder=True）
        """
        context = f"{stock_id} {date}" if stock_id and date else "Unknown"

        # 處理 None 值
        if open is None or high is None or low is None or close is None:
            return False, f"{context}: 價格欄位不能為 None（open={open}, high={high}, low={low}, close={close}）"

        # 轉換為 Decimal（確保精確計算）
        try:
            open = Decimal(str(open))
            high = Decimal(str(high))
            low = Decimal(str(low))
            close = Decimal(str(close))
        except (ValueError, TypeError) as e:
            return False, f"{context}: 價格格式錯誤 - {e}"

        # 檢查是否為全零佔位記錄
        is_zero_placeholder = (
            open == Decimal('0') and
            high == Decimal('0') and
            low == Decimal('0') and
            close == Decimal('0')
        )

        if is_zero_placeholder:
            if allow_zero_placeholder:
                # 全零佔位記錄是允許的（用於特殊情況）
                return True, None
            else:
                return False, f"{context}: 不允許全零的佔位記錄"

        # 驗證規則 1: 最高價必須 >= 最低價
        if high < low:
            return False, f"{context}: 最高價 ({high}) < 最低價 ({low})"

        # 驗證規則 2: 收盤價必須在最低和最高之間
        if not (low <= close <= high):
            return False, f"{context}: 收盤價 ({close}) 不在 [{low}, {high}] 範圍內"

        # 驗證規則 3: 價格必須為正數
        if open <= 0:
            return False, f"{context}: 開盤價 ({open}) 必須 > 0"
        if high <= 0:
            return False, f"{context}: 最高價 ({high}) 必須 > 0"
        if low <= 0:
            return False, f"{context}: 最低價 ({low}) 必須 > 0"
        if close <= 0:
            return False, f"{context}: 收盤價 ({close}) 必須 > 0"

        # 驗證成交量（如果提供）
        if volume is not None and volume < 0:
            return False, f"{context}: 成交量 ({volume}) 不能為負數"

        # 所有驗證通過
        return True, None

    @staticmethod
    def validate_and_log(
        open: Optional[Decimal],
        high: Optional[Decimal],
        low: Optional[Decimal],
        close: Optional[Decimal],
        volume: Optional[int] = None,
        stock_id: Optional[str] = None,
        date: Optional[str] = None,
        allow_zero_placeholder: bool = True,
        raise_on_error: bool = False
    ) -> bool:
        """
        驗證價格數據並記錄錯誤日誌

        Args:
            同 validate_price_data()
            raise_on_error: 是否在驗證失敗時拋出異常（預設 False）

        Returns:
            True 表示有效，False 表示無效

        Raises:
            PriceValidationError: 如果 raise_on_error=True 且驗證失敗
        """
        is_valid, error_msg = PriceValidator.validate_price_data(
            open, high, low, close, volume, stock_id, date, allow_zero_placeholder
        )

        if not is_valid:
            logger.warning(f"⚠️  [PRICE_VALIDATION] {error_msg}")

            if raise_on_error:
                raise PriceValidationError(error_msg)

        return is_valid

    @staticmethod
    def validate_price_dict(
        price_data: Dict,
        stock_id: Optional[str] = None,
        date: Optional[str] = None,
        allow_zero_placeholder: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        驗證價格數據字典

        Args:
            price_data: 包含 open, high, low, close, volume 的字典
            stock_id: 股票代碼（用於日誌）
            date: 日期（用於日誌）
            allow_zero_placeholder: 是否允許全零佔位記錄

        Returns:
            (is_valid, error_message) 元組
        """
        return PriceValidator.validate_price_data(
            open=price_data.get('open'),
            high=price_data.get('high'),
            low=price_data.get('low'),
            close=price_data.get('close'),
            volume=price_data.get('volume'),
            stock_id=stock_id,
            date=date,
            allow_zero_placeholder=allow_zero_placeholder
        )


# 便捷函數
def validate_price(
    open: Decimal, high: Decimal, low: Decimal, close: Decimal,
    stock_id: str = None, date: str = None
) -> bool:
    """
    快速驗證價格數據（便捷函數）

    Returns:
        True 表示有效，False 表示無效
    """
    return PriceValidator.validate_and_log(
        open, high, low, close,
        stock_id=stock_id,
        date=date,
        raise_on_error=False
    )
