#!/usr/bin/env python3
"""
RD-Agent 最小化測試腳本
用途：診斷 RD-Agent 執行時的具體錯誤
"""

import os
import sys
import traceback

# 設定環境變數
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
os.environ["QLIB_DATA_PATH"] = os.getenv("QLIB_DATA_PATH", "/data/qlib/tw_stock_v2")

print("=" * 80)
print("RD-Agent 最小化測試")
print("=" * 80)
print()

# 檢查環境變數
print("環境變數檢查:")
print(f"  OPENAI_API_KEY: {'✓ 已設定' if os.environ.get('OPENAI_API_KEY') else '✗ 未設定'}")
print(f"  QLIB_DATA_PATH: {os.environ.get('QLIB_DATA_PATH')}")
print()

# 檢查 RD-Agent 導入
print("檢查 RD-Agent 導入...")
try:
    from rdagent.app.qlib_rd_loop.factor import main
    print("  ✓ RD-Agent 導入成功")
except Exception as e:
    print(f"  ✗ RD-Agent 導入失敗: {e}")
    traceback.print_exc()
    sys.exit(1)

# 檢查 Qlib 數據
print()
print("檢查 Qlib 數據路徑...")
qlib_path = os.environ.get("QLIB_DATA_PATH")
if os.path.exists(qlib_path):
    print(f"  ✓ Qlib 數據目錄存在: {qlib_path}")
    # 列出一些檔案
    try:
        import os
        features_dir = os.path.join(qlib_path, "features")
        if os.path.exists(features_dir):
            stocks = os.listdir(features_dir)[:5]
            print(f"  ✓ 找到 {len(os.listdir(features_dir))} 個股票數據")
            print(f"  範例: {stocks}")
        else:
            print(f"  ⚠ features 目錄不存在: {features_dir}")
    except Exception as e:
        print(f"  ⚠ 無法列出數據目錄: {e}")
else:
    print(f"  ✗ Qlib 數據目錄不存在: {qlib_path}")

# 嘗試執行 RD-Agent（1 次迭代）
print()
print("=" * 80)
print("開始執行 RD-Agent (1 次迭代)...")
print("=" * 80)
print()

try:
    main(step_n=1)
    print()
    print("=" * 80)
    print("✓ RD-Agent 執行成功！")
    print("=" * 80)
except Exception as e:
    print()
    print("=" * 80)
    print(f"✗ RD-Agent 執行失敗: {e}")
    print("=" * 80)
    print()
    print("完整錯誤追蹤:")
    traceback.print_exc()
    sys.exit(1)
