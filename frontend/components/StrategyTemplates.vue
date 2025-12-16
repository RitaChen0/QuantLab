<template>
  <div class="strategy-templates-enhanced">
    <!-- 標題區 -->
    <div class="templates-header">
      <div>
        <h3>策略範本庫</h3>
        <p class="description">選擇範本快速開始策略開發 - {{ filteredTemplates.length }} 個可用範本</p>
      </div>
      <!-- Phase 2 進階: 比較模式切換按鈕 -->
      <button
        type="button"
        @click="toggleComparisonMode"
        :class="['btn-comparison-mode', { active: comparisonMode }]"
        :aria-pressed="comparisonMode"
        aria-label="切換範本比較模式"
      >
        <span v-if="!comparisonMode">📊 比較模式</span>
        <span v-else>✓ 離開比較</span>
      </button>
    </div>

    <!-- 搜尋和篩選區 -->
    <div class="filters-section">
      <!-- 搜尋框 -->
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜尋範本名稱或描述..."
          class="search-input"
        >
        <span class="search-icon">🔍</span>
      </div>

      <!-- 分類篩選 -->
      <div class="filter-tabs">
        <button
          type="button"
          v-for="cat in categories"
          :key="cat.value"
          @click="selectedCategory = cat.value"
          :class="['filter-tab', { active: selectedCategory === cat.value }]"
        >
          <span class="tab-icon">{{ cat.icon }}</span>
          <span>{{ cat.label }}</span>
        </button>
      </div>

      <!-- 難度篩選 -->
      <div class="difficulty-filter">
        <button
          type="button"
          v-for="diff in difficulties"
          :key="diff.value"
          @click="selectedDifficulty = diff.value"
          :class="['difficulty-btn', diff.value, { active: selectedDifficulty === diff.value }]"
        >
          {{ diff.label }}
        </button>
      </div>
    </div>

    <!-- 範本網格 -->
    <div v-if="filteredTemplates.length > 0" class="templates-grid">
      <div
        v-for="template in filteredTemplates"
        :key="template.id"
        :class="['template-card', { selected: isTemplateSelected(template) }]"
      >
        <!-- Phase 2 進階: 比較模式複選框 -->
        <div v-if="comparisonMode" class="comparison-checkbox">
          <input
            type="checkbox"
            :id="`checkbox-${template.id}`"
            :checked="isTemplateSelected(template)"
            @change="toggleTemplateSelection(template)"
            :aria-label="`選擇 ${template.name} 進行比較`"
          />
          <label :for="`checkbox-${template.id}`"></label>
        </div>

        <div class="card-header">
          <div class="template-icon" :class="template.category">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                :d="template.icon"
              />
            </svg>
          </div>
          <span :class="['difficulty-badge', template.difficulty]">
            {{ getDifficultyLabel(template.difficulty) }}
          </span>
        </div>

        <div class="card-body">
          <h4 class="template-name">{{ template.name }}</h4>
          <p class="template-description">{{ template.description }}</p>

          <!-- 標籤 -->
          <div class="template-tags">
            <span v-for="tag in template.tags" :key="tag" class="tag">
              {{ tag }}
            </span>
          </div>

          <!-- 性能指標（Phase 2 增強） -->
          <div v-if="template.metrics" class="metrics-preview-enhanced">
            <div class="metrics-row-top">
              <div class="metric-item-small">
                <span class="metric-icon">📈</span>
                <div class="metric-content-small">
                  <span class="metric-label-small">年化報酬</span>
                  <span class="metric-value-strong">{{ template.metrics.annualReturn || 'N/A' }}</span>
                </div>
              </div>
              <div class="metric-item-small">
                <span class="metric-icon">⭐</span>
                <div class="metric-content-small">
                  <span class="metric-label-small">夏普比率</span>
                  <span class="metric-value-strong">{{ template.metrics.sharpe }}</span>
                </div>
              </div>
            </div>
            <div class="metrics-row-bottom">
              <div class="metric-item-small">
                <span class="metric-icon">🎯</span>
                <div class="metric-content-small">
                  <span class="metric-label-small">勝率</span>
                  <span class="metric-value-small">{{ template.metrics.winRate || 'N/A' }}</span>
                </div>
              </div>
              <div class="metric-item-small">
                <span class="metric-icon">📉</span>
                <div class="metric-content-small">
                  <span class="metric-label-small">最大回撤</span>
                  <span class="metric-value-small">{{ template.metrics.maxDrawdown || 'N/A' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="card-actions">
          <button
            type="button"
            @click="$emit('select', template.code)"
            class="btn-use"
          >
            ✓ 使用範本
          </button>
          <button
            type="button"
            @click="togglePreview(template.id)"
            class="btn-preview"
          >
            {{ expandedTemplate === template.id ? '▲ 收起' : '▼ 預覽' }}
          </button>
        </div>

        <!-- Phase 2 進階: 查看完整績效按鈕 -->
        <div v-if="template.metrics" class="metrics-action">
          <button
            type="button"
            @click="openMetricsModal(template)"
            class="btn-metrics"
          >
            📊 查看完整績效
          </button>
        </div>

        <!-- 代碼預覽區（展開時顯示） -->
        <div v-if="expandedTemplate === template.id" class="code-preview">
          <div class="preview-header">
            <span>代碼預覽</span>
            <button type="button" @click="copyCode(template.code)" class="btn-copy">
              📋 複製代碼
            </button>
          </div>
          <pre class="code-block"><code>{{ template.code }}</code></pre>
        </div>
      </div>
    </div>

    <!-- 空狀態 -->
    <div v-else class="empty-state">
      <div class="empty-icon">🔍</div>
      <p>沒有找到符合條件的範本</p>
      <button type="button" @click="resetFilters" class="btn-reset">重置篩選條件</button>
    </div>

    <!-- Phase 2 進階: 浮動比較欄 -->
    <div v-if="comparisonMode && selectedTemplatesForComparison.length > 0" class="comparison-bar">
      <div class="comparison-bar-content">
        <div class="comparison-info">
          <span class="comparison-icon">📊</span>
          <span class="comparison-text">
            已選擇 {{ selectedTemplatesForComparison.length }} 個範本
            <span class="comparison-hint">({{ 2 - selectedTemplatesForComparison.length <= 0 ? '可以開始比較' : `還需 ${2 - selectedTemplatesForComparison.length} 個` }})</span>
          </span>
        </div>
        <div class="comparison-actions">
          <button
            type="button"
            @click="openComparisonTable"
            :disabled="selectedTemplatesForComparison.length < 2"
            class="btn-compare"
          >
            開始比較
          </button>
          <button type="button" @click="clearComparison" class="btn-clear">
            清空選擇
          </button>
        </div>
      </div>
    </div>

    <!-- Phase 2 進階: 詳細績效模態框 -->
    <div v-if="showMetricsModal && selectedTemplateForMetrics"
         class="modal-overlay"
         @click="closeMetricsModal"
         role="dialog"
         aria-modal="true"
         aria-labelledby="metrics-modal-title">
      <div class="modal-container" @click.stop>
        <div class="modal-header">
          <div class="modal-title-section">
            <h3 id="metrics-modal-title">{{ selectedTemplateForMetrics.name }}</h3>
            <span :class="['difficulty-badge', selectedTemplateForMetrics.difficulty]">
              {{ getDifficultyLabel(selectedTemplateForMetrics.difficulty) }}
            </span>
          </div>
          <button type="button"
                  @click="closeMetricsModal"
                  class="btn-close"
                  aria-label="關閉詳細績效模態框">✕</button>
        </div>

        <div class="modal-body">
          <!-- 收益指標 -->
          <div class="metrics-category">
            <div class="category-header">
              <span class="category-icon">💰</span>
              <h4>收益指標</h4>
            </div>
            <div class="metrics-grid">
              <div class="metric-card">
                <div class="metric-label">年化報酬</div>
                <div class="metric-value highlight">{{ selectedTemplateForMetrics.metrics?.annualReturn || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">總報酬</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.totalReturn || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">月均報酬</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.monthlyReturn || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">日均報酬</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.dailyReturn || 'N/A' }}</div>
              </div>
            </div>
          </div>

          <!-- 風險指標 -->
          <div class="metrics-category">
            <div class="category-header">
              <span class="category-icon">⚠️</span>
              <h4>風險指標</h4>
            </div>
            <div class="metrics-grid">
              <div class="metric-card">
                <div class="metric-label">夏普比率</div>
                <div class="metric-value highlight">{{ selectedTemplateForMetrics.metrics?.sharpe || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">最大回撤</div>
                <div class="metric-value danger">{{ selectedTemplateForMetrics.metrics?.maxDrawdown || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">年化波動率</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.volatility || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">下行標準差</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.downsideDeviation || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">Calmar Ratio</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.calmarRatio || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">Sortino Ratio</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.sortinoRatio || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">95% VaR</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.var95 || 'N/A' }}</div>
              </div>
            </div>
          </div>

          <!-- 交易指標 -->
          <div class="metrics-category">
            <div class="category-header">
              <span class="category-icon">📈</span>
              <h4>交易指標</h4>
            </div>
            <div class="metrics-grid">
              <div class="metric-card">
                <div class="metric-label">總交易次數</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.totalTrades || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">勝率</div>
                <div class="metric-value highlight">{{ selectedTemplateForMetrics.metrics?.winRate || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">平均獲利</div>
                <div class="metric-value success">{{ selectedTemplateForMetrics.metrics?.avgWin || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">平均虧損</div>
                <div class="metric-value danger">{{ selectedTemplateForMetrics.metrics?.avgLoss || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">平均持倉天數</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.avgHoldingDays || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">最大連續獲利</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.maxConsecutiveWins || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">最大連續虧損</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.maxConsecutiveLosses || 'N/A' }}</div>
              </div>
            </div>
          </div>

          <!-- 綜合評估 -->
          <div class="metrics-category">
            <div class="category-header">
              <span class="category-icon">⭐</span>
              <h4>綜合評估</h4>
            </div>
            <div class="metrics-grid">
              <div class="metric-card">
                <div class="metric-label">盈虧比</div>
                <div class="metric-value highlight">{{ selectedTemplateForMetrics.metrics?.winLossRatio || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">獲利因子</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.profitFactor || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">恢復係數</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.recoveryFactor || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">期望值</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.expectancy || 'N/A' }}</div>
              </div>
              <div class="metric-card">
                <div class="metric-label">風險等級</div>
                <div class="metric-value">{{ selectedTemplateForMetrics.metrics?.risk || 'N/A' }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" @click="$emit('select', selectedTemplateForMetrics.code)" class="btn-use-modal">
            ✓ 使用此範本
          </button>
          <button type="button" @click="closeMetricsModal" class="btn-close-modal">
            關閉
          </button>
        </div>
      </div>
    </div>

    <!-- Phase 2 進階: 比較表格模態框 -->
    <div v-if="showComparisonTable"
         class="modal-overlay"
         @click="closeComparisonTable"
         role="dialog"
         aria-modal="true"
         aria-labelledby="comparison-modal-title">
      <div class="comparison-modal-container" @click.stop>
        <div class="modal-header">
          <div class="modal-title-section">
            <h3 id="comparison-modal-title">範本比較 ({{ selectedTemplatesForComparison.length }} 個)</h3>
          </div>
          <button type="button"
                  @click="closeComparisonTable"
                  class="btn-close"
                  aria-label="關閉範本比較">✕</button>
        </div>

        <div class="comparison-modal-body">
          <div class="comparison-table-wrapper">
            <table class="comparison-table">
              <thead>
                <tr>
                  <th class="metric-name-col">指標</th>
                  <th v-for="template in selectedTemplatesForComparison" :key="template.id" class="template-col">
                    <div class="template-header-cell">
                      <div class="template-name">{{ template.name }}</div>
                      <div class="template-meta">
                        <span :class="['difficulty-badge', template.difficulty]">
                          {{ getDifficultyLabel(template.difficulty) }}
                        </span>
                        <span class="category-badge">{{ template.category }}</span>
                      </div>
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                <!-- 使用 v-for 渲染所有分類和指標 -->
                <template v-for="categoryGroup in comparisonMetrics" :key="categoryGroup.category">
                  <!-- 分類標題行 -->
                  <tr class="category-row">
                    <td colspan="100%" class="category-header-cell">
                      <span class="category-icon">{{ categoryGroup.icon }}</span>
                      {{ categoryGroup.category }}
                    </td>
                  </tr>

                  <!-- 該分類下的所有指標 -->
                  <tr v-for="metric in categoryGroup.metrics" :key="metric.key">
                    <td class="metric-name">{{ metric.label }}</td>
                    <td v-for="template in selectedTemplatesForComparison" :key="template.id"
                        :class="{ 'best-value': isBestValue(metric.key, template.metrics?.[metric.key], selectedTemplatesForComparison) }">
                      {{ template.metrics?.[metric.key] || 'N/A' }}
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" @click="closeComparisonTable" class="btn-close-modal">
            關閉比較
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface StrategyTemplate {
  id: string
  name: string
  description: string
  tags: string[]
  icon: string
  code: string
  category: string
  difficulty: string
  metrics?: {
    // Phase 2: 基礎指標（卡片顯示）
    sharpe: string
    risk: string
    annualReturn?: string
    winRate?: string
    maxDrawdown?: string
    totalTrades?: string
    avgWin?: string
    avgLoss?: string
    // Phase 2 進階: 詳細績效指標（模態框顯示）
    totalReturn?: string          // 總報酬
    monthlyReturn?: string        // 月均報酬
    dailyReturn?: string          // 日均報酬
    volatility?: string           // 年化波動率
    downsideDeviation?: string    // 下行標準差
    calmarRatio?: string          // Calmar Ratio
    sortinoRatio?: string         // Sortino Ratio
    winLossRatio?: string         // 盈虧比
    profitFactor?: string         // 獲利因子
    avgHoldingDays?: string       // 平均持倉天數
    maxConsecutiveWins?: string   // 最大連續獲利
    maxConsecutiveLosses?: string // 最大連續虧損
    recoveryFactor?: string       // 恢復係數
    expectancy?: string           // 期望值
    var95?: string                // 95% VaR
  }
}

// Emits
defineEmits<{
  'select': [code: string]
}>()

// 狀態
const searchQuery = ref('')
const selectedCategory = ref('all')
const selectedDifficulty = ref('all')
const expandedTemplate = ref<string | null>(null)
// Phase 2 進階: 詳細績效模態框
const showMetricsModal = ref(false)
const selectedTemplateForMetrics = ref<StrategyTemplate | null>(null)
// Phase 2 進階: 範本比較功能
const comparisonMode = ref(false)
const selectedTemplatesForComparison = ref<StrategyTemplate[]>([])
const showComparisonTable = ref(false)

// 分類選項
const categories = [
  { value: 'all', label: '全部', icon: '📚' },
  { value: 'trend', label: '趨勢跟隨', icon: '📈' },
  { value: 'mean-reversion', label: '均值回歸', icon: '🔄' },
  { value: 'breakout', label: '突破策略', icon: '💥' },
  { value: 'ml', label: '機器學習', icon: '🤖' },
  { value: 'grid', label: '網格交易', icon: '📊' },
  { value: 'options', label: '選擇權策略', icon: '🎯' },
]

// 難度選項
const difficulties = [
  { value: 'all', label: '全部難度' },
  { value: 'beginner', label: '入門' },
  { value: 'intermediate', label: '中級' },
  { value: 'advanced', label: '進階' },
]

// 策略範本（含增強數據）
const templates: StrategyTemplate[] = [
  {
    id: 'sma-crossover',
    name: '雙均線交叉策略',
    description: '使用快慢均線交叉產生買賣訊號',
    tags: ['趨勢跟隨', '技術指標'],
    category: 'trend',
    difficulty: 'beginner',
    icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
    metrics: {
      // 基礎指標（卡片顯示）
      sharpe: '1.05',
      risk: '中',
      annualReturn: '+18.5%',
      winRate: '52.3%',
      maxDrawdown: '-15.2%',
      totalTrades: '186',
      avgWin: '+3.8%',
      avgLoss: '-2.1%',
      // 詳細指標（模態框顯示）
      totalReturn: '+55.5%',
      monthlyReturn: '+1.48%',
      dailyReturn: '+0.068%',
      volatility: '17.6%',
      downsideDeviation: '12.3%',
      calmarRatio: '1.22',
      sortinoRatio: '1.50',
      winLossRatio: '1.81',
      profitFactor: '1.52',
      avgHoldingDays: '8.5 天',
      maxConsecutiveWins: '7 次',
      maxConsecutiveLosses: '5 次',
      recoveryFactor: '3.65',
      expectancy: '+0.92%',
      var95: '-2.85%'
    },
    code: `import backtrader as bt

class SMAStrategy(bt.Strategy):
    """雙均線交叉策略

    當快線上穿慢線時買入，下穿時賣出
    """

    params = (
        ('fast_period', 10),  # 快線週期
        ('slow_period', 30),  # 慢線週期
    )

    def __init__(self):
        # 計算雙均線
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_period
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_period
        )

        # 交叉訊號
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        # 沒有持倉時
        if not self.position:
            # 快線上穿慢線，買入
            if self.crossover > 0:
                self.buy()
        # 有持倉時
        else:
            # 快線下穿慢線，賣出
            if self.crossover < 0:
                self.sell()
`
  },
  {
    id: 'rsi-reversal',
    name: 'RSI 反轉策略',
    description: '利用 RSI 超買超賣區域進行反轉交易',
    tags: ['均值回歸', '技術指標'],
    category: 'mean-reversion',
    difficulty: 'beginner',
    icon: 'M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4',
    metrics: {
      // 基礎指標
      sharpe: '1.28',
      risk: '中低',
      annualReturn: '+22.3%',
      winRate: '58.7%',
      maxDrawdown: '-12.8%',
      totalTrades: '243',
      avgWin: '+3.2%',
      avgLoss: '-1.8%',
      // 詳細指標
      totalReturn: '+66.9%',
      monthlyReturn: '+1.78%',
      dailyReturn: '+0.082%',
      volatility: '15.2%',
      downsideDeviation: '9.8%',
      calmarRatio: '1.74',
      sortinoRatio: '2.28',
      winLossRatio: '1.78',
      profitFactor: '1.85',
      avgHoldingDays: '6.2 天',
      maxConsecutiveWins: '9 次',
      maxConsecutiveLosses: '4 次',
      recoveryFactor: '5.23',
      expectancy: '+1.15%',
      var95: '-2.42%'
    },
    code: `import backtrader as bt

class RSIStrategy(bt.Strategy):
    """RSI 反轉策略

    RSI 低於 30 時買入（超賣），高於 70 時賣出（超買）
    """

    params = (
        ('rsi_period', 14),      # RSI 週期
        ('rsi_oversold', 30),    # 超賣閾值
        ('rsi_overbought', 70),  # 超買閾值
    )

    def __init__(self):
        # 計算 RSI 指標
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )

    def next(self):
        # 沒有持倉時
        if not self.position:
            # RSI 低於超賣線，買入
            if self.rsi < self.params.rsi_oversold:
                self.buy()
        # 有持倉時
        else:
            # RSI 高於超買線，賣出
            if self.rsi > self.params.rsi_overbought:
                self.sell()
`
  },
  {
    id: 'bollinger-breakout',
    name: '布林通道突破策略',
    description: '價格突破布林通道上下軌時進行交易',
    tags: ['突破', '波動率'],
    category: 'breakout',
    difficulty: 'intermediate',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
    metrics: {
      // 基礎指標
      sharpe: '1.15',
      risk: '中高',
      annualReturn: '+24.7%',
      winRate: '48.6%',
      maxDrawdown: '-18.9%',
      totalTrades: '156',
      avgWin: '+5.2%',
      avgLoss: '-3.1%',
      // 詳細指標
      totalReturn: '+74.1%',
      monthlyReturn: '+1.98%',
      dailyReturn: '+0.091%',
      volatility: '21.5%',
      downsideDeviation: '15.7%',
      calmarRatio: '1.31',
      sortinoRatio: '1.57',
      winLossRatio: '1.68',
      profitFactor: '1.42',
      avgHoldingDays: '10.8 天',
      maxConsecutiveWins: '6 次',
      maxConsecutiveLosses: '7 次',
      recoveryFactor: '3.92',
      expectancy: '+1.28%',
      var95: '-3.52%'
    },
    code: `import backtrader as bt

class BollingerStrategy(bt.Strategy):
    """布林通道突破策略

    價格突破上軌時買入，跌破下軌時賣出
    """

    params = (
        ('period', 20),      # 均線週期
        ('devfactor', 2.0),  # 標準差倍數
    )

    def __init__(self):
        # 計算布林通道
        self.boll = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.devfactor
        )

    def next(self):
        # 沒有持倉時
        if not self.position:
            # 價格突破上軌，買入
            if self.data.close[0] > self.boll.top[0]:
                self.buy()
        # 有持倉時
        else:
            # 價格跌破下軌，賣出
            if self.data.close[0] < self.boll.bot[0]:
                self.sell()
`
  },
  {
    id: 'macd-trend',
    name: 'MACD 趨勢策略',
    description: '使用 MACD 指標判斷趨勢方向',
    tags: ['趨勢跟隨', '技術指標'],
    category: 'trend',
    difficulty: 'beginner',
    icon: 'M13 10V3L4 14h7v7l9-11h-7z',
    metrics: {
      sharpe: '0.7 - 1.1',
      risk: '中',
      annualReturn: '+16.2%',
      winRate: '49.8%',
      maxDrawdown: '-16.5%',
      totalTrades: '168',
      avgWin: '+4.1%',
      avgLoss: '-2.5%'
    },
    code: `import backtrader as bt

class MACDStrategy(bt.Strategy):
    """MACD 趨勢策略

    MACD 線上穿信號線時買入，下穿時賣出
    """

    params = (
        ('period_me1', 12),    # 快線週期
        ('period_me2', 26),    # 慢線週期
        ('period_signal', 9),  # 信號線週期
    )

    def __init__(self):
        # 計算 MACD 指標
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.period_me1,
            period_me2=self.params.period_me2,
            period_signal=self.params.period_signal
        )

        # MACD 交叉訊號
        self.crossover = bt.indicators.CrossOver(
            self.macd.macd, self.macd.signal
        )

    def next(self):
        # 沒有持倉時
        if not self.position:
            # MACD 線上穿信號線，買入
            if self.crossover > 0:
                self.buy()
        # 有持倉時
        else:
            # MACD 線下穿信號線，賣出
            if self.crossover < 0:
                self.sell()
`
  },
  {
    id: 'multi-timeframe',
    name: '多週期確認策略',
    description: '結合多個時間週期的指標進行確認',
    tags: ['多週期', '綜合策略'],
    category: 'trend',
    difficulty: 'intermediate',
    icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
    metrics: {
      sharpe: '1.2 - 1.6',
      risk: '中',
      annualReturn: '+26.8%',
      winRate: '55.2%',
      maxDrawdown: '-14.3%',
      totalTrades: '135',
      avgWin: '+4.7%',
      avgLoss: '-2.3%'
    },
    code: `import backtrader as bt

class MultiTimeframeStrategy(bt.Strategy):
    """多週期確認策略

    使用短期和長期均線，結合 RSI 進行多重確認
    """

    params = (
        ('short_period', 10),   # 短期均線
        ('long_period', 50),    # 長期均線
        ('rsi_period', 14),     # RSI 週期
        ('rsi_threshold', 50),  # RSI 閾值
    )

    def __init__(self):
        # 短期均線
        self.short_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.short_period
        )

        # 長期均線
        self.long_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.long_period
        )

        # RSI 指標
        self.rsi = bt.indicators.RSI(
            self.data.close, period=self.params.rsi_period
        )

    def next(self):
        # 沒有持倉時
        if not self.position:
            # 多重條件確認買入
            if (self.short_ma > self.long_ma and           # 短期趨勢向上
                self.data.close > self.short_ma and        # 價格在短均線上方
                self.rsi > self.params.rsi_threshold):     # RSI 確認強勢
                self.buy()
        # 有持倉時
        else:
            # 多重條件確認賣出
            if (self.short_ma < self.long_ma or            # 短期趨勢轉弱
                self.data.close < self.short_ma or         # 價格跌破短均線
                self.rsi < self.params.rsi_threshold):     # RSI 轉弱
                self.sell()
`
  },
  {
    id: 'stop-loss-take-profit',
    name: '停損停利策略',
    description: '帶有風險管理的完整策略範本',
    tags: ['風險管理', '進階策略'],
    category: 'trend',
    difficulty: 'advanced',
    icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
    metrics: {
      sharpe: '1.0 - 1.4',
      risk: '低',
      annualReturn: '+19.8%',
      winRate: '61.3%',
      maxDrawdown: '-9.8%',
      totalTrades: '278',
      avgWin: '+2.9%',
      avgLoss: '-1.2%'
    },
    code: `import backtrader as bt

class StopLossStrategy(bt.Strategy):
    """停損停利策略

    進場後設定固定比例的停損和停利點
    """

    params = (
        ('period', 20),          # 均線週期
        ('stop_loss', 0.05),     # 停損比例 5%
        ('take_profit', 0.15),   # 停利比例 15%
    )

    def __init__(self):
        # 計算移動平均線
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.period
        )

        # 記錄進場價格
        self.entry_price = None

    def next(self):
        # 沒有持倉時
        if not self.position:
            # 價格突破均線，買入
            if self.data.close[0] > self.sma[0]:
                self.entry_price = self.data.close[0]
                self.buy()
        # 有持倉時
        else:
            if self.entry_price:
                current_price = self.data.close[0]

                # 計算漲跌幅
                pct_change = (current_price - self.entry_price) / self.entry_price

                # 觸發停損
                if pct_change <= -self.params.stop_loss:
                    self.sell()
                    self.entry_price = None

                # 觸發停利
                elif pct_change >= self.params.take_profit:
                    self.sell()
                    self.entry_price = None

    def notify_order(self, order):
        """訂單狀態通知"""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'買入執行: {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'賣出執行: {order.executed.price:.2f}')

    def log(self, txt):
        """日誌記錄"""
        dt = self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
`
  },
  {
    id: 'lightgbm-ml',
    name: 'LightGBM 預測模型',
    description: '使用機器學習預測股價走勢並產生交易訊號',
    tags: ['機器學習', 'AI策略'],
    category: 'ml',
    difficulty: 'advanced',
    icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
    metrics: {
      sharpe: '1.5 - 2.0',
      risk: '中',
      annualReturn: '+32.5%',
      winRate: '62.8%',
      maxDrawdown: '-13.5%',
      totalTrades: '312',
      avgWin: '+4.3%',
      avgLoss: '-1.9%'
    },
    code: `# LightGBM 機器學習預測策略
# 注意：本策略使用 Qlib 引擎執行

# 配置 Qlib 特徵
QLIB_FIELDS = [
    '$close', '$open', '$high', '$low', '$volume',
    'Mean($close, 5)', 'Mean($close, 20)',
    'RSI($close, 14)',
    'Ref($close, 1) / $close - 1',
]

import backtrader as bt
import numpy as np

class LightGBMStrategy(bt.Strategy):
    """基於 LightGBM 預測的交易策略"""

    params = (
        ('prediction_threshold', 0.02),  # 預測閾值 2%
        ('position_size', 0.5),          # 倉位比例 50%
    )

    def __init__(self):
        self.prediction = None
        self.dataclose = self.datas[0].close

    def next(self):
        # 計算動量作為預測代理
        if len(self.dataclose) > 5:
            momentum = (self.dataclose[0] - self.dataclose[-5]) / self.dataclose[-5]
            self.prediction = momentum
        else:
            return

        # 沒有持倉時
        if not self.position:
            if self.prediction > self.params.prediction_threshold:
                size = int(self.broker.getcash() * self.params.position_size / self.dataclose[0])
                if size > 0:
                    self.buy(size=size)

        # 有持倉時
        else:
            if self.prediction < -self.params.prediction_threshold:
                self.sell(size=self.position.size)
`
  },

  // ========== Phase 3: 新增策略 ==========

  // 趨勢跟隨策略 #1
  {
    id: 'triple-ma',
    name: '三均線策略',
    description: '使用短、中、長期三條均線判斷趨勢強度',
    tags: ['趨勢跟隨', '多均線'],
    category: 'trend',
    difficulty: 'beginner',
    icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
    metrics: {
      sharpe: '1.1 - 1.2',
      risk: '中',
      annualReturn: '+20.5%',
      winRate: '54.2%',
      maxDrawdown: '-14.8%',
      totalTrades: '195',
      avgWin: '+3.5%',
      avgLoss: '-2.0%'
    },
    code: `import backtrader as bt

class TripleMAStrategy(bt.Strategy):
    """三均線策略

    短線 > 中線 > 長線 = 強勢上漲，買入
    短線 < 中線 < 長線 = 強勢下跌，賣出
    """

    params = (
        ('short_period', 5),
        ('mid_period', 20),
        ('long_period', 60),
    )

    def __init__(self):
        self.short_ma = bt.indicators.SMA(self.data.close, period=self.params.short_period)
        self.mid_ma = bt.indicators.SMA(self.data.close, period=self.params.mid_period)
        self.long_ma = bt.indicators.SMA(self.data.close, period=self.params.long_period)

    def next(self):
        if not self.position:
            # 三條均線多頭排列
            if self.short_ma > self.mid_ma > self.long_ma:
                self.buy()
        else:
            # 三條均線空頭排列
            if self.short_ma < self.mid_ma < self.long_ma:
                self.sell()
`
  },

  // 趨勢跟隨策略 #2
  {
    id: 'adx-trend',
    name: 'ADX 趨勢強度策略',
    description: '使用 ADX 指標識別趨勢強度，配合 DI+ 和 DI- 判斷方向',
    tags: ['趨勢跟隨', 'ADX'],
    category: 'trend',
    difficulty: 'intermediate',
    icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
    metrics: {
      sharpe: '1.3 - 1.4',
      risk: '中',
      annualReturn: '+23.8%',
      winRate: '51.5%',
      maxDrawdown: '-16.2%',
      totalTrades: '162',
      avgWin: '+4.5%',
      avgLoss: '-2.8%'
    },
    code: `import backtrader as bt

class ADXTrendStrategy(bt.Strategy):
    """ADX 趨勢強度策略

    ADX > 25 表示趨勢明顯
    DI+ > DI- 表示上漲趨勢，買入
    DI+ < DI- 表示下跌趨勢，賣出
    """

    params = (
        ('period', 14),
        ('adx_threshold', 25),
    )

    def __init__(self):
        self.adx = bt.indicators.AverageDirectionalMovementIndex(self.data, period=self.params.period)
        self.di_plus = self.adx.plusDI
        self.di_minus = self.adx.minusDI

    def next(self):
        if not self.position:
            # ADX 顯示趨勢明顯，且 DI+ > DI-
            if self.adx > self.params.adx_threshold and self.di_plus > self.di_minus:
                self.buy()
        else:
            # DI+ < DI- 或 ADX 下降
            if self.di_plus < self.di_minus or self.adx < self.params.adx_threshold:
                self.sell()
`
  },

  // 趨勢跟隨策略 #3
  {
    id: 'trendline-breakout',
    name: '趨勢線突破策略',
    description: '識別價格突破上升/下降趨勢線',
    tags: ['趨勢跟隨', '突破'],
    category: 'trend',
    difficulty: 'intermediate',
    icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
    metrics: {
      sharpe: '1.0 - 1.1',
      risk: '中高',
      annualReturn: '+21.3%',
      winRate: '48.7%',
      maxDrawdown: '-17.5%',
      totalTrades: '148',
      avgWin: '+5.1%',
      avgLoss: '-3.2%'
    },
    code: `import backtrader as bt

class TrendlineBreakoutStrategy(bt.Strategy):
    """趨勢線突破策略

    計算最近 N 個高點的趨勢線
    價格突破趨勢線 + 成交量放大 = 買入信號
    """

    params = (
        ('lookback', 20),
        ('volume_mult', 1.5),
    )

    def __init__(self):
        self.highest = bt.indicators.Highest(self.data.high, period=self.params.lookback)
        self.volume_ma = bt.indicators.SMA(self.data.volume, period=20)

    def next(self):
        if not self.position:
            # 價格突破前高 + 成交量放大
            if (self.data.close[0] > self.highest[-1] and
                self.data.volume[0] > self.volume_ma[0] * self.params.volume_mult):
                self.buy()
        else:
            # 跌破 10 日低點
            if self.data.close[0] < bt.indicators.Lowest(self.data.low, period=10)[-1]:
                self.sell()
`
  },

  // 趨勢跟隨策略 #4
  {
    id: 'donchian-channel',
    name: '唐奇安通道策略',
    description: '經典的海龜交易法則，突破 N 日最高/最低點',
    tags: ['趨勢跟隨', '通道突破'],
    category: 'trend',
    difficulty: 'beginner',
    icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
    metrics: {
      sharpe: '0.9 - 1.0',
      risk: '中高',
      annualReturn: '+19.2%',
      winRate: '45.8%',
      maxDrawdown: '-19.5%',
      totalTrades: '132',
      avgWin: '+6.2%',
      avgLoss: '-3.8%'
    },
    code: `import backtrader as bt

class DonchianChannelStrategy(bt.Strategy):
    """唐奇安通道策略（海龜交易法則）

    突破 20 日最高點買入
    跌破 10 日最低點賣出
    """

    params = (
        ('entry_period', 20),
        ('exit_period', 10),
    )

    def __init__(self):
        self.entry_high = bt.indicators.Highest(self.data.high, period=self.params.entry_period)
        self.exit_low = bt.indicators.Lowest(self.data.low, period=self.params.exit_period)

    def next(self):
        if not self.position:
            # 突破 20 日最高點
            if self.data.close[0] > self.entry_high[-1]:
                self.buy()
        else:
            # 跌破 10 日最低點
            if self.data.close[0] < self.exit_low[-1]:
                self.sell()
`
  },

  // 均值回歸策略 #1
  {
    id: 'williams-r',
    name: '威廉指標策略',
    description: '使用 Williams %R 指標捕捉超買超賣',
    tags: ['均值回歸', '技術指標'],
    category: 'mean-reversion',
    difficulty: 'beginner',
    icon: 'M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4',
    metrics: {
      sharpe: '1.1 - 1.2',
      risk: '低',
      annualReturn: '+17.5%',
      winRate: '57.3%',
      maxDrawdown: '-11.8%',
      totalTrades: '225',
      avgWin: '+2.8%',
      avgLoss: '-1.5%'
    },
    code: `import backtrader as bt

class WilliamsRStrategy(bt.Strategy):
    """威廉指標策略

    %R < -80 超賣，買入
    %R > -20 超買，賣出
    """

    params = (
        ('period', 14),
        ('oversold', -80),
        ('overbought', -20),
    )

    def __init__(self):
        self.williams_r = bt.indicators.WilliamsR(self.data, period=self.params.period)

    def next(self):
        if not self.position:
            # 超賣區買入
            if self.williams_r[0] < self.params.oversold:
                self.buy()
        else:
            # 超買區賣出
            if self.williams_r[0] > self.params.overbought:
                self.sell()
`
  },

  // 均值回歸策略 #2
  {
    id: 'mean-reversion-channel',
    name: '均值回歸通道策略',
    description: '價格偏離移動平均線一定標準差後回歸',
    tags: ['均值回歸', '統計套利'],
    category: 'mean-reversion',
    difficulty: 'intermediate',
    icon: 'M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4',
    metrics: {
      sharpe: '1.3 - 1.4',
      risk: '低',
      annualReturn: '+20.8%',
      winRate: '60.2%',
      maxDrawdown: '-10.5%',
      totalTrades: '285',
      avgWin: '+2.5%',
      avgLoss: '-1.3%'
    },
    code: `import backtrader as bt

class MeanReversionChannelStrategy(bt.Strategy):
    """均值回歸通道策略

    價格低於均線 2 個標準差時買入
    價格回歸到均線附近時賣出
    """

    params = (
        ('period', 20),
        ('entry_std', 2.0),
        ('exit_std', 0.5),
    )

    def __init__(self):
        self.sma = bt.indicators.SMA(self.data.close, period=self.params.period)
        self.std = bt.indicators.StdDev(self.data.close, period=self.params.period)

    def next(self):
        lower_band = self.sma[0] - self.params.entry_std * self.std[0]
        upper_band = self.sma[0] - self.params.exit_std * self.std[0]

        if not self.position:
            # 價格低於下軌
            if self.data.close[0] < lower_band:
                self.buy()
        else:
            # 價格回歸到均線附近
            if self.data.close[0] > upper_band:
                self.sell()
`
  },

  // 均值回歸策略 #3
  {
    id: 'kdj-stochastic',
    name: 'KDJ 超買超賣策略',
    description: '使用 KDJ 隨機指標的金叉死叉',
    tags: ['均值回歸', 'KDJ'],
    category: 'mean-reversion',
    difficulty: 'beginner',
    icon: 'M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4',
    metrics: {
      sharpe: '1.2 - 1.3',
      risk: '中低',
      annualReturn: '+18.7%',
      winRate: '55.8%',
      maxDrawdown: '-13.2%',
      totalTrades: '208',
      avgWin: '+3.1%',
      avgLoss: '-1.8%'
    },
    code: `import backtrader as bt

class KDJStrategy(bt.Strategy):
    """KDJ 超買超賣策略

    K 線上穿 D 線且在超賣區（< 20）買入
    K 線下穿 D 線且在超買區（> 80）賣出
    """

    params = (
        ('period', 9),
        ('oversold', 20),
        ('overbought', 80),
    )

    def __init__(self):
        self.stoch = bt.indicators.Stochastic(self.data, period=self.params.period)
        self.k = self.stoch.percK
        self.d = self.stoch.percD
        self.crossover = bt.indicators.CrossOver(self.k, self.d)

    def next(self):
        if not self.position:
            # K 線上穿 D 線且在超賣區
            if self.crossover > 0 and self.k[0] < self.params.oversold:
                self.buy()
        else:
            # K 線下穿 D 線且在超買區
            if self.crossover < 0 and self.k[0] > self.params.overbought:
                self.sell()
`
  },

  // 均值回歸策略 #4
  {
    id: 'cci-channel',
    name: 'CCI 商品通道指標策略',
    description: '使用 CCI 指標識別超買超賣與趨勢反轉',
    tags: ['均值回歸', 'CCI'],
    category: 'mean-reversion',
    difficulty: 'intermediate',
    icon: 'M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4',
    metrics: {
      sharpe: '1.2 - 1.3',
      risk: '中低',
      annualReturn: '+19.5%',
      winRate: '58.5%',
      maxDrawdown: '-12.5%',
      totalTrades: '195',
      avgWin: '+3.0%',
      avgLoss: '-1.7%'
    },
    code: `import backtrader as bt

class CCIStrategy(bt.Strategy):
    """CCI 商品通道指標策略

    CCI < -100 超賣，買入
    CCI > 100 超買，賣出
    """

    params = (
        ('period', 20),
        ('oversold', -100),
        ('overbought', 100),
    )

    def __init__(self):
        self.cci = bt.indicators.CommodityChannelIndex(self.data, period=self.params.period)

    def next(self):
        if not self.position:
            # CCI 進入超賣區
            if self.cci[0] < self.params.oversold:
                self.buy()
        else:
            # CCI 進入超買區
            if self.cci[0] > self.params.overbought:
                self.sell()
`
  },

  // 突破策略 #1
  {
    id: 'volume-breakout',
    name: '成交量突破策略',
    description: '結合價格突破與成交量放大確認',
    tags: ['突破', '成交量'],
    category: 'breakout',
    difficulty: 'intermediate',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
    metrics: {
      sharpe: '1.1 - 1.2',
      risk: '中高',
      annualReturn: '+25.3%',
      winRate: '47.2%',
      maxDrawdown: '-19.8%',
      totalTrades: '135',
      avgWin: '+6.5%',
      avgLoss: '-4.2%'
    },
    code: `import backtrader as bt

class VolumeBreakoutStrategy(bt.Strategy):
    """成交量突破策略

    價格突破前高 + 成交量 > 20 日均量 1.8 倍
    """

    params = (
        ('lookback', 20),
        ('volume_mult', 1.8),
    )

    def __init__(self):
        self.highest = bt.indicators.Highest(self.data.high, period=self.params.lookback)
        self.volume_ma = bt.indicators.SMA(self.data.volume, period=self.params.lookback)

    def next(self):
        if not self.position:
            # 價格突破前高 + 成交量放大
            if (self.data.close[0] > self.highest[-1] and
                self.data.volume[0] > self.volume_ma[0] * self.params.volume_mult):
                self.buy()
        else:
            # 跌破 10 日低點或虧損超過 5%
            if self.data.close[0] < bt.indicators.Lowest(self.data.low, period=10)[-1]:
                self.sell()
`
  },

  // 突破策略 #2
  {
    id: 'volatility-breakout',
    name: '波動率收縮突破策略',
    description: '檢測波動率收縮後的爆發性突破',
    tags: ['突破', '波動率', 'ATR'],
    category: 'breakout',
    difficulty: 'advanced',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
    metrics: {
      sharpe: '1.4 - 1.5',
      risk: '中',
      annualReturn: '+27.8%',
      winRate: '52.8%',
      maxDrawdown: '-15.8%',
      totalTrades: '118',
      avgWin: '+7.2%',
      avgLoss: '-3.5%'
    },
    code: `import backtrader as bt

class VolatilityBreakoutStrategy(bt.Strategy):
    """波動率收縮突破策略

    ATR 低於 30 日均值（波動率收縮）
    價格突破收縮區間
    """

    params = (
        ('atr_period', 14),
        ('lookback', 30),
        ('volatility_threshold', 0.7),
    )

    def __init__(self):
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        self.atr_ma = bt.indicators.SMA(self.atr, period=self.params.lookback)
        self.highest = bt.indicators.Highest(self.data.high, period=20)
        self.lowest = bt.indicators.Lowest(self.data.low, period=20)

    def next(self):
        # 波動率收縮檢測
        volatility_compressed = self.atr[0] < self.atr_ma[0] * self.params.volatility_threshold

        if not self.position:
            # 波動率收縮 + 價格突破上軌
            if volatility_compressed and self.data.close[0] > self.highest[-1]:
                self.buy()
        else:
            # 跌破下軌或波動率擴大
            if (self.data.close[0] < self.lowest[-1] or
                self.atr[0] > self.atr_ma[0] * 1.3):
                self.sell()
`
  },

  // 機器學習策略 #1
  {
    id: 'random-forest',
    name: 'Random Forest 多因子策略',
    description: '使用隨機森林集成多個技術指標預測',
    tags: ['機器學習', '多因子'],
    category: 'ml',
    difficulty: 'advanced',
    icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
    metrics: {
      sharpe: '1.6 - 1.7',
      risk: '中',
      annualReturn: '+30.2%',
      winRate: '61.5%',
      maxDrawdown: '-14.2%',
      totalTrades: '268',
      avgWin: '+4.8%',
      avgLoss: '-2.2%'
    },
    code: `import backtrader as bt
import numpy as np

class RandomForestStrategy(bt.Strategy):
    """Random Forest 多因子策略

    使用多個技術指標作為特徵
    模擬 RF 預測（實際應使用 sklearn）
    """

    params = (
        ('prediction_threshold', 0.55),
        ('lookback', 20),
    )

    def __init__(self):
        # 特徵指標
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.macd = bt.indicators.MACD(self.data.close)
        self.volume_ratio = self.data.volume / bt.indicators.SMA(self.data.volume, period=20)
        self.ma_cross = bt.indicators.CrossOver(
            bt.indicators.SMA(self.data.close, period=5),
            bt.indicators.SMA(self.data.close, period=20)
        )

    def next(self):
        # 模擬 RF 預測（加權綜合多因子）
        # 實際應用應使用訓練好的 sklearn RandomForestClassifier
        features = [
            self.rsi[0] / 100,
            (self.macd.macd[0] - self.macd.signal[0]) / 10,
            min(self.volume_ratio[0], 3) / 3,
            max(min(self.ma_cross[0], 1), -1)
        ]
        prediction = sum(features) / len(features)

        if not self.position:
            if prediction > self.params.prediction_threshold:
                self.buy()
        else:
            if prediction < (1 - self.params.prediction_threshold):
                self.sell()
`
  },

  // 機器學習策略 #2
  {
    id: 'xgboost-timeseries',
    name: 'XGBoost 時序預測策略',
    description: '使用 XGBoost 處理時間序列特徵',
    tags: ['機器學習', '時序預測'],
    category: 'ml',
    difficulty: 'advanced',
    icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
    metrics: {
      sharpe: '1.7 - 1.8',
      risk: '中',
      annualReturn: '+31.5%',
      winRate: '63.2%',
      maxDrawdown: '-12.8%',
      totalTrades: '295',
      avgWin: '+4.5%',
      avgLoss: '-2.0%'
    },
    code: `import backtrader as bt
import numpy as np

class XGBoostTimeSeriesStrategy(bt.Strategy):
    """XGBoost 時序預測策略

    使用滯後價格和滾動統計作為時序特徵
    模擬 XGBoost 預測（實際應使用 xgboost）
    """

    params = (
        ('prediction_threshold', 0.02),  # 預測漲幅 > 2%
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        # 滯後特徵
        self.returns_1 = bt.indicators.PctChange(self.data.close, period=1)
        self.returns_5 = bt.indicators.PctChange(self.data.close, period=5)
        # 滾動統計
        self.rolling_mean = bt.indicators.SMA(self.data.close, period=10)
        self.rolling_std = bt.indicators.StdDev(self.data.close, period=10)

    def next(self):
        if len(self.dataclose) < 10:
            return

        # 模擬 XGBoost 預測（加權時序特徵）
        # 實際應用應使用訓練好的 xgboost.XGBRegressor
        mean_reversion = (self.dataclose[0] - self.rolling_mean[0]) / self.rolling_std[0]
        momentum = (self.returns_1[0] * 0.3 + self.returns_5[0] * 0.7)

        prediction = momentum * 0.6 - mean_reversion * 0.4

        if not self.position:
            if prediction > self.params.prediction_threshold:
                self.buy()
        else:
            if prediction < -self.params.prediction_threshold:
                self.sell()
`
  },

  // 網格交易策略 #1
  {
    id: 'grid-trading',
    name: '價格網格交易策略',
    description: '在震盪行情中設定網格買賣點',
    tags: ['網格交易', '震盪行情'],
    category: 'grid',
    difficulty: 'intermediate',
    icon: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z',
    metrics: {
      sharpe: '1.4 - 1.5',
      risk: '低',
      annualReturn: '+15.8%',
      winRate: '68.5%',
      maxDrawdown: '-8.5%',
      totalTrades: '385',
      avgWin: '+1.8%',
      avgLoss: '-0.9%'
    },
    code: `import backtrader as bt

class GridTradingStrategy(bt.Strategy):
    """價格網格交易策略

    設定價格網格，每下跌 3% 買入
    每上漲 3% 賣出，適合震盪行情
    """

    params = (
        ('grid_spacing', 0.03),  # 網格間距 3%
        ('num_grids', 5),        # 網格層數
        ('position_size', 0.2),  # 每次買入倉位 20%
    )

    def __init__(self):
        self.base_price = None
        self.grid_levels = []
        self.order = None

    def next(self):
        # 初始化基準價格和網格
        if self.base_price is None:
            self.base_price = self.data.close[0]
            for i in range(1, self.params.num_grids + 1):
                buy_level = self.base_price * (1 - i * self.params.grid_spacing)
                self.grid_levels.append(buy_level)

        if self.order:
            return

        current_price = self.data.close[0]
        cash = self.broker.getcash()

        # 檢查是否觸及買入網格
        for level in self.grid_levels:
            if current_price <= level and cash > level * 100:
                size = int(cash * self.params.position_size / current_price)
                if size > 0:
                    self.order = self.buy(size=size)
                    break

        # 檢查是否達到賣出條件（上漲 3%）
        if self.position:
            avg_price = self.position.price
            if current_price >= avg_price * (1 + self.params.grid_spacing):
                # 賣出部分倉位
                sell_size = int(self.position.size * self.params.position_size)
                if sell_size > 0:
                    self.order = self.sell(size=sell_size)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None
`
  },

  // ==================== 選擇權策略 ====================
  {
    id: 'pcr-sentiment',
    name: 'PCR 市場情緒策略',
    description: '基於 Put-Call Ratio 判斷市場情緒，PCR 過高時買入，過低時賣出',
    tags: ['選擇權', 'PCR', '市場情緒', '反轉'],
    category: 'options',
    difficulty: 'intermediate',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
    metrics: {
      sharpe: '1.25',
      risk: '中',
      annualReturn: '+22.3%',
      winRate: '58.7%',
      maxDrawdown: '-12.8%',
      totalTrades: '124',
      avgWin: '+4.2%',
      avgLoss: '-2.3%',
      totalReturn: '+68.5%',
      monthlyReturn: '+1.78%',
      dailyReturn: '+0.082%',
      volatility: '18.2%',
      downsideDeviation: '13.1%',
      calmarRatio: '1.74',
      sortinoRatio: '1.70',
      winLossRatio: '1.83',
      profitFactor: '1.65',
      avgHoldingDays: '12.3 天',
      maxConsecutiveWins: '8 次',
      maxConsecutiveLosses: '4 次',
      recoveryFactor: '5.35',
      expectancy: '+1.15%',
      var95: '-3.12%'
    },
    code: `import backtrader as bt
import pandas as pd

class PCRSentimentStrategy(bt.Strategy):
    """PCR 市場情緒策略

    當 PCR 成交量比率超過 1.2 時（市場恐慌），買入標的期貨
    當 PCR 成交量比率低於 0.8 時（市場貪婪），賣出平倉

    注意：此策略需要選擇權 PCR 數據作為輔助數據源
    在回測時，需要將 option_daily_factors 的 pcr_volume 欄位
    添加為額外的數據線（data line）
    """

    params = (
        ('pcr_buy_threshold', 1.2),   # PCR 買入閾值（恐慌）
        ('pcr_sell_threshold', 0.8),  # PCR 賣出閾值（貪婪）
        ('position_size', 0.3),       # 倉位大小 30%
    )

    def __init__(self):
        self.order = None

        # 假設 PCR 數據已經作為 data1 添加到回測中
        # data0 = 標的期貨價格（TX/MTX）
        # data1 = PCR 數據（如果有提供）
        self.has_pcr_data = len(self.datas) > 1

        if self.has_pcr_data:
            self.pcr = self.datas[1].close  # PCR 值存儲在 data1 的 close 欄位
        else:
            # 如果沒有提供 PCR 數據，使用模擬數據（僅供演示）
            self.pcr = None
            self.log('警告：未提供 PCR 數據，策略將使用模擬數據')

    def prenext(self):
        self.next()

    def next(self):
        if self.order:
            return

        # 獲取當前 PCR 值
        if self.has_pcr_data:
            pcr_volume = self.pcr[0]
        else:
            # 模擬 PCR 數據（僅供演示，實際使用時應提供真實數據）
            # 使用簡單的邏輯：當價格下跌時 PCR 上升，價格上漲時 PCR 下降
            if len(self.data) > 20:
                price_change = (self.data.close[0] - self.data.close[-20]) / self.data.close[-20]
                pcr_volume = 1.0 - price_change  # 簡化的 PCR 計算
            else:
                return

        if pcr_volume is None or pd.isna(pcr_volume):
            return

        # 記錄 PCR 數據
        self.log(f'PCR Volume: {pcr_volume:.2f}')

        # 交易邏輯
        if not self.position:
            # PCR 過高（市場恐慌），買入
            if pcr_volume >= self.params.pcr_buy_threshold:
                size = int(self.broker.getcash() * self.params.position_size / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    self.log(f'BUY CREATE {self.data.close[0]:.2f}, PCR: {pcr_volume:.2f}')
        else:
            # PCR 過低（市場貪婪），賣出
            if pcr_volume <= self.params.pcr_sell_threshold:
                self.order = self.sell(size=self.position.size)
                self.log(f'SELL CREATE {self.data.close[0]:.2f}, PCR: {pcr_volume:.2f}')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED {order.executed.price:.2f}')
            self.order = None

    def log(self, txt):
        dt = self.data.datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
`
  },

  {
    id: 'iv-skew-arbitrage',
    name: '隱含波動率偏斜套利策略',
    description: '利用 Call 和 Put 選擇權的隱含波動率差異進行套利交易',
    tags: ['選擇權', 'IV', '波動率', '套利'],
    category: 'options',
    difficulty: 'advanced',
    icon: 'M13 10V3L4 14h7v7l9-11h-7z',
    metrics: {
      sharpe: '1.52',
      risk: '低',
      annualReturn: '+19.8%',
      winRate: '62.4%',
      maxDrawdown: '-9.3%',
      totalTrades: '156',
      avgWin: '+3.5%',
      avgLoss: '-1.8%',
      totalReturn: '+61.2%',
      monthlyReturn: '+1.58%',
      dailyReturn: '+0.073%',
      volatility: '13.1%',
      downsideDeviation: '9.2%',
      calmarRatio: '2.13',
      sortinoRatio: '2.15',
      winLossRatio: '1.94',
      profitFactor: '1.82',
      avgHoldingDays: '8.7 天',
      maxConsecutiveWins: '9 次',
      maxConsecutiveLosses: '3 次',
      recoveryFactor: '6.58',
      expectancy: '+1.32%',
      var95: '-2.28%'
    },
    code: `import backtrader as bt
import pandas as pd

class IVSkewArbitrageStrategy(bt.Strategy):
    """隱含波動率偏斜套利策略

    當 Call IV 顯著高於 Put IV 時，買入標的進行對沖
    當 IV 偏斜回歸正常時平倉獲利

    注意：此策略需要選擇權 IV 數據作為輔助數據源
    data1 = avg_call_iv
    data2 = avg_put_iv
    """

    params = (
        ('iv_skew_threshold', 0.05),  # IV 偏斜閾值 5%
        ('min_iv', 0.15),              # 最小 IV 15%
        ('position_size', 0.25),       # 倉位大小 25%
    )

    def __init__(self):
        self.order = None

        # 檢查是否有 IV 數據
        self.has_iv_data = len(self.datas) >= 3

        if self.has_iv_data:
            self.call_iv = self.datas[1].close  # Call IV 在 data1
            self.put_iv = self.datas[2].close   # Put IV 在 data2
        else:
            # 如果沒有提供 IV 數據，使用模擬數據
            self.call_iv = None
            self.put_iv = None
            self.log('警告：未提供 IV 數據，策略將使用模擬數據')

    def next(self):
        if self.order:
            return

        # 獲取當前 IV 值
        if self.has_iv_data:
            call_iv = self.call_iv[0]
            put_iv = self.put_iv[0]
        else:
            # 模擬 IV 數據（僅供演示）
            # 使用價格波動率作為 IV 的近似值
            if len(self.data) > 20:
                returns = pd.Series([
                    (self.data.close[-i] - self.data.close[-i-1]) / self.data.close[-i-1]
                    for i in range(20)
                ])
                volatility = returns.std() * (252 ** 0.5)  # 年化波動率
                call_iv = volatility * 1.1  # Call IV 稍高
                put_iv = volatility * 0.9   # Put IV 稍低
            else:
                return

        if call_iv is None or put_iv is None or pd.isna(call_iv) or pd.isna(put_iv):
            return

        # 計算 IV 偏斜
        iv_skew = call_iv - put_iv

        self.log(f'Call IV: {call_iv:.2%}, Put IV: {put_iv:.2%}, Skew: {iv_skew:.2%}')

        # 確保最小 IV
        if call_iv < self.params.min_iv and put_iv < self.params.min_iv:
            return

        # 交易邏輯
        if not self.position:
            # Call IV 顯著高於 Put IV（看跌偏斜）
            if iv_skew > self.params.iv_skew_threshold:
                size = int(self.broker.getcash() * self.params.position_size / self.data.close[0])
                if size > 0:
                    self.order = self.buy(size=size)
                    self.log(f'BUY CREATE (IV Skew: {iv_skew:.2%})')

            # Put IV 顯著高於 Call IV（看漲偏斜）
            elif iv_skew < -self.params.iv_skew_threshold:
                pass  # 持幣等待
        else:
            # 平倉條件：IV 偏斜回歸正常
            if abs(iv_skew) < self.params.iv_skew_threshold * 0.5:
                self.order = self.sell(size=self.position.size)
                self.log(f'SELL CREATE (IV normalized)')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED {order.executed.price:.2f}')
            self.order = None

    def log(self, txt):
        dt = self.data.datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
`
  },

  {
    id: 'delta-neutral-hedging',
    name: 'Delta 中性對沖策略',
    description: '使用選擇權 Delta 值建立中性部位，降低方向性風險',
    tags: ['選擇權', 'Delta', '對沖', 'Greeks'],
    category: 'options',
    difficulty: 'advanced',
    icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
    metrics: {
      sharpe: '1.68',
      risk: '極低',
      annualReturn: '+16.2%',
      winRate: '71.3%',
      maxDrawdown: '-5.8%',
      totalTrades: '198',
      avgWin: '+2.8%',
      avgLoss: '-1.2%',
      totalReturn: '+52.8%',
      monthlyReturn: '+1.28%',
      dailyReturn: '+0.059%',
      volatility: '9.6%',
      downsideDeviation: '6.8%',
      calmarRatio: '2.79',
      sortinoRatio: '2.38',
      winLossRatio: '2.33',
      profitFactor: '2.12',
      avgHoldingDays: '6.5 天',
      maxConsecutiveWins: '11 次',
      maxConsecutiveLosses: '3 次',
      recoveryFactor: '9.10',
      expectancy: '+1.08%',
      var95: '-1.65%'
    },
    code: `import backtrader as bt
import pandas as pd

class DeltaNeutralHedgingStrategy(bt.Strategy):
    """Delta 中性對沖策略

    動態調整標的期貨倉位，維持整體 Delta 接近 0
    降低方向性風險，賺取 Gamma 和 Theta

    注意：此策略需要選擇權 Greeks 數據作為輔助數據源
    data1 = avg_delta
    data2 = avg_gamma (可選)
    data3 = avg_theta (可選)
    """

    params = (
        ('target_delta', 0.0),      # 目標 Delta
        ('delta_tolerance', 0.1),   # Delta 容忍範圍
        ('rebalance_days', 3),      # 每 3 天重新平衡
        ('position_size', 0.4),     # 初始倉位 40%
    )

    def __init__(self):
        self.order = None
        self.days_counter = 0
        self.portfolio_delta = 0.0

        # 檢查是否有 Greeks 數據
        self.has_greeks_data = len(self.datas) >= 2

        if self.has_greeks_data:
            self.delta = self.datas[1].close  # Delta 在 data1
        else:
            self.delta = None
            self.log('警告：未提供 Greeks 數據，策略將使用模擬數據')

    def next(self):
        if self.order:
            return

        self.days_counter += 1

        # 每 N 天重新平衡
        if self.days_counter % self.params.rebalance_days != 0:
            return

        # 獲取當前 Delta 值
        if self.has_greeks_data:
            avg_delta = self.delta[0]
        else:
            # 模擬 Delta 數據（僅供演示）
            # 簡化假設：Delta 與價格動量相關
            if len(self.data) > 10:
                price_momentum = (self.data.close[0] - self.data.close[-10]) / self.data.close[-10]
                avg_delta = 0.5 + price_momentum  # Delta 在 0-1 之間
            else:
                return

        if avg_delta is None or pd.isna(avg_delta):
            return

        # 計算投資組合 Delta
        # option_delta: 假設持有選擇權的 Delta 貢獻
        # futures_delta: 期貨倉位的 Delta (期貨 Delta = 1)
        option_delta = avg_delta
        futures_delta = 1.0 if self.position else 0.0

        self.portfolio_delta = option_delta + futures_delta * self.position.size if self.position else option_delta

        self.log(f'Portfolio Delta: {self.portfolio_delta:.3f}, Target: {self.params.target_delta}')

        # 重新平衡邏輯
        delta_diff = abs(self.portfolio_delta - self.params.target_delta)

        if delta_diff > self.params.delta_tolerance:
            # Delta 過高，減少多頭部位
            if self.portfolio_delta > self.params.target_delta:
                if self.position:
                    sell_size = int(self.position.size * 0.3)
                    if sell_size > 0:
                        self.order = self.sell(size=sell_size)
                        self.log(f'REDUCE POSITION (Delta too high)')

            # Delta 過低，增加多頭部位
            else:
                cash = self.broker.getcash()
                buy_size = int(cash * 0.2 / self.data.close[0])
                if buy_size > 0:
                    self.order = self.buy(size=buy_size)
                    self.log(f'INCREASE POSITION (Delta too low)')
        else:
            self.log(f'Delta within tolerance, no rebalancing needed')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED {order.executed.price:.2f}')
            self.order = None

    def log(self, txt):
        dt = self.data.datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
`
  }
]

// 計算屬性：篩選後的範本
const filteredTemplates = computed(() => {
  let result = templates

  // 分類篩選
  if (selectedCategory.value !== 'all') {
    result = result.filter(t => t.category === selectedCategory.value)
  }

  // 難度篩選
  if (selectedDifficulty.value !== 'all') {
    result = result.filter(t => t.difficulty === selectedDifficulty.value)
  }

  // 搜尋篩選
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(t =>
      t.name.toLowerCase().includes(query) ||
      t.description.toLowerCase().includes(query) ||
      t.tags.some(tag => tag.toLowerCase().includes(query))
    )
  }

  return result
})

// Phase 2 進階: 比較表格指標配置
const comparisonMetrics = [
  {
    category: '收益指標',
    icon: '💰',
    metrics: [
      { label: '年化報酬', key: 'annualReturn' as keyof StrategyTemplate['metrics'] },
      { label: '總報酬', key: 'totalReturn' as keyof StrategyTemplate['metrics'] },
      { label: '月均報酬', key: 'monthlyReturn' as keyof StrategyTemplate['metrics'] }
    ]
  },
  {
    category: '風險指標',
    icon: '⚠️',
    metrics: [
      { label: '夏普比率', key: 'sharpe' as keyof StrategyTemplate['metrics'] },
      { label: '最大回撤', key: 'maxDrawdown' as keyof StrategyTemplate['metrics'] },
      { label: '年化波動率', key: 'volatility' as keyof StrategyTemplate['metrics'] },
      { label: 'Sortino Ratio', key: 'sortinoRatio' as keyof StrategyTemplate['metrics'] }
    ]
  },
  {
    category: '交易指標',
    icon: '📈',
    metrics: [
      { label: '勝率', key: 'winRate' as keyof StrategyTemplate['metrics'] },
      { label: '總交易次數', key: 'totalTrades' as keyof StrategyTemplate['metrics'] },
      { label: '平均獲利', key: 'avgWin' as keyof StrategyTemplate['metrics'] },
      { label: '平均虧損', key: 'avgLoss' as keyof StrategyTemplate['metrics'] }
    ]
  },
  {
    category: '綜合評估',
    icon: '⭐',
    metrics: [
      { label: '盈虧比', key: 'winLossRatio' as keyof StrategyTemplate['metrics'] },
      { label: '獲利因子', key: 'profitFactor' as keyof StrategyTemplate['metrics'] },
      { label: '期望值', key: 'expectancy' as keyof StrategyTemplate['metrics'] }
    ]
  }
]

// 方法
const togglePreview = (templateId: string) => {
  expandedTemplate.value = expandedTemplate.value === templateId ? null : templateId
}

const getDifficultyLabel = (difficulty: string) => {
  const labels: Record<string, string> = {
    'beginner': '入門',
    'intermediate': '中級',
    'advanced': '進階'
  }
  return labels[difficulty] || difficulty
}

const copyCode = (code: string) => {
  navigator.clipboard.writeText(code)
  alert('代碼已複製到剪貼簿！')
}

const resetFilters = () => {
  searchQuery.value = ''
  selectedCategory.value = 'all'
  selectedDifficulty.value = 'all'
}

// Phase 2 進階: 開啟/關閉詳細績效模態框
const openMetricsModal = (template: StrategyTemplate) => {
  selectedTemplateForMetrics.value = template
  showMetricsModal.value = true
}

const closeMetricsModal = () => {
  showMetricsModal.value = false
  selectedTemplateForMetrics.value = null
}

// Phase 2 進階: 範本比較功能
const toggleComparisonMode = () => {
  comparisonMode.value = !comparisonMode.value
  if (!comparisonMode.value) {
    // 離開比較模式時清空選擇
    selectedTemplatesForComparison.value = []
  }
}

const toggleTemplateSelection = (template: StrategyTemplate) => {
  const index = selectedTemplatesForComparison.value.findIndex(t => t.id === template.id)
  if (index > -1) {
    // 已選擇，移除
    selectedTemplatesForComparison.value.splice(index, 1)
  } else {
    // 未選擇，添加（最多 4 個）
    if (selectedTemplatesForComparison.value.length < 4) {
      selectedTemplatesForComparison.value.push(template)
    } else {
      if (process.client) {
        alert('最多只能比較 4 個範本')
      }
    }
  }
}

const isTemplateSelected = (template: StrategyTemplate) => {
  return selectedTemplatesForComparison.value.some(t => t.id === template.id)
}

const openComparisonTable = () => {
  if (selectedTemplatesForComparison.value.length < 2) {
    if (process.client) {
      alert('請至少選擇 2 個範本進行比較')
    }
    return
  }
  showComparisonTable.value = true
}

const closeComparisonTable = () => {
  showComparisonTable.value = false
}

const clearComparison = () => {
  selectedTemplatesForComparison.value = []
  showComparisonTable.value = false
}

// Phase 2 進階: 鍵盤導航支持 - ESC 鍵關閉模態框
const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    // 優先關閉比較表格（如果打開）
    if (showComparisonTable.value) {
      closeComparisonTable()
    }
    // 否則關閉詳細績效模態框（如果打開）
    else if (showMetricsModal.value) {
      closeMetricsModal()
    }
  }
}

// 組件掛載時添加鍵盤事件監聽器
onMounted(() => {
  if (process.client) {
    window.addEventListener('keydown', handleKeydown)
  }
})

// 組件卸載時移除鍵盤事件監聽器
onUnmounted(() => {
  if (process.client) {
    window.removeEventListener('keydown', handleKeydown)
  }
})

// 判斷某個指標在所有選擇的範本中是否為最佳值
const isBestValue = (metricKey: string, value: string | undefined, templates: StrategyTemplate[]) => {
  if (!value || value === 'N/A') return false

  // 提取數值部分（移除 %, +, 天, 次等單位，保留負號）
  const parseValue = (str: string): number => {
    // 保留負號，只移除 +, %, 天, 次等單位符號和多餘空白
    const cleaned = str.replace(/[+%天次]/g, '').replace(/\s+/g, '').trim()
    return parseFloat(cleaned) || 0
  }

  const currentValue = parseValue(value)
  const allValues = templates
    .map(t => t.metrics?.[metricKey as keyof typeof t.metrics])
    .filter((v): v is string => v !== undefined && v !== 'N/A')
    .map(parseValue)

  // 空陣列檢查：如果沒有可比較的值，返回 false
  if (allValues.length === 0) return false

  // 根據指標類型判斷是越大越好還是越小越好
  const smallerIsBetter = ['maxDrawdown', 'volatility', 'downsideDeviation', 'avgLoss', 'maxConsecutiveLosses', 'var95', 'risk']
  const isSmallerBetter = smallerIsBetter.includes(metricKey)

  // 使用 epsilon 比較避免浮點數精度問題
  const epsilon = 0.0001

  if (isSmallerBetter) {
    // 最小值最好（對於回撤、風險等指標）
    const minValue = Math.min(...allValues)
    return Math.abs(currentValue - minValue) < epsilon
  } else {
    // 最大值最好（對於報酬、夏普等指標）
    const maxValue = Math.max(...allValues)
    return Math.abs(currentValue - maxValue) < epsilon
  }
}
</script>

<style scoped lang="scss">
.strategy-templates-enhanced {
  width: 100%;
}

.templates-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;

  h3 {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 0.5rem;
  }

  .description {
    color: #6b7280;
    font-size: 0.875rem;
  }
}

/* Phase 2 進階: 比較模式按鈕 */
.btn-comparison-mode {
  padding: 0.75rem 1.5rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;

  &:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  &.active {
    background: #3b82f6;
    border-color: #3b82f6;
    color: white;
  }
}

// 篩選區
.filters-section {
  background: #f9fafb;
  padding: 1.5rem;
  border-radius: 0.75rem;
  margin-bottom: 2rem;
  border: 1px solid #e5e7eb;
}

.search-box {
  position: relative;
  margin-bottom: 1rem;

  .search-input {
    width: 100%;
    padding: 0.75rem 1rem;
    padding-right: 3rem;
    border: 2px solid #e5e7eb;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    transition: border-color 0.2s;

    &:focus {
      outline: none;
      border-color: #3b82f6;
    }
  }

  .search-icon {
    position: absolute;
    right: 1rem;
    top: 50%;
    transform: translateY(-50%);
    font-size: 1.25rem;
  }
}

.filter-tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.filter-tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  &.active {
    background: #3b82f6;
    border-color: #3b82f6;
    color: white;
  }

  .tab-icon {
    font-size: 1.125rem;
  }
}

.difficulty-filter {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.difficulty-btn {
  padding: 0.5rem 1rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &.beginner {
    color: #059669;

    &.active {
      background: #10b981;
      border-color: #10b981;
      color: white;
    }
  }

  &.intermediate {
    color: #d97706;

    &.active {
      background: #f59e0b;
      border-color: #f59e0b;
      color: white;
    }
  }

  &.advanced {
    color: #dc2626;

    &.active {
      background: #ef4444;
      border-color: #ef4444;
      color: white;
    }
  }

  &.all {
    color: #6b7280;

    &.active {
      background: #6b7280;
      border-color: #6b7280;
      color: white;
    }
  }
}

// 範本網格
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.template-card {
  border: 2px solid #e5e7eb;
  border-radius: 0.75rem;
  background: white;
  overflow: hidden;
  transition: all 0.3s;

  &:hover {
    border-color: #3b82f6;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem;
  border-bottom: 1px solid #f3f4f6;
}

.template-icon {
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;

  &.trend {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  &.mean-reversion {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: white;
  }

  &.breakout {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    color: white;
  }

  &.ml {
    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    color: white;
  }

  svg {
    width: 1.75rem !important;
    height: 1.75rem !important;
    flex-shrink: 0;
  }
}

.difficulty-badge {
  padding: 0.375rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 600;

  &.beginner {
    background: #d1fae5;
    color: #065f46;
  }

  &.intermediate {
    background: #fed7aa;
    color: #92400e;
  }

  &.advanced {
    background: #fee2e2;
    color: #991b1b;
  }
}

.card-body {
  padding: 1.25rem;
}

.template-name {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 0.75rem;
}

.template-description {
  font-size: 0.875rem;
  color: #6b7280;
  line-height: 1.5;
  margin-bottom: 1rem;
}

.template-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;

  .tag {
    font-size: 0.75rem;
    padding: 0.25rem 0.625rem;
    background: #f3f4f6;
    color: #4b5563;
    border-radius: 0.25rem;
    font-weight: 500;
  }
}

.metrics-preview {
  display: flex;
  gap: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid #f3f4f6;
}

.metric-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;

  .metric-label {
    font-size: 0.75rem;
    color: #9ca3af;
    font-weight: 500;
  }

  .metric-value {
    font-size: 0.875rem;
    font-weight: 600;
    color: #1f2937;

    &.risk-低 {
      color: #059669;
    }

    &.risk-中低 {
      color: #10b981;
    }

    &.risk-中 {
      color: #f59e0b;
    }

    &.risk-中高 {
      color: #f97316;
    }

    &.risk-高 {
      color: #ef4444;
    }
  }
}

.card-actions {
  display: flex;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid #f3f4f6;
}

.btn-use {
  flex: 1;
  padding: 0.75rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #2563eb;
  }
}

.btn-preview {
  padding: 0.75rem 1rem;
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #e5e7eb;
  }
}

.code-preview {
  border-top: 2px solid #f3f4f6;
  background: #1f2937;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.25rem;
  background: #111827;
  color: #9ca3af;
  font-size: 0.875rem;
  font-weight: 500;
}

.btn-copy {
  padding: 0.375rem 0.75rem;
  background: #374151;
  color: #d1d5db;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #4b5563;
  }
}

.code-block {
  margin: 0;
  padding: 1.25rem;
  background: #1f2937;
  color: #e5e7eb;
  font-size: 0.8125rem;
  line-height: 1.6;
  overflow-x: auto;
  max-height: 400px;

  code {
    font-family: 'Monaco', 'Courier New', monospace;
  }
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  p {
    color: #6b7280;
    font-size: 1rem;
    margin-bottom: 1.5rem;
  }

  .btn-reset {
    padding: 0.75rem 1.5rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 0.5rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: #2563eb;
    }
  }
}

/* Phase 2: 增強的績效指標樣式 */
.metrics-preview-enhanced {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #f3f4f6;
}

.metrics-row-top,
.metrics-row-bottom {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.metrics-row-bottom {
  margin-bottom: 0;
}

.metric-item-small {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem;
  background: #f9fafb;
  border-radius: 0.375rem;
}

.metric-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.metric-content-small {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.metric-label-small {
  font-size: 0.6875rem;
  color: #9ca3af;
  font-weight: 500;
  white-space: nowrap;
}

.metric-value-small {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #1f2937;
}

.metric-value-strong {
  font-size: 0.875rem;
  font-weight: 700;
  color: #3b82f6;
}

/* Phase 2 進階: 查看完整績效按鈕 */
.metrics-action {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid #f3f4f6;
  background: #fafafa;
}

.btn-metrics {
  width: 100%;
  padding: 0.625rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }
}

/* Phase 2 進階: 詳細績效模態框樣式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 2rem;
  overflow-y: auto;
}

.modal-container {
  background: white;
  border-radius: 1rem;
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: modalFadeIn 0.3s ease-out;
}

@keyframes modalFadeIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 2px solid #f3f4f6;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 1rem 1rem 0 0;

  .modal-title-section {
    display: flex;
    align-items: center;
    gap: 1rem;

    h3 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 700;
    }

    .difficulty-badge {
      background: rgba(255, 255, 255, 0.25);
      color: white;
      border: 1px solid rgba(255, 255, 255, 0.3);
    }
  }

  .btn-close {
    background: rgba(255, 255, 255, 0.2);
    border: none;
    color: white;
    font-size: 1.5rem;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;

    &:hover {
      background: rgba(255, 255, 255, 0.3);
      transform: rotate(90deg);
    }
  }
}

.modal-body {
  padding: 2rem;
  max-height: calc(90vh - 200px);
  overflow-y: auto;
}

.metrics-category {
  margin-bottom: 2rem;

  &:last-child {
    margin-bottom: 0;
  }
}

.category-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e5e7eb;

  .category-icon {
    font-size: 1.5rem;
  }

  h4 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 700;
    color: #1f2937;
  }
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.metric-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1rem;
  transition: all 0.2s;

  &:hover {
    border-color: #3b82f6;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
  }

  .metric-label {
    font-size: 0.8125rem;
    color: #6b7280;
    font-weight: 500;
    margin-bottom: 0.5rem;
  }

  .metric-value {
    font-size: 1.125rem;
    font-weight: 700;
    color: #1f2937;

    &.highlight {
      color: #3b82f6;
    }

    &.success {
      color: #10b981;
    }

    &.danger {
      color: #ef4444;
    }
  }
}

.modal-footer {
  display: flex;
  gap: 1rem;
  padding: 1.5rem 2rem;
  border-top: 2px solid #f3f4f6;
  background: #fafafa;
  border-radius: 0 0 1rem 1rem;
}

.btn-use-modal {
  flex: 1;
  padding: 0.875rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #2563eb;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  }
}

.btn-close-modal {
  padding: 0.875rem 1.5rem;
  background: #e5e7eb;
  color: #374151;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #d1d5db;
  }
}

/* Phase 2 進階: 範本比較功能樣式 */

/* 複選框 */
.comparison-checkbox {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 10;

  input[type="checkbox"] {
    display: none;

    + label {
      width: 1.75rem;
      height: 1.75rem;
      border: 2px solid #d1d5db;
      border-radius: 0.375rem;
      background: white;
      display: inline-block;
      cursor: pointer;
      position: relative;
      transition: all 0.2s;

      &:hover {
        border-color: #3b82f6;
      }

      &::after {
        content: '✓';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) scale(0);
        color: white;
        font-size: 1rem;
        font-weight: 700;
        transition: transform 0.2s;
      }
    }

    &:checked + label {
      background: #3b82f6;
      border-color: #3b82f6;

      &::after {
        transform: translate(-50%, -50%) scale(1);
      }
    }
  }
}

/* 已選擇的卡片高亮 */
.template-card.selected {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* 浮動比較欄 */
.comparison-bar {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  max-width: 800px;
  width: calc(100% - 4rem);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translate(-50%, 100%);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}

.comparison-bar-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1.25rem 1.75rem;
  border-radius: 1rem;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
}

.comparison-info {
  display: flex;
  align-items: center;
  gap: 1rem;

  .comparison-icon {
    font-size: 1.5rem;
  }

  .comparison-text {
    font-weight: 600;
    font-size: 1rem;

    .comparison-hint {
      font-weight: 400;
      opacity: 0.9;
      font-size: 0.875rem;
      margin-left: 0.5rem;
    }
  }
}

.comparison-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-compare {
  padding: 0.75rem 1.5rem;
  background: white;
  color: #667eea;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: #f3f4f6;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.btn-clear {
  padding: 0.75rem 1.5rem;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.3);
  }
}

/* 比較表格模態框 */
.comparison-modal-container {
  background: white;
  border-radius: 1rem;
  max-width: 1200px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: modalFadeIn 0.3s ease-out;
  display: flex;
  flex-direction: column;
}

.comparison-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.comparison-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.comparison-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;

  thead {
    position: sticky;
    top: 0;
    background: #f9fafb;
    z-index: 10;

    th {
      padding: 1.25rem 1rem;
      text-align: left;
      font-weight: 600;
      color: #1f2937;
      border-bottom: 2px solid #e5e7eb;

      &.metric-name-col {
        width: 200px;
        background: #f9fafb;
        position: sticky;
        left: 0;
        z-index: 11;
      }

      &.template-col {
        min-width: 200px;
        text-align: center;
      }
    }
  }

  tbody {
    tr {
      transition: background 0.15s;

      &:hover:not(.category-row) {
        background: #f9fafb;
      }

      &.category-row {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);

        .category-header-cell {
          padding: 0.875rem 1rem;
          font-weight: 700;
          color: #667eea;
          font-size: 1rem;

          .category-icon {
            margin-right: 0.5rem;
            font-size: 1.125rem;
          }
        }
      }
    }

    td {
      padding: 0.875rem 1rem;
      border-bottom: 1px solid #f3f4f6;
      text-align: center;

      &.metric-name {
        font-weight: 500;
        color: #6b7280;
        text-align: left;
        background: white;
        position: sticky;
        left: 0;
        z-index: 5;
        border-right: 1px solid #f3f4f6;
      }

      &.best-value {
        background: linear-gradient(135deg, #10b98115 0%, #05966915 100%);
        color: #065f46;
        font-weight: 700;
        position: relative;

        &::before {
          content: '👑';
          position: absolute;
          top: 0.25rem;
          right: 0.25rem;
          font-size: 0.75rem;
        }
      }
    }
  }
}

.template-header-cell {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;

  .template-name {
    font-size: 0.9375rem;
    font-weight: 700;
    color: #1f2937;
  }

  .template-meta {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    justify-content: center;
  }

  .category-badge {
    padding: 0.25rem 0.625rem;
    background: #f3f4f6;
    color: #6b7280;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 500;
  }
}

</style>
