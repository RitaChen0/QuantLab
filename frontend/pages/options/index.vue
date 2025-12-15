<template>
  <div class="dashboard-container">
    <!-- 頂部導航欄 -->
    <AppHeader />

    <!-- 主要內容區 -->
    <main class="dashboard-main">
      <div class="page-container">
        <!-- 頁面標題 -->
        <div class="page-header">
          <div>
            <h1 class="page-title">選擇權 Option Chain</h1>
            <p class="page-subtitle">查詢台指選擇權（TXO）價格、PCR 因子與市場情緒</p>
          </div>

          <!-- 階段資訊 -->
          <div v-if="stageInfo" class="stage-badge">
            <span class="badge">階段 {{ stageInfo.stage }}</span>
            <span class="feature-list">{{ stageInfo.available_factors.length }} 個因子可用</span>
          </div>
        </div>

        <!-- 控制面板 -->
        <div class="control-panel">
          <!-- 標的物選擇 -->
          <div class="control-group">
            <label class="control-label">標的物：</label>
            <div class="btn-group">
              <button
                v-for="u in underlyings"
                :key="u.id"
                @click="selectUnderlying(u.id)"
                :class="['btn-underlying', { active: selectedUnderlying === u.id }]"
              >
                {{ u.id }} - {{ u.name }}
              </button>
            </div>
          </div>

          <!-- 到期日選擇 -->
          <div class="control-group">
            <label class="control-label">到期日：</label>
            <select
              v-model="selectedExpiry"
              @change="loadOptionChain"
              class="expiry-select"
              :disabled="loadingExpiries || !selectedUnderlying"
            >
              <option value="">{{ loadingExpiries ? '載入中...' : '請選擇到期日' }}</option>
              <option v-for="date in expiryDates" :key="date" :value="date">
                {{ formatDate(date) }}
              </option>
            </select>
            <button
              @click="loadExpiryDates"
              class="btn-refresh"
              :disabled="!selectedUnderlying"
            >
              🔄 重新載入
            </button>
          </div>

          <!-- 自動刷新 -->
          <div class="control-group">
            <label class="control-label">自動刷新：</label>
            <button
              @click="toggleAutoRefresh"
              :class="['btn-auto-refresh', { active: autoRefreshEnabled }]"
              :disabled="!selectedUnderlying"
            >
              {{ autoRefreshEnabled ? '⏸️ 停止' : '▶️ 開始' }} ({{ refreshInterval }}s)
            </button>
          </div>

          <!-- 篩選控件 -->
          <div class="control-group filter-group">
            <label class="control-label">篩選履約價：</label>
            <div class="filter-inputs">
              <input
                v-model.number="filterMinStrike"
                type="number"
                placeholder="最小"
                class="filter-input"
                :disabled="!optionChain"
              />
              <span class="filter-separator">~</span>
              <input
                v-model.number="filterMaxStrike"
                type="number"
                placeholder="最大"
                class="filter-input"
                :disabled="!optionChain"
              />
              <button @click="resetFilters" class="btn-reset-filter" :disabled="!optionChain">
                🔄 重置
              </button>
            </div>
          </div>
        </div>

        <!-- 市場情緒儀表板 -->
        <div v-if="factorSummary" class="sentiment-dashboard">
          <div class="sentiment-card">
            <div class="sentiment-icon">{{ getSentimentEmoji(factorSummary.sentiment) }}</div>
            <div class="sentiment-info">
              <div class="sentiment-label">市場情緒</div>
              <div class="sentiment-value" :class="`sentiment-${factorSummary.sentiment}`">
                {{ getSentimentText(factorSummary.sentiment) }}
              </div>
            </div>
          </div>

          <div class="factor-card">
            <div class="factor-label">PCR Volume</div>
            <div class="factor-value">{{ formatNumber(factorSummary.pcr_volume) }}</div>
            <div class="factor-hint">{{ getPCRHint(factorSummary.pcr_volume) }}</div>
          </div>

          <div class="factor-card">
            <div class="factor-label">PCR Open Interest</div>
            <div class="factor-value">{{ formatNumber(factorSummary.pcr_open_interest) }}</div>
          </div>

          <div class="factor-card">
            <div class="factor-label">ATM IV</div>
            <div class="factor-value">{{ formatNumber(factorSummary.atm_iv) }}%</div>
            <div class="factor-hint">隱含波動率</div>
          </div>

          <div class="factor-card">
            <div class="factor-label">資料品質</div>
            <div class="factor-value">{{ formatPercent(factorSummary.data_quality_score) }}</div>
          </div>

          <div class="factor-card">
            <div class="factor-label">資料日期</div>
            <div class="factor-value small">{{ formatDate(factorSummary.date) }}</div>
          </div>
        </div>

        <!-- Option Chain 表格 -->
        <div v-if="optionChain" class="option-chain-container">
          <div class="chain-header">
            <div>
              <h3>Option Chain - {{ selectedUnderlying }} ({{ formatDate(selectedExpiry) }})</h3>
              <div class="spot-price" v-if="optionChain.spot_price">
                現價：<span class="price-value">{{ optionChain.spot_price }}</span>
              </div>
            </div>
            <button @click="exportToCSV" class="btn-export">
              📥 匯出 CSV
            </button>
          </div>

          <div class="chain-table-wrapper">
            <table class="chain-table">
              <thead>
                <tr>
                  <th colspan="5" class="section-header call-header">CALL (買權)</th>
                  <th class="strike-header">履約價</th>
                  <th colspan="5" class="section-header put-header">PUT (賣權)</th>
                </tr>
                <tr>
                  <th @click="sortBy('call_volume')" class="sortable">
                    成交量
                    <span v-if="sortField === 'call_volume'" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                  <th @click="sortBy('call_open_interest')" class="sortable">
                    未平倉
                    <span v-if="sortField === 'call_open_interest'" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                  <th @click="sortBy('call_bid_price')" class="sortable">
                    買價
                    <span v-if="sortField === 'call_bid_price'" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                  <th @click="sortBy('call_ask_price')" class="sortable">
                    賣價
                    <span v-if="sortField === 'call_ask_price'" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                  <th @click="sortBy('call_last_price')" class="sortable">
                    成交價
                    <span v-if="sortField === 'call_last_price'" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                  <th @click="sortBy('strike')" class="strike-cell sortable">
                    Strike
                    <span v-if="sortField === 'strike'" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                  <th @click="sortBy('put_last_price')" class="sortable">
                    成交價
                    <span v-if="sortField === 'put_last_price'" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                  <th @click="sortBy('put_ask_price')" class="sortable">
                    賣價
                    <span v-if="sortField === 'put_ask_price'" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                  <th @click="sortBy('put_bid_price')" class="sortable">
                    買價
                    <span v-if="sortField === 'put_bid_price'" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                  <th @click="sortBy('put_open_interest')" class="sortable">
                    未平倉
                    <span v-if="sortField === 'put_open_interest'" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                  <th @click="sortBy('put_volume')" class="sortable">
                    成交量
                    <span v-if="sortField === 'put_volume'" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(strike, index) in filteredStrikeList" :key="strike"
                    :class="{ 'atm-row': isATM(strike) }">
                  <!-- CALL 資料 -->
                  <td>{{ getCallData(strike, 'volume') }}</td>
                  <td>{{ getCallData(strike, 'open_interest') }}</td>
                  <td>{{ getCallData(strike, 'bid_price') }}</td>
                  <td>{{ getCallData(strike, 'ask_price') }}</td>
                  <td class="price-cell call-price">{{ getCallData(strike, 'last_price') }}</td>

                  <!-- 履約價 -->
                  <td class="strike-cell">
                    <strong>{{ strike }}</strong>
                    <span v-if="isATM(strike)" class="atm-badge">ATM</span>
                  </td>

                  <!-- PUT 資料 -->
                  <td class="price-cell put-price">{{ getPutData(strike, 'last_price') }}</td>
                  <td>{{ getPutData(strike, 'ask_price') }}</td>
                  <td>{{ getPutData(strike, 'bid_price') }}</td>
                  <td>{{ getPutData(strike, 'open_interest') }}</td>
                  <td>{{ getPutData(strike, 'volume') }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="chain-legend">
            <span class="legend-item">
              <span class="legend-color call-color"></span> CALL (看漲)
            </span>
            <span class="legend-item">
              <span class="legend-color put-color"></span> PUT (看跌)
            </span>
            <span class="legend-item">
              <span class="legend-badge atm-badge">ATM</span> 價平合約
            </span>
          </div>
        </div>

        <!-- PCR 歷史圖表 -->
        <div v-if="selectedUnderlying" class="chart-section">
          <h3>PCR 歷史趨勢</h3>
          <div class="chart-controls">
            <button @click="chartPeriod = 30" :class="['btn-period', { active: chartPeriod === 30 }]">30 天</button>
            <button @click="chartPeriod = 60" :class="['btn-period', { active: chartPeriod === 60 }]">60 天</button>
            <button @click="chartPeriod = 90" :class="['btn-period', { active: chartPeriod === 90 }]">90 天</button>
          </div>
          <div ref="chartRef" class="chart-container"></div>
        </div>

        <!-- 載入狀態 -->
        <div v-if="loading" class="loading-overlay">
          <div class="spinner"></div>
          <p>載入中...</p>
        </div>

        <!-- 錯誤訊息 -->
        <div v-if="error" class="error-message">
          <div class="error-icon">⚠️</div>
          <div class="error-text">{{ error }}</div>
          <button @click="error = ''" class="btn-dismiss">關閉</button>
        </div>

        <!-- 空狀態 -->
        <div v-if="!selectedUnderlying" class="empty-state">
          <div class="empty-icon">📊</div>
          <h3>選擇標的物開始查詢</h3>
          <p>請在上方選擇 TX (台指) 或 MTX (小台) 查看 Option Chain</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth'
})

