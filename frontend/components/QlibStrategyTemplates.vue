<template>
  <div class="templates-container">
    <h3 class="templates-title">Qlib 量化策略範本</h3>
    <p class="templates-subtitle">使用 Microsoft Qlib 表達式引擎和機器學習模型</p>

    <div class="templates-grid">
      <div
        v-for="template in templates"
        :key="template.id"
        class="template-card"
      >
        <div class="template-header">
          <span class="template-icon">{{ template.icon }}</span>
          <h4 class="template-name">{{ template.name }}</h4>
        </div>
        <p class="template-description">{{ template.description }}</p>
        <div class="template-tags">
          <span
            v-for="tag in template.tags"
            :key="tag"
            class="tag"
          >
            {{ tag }}
          </span>
        </div>
        <div class="template-actions">
          <button
            type="button"
            class="btn-insert btn-replace"
            @click.stop="selectTemplate(template, 'replace')"
            title="完全替換編輯器中的代碼"
          >
            🔄 替換策略
          </button>
          <button
            type="button"
            class="btn-insert btn-factor"
            @click.stop="selectTemplate(template, 'factor')"
            title="只插入因子計算邏輯"
          >
            ⭐ 插入因子
          </button>
          <button
            type="button"
            class="btn-insert btn-append"
            @click.stop="selectTemplate(template, 'append')"
            title="追加到現有代碼末尾"
          >
            ➕ 追加代碼
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const emit = defineEmits(['select'])

