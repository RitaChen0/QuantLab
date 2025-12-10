<template>
  <div class="performance-metrics">
    <!-- 績效總覽 -->
    <div class="metrics-overview">
      <div class="overview-card highlight">
        <div class="overview-icon">💰</div>
        <div class="overview-content">
          <div class="overview-label">總報酬率</div>
          <div :class="['overview-value', totalReturn >= 0 ? 'positive' : 'negative']">
            {{ totalReturn >= 0 ? '+' : '' }}{{ totalReturn.toFixed(2) }}%
          </div>
          <div class="overview-subtitle">
            最終資產：{{ formatCurrency(finalValue) }}
          </div>
        </div>
      </div>

      <div class="overview-card">
        <div class="overview-icon">📈</div>
        <div class="overview-content">
          <div class="overview-label">年化報酬</div>
          <div :class="['overview-value', annualReturn >= 0 ? 'positive' : 'negative']">
            {{ annualReturn >= 0 ? '+' : '' }}{{ annualReturn.toFixed(2) }}%
          </div>
          <div class="overview-subtitle">
            {{ getRatingText(annualReturn, 'return') }}
          </div>
        </div>
      </div>

      <div class="overview-card">
        <div class="overview-icon">⚡</div>
        <div class="overview-content">
          <div class="overview-label">夏普比率</div>
          <div class="overview-value">{{ sharpeRatio.toFixed(2) }}</div>
          <div class="overview-subtitle">
            {{ getRatingText(sharpeRatio, 'sharpe') }}
          </div>
        </div>
      </div>

      <div class="overview-card">
        <div class="overview-icon">📉</div>
        <div class="overview-content">
          <div class="overview-label">最大回撤</div>
          <div class="overview-value negative">{{ Math.abs(maxDrawdown).toFixed(2) }}%</div>
          <div class="overview-subtitle">
            {{ getRatingText(Math.abs(maxDrawdown), 'drawdown') }}
          </div>
        </div>
      </div>
    </div>

    <!-- 詳細指標分類 -->
    <div class="metrics-sections">
      <!-- 報酬指標 -->
      <div class="metrics-section">
        <h3 class="section-title">
          <span class="section-icon">💹</span>
          報酬指標
        </h3>
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-name">總報酬率</span>
              <span class="metric-info" @click="showInfo('total_return')">ⓘ</span>
            </div>
            <div :class="['metric-value', totalReturn >= 0 ? 'positive' : 'negative']">
              {{ totalReturn >= 0 ? '+' : '' }}{{ totalReturn.toFixed(2) }}%
            </div>
          </div>

          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-name">年化報酬率</span>
              <span class="metric-info" @click="showInfo('annual_return')">ⓘ</span>
            </div>
            <div :class="['metric-value', annualReturn >= 0 ? 'positive' : 'negative']">
              {{ annualReturn >= 0 ? '+' : '' }}{{ annualReturn.toFixed(2) }}%
            </div>
          </div>

          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-name">最終資產淨值</span>
              <span class="metric-info" @click="showInfo('final_value')">ⓘ</span>
            </div>
            <div class="metric-value">{{ formatCurrency(finalValue) }}</div>
          </div>
        </div>
      </div>

      <!-- 風險指標 -->
      <div class="metrics-section">
        <h3 class="section-title">
          <span class="section-icon">⚠️</span>
          風險指標
        </h3>
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-name">最大回撤</span>
              <span class="metric-info" @click="showInfo('max_drawdown')">ⓘ</span>
            </div>
            <div class="metric-value negative">{{ Math.abs(maxDrawdown).toFixed(2) }}%</div>
          </div>

          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-name">波動率</span>
              <span class="metric-info" @click="showInfo('volatility')">ⓘ</span>
            </div>
            <div class="metric-value">{{ volatility.toFixed(2) }}%</div>
          </div>

          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-name">夏普比率</span>
              <span class="metric-info" @click="showInfo('sharpe_ratio')">ⓘ</span>
            </div>
            <div class="metric-value">{{ sharpeRatio.toFixed(2) }}</div>
          </div>

          <div class="metric-card" v-if="sortinoRatio !== null">
            <div class="metric-header">
              <span class="metric-name">索提諾比率</span>
              <span class="metric-info" @click="showInfo('sortino_ratio')">ⓘ</span>
            </div>
            <div class="metric-value">{{ sortinoRatio.toFixed(2) }}</div>
          </div>

          <div class="metric-card" v-if="calmarRatio !== null">
            <div class="metric-header">
              <span class="metric-name">卡瑪比率</span>
              <span class="metric-info" @click="showInfo('calmar_ratio')">ⓘ</span>
            </div>
            <div class="metric-value">{{ calmarRatio.toFixed(2) }}</div>
          </div>
        </div>
      </div>

      <!-- 交易統計 -->
      <div class="metrics-section">
        <h3 class="section-title">
          <span class="section-icon">📊</span>
          交易統計
        </h3>
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-name">總交易次數</span>
              <span class="metric-info" @click="showInfo('total_trades')">ⓘ</span>
            </div>
            <div class="metric-value">{{ totalTrades }}</div>
          </div>

          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-name">獲利交易</span>
              <span class="metric-info" @click="showInfo('winning_trades')">ⓘ</span>
            </div>
            <div class="metric-value positive">{{ winningTrades }}</div>
          </div>

          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-name">虧損交易</span>
              <span class="metric-info" @click="showInfo('losing_trades')">ⓘ</span>
            </div>
            <div class="metric-value negative">{{ losingTrades }}</div>
          </div>

          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-name">勝率</span>
              <span class="metric-info" @click="showInfo('win_rate')">ⓘ</span>
            </div>
            <div class="metric-value">{{ winRate.toFixed(2) }}%</div>
          </div>
        </div>
      </div>

      <!-- 獲利分析 -->
      <div class="metrics-section">
        <h3 class="section-title">
          <span class="section-icon">💵</span>
          獲利分析
        </h3>
        <div class="metrics-grid">
          <div class="metric-card" v-if="averageProfit !== null">
            <div class="metric-header">
              <span class="metric-name">平均獲利</span>
              <span class="metric-info" @click="showInfo('average_profit')">ⓘ</span>
            </div>
            <div class="metric-value positive">{{ formatCurrency(averageProfit) }}</div>
          </div>

          <div class="metric-card" v-if="averageLoss !== null">
            <div class="metric-header">
              <span class="metric-name">平均虧損</span>
              <span class="metric-info" @click="showInfo('average_loss')">ⓘ</span>
            </div>
            <div class="metric-value negative">{{ formatCurrency(averageLoss) }}</div>
          </div>

          <div class="metric-card" v-if="profitFactor !== null">
            <div class="metric-header">
              <span class="metric-name">獲利因子</span>
              <span class="metric-info" @click="showInfo('profit_factor')">ⓘ</span>
            </div>
            <div class="metric-value">{{ profitFactor.toFixed(2) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 指標說明 Modal -->
    <div v-if="showInfoModal" class="info-modal-overlay" @click="showInfoModal = false">
      <div class="info-modal" @click.stop>
        <div class="info-modal-header">
          <h3>{{ currentInfo.title }}</h3>
          <button @click="showInfoModal = false" class="btn-close">✕</button>
        </div>
        <div class="info-modal-body">
          <p class="info-description">{{ currentInfo.description }}</p>
          <div class="info-formula" v-if="currentInfo.formula">
            <strong>計算公式：</strong>
            <code>{{ currentInfo.formula }}</code>
          </div>
          <div class="info-interpretation" v-if="currentInfo.interpretation">
            <strong>解讀標準：</strong>
            <ul>
              <li v-for="(item, index) in currentInfo.interpretation" :key="index">{{ item }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Props
interface Props {
  result: {
    total_return: number
    annual_return: number
    final_portfolio_value: number
    sharpe_ratio: number
    max_drawdown: number
    volatility: number
    total_trades: number
    winning_trades: number
    losing_trades: number
    win_rate: number
    average_profit?: number
    average_loss?: number
    profit_factor?: number
    sortino_ratio?: number
    calmar_ratio?: number
    information_ratio?: number
  }
}

const props = defineProps<Props>()

// Computed properties
// 注意：後端返回的百分比欄位是小數格式 (如 1.65 代表 165%)，需要乘以 100 才能顯示為百分比
const totalReturn = computed(() => (props.result.total_return || 0) * 100)
const annualReturn = computed(() => (props.result.annual_return || 0) * 100)
const finalValue = computed(() => props.result.final_portfolio_value || 0)
const sharpeRatio = computed(() => props.result.sharpe_ratio || 0)
const maxDrawdown = computed(() => (props.result.max_drawdown || 0) * 100)
const volatility = computed(() => (props.result.volatility || 0) * 100)
const totalTrades = computed(() => props.result.total_trades || 0)
const winningTrades = computed(() => props.result.winning_trades || 0)
const losingTrades = computed(() => props.result.losing_trades || 0)
const winRate = computed(() => (props.result.win_rate || 0) * 100)
const averageProfit = computed(() => props.result.average_profit || null)
const averageLoss = computed(() => props.result.average_loss || null)
const profitFactor = computed(() => props.result.profit_factor || null)
const sortinoRatio = computed(() => props.result.sortino_ratio || null)
const calmarRatio = computed(() => props.result.calmar_ratio || null)

// Modal state
const showInfoModal = ref(false)
const currentInfo = ref({
  title: '',
  description: '',
  formula: '',
  interpretation: [] as string[]
})

// 指標說明資料
const metricsInfo: Record<string, any> = {
  total_return: {
    title: '總報酬率',
    description: '投資期間內的總報酬百分比，衡量策略的整體獲利能力。',
    formula: '(最終資產 - 初始資本) / 初始資本 × 100%',
    interpretation: [
      '> 0%：策略獲利',
      '= 0%：無獲利無虧損',
      '< 0%：策略虧損'
    ]
  },
  annual_return: {
    title: '年化報酬率',
    description: '將總報酬率換算成年度報酬率，便於與其他投資比較。',
    formula: '(1 + 總報酬率) ^ (365 / 回測天數) - 1',
    interpretation: [
      '> 15%：優秀',
      '10% - 15%：良好',
      '5% - 10%：中等',
      '< 5%：偏低'
    ]
  },
  final_value: {
    title: '最終資產淨值',
    description: '回測結束時的總資產價值，包含現金和持倉市值。',
    formula: '初始資本 + 累計損益',
    interpretation: [
      '越高表示策略獲利越多'
    ]
  },
  max_drawdown: {
    title: '最大回撤',
    description: '資產淨值從最高點到最低點的最大跌幅，衡量策略的最大風險。',
    formula: '(最低點淨值 - 最高點淨值) / 最高點淨值',
    interpretation: [
      '< 10%：風險低',
      '10% - 20%：風險中等',
      '20% - 30%：風險較高',
      '> 30%：風險很高'
    ]
  },
  volatility: {
    title: '波動率（標準差）',
    description: '報酬率的標準差，衡量策略報酬的波動程度。',
    formula: 'sqrt(Σ(報酬率 - 平均報酬率)² / N)',
    interpretation: [
      '< 10%：低波動',
      '10% - 20%：中等波動',
      '> 20%：高波動'
    ]
  },
  sharpe_ratio: {
    title: '夏普比率',
    description: '衡量每承擔一單位風險所獲得的超額報酬，是最常用的風險調整後報酬指標。',
    formula: '(年化報酬率 - 無風險利率) / 年化標準差',
    interpretation: [
      '> 2：非常好',
      '1 - 2：良好',
      '0 - 1：可接受',
      '< 0：不佳'
    ]
  },
  sortino_ratio: {
    title: '索提諾比率',
    description: '類似夏普比率，但只考慮下行波動（虧損的波動），更關注負面風險。',
    formula: '(年化報酬率 - 無風險利率) / 下行標準差',
    interpretation: [
      '> 2：非常好',
      '1 - 2：良好',
      '< 1：需改善'
    ]
  },
  calmar_ratio: {
    title: '卡瑪比率',
    description: '年化報酬率與最大回撤的比值，衡量每承擔一單位最大回撤風險所獲得的報酬。',
    formula: '年化報酬率 / |最大回撤|',
    interpretation: [
      '> 3：優秀',
      '1 - 3：良好',
      '< 1：需改善'
    ]
  },
  total_trades: {
    title: '總交易次數',
    description: '回測期間內的總交易數量（買入和賣出各算一次）。',
    formula: '買入次數 + 賣出次數',
    interpretation: [
      '過多可能增加交易成本',
      '過少可能錯失機會',
      '需與策略特性匹配'
    ]
  },
  winning_trades: {
    title: '獲利交易次數',
    description: '實現獲利的交易數量。',
    interpretation: [
      '與勝率相關',
      '越高表示策略穩定性越好'
    ]
  },
  losing_trades: {
    title: '虧損交易次數',
    description: '實現虧損的交易數量。',
    interpretation: [
      '與勝率相關',
      '需控制在可接受範圍'
    ]
  },
  win_rate: {
    title: '勝率',
    description: '獲利交易次數佔總交易次數的比例。',
    formula: '獲利交易次數 / 總交易次數 × 100%',
    interpretation: [
      '> 60%：高勝率',
      '50% - 60%：中等勝率',
      '40% - 50%：較低勝率（需搭配高盈虧比）',
      '< 40%：低勝率'
    ]
  },
  average_profit: {
    title: '平均獲利',
    description: '每筆獲利交易的平均獲利金額。',
    formula: '總獲利金額 / 獲利交易次數',
    interpretation: [
      '越高越好',
      '應大於平均虧損'
    ]
  },
  average_loss: {
    title: '平均虧損',
    description: '每筆虧損交易的平均虧損金額。',
    formula: '總虧損金額 / 虧損交易次數',
    interpretation: [
      '應小於平均獲利',
      '需嚴格控制'
    ]
  },
  profit_factor: {
    title: '獲利因子',
    description: '總獲利與總虧損的比值，衡量策略的整體獲利能力。',
    formula: '總獲利金額 / |總虧損金額|',
    interpretation: [
      '> 2：優秀',
      '1.5 - 2：良好',
      '1 - 1.5：可接受',
      '< 1：虧損（總虧損>總獲利）'
    ]
  }
}

// 顯示指標說明
const showInfo = (metric: string) => {
  if (metricsInfo[metric]) {
    currentInfo.value = metricsInfo[metric]
    showInfoModal.value = true
  }
}

// 評級文字
const getRatingText = (value: number, type: string) => {
  switch (type) {
    case 'return':
      if (value > 15) return '優秀'
      if (value > 10) return '良好'
      if (value > 5) return '中等'
      return '偏低'
    case 'sharpe':
      if (value > 2) return '非常好'
      if (value > 1) return '良好'
      if (value > 0) return '可接受'
      return '不佳'
    case 'drawdown':
      if (value < 10) return '風險低'
      if (value < 20) return '風險中等'
      if (value < 30) return '風險較高'
      return '風險很高'
    default:
      return ''
  }
}

// 格式化貨幣
const formatCurrency = (value: number) => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('zh-TW', {
    style: 'currency',
    currency: 'TWD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value)
}
</script>

<style scoped lang="scss">
.performance-metrics {
  width: 100%;
}

// 績效總覽
.metrics-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.overview-card {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  &.highlight {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;

    .overview-label,
    .overview-subtitle {
      color: rgba(255, 255, 255, 0.9);
    }

    .overview-value {
      color: white;
    }
  }
}

.overview-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.overview-content {
  flex: 1;
  min-width: 0;
}

.overview-label {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.overview-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  margin-bottom: 0.25rem;

  &.positive {
    color: #10b981;
  }

  &.negative {
    color: #ef4444;
  }
}

.overview-subtitle {
  font-size: 0.75rem;
  color: #9ca3af;
}

// 詳細指標
.metrics-sections {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.metrics-section {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 1rem 0;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e5e7eb;
}

.section-icon {
  font-size: 1.25rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.metric-card {
  background: #f9fafb;
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;

  &:hover {
    border-color: #3b82f6;
    box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
  }
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.metric-name {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.metric-info {
  font-size: 0.875rem;
  color: #9ca3af;
  cursor: pointer;
  padding: 0 0.25rem;
  border-radius: 50%;
  transition: all 0.2s;

  &:hover {
    color: #3b82f6;
    background: #dbeafe;
  }
}

.metric-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #111827;

  &.positive {
    color: #10b981;
  }

  &.negative {
    color: #ef4444;
  }
}

// Modal
.info-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.info-modal {
  background: white;
  border-radius: 0.75rem;
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.info-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;

  h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: #111827;
    margin: 0;
  }
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
  transition: color 0.2s;
  padding: 0.25rem;

  &:hover {
    color: #111827;
  }
}

.info-modal-body {
  padding: 1.5rem;
}

.info-description {
  color: #374151;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.info-formula {
  background: #f3f4f6;
  padding: 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;

  strong {
    display: block;
    margin-bottom: 0.5rem;
    color: #374151;
  }

  code {
    display: block;
    font-family: 'Monaco', 'Courier New', monospace;
    font-size: 0.875rem;
    color: #111827;
    background: white;
    padding: 0.5rem;
    border-radius: 0.25rem;
    border: 1px solid #d1d5db;
  }
}

.info-interpretation {
  strong {
    display: block;
    margin-bottom: 0.5rem;
    color: #374151;
  }

  ul {
    margin: 0;
    padding-left: 1.5rem;

    li {
      color: #6b7280;
      line-height: 1.8;
    }
  }
}

// 響應式
@media (max-width: 768px) {
  .metrics-overview {
    grid-template-columns: 1fr;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