const router = useRouter()
const config = useRuntimeConfig()

// 狀態管理
const stageInfo = ref<any>(null)
const selectedUnderlying = ref<string>('')
const expiryDates = ref<string[]>([])
const selectedExpiry = ref<string>('')
const optionChain = ref<any>(null)
const factorSummary = ref<any>(null)
const loading = ref(false)
const loadingExpiries = ref(false)
const error = ref('')
const chartRef = ref<HTMLElement | null>(null)
const chartPeriod = ref(30)
let chartInstance: any = null

// 實時更新
const autoRefreshEnabled = ref(false)
const refreshInterval = ref(30) // 秒
let refreshIntervalId: NodeJS.Timeout | null = null

// 篩選
const filterMinStrike = ref<number | null>(null)
const filterMaxStrike = ref<number | null>(null)
const filterOptionType = ref<string>('all') // 'all', 'call', 'put'

// 排序
const sortField = ref<string>('')
const sortDirection = ref<'asc' | 'desc'>('asc')

// TypeScript 聲明
declare global {
  interface Window {
    echarts: any
  }
}

// 標的物清單
const underlyings = [
  { id: 'TX', name: '台指期貨' },
  { id: 'MTX', name: '小台期貨' }
]

// 載入階段資訊
const loadStageInfo = async () => {
  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    const response = await $fetch<any>(`${config.public.apiBase}/api/v1/options/stage`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    stageInfo.value = response
    console.log('Stage info loaded:', response)
  } catch (err: any) {
    console.error('Failed to load stage info:', err)
  }
}

