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
            <h1 class="page-title">法人買賣超分析</h1>
            <p class="page-subtitle">查詢外資、投信、自營商三大法人買賣超數據</p>
          </div>
        </div>

        <!-- 搜尋區 -->
        <div class="search-section">
          <div class="search-box">
            <input
              v-model="searchKeyword"
              @keyup.enter="handleSearch"
              type="text"
              placeholder="搜尋股票代碼或名稱（例如：2330、台積電）"
              class="search-input"
            >
            <button @click="handleSearch" class="btn-search" :disabled="searching">
              {{ searching ? '搜尋中...' : '🔍 搜尋' }}
            </button>
          </div>

          <div class="quick-stocks">
            <span class="label">熱門股票：</span>
            <button
              v-for="stock in popularStocks"
              :key="stock.id"
              @click="selectStock(stock.id, stock.name)"
              class="btn-quick-stock"
            >
              {{ stock.id }} {{ stock.name }}
            </button>
          </div>
        </div>

        <!-- 搜尋結果 -->
        <div v-if="searchResults.length > 0" class="search-results">
          <h3>搜尋結果（{{ searchResults.length }} 筆）</h3>
          <div class="results-grid">
            <div
              v-for="stock in searchResults"
              :key="stock.stock_id"
              @click="selectStock(stock.stock_id, stock.name)"
              class="result-card"
            >
              <div class="stock-id">{{ stock.stock_id }}</div>
              <div class="stock-name">{{ stock.name }}</div>
            </div>
          </div>
        </div>

        <!-- 股票詳情 -->
        <div v-if="selectedStock" class="stock-detail">
          <div class="detail-header">
            <div>
              <h2>{{ selectedStock.id }} - {{ selectedStock.name }}</h2>
              <p v-if="latestDate" class="latest-info">
                最新數據日期：<span class="date-value">{{ latestDate }}</span>
              </p>
            </div>
            <button @click="clearSelection" class="btn-clear">
              ✕ 清除
            </button>
          </div>

          <!-- 日期選擇 -->
          <div class="date-selector">
            <div class="date-inputs">
              <div class="input-group">
                <label>開始日期：</label>
                <input v-model="startDate" type="date" class="date-input">
              </div>
              <div class="input-group">
                <label>結束日期：</label>
                <input v-model="endDate" type="date" class="date-input">
              </div>
            </div>
            <div class="date-quick-buttons">
              <button @click="setDateRange(7)" class="btn-date-range">近 7 天</button>
              <button @click="setDateRange(30)" class="btn-date-range">近 30 天</button>
              <button @click="setDateRange(90)" class="btn-date-range">近 3 個月</button>
              <button @click="setDateRange(180)" class="btn-date-range">近 6 個月</button>
              <button @click="setDateRange(365)" class="btn-date-range">近 1 年</button>
            </div>
          </div>

          <!-- 法人類型選擇 -->
          <div class="investor-type-tabs">
            <button
              @click="investorType = 'Foreign_Investor'"
              :class="['tab-btn', { active: investorType === 'Foreign_Investor' }]"
            >
              外資
            </button>
            <button
              @click="investorType = 'Investment_Trust'"
              :class="['tab-btn', { active: investorType === 'Investment_Trust' }]"
            >
              投信
            </button>
            <button
              @click="investorType = 'Dealer_self'"
              :class="['tab-btn', { active: investorType === 'Dealer_self' }]"
            >
              自營商
            </button>
            <button
              @click="investorType = null"
              :class="['tab-btn', { active: investorType === null }]"
            >
              全部
            </button>
          </div>

          <!-- 載入按鈕 -->
          <div class="load-section">
            <button @click="loadInstitutionalData" class="btn-load" :disabled="loadingData">
              {{ loadingData ? '載入中...' : '📊 載入法人買賣超數據' }}
            </button>
          </div>

          <!-- 錯誤訊息 -->
          <div v-if="dataError" class="error-message">
            {{ dataError }}
          </div>

          <!-- 數據顯示 -->
          <div v-if="institutionalData && institutionalData.length > 0" class="data-display">
            <!-- 圖表區 -->
            <div class="chart-section">
              <div class="chart-header">
                <h3>📈 法人買賣超趨勢圖</h3>
              </div>
              <div class="chart-container">
                <div ref="chartRef" class="chart-canvas"></div>
              </div>
            </div>

            <!-- 統計摘要 -->
            <div class="statistics">
              <h3>統計資訊</h3>
              <div class="stats-grid">
                <div class="stat-item">
                  <span class="stat-label">資料筆數：</span>
                  <span class="stat-value">{{ institutionalData.length }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">總買進：</span>
                  <span class="stat-value">{{ formatVolume(getTotalBuy()) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">總賣出：</span>
                  <span class="stat-value">{{ formatVolume(getTotalSell()) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">淨買賣超：</span>
                  <span :class="['stat-value', getNetClass()]">{{ formatVolume(getTotalNet()) }}</span>
                </div>
              </div>
            </div>

            <!-- 數據表格 -->
            <div class="table-section">
              <h3>法人買賣超明細（{{ institutionalData.length }} 筆）</h3>
              <div class="table-wrapper">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>日期</th>
                      <th>法人類型</th>
                      <th>買進股數</th>
                      <th>賣出股數</th>
                      <th>買賣超</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="record in institutionalData" :key="`${record.date}-${record.investor_type}`">
                      <td>{{ formatDate(record.date) }}</td>
                      <td>{{ getInvestorTypeName(record.investor_type) }}</td>
                      <td class="volume-cell positive">{{ formatVolume(record.buy_volume) }}</td>
                      <td class="volume-cell negative">{{ formatVolume(record.sell_volume) }}</td>
                      <td :class="['volume-cell', getNetClass(record.net_buy_sell)]">
                        {{ formatVolume(record.net_buy_sell) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- 空狀態 -->
        <div v-if="!selectedStock && searchResults.length === 0" class="empty-state">
          <div class="empty-icon">💼</div>
          <h3>開始查詢法人買賣超數據</h3>
          <p>在上方搜尋框輸入股票代碼或名稱，或點選熱門股票開始查詢</p>
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
const { loadUserInfo } = useUserInfo()
const config = useRuntimeConfig()

// 搜尋狀態
const searchKeyword = ref('')
const searching = ref(false)
const searchResults = ref<any[]>([])

// 選中的股票
const selectedStock = ref<{ id: string; name: string } | null>(null)
const latestDate = ref<string | null>(null)

// 日期範圍
const startDate = ref('')
const endDate = ref('')

// 法人類型
const investorType = ref<string | null>('Foreign_Investor')

// 載入狀態
const loadingData = ref(false)
const institutionalData = ref<any[]>([])
const dataError = ref('')

// 圖表狀態
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: any = null

// TypeScript 聲明
declare global {
  interface Window {
    echarts: any
  }
}

// 熱門股票
const popularStocks = [
  { id: '2330', name: '台積電' },
  { id: '2317', name: '鴻海' },
  { id: '2454', name: '聯發科' },
  { id: '2412', name: '中華電' },
  { id: '2882', name: '國泰金' },
  { id: '2881', name: '富邦金' },
]

// 搜尋股票
const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    alert('請輸入搜尋關鍵字')
    return
  }

  searching.value = true
  dataError.value = ''

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    const response = await $fetch<any>(`${config.public.apiBase}/api/v1/data/stocks/search`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: {
        keyword: searchKeyword.value
      }
    })

    searchResults.value = response.results || []
    console.log('Search results:', searchResults.value.length)

    if (searchResults.value.length === 0) {
      alert('找不到符合的股票')
    }
  } catch (error: any) {
    console.error('Search failed:', error)
    dataError.value = error.data?.detail || '搜尋失敗'
  } finally {
    searching.value = false
  }
}

// 選擇股票
const selectStock = async (stockId: string, stockName: string) => {
  selectedStock.value = { id: stockId, name: stockName }
  searchResults.value = []
  searchKeyword.value = ''
  institutionalData.value = []
  dataError.value = ''

  // 設定預設日期範圍（30天）
  setDateRange(30)

  // 載入最新數據日期
  await loadLatestDate(stockId)
}

// 清除選擇
const clearSelection = () => {
  selectedStock.value = null
  latestDate.value = null
  institutionalData.value = []
  dataError.value = ''
}

// 設定日期範圍
const setDateRange = (days: number) => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - days)

  endDate.value = end.toISOString().split('T')[0]
  startDate.value = start.toISOString().split('T')[0]
}

// 載入最新數據日期
const loadLatestDate = async (stockId: string) => {
  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) return

    const response = await $fetch<any>(
      `${config.public.apiBase}/api/v1/institutional/status/latest-date`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        params: {
          stock_id: stockId
        }
      }
    )

    latestDate.value = response.latest_date
  } catch (error: any) {
    console.error('Failed to load latest date:', error)
    latestDate.value = null
  }
}

