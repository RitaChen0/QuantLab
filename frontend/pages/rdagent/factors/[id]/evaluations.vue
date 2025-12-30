<template>
  <div class="evaluations-page">
    <!-- 頂部導航欄 -->
    <AppHeader />

    <!-- 麵包屑 -->
    <div class="breadcrumb">
      <NuxtLink to="/rdagent">自動研發</NuxtLink>
      <span class="separator">›</span>
      <NuxtLink to="/rdagent?tab=factors">因子列表</NuxtLink>
      <span class="separator">›</span>
      <span class="current">評估歷史</span>
    </div>

    <!-- 載入中 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>載入評估歷史中...</p>
    </div>

    <!-- 錯誤訊息 -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <NuxtLink to="/rdagent?tab=factors" class="btn-back">返回因子列表</NuxtLink>
    </div>

    <!-- 內容 -->
    <div v-else class="content">
      <!-- 因子資訊 -->
      <div v-if="factor" class="factor-info">
        <h1>{{ factor.name }}</h1>
        <p class="factor-description">{{ factor.description }}</p>
        <div class="factor-formula">
          <strong>公式：</strong>
          <code>{{ factor.formula }}</code>
        </div>
        <div v-if="factor.ic !== null" class="factor-current-metrics">
          <div class="metric-card">
            <div class="metric-label">IC</div>
            <div class="metric-value">{{ factor.ic.toFixed(4) }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">ICIR</div>
            <div class="metric-value">{{ factor.icir ? factor.icir.toFixed(4) : 'N/A' }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Sharpe Ratio</div>
            <div class="metric-value">{{ factor.sharpe_ratio ? factor.sharpe_ratio.toFixed(2) : 'N/A' }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">年化報酬</div>
            <div class="metric-value">{{ factor.annual_return ? (factor.annual_return * 100).toFixed(2) + '%' : 'N/A' }}</div>
          </div>
        </div>
      </div>

      <!-- IC 衰減分析按鈕 -->
      <div class="actions">
        <button @click="analyzeICDecay" class="btn-ic-decay" :disabled="analyzingDecay">
          <span v-if="analyzingDecay">⏳ 分析中...</span>
          <span v-else>📈 IC 衰減分析</span>
        </button>
      </div>

      <!-- IC 衰減分析圖表 -->
      <div v-if="icDecayData" class="ic-decay-section">
        <h2>📈 IC 衰減分析</h2>
        <p class="section-description">
          分析因子在不同持有期（1-{{ icDecayData.lags[icDecayData.lags.length - 1] }} 天）下的預測能力衰減情況
        </p>
        <div class="chart-container">
          <canvas ref="icDecayChart"></canvas>
        </div>
        <div class="decay-insights">
          <h3>🔍 分析洞察</h3>
          <div class="insights-grid">
            <div class="insight-card">
              <div class="insight-label">最佳持有期</div>
              <div class="insight-value">{{ bestHoldingPeriod }} 天</div>
            </div>
            <div class="insight-card">
              <div class="insight-label">最大 IC</div>
              <div class="insight-value">{{ maxIC.toFixed(4) }}</div>
            </div>
            <div class="insight-card">
              <div class="insight-label">因子類型</div>
              <div class="insight-value">{{ factorType }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 評估歷史表格 -->
      <div class="evaluations-section">
        <h2>📊 評估歷史記錄</h2>
        <div v-if="evaluations.length === 0" class="empty-state">
          此因子尚無評估記錄
        </div>
        <div v-else class="evaluations-table">
          <table>
            <thead>
              <tr>
                <th>評估時間</th>
                <th>股票池</th>
                <th>IC</th>
                <th>ICIR</th>
                <th>Rank IC</th>
                <th>Rank ICIR</th>
                <th>Sharpe Ratio</th>
                <th>年化報酬</th>
                <th>最大回撤</th>
                <th>勝率</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="evaluation in evaluations" :key="evaluation.id">
                <td>{{ formatDate(evaluation.created_at) }}</td>
                <td>{{ getStockPoolLabel(evaluation.stock_pool) }}</td>
                <td :class="getICClass(evaluation.ic)">{{ evaluation.ic ? evaluation.ic.toFixed(4) : 'N/A' }}</td>
                <td>{{ evaluation.icir ? evaluation.icir.toFixed(4) : 'N/A' }}</td>
                <td>{{ evaluation.rank_ic ? evaluation.rank_ic.toFixed(4) : 'N/A' }}</td>
                <td>{{ evaluation.rank_icir ? evaluation.rank_icir.toFixed(4) : 'N/A' }}</td>
                <td :class="getSharpeClass(evaluation.sharpe_ratio)">{{ evaluation.sharpe_ratio ? evaluation.sharpe_ratio.toFixed(2) : 'N/A' }}</td>
                <td :class="getReturnClass(evaluation.annual_return)">{{ evaluation.annual_return ? (evaluation.annual_return * 100).toFixed(2) + '%' : 'N/A' }}</td>
                <td :class="getDrawdownClass(evaluation.max_drawdown)">{{ evaluation.max_drawdown ? (evaluation.max_drawdown * 100).toFixed(2) + '%' : 'N/A' }}</td>
                <td>{{ evaluation.win_rate ? (evaluation.win_rate * 100).toFixed(2) + '%' : 'N/A' }}</td>
                <td>
                  <button @click="deleteEvaluation(evaluation.id)" class="btn-delete">
                    🗑️
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Chart from 'chart.js/auto'

const config = useRuntimeConfig()
const route = useRoute()
const router = useRouter()

const factorId = computed(() => parseInt(route.params.id as string))
const factor = ref(null)
const evaluations = ref([])
const loading = ref(true)
const error = ref('')
const analyzingDecay = ref(false)
const icDecayData = ref(null)
const icDecayChart = ref(null)
let chartInstance = null

// 載入因子資訊
const loadFactor = async () => {
  try {
    const token = localStorage.getItem('access_token')
    factor.value = await $fetch(`${config.public.apiBase}/api/v1/rdagent/factors/${factorId.value}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
  } catch (err: any) {
    console.error('Failed to load factor:', err)
    error.value = '無法載入因子資訊'
  }
}

// 載入評估歷史
const loadEvaluations = async () => {
  try {
    const token = localStorage.getItem('access_token')
    evaluations.value = await $fetch(
      `${config.public.apiBase}/api/v1/factor-evaluation/factor/${factorId.value}/evaluations`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    )
  } catch (err: any) {
    console.error('Failed to load evaluations:', err)
  }
}

// 格式化日期
const formatDate = (dateStr: string) => {
  if (!dateStr) return 'N/A'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 股票池標籤
const getStockPoolLabel = (pool: string) => {
  const labels = {
    'all': '全市場',
    'top100': '前 100 大',
    'mid_cap': '中型股',
    'high_liquid': '高流動性'
  }
  return labels[pool] || pool
}

// IC 類別
const getICClass = (ic: number) => {
  if (!ic) return ''
  if (ic > 0.05) return 'value-good'
  if (ic > 0.03) return 'value-fair'
  return 'value-poor'
}

// Sharpe 類別
const getSharpeClass = (sharpe: number) => {
  if (!sharpe) return ''
  if (sharpe > 1.5) return 'value-good'
  if (sharpe > 1.0) return 'value-fair'
  return 'value-poor'
}

// 報酬類別
const getReturnClass = (returnVal: number) => {
  if (!returnVal) return ''
  if (returnVal > 0.15) return 'value-good'
  if (returnVal > 0.08) return 'value-fair'
  if (returnVal < 0) return 'value-poor'
  return ''
}

// 回撤類別
const getDrawdownClass = (dd: number) => {
  if (!dd) return ''
  if (dd < 0.1) return 'value-good'
  if (dd < 0.2) return 'value-fair'
  return 'value-poor'
}

// 刪除評估記錄
const deleteEvaluation = async (evaluationId: number) => {
  if (!confirm('確定要刪除此評估記錄嗎？')) return

  try {
    const token = localStorage.getItem('access_token')
    await $fetch(
      `${config.public.apiBase}/api/v1/factor-evaluation/evaluation/${evaluationId}`,
      {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      }
    )

    alert('評估記錄已刪除')
    await loadEvaluations()
  } catch (err: any) {
    alert('刪除失敗：' + (err.data?.detail || err.message || '未知錯誤'))
  }
}

// IC 衰減分析
const analyzeICDecay = async () => {
  analyzingDecay.value = true

  try {
    const token = localStorage.getItem('access_token')
    const response = await $fetch(`${config.public.apiBase}/api/v1/factor-evaluation/ic-decay`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: {
        factor_id: factorId.value,
        stock_pool: 'all',
        max_lag: 20
      }
    })

    icDecayData.value = response

    // 等待 DOM 更新
    await nextTick()

    // 繪製圖表
    renderICDecayChart()
  } catch (err: any) {
    alert('IC 衰減分析失敗：' + (err.data?.detail || err.message || '未知錯誤'))
  } finally {
    analyzingDecay.value = false
  }
}

// 繪製 IC 衰減圖表
const renderICDecayChart = () => {
  if (!icDecayChart.value || !icDecayData.value) return

  // 銷毀舊圖表
  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = icDecayChart.value.getContext('2d')

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: icDecayData.value.lags,
      datasets: [
        {
          label: 'IC',
          data: icDecayData.value.ic_values,
          borderColor: 'rgb(102, 126, 234)',
          backgroundColor: 'rgba(102, 126, 234, 0.1)',
          tension: 0.4,
          fill: true
        },
        {
          label: 'Rank IC',
          data: icDecayData.value.rank_ic_values,
          borderColor: 'rgb(245, 87, 108)',
          backgroundColor: 'rgba(245, 87, 108, 0.1)',
          tension: 0.4,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'IC 衰減曲線'
        },
        legend: {
          position: 'top'
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: '持有期（天）'
          }
        },
        y: {
          title: {
            display: true,
            text: 'IC 值'
          }
        }
      }
    }
  })
}

// 最佳持有期
const bestHoldingPeriod = computed(() => {
  if (!icDecayData.value) return 0

  const maxIndex = icDecayData.value.ic_values.indexOf(
    Math.max(...icDecayData.value.ic_values)
  )
  return icDecayData.value.lags[maxIndex]
})

// 最大 IC
const maxIC = computed(() => {
  if (!icDecayData.value) return 0
  return Math.max(...icDecayData.value.ic_values)
})

// 因子類型
const factorType = computed(() => {
  if (!icDecayData.value) return 'N/A'

  const icValues = icDecayData.value.ic_values
  const firstIC = icValues[0]
  const lastIC = icValues[icValues.length - 1]

  // 衰減速度計算
  const decayRate = (firstIC - lastIC) / firstIC

  if (decayRate > 0.5) {
    return '短期因子'
  } else if (decayRate > 0.2) {
    return '中期因子'
  } else {
    return '長期因子'
  }
})

// 初始化
onMounted(async () => {
  loading.value = true
  await Promise.all([loadFactor(), loadEvaluations()])
  loading.value = false
})
</script>

<style scoped lang="scss">
.evaluations-page {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 2rem;
  font-size: 0.875rem;
  color: #6b7280;

  a {
    color: #3b82f6;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  .separator {
    color: #9ca3af;
  }

  .current {
    color: #111827;
    font-weight: 500;
  }
}

.loading-state,
.error-state {
  text-align: center;
  padding: 4rem 0;

  .spinner {
    border: 4px solid #f3f4f6;
    border-top: 4px solid #3b82f6;
    border-radius: 50%;
    width: 3rem;
    height: 3rem;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.btn-back {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border-radius: 0.375rem;
  text-decoration: none;
  margin-top: 1rem;

  &:hover {
    background: #2563eb;
  }
}

.factor-info {
  background: white;
  border-radius: 0.75rem;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;

  h1 {
    margin: 0 0 1rem 0;
    color: #111827;
  }

  .factor-description {
    color: #6b7280;
    margin-bottom: 1rem;
  }

  .factor-formula {
    background: #f9fafb;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1.5rem;

    strong {
      display: block;
      margin-bottom: 0.5rem;
      color: #374151;
    }

    code {
      font-family: 'Monaco', 'Courier New', monospace;
      font-size: 0.875rem;
      color: #1f2937;
    }
  }

  .factor-current-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;

    .metric-card {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 1rem;
      border-radius: 0.5rem;
      text-align: center;

      .metric-label {
        font-size: 0.875rem;
        opacity: 0.9;
        margin-bottom: 0.5rem;
      }

      .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
      }
    }
  }
}

.actions {
  margin-bottom: 2rem;

  .btn-ic-decay {
    padding: 0.75rem 1.5rem;
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: white;
    border: none;
    border-radius: 0.375rem;
    cursor: pointer;
    font-weight: 500;
    font-size: 1rem;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(245, 87, 108, 0.4);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
}

.ic-decay-section {
  background: white;
  border-radius: 0.75rem;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;

  h2 {
    margin: 0 0 0.5rem 0;
    color: #111827;
  }

  .section-description {
    color: #6b7280;
    margin-bottom: 1.5rem;
  }

  .chart-container {
    height: 400px;
    margin-bottom: 2rem;
  }

  .decay-insights {
    h3 {
      margin: 0 0 1rem 0;
      color: #374151;
    }

    .insights-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;

      .insight-card {
        background: #f9fafb;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;

        .insight-label {
          font-size: 0.875rem;
          color: #6b7280;
          margin-bottom: 0.5rem;
        }

        .insight-value {
          font-size: 1.25rem;
          font-weight: 700;
          color: #111827;
        }
      }
    }
  }
}

.evaluations-section {
  background: white;
  border-radius: 0.75rem;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

  h2 {
    margin: 0 0 1.5rem 0;
    color: #111827;
  }

  .empty-state {
    text-align: center;
    padding: 3rem 0;
    color: #6b7280;
  }

  .evaluations-table {
    overflow-x: auto;

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;

      thead {
        background: #f9fafb;

        th {
          padding: 0.75rem 1rem;
          text-align: left;
          font-weight: 600;
          color: #374151;
          border-bottom: 2px solid #e5e7eb;
          white-space: nowrap;
        }
      }

      tbody {
        tr {
          border-bottom: 1px solid #e5e7eb;
          transition: background 0.2s;

          &:hover {
            background: #f9fafb;
          }
        }

        td {
          padding: 0.75rem 1rem;
          color: #6b7280;
          white-space: nowrap;

          &.value-good {
            color: #059669;
            font-weight: 600;
          }

          &.value-fair {
            color: #d97706;
            font-weight: 600;
          }

          &.value-poor {
            color: #dc2626;
            font-weight: 600;
          }
        }
      }

      .btn-delete {
        padding: 0.25rem 0.5rem;
        background: transparent;
        border: none;
        cursor: pointer;
        font-size: 1rem;
        opacity: 0.6;
        transition: opacity 0.2s;

        &:hover {
          opacity: 1;
        }
      }
    }
  }
}
</style>