// 選擇標的物
const selectUnderlying = async (underlyingId: string) => {
  selectedUnderlying.value = underlyingId
  selectedExpiry.value = ''
  optionChain.value = null

  await Promise.all([
    loadExpiryDates(),
    loadFactorSummary(),
    loadPCRChart()
  ])
}

// 載入到期日列表
const loadExpiryDates = async () => {
  if (!selectedUnderlying.value) return

  loadingExpiries.value = true
  error.value = ''

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    const response = await $fetch<string[]>(
      `${config.public.apiBase}/api/v1/options/contracts/${selectedUnderlying.value}/expiries`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        params: {
          is_active: 'active'
        }
      }
    )

    expiryDates.value = response
    console.log('Expiry dates loaded:', response.length)

    // 自動選擇最近的到期日
    if (response.length > 0) {
      selectedExpiry.value = response[0]
      await loadOptionChain()
    }
  } catch (err: any) {
    console.error('Failed to load expiry dates:', err)
    error.value = '載入到期日失敗：' + (err.data?.detail || err.message)
  } finally {
    loadingExpiries.value = false
  }
}

// 載入 Option Chain
const loadOptionChain = async () => {
  if (!selectedUnderlying.value || !selectedExpiry.value) return

  loading.value = true
  error.value = ''

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    const response = await $fetch<any>(
      `${config.public.apiBase}/api/v1/options/chain/${selectedUnderlying.value}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        params: {
          expiry_date: selectedExpiry.value
        }
      }
    )

    optionChain.value = response
    console.log('Option chain loaded:', response)
  } catch (err: any) {
    console.error('Failed to load option chain:', err)
    error.value = '載入 Option Chain 失敗：' + (err.data?.detail || err.message)
  } finally {
    loading.value = false
  }
}

// 載入因子摘要
const loadFactorSummary = async () => {
  if (!selectedUnderlying.value) return

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) return

    const response = await $fetch<any>(
      `${config.public.apiBase}/api/v1/options/factors/${selectedUnderlying.value}/summary`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    factorSummary.value = response
    console.log('Factor summary loaded:', response)
  } catch (err: any) {
    console.error('Failed to load factor summary:', err)
  }
}

// 載入 PCR 圖表
const loadPCRChart = async () => {
  if (!selectedUnderlying.value || !process.client) return

  try {
    const token = localStorage.getItem('access_token')
    if (!token) return

    const response = await $fetch<any[]>(
      `${config.public.apiBase}/api/v1/options/factors/${selectedUnderlying.value}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        params: {
          limit: chartPeriod.value
        }
      }
    )

    if (response && response.length > 0) {
      renderChart(response)
    }
  } catch (err: any) {
    console.error('Failed to load PCR chart data:', err)
  }
}

