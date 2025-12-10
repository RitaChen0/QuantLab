<template>
  <div class="factor-templates">
    <h3>🧬 因子策略範本庫</h3>
    <p class="description">基於 RD-Agent 生成的量化因子，一鍵插入可執行的 Backtrader 策略代碼</p>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>載入因子範本...</p>
    </div>

    <div v-else-if="templates.length === 0" class="empty">
      <p>⚠️ 尚未生成任何因子，請先執行 RD-Agent 因子挖掘任務</p>
      <NuxtLink to="/rdagent" class="btn-primary">前往 RD-Agent</NuxtLink>
    </div>

    <div v-else class="templates-grid">
      <div
        v-for="template in templates"
        :key="template.id"
        class="template-card"
        @click="selectTemplate(template)"
      >
        <div class="template-header">
          <div class="template-icon">📊</div>
          <div class="template-info">
            <h4>{{ template.name }}</h4>
            <span class="badge">{{ template.category }}</span>
          </div>
        </div>

        <div class="template-description">
          <p>{{ template.description }}</p>
        </div>

        <div class="template-formula">
          <strong>公式：</strong>
          <code>{{ template.formula_preview }}</code>
        </div>

        <div class="template-tags">
          <span class="tag" v-for="tag in template.tags" :key="tag">{{ tag }}</span>
        </div>

        <div class="template-actions">
          <button
            type="button"
            class="btn-insert btn-replace"
            @click.stop="insertTemplate(template, 'replace')"
            title="完全替換編輯器中的代碼"
          >
            🔄 替換策略
          </button>
          <button
            type="button"
            class="btn-insert btn-factor"
            @click.stop="insertTemplate(template, 'factor')"
            title="只插入因子計算邏輯"
          >
            ⭐ 插入因子
          </button>
          <button
            type="button"
            class="btn-insert btn-append"
            @click.stop="insertTemplate(template, 'append')"
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
import { ref, onMounted } from 'vue'
import { useRuntimeConfig } from '#app'

const config = useRuntimeConfig()
const emit = defineEmits(['select'])

// 接收引擎類型 prop
const props = defineProps({
  engineType: {
    type: String,
    default: 'qlib'  // 預設為 Qlib，因為 RD-Agent 因子主要用於 Qlib
  }
})

interface FactorTemplate {
  id: number
  name: string
  description: string
  formula: string
  formula_preview: string
  category: string
  code: string
  strategy_code: string
  tags: string[]
}

const loading = ref(true)
const templates = ref<FactorTemplate[]>([])

const fetchFactorTemplates = async () => {
  try {
    loading.value = true
    const token = localStorage.getItem('access_token')

    const response = await fetch(`${config.public.apiBase}/api/v1/rdagent/factors`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) {
      throw new Error('Failed to fetch factors')
    }

    const factors = await response.json()

    // 為每個因子生成策略範本
    templates.value = factors.map((factor: any) => generateStrategyTemplate(factor))

  } catch (error) {
    console.error('載入因子範本失敗:', error)
    templates.value = []
  } finally {
    loading.value = false
  }
}

const generateStrategyTemplate = (factor: any): FactorTemplate => {
  // 根據引擎類型和因子類型生成對應的策略代碼
  let strategyCode = ''
  let tags = [factor.category || 'momentum']

  // ========== 根據引擎類型生成策略 ==========
  if (props.engineType === 'qlib') {
    // Qlib 引擎：生成 Qlib 策略代碼
    strategyCode = generateQlibStrategy(factor)
    tags.push('Qlib', '表達式引擎')
  } else {
    // Backtrader 引擎：根據因子類型生成對應策略
    if (factor.name.toLowerCase().includes('sma') || factor.name.toLowerCase().includes('moving')) {
      strategyCode = generateSMAStrategy(factor)
      tags.push('趨勢跟隨', 'SMA')
    } else if (factor.name.toLowerCase().includes('momentum')) {
      strategyCode = generateMomentumStrategy(factor)
      tags.push('動量', '反轉')
    } else if (factor.name.toLowerCase().includes('volume')) {
      strategyCode = generateVolumeWeightedStrategy(factor)
      tags.push('成交量', '加權')
    } else {
      strategyCode = generateGenericFactorStrategy(factor)
      tags.push('通用因子')
    }
  }

  return {
    id: factor.id,
    name: factor.name,
    description: factor.description || `基於 ${factor.name} 因子的量化策略`,
    formula: factor.formula,
    formula_preview: factor.formula.length > 50 ? factor.formula.substring(0, 50) + '...' : factor.formula,
    category: factor.category || 'momentum',
    code: factor.code || '',
    strategy_code: strategyCode,
    tags
  }
}