// 初始化 ECharts
const initChart = async () => {
  if (!process.client) return

  try {
    if (!window.echarts) {
      console.log('Loading ECharts from CDN...')
      const script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'
      document.head.appendChild(script)

      await new Promise((resolve, reject) => {
        script.onload = () => {
          console.log('ECharts loaded successfully')
          resolve(true)
        }
        script.onerror = () => {
          console.error('Failed to load ECharts')
          reject(new Error('Failed to load ECharts'))
        }
        setTimeout(() => reject(new Error('ECharts load timeout')), 10000)
      })
    }

    if (chartRef.value && window.echarts) {
      if (chartInstance) {
        chartInstance.dispose()
      }
      chartInstance = window.echarts.init(chartRef.value)
    }
  } catch (error) {
    console.error('Error initializing chart:', error)
    dataError.value = '圖表初始化失敗，請重新載入頁面'
  }
}

// 渲染法人買賣超趨勢圖
const renderInstitutionalChart = () => {
  if (!chartInstance || !institutionalData.value || institutionalData.value.length === 0) {
    console.error('Cannot render chart')
    return
  }

  try {
    // 按日期分組數據
    const dataByDate: Record<string, Record<string, number>> = {}
    institutionalData.value.forEach(record => {
      if (!dataByDate[record.date]) {
        dataByDate[record.date] = {}
      }
      dataByDate[record.date][record.investor_type] = record.net_buy_sell
    })

    const dates = Object.keys(dataByDate).sort()

    // 準備各法人的數據系列
    const foreignData = dates.map(date => dataByDate[date]['Foreign_Investor'] || 0)
    const trustData = dates.map(date => dataByDate[date]['Investment_Trust'] || 0)
    const dealerData = dates.map(date => dataByDate[date]['Dealer_self'] || 0)

    const series: any[] = []

    if (investorType.value === null || investorType.value === 'Foreign_Investor') {
      series.push({
        name: '外資',
        type: 'line',
        data: foreignData,
        smooth: true,
        lineStyle: { width: 2, color: '#ef4444' },
        itemStyle: { color: '#ef4444' },
      })
    }

    if (investorType.value === null || investorType.value === 'Investment_Trust') {
      series.push({
        name: '投信',
        type: 'line',
        data: trustData,
        smooth: true,
        lineStyle: { width: 2, color: '#3b82f6' },
        itemStyle: { color: '#3b82f6' },
      })
    }

    if (investorType.value === null || investorType.value === 'Dealer_self') {
      series.push({
        name: '自營商',
        type: 'line',
        data: dealerData,
        smooth: true,
        lineStyle: { width: 2, color: '#22c55e' },
        itemStyle: { color: '#22c55e' },
      })
    }

    const option = {
      title: {
        text: `${selectedStock.value?.name || ''} 法人買賣超趨勢`,
        left: 'center',
        textStyle: {
          fontSize: 18,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: (params: any) => {
          const date = params[0].axisValue
          let tooltip = `${date}<br/>`
          params.forEach((param: any) => {
            const value = param.data
            tooltip += `${param.seriesName}: ${value >= 0 ? '+' : ''}${formatVolume(value)}<br/>`
          })
          return tooltip
        }
      },
      legend: {
        data: series.map(s => s.name),
        top: 35
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: 80,
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: {
          rotate: 45,
          formatter: (value: string) => {
            const date = new Date(value)
            return `${date.getMonth() + 1}/${date.getDate()}`
          }
        }
      },
      yAxis: {
        type: 'value',
        name: '買賣超（股）',
        axisLabel: {
          formatter: (value: number) => {
            if (Math.abs(value) >= 1000000) {
              return (value / 1000000).toFixed(1) + 'M'
            } else if (Math.abs(value) >= 1000) {
              return (value / 1000).toFixed(1) + 'K'
            }
            return value.toString()
          }
        },
        scale: true
      },
      series: series
    }

    chartInstance.setOption(option)
    console.log('Institutional chart rendered')
  } catch (error) {
    console.error('Error in renderInstitutionalChart:', error)
    throw error
  }
}

// 載入法人買賣超數據
const loadInstitutionalData = async () => {
  if (!selectedStock.value) return

  if (!startDate.value || !endDate.value) {
    alert('請選擇日期範圍')
    return
  }

  loadingData.value = true
  dataError.value = ''
  institutionalData.value = []

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    const params: any = {
      start_date: startDate.value,
      end_date: endDate.value
    }

    if (investorType.value) {
      params.investor_type = investorType.value
    }

    const response = await $fetch<any>(
      `${config.public.apiBase}/api/v1/institutional/stocks/${selectedStock.value.id}/data`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        params: params
      }
    )

    institutionalData.value = response
    console.log('Loaded institutional data:', institutionalData.value.length, 'records')

    // 渲染圖表
    await nextTick()
    await initChart()
    renderInstitutionalChart()
  } catch (error: any) {
    console.error('Failed to load institutional data:', error)
    dataError.value = error.data?.detail || '載入資料失敗'
  } finally {
    loadingData.value = false
  }
}