const templates = [
  {
    id: 'qlib_ma_cross',
    name: '均線交叉策略（Qlib 表達式）',
    description: '使用 Qlib 表達式計算均線，當短期均線上穿長期均線時買入',
    icon: '📊',
    tags: ['Qlib 表達式', '均線', '入門'],
    code: `# Qlib 均線交叉策略
# 使用 Qlib 的 D.features() API 計算均線

from qlib.data import D
import pandas as pd

# 定義 Qlib 表達式字段
QLIB_FIELDS = [
    '$close',
    'Mean($close, 5)',   # 5 日均線（Qlib 表達式）
    'Mean($close, 20)',  # 20 日均線（Qlib 表達式）
]

# 注意：df 會包含這些 Qlib 計算的字段
# 欄位名稱: '$close', 'Mean($close, 5)', 'Mean($close, 20)'

# 計算均線交叉信號
ma5 = df['Mean($close, 5)']
ma20 = df['Mean($close, 20)']

# 初始化信號
signals = pd.Series(0, index=df.index)

# 黃金交叉：短期均線上穿長期均線
signals[(ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))] = 1

# 死亡交叉：短期均線下穿長期均線
signals[(ma5 < ma20) & (ma5.shift(1) >= ma20.shift(1))] = -1

print(f"生成了 {len(signals[signals != 0])} 個交易信號")

# 策略參數設定
# {
#   "use_qlib_expressions": true,
#   "qlib_fields": ["$close", "Mean($close, 5)", "Mean($close, 20)"]
# }
`,
  },
  {
    id: 'qlib_momentum',
    name: '動量因子策略（Qlib 表達式）',
    description: '使用 Qlib 表達式計算多周期動量，結合波動率過濾',
    icon: '🚀',
    tags: ['Qlib 表達式', '動量', '中等'],
    code: `# Qlib 動量因子策略
# 使用 Qlib 表達式計算動量和波動率

from qlib.data import D
import pandas as pd
import numpy as np

# 定義 Qlib 表達式字段
QLIB_FIELDS = [
    '$close',
    '$volume',
    'Ref($close, 5) / $close - 1',    # 5 日動量（Qlib 表達式）
    'Ref($close, 10) / $close - 1',   # 10 日動量
    'Ref($close, 20) / $close - 1',   # 20 日動量
    'Std($close, 20)',                 # 20 日波動率
    'Mean($volume, 20)',               # 20 日平均成交量
]

# 計算動量評分
momentum_5 = df['Ref($close, 5) / $close - 1']
momentum_10 = df['Ref($close, 10) / $close - 1']
momentum_20 = df['Ref($close, 20) / $close - 1']

# 加權平均動量
momentum_score = (
    momentum_5 * 0.5 +
    momentum_10 * 0.3 +
    momentum_20 * 0.2
)

# 成交量確認
volume_ratio = df['$volume'] / df['Mean($volume, 20)']
volatility = df['Std($close, 20)']

# 綜合因子（動量 * 成交量 / 波動率）
factor = momentum_score * np.log1p(volume_ratio) / (volatility + 1e-6)

# 生成信號
signals = pd.Series(0, index=df.index)

# 買入：因子分數在前 20%
buy_threshold = factor.quantile(0.8)
signals[factor >= buy_threshold] = 1

# 賣出：因子分數在後 20%
sell_threshold = factor.quantile(0.2)
signals[factor <= sell_threshold] = -1

print(f"動量策略：買入 {(signals == 1).sum()} 次，賣出 {(signals == -1).sum()} 次")

# 策略參數設定
# {
#   "use_qlib_expressions": true,
#   "qlib_fields": ["$close", "$volume", "Ref($close, 5) / $close - 1", ...]
# }
`,
  },
  {
    id: 'qlib_volatility',
    name: '波動率突破策略（Qlib 表達式）',
    description: '使用 Qlib 表達式計算布林通道和 ATR，捕捉突破機會',
    icon: '⚡',
    tags: ['Qlib 表達式', '波動率', '進階'],
    code: `# Qlib 波動率突破策略
# 使用 Qlib 表達式計算布林通道

from qlib.data import D
import pandas as pd

# 定義 Qlib 表達式字段
QLIB_FIELDS = [
    '$close', '$high', '$low',
    'Mean($close, 20)',                    # 20 日均線
    'Std($close, 20)',                     # 20 日標準差
    'Max($high, 14) - Min($low, 14)',     # ATR 近似值
]

# 計算布林通道
ma20 = df['Mean($close, 20)']
std20 = df['Std($close, 20)']

upper_band = ma20 + 2 * std20
lower_band = ma20 - 2 * std20

# 波動率狀態
volatility_ratio = std20 / df['$close']
median_vol = volatility_ratio.median()

# 生成信號
signals = pd.Series(0, index=df.index)

# 向上突破上軌 + 高波動
signals[(df['$close'] > upper_band) & (volatility_ratio > median_vol)] = 1

# 向下突破下軌 + 高波動
signals[(df['$close'] < lower_band) & (volatility_ratio > median_vol)] = -1

# 回歸均值：價格回到通道內
signals[(df['$close'] < upper_band) & (df['$close'] > lower_band)] = 0

print(f"波動率策略：{len(signals[signals != 0])} 個信號")

# 策略參數設定
# {
#   "use_qlib_expressions": true,
#   "qlib_fields": ["$close", "$high", "$low", "Mean($close, 20)", "Std($close, 20)", ...]
# }
`,
  },
  {
    id: 'qlib_mean_reversion',
    name: '均值回歸策略（Qlib 表達式）',
    description: '使用 Qlib 表達式計算 Z-Score 和 RSI，捕捉回歸機會',
    icon: '🔄',
    tags: ['Qlib 表達式', '均值回歸', '中等'],
    code: `# Qlib 均值回歸策略
# 使用 Qlib 表達式計算 Z-Score

from qlib.data import D
import pandas as pd
import numpy as np

# 定義 Qlib 表達式字段
QLIB_FIELDS = [
    '$close',
    'Mean($close, 20)',                                    # 20 日均線
    'Std($close, 20)',                                     # 20 日標準差
    '($close - Mean($close, 20)) / Std($close, 20)',     # Z-Score（Qlib 表達式）
]

# 使用 Qlib 計算的 Z-Score
z_score = df['($close - Mean($close, 20)) / Std($close, 20)']

# 計算 RSI（使用 pandas）
delta = df['$close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
rs = gain / (loss + 1e-6)
rsi = 100 - (100 / (1 + rs))

# 生成信號
signals = pd.Series(0, index=df.index)

# 買入：價格低估（Z-Score < -2）且 RSI 超賣
signals[(z_score < -2) & (rsi < 30)] = 1

# 賣出：價格高估（Z-Score > 2）且 RSI 超買
signals[(z_score > 2) & (rsi > 70)] = -1

# 回歸均值：Z-Score 回到 [-0.5, 0.5] 範圍
signals[(z_score > -0.5) & (z_score < 0.5)] = 0

print(f"均值回歸策略：Z-Score 範圍 [{z_score.min():.2f}, {z_score.max():.2f}]")
print(f"信號數量：{len(signals[signals != 0])}")

# 策略參數設定
# {
#   "use_qlib_expressions": true,
#   "qlib_fields": ["$close", "Mean($close, 20)", "Std($close, 20)", "($close - Mean($close, 20)) / Std($close, 20)"]
# }
`,
  },
  {
    id: 'qlib_correlation',
    name: '價量相關性策略（Qlib 表達式）',
    description: '使用 Qlib 表達式計算價量相關性，捕捉趨勢確認信號',
    icon: '📈',
    tags: ['Qlib 表達式', '相關性', '進階'],
    code: `# Qlib 價量相關性策略
# 使用 Qlib 的 Corr() 表達式

from qlib.data import D
import pandas as pd

# 定義 Qlib 表達式字段
QLIB_FIELDS = [
    '$close', '$volume',
    'Corr($close, $volume, 10)',          # 10 日價量相關性（Qlib 表達式）
    'Corr($close, $volume, 20)',          # 20 日價量相關性
    'Mean($close, 5) / Mean($close, 20)', # 均線比率
    'Std($close, 20)',                     # 波動率
]

# 使用 Qlib 計算的相關性
corr_10 = df['Corr($close, $volume, 10)']
corr_20 = df['Corr($close, $volume, 20)']
ma_ratio = df['Mean($close, 5) / Mean($close, 20)']

# 趨勢確認信號
trend_up = (ma_ratio > 1.02) & (corr_10 > 0.5)    # 上漲趨勢 + 正相關
trend_down = (ma_ratio < 0.98) & (corr_10 < -0.5)  # 下跌趨勢 + 負相關

# 生成信號
signals = pd.Series(0, index=df.index)

# 買入：上漲趨勢且價量正相關
signals[trend_up] = 1

# 賣出：下跌趨勢且價量負相關
signals[trend_down] = -1

# 趨勢反轉：相關性轉向
signals[(corr_10 < 0) & (corr_10.shift(1) > 0)] = 0  # 平倉

print(f"價量策略：相關性範圍 [{corr_10.min():.2f}, {corr_10.max():.2f}]")
print(f"買入信號：{(signals == 1).sum()}，賣出信號：{(signals == -1).sum()}")

# 策略參數設定
# {
#   "use_qlib_expressions": true,
#   "qlib_fields": ["$close", "$volume", "Corr($close, $volume, 10)", ...]
# }
`,
  },
  {
    id: 'qlib_ml_lightgbm',
    name: 'LightGBM 預測模型（Qlib ML）',
    description: '使用 Qlib 整合的 LightGBM 模型預測未來收益率',
    icon: '🤖',
    tags: ['機器學習', 'LightGBM', '進階'],
    code: `# LightGBM 機器學習預測策略
# 使用多個技術指標組合生成交易訊號（模擬 ML 模型預測）

from qlib.data import D
import pandas as pd
import numpy as np

# ========== 特徵工程 ==========
# 定義 18 個量化因子（模擬 LightGBM 特徵）
QLIB_FIELDS = [
    # 基礎價量
    '$close', '$open', '$high', '$low', '$volume',

    # 移動平均線
    'Mean($close, 5)',   # 短期均線
    'Mean($close, 10)',  # 中期均線
    'Mean($close, 20)',  # 長期均線
    'Mean($close, 60)',  # 超長期均線

    # MACD 指標
    '(EMA($close, 12) - EMA($close, 26))',  # MACD DIF

    # 波動率指標
    'Std($close, 20)',   # 20 日標準差

    # 動量指標
    'Ref($close, 1) / $close - 1',   # 1 日動量
    'Ref($close, 5) / $close - 1',   # 5 日動量
    'Ref($close, 10) / $close - 1',  # 10 日動量

    # 成交量指標
    '$volume / Mean($volume, 20)',   # 成交量比率

    # 價格位置
    '($close - Min($close, 20)) / (Max($close, 20) - Min($close, 20))',  # 威廉指標

    # 價量相關性
    'Corr($close, $volume, 10)',     # 10 日價量相關性

    # 最高最低價差
    '($high - $low) / $close',       # 振幅比率
]

# ========== 多因子綜合評分 ==========

# 1️⃣ 趨勢因子（40% 權重）
ma5 = df['Mean($close, 5)']
ma10 = df['Mean($close, 10)']
ma20 = df['Mean($close, 20)']
ma60 = df['Mean($close, 60)']

# 均線排列：短期 > 中期 > 長期 = 多頭趨勢
trend_score = (
    (ma5 > ma10).astype(int) * 0.3 +
    (ma10 > ma20).astype(int) * 0.3 +
    (ma20 > ma60).astype(int) * 0.2 +
    (df['$close'] > ma20).astype(int) * 0.2
)

# 2️⃣ 動量因子（30% 權重）
momentum_1d = df['Ref($close, 1) / $close - 1']
momentum_5d = df['Ref($close, 5) / $close - 1']
momentum_10d = df['Ref($close, 10) / $close - 1']

# 加權動量評分
momentum_score = (
    momentum_1d * 0.2 +
    momentum_5d * 0.4 +
    momentum_10d * 0.4
)

# 3️⃣ 波動率因子（15% 權重）
volatility = df['Std($close, 20)']
amplitude = df['($high - $low) / $close']

# 低波動 = 穩定趨勢 = 正評分
volatility_score = -volatility / df['$close']  # 標準化波動率（負值轉正）

# 4️⃣ 成交量因子（15% 權重）
volume_ratio = df['$volume / Mean($volume, 20)']
price_volume_corr = df['Corr($close, $volume, 10)']

# 放量上漲 = 正評分
volume_score = (
    (volume_ratio > 1.2).astype(int) * 0.6 +
    (price_volume_corr > 0.3).astype(int) * 0.4
)

# ========== 綜合評分（模擬 LightGBM 預測） ==========
composite_score = (
    trend_score * 0.40 +         # 趨勢權重 40%
    momentum_score * 0.30 +      # 動量權重 30%
    volatility_score * 0.15 +    # 波動權重 15%
    volume_score * 0.15          # 成交量權重 15%
)

# 標準化評分（Z-Score）
composite_mean = composite_score.mean()
composite_std = composite_score.std()
normalized_score = (composite_score - composite_mean) / (composite_std + 1e-6)

# ========== 訊號生成（模擬 ML 模型決策） ==========
signals = pd.Series(0, index=df.index)

# 策略 1：基於分位數的訊號（保證有訊號）
# 買入：綜合評分前 30%
buy_threshold = normalized_score.quantile(0.70)
# 賣出：綜合評分後 30%
sell_threshold = normalized_score.quantile(0.30)

# 生成原始訊號
signals[normalized_score >= buy_threshold] = 1
signals[normalized_score <= sell_threshold] = -1

# 策略 2：趨勢確認（提升訊號品質）
# 只在明確趨勢時交易
ma5_vs_ma20 = ma5 / ma20 - 1  # 短期均線相對長期均線的比率

# 買入：綜合評分高 AND 短期均線 > 長期均線（上升趨勢）
signals[(normalized_score >= buy_threshold) & (ma5_vs_ma20 > 0.02)] = 1

# 賣出：綜合評分低 AND 短期均線 < 長期均線（下降趨勢）
signals[(normalized_score <= sell_threshold) & (ma5_vs_ma20 < -0.02)] = -1

# ========== 統計輸出 ==========
buy_signals = (signals == 1).sum()
sell_signals = (signals == -1).sum()
total_signals = buy_signals + sell_signals

print(f"🤖 LightGBM 模擬策略")
print(f"📊 使用 {len(QLIB_FIELDS)} 個量化因子")
print(f"✅ 買入訊號：{buy_signals} 次")
print(f"❌ 賣出訊號：{sell_signals} 次")
print(f"📈 總訊號數：{total_signals} 次")
print(f"🎯 訊號密度：{(total_signals / len(df) * 100):.2f}%")
print(f"📉 綜合評分範圍：[{normalized_score.min():.2f}, {normalized_score.max():.2f}]")

# 策略參數設定（可選）
# {
#   "signal_threshold": 1.0,
#   "min_holding_days": 2,
#   "max_positions": 1
# }
`,
  },
  {
    id: 'alpha158_multifactor',
    name: 'Alpha158 多因子策略',
    description: '使用 Alpha158 因子庫的多個技術指標組合，捕捉市場機會',
    icon: '🧬',
    tags: ['Alpha158', '多因子', '進階'],
    code: `# Alpha158 多因子組合策略
# 使用 Microsoft Qlib Alpha158 標準因子庫
# 包含 158 個預定義因子：KBar、Price、Volume、Rolling

from qlib.data import D
import pandas as pd
import numpy as np

# Alpha158 因子配置
# 說明：Alpha158 包含 4 大類因子
# 1. KBar (9): K線形態因子（KMID, KLEN, KUP, KLOW 等）
# 2. Price (20): 歷史價格因子（OPEN0-4, HIGH0-4, LOW0-4, CLOSE0-4, VWAP0-4）
# 3. Volume (5): 成交量因子（VOLUME0-4）
# 4. Rolling (124): 滾動窗口技術指標（ROC, MA, STD, BETA, RSV 等，窗口 5/10/20/30/60）

ALPHA158_CONFIG = {
    'kbar': {},  # 使用所有 9 個 K線形態因子
    'price': {
        'windows': [0, 1, 2],  # 最近 3 天的價格
        'feature': ['CLOSE', 'HIGH', 'LOW']
    },
    'volume': {
        'windows': [0, 1, 2]  # 最近 3 天的成交量
    },
    'rolling': {
        'windows': [5, 10, 20],  # 使用 3 個窗口
        'include': [
            'ROC',   # 變化率
            'MA',    # 均線
            'STD',   # 標準差
            'RSV',   # 相對強度值
            'MAX',   # 最大值
            'MIN',   # 最小值
            'CORR',  # 價量相關性
            'BETA',  # Beta 系數
        ]
    }
}

# 注意：使用 Alpha158 時，QLIB_FIELDS 可設為 None
# 系統會自動根據 ALPHA158_CONFIG 計算所有因子

# df 會包含所有 Alpha158 計算的因子欄位
# 例如：KMID, KLEN, CLOSE0, CLOSE1, VOLUME0, ROC5, MA10, STD20, RSV5 等

# === 策略邏輯 ===

# 1. 趨勢因子（使用 MA 和 ROC）
trend_score = (
    df['MA5'] * 0.4 +      # 短期均線
    df['MA10'] * 0.3 +     #中期均線
    df['MA20'] * 0.3       # 長期均線
)

# 2. 動量因子（使用 ROC）
momentum_score = (
    df['ROC5'] * 0.5 +     # 5日動量
    df['ROC10'] * 0.3 +    # 10日動量
    df['ROC20'] * 0.2      # 20日動量
)

# 3. 波動率因子（使用 STD 和 RSV）
volatility = (df['STD5'] + df['STD10'] + df['STD20']) / 3
rsv_signal = (df['RSV5'] + df['RSV10'] + df['RSV20']) / 3

# 4. 價量配合（使用 CORR 和 BETA）
price_volume_sync = df['CORR5']  # 價量相關性
market_beta = df['BETA5']         # 市場 Beta

# 5. K線形態（使用 KBar 因子）
kbar_score = (
    df['KMID'] * 0.3 +    # K線實體位置
    df['KLEN'] * 0.3 +    # K線長度
    df['KUP'] * 0.2 +     # 上影線
    df['KLOW'] * 0.2      # 下影線
)

# === 綜合評分 ===
# 多因子加權組合
composite_score = (
    trend_score * 0.3 +           # 趨勢權重 30%
    momentum_score * 0.25 +       # 動量權重 25%
    rsv_signal * 0.2 +            # RSV 權重 20%
    price_volume_sync * 0.15 +    # 價量配合 15%
    kbar_score * 0.1              # K線形態 10%
)

# 波動率過濾：高波動時降低信號強度
composite_score = composite_score * (1 / (1 + volatility))

# === 生成信號 ===
signals = pd.Series(0, index=df.index)

# 買入信號：綜合評分在前 20%
buy_threshold = composite_score.quantile(0.8)
signals[composite_score >= buy_threshold] = 1

# 賣出信號：綜合評分在後 20%
sell_threshold = composite_score.quantile(0.2)
signals[composite_score <= sell_threshold] = -1

print(f"✅ Alpha158 多因子策略")
print(f"📊 因子數量：{len([col for col in df.columns if col not in ['$open', '$high', '$low', '$close', '$volume']])} 個")
print(f"🎯 買入信號：{(signals == 1).sum()} 次")
print(f"📉 賣出信號：{(signals == -1).sum()} 次")
print(f"📈 綜合評分範圍：[{composite_score.min():.4f}, {composite_score.max():.4f}]")

# 策略參數設定
# {
#   "use_alpha158": true,
#   "alpha158_config": {
#     "kbar": {},
#     "price": {"windows": [0, 1, 2], "feature": ["CLOSE", "HIGH", "LOW"]},
#     "volume": {"windows": [0, 1, 2]},
#     "rolling": {
#       "windows": [5, 10, 20],
#       "include": ["ROC", "MA", "STD", "RSV", "MAX", "MIN", "CORR", "BETA"]
#     }
#   }
# }
`,
  },
  {
    id: 'alpha158_ml_features',
    name: 'Alpha158 機器學習特徵',
    description: '使用完整 Alpha158 因子作為機器學習特徵，自動訓練預測模型',
    icon: '🎯',
    tags: ['Alpha158', '機器學習', '完整因子'],
    code: `# Alpha158 + 機器學習策略
# 使用完整 Alpha158 因子庫（158 個因子）作為 ML 特徵
# 適合 LightGBM、XGBoost 等樹模型

from qlib.data import D
import pandas as pd
import numpy as np

# 完整 Alpha158 配置
# 說明：使用所有 158 個標準因子
ALPHA158_CONFIG = {
    'kbar': {},  # 9 個 K線形態因子
    'price': {
        'windows': [0, 1, 2, 3, 4],  # 5 天歷史價格
        'feature': ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VWAP']  # 5 種價格
        # 共 5 × 5 = 25 個因子（實際 20 個，VWAP 可能不可用）
    },
    'volume': {
        'windows': [0, 1, 2, 3, 4]  # 5 天成交量
        # 共 5 個因子
    },
    'rolling': {
        'windows': [5, 10, 20, 30, 60],  # 5 個時間窗口
        'include': [
            # 29 種滾動指標 × 5 個窗口 = 145 個因子（實際 124 個）
            'ROC',   # Rate of Change - 變化率
            'MA',    # Moving Average - 移動平均
            'STD',   # Standard Deviation - 標準差
            'BETA',  # Beta coefficient - Beta 係數
            'RSQR',  # R-squared - R 平方
            'RESI',  # Residual - 殘差
            'MAX',   # Maximum - 最大值
            'MIN',   # Minimum - 最小值
            'QTLU',  # Quantile upper - 上四分位
            'QTLD',  # Quantile lower - 下四分位
            'RANK',  # Rank - 排名
            'RSV',   # Relative Strength Value - 相對強度
            'IMAX',  # Index of maximum - 最大值位置
            'IMIN',  # Index of minimum - 最小值位置
            'IMXD',  # Max - Min index diff - 極值位置差
            'CORR',  # Correlation - 相關性
            'CORD',  # Correlation delta - 相關性變化
            'CNTP',  # Count positive - 正值計數
            'CNTN',  # Count negative - 負值計數
            'CNTD',  # Count delta - 變化計數
            'SUMP',  # Sum positive - 正值總和
            'SUMN',  # Sum negative - 負值總和
            'SUMD',  # Sum delta - 變化總和
            'VMA',   # Volume moving average - 成交量均線
            'VSTD',  # Volume std - 成交量標準差
            'WVMA',  # Weighted volume MA - 加權成交量均線
            'VSUMP', # Volume sum positive - 成交量正和
            'VSUMN', # Volume sum negative - 成交量負和
            'VSUMD', # Volume sum delta - 成交量變化和
        ]
    }
}

# === 機器學習特徵工程 ===

# 方案 1：直接使用所有 Alpha158 因子作為特徵
# 系統會自動提取所有 Alpha158 欄位
feature_columns = [col for col in df.columns if col not in ['$open', '$high', '$low', '$close', '$volume']]

print(f"✅ Alpha158 完整因子庫")
print(f"📊 特徵數量：{len(feature_columns)} 個")
print(f"🎯 適用模型：LightGBM、XGBoost、Random Forest")
print(f"")
print(f"因子分類統計：")
print(f"  - KBar 因子：9 個（K線形態）")
print(f"  - Price 因子：20 個（歷史價格）")
print(f"  - Volume 因子：5 個（成交量）")
print(f"  - Rolling 因子：124 個（技術指標）")
print(f"")

# === 特徵重要性提示 ===
print(f"💡 建議 ML 配置：")
print(f"  1. train_ratio = 0.7 （70% 訓練數據）")
print(f"  2. prediction_days = 5 （預測未來 5 天收益）")
print(f"  3. n_estimators = 200-500 （樹數量）")
print(f"  4. learning_rate = 0.05-0.1 （學習率）")
print(f"  5. max_depth = 5-8 （樹深度）")
print(f"")
print(f"⚠️ 注意：158 個特徵可能導致過擬合")
print(f"建議使用特徵選擇（如 feature_importance）選取前 50-80 個特徵")

# === 信號生成（ML 模型會自動處理） ===
# 使用 strategy_type: "ml_model" 時，系統會：
# 1. 自動提取 Alpha158 特徵
# 2. 訓練 LightGBM 模型預測未來收益
# 3. 根據預測結果生成買賣信號

signals = pd.Series(0, index=df.index)
print(f"🤖 已準備 ML 特徵，等待模型訓練...")

# 策略參數設定
# {
#   "strategy_type": "ml_model",
#   "use_alpha158": true,
#   "alpha158_config": {
#     "kbar": {},
#     "price": {"windows": [0, 1, 2, 3, 4], "feature": ["OPEN", "HIGH", "LOW", "CLOSE", "VWAP"]},
#     "volume": {"windows": [0, 1, 2, 3, 4]},
#     "rolling": {
#       "windows": [5, 10, 20, 30, 60],
#       "include": ["ROC", "MA", "STD", "BETA", "RSQR", "RESI", "MAX", "MIN", "QTLU", "QTLD", "RANK", "RSV", "IMAX", "IMIN", "IMXD", "CORR", "CORD", "CNTP", "CNTN", "CNTD", "SUMP", "SUMN", "SUMD", "VMA", "VSTD", "WVMA", "VSUMP", "VSUMN", "VSUMD"]
#     }
#   },
#   "train_ratio": 0.7,
#   "prediction_days": 5,
#   "signal_threshold": 0.015,
#   "n_estimators": 300,
#   "learning_rate": 0.05,
#   "max_depth": 6
# }
`,
  },
  {
    id: 'alpha158_lightgbm_real',
    name: 'Alpha158 真正ML（修復版）',
    description: '使用 LightGBM 訓練 Alpha158 因子預測未來報酬率。完整的機器學習流程：特徵提取 → 模型訓練 → 預測 → 信號生成',
    icon: '🤖',
    tags: ['Alpha158', 'LightGBM', '真正ML'],
    code: `# ============================================================
# Alpha158 + LightGBM 真正的機器學習策略（v3 修復版）
# ============================================================

# 提取參數
train_ratio = params.get('train_ratio', 0.7)
prediction_days = params.get('prediction_days', 5)
signal_threshold = params.get('signal_threshold', 0.015)
n_estimators = params.get('n_estimators', 100)
learning_rate = params.get('learning_rate', 0.05)
max_depth = params.get('max_depth', 5)

print("="*60)
print("Alpha158 + LightGBM 機器學習策略")
print("="*60)

# 清理特徵名稱（移除 LightGBM 不支援的字符）
df_clean = df.copy()
df_clean.columns = [
    col.replace('$', '').replace('(', '').replace(')', '').replace(' ', '_').replace(',', '_')
    for col in df_clean.columns
]

# 提取特徵
base_cols = ['open', 'high', 'low', 'close', 'volume']
feature_cols = [c for c in df_clean.columns if c not in base_cols]

print(f"樣本數: {len(df_clean)} | 特徵數: {len(feature_cols)}")

# 創建目標變數
df_ml = df_clean.copy()
df_ml['target'] = df_ml['close'].shift(-prediction_days) / df_ml['close'] - 1
df_ml = df_ml.dropna()

# 訓練/測試分割
split = int(len(df_ml) * train_ratio)
X_train = df_ml[feature_cols].iloc[:split]
y_train = df_ml['target'].iloc[:split]
X_test = df_ml[feature_cols].iloc[split:]
y_test = df_ml['target'].iloc[split:]

print(f"訓練: {len(X_train)} | 測試: {len(X_test)}")

# 訓練 LightGBM
if lgb is None:
    print("❌ LightGBM 不可用")
    signals = pd.Series(0, index=df.index)
else:
    model = lgb.LGBMRegressor(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        num_leaves=31,
        random_state=42,
        n_jobs=1,
        verbose=-1
    )

    model.fit(X_train, y_train)

    # 預測
    preds = pd.Series(0.0, index=df.index)
    preds[X_test.index] = model.predict(X_test)

    # 生成信號
    signals = pd.Series(0, index=df.index)
    signals[preds > signal_threshold] = 1
    signals[preds < -signal_threshold] = -1

    buy = (signals == 1).sum()
    sell = (signals == -1).sum()

    print(f"買入: {buy} | 賣出: {sell}")
    print(f"R²: {model.score(X_test, y_test):.4f}")
    print("="*60)
`,
  },

  // ==================== 量化因子策略（5 個）====================

  {
    id: 'fama_french_3factor',
    name: 'Fama-French 三因子模型',
    description: '經典的多因子模型：市場因子、規模因子(SMB)、價值因子(HML)',
    icon: '📚',
    tags: ['多因子', '學術', '價值投資'],
    code: `# Fama-French 三因子模型
# 市場因子 + 規模因子(SMB) + 價值因子(HML)

import pandas as pd
import numpy as np

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '$close',
    '$volume',
    # 市場因子（Market Factor）
    '($close - Mean($close, 252)) / Std($close, 252)',  # 超額收益標準化

    # 規模因子（SMB: Small Minus Big）- 使用成交量作為規模代理
    'Log($volume) / Mean(Log($volume), 252)',  # 成交量相對水平

    # 價值因子（HML: High Minus Low）- 使用價格動量的倒數作為價值代理
    '1 / (1 + ($close / Ref($close, 252) - 1))',  # 反向動量（價值）

    # 動量因子（額外）
    '($close / Ref($close, 20) - 1)',  # 近期動量
]

# ========== 因子計算 ==========
market_factor = df['($close - Mean($close, 252)) / Std($close, 252)']
smb_factor = df['Log($volume) / Mean(Log($volume), 252)']  # 小盤股溢價
hml_factor = df['1 / (1 + ($close / Ref($close, 252) - 1))']  # 價值溢價
momentum = df['($close / Ref($close, 20) - 1)']

# ========== 多因子評分 ==========
# 權重設定（可調整）
w_market = 0.3
w_smb = 0.3
w_hml = 0.4

# 標準化因子
market_z = (market_factor - market_factor.mean()) / market_factor.std()
smb_z = (smb_factor - smb_factor.mean()) / smb_factor.std()
hml_z = (hml_factor - hml_factor.mean()) / hml_factor.std()

# 綜合評分
score = w_market * market_z + w_smb * smb_z + w_hml * hml_z

# ========== 信號生成 ==========
signals = pd.Series(0, index=df.index)

# 買入：綜合評分高於 70% 分位數
buy_threshold = score.quantile(0.7)
signals[score > buy_threshold] = 1

# 賣出：綜合評分低於 30% 分位數
sell_threshold = score.quantile(0.3)
signals[score < sell_threshold] = -1

print(f"✅ Fama-French 三因子模型")
print(f"市場因子權重: {w_market}")
print(f"規模因子權重: {w_smb}")
print(f"價值因子權重: {w_hml}")
print(f"買入信號: {(signals == 1).sum()}")
print(f"賣出信號: {(signals == -1).sum()}")
`,
  },

  {
    id: 'momentum_reversal',
    name: '動量反轉組合策略',
    description: '結合時序動量和橫截面動量，捕捉趨勢延續與反轉機會',
    icon: '🔄',
    tags: ['動量', '反轉', '中級'],
    code: `# 動量反轉組合策略
# 時序動量 + 橫截面動量 + 短期反轉

import pandas as pd
import numpy as np

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '$close',
    # 長期動量（12個月排除最近1個月）
    '($close / Ref($close, 252) - 1)',  # 年度收益率

    # 中期動量（6個月）
    '($close / Ref($close, 126) - 1)',  # 半年收益率

    # 短期動量（1個月）
    '($close / Ref($close, 21) - 1)',   # 月度收益率

    # 短期反轉（1週）
    '($close / Ref($close, 5) - 1)',    # 週度收益率

    # 動量波動率
    'Std($close / Ref($close, 1) - 1, 60)',  # 60日波動率
]

# ========== 因子提取 ==========
mom_12m = df['($close / Ref($close, 252) - 1)']
mom_6m = df['($close / Ref($close, 126) - 1)']
mom_1m = df['($close / Ref($close, 21) - 1)']
reversal_1w = df['($close / Ref($close, 5) - 1)']
volatility = df['Std($close / Ref($close, 1) - 1, 60)']

# ========== 動量評分 ==========
# 標準化
mom_12m_z = (mom_12m - mom_12m.mean()) / mom_12m.std()
mom_6m_z = (mom_6m - mom_6m.mean()) / mom_6m.std()
mom_1m_z = (mom_1m - mom_1m.mean()) / mom_1m.std()

# 動量綜合評分（權重遞減）
momentum_score = 0.5 * mom_12m_z + 0.3 * mom_6m_z + 0.2 * mom_1m_z

# 短期反轉評分（反向）
reversal_score = -reversal_1w  # 反轉：近期下跌後反彈

# ========== 信號生成 ==========
signals = pd.Series(0, index=df.index)

# 策略 1: 動量買入（長期動量強 + 中期動量確認）
momentum_buy = (momentum_score > momentum_score.quantile(0.7)) & (mom_1m > 0)

# 策略 2: 反轉買入（短期超跌 + 長期趨勢向上）
reversal_buy = (reversal_1w < reversal_1w.quantile(0.2)) & (mom_12m > 0)

# 綜合買入信號
signals[momentum_buy | reversal_buy] = 1

# 賣出信號：動量轉弱或短期衝高
momentum_sell = (momentum_score < momentum_score.quantile(0.3))
reversal_sell = (reversal_1w > reversal_1w.quantile(0.8))
signals[momentum_sell | reversal_sell] = -1

print(f"✅ 動量反轉組合策略")
print(f"動量買入: {momentum_buy.sum()}")
print(f"反轉買入: {reversal_buy.sum()}")
print(f"總買入: {(signals == 1).sum()}")
print(f"總賣出: {(signals == -1).sum()}")
`,
  },

  {
    id: 'quality_factor',
    name: '質量因子策略',
    description: '基於財務健康度的質量投資：高 ROE、穩定盈利、低槓桿',
    icon: '💎',
    tags: ['質量', '基本面', '進階'],
    code: `# 質量因子策略
# 使用技術指標模擬財務質量特徵

import pandas as pd
import numpy as np

# ========== Qlib 表達式字段 ==========
# 注意：由於缺少財務數據，使用技術指標模擬質量特徵
QLIB_FIELDS = [
    '$close',
    '$volume',
    # 盈利穩定性（使用價格穩定性代理）
    'Mean($close, 60) / Std($close, 60)',  # 均值/標準差比率

    # 成長性（使用趨勢強度代理）
    '($close / Mean($close, 252) - 1)',  # 年度漲幅

    # 流動性質量（成交量穩定性）
    'Mean($volume, 60) / Std($volume, 60)',

    # 價格動量質量（趨勢一致性）
    'Corr($close, Sequence(252), 60)',  # 與時間序列相關性

    # 低波動率（質量股特徵）
    '1 / (1 + Std($close / Ref($close, 1) - 1, 60))',
]

# ========== 質量因子計算 ==========
# 1. 盈利穩定性（Profitability Stability）
profit_stability = df['Mean($close, 60) / Std($close, 60)']

# 2. 成長性（Growth）
growth = df['($close / Mean($close, 252) - 1)']

# 3. 流動性質量（Liquidity Quality）
liquidity_quality = df['Mean($volume, 60) / Std($volume, 60)']

# 4. 趨勢一致性（Trend Consistency）
trend_consistency = df['Corr($close, Sequence(252), 60)']

# 5. 低波動率（Low Volatility）
low_volatility = df['1 / (1 + Std($close / Ref($close, 1) - 1, 60))']

# ========== 質量評分 ==========
# 標準化因子
stability_z = (profit_stability - profit_stability.mean()) / profit_stability.std()
growth_z = (growth - growth.mean()) / growth.std()
liquidity_z = (liquidity_quality - liquidity_quality.mean()) / liquidity_quality.std()
consistency_z = (trend_consistency - trend_consistency.mean()) / trend_consistency.std()
volatility_z = (low_volatility - low_volatility.mean()) / low_volatility.std()

# 綜合質量評分（權重可調）
quality_score = (
    0.25 * stability_z +
    0.20 * growth_z +
    0.20 * liquidity_z +
    0.20 * consistency_z +
    0.15 * volatility_z
)

# ========== 信號生成 ==========
signals = pd.Series(0, index=df.index)

# 高質量買入：質量評分前 30%
buy_threshold = quality_score.quantile(0.7)
signals[quality_score > buy_threshold] = 1

# 低質量賣出：質量評分後 30%
sell_threshold = quality_score.quantile(0.3)
signals[quality_score < sell_threshold] = -1

print(f"✅ 質量因子策略")
print(f"平均質量評分: {quality_score.mean():.4f}")
print(f"質量評分標準差: {quality_score.std():.4f}")
print(f"高質量買入: {(signals == 1).sum()}")
print(f"低質量賣出: {(signals == -1).sum()}")
`,
  },

  {
    id: 'value_factor',
    name: '價值因子策略',
    description: '價值投資策略：低估值、高股息、價格動量反轉',
    icon: '💰',
    tags: ['價值', '反向投資', '長期'],
    code: `# 價值因子策略
# 使用技術指標模擬價值特徵

import pandas as pd
import numpy as np

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '$close',
    '$volume',
    # 價格相對水平（模擬 P/E 比率）
    '$close / Mean($close, 252)',  # 當前價格 / 年均價

    # 反向動量（價值股特徵）
    '1 / (1 + ($close / Ref($close, 252) - 1))',  # 反向年度收益

    # 價格波動率（低波動 = 穩定價值）
    'Std($close / Ref($close, 1) - 1, 60)',

    # 成交量相對水平（模擬流動性）
    '$volume / Mean($volume, 60)',

    # 價格動量（趨勢確認）
    '($close / Ref($close, 60) - 1)',  # 季度動量
]

# ========== 價值因子計算 ==========
# 1. 價格估值水平（低估值 = 價值股）
price_level = df['$close / Mean($close, 252)']
valuation_score = 1 / price_level  # 倒數：價格越低，評分越高

# 2. 反向動量（價值股特徵）
reverse_momentum = df['1 / (1 + ($close / Ref($close, 252) - 1))']

# 3. 低波動率（穩定性）
volatility = df['Std($close / Ref($close, 1) - 1, 60)']
stability_score = 1 / (1 + volatility)

# 4. 流動性（避免流動性陷阱）
volume_ratio = df['$volume / Mean($volume, 60)']

# 5. 近期動量（確認反轉）
recent_momentum = df['($close / Ref($close, 60) - 1)']

# ========== 價值評分 ==========
# 標準化
valuation_z = (valuation_score - valuation_score.mean()) / valuation_score.std()
reverse_z = (reverse_momentum - reverse_momentum.mean()) / reverse_momentum.std()
stability_z = (stability_score - stability_score.mean()) / stability_score.std()
liquidity_z = (volume_ratio - volume_ratio.mean()) / volume_ratio.std()

# 綜合價值評分
value_score = (
    0.40 * valuation_z +      # 估值最重要
    0.30 * reverse_z +         # 反向動量
    0.20 * stability_z +       # 穩定性
    0.10 * liquidity_z         # 流動性
)

# ========== 信號生成 ==========
signals = pd.Series(0, index=df.index)

# 價值買入：高價值評分 + 近期動量轉正
value_buy = (value_score > value_score.quantile(0.7)) & (recent_momentum > 0)
signals[value_buy] = 1

# 價值賣出：低價值評分或過度高估
value_sell = (value_score < value_score.quantile(0.3)) | (price_level > price_level.quantile(0.9))
signals[value_sell] = -1

print(f"✅ 價值因子策略")
print(f"平均估值水平: {price_level.mean():.4f}")
print(f"價值買入: {(signals == 1).sum()}")
print(f"價值賣出: {(signals == -1).sum()}")
`,
  },

  {
    id: 'low_volatility',
    name: '低波動率異常策略',
    description: '投資低波動率股票，利用風險調整收益異常',
    icon: '📉',
    tags: ['低波動', '防禦性', '穩健'],
    code: `# 低波動率異常策略
# Low Volatility Anomaly: 低風險高收益

import pandas as pd
import numpy as np

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '$close',
    '$volume',
    # 短期波動率（20日）
    'Std($close / Ref($close, 1) - 1, 20)',

    # 中期波動率（60日）
    'Std($close / Ref($close, 1) - 1, 60)',

    # 長期波動率（252日）
    'Std($close / Ref($close, 1) - 1, 252)',

    # 下行波動率（負收益的標準差）
    'Std(Min($close / Ref($close, 1) - 1, 0), 60)',

    # 波動率穩定性
    'Std($close / Ref($close, 1) - 1, 20) / Std($close / Ref($close, 1) - 1, 60)',

    # 收益率
    '($close / Ref($close, 60) - 1)',
]

# ========== 波動率計算 ==========
vol_20d = df['Std($close / Ref($close, 1) - 1, 20)']
vol_60d = df['Std($close / Ref($close, 1) - 1, 60)']
vol_252d = df['Std($close / Ref($close, 1) - 1, 252)']
downside_vol = df['Std(Min($close / Ref($close, 1) - 1, 0), 60)']
vol_stability = df['Std($close / Ref($close, 1) - 1, 20) / Std($close / Ref($close, 1) - 1, 60)']
returns = df['($close / Ref($close, 60) - 1)']

# ========== 風險調整收益 ==========
# Sharpe 比率（簡化版）
sharpe = returns / (vol_60d + 1e-6)  # 避免除零

# 下行風險調整收益（Sortino 比率）
sortino = returns / (downside_vol + 1e-6)

# ========== 低波動率評分 ==========
# 波動率評分（越低越好）
vol_score_20 = 1 / (1 + vol_20d)
vol_score_60 = 1 / (1 + vol_60d)
vol_score_252 = 1 / (1 + vol_252d)

# 標準化
vol_20_z = (vol_score_20 - vol_score_20.mean()) / vol_score_20.std()
vol_60_z = (vol_score_60 - vol_score_60.mean()) / vol_score_60.std()
sharpe_z = (sharpe - sharpe.mean()) / sharpe.std()
sortino_z = (sortino - sortino.mean()) / sortino.std()

# 綜合低波動評分
low_vol_score = (
    0.30 * vol_20_z +      # 短期波動
    0.30 * vol_60_z +      # 中期波動
    0.20 * sharpe_z +      # Sharpe 比率
    0.20 * sortino_z       # Sortino 比率
)

# ========== 信號生成 ==========
signals = pd.Series(0, index=df.index)

# 買入：低波動率 + 正收益
low_vol_buy = (low_vol_score > low_vol_score.quantile(0.7)) & (returns > 0)
signals[low_vol_buy] = 1

# 賣出：高波動率或負收益
high_vol_sell = (low_vol_score < low_vol_score.quantile(0.3)) | (returns < returns.quantile(0.2))
signals[high_vol_sell] = -1

print(f"✅ 低波動率異常策略")
print(f"平均波動率(60日): {vol_60d.mean():.4%}")
print(f"平均 Sharpe 比率: {sharpe.mean():.4f}")
print(f"低波動買入: {(signals == 1).sum()}")
print(f"高波動賣出: {(signals == -1).sum()}")
`,
  },

  // ==================== 機器學習模型（4 個）====================

  {
    id: 'xgboost_multifactor',
    name: 'XGBoost 多因子預測',
    description: '使用 XGBoost 訓練多因子預測模型，預測未來收益率',
    icon: '🌲',
    tags: ['XGBoost', '機器學習', '多因子'],
    code: `# XGBoost 多因子預測模型
# 訓練 XGBoost 模型預測未來收益率

import pandas as pd
import numpy as np

# 動態導入 XGBoost
try:
    import xgboost as xgb
except ImportError:
    xgb = None
    print("⚠️  XGBoost 未安裝，使用備用策略")

# ========== Qlib 表達式字段（技術因子）==========
QLIB_FIELDS = [
    '$close', '$open', '$high', '$low', '$volume',

    # 價格動量因子
    '($close / Ref($close, 5) - 1)',
    '($close / Ref($close, 10) - 1)',
    '($close / Ref($close, 20) - 1)',
    '($close / Ref($close, 60) - 1)',

    # 均線因子
    'Mean($close, 5)', 'Mean($close, 10)', 'Mean($close, 20)', 'Mean($close, 60)',

    # 波動率因子
    'Std($close, 20)', 'Std($close, 60)',

    # 成交量因子
    '$volume / Mean($volume, 20)',
    'Corr($close, $volume, 20)',

    # 高低點因子
    '($high - $low) / $close',
    '($close - $open) / $close',
]

# ========== 策略參數 ==========
train_ratio = 0.7
prediction_days = 5
signal_threshold = 0.015

# XGBoost 參數
n_estimators = 100
max_depth = 5
learning_rate = 0.05
subsample = 0.8

# ========== 數據準備 ==========
print("="*60)
print("🌲 XGBoost 多因子預測模型")
print("="*60)

# 清理欄位名稱（移除特殊字符）
df_clean = df.copy()
df_clean.columns = [
    col.replace('$', '').replace('(', '').replace(')', '').replace(' ', '_').replace(',', '_').replace('/', '_div_')
    for col in df_clean.columns
]

# 提取特徵
base_cols = ['open', 'high', 'low', 'close', 'volume']
feature_cols = [c for c in df_clean.columns if c not in base_cols]

print(f"樣本數: {len(df_clean)} | 特徵數: {len(feature_cols)}")

# 創建目標變數（未來 N 日收益率）
df_ml = df_clean.copy()
df_ml['target'] = df_ml['close'].shift(-prediction_days) / df_ml['close'] - 1
df_ml = df_ml.dropna()

# 訓練/測試分割
split = int(len(df_ml) * train_ratio)
X_train = df_ml[feature_cols].iloc[:split]
y_train = df_ml['target'].iloc[:split]
X_test = df_ml[feature_cols].iloc[split:]
y_test = df_ml['target'].iloc[split:]

print(f"訓練: {len(X_train)} | 測試: {len(X_test)}")

# ========== 訓練 XGBoost ==========
if xgb is None:
    print("❌ XGBoost 不可用，使用簡單動量策略")
    signals = pd.Series(0, index=df.index)
    momentum = df['($close / Ref($close, 20) - 1)']
    signals[momentum > momentum.quantile(0.7)] = 1
    signals[momentum < momentum.quantile(0.3)] = -1
else:
    model = xgb.XGBRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=1,
        verbosity=0
    )

    model.fit(X_train, y_train)

    # 預測
    preds = pd.Series(0.0, index=df.index)
    preds[X_test.index] = model.predict(X_test)

    # 生成信號
    signals = pd.Series(0, index=df.index)
    signals[preds > signal_threshold] = 1
    signals[preds < -signal_threshold] = -1

    buy = (signals == 1).sum()
    sell = (signals == -1).sum()

    # 特徵重要性
    importance = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print(f"\\n前 5 重要特徵:")
    for i, (feat, imp) in enumerate(importance.head(5).items(), 1):
        print(f"  {i}. {feat}: {imp:.4f}")

    print(f"\\n買入: {buy} | 賣出: {sell}")
    print(f"R²: {model.score(X_test, y_test):.4f}")
    print("="*60)
`,
  },

  {
    id: 'random_forest_classifier',
    name: 'Random Forest 分類模型',
    description: '使用隨機森林分類模型，預測未來漲跌方向',
    icon: '🌳',
    tags: ['Random Forest', '分類', '集成學習'],
    code: `# Random Forest 分類模型
# 預測未來漲跌方向（三分類：漲/平/跌）

import pandas as pd
import numpy as np

# 動態導入 sklearn
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import classification_report, accuracy_score
    sklearn_available = True
except ImportError:
    sklearn_available = False
    print("⚠️  Scikit-learn 未安裝")

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '$close', '$volume',

    # 價格特徵
    '($close / Ref($close, 1) - 1)',   # 日收益率
    '($close / Ref($close, 5) - 1)',
    '($close / Ref($close, 20) - 1)',

    # 技術指標
    'Mean($close, 5)', 'Mean($close, 20)',
    'Std($close, 20)',

    # RSI（簡化版）
    'Mean(Max($close - Ref($close, 1), 0), 14) / (Mean(Abs($close - Ref($close, 1)), 14) + 1e-6)',

    # 成交量
    '$volume / Mean($volume, 20)',

    # 價格位置
    '($close - Min($low, 20)) / (Max($high, 20) - Min($low, 20) + 1e-6)',
]

# ========== 策略參數 ==========
train_ratio = 0.7
prediction_days = 5
threshold_up = 0.02    # 上漲閾值（2%）
threshold_down = -0.02 # 下跌閾值（-2%）

# Random Forest 參數
n_estimators = 100
max_depth = 8
min_samples_split = 5

# ========== 數據準備 ==========
print("="*60)
print("🌳 Random Forest 三分類模型")
print("="*60)

df_clean = df.copy()
df_clean.columns = [
    col.replace('$', '').replace('(', '').replace(')', '').replace(' ', '_').replace(',', '_').replace('/', '_div_')
    for col in df_clean.columns
]

base_cols = ['open', 'high', 'low', 'close', 'volume']
feature_cols = [c for c in df_clean.columns if c not in base_cols]

# 創建目標變數（三分類）
df_ml = df_clean.copy()
future_return = df_ml['close'].shift(-prediction_days) / df_ml['close'] - 1

# 分類標籤：1=上漲, 0=持平, -1=下跌
df_ml['target'] = 0
df_ml.loc[future_return > threshold_up, 'target'] = 1
df_ml.loc[future_return < threshold_down, 'target'] = -1
df_ml = df_ml.dropna()

print(f"樣本數: {len(df_ml)}")
print(f"上漲: {(df_ml['target'] == 1).sum()}")
print(f"持平: {(df_ml['target'] == 0).sum()}")
print(f"下跌: {(df_ml['target'] == -1).sum()}")

# 訓練/測試分割
split = int(len(df_ml) * train_ratio)
X_train = df_ml[feature_cols].iloc[:split]
y_train = df_ml['target'].iloc[:split]
X_test = df_ml[feature_cols].iloc[split:]
y_test = df_ml['target'].iloc[split:]

# ========== 訓練 Random Forest ==========
if not sklearn_available:
    print("❌ Scikit-learn 不可用")
    signals = pd.Series(0, index=df.index)
else:
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        random_state=42,
        n_jobs=1
    )

    model.fit(X_train, y_train)

    # 預測
    preds = pd.Series(0, index=df.index)
    preds[X_test.index] = model.predict(X_test)

    # 生成信號（直接使用預測結果）
    signals = preds

    # 評估
    accuracy = accuracy_score(y_test, preds[X_test.index])

    buy = (signals == 1).sum()
    hold = (signals == 0).sum()
    sell = (signals == -1).sum()

    print(f"\\n準確率: {accuracy:.2%}")
    print(f"買入: {buy} | 持有: {hold} | 賣出: {sell}")
    print("="*60)
`,
  },

  {
    id: 'lstm_timeseries',
    name: 'LSTM 時序預測',
    description: '使用 LSTM 神經網絡捕捉時間序列模式，預測未來價格走勢',
    icon: '🧠',
    tags: ['LSTM', '深度學習', '時序'],
    code: `# LSTM 時序預測模型
# 使用長短期記憶網絡預測價格趨勢

import pandas as pd
import numpy as np

# 注意：LSTM 需要 TensorFlow/PyTorch，這裡提供框架代碼
# 實際部署需要安裝深度學習框架

print("="*60)
print("🧠 LSTM 時序預測模型（框架代碼）")
print("="*60)
print("⚠️  需要安裝 TensorFlow 或 PyTorch")
print("⚠️  以下為簡化版策略，使用技術指標模擬")

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '$close', '$volume',

    # 時序特徵（過去 N 日）
    'Ref($close, 1)', 'Ref($close, 2)', 'Ref($close, 3)', 'Ref($close, 5)',

    # 收益率序列
    '($close / Ref($close, 1) - 1)',
    '(Ref($close, 1) / Ref($close, 2) - 1)',
    '(Ref($close, 2) / Ref($close, 3) - 1)',

    # 均線序列
    'Mean($close, 5)', 'Mean($close, 10)', 'Mean($close, 20)',

    # 波動率序列
    'Std($close, 5)', 'Std($close, 10)', 'Std($close, 20)',

    # 成交量序列
    '$volume / Mean($volume, 5)',
]

# ========== 簡化策略（模擬 LSTM 行為）==========
# 使用多時間尺度動量組合模擬 LSTM 的時序記憶能力

# 短期趨勢（LSTM 短期記憶）
short_term = df['($close / Ref($close, 1) - 1)']
ma5 = df['Mean($close, 5)']
trend_short = (df['$close'] > ma5).astype(int) * 2 - 1

# 中期趨勢（LSTM 中期記憶）
ma10 = df['Mean($close, 10)']
ma20 = df['Mean($close, 20)']
trend_mid = (ma10 > ma20).astype(int) * 2 - 1

# 長期趨勢（LSTM 長期記憶）
vol_5d = df['Std($close, 5)']
vol_20d = df['Std($close, 20)']
vol_stable = (vol_5d < vol_20d).astype(int)  # 波動率穩定性

# 成交量確認（LSTM 輔助特徵）
volume_confirm = (df['$volume / Mean($volume, 5)'] > 1).astype(int)

# ========== 模擬 LSTM 決策 ==========
# LSTM 會給不同時間尺度賦予不同權重
weight_short = 0.4
weight_mid = 0.35
weight_long = 0.25

lstm_score = (
    weight_short * trend_short +
    weight_mid * trend_mid +
    weight_long * vol_stable
)

# 結合成交量確認
lstm_score = lstm_score * (0.5 + 0.5 * volume_confirm)

# ========== 信號生成 ==========
signals = pd.Series(0, index=df.index)

# 買入：LSTM 預測上漲（綜合評分高）
buy_threshold = lstm_score.quantile(0.65)
signals[lstm_score > buy_threshold] = 1

# 賣出：LSTM 預測下跌（綜合評分低）
sell_threshold = lstm_score.quantile(0.35)
signals[lstm_score < sell_threshold] = -1

print(f"\\nLSTM 模擬評分統計:")
print(f"  平均分數: {lstm_score.mean():.4f}")
print(f"  標準差: {lstm_score.std():.4f}")
print(f"  買入閾值: {buy_threshold:.4f}")
print(f"  賣出閾值: {sell_threshold:.4f}")

print(f"\\n買入信號: {(signals == 1).sum()}")
print(f"賣出信號: {(signals == -1).sum()}")

print("\\n💡 提示：")
print("  實際 LSTM 模型需要：")
print("  1. 安裝 TensorFlow 或 PyTorch")
print("  2. 準備時序數據（序列窗口）")
print("  3. 設計網絡架構（輸入層、LSTM層、輸出層）")
print("  4. 訓練模型並保存權重")
print("="*60)
`,
  },

  {
    id: 'transformer_attention',
    name: 'Transformer 注意力機制',
    description: '使用 Transformer 架構和多頭注意力機制捕捉複雜模式',
    icon: '✨',
    tags: ['Transformer', '注意力', '最先進'],
    code: `# Transformer 注意力機制模型
# 使用自注意力機制捕捉長程依賴

import pandas as pd
import numpy as np

print("="*60)
print("✨ Transformer 注意力機制（框架代碼）")
print("="*60)
print("⚠️  需要安裝 PyTorch 或 TensorFlow")
print("⚠️  以下為簡化版策略，使用多因子模擬注意力機制")

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '$close', '$volume',

    # 多時間尺度特徵（模擬多頭注意力）
    'Mean($close, 5)', 'Mean($close, 10)', 'Mean($close, 20)', 'Mean($close, 60)',

    # 動量特徵（不同窗口）
    '($close / Ref($close, 5) - 1)',
    '($close / Ref($close, 10) - 1)',
    '($close / Ref($close, 20) - 1)',
    '($close / Ref($close, 60) - 1)',

    # 波動率特徵
    'Std($close, 5)', 'Std($close, 20)', 'Std($close, 60)',

    # 成交量特徵
    '$volume / Mean($volume, 5)',
    '$volume / Mean($volume, 20)',

    # 相關性特徵（模擬注意力）
    'Corr($close, $volume, 20)',
    'Corr(Mean($close, 5), Mean($close, 20), 40)',
]

# ========== 模擬多頭注意力機制 ==========
# Transformer 的核心是自注意力，關注不同時間點的重要性

# Head 1: 關注短期動量
head1_query = df['($close / Ref($close, 5) - 1)']
head1_key = df['Mean($close, 5)']
head1_attention = (head1_query - head1_query.mean()) / head1_query.std()

# Head 2: 關注中期趨勢
head2_query = df['($close / Ref($close, 20) - 1)']
head2_key = df['Mean($close, 20)']
head2_attention = (head2_query - head2_query.mean()) / head2_query.std()

# Head 3: 關注長期波動
head3_query = df['Std($close, 60)']
head3_key = df['Std($close, 20)']
head3_attention = (head3_key / head3_query).fillna(0)
head3_attention = (head3_attention - head3_attention.mean()) / head3_attention.std()

# Head 4: 關注成交量
head4_query = df['$volume / Mean($volume, 20)']
head4_attention = (head4_query - head4_query.mean()) / head4_query.std()

# ========== 多頭注意力聚合 ==========
# Transformer 會學習每個 head 的權重
# 這裡使用固定權重模擬

# 計算注意力分數
attention_scores = pd.DataFrame({
    'head1': head1_attention,
    'head2': head2_attention,
    'head3': head3_attention,
    'head4': head4_attention
})

# 多頭加權（模擬 Transformer 的 concat + linear）
weights = [0.3, 0.3, 0.2, 0.2]  # 可學習的權重
transformer_output = sum(w * attention_scores[f'head{i+1}'] for i, w in enumerate(weights))

# ========== 前饋網絡（Feed Forward）==========
# Transformer 的第二部分：position-wise FFN

# Layer 1: 擴展維度並激活
ffn_hidden = transformer_output * 2  # 簡化版擴展
ffn_activated = np.tanh(ffn_hidden)  # ReLU 簡化為 tanh

# Layer 2: 壓縮回原維度
ffn_output = ffn_activated * 0.5

# 殘差連接（Residual Connection）
final_output = transformer_output + ffn_output

# 層歸一化（Layer Normalization）
final_output = (final_output - final_output.mean()) / final_output.std()

# ========== 信號生成 ==========
signals = pd.Series(0, index=df.index)

# 買入：Transformer 輸出高分
buy_threshold = final_output.quantile(0.7)
signals[final_output > buy_threshold] = 1

# 賣出：Transformer 輸出低分
sell_threshold = final_output.quantile(0.3)
signals[final_output < sell_threshold] = -1

print(f"\\nTransformer 輸出統計:")
print(f"  平均值: {final_output.mean():.4f}")
print(f"  標準差: {final_output.std():.4f}")

print(f"\\n多頭注意力權重:")
for i, w in enumerate(weights, 1):
    print(f"  Head {i}: {w}")

print(f"\\n買入信號: {(signals == 1).sum()}")
print(f"賣出信號: {(signals == -1).sum()}")

print("\\n💡 提示：")
print("  實際 Transformer 模型需要：")
print("  1. 安裝 PyTorch (torch.nn.Transformer)")
print("  2. 準備序列數據（batch, seq_len, features）")
print("  3. 實作位置編碼（Positional Encoding）")
print("  4. 訓練自注意力權重和 FFN 參數")
print("  5. 使用 GPU 加速訓練")
print("="*60)
`,
  },

  // ==================== 高級策略（4 個）====================

  {
    id: 'pairs_trading',
    name: '配對交易策略（協整）',
    description: '尋找協整股票對，當價差偏離時進行套利交易',
    icon: '🔗',
    tags: ['配對交易', '套利', '統計'],
    code: `# 配對交易策略（Pairs Trading）
# 使用價格相關性和價差模擬協整關係

import pandas as pd
import numpy as np

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '$close',
    '$volume',

    # 價格序列
    'Ref($close, 1)', 'Ref($close, 5)', 'Ref($close, 10)',

    # 移動平均（作為價格趨勢）
    'Mean($close, 20)', 'Mean($close, 60)',

    # 波動率
    'Std($close, 20)', 'Std($close, 60)',

    # 價格動量
    '($close / Ref($close, 20) - 1)',

    # 成交量
    '$volume / Mean($volume, 20)',
]

# ========== 策略參數 ==========
lookback = 60        # 計算價差的回顧期
entry_zscore = 2.0   # 進場 Z-Score 閾值
exit_zscore = 0.5    # 出場 Z-Score 閾值

print("="*60)
print("🔗 配對交易策略（協整模擬）")
print("="*60)
print("⚠️  注意：實際配對交易需要多股票數據")
print("⚠️  以下為單股票策略，使用價格偏離均值模擬")

# ========== 模擬配對邏輯 ==========
# 在單股票情況下，使用價格相對長期均值的偏離程度

# 基準價格（長期均值）
baseline = df['Mean($close, 60)']

# 當前價格與基準價格的價差
spread = df['$close'] - baseline

# 價差的標準差（滾動窗口）
spread_mean = spread.rolling(lookback).mean()
spread_std = spread.rolling(lookback).std()

# Z-Score（價差標準化）
zscore = (spread - spread_mean) / (spread_std + 1e-6)

# ========== 信號生成 ==========
signals = pd.Series(0, index=df.index)

# 做多信號：價差過度負偏（價格低於均值）
# 預期價格回歸均值（上漲）
long_entry = zscore < -entry_zscore
long_exit = zscore > -exit_zscore

# 做空信號：價差過度正偏（價格高於均值）
# 預期價格回歸均值（下跌）
short_entry = zscore > entry_zscore
short_exit = zscore < exit_zscore

# 狀態追蹤
position = 0  # 0=空倉, 1=多頭, -1=空頭

for i in range(len(signals)):
    if position == 0:
        # 空倉：尋找進場信號
        if long_entry.iloc[i]:
            signals.iloc[i] = 1
            position = 1
        elif short_entry.iloc[i]:
            signals.iloc[i] = -1
            position = -1
    elif position == 1:
        # 多頭：尋找出場信號
        if long_exit.iloc[i]:
            signals.iloc[i] = 0
            position = 0
        else:
            signals.iloc[i] = 1  # 持有
    elif position == -1:
        # 空頭：尋找出場信號
        if short_exit.iloc[i]:
            signals.iloc[i] = 0
            position = 0
        else:
            signals.iloc[i] = -1  # 持有

print(f"\\n價差統計:")
print(f"  平均值: {spread_mean.mean():.4f}")
print(f"  標準差: {spread_std.mean():.4f}")
print(f"  Z-Score 範圍: [{zscore.min():.2f}, {zscore.max():.2f}]")

print(f"\\n交易信號:")
print(f"  做多進場: {long_entry.sum()}")
print(f"  做空進場: {short_entry.sum()}")
print(f"  總交易: {(signals != 0).sum()}")

print("\\n💡 提示：")
print("  實際配對交易需要：")
print("  1. 選擇兩支協整股票（Engle-Granger 檢驗）")
print("  2. 計算對沖比率（hedge ratio）")
print("  3. 監控價差（spread = stock1 - hedge_ratio * stock2）")
print("  4. 根據 Z-Score 進行套利")
print("="*60)
`,
  },

  {
    id: 'event_driven',
    name: '事件驅動策略',
    description: '基於財報公告、重大事件的價格反應策略',
    icon: '📰',
    tags: ['事件驅動', '財報', '進階'],
    code: `# 事件驅動策略（Event-Driven Strategy）
# 捕捉價格異常波動和成交量異常

import pandas as pd
import numpy as np

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '$close', '$volume', '$high', '$low',

    # 價格跳空（Gap）
    '($open / Ref($close, 1) - 1)',  # 開盤跳空幅度

    # 單日波動率
    '($high - $low) / $close',  # 日內振幅

    # 價格動量
    '($close / Ref($close, 1) - 1)',  # 日收益率
    '($close / Ref($close, 5) - 1)',  # 週收益率

    # 成交量異常
    '$volume / Mean($volume, 20)',  # 成交量比率
    '$volume / Mean($volume, 60)',

    # 波動率異常
    'Std($close / Ref($close, 1) - 1, 5)',   # 短期波動
    'Std($close / Ref($close, 1) - 1, 20)',  # 中期波動
]

# ========== 策略參數 ==========
volume_threshold = 2.0    # 成交量異常閾值（2倍均值）
volatility_threshold = 1.5  # 波動率異常閾值
momentum_threshold = 0.03  # 動量閾值（3%）

print("="*60)
print("📰 事件驅動策略")
print("="*60)
print("⚠️  捕捉價格和成交量異常，模擬事件驅動交易")

# ========== 事件檢測 ==========

# 1. 成交量異常（可能是財報、公告）
volume_ratio = df['$volume / Mean($volume, 20)']
volume_spike = volume_ratio > volume_threshold

# 2. 波動率異常（重大事件）
vol_5d = df['Std($close / Ref($close, 1) - 1, 5)']
vol_20d = df['Std($close / Ref($close, 1) - 1, 20)']
volatility_spike = vol_5d > volatility_threshold * vol_20d

# 3. 價格跳空（隔夜消息）
price_return = df['($close / Ref($close, 1) - 1)']
price_gap = abs(price_return) > momentum_threshold

# 4. 日內振幅異常
daily_range = df['($high - $low) / $close']
range_mean = daily_range.rolling(20).mean()
range_spike = daily_range > 1.5 * range_mean

# ========== 事件綜合評分 ==========
# 多個異常指標同時出現 = 高確信度事件

event_score = (
    volume_spike.astype(int) * 2 +      # 成交量最重要
    volatility_spike.astype(int) * 1.5 +
    price_gap.astype(int) * 1 +
    range_spike.astype(int) * 1
)

# ========== 信號生成 ==========
signals = pd.Series(0, index=df.index)

# 事件驅動買入：
# 1. 事件綜合評分高
# 2. 價格上漲（正面事件）
# 3. 後續動量確認
event_threshold = event_score.quantile(0.8)
positive_event = (event_score > event_threshold) & (price_return > 0)

# 買入信號：正面事件後的動量跟隨
signals[positive_event] = 1

# 賣出信號：負面事件或事件消退
negative_event = (event_score > event_threshold) & (price_return < -momentum_threshold)
signals[negative_event] = -1

# 事件後持有期（3-5天）
holding_period = 5
for i in range(len(signals)):
    if signals.iloc[i] == 1:
        # 買入後持有幾天
        for j in range(1, holding_period + 1):
            if i + j < len(signals) and signals.iloc[i + j] == 0:
                signals.iloc[i + j] = 1

print(f"\\n事件檢測統計:")
print(f"  成交量異常: {volume_spike.sum()}")
print(f"  波動率異常: {volatility_spike.sum()}")
print(f"  價格跳空: {price_gap.sum()}")
print(f"  日內振幅異常: {range_spike.sum()}")

print(f"\\n交易信號:")
print(f"  正面事件買入: {positive_event.sum()}")
print(f"  負面事件賣出: {negative_event.sum()}")
print(f"  總信號數: {(signals != 0).sum()}")

print("\\n💡 提示：")
print("  實際事件驅動策略需要：")
print("  1. 財報日歷（earnings calendar）")
print("  2. 新聞情緒分析（NLP）")
print("  3. 公司公告數據")
print("  4. 行業事件追蹤")
print("="*60)
`,
  },

  {
    id: 'sector_rotation',
    name: '行業輪動策略',
    description: '基於經濟週期和行業動量的輪動配置',
    icon: '🔄',
    tags: ['行業輪動', '宏觀', '配置'],
    code: `# 行業輪動策略（Sector Rotation）
# 使用相對強度和動量進行行業選擇

import pandas as pd
import numpy as np

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '$close', '$volume',

    # 多週期動量（行業輪動關鍵指標）
    '($close / Ref($close, 20) - 1)',   # 1個月動量
    '($close / Ref($close, 60) - 1)',   # 3個月動量
    '($close / Ref($close, 126) - 1)',  # 6個月動量
    '($close / Ref($close, 252) - 1)',  # 12個月動量

    # 相對強度（RS）
    'Mean($close / Ref($close, 1) - 1, 20)',  # 20日平均收益率

    # 趨勢強度
    'Corr($close, Sequence(60), 60)',  # 價格與時間相關性

    # 波動率（風險調整）
    'Std($close / Ref($close, 1) - 1, 60)',

    # 成交量趨勢
    'Mean($volume, 20) / Mean($volume, 60)',
]

# ========== 策略參數 ==========
momentum_weight = 0.4      # 動量權重
trend_weight = 0.3         # 趨勢權重
volume_weight = 0.2        # 成交量權重
volatility_weight = 0.1    # 波動率權重（反向）

print("="*60)
print("🔄 行業輪動策略")
print("="*60)
print("⚠️  單股票版本，使用相對強度模擬行業輪動")

# ========== 計算相對強度 ==========

# 1. 多週期動量綜合評分
mom_1m = df['($close / Ref($close, 20) - 1)']
mom_3m = df['($close / Ref($close, 60) - 1)']
mom_6m = df['($close / Ref($close, 126) - 1)']
mom_12m = df['($close / Ref($close, 252) - 1)']

# 動量綜合得分（權重遞減）
momentum_score = (
    0.1 * mom_1m +
    0.2 * mom_3m +
    0.3 * mom_6m +
    0.4 * mom_12m
)

# 標準化
momentum_z = (momentum_score - momentum_score.mean()) / momentum_score.std()

# 2. 趨勢強度（價格與時間序列相關性）
trend_strength = df['Corr($close, Sequence(60), 60)']
trend_z = (trend_strength - trend_strength.mean()) / trend_strength.std()

# 3. 成交量趨勢（資金流入）
volume_trend = df['Mean($volume, 20) / Mean($volume, 60)']
volume_z = (volume_trend - volume_trend.mean()) / volume_trend.std()

# 4. 波動率（風險，反向評分）
volatility = df['Std($close / Ref($close, 1) - 1, 60)']
volatility_score = 1 / (1 + volatility)  # 低波動率得高分
volatility_z = (volatility_score - volatility_score.mean()) / volatility_score.std()

# ========== 行業評分（綜合相對強度）==========
sector_score = (
    momentum_weight * momentum_z +
    trend_weight * trend_z +
    volume_weight * volume_z +
    volatility_weight * volatility_z
)

# ========== 輪動信號 ==========
signals = pd.Series(0, index=df.index)

# 買入：相對強度高（領漲行業）
strong_threshold = sector_score.quantile(0.7)
signals[sector_score > strong_threshold] = 1

# 賣出：相對強度低（落後行業）
weak_threshold = sector_score.quantile(0.3)
signals[sector_score < weak_threshold] = -1

# 輪動頻率控制（避免過度交易）
# 每月評估一次（20個交易日）
for i in range(0, len(signals), 20):
    chunk = signals.iloc[i:i+20]
    if len(chunk) > 0:
        # 該月份使用第一個交易日的信號
        monthly_signal = chunk.iloc[0]
        signals.iloc[i:i+20] = monthly_signal

print(f"\\n相對強度統計:")
print(f"  動量得分: {momentum_score.mean():.4f} ± {momentum_score.std():.4f}")
print(f"  趨勢強度: {trend_strength.mean():.4f}")
print(f"  成交量趨勢: {volume_trend.mean():.4f}")

print(f"\\n輪動信號:")
print(f"  強勢持有: {(signals == 1).sum()}")
print(f"  弱勢避開: {(signals == -1).sum()}")
print(f"  中性觀望: {(signals == 0).sum()}")

print("\\n💡 提示：")
print("  實際行業輪動需要：")
print("  1. 多行業股票池（至少 5-10 個行業）")
print("  2. 計算每個行業的相對強度")
print("  3. 選擇前 N 強行業配置")
print("  4. 定期再平衡（月度或季度）")
print("="*60)
`,
  },

  {
    id: 'market_neutral',
    name: '市場中性策略',
    description: '多空對沖，消除市場風險，賺取 Alpha 收益',
    icon: '⚖️',
    tags: ['市場中性', '對沖', 'Alpha'],
    code: `# 市場中性策略（Market Neutral）
# 同時持有多頭和空頭，對沖市場風險

import pandas as pd
import numpy as np

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '$close', '$volume',

    # Alpha 因子（超額收益來源）
    # 1. 動量因子
    '($close / Ref($close, 20) - 1)',

    # 2. 反轉因子
    '($close / Ref($close, 5) - 1)',

    # 3. 波動率因子
    'Std($close / Ref($close, 1) - 1, 20)',

    # 4. 成交量因子
    '$volume / Mean($volume, 20)',

    # 5. 價值因子（價格相對均值）
    '$close / Mean($close, 60)',

    # Beta（市場敏感度）- 使用相關性模擬
    'Corr($close / Ref($close, 1) - 1, Mean($close, 5) / Ref(Mean($close, 5), 1) - 1, 60)',

    # 均線偏離
    '($close - Mean($close, 20)) / Std($close, 20)',
]

# ========== 策略參數 ==========
alpha_threshold = 0.5  # Alpha 評分閾值
target_beta = 0.0      # 目標 Beta（市場中性）
rebalance_days = 20    # 再平衡週期

print("="*60)
print("⚖️  市場中性策略")
print("="*60)
print("⚠️  單股票版本，使用動態多空平衡模擬")

# ========== Alpha 計算 ==========

# 多因子 Alpha 模型
momentum = df['($close / Ref($close, 20) - 1)']
reversal = -df['($close / Ref($close, 5) - 1)']  # 反轉（負號）
volatility = 1 / (1 + df['Std($close / Ref($close, 1) - 1, 20)'])  # 低波動
volume = df['$volume / Mean($volume, 20)']
value = 1 / df['$close / Mean($close, 60)']  # 低估值

# 標準化
momentum_z = (momentum - momentum.mean()) / momentum.std()
reversal_z = (reversal - reversal.mean()) / reversal.std()
volatility_z = (volatility - volatility.mean()) / volatility.std()
volume_z = (volume - volume.mean()) / volume.std()
value_z = (value - value.mean()) / value.std()

# Alpha 綜合評分（權重可調）
alpha = (
    0.3 * momentum_z +
    0.2 * reversal_z +
    0.2 * volatility_z +
    0.15 * volume_z +
    0.15 * value_z
)

# ========== Beta 計算（市場敏感度）==========
# 簡化版：使用價格與均線的相關性
market_proxy = df['Mean($close, 5)'] / df['Ref(Mean($close, 5), 1)'] - 1
stock_return = df['$close'] / df['Ref($close, 1)'] - 1

beta = df['Corr($close / Ref($close, 1) - 1, Mean($close, 5) / Ref(Mean($close, 5), 1) - 1, 60)']

# ========== 市場中性倉位 ==========
# 根據 Alpha 和 Beta 計算多空比例

signals = pd.Series(0, index=df.index)

# Alpha 高：做多（預期超額收益）
# Alpha 低：做空（預期低於市場）
long_signal = alpha > alpha_threshold
short_signal = alpha < -alpha_threshold

# 多頭倉位（正 Alpha）
signals[long_signal] = 1

# 空頭倉位（負 Alpha）
signals[short_signal] = -1

# ========== Beta 中性調整 ==========
# 理想情況下，多頭 Beta 和空頭 Beta 應相等（市場中性）
# 單股票策略：使用持倉比例調整

# 計算滾動 Beta 均值
rolling_beta = beta.rolling(20).mean()

# 如果 Beta 過高，降低多頭或增加空頭
high_beta = rolling_beta > 0.5
low_beta = rolling_beta < -0.5

# Beta 調整（簡化版）
signals[high_beta & (signals == 1)] = 0.5   # 降低多頭倉位
signals[low_beta & (signals == -1)] = -0.5  # 降低空頭倉位

# ========== 定期再平衡 ==========
# 每 N 天重新評估 Alpha 和調整倉位
for i in range(0, len(signals), rebalance_days):
    chunk = signals.iloc[i:i+rebalance_days]
    if len(chunk) > 0:
        # 使用該期間第一個交易日的信號
        period_signal = chunk.iloc[0]
        signals.iloc[i:i+rebalance_days] = period_signal

print(f"\\nAlpha 統計:")
print(f"  平均值: {alpha.mean():.4f}")
print(f"  標準差: {alpha.std():.4f}")
print(f"  範圍: [{alpha.min():.2f}, {alpha.max():.2f}]")

print(f"\\nBeta 統計:")
print(f"  平均值: {beta.mean():.4f}")
print(f"  標準差: {beta.std():.4f}")

print(f"\\n持倉分布:")
print(f"  多頭: {(signals > 0).sum()}")
print(f"  空頭: {(signals < 0).sum()}")
print(f"  中性: {(signals == 0).sum()}")
print(f"  淨暴露: {signals.sum() / len(signals):.2%}")

print("\\n💡 提示：")
print("  實際市場中性策略需要：")
print("  1. 股票池（至少 50-100 支）")
print("  2. 計算每支股票的 Alpha 和 Beta")
print("  3. 構建多頭組合（高 Alpha）和空頭組合（低 Alpha）")
print("  4. 調整倉位使組合 Beta ≈ 0")
print("  5. 使用槓桿或衍生品對沖市場風險")
print("="*60)
`,
  },
]

function selectTemplate(template: any, mode: 'replace' | 'factor' | 'append') {
  emit('select', {
    code: template.code,
    mode: mode,
    template: template
  })
}
</script>

<style scoped>
.templates-container {
  margin-bottom: 1.5rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
}

.templates-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
}

.templates-subtitle {
  font-size: 0.875rem;
  opacity: 0.9;
  margin: 0 0 1.5rem 0;
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.template-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.template-card:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
}

.template-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.template-icon {
  font-size: 1.75rem;
}

.template-name {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}

.template-description {
  font-size: 0.875rem;
  line-height: 1.5;
  opacity: 0.9;
  margin: 0 0 0.75rem 0;
}

.template-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag {
  font-size: 0.75rem;
  padding: 0.25rem 0.75rem;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  font-weight: 500;
}

.template-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-insert {
  width: 100%;
  padding: 0.5rem 0.75rem;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.btn-replace {
  background-color: #ef4444;
}

.btn-replace:hover {
  background-color: #dc2626;
}

.btn-factor {
  background-color: #3b82f6;
}

.btn-factor:hover {
  background-color: #2563eb;
}

.btn-append {
  background-color: #6b7280;
}

.btn-append:hover {
  background-color: #4b5563;
}
</style>
