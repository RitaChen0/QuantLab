"""
會員等級與 Rate Limit 配置

根據會員等級提供不同的 API 使用限制。
所有限制均為固定值，不使用倍數系統。
"""

from typing import Dict
from loguru import logger


# 會員等級定義
MEMBER_LEVELS = {
    0: "註冊會員",
    1: "普通會員",
    2: "中階會員",
    3: "高階會員",
    4: "VIP會員",
    5: "系統推廣會員",
    6: "系統管理員1",
    7: "系統管理員2",
    8: "系統管理員3",
    9: "創造者等級",
}

# 最低等級和最高等級
MIN_LEVEL = 0
MAX_LEVEL = 9


class MemberRateLimits:
    """會員等級 Rate Limit 固定值配置"""

    # 回測執行限制 (per hour)
    BACKTEST_LIMITS: Dict[int, str] = {
        0: "10/hour",
        1: "20/hour",
        2: "30/hour",
        3: "40/hour",
        4: "50/hour",
        5: "60/hour",
        6: "70/hour",
        7: "3000/hour",
        8: "3000/hour",
        9: "3000/hour",
    }

    # 策略建立限制 (per hour)
    STRATEGY_CREATE_LIMITS: Dict[int, str] = {
        0: "10/hour",
        1: "20/hour",
        2: "30/hour",
        3: "40/hour",
        4: "50/hour",
        5: "60/hour",
        6: "70/hour",
        7: "3000/hour",
        8: "3000/hour",
        9: "3000/hour",
    }

    # 資料查詢限制 (per minute)
    DATA_QUERY_LIMITS: Dict[int, str] = {
        0: "100/minute",
        1: "200/minute",
        2: "300/minute",
        3: "400/minute",
        4: "500/minute",
        5: "600/minute",
        6: "700/minute",
        7: "3000/minute",
        8: "3000/minute",
        9: "3000/minute",
    }

    # 因子挖掘限制 (per hour)
    FACTOR_MINING_LIMITS: Dict[int, str] = {
        0: "0/hour",
        1: "0/hour",
        2: "0/hour",
        3: "1/hour",
        4: "2/hour",
        5: "3/hour",
        6: "6/hour",
        7: "3000/hour",
        8: "3000/hour",
        9: "3000/hour",
    }

    @classmethod
    def _get_limit_with_fallback(cls, limits_dict: Dict[int, str], user_level: int, limit_name: str) -> str:
        """
        獲取限制值，如果等級不存在則降級處理

        Args:
            limits_dict: 限制字典
            user_level: 用戶等級
            limit_name: 限制名稱（用於日誌）

        Returns:
            限制字串
        """
        # 確保等級在有效範圍內
        if user_level < MIN_LEVEL:
            logger.warning(f"User level {user_level} below minimum, using level {MIN_LEVEL}")
            user_level = MIN_LEVEL
        elif user_level > MAX_LEVEL:
            logger.warning(f"User level {user_level} above maximum, using level {MAX_LEVEL}")
            user_level = MAX_LEVEL

        # 直接返回對應等級的限制
        if user_level in limits_dict:
            return limits_dict[user_level]

        # 降級處理：找到最接近且不超過的等級
        valid_levels = sorted(limits_dict.keys())
        for level in reversed(valid_levels):
            if user_level >= level:
                logger.warning(
                    f"Unknown level {user_level} for {limit_name}, using level {level}"
                )
                return limits_dict[level]

        # 如果都不匹配，使用最低等級
        return limits_dict[MIN_LEVEL]


def get_level_name(member_level: int) -> str:
    """
    獲取會員等級名稱

    Args:
        member_level: 會員等級 (0-9)

    Returns:
        等級名稱字串
    """
    if member_level in MEMBER_LEVELS:
        return MEMBER_LEVELS[member_level]

    return f"未知等級 ({member_level})"


def get_backtest_limit(user_level: int = 0) -> str:
    """
    獲取回測執行的 Rate Limit

    Args:
        user_level: 用戶等級 (0-9)

    Returns:
        限制字串 (例如: "10/hour")
    """
    return MemberRateLimits._get_limit_with_fallback(
        MemberRateLimits.BACKTEST_LIMITS,
        user_level,
        "backtest"
    )


def get_strategy_create_limit(user_level: int = 0) -> str:
    """
    獲取策略建立的 Rate Limit

    Args:
        user_level: 用戶等級 (0-9)

    Returns:
        限制字串 (例如: "10/hour")
    """
    return MemberRateLimits._get_limit_with_fallback(
        MemberRateLimits.STRATEGY_CREATE_LIMITS,
        user_level,
        "strategy_create"
    )


def get_data_query_limit(user_level: int = 0) -> str:
    """
    獲取資料查詢的 Rate Limit

    Args:
        user_level: 用戶等級 (0-9)

    Returns:
        限制字串 (例如: "100/minute")
    """
    return MemberRateLimits._get_limit_with_fallback(
        MemberRateLimits.DATA_QUERY_LIMITS,
        user_level,
        "data_query"
    )


def get_factor_mining_limit(user_level: int = 0) -> str:
    """
    獲取因子挖掘的 Rate Limit

    因子挖掘限制：
    - Level 0-2: 0/hour（不可使用）
    - Level 3: 1/hour
    - Level 4: 2/hour
    - Level 5: 3/hour
    - Level 6: 6/hour
    - Level 7-9: 3000/hour（管理員/創造者）

    Args:
        user_level: 用戶等級 (0-9)

    Returns:
        限制字串 (例如: "0/hour")
    """
    return MemberRateLimits._get_limit_with_fallback(
        MemberRateLimits.FACTOR_MINING_LIMITS,
        user_level,
        "factor_mining"
    )


def get_all_limits(user_level: int = 0) -> Dict[str, str]:
    """
    獲取用戶的所有 Rate Limit

    Args:
        user_level: 用戶等級 (0-9)

    Returns:
        包含所有限制的字典
    """
    return {
        "回測執行": get_backtest_limit(user_level),
        "策略建立": get_strategy_create_limit(user_level),
        "資料查詢": get_data_query_limit(user_level),
        "因子挖掘": get_factor_mining_limit(user_level),
    }


def is_level_valid(member_level: int) -> bool:
    """
    檢查會員等級是否有效

    Args:
        member_level: 會員等級

    Returns:
        是否為有效等級
    """
    return MIN_LEVEL <= member_level <= MAX_LEVEL


def get_level_color(member_level: int) -> str:
    """
    獲取會員等級對應的顏色代碼（用於前端顯示）

    Args:
        member_level: 會員等級 (0-9)

    Returns:
        顏色代碼
    """
    color_map = {
        0: "#9ca3af",  # 灰色 - 註冊會員
        1: "#60a5fa",  # 淺藍 - 普通會員
        2: "#34d399",  # 綠色 - 中階會員
        3: "#fbbf24",  # 金色 - 高階會員
        4: "#f59e0b",  # 橙色 - VIP會員
        5: "#ec4899",  # 粉紅 - 系統推廣會員
        6: "#8b5cf6",  # 紫色 - 系統管理員1
        7: "#6366f1",  # 靛色 - 系統管理員2
        8: "#3b82f6",  # 藍色 - 系統管理員3
        9: "#ef4444",  # 紅色 - 創造者等級
    }
    return color_map.get(member_level, "#9ca3af")