// === 策略生成函數 ===

const generateSMAStrategy = (factor: any) => {
  const period = extractPeriod(factor.name, factor.formula) || 20

  return `import backtrader as bt

class ${toPascalCase(factor.name)}Strategy(bt.Strategy):
    """
    ${factor.name} 策略

    策略邏輯：
    - 使用 ${period} 日簡單移動平均線 (SMA)
    - 當價格突破 SMA 上方時買入
    - 當價格跌破 SMA 下方時賣出

    因子公式：${factor.formula}
    """

    params = (
        ('sma_period', ${period}),        # SMA 週期
        ('printlog', True),               # 是否列印日誌
    )

    def __init__(self):
        # 計算 SMA 因子
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close,
            period=self.params.sma_period
        )

        # 交叉信號
        self.crossover = bt.indicators.CrossOver(self.data.close, self.sma)

    def next(self):
        if not self.position:
            # 價格突破 SMA，買入信號
            if self.crossover > 0:
                self.buy()
                if self.params.printlog:
                    print(f'{self.data.datetime.date()}: BUY at {self.data.close[0]:.2f}')
        else:
            # 價格跌破 SMA，賣出信號
            if self.crossover < 0:
                self.sell()
                if self.params.printlog:
                    print(f'{self.data.datetime.date()}: SELL at {self.data.close[0]:.2f}')

    def stop(self):
        if self.params.printlog:
            print(f'最終資產: {self.broker.getvalue():.2f}')`
}

const generateMomentumStrategy = (factor: any) => {
  const period = extractPeriod(factor.name, factor.formula) || 10

  return `import backtrader as bt

class ${toPascalCase(factor.name)}Strategy(bt.Strategy):
    """
    ${factor.name} 動量策略

    策略邏輯：
    - 計算 ${period} 日價格動量 (價格變化百分比)
    - 動量 > 閾值時買入 (正向動量)
    - 動量 < 負閾值時賣出 (負向動量)

    因子公式：${factor.formula}
    """

    params = (
        ('momentum_period', ${period}),   # 動量計算週期
        ('buy_threshold', 0.05),          # 買入閾值 (5%)
        ('sell_threshold', -0.05),        # 賣出閾值 (-5%)
        ('printlog', True),
    )

    def __init__(self):
        # 計算 ${period} 日動量因子
        self.momentum = (
            (self.data.close - self.data.close(-self.params.momentum_period)) /
            self.data.close(-self.params.momentum_period)
        )

    def next(self):
        # 確保有足夠的歷史數據
        if len(self.data) < self.params.momentum_period:
            return

        current_momentum = self.momentum[0]

        if not self.position:
            # 正向動量超過閾值，買入
            if current_momentum > self.params.buy_threshold:
                self.buy()
                if self.params.printlog:
                    print(f'{self.data.datetime.date()}: BUY - Momentum: {current_momentum:.2%}')
        else:
            # 負向動量超過閾值，賣出
            if current_momentum < self.params.sell_threshold:
                self.sell()
                if self.params.printlog:
                    print(f'{self.data.datetime.date()}: SELL - Momentum: {current_momentum:.2%}')

    def stop(self):
        if self.params.printlog:
            print(f'最終資產: {self.broker.getvalue():.2f}')`
}

const generateVolumeWeightedStrategy = (factor: any) => {
  const period = extractPeriod(factor.name, factor.formula) || 10

  return `import backtrader as bt
import numpy as np

class ${toPascalCase(factor.name)}Strategy(bt.Strategy):
    """
    ${factor.name} 成交量加權策略

    策略邏輯：
    - 計算成交量加權動量因子
    - 考慮價格變化與成交量的關係
    - 高成交量支撐的價格變動更可信

    因子公式：${factor.formula}
    """

    params = (
        ('period', ${period}),            # 計算週期
        ('signal_threshold', 0.0),        # 信號閾值
        ('printlog', True),
    )

    def __init__(self):
        # 用於儲存歷史數據
        self.prices = []
        self.volumes = []

    def next(self):
        # 收集數據
        self.prices.append(self.data.close[0])
        self.volumes.append(self.data.volume[0])

        # 保持固定長度
        if len(self.prices) > self.params.period:
            self.prices.pop(0)
            self.volumes.pop(0)

        # 確保有足夠數據
        if len(self.prices) < self.params.period:
            return

        # 計算成交量加權價格
        prices_array = np.array(self.prices)
        volumes_array = np.array(self.volumes)

        vwap = np.sum(prices_array * volumes_array) / np.sum(volumes_array)

        # 計算相對於 VWAP 的偏離
        deviation = (self.data.close[0] - vwap) / vwap

        if not self.position:
            # VWAP 上方且有成交量支撐，買入
            if deviation > self.params.signal_threshold and self.data.volume[0] > np.mean(volumes_array):
                self.buy()
                if self.params.printlog:
                    print(f'{self.data.datetime.date()}: BUY - VWAP偏離: {deviation:.2%}')
        else:
            # VWAP 下方，賣出
            if deviation < -self.params.signal_threshold:
                self.sell()
                if self.params.printlog:
                    print(f'{self.data.datetime.date()}: SELL - VWAP偏離: {deviation:.2%}')

    def stop(self):
        if self.params.printlog:
            print(f'最終資產: {self.broker.getvalue():.2f}')`
}