// 渲染圖表
const renderChart = (data: any[]) => {
  if (!process.client || !chartRef.value) return

  // 載入 ECharts
  if (!window.echarts) {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'
    script.onload = () => {
      renderChartImpl(data)
    }
    document.head.appendChild(script)
  } else {
    renderChartImpl(data)
  }
}

const renderChartImpl = (data: any[]) => {
  if (!chartRef.value || !window.echarts) return

  // 銷毀舊圖表
  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = window.echarts.init(chartRef.value)

  // 反轉數據（最新在右）
  const reversedData = [...data].reverse()

  const dates = reversedData.map((d: any) => d.date)
  const pcrValues = reversedData.map((d: any) => d.pcr_volume ? parseFloat(d.pcr_volume) : null)
  const atmIvValues = reversedData.map((d: any) => d.atm_iv ? parseFloat(d.atm_iv) : null)

  const option = {
    title: {
      text: `${selectedUnderlying.value} - PCR 與 ATM IV 趨勢`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['PCR Volume', 'ATM IV'],
      top: 30
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates
    },
    yAxis: [
      {
        type: 'value',
        name: 'PCR',
        position: 'left',
        axisLine: {
          lineStyle: {
            color: '#5470c6'
          }
        }
      },
      {
        type: 'value',
        name: 'ATM IV (%)',
        position: 'right',
        axisLine: {
          lineStyle: {
            color: '#91cc75'
          }
        }
      }
    ],
    series: [
      {
        name: 'PCR Volume',
        type: 'line',
        data: pcrValues,
        smooth: true,
        lineStyle: {
          width: 2
        },
        itemStyle: {
          color: '#5470c6'
        },
        markLine: {
          silent: true,
          lineStyle: {
            type: 'dashed'
          },
          data: [
            { yAxis: 1.2, label: { formatter: 'High (1.2)' }, lineStyle: { color: '#ee6666' } },
            { yAxis: 0.8, label: { formatter: 'Low (0.8)' }, lineStyle: { color: '#73c0de' } }
          ]
        }
      },
      {
        name: 'ATM IV',
        type: 'line',
        yAxisIndex: 1,
        data: atmIvValues,
        smooth: true,
        lineStyle: {
          width: 2
        },
        itemStyle: {
          color: '#91cc75'
        }
      }
    ]
  }

  chartInstance.setOption(option)
}

// 監聽圖表週期變化
watch(chartPeriod, () => {
  loadPCRChart()
})

// 輔助函數
const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

