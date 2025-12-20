#!/usr/bin/env python3
"""
自動修復 datetime.now() 和 datetime.utcnow() 缺少時區的問題

此腳本會:
1. 檢查所有 Python 文件中的 datetime.now() 和 datetime.utcnow()
2. 替換為 datetime.now(timezone.utc)
3. 確保有正確的 import 語句
4. 生成報告顯示修改內容

使用方法:
    python scripts/fix_datetime_timezone.py --dry-run  # 預覽修改
    python scripts/fix_datetime_timezone.py            # 實際修改
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple
import argparse


def find_python_files(base_dir: Path) -> List[Path]:
    """找出所有需要檢查的 Python 文件"""
    # 排除這些目錄
    exclude_dirs = {
        'venv', '.venv', 'env', '__pycache__', '.git',
        'node_modules', 'alembic/versions'  # 不修改舊的遷移文件
    }

    python_files = []
    for py_file in base_dir.rglob('*.py'):
        # 檢查是否在排除目錄中
        if any(excluded in py_file.parts for excluded in exclude_dirs):
            continue
        python_files.append(py_file)

    return python_files


def check_and_fix_file(file_path: Path, dry_run: bool = True) -> Tuple[bool, List[str]]:
    """
    檢查並修復單個文件

    Returns:
        (是否需要修改, 修改說明列表)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, [f"❌ 無法讀取: {e}"]

    original_content = content
    changes = []

    # 1. 檢查是否有 datetime import
    has_datetime_import = re.search(
        r'from datetime import.*datetime',
        content
    ) or re.search(
        r'import datetime',
        content
    )

    # 2. 檢查並替換 datetime.now()
    # 匹配 datetime.now() 但不匹配 datetime.now(timezone.utc) 或 datetime.now(pytz.timezone(...))
    pattern_now = r'\bdatetime\.now\(\)(?!\s*[,)])'

    matches_now = list(re.finditer(pattern_now, content))
    if matches_now:
        content = re.sub(pattern_now, 'datetime.now(timezone.utc)', content)
        changes.append(f"  ✅ 修復 {len(matches_now)} 處 datetime.now() -> datetime.now(timezone.utc)")

    # 3. 檢查並替換 datetime.utcnow()
    pattern_utcnow = r'\bdatetime\.utcnow\(\)'

    matches_utcnow = list(re.finditer(pattern_utcnow, content))
    if matches_utcnow:
        content = re.sub(pattern_utcnow, 'datetime.now(timezone.utc)', content)
        changes.append(f"  ✅ 修復 {len(matches_utcnow)} 處 datetime.utcnow() -> datetime.now(timezone.utc)")

    # 4. 如果有修改，確保有正確的 import
    if changes:
        # 檢查是否需要添加 timezone import
        needs_timezone = 'timezone.utc' in content

        if needs_timezone:
            # 情況 1: 已有 from datetime import ...
            if re.search(r'from datetime import', content):
                # 檢查是否已 import timezone
                if not re.search(r'from datetime import.*timezone', content):
                    # 在現有 import 中添加 timezone
                    content = re.sub(
                        r'(from datetime import [^;\n]+)',
                        lambda m: m.group(1) + ', timezone' if 'timezone' not in m.group(1) else m.group(1),
                        content,
                        count=1
                    )
                    changes.append(f"  ✅ 添加 timezone 到 import 語句")

            # 情況 2: 只有 import datetime
            elif re.search(r'^import datetime$', content, re.MULTILINE):
                # 保持 import datetime，datetime.now(timezone.utc) 會變成 datetime.now(datetime.timezone.utc)
                # 需要手動調整或改用 from datetime import
                changes.append(f"  ⚠️  需手動檢查: 使用 import datetime，建議改為 from datetime import datetime, timezone")

            # 情況 3: 沒有 datetime import (unlikely)
            else:
                # 在文件開頭添加
                import_line = "from datetime import datetime, timezone\n"
                content = import_line + content
                changes.append(f"  ✅ 添加 from datetime import datetime, timezone")

    # 5. 寫回文件
    if changes and not dry_run:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            changes.append(f"  ❌ 寫入失敗: {e}")
            return False, changes

    return bool(changes), changes


def main():
    parser = argparse.ArgumentParser(description='修復 Python 代碼中的時區問題')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='預覽模式，不實際修改文件'
    )
    parser.add_argument(
        '--base-dir',
        type=str,
        default='/home/ubuntu/QuantLab/backend/app',
        help='要掃描的基礎目錄'
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    if not base_dir.exists():
        print(f"❌ 目錄不存在: {base_dir}")
        sys.exit(1)

    print(f"{'='*80}")
    print(f"時區修復工具")
    print(f"{'='*80}")
    print(f"模式: {'🔍 預覽模式 (不會修改文件)' if args.dry_run else '✏️  修改模式'}")
    print(f"掃描目錄: {base_dir}")
    print(f"{'='*80}\n")

    # 找出所有 Python 文件
    python_files = find_python_files(base_dir)
    print(f"找到 {len(python_files)} 個 Python 文件\n")

    # 統計
    total_files = 0
    modified_files = 0
    total_changes = 0

    # 處理每個文件
    for py_file in python_files:
        total_files += 1
        needs_fix, changes = check_and_fix_file(py_file, dry_run=args.dry_run)

        if needs_fix:
            modified_files += 1
            total_changes += len([c for c in changes if c.startswith('  ✅')])

            print(f"📝 {py_file.relative_to(base_dir)}")
            for change in changes:
                print(change)
            print()

    # 總結
    print(f"{'='*80}")
    print(f"總結")
    print(f"{'='*80}")
    print(f"掃描文件: {total_files}")
    print(f"需修改文件: {modified_files}")
    print(f"修改項目: {total_changes}")

    if args.dry_run and modified_files > 0:
        print(f"\n💡 這是預覽模式，未實際修改文件。")
        print(f"   若要執行修改，請運行: python {sys.argv[0]} --base-dir {base_dir}")
    elif modified_files > 0:
        print(f"\n✅ 修改完成！建議執行以下檢查:")
        print(f"   1. git diff 查看變更")
        print(f"   2. pytest 執行測試")
        print(f"   3. flake8 檢查語法")
    else:
        print(f"\n✨ 沒有發現需要修改的文件，代碼已符合時區規範！")

    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
