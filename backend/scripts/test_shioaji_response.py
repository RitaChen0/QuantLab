#!/usr/bin/env python3
"""
测试 Shioaji API 的详细返回内容

用于诊断为什么 API 返回 0 笔数据
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.shioaji_client import ShioajiClient
from datetime import datetime, timedelta
from app.utils.timezone_helpers import today_taiwan
import json

def test_shioaji_api():
    """测试 Shioaji API 返回的详细内容"""

    print("\n" + "="*60)
    print("🔍 Shioaji API 响应诊断工具")
    print("="*60)

    # 测试参数
    stock_id = "2330"

    # 测试不同的日期范围
    test_cases = [
        {
            "name": "今天（可能无数据）",
            "start": datetime.now().replace(hour=9, minute=0, second=0),
            "end": datetime.now().replace(hour=13, minute=30, second=0),
        },
        {
            "name": "昨天（12/24）",
            "start": datetime(2025, 12, 24, 9, 0, 0),
            "end": datetime(2025, 12, 24, 13, 30, 0),
        },
        {
            "name": "12/23（周二）",
            "start": datetime(2025, 12, 23, 9, 0, 0),
            "end": datetime(2025, 12, 23, 13, 30, 0),
        },
        {
            "name": "12/18（已知有数据）",
            "start": datetime(2025, 12, 18, 9, 0, 0),
            "end": datetime(2025, 12, 18, 13, 30, 0),
        },
    ]

    with ShioajiClient() as client:
        if not client.is_available():
            print("❌ Shioaji 客户端初始化失败")
            return

        print(f"\n✅ Shioaji 客户端已连接")
        print(f"📊 测试股票: {stock_id} (台积电)")
        print("\n" + "-"*60)

        for i, case in enumerate(test_cases, 1):
            print(f"\n📋 测试 {i}/{len(test_cases)}: {case['name']}")
            print(f"   时间范围: {case['start'].strftime('%Y-%m-%d %H:%M')} ~ {case['end'].strftime('%Y-%m-%d %H:%M')}")

            try:
                # 获取合约
                contract = client.get_contract(stock_id)
                if not contract:
                    print(f"   ❌ 无法获取合约")
                    continue

                print(f"   ✅ 合约: {contract}")

                # 调用 API
                print(f"   🔄 正在调用 Shioaji API...")
                kbars = client._api.kbars(
                    contract=contract,
                    start=case['start'].strftime('%Y-%m-%d'),
                    end=case['end'].strftime('%Y-%m-%d'),
                    timeout=30000
                )

                # 详细检查返回对象
                print(f"\n   📦 API 返回对象类型: {type(kbars)}")
                print(f"   📦 返回对象: {kbars}")

                if kbars:
                    print(f"   📦 对象属性:")
                    for attr in dir(kbars):
                        if not attr.startswith('_'):
                            try:
                                value = getattr(kbars, attr)
                                if not callable(value):
                                    print(f"      - {attr}: {value}")
                            except:
                                pass

                    # 检查时间戳列表
                    if hasattr(kbars, 'ts'):
                        print(f"\n   📊 时间戳数量: {len(kbars.ts)}")
                        if len(kbars.ts) > 0:
                            print(f"   📊 第一笔时间: {kbars.ts[0]}")
                            print(f"   📊 最后一笔时间: {kbars.ts[-1]}")
                            print(f"   📊 第一笔数据: O:{kbars.Open[0]}, H:{kbars.High[0]}, L:{kbars.Low[0]}, C:{kbars.Close[0]}, V:{kbars.Volume[0]}")
                        else:
                            print(f"   ⚠️  时间戳列表为空（0 笔数据）")
                    else:
                        print(f"   ⚠️  返回对象没有 'ts' 属性")
                else:
                    print(f"   ❌ API 返回 None")

            except Exception as e:
                print(f"   ❌ 错误: {str(e)}")
                import traceback
                traceback.print_exc()

            print("-"*60)

        print("\n" + "="*60)
        print("✅ 诊断完成")
        print("="*60)

if __name__ == "__main__":
    test_shioaji_api()