// 監聽法人類型變化，重新渲染圖表
watch(investorType, () => {
  if (institutionalData.value.length > 0) {
    renderInstitutionalChart()
  }
})

// 監聽窗口大小變化
onMounted(() => {
  loadUserInfo()
  if (process.client) {
    window.addEventListener('resize', () => {
      chartInstance?.resize()
    })
  }
})

// 清理圖表實例
onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
})

// 格式化日期
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

// 格式化成交量
const formatVolume = (volume: any) => {
  if (volume === null || volume === undefined) return '-'
  const numVolume = typeof volume === 'string' ? parseFloat(volume) : volume
  if (isNaN(numVolume)) return '-'

  const sign = numVolume >= 0 ? '+' : ''

  if (Math.abs(numVolume) >= 1000000) {
    return sign + (numVolume / 1000000).toFixed(2) + 'M'
  } else if (Math.abs(numVolume) >= 1000) {
    return sign + (numVolume / 1000).toFixed(2) + 'K'
  }
  return sign + numVolume.toString()
}

// 獲取法人類型名稱
const getInvestorTypeName = (type: string) => {
  const names: Record<string, string> = {
    'Foreign_Investor': '外資',
    'Investment_Trust': '投信',
    'Dealer_self': '自營商',
    'Dealer_Hedging': '自營商(避險)',
    'Foreign_Dealer_Self': '外資自營'
  }
  return names[type] || type
}

