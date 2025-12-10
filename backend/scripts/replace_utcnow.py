#!/usr/bin/env python3
"""
替換已棄用的 datetime.utcnow() 為 datetime.now(timezone.utc)

Python 3.12+ 已棄用 datetime.utcnow()，需要使用時區感知的替代方案。
"""

import re
from pathlib import Path
from typing import List, Tuple

# 需要修復的檔案列表
FILES_TO_FIX = [
    "backend/app/repositories/backtest.py",
    "backend/app/api/v1/admin.py",
    "backend/app/repositories/industry_chain.py",
    "backend/app/tasks/fundamental_sync.py",
    "backend/app/api/v1/backtest.py",
    "backend/app/tasks/stock_data.py",
    "backend/app/core/security.py",
    "backend/app/repositories/user.py",
]

PATTERN = r'datetime\.utcnow\(\)'
REPLACEMENT = 'datetime.now(timezone.utc)'


def fix_imports(content: str) -> str:
    """
    修復 import 語句，確保包含 timezone

    Args:
        content: 檔案內容

    Returns:
        修復後的內容
    """
    # 檢查是否已經有 timezone import
    if 'timezone' in content:
        return content

    # 找到 datetime import 並加入 timezone
    # 匹配各種 import 格式
    patterns = [
        (r'from datetime import datetime\b(?!.*timezone)', 'from datetime import datetime, timezone'),
        (r'import datetime\b', 'import datetime\nfrom datetime import timezone'),
    ]

    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content, count=1)
            break

    return content


def replace_utcnow(file_path: Path) -> Tuple[bool, int, str]:
    """
    替換檔案中的 datetime.utcnow()

    Args:
        file_path: 檔案路徑

    Returns:
        (是否有變更, 替換次數, 錯誤訊息)
    """
    try:
        # 讀取檔案
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # 計算替換次數
        matches = re.findall(PATTERN, content)
        count = len(matches)

        if count == 0:
            return False, 0, ""

        # 修復 imports
        content = fix_imports(content)

        # 替換 utcnow()
        content = re.sub(PATTERN, REPLACEMENT, content)

        # 寫回檔案
        file_path.write_text(content, encoding='utf-8')

        # 驗證是否真的有變更
        changed = content != original_content

        return changed, count, ""

    except Exception as e:
        return False, 0, str(e)


def main():
    """主函數"""
    print("🔄 開始替換已棄用的 datetime.utcnow()")
    print("=" * 60)

    total_files = 0
    total_replacements = 0
    errors: List[str] = []

    for file_path_str in FILES_TO_FIX:
        file_path = Path(file_path_str)

        if not file_path.exists():
            # 嘗試從專案根目錄尋找
            file_path = Path("/data/CCTest/QuantLab") / file_path_str

        if not file_path.exists():
            errors.append(f"❌ 找不到檔案: {file_path_str}")
            continue

        changed, count, error = replace_utcnow(file_path)

        if error:
            errors.append(f"❌ 處理 {file_path_str} 時發生錯誤: {error}")
        elif changed:
            print(f"✅ {file_path_str}: 替換 {count} 次")
            total_files += 1
            total_replacements += count
        else:
            print(f"⏭️  {file_path_str}: 無需替換")

    print("=" * 60)
    print(f"\n📊 總結：")
    print(f"  修改檔案數: {total_files}")
    print(f"  總替換次數: {total_replacements}")

    if errors:
        print(f"\n⚠️  錯誤：")
        for error in errors:
            print(f"  {error}")
        return 1

    print("\n✨ 完成！所有檔案已更新為使用 datetime.now(timezone.utc)")
    return 0


if __name__ == "__main__":
    exit(main())
