#!/usr/bin/env python3
"""檢查 RD-Agent 因子解析"""
import pickle
import re
from pathlib import Path

log_dir = Path("/app/log/2025-12-07_05-27-41-959658")

# 查找所有 experiment generation pickle 檔案
exp_files = sorted(log_dir.glob("Loop_*/direct_exp_gen/r/experiment generation/**/*.pkl"))

print(f"找到 {len(exp_files)} 個 experiment pickle 檔案\n")

all_factors = []

for exp_file in exp_files:
    print(f"=== 檔案: {exp_file.name} ===")
    try:
        with open(exp_file, "rb") as f:
            data = pickle.load(f)

        print(f"資料類型: {type(data)}")

        if isinstance(data, list):
            print(f"包含 {len(data)} 個項目")
            for i, item in enumerate(data):
                print(f"  項目 {i+1}: {type(item).__name__}")

                # 提取因子名稱
                factor_name = getattr(item, 'factor_name', None) or str(item)
                if '<' in factor_name and '[' in factor_name:
                    match = re.search(r'\[(.+?)\]', factor_name)
                    if match:
                        factor_name = match.group(1)

                print(f"    因子名稱: {factor_name}")
                all_factors.append(factor_name)
        else:
            print(f"  項目: {data}")

    except Exception as e:
        print(f"  錯誤: {e}")

    print()

print(f"\n總共解析到 {len(all_factors)} 個因子:")
for i, name in enumerate(all_factors, 1):
    print(f"  {i}. {name}")