const formatNumber = (value: any) => {
  if (value === null || value === undefined) return '-'
  const num = parseFloat(value)
  return isNaN(num) ? '-' : num.toFixed(4)
}

const formatPercent = (value: any) => {
  if (value === null || value === undefined) return '-'
  const num = parseFloat(value)
  return isNaN(num) ? '-' : (num * 100).toFixed(1) + '%'
}

const getSentimentEmoji = (sentiment: string) => {
  const emojis: Record<string, string> = {
    'bullish': '🚀',
    'bearish': '📉',
    'neutral': '➡️'
  }
  return emojis[sentiment] || '❓'
}

const getSentimentText = (sentiment: string) => {
  const texts: Record<string, string> = {
    'bullish': '看漲',
    'bearish': '看跌',
    'neutral': '中性'
  }
  return texts[sentiment] || '未知'
}

const getPCRHint = (pcr: any) => {
  if (!pcr) return ''
  const value = parseFloat(pcr)
  if (value > 1.2) return '偏空（做多訊號）'
  if (value < 0.8) return '偏多（做空訊號）'
  return '平衡'
}

// Option Chain 輔助函數
const strikeList = computed(() => {
  if (!optionChain.value) return []

  const strikes = new Set<number>()
  optionChain.value.calls?.forEach((c: any) => strikes.add(parseFloat(c.strike_price)))
  optionChain.value.puts?.forEach((p: any) => strikes.add(parseFloat(p.strike_price)))

  return Array.from(strikes).sort((a, b) => a - b)
})

const filteredStrikeList = computed(() => {
  let filtered = [...strikeList.value]

  // 篩選履約價範圍
  if (filterMinStrike.value !== null) {
    filtered = filtered.filter(s => s >= filterMinStrike.value!)
  }
  if (filterMaxStrike.value !== null) {
    filtered = filtered.filter(s => s <= filterMaxStrike.value!)
  }

  // 篩選選擇權類型
  if (filterOptionType.value !== 'all') {
    // 保留所有履約價，但在顯示時會隱藏對應欄位
  }

  // 排序
  if (sortField.value) {
    filtered.sort((a, b) => {
      let aValue: any, bValue: any

      if (sortField.value === 'strike') {
        aValue = a
        bValue = b
      } else if (sortField.value.startsWith('call_')) {
        const field = sortField.value.replace('call_', '')
        const aCall = optionChain.value?.calls?.find((c: any) => parseFloat(c.strike_price) === a)
        const bCall = optionChain.value?.calls?.find((c: any) => parseFloat(c.strike_price) === b)
        aValue = aCall?.[field] ? parseFloat(aCall[field]) : 0
        bValue = bCall?.[field] ? parseFloat(bCall[field]) : 0
      } else if (sortField.value.startsWith('put_')) {
        const field = sortField.value.replace('put_', '')
        const aPut = optionChain.value?.puts?.find((p: any) => parseFloat(p.strike_price) === a)
        const bPut = optionChain.value?.puts?.find((p: any) => parseFloat(p.strike_price) === b)
        aValue = aPut?.[field] ? parseFloat(aPut[field]) : 0
        bValue = bPut?.[field] ? parseFloat(bPut[field]) : 0
      }

      if (sortDirection.value === 'asc') {
        return aValue - bValue
      } else {
        return bValue - aValue
      }
    })
  }

  return filtered
})

const getCallData = (strike: number, field: string) => {
  const call = optionChain.value?.calls?.find((c: any) => parseFloat(c.strike_price) === strike)
  if (!call || !call[field]) return '-'
  return formatNumber(call[field])
}

const getPutData = (strike: number, field: string) => {
  const put = optionChain.value?.puts?.find((p: any) => parseFloat(p.strike_price) === strike)
  if (!put || !put[field]) return '-'
  return formatNumber(put[field])
}

const isATM = (strike: number) => {
  if (!optionChain.value?.spot_price) return false
  const spotPrice = parseFloat(optionChain.value.spot_price)
  return Math.abs(strike - spotPrice) < 200 // Within 200 points
}

