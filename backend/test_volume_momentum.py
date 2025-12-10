"""
VolumeWeightedMomentum10Days - Qlib 策略（修復版）
成交量加權動量因子：計算過去 10 天的成交量加權平均價格，並與 10 天前的價格比較

修復內容：
1. 將 LaTeX 公式改為有效的 Qlib 表達式語法
2. 使用正確的 Qlib 運算符：Sum(), Ref(), Mean()
3. 保留原始信號生成邏輯
"""

import pandas as pd
import numpy as np
from qlib.data import D

# Qlib 表達式字段（修復版）
QLIB_FIELDS = [
    # 成交量加權動量：(10日VWAP - 10日前收盤價)
    '(Sum($close*$volume, 10) / Sum($volume, 10)) - Ref($close, 10)',  # VolumeWeightedMomentum10Days
]

def generate_signals(stock_id: str, start_date: str, end_date: str):
    """
    生成交易信號

    Parameters:
    -----------
    stock_id : str
        股票代碼
    start_date : str
        開始日期 (格式: 'YYYY-MM-DD')
    end_date : str
        結束日期 (格式: 'YYYY-MM-DD')

    Returns:
    --------
    pd.DataFrame
        包含因子值和交易信號的 DataFrame
    """
    try:
        # 使用 Qlib 的 D.features() 獲取數據
        df = D.features(
            instruments=[stock_id],
            fields=QLIB_FIELDS,
            start_time=start_date,
            end_time=end_date
        )

        if df is None or df.empty:
            print(f"⚠️  警告：股票 {stock_id} 在 {start_date} 至 {end_date} 期間無數據")
            return pd.DataFrame()

        # 重命名因子列
        df.columns = ['volumeweightedmomentum10days']

        # 移除 NaN 值（前 10 天會是 NaN）
        df = df.dropna()

        if df.empty:
            print(f"⚠️  警告：股票 {stock_id} 移除 NaN 後無有效數據")
            return pd.DataFrame()

        # 生成交易信號（基於因子值的分位數）
        df['signal'] = 0
        threshold_high = df['volumeweightedmomentum10days'].quantile(0.7)  # 買入閾值（70%）
        threshold_low = df['volumeweightedmomentum10days'].quantile(0.3)   # 賣出閾值（30%）

        # 買入信號：動量值 > 70 分位數（強勢上漲）
        df.loc[df['volumeweightedmomentum10days'] > threshold_high, 'signal'] = 1

        # 賣出信號：動量值 < 30 分位數（弱勢下跌）
        df.loc[df['volumeweightedmomentum10days'] < threshold_low, 'signal'] = -1

        # 統計信號數量
        buy_signals = (df['signal'] == 1).sum()
        sell_signals = (df['signal'] == -1).sum()
        print(f"✅ 股票 {stock_id}：買入信號 {buy_signals} 個，賣出信號 {sell_signals} 個")

        return df

    except Exception as e:
        print(f"❌ 錯誤：生成信號時發生異常 - {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

# 策略參數
STRATEGY_CONFIG = {
    'factor_name': 'VolumeWeightedMomentum10Days',
    'formula': '(Sum($close*$volume, 10) / Sum($volume, 10)) - Ref($close, 10)',
    'signal_method': 'quantile',
    'buy_threshold': 0.7,
    'sell_threshold': 0.3,
    'description': '成交量加權動量策略：計算 10 日 VWAP 與 10 日前價格的差值，作為趨勢強度指標'
}

# 測試函數
if __name__ == '__main__':
    # 初始化 Qlib
    import qlib
    from pathlib import Path

    qlib_data_path = Path("/data/qlib/tw_stock_v2")
    if not qlib_data_path.exists():
        print(f"❌ 錯誤：Qlib 數據路徑不存在 - {qlib_data_path}")
        exit(1)

    print("🔧 初始化 Qlib...")
    qlib.init(provider_uri=str(qlib_data_path), region="cn")
    print("✅ Qlib 初始化完成\n")

    # 測試用例
    test_stock = '2330'  # 台積電
    test_start = '2024-01-01'
    test_end = '2024-12-31'

    print(f"開始測試策略：{STRATEGY_CONFIG['factor_name']}")
    print(f"測試股票：{test_stock}")
    print(f"測試期間：{test_start} 至 {test_end}")
    print("=" * 60)

    signals = generate_signals(test_stock, test_start, test_end)

    if not signals.empty:
        print("\n📊 信號統計：")
        print(signals['signal'].value_counts().sort_index())
        print("\n📈 因子值統計：")
        print(signals['volumeweightedmomentum10days'].describe())
    else:
        print("\n⚠️  測試失敗：未生成任何信號")