// 獲取淨買賣超樣式類別
const getNetClass = (net?: number) => {
  const value = net !== undefined ? net : getTotalNet()
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return 'neutral'
}

// 計算統計
const getTotalBuy = () => {
  return institutionalData.value.reduce((sum, record) => sum + record.buy_volume, 0)
}

const getTotalSell = () => {
  return institutionalData.value.reduce((sum, record) => sum + record.sell_volume, 0)
}

const getTotalNet = () => {
  return institutionalData.value.reduce((sum, record) => sum + record.net_buy_sell, 0)
}
</script>

<style scoped lang="scss">
// 複用通用樣式
.dashboard-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.dashboard-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.page-container {
  width: 100%;
}

.page-header {
  margin-bottom: 2rem;

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    color: #111827;
    margin: 0 0 0.5rem 0;
  }

  .page-subtitle {
    color: #6b7280;
    margin: 0;
  }
}

// 搜尋區
.search-section {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.search-box {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;

  .search-input {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.5rem;
    font-size: 1rem;

    &:focus {
      outline: none;
      border-color: #3b82f6;
    }
  }
}

.btn-search {
  padding: 0.75rem 2rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;

  &:hover:not(:disabled) {
    background: #2563eb;
  }

  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }
}

.quick-stocks {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;

  .label {
    color: #6b7280;
    font-weight: 500;
  }
}

.btn-quick-stock {
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;

  &:hover {
    background: #dbeafe;
    border-color: #3b82f6;
    color: #1e40af;
  }
}