// 自動刷新功能
const startAutoRefresh = () => {
  if (refreshIntervalId) return

  refreshIntervalId = setInterval(() => {
    if (selectedUnderlying.value) {
      loadFactorSummary()
      loadPCRChart()
      if (selectedExpiry.value) {
        loadOptionChain()
      }
    }
  }, refreshInterval.value * 1000)

  console.log(`Auto-refresh started: every ${refreshInterval.value}s`)
}

const stopAutoRefresh = () => {
  if (refreshIntervalId) {
    clearInterval(refreshIntervalId)
    refreshIntervalId = null
    console.log('Auto-refresh stopped')
  }
}

const toggleAutoRefresh = () => {
  autoRefreshEnabled.value = !autoRefreshEnabled.value
  if (autoRefreshEnabled.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

// 篩選功能
const resetFilters = () => {
  filterMinStrike.value = null
  filterMaxStrike.value = null
  filterOptionType.value = 'all'
}

// 排序功能
const sortBy = (field: string) => {
  if (sortField.value === field) {
    // Toggle direction
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDirection.value = 'asc'
  }
}

// CSV 匯出功能
const exportToCSV = () => {
  if (!optionChain.value) return

  const rows: string[] = []

  // Header
  rows.push('Strike,Call Volume,Call OI,Call Bid,Call Ask,Call Last,Put Last,Put Ask,Put Bid,Put OI,Put Volume')

  // Data rows
  filteredStrikeList.value.forEach((strike: number) => {
    const callData = optionChain.value?.calls?.find((c: any) => parseFloat(c.strike_price) === strike)
    const putData = optionChain.value?.puts?.find((p: any) => parseFloat(p.strike_price) === strike)

    rows.push([
      strike,
      callData?.volume || '',
      callData?.open_interest || '',
      callData?.bid_price || '',
      callData?.ask_price || '',
      callData?.last_price || '',
      putData?.last_price || '',
      putData?.ask_price || '',
      putData?.bid_price || '',
      putData?.open_interest || '',
      putData?.volume || ''
    ].join(','))
  })

  const csvContent = rows.join('\n')
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)

  link.setAttribute('href', url)
  link.setAttribute('download', `option_chain_${selectedUnderlying.value}_${selectedExpiry.value}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// 生命週期
onMounted(() => {
  loadStageInfo()
})

onUnmounted(() => {
  stopAutoRefresh()
  if (chartInstance) {
    chartInstance.dispose()
  }
})
</script>

<style scoped>
.dashboard-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.dashboard-main {
  padding: 2rem 0;
}

.page-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: white;
  margin: 0 0 0.5rem 0;
}

.page-subtitle {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

.stage-badge {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
}

.badge {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
}

.feature-list {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.875rem;
}

.control-panel {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.control-group {
  margin-bottom: 1.5rem;
}

.control-group:last-child {
  margin-bottom: 0;
}

.control-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #333;
}

.btn-group {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.btn-underlying {
  padding: 0.75rem 1.5rem;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  font-weight: 500;
}

.btn-underlying:hover {
  border-color: #667eea;
  background: #f7fafc;
}

.btn-underlying.active {
  border-color: #667eea;
  background: #667eea;
  color: white;
}

.expiry-select {
  flex: 1;
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 1rem;
  margin-right: 0.5rem;
}

.btn-refresh {
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.3s;
}

.btn-refresh:hover:not(:disabled) {
  background: #5568d3;
}

.btn-refresh:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
}

.btn-auto-refresh {
  padding: 0.75rem 1.5rem;
  background: #48bb78;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.3s;
}

.btn-auto-refresh:hover:not(:disabled) {
  background: #38a169;
}

.btn-auto-refresh.active {
  background: #f56565;
}

.btn-auto-refresh.active:hover {
  background: #e53e3e;
}

.btn-auto-refresh:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
}

.filter-group {
  border-top: 1px solid #e2e8f0;
  padding-top: 1.5rem;
}

.filter-inputs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-input {
  width: 120px;
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 1rem;
}

.filter-separator {
  color: #718096;
  font-weight: 500;
}

.btn-reset-filter {
  padding: 0.75rem 1rem;
  background: #edf2f7;
  color: #2d3748;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.3s;
}

.btn-reset-filter:hover:not(:disabled) {
  background: #e2e8f0;
}

.btn-reset-filter:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-export {
  padding: 0.75rem 1.5rem;
  background: #48bb78;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.3s;
}

.btn-export:hover {
  background: #38a169;
}

.sortable {
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.sortable:hover {
  background: rgba(0, 0, 0, 0.05);
}

.sort-indicator {
  margin-left: 0.25rem;
  font-size: 0.75rem;
  color: #667eea;
}

.sentiment-dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.sentiment-card, .factor-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.sentiment-card {
  grid-column: 1 / 2;
}

.sentiment-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.sentiment-label {
  font-size: 0.875rem;
  color: #718096;
  margin-bottom: 0.5rem;
}

.sentiment-value {
  font-size: 1.5rem;
  font-weight: 700;
}

.sentiment-bullish {
  color: #48bb78;
}

.sentiment-bearish {
  color: #f56565;
}

.sentiment-neutral {
  color: #718096;
}

.factor-label {
  font-size: 0.875rem;
  color: #718096;
  margin-bottom: 0.5rem;
}

.factor-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #2d3748;
  margin-bottom: 0.25rem;
}

.factor-value.small {
  font-size: 1.25rem;
}

.factor-hint {
  font-size: 0.75rem;
  color: #a0aec0;
}

.option-chain-container {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.chain-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.chain-header h3 {
  margin: 0;
  color: #2d3748;
}

.spot-price {
  font-size: 1.125rem;
  color: #4a5568;
}

.price-value {
  font-weight: 700;
  color: #2d3748;
  margin-left: 0.5rem;
}

.chain-table-wrapper {
  overflow-x: auto;
}

.chain-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.chain-table th {
  padding: 0.75rem 0.5rem;
  text-align: center;
  font-weight: 600;
  border-bottom: 2px solid #e2e8f0;
}

.section-header {
  background: #f7fafc;
  font-size: 1rem;
}

.call-header {
  background: #bee3f8;
  color: #2c5282;
}

.put-header {
  background: #fed7d7;
  color: #742a2a;
}

.strike-header {
  background: #edf2f7;
}

.chain-table td {
  padding: 0.5rem;
  text-align: center;
  border-bottom: 1px solid #e2e8f0;
}

.strike-cell {
  background: #edf2f7;
  font-weight: 600;
  font-size: 1rem;
}

.price-cell {
  font-weight: 600;
  font-size: 1rem;
}

.call-price {
  background: #ebf8ff;
  color: #2c5282;
}

.put-price {
  background: #fff5f5;
  color: #742a2a;
}

.atm-row {
  background: #fffaf0;
}

.atm-badge {
  display: inline-block;
  background: #fbd38d;
  color: #744210;
  padding: 0.125rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-left: 0.5rem;
}

.chain-legend {
  display: flex;
  justify-content: center;
  gap: 2rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #4a5568;
}

.legend-color {
  width: 20px;
  height: 20px;
  border-radius: 4px;
}

.call-color {
  background: #bee3f8;
}

.put-color {
  background: #fed7d7;
}

.chart-section {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.chart-section h3 {
  margin: 0 0 1rem 0;
  color: #2d3748;
}

.chart-controls {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.btn-period {
  padding: 0.5rem 1rem;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-period:hover {
  border-color: #667eea;
}

.btn-period.active {
  border-color: #667eea;
  background: #667eea;
  color: white;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-overlay p {
  color: white;
  margin-top: 1rem;
  font-size: 1.125rem;
}

.error-message {
  background: #fff5f5;
  border: 2px solid #fc8181;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.error-icon {
  font-size: 2rem;
}

.error-text {
  flex: 1;
  color: #742a2a;
}

.btn-dismiss {
  padding: 0.5rem 1rem;
  background: #fc8181;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.empty-state {
  background: white;
  border-radius: 12px;
  padding: 4rem 2rem;
  text-align: center;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-state h3 {
  margin: 0 0 0.5rem 0;
  color: #2d3748;
}

.empty-state p {
  margin: 0;
  color: #718096;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 1rem;
  }

  .sentiment-dashboard {
    grid-template-columns: 1fr;
  }

  .chain-table {
    font-size: 0.75rem;
  }

  .chain-table th,
  .chain-table td {
    padding: 0.25rem;
  }
}
</style>