const generateGenericFactorStrategy = (factor: any) => {
  return `import backtrader as bt

class ${toPascalCase(factor.name)}Strategy(bt.Strategy):
    """
    ${factor.name} 因子策略

    描述：${factor.description || '基於量化因子的交易策略'}

    因子公式：${factor.formula}

    策略邏輯：
    - 使用因子值作為交易信號
    - 因子值 > 閾值時買入
    - 因子值 < 負閾值時賣出
    """

    params = (
        ('signal_threshold', 0.0),        # 信號閾值
        ('printlog', True),
    )

    def __init__(self):
        # TODO: 在此實作因子計算邏輯
        # 完整的因子代碼請參考「自動研發」頁面的因子詳情

        self.factor_value = None  # 替換為實際因子計算

    def next(self):
        # 確保因子已計算
        if self.factor_value is None:
            return

        if not self.position:
            if self.factor_value > self.params.signal_threshold:
                self.buy()
        else:
            if self.factor_value < -self.params.signal_threshold:
                self.sell()

    def stop(self):
        if self.params.printlog:
            print(f'最終資產: {self.broker.getvalue():.2f}')`
}

// === Qlib 策略生成函數 ===

const generateQlibStrategy = (factor: any) => {
  return `"""
${factor.name} - Qlib 策略

因子公式：${factor.formula}
描述：${factor.description || '基於量化因子的交易策略'}

✅ 此策略使用 Qlib 表達式引擎，直接使用因子公式
"""

import pandas as pd
import numpy as np

# ========== Qlib 表達式字段 ==========
QLIB_FIELDS = [
    '${factor.formula}',  # 原始因子公式
]

# ========== 策略邏輯：直接生成交易信號 ==========

# 檢查 df 是否包含因子欄位
if '${factor.formula}' in df.columns:
    factor_col = '${factor.formula}'
else:
    # Fallback: 使用第一個非基礎欄位
    base_cols = ['$open', '$high', '$low', '$close', '$volume', '$factor']
    factor_col = [col for col in df.columns if col not in base_cols][0] if len(df.columns) > len(base_cols) else '$close'

# 初始化信號
signals = pd.Series(0, index=df.index)

# 計算分位數閾值（可調整）
buy_threshold = 0.7   # 買入閾值：因子值 > 70% 分位數
sell_threshold = 0.3  # 賣出閾值：因子值 < 30% 分位數

threshold_high = df[factor_col].quantile(buy_threshold)
threshold_low = df[factor_col].quantile(sell_threshold)

# 買入信號：因子值 > 高閾值
signals[df[factor_col] > threshold_high] = 1

# 賣出信號：因子值 < 低閾值
signals[df[factor_col] < threshold_low] = -1

# 調試信息
print(f"✅ 因子: ${factor.name}")
print(f"✅ 使用欄位: {factor_col}")
print(f"✅ 高閾值 (買入): {threshold_high:.4f}")
print(f"✅ 低閾值 (賣出): {threshold_low:.4f}")
print(f"✅ 生成 {len(signals[signals == 1])} 個買入信號")
print(f"✅ 生成 {len(signals[signals == -1])} 個賣出信號")

# ========== 策略參數 ==========
STRATEGY_CONFIG = {
    'factor_name': '${factor.name}',
    'formula': '${factor.formula}',
    'signal_method': 'quantile',
    'buy_threshold': buy_threshold,
    'sell_threshold': sell_threshold,
}`
}

// === 輔助函數 ===

const extractPeriodFromFormula = (formula: string): number | null => {
  // 從 Qlib 公式中提取週期，例如 "Ref($close, 5)" -> 5
  const refMatch = formula.match(/Ref\([^,]+,\s*(\d+)\)/)
  if (refMatch) {
    return parseInt(refMatch[1])
  }

  // 從 Mean/Std 等函數中提取，例如 "Mean($close, 20)" -> 20
  const meanMatch = formula.match(/(?:Mean|Std|Sum|Max|Min)\([^,]+,\s*(\d+)\)/)
  if (meanMatch) {
    return parseInt(meanMatch[1])
  }

  return null
}