// 搜尋結果
.search-results {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

  h3 {
    margin: 0 0 1rem 0;
    color: #111827;
  }
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.result-card {
  padding: 1rem;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #3b82f6;
    background: #f9fafb;
  }

  .stock-id {
    font-size: 1.125rem;
    font-weight: 600;
    color: #1e40af;
    margin-bottom: 0.25rem;
  }

  .stock-name {
    color: #111827;
  }
}

// 股票詳情
.stock-detail {
  background: white;
  padding: 2rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e5e7eb;

  h2 {
    font-size: 1.75rem;
    font-weight: 600;
    color: #111827;
    margin: 0 0 0.5rem 0;
  }

  .latest-info {
    font-size: 1rem;
    color: #6b7280;
    margin: 0;

    .date-value {
      font-weight: 600;
      color: #059669;
    }
  }
}

.btn-clear {
  padding: 0.5rem 1rem;
  background: #fee2e2;
  color: #991b1b;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #fecaca;
  }
}

.date-selector {
  margin-bottom: 1.5rem;
}

.date-inputs {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;

  .input-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;

    label {
      font-weight: 500;
      color: #374151;
    }
  }
}

.date-input {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;

  &:focus {
    outline: none;
    border-color: #3b82f6;
  }
}

.date-quick-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.btn-date-range {
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;

  &:hover {
    background: #e5e7eb;
    border-color: #9ca3af;
  }
}

.investor-type-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.tab-btn {
  padding: 0.75rem 1.5rem;
  background: #f3f4f6;
  border: 2px solid transparent;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;

  &:hover {
    background: #e5e7eb;
  }

  &.active {
    background: #dbeafe;
    color: #1e40af;
    border-color: #3b82f6;
  }
}

.load-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.btn-load {
  padding: 0.75rem 2rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;

  &:hover:not(:disabled) {
    background: #2563eb;
  }

  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }
}

.error-message {
  padding: 1rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  margin-bottom: 1rem;
}

// 資料顯示
.data-display {
  margin-top: 2rem;
}

// 圖表區
.chart-section {
  margin-bottom: 2rem;
  background: white;
  padding: 2rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-header {
  margin-bottom: 1.5rem;

  h3 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #111827;
  }
}

.chart-container {
  width: 100%;
  margin-top: 1rem;
}

.chart-canvas {
  width: 100%;
  height: 500px;
}

// 統計
.statistics {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 0.5rem;

  h3 {
    margin: 0 0 1rem 0;
    color: #111827;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-item {
  display: flex;
  gap: 0.5rem;

  .stat-label {
    color: #6b7280;
  }

  .stat-value {
    font-weight: 600;
    color: #111827;

    &.positive {
      color: #059669;
    }

    &.negative {
      color: #dc2626;
    }

    &.neutral {
      color: #6b7280;
    }
  }
}

// 表格
.table-section {
  margin-bottom: 2rem;

  h3 {
    margin: 0 0 1rem 0;
    color: #111827;
  }
}

.table-wrapper {
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
}

.data-table {
  width: 100%;
  border-collapse: collapse;

  thead {
    background: #f9fafb;

    th {
      padding: 0.75rem 1rem;
      text-align: left;
      font-weight: 600;
      color: #374151;
      border-bottom: 2px solid #e5e7eb;
    }
  }

  tbody {
    tr {
      &:hover {
        background: #f9fafb;
      }

      &:not(:last-child) td {
        border-bottom: 1px solid #e5e7eb;
      }
    }

    td {
      padding: 0.75rem 1rem;
      color: #111827;

      &.volume-cell {
        font-family: 'Monaco', 'Courier New', monospace;
        font-weight: 500;

        &.positive {
          color: #059669;
        }

        &.negative {
          color: #dc2626;
        }
      }
    }
  }
}

// 空狀態
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  h3 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #111827;
    margin: 0 0 0.5rem 0;
  }

  p {
    color: #6b7280;
    margin: 0;
  }
}

// 響應式
@media (max-width: 768px) {
  .search-box {
    flex-direction: column;
  }

  .date-inputs {
    flex-direction: column;
  }

  .detail-header {
    flex-direction: column;
    gap: 1rem;
  }

  .results-grid {
    grid-template-columns: 1fr;
  }
}
</style>
