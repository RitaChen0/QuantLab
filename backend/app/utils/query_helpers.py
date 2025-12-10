"""
查詢輔助工具函數
"""


def escape_like_pattern(pattern: str, escape_char: str = '\\') -> str:
    """
    轉義 SQL LIKE 模式中的特殊字符

    Args:
        pattern: 原始搜尋關鍵字
        escape_char: 轉義字符（默認為反斜線）

    Returns:
        轉義後的安全模式

    Examples:
        >>> escape_like_pattern("test_user")
        'test\\_user'

        >>> escape_like_pattern("50%")
        '50\\%'

        >>> escape_like_pattern("test\\data")
        'test\\\\data'
    """
    # 首先轉義轉義字符本身
    safe_pattern = pattern.replace(escape_char, escape_char + escape_char)

    # 轉義 SQL LIKE 萬用字元
    safe_pattern = safe_pattern.replace('%', escape_char + '%')
    safe_pattern = safe_pattern.replace('_', escape_char + '_')

    return safe_pattern