const extractPeriod = (name: string, formula?: string): number | null => {
  // 優先從公式中提取
  if (formula) {
    const periodFromFormula = extractPeriodFromFormula(formula)
    if (periodFromFormula) {
      return periodFromFormula
    }
  }

  // 否則從名稱中提取
  const match = name.match(/(\d+)[Dd]ay/)
  return match ? parseInt(match[1]) : null
}

const toPascalCase = (str: string): string => {
  // Python 關鍵字列表
  const PYTHON_KEYWORDS = new Set([
    'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
    'elif', 'else', 'except', 'false', 'finally', 'for', 'from', 'global',
    'if', 'import', 'in', 'is', 'lambda', 'none', 'nonlocal', 'not',
    'or', 'pass', 'raise', 'return', 'true', 'try', 'while', 'with', 'yield'
  ])

  // 常見的內建類型和模組名稱（避免衝突）
  const PYTHON_BUILTINS = new Set([
    'int', 'str', 'list', 'dict', 'set', 'tuple', 'bool', 'float', 'complex',
    'bytes', 'type', 'object', 'super', 'property', 'staticmethod', 'classmethod'
  ])

  // 處理空字串或 null/undefined
  if (!str || typeof str !== 'string' || str.trim().length === 0) {
    return 'DefaultStrategy'
  }

  // 移除前後空白並正規化
  str = str.trim()

  // 處理連續的非字母數字字符（替換為單一底線）
  str = str.replace(/[^a-zA-Z0-9]+/g, '_')

  // 分割並轉換為 PascalCase
  let result = str
    .split('_')
    .filter(s => s.length > 0)
    .map(s => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase())
    .join('')

  // 如果結果為空（所有字符都被過濾掉了）
  if (!result || result.length === 0) {
    return 'DefaultStrategy'
  }

  // 如果結果太短（單字母），添加描述性後綴
  if (result.length === 1) {
    result = result + 'Strategy'
  }

  // 如果結果以數字開頭，添加 "Factor" 前綴
  // Python 類別名稱不能以數字開頭
  if (/^[0-9]/.test(result)) {
    result = 'Factor' + result
  }

  // 如果結果是 Python 關鍵字，添加 "Strategy" 後綴
  const lowerResult = result.toLowerCase()
  if (PYTHON_KEYWORDS.has(lowerResult) || PYTHON_BUILTINS.has(lowerResult)) {
    result = result + 'Strategy'
  }

  // 最終驗證：確保結果是有效的 Python 標識符
  // 必須以字母或底線開頭，後續可以是字母、數字或底線
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(result)) {
    console.warn(`Generated invalid Python identifier: ${result}, using default`)
    return 'DefaultStrategy'
  }

  return result
}

const selectTemplate = (template: FactorTemplate) => {
  // 可以顯示詳細資訊或預覽
  console.log('Selected template:', template)
}

const insertTemplate = (template: FactorTemplate, mode: 'replace' | 'factor' | 'append') => {
  emit('select', {
    code: template.strategy_code,
    mode: mode,
    template: template
  })
}

onMounted(() => {
  fetchFactorTemplates()
})
</script>

<style scoped>
.factor-templates {
  padding: 20px;
}

.factor-templates h3 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
  color: #1a202c;
}

.description {
  color: #718096;
  margin-bottom: 1.5rem;
}

.loading {
  text-align: center;
  padding: 3rem;
}

.spinner {
  border: 4px solid #f3f4f6;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty {
  text-align: center;
  padding: 3rem;
  color: #718096;
}

.btn-primary {
  display: inline-block;
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background-color: #3b82f6;
  color: white;
  text-decoration: none;
  border-radius: 0.375rem;
  transition: background-color 0.2s;
}

.btn-primary:hover {
  background-color: #2563eb;
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.template-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.template-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.template-header {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}

.template-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.template-info h4 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1a202c;
  margin-bottom: 0.25rem;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  background-color: #dbeafe;
  color: #1e40af;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.template-description {
  margin-bottom: 1rem;
  color: #4a5568;
  font-size: 0.875rem;
  line-height: 1.5;
}

.template-formula {
  margin-bottom: 1rem;
  padding: 0.75rem;
  background-color: #f7fafc;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.template-formula strong {
  color: #2d3748;
  display: block;
  margin-bottom: 0.25rem;
}

.template-formula code {
  color: #d97706;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.8125rem;
}

.template-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.tag {
  padding: 0.25rem 0.5rem;
  background-color: #f3f4f6;
  color: #6b7280;
  border-radius: 0.25rem;
  font-size: 0.75rem;
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
