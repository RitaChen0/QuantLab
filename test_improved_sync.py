#!/usr/bin/env python3
"""测试改进后的 save_to_postgresql 方法"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# 添加专案路径
sys.path.insert(0, '/home/ubuntu/QuantLab/backend')

from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 创建测试数据
def create_test_data(num_records=1000):
    """创建测试数据（包含 NaN 值）"""
    base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    data = {
        'datetime': [base_time + timedelta(minutes=i) for i in range(num_records)],
        'open': np.random.uniform(100, 200, num_records),
        'high': np.random.uniform(100, 200, num_records),
        'low': np.random.uniform(100, 200, num_records),
        'close': np.random.uniform(100, 200, num_records),
        'volume': np.random.randint(0, 10000, num_records, dtype=float)
    }

    df = pd.DataFrame(data)

    # 插入一些 NaN 值（模拟无交易的分钟）
    nan_indices = np.random.choice(num_records, size=int(num_records * 0.1), replace=False)
    df.loc[nan_indices, 'volume'] = np.nan

    return df

# 测试向量化 vs iterrows 性能
def test_performance():
    import time

    df = create_test_data(10000)
    stock_id = 'TEST'

    print("=" * 60)
    print("性能测试：向量化 vs iterrows")
    print("=" * 60)

    # 方法 1: iterrows（旧方法）
    start = time.time()
    records_old = []
    for _, row in df.iterrows():
        records_old.append({
            'stock_id': stock_id,
            'datetime': row['datetime'],
            'timeframe': '1min',
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': int(row['volume']) if pd.notna(row['volume']) else 0
        })
    time_old = time.time() - start

    # 方法 2: 向量化（新方法）
    start = time.time()
    df_copy = df.copy()
    df_copy['stock_id'] = stock_id
    df_copy['timeframe'] = '1min'
    df_copy['open'] = df_copy['open'].astype(float)
    df_copy['high'] = df_copy['high'].astype(float)
    df_copy['low'] = df_copy['low'].astype(float)
    df_copy['close'] = df_copy['close'].astype(float)
    df_copy['volume'] = df_copy['volume'].fillna(0).astype(int)
    records_new = df_copy[['stock_id', 'datetime', 'timeframe', 'open', 'high', 'low', 'close', 'volume']].to_dict('records')
    time_new = time.time() - start

    print(f"iterrows 方法：{time_old:.4f} 秒")
    print(f"向量化方法：{time_new:.4f} 秒")
    print(f"性能提升：{time_old / time_new:.2f} 倍")
    print(f"记录数：{len(records_new)}")
    print(f"NaN 处理正确：{all(r['volume'] >= 0 for r in records_new)}")
    print("=" * 60)

if __name__ == '__main__':
    test_performance()
