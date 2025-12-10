<template>
  <div class="dashboard-container">
    <!-- 頂部導航欄 -->
    <AppHeader />

    <!-- 主要內容區 -->
    <main class="dashboard-main">
      <div class="page-container">
        <!-- 返回按鈕 -->
        <div class="back-button-container">
          <NuxtLink to="/backtest" class="btn-back">
            ← 返回回測列表
          </NuxtLink>
        </div>

        <!-- 載入中 -->
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>載入回測結果中...</p>
        </div>

        <!-- 錯誤訊息 -->
        <div v-else-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <!-- 回測詳情 -->
        <div v-else-if="backtest" class="backtest-detail">
          <!-- 基本信息 -->
          <div class="info-card">
            <h2 class="card-title">回測信息</h2>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">名稱：</span>
                <span class="info-value">{{ backtest.name }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">股票代碼：</span>
                <span class="info-value">{{ backtest.symbol }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">回測期間：</span>
                <span class="info-value">{{ formatDate(backtest.start_date) }} ~ {{ formatDate(backtest.end_date) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">初始資金：</span>
                <span class="info-value">{{ formatCurrency(backtest.initial_capital) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">策略：</span>
                <span class="info-value">{{ backtest.strategy?.name || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">狀態：</span>
                <span :class="['status-badge', `status-${backtest.status}`]">
                  {{ getStatusText(backtest.status) }}
                </span>
              </div>
              <div class="info-item">
                <span class="info-label">回測引擎：</span>
                <span class="engine-badge" :class="backtest.engine_type || 'backtrader'">
                  {{ (backtest.engine_type || 'backtrader') === 'qlib' ? '🤖 Qlib (機器學習)' : '📊 Backtrader (技術指標)' }}
                </span>
              </div>
            </div>
          </div>

          <!-- 績效指標 -->
          <div v-if="backtest.result">
            <PerformanceMetrics :result="backtest.result" />
          </div>

          <!-- 詳細視覺化圖表 -->
          <div v-if="backtest.result?.detailed_results" class="charts-container">
            <h2 class="section-title">📊 詳細分析圖表</h2>

            <!-- 標籤頁導航 -->
            <div class="tabs-nav">
              <button
                v-for="tab in chartTabs"
                :key="tab.id"
                @click="activeTab = tab.id"
                :class="['tab-button', { active: activeTab === tab.id }]"
              >
                {{ tab.icon }} {{ tab.label }}
              </button>
            </div>

            <!-- 標籤頁內容 -->
            <div class="tab-content">
              <!-- 淨值曲線 -->
              <div v-show="activeTab === 'nav'" class="chart-panel">
                <div ref="navChartRef" class="chart-canvas"></div>
              </div>

              <!-- 月度報酬熱圖 -->
              <div v-show="activeTab === 'monthly'" class="chart-panel">
                <div ref="monthlyChartRef" class="chart-canvas"></div>
              </div>

              <!-- 交易分佈 -->
              <div v-show="activeTab === 'distribution'" class="chart-panel">
                <div ref="distributionChartRef" class="chart-canvas"></div>
              </div>

              <!-- 滾動指標 -->
              <div v-show="activeTab === 'rolling'" class="chart-panel">
                <div ref="rollingChartRef" class="chart-canvas"></div>
              </div>
            </div>
          </div>

          <!-- 交易記錄 -->
          <div v-if="backtest.trades && backtest.trades.length > 0" class="trades-card">
            <h2 class="card-title">交易記錄（{{ backtest.trades.length }} 筆）</h2>

            <!-- 交易圖表 -->
            <div class="trade-chart-section">
              <div class="chart-header">
                <h3>📊 交易視覺化</h3>
                <button @click="loadChartData" class="btn-refresh" :disabled="chartLoading">
                  {{ chartLoading ? '載入中...' : '🔄 重新載入圖表' }}
                </button>
              </div>

              <div v-if="chartError" class="chart-error">
                {{ chartError }}
              </div>

              <div v-else-if="chartLoading" class="chart-loading">
                <div class="spinner"></div>
                <p>載入圖表資料中...</p>
              </div>

              <div v-else-if="!priceData" class="chart-placeholder">
                <div class="placeholder-icon">📊</div>
                <p>點擊上方「🔄 重新載入圖表」按鈕來顯示交易視覺化</p>
              </div>

              <!-- 圖表畫布 -->
              <div v-show="priceData && !chartError && !chartLoading" ref="tradeChartRef" class="trade-chart-canvas"></div>
            </div>

            <div class="trades-table-container">
              <table class="trades-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>類型</th>
                    <th>價格</th>
                    <th>數量</th>
                    <th>價值</th>
                    <th>損益</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(trade, index) in backtest.trades" :key="index">
                    <td>{{ formatDate(trade.date) }}</td>
                    <td>
                      <span :class="['trade-type', trade.action === 'BUY' ? 'buy' : 'sell']">
                        {{ trade.action === 'BUY' ? '買入' : '賣出' }}
                      </span>
                    </td>
                    <td>{{ trade.price?.toFixed(2) || '-' }}</td>
                    <td>{{ trade.quantity }}</td>
                    <td>{{ formatCurrency(trade.total_amount) }}</td>
                    <td v-if="trade.profit_loss !== null && trade.profit_loss !== undefined">
                      <span :class="['pnl', trade.profit_loss >= 0 ? 'positive' : 'negative']">
                        {{ trade.profit_loss >= 0 ? '+' : '' }}{{ formatCurrency(trade.profit_loss) }}
                      </span>
                    </td>
                    <td v-else>-</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth'
})

const route = useRoute()
const router = useRouter()
const { loadUserInfo } = useUserInfo()
const config = useRuntimeConfig()

// 狀態
const backtest = ref<any>(null)
const loading = ref(false)
const errorMessage = ref('')

// 從路由獲取 ID
const backtestId = computed(() => parseInt(route.params.id as string))

// 載入回測詳情
const loadBacktestDetail = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    // 獲取回測詳情
    const response = await $fetch<any>(
      `${config.public.apiBase}/api/v1/backtest/${backtestId.value}`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    backtest.value = response
    console.log('Backtest detail loaded:', backtest.value)

    // 如果有結果，獲取結果詳情
    if (response.status === 'COMPLETED') {
      const resultResponse = await $fetch<any>(
        `${config.public.apiBase}/api/v1/backtest/${backtestId.value}/result`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )

      backtest.value.result = resultResponse.result
      backtest.value.trades = resultResponse.trades || []
      console.log('Backtest result loaded:', backtest.value.result)
    }

  } catch (error: any) {
    console.error('Failed to load backtest detail:', error)
    errorMessage.value = error.data?.detail || '載入回測詳情失敗'

    if (error.status === 401) {
      router.push('/login')
    }
  } finally {
    loading.value = false
  }
}

// 格式化日期
const formatDate = (dateString: string) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

// 格式化金額
const formatCurrency = (amount: number) => {
  if (!amount && amount !== 0) return '-'
  return new Intl.NumberFormat('zh-TW', {
    style: 'currency',
    currency: 'TWD',
    minimumFractionDigits: 0
  }).format(amount)
}

// 狀態文字
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '待執行',
    running: '執行中',
    completed: '已完成',
    failed: '失敗'
  }
  return statusMap[status?.toLowerCase()] || status
}

// ===== 交易圖表相關 =====
declare global {
  interface Window {
    echarts: any
  }
}

const tradeChartRef = ref<HTMLElement | null>(null)
let chartInstance: any = null
const chartLoading = ref(false)
const chartError = ref('')
const priceData = ref<any>(null)

// ===== 視覺化圖表相關 =====
const activeTab = ref('nav')

const chartTabs = [
  { id: 'nav', label: '淨值曲線', icon: '📈' },
  { id: 'monthly', label: '月度報酬', icon: '📅' },
  { id: 'distribution', label: '交易分佈', icon: '📊' },
  { id: 'rolling', label: '滾動指標', icon: '🔄' }
]

// 圖表 refs
const navChartRef = ref<HTMLElement | null>(null)
const monthlyChartRef = ref<HTMLElement | null>(null)
const distributionChartRef = ref<HTMLElement | null>(null)
const rollingChartRef = ref<HTMLElement | null>(null)

// 圖表實例
let navChart: any = null
let monthlyChart: any = null
let distributionChart: any = null
let rollingChart: any = null

const detailedResults = computed(() => backtest.value?.result?.detailed_results)

// 初始化 ECharts
const initChart = async () => {
  if (!process.client) {
    console.log('Not in client mode, skipping chart init')
    return
  }

  try {
    console.log('Initializing chart...')

    // 載入 ECharts（如果尚未載入）
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
        setTimeout(() => reject(new Error('ECharts 載入超時')), 10000)
      })
    } else {
      console.log('ECharts already loaded')
    }

    // 初始化圖表實例
    if (!tradeChartRef.value) {
      console.error('Chart ref not available')
      chartError.value = '圖表元素未就緒'
      return
    }

    if (!window.echarts) {
      console.error('ECharts not available')
      chartError.value = 'ECharts 載入失敗'
      return
    }

    if (chartInstance) {
      console.log('Disposing old chart instance')
      chartInstance.dispose()
    }

    console.log('Creating new chart instance...')
    console.log('Container dimensions:', {
      width: tradeChartRef.value.offsetWidth,
      height: tradeChartRef.value.offsetHeight
    })
    chartInstance = window.echarts.init(tradeChartRef.value)
    console.log('Chart instance created successfully')

    // 強制調整圖表大小以適應容器
    setTimeout(() => {
      if (chartInstance) {
        chartInstance.resize()
        console.log('Chart resized after initialization')
      }
    }, 100)
  } catch (error: any) {
    console.error('初始化圖表失敗:', error)
    chartError.value = error.message || '圖表初始化失敗'
    throw error
  }
}

// 載入價格資料（用戶點擊按鈕時觸發）
const loadChartData = async () => {
  if (!backtest.value) {
    console.log('No backtest data available')
    return
  }

  chartLoading.value = true
  chartError.value = ''

  // 確保 DOM 已渲染
  await nextTick()

  if (!tradeChartRef.value) {
    chartError.value = '圖表元素尚未就緒，請稍後再試'
    chartLoading.value = false
    return
  }

  try {
    const token = localStorage.getItem('access_token')
    if (!token) {
      chartError.value = '未登入，請先登入'
      chartLoading.value = false
      return
    }

    console.log(`Loading price data for ${backtest.value.symbol} from ${backtest.value.start_date} to ${backtest.value.end_date}`)

    // 獲取股票價格資料
    const response = await $fetch<any>(
      `${config.public.apiBase}/api/v1/data/price/${backtest.value.symbol}`,
      {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` },
        params: {
          start_date: backtest.value.start_date,
          end_date: backtest.value.end_date
        }
      }
    )

    priceData.value = response
    await renderTradeChart()
  } catch (error: any) {
    console.error('載入圖表資料失敗:', error)
    chartError.value = error.data?.detail || '無法載入圖表資料'
  } finally {
    chartLoading.value = false
  }
}

// 渲染交易圖表
const renderTradeChart = async () => {
  if (!priceData.value || !backtest.value?.trades) {
    console.log('Missing data for chart:', {
      hasPriceData: !!priceData.value,
      hasTrades: !!backtest.value?.trades
    })
    return
  }

  try {
    await nextTick()
    await initChart()

    if (!chartInstance) {
      console.error('Chart instance not created')
      chartError.value = '圖表初始化失敗'
      return
    }

    console.log('Chart instance ready, rendering...')

    // 準備價格資料
    const rawDates = Object.keys(priceData.value.data).sort()
    const prices = rawDates.map(date => priceData.value.data[date])

    // 標準化日期格式：只取 YYYY-MM-DD 部分
    const normalizeDateStr = (dateStr: string) => {
      if (!dateStr) return ''
      // 處理 "2007-04-23 00:00:00" 或 "2007-04-23" 格式
      return dateStr.split(' ')[0].split('T')[0]
    }

    // 建立日期對應表：normalized date -> original date
    const dateMap: Record<string, string> = {}
    const dates = rawDates.map(date => {
      const normalized = normalizeDateStr(date)
      dateMap[normalized] = date
      return date
    })

    console.log('=== 圖表數據準備 ===')
    console.log('價格數據日期範圍:', dates[0], 'to', dates[dates.length - 1])
    console.log('價格數據點數量:', dates.length)
    console.log('交易總數:', backtest.value.trades.length)
    console.log('日期映射表建立完成，共', Object.keys(dateMap).length, '個標準化日期')

    // 準備交易標記
    const buyMarkers: any[] = []
    const sellMarkers: any[] = []
    let minTradeDate = dates[dates.length - 1]
    let maxTradeDate = dates[0]

    backtest.value.trades.forEach((trade: any, index: number) => {
      const tradeDate = trade.date
      const normalizedTradeDate = normalizeDateStr(tradeDate)

      // 使用標準化日期尋找對應的原始日期
      const matchingDate = dateMap[normalizedTradeDate]

      // 調試：顯示前幾筆交易的資訊
      if (index < 10 && matchingDate) {
        const closePrice = priceData.value.data[matchingDate]
        console.log(`[交易 ${index + 1}] ${trade.action}`, {
          日期: tradeDate,
          成交價: parseFloat(trade.price),
          收盤價: closePrice,
          差異: (closePrice - parseFloat(trade.price)).toFixed(2)
        })
      }

      const dateIndex = matchingDate ? dates.indexOf(matchingDate) : -1

      if (dateIndex !== -1 && matchingDate) {
        // 追蹤交易日期範圍（使用 matchingDate 以便與 dates 陣列比對）
        if (matchingDate < minTradeDate) minTradeDate = matchingDate
        if (matchingDate > maxTradeDate) maxTradeDate = matchingDate

        // 使用當天的收盤價作為 Y 軸座標，而不是交易價格
        const closePrice = priceData.value.data[matchingDate]

        const marker = {
          value: [matchingDate, closePrice],  // Y 軸使用收盤價
          // 保存交易信息用於 tooltip 顯示
          tradePrice: parseFloat(trade.price),
          tradeAction: trade.action,
          tradeQuantity: trade.quantity,
          itemStyle: {
            color: trade.action === 'BUY' ? '#22c55e' : '#ef4444'
          }
        }

        if (trade.action === 'BUY') {
          buyMarkers.push(marker)
        } else {
          sellMarkers.push(marker)
        }
      } else if (index < 3) {
        console.warn(`Trade date ${tradeDate} not found in price data`)
        console.log('Available dates sample:', dates.slice(0, 5))
      }
    })

    console.log(`\n=== 標記創建結果 ===`)
    console.log(`✅ 買入標記: ${buyMarkers.length} 個`)
    console.log(`✅ 賣出標記: ${sellMarkers.length} 個`)

    if (buyMarkers.length > 0) {
      console.log('前 3 個買入標記:')
      buyMarkers.slice(0, 3).forEach((m, i) => {
        console.log(`  買入 ${i+1}: 日期=${m.value[0]}, 價格=${m.value[1]}`)
      })
    }

    if (sellMarkers.length > 0) {
      console.log('前 3 個賣出標記:')
      sellMarkers.slice(0, 3).forEach((m, i) => {
        console.log(`  賣出 ${i+1}: 日期=${m.value[0]}, 價格=${m.value[1]}`)
      })
    }

    // 計算初始縮放範圍
    let zoomStartPercent = 0
    let zoomEndPercent = 100

    if (buyMarkers.length > 0 || sellMarkers.length > 0) {
      // 有交易標記時，聚焦到交易範圍
      const minTradeIndex = dates.indexOf(minTradeDate)
      const maxTradeIndex = dates.indexOf(maxTradeDate)
      const tradeRange = maxTradeIndex - minTradeIndex

      // 計算 padding：交易範圍的 20% 或至少 50 個交易日
      const padding = Math.max(Math.floor(tradeRange * 0.2), 50)

      let zoomStart = Math.max(0, minTradeIndex - padding)
      let zoomEnd = Math.min(dates.length - 1, maxTradeIndex + padding)

      // 確保縮放範圍至少佔整個數據的 30%
      const zoomRange = zoomEnd - zoomStart
      const minZoomRange = Math.floor(dates.length * 0.3)

      if (zoomRange < minZoomRange) {
        // 如果範圍太小，從交易中心點向兩側擴展
        const center = Math.floor((minTradeIndex + maxTradeIndex) / 2)
        zoomStart = Math.max(0, center - Math.floor(minZoomRange / 2))
        zoomEnd = Math.min(dates.length - 1, zoomStart + minZoomRange)

        // 如果右側超出，調整左側
        if (zoomEnd === dates.length - 1) {
          zoomStart = Math.max(0, zoomEnd - minZoomRange)
        }
      }

      zoomStartPercent = (zoomStart / dates.length) * 100
      zoomEndPercent = (zoomEnd / dates.length) * 100

      console.log(`\n=== 縮放範圍計算 ===`)
      console.log(`交易日期範圍: ${minTradeDate} 到 ${maxTradeDate}`)
      console.log(`交易索引範圍: ${minTradeIndex} 到 ${maxTradeIndex} (共 ${tradeRange} 個交易日)`)
      console.log(`縮放索引範圍: ${zoomStart} 到 ${zoomEnd} (共 ${zoomEnd - zoomStart} 個交易日)`)
      console.log(`初始縮放: ${zoomStartPercent.toFixed(1)}% 到 ${zoomEndPercent.toFixed(1)}%`)
    } else {
      // 沒有交易標記時，顯示最後 30% 的資料
      zoomStartPercent = 70
      zoomEndPercent = 100
      console.warn('No trade markers found, showing last 30% of data')
    }

    // 圖表配置
    const option = {
      title: {
        text: `${backtest.value.symbol} 交易記錄視覺化`,
        subtext: `${dates.length} 個交易日 | ${buyMarkers.length} 次買入 | ${sellMarkers.length} 次賣出`,
        left: 'center',
        textStyle: { fontSize: 18, fontWeight: 'bold' },
        subtextStyle: { fontSize: 12, color: '#6b7280' }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: any) => {
          let result = `${params[0].axisValue}<br/>`

          params.forEach((param: any) => {
            if (param.seriesName === '收盤價') {
              result += `收盤價: ${param.data?.toFixed(2)} TWD<br/>`
            } else if (param.seriesName === '買入點') {
              const closePrice = param.data?.value ? param.data.value[1] : param.value[1]
              const tradePrice = param.data?.tradePrice
              const quantity = param.data?.tradeQuantity
              result += `<span style="color: #22c55e">● 買入<br/>`
              result += `  收盤價: ${closePrice?.toFixed(2)} TWD<br/>`
              if (tradePrice) result += `  成交價: ${tradePrice.toFixed(2)} TWD<br/>`
              if (quantity) result += `  數量: ${quantity} 股<br/>`
              result += `</span>`
            } else if (param.seriesName === '賣出點') {
              const closePrice = param.data?.value ? param.data.value[1] : param.value[1]
              const tradePrice = param.data?.tradePrice
              const quantity = param.data?.tradeQuantity
              result += `<span style="color: #ef4444">● 賣出<br/>`
              result += `  收盤價: ${closePrice?.toFixed(2)} TWD<br/>`
              if (tradePrice) result += `  成交價: ${tradePrice.toFixed(2)} TWD<br/>`
              if (quantity) result += `  數量: ${quantity} 股<br/>`
              result += `</span>`
            }
          })

          return result
        }
      },
      legend: {
        data: ['收盤價', '買入點', '賣出點'],
        top: 60
      },
      // 添加資料縮放控制
      dataZoom: [
        {
          type: 'slider',
          show: true,
          xAxisIndex: 0,
          start: zoomStartPercent,  // 智能初始範圍
          end: zoomEndPercent,      // 智能初始範圍
          height: 30,
          bottom: 10,
          borderColor: '#e5e7eb',
          fillerColor: 'rgba(59, 130, 246, 0.15)',
          handleStyle: {
            color: '#3b82f6'
          },
          textStyle: {
            color: '#6b7280'
          },
          labelFormatter: (value: number) => {
            const date = new Date(dates[value])
            return `${date.getFullYear()}/${date.getMonth() + 1}`
          }
        },
        {
          type: 'inside',
          xAxisIndex: 0,
          start: zoomStartPercent,
          end: zoomEndPercent,
          zoomOnMouseWheel: true,   // 滾輪縮放
          moveOnMouseMove: true,    // 滑鼠拖動
          moveOnMouseWheel: false   // 禁用滾輪移動（改用拖動）
        }
      ],
      grid: {
        left: '3%',
        right: '4%',
        bottom: '80px',  // 增加底部空間給縮放控制條
        top: 100,
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
        name: '價格 (TWD)',
        scale: true,
        axisLabel: {
          formatter: (value: number) => value.toFixed(0)
        }
      },
      series: [
        {
          name: '收盤價',
          type: 'line',
          data: prices,
          smooth: false,
          symbol: 'none',
          lineStyle: { width: 2, color: '#3b82f6' },
          itemStyle: { color: '#3b82f6' },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(59, 130, 246, 0.2)' },
                { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
              ]
            }
          }
        },
        {
          name: '買入點',
          type: 'scatter',
          data: buyMarkers,
          symbol: 'triangle',
          symbolSize: 15,
          symbolRotate: 0,
          itemStyle: {
            color: '#22c55e',
            borderColor: '#16a34a',
            borderWidth: 2
          },
          zlevel: 10
        },
        {
          name: '賣出點',
          type: 'scatter',
          data: sellMarkers,
          symbol: 'triangle',
          symbolSize: 15,
          symbolRotate: 180,
          itemStyle: {
            color: '#ef4444',
            borderColor: '#dc2626',
            borderWidth: 2
          },
          zlevel: 10
        }
      ]
    }

    chartInstance.setOption(option)

    // 強制調整圖表大小以確保正確顯示
    setTimeout(() => {
      if (chartInstance) {
        chartInstance.resize()
        console.log('Chart resized after rendering')
      }
    }, 100)

    console.log('\n=== 圖表渲染完成 ===')
    console.log('✅ 圖表已成功渲染')
    console.log('📊 圖表包含 3 個系列:', option.series.map((s: any) => s.name))
  } catch (error: any) {
    console.error('渲染圖表失敗:', error)
    chartError.value = error.message || '圖表渲染失敗'
  }
}

// ===== 視覺化圖表渲染函數 =====

// 1. 淨值曲線圖
const renderNavChart = () => {
  if (!detailedResults.value?.daily_nav || !navChartRef.value) return

  if (!window.echarts) {
    console.warn('ECharts not loaded yet')
    return
  }

  if (navChart) {
    navChart.dispose()
  }

  navChart = window.echarts.init(navChartRef.value)
  const data = detailedResults.value.daily_nav
  const drawdowns = detailedResults.value.drawdown_series || []

  const dates = data.map((d: any) => d.date)
  const values = data.map((d: any) => d.value)

  // 計算回撤區域數據
  const drawdownMap: Record<string, number> = {}
  drawdowns.forEach((d: any) => {
    drawdownMap[d.date] = d.drawdown_pct
  })

  const areaData = dates.map((date: string, i: number) => {
    const dd = drawdownMap[date]
    return dd && dd < 0 ? values[i] : null
  })

  const option = {
    title: { text: '淨值曲線與回撤', left: 'center' },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const date = params[0].axisValue
        const nav = params[0].value
        const dd = drawdownMap[date]
        return `
          <b>${date}</b><br/>
          淨值: ${nav ? nav.toLocaleString('zh-TW', { style: 'currency', currency: 'TWD' }) : '-'}<br/>
          ${dd ? `回撤: ${dd.toFixed(2)}%` : ''}
        `
      }
    },
    grid: { left: 60, right: 60, top: 60, bottom: 60 },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (value: number) => value.toLocaleString()
      }
    },
    series: [
      {
        name: '淨值',
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#3b82f6' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
              { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
            ]
          }
        }
      },
      {
        name: '回撤區域',
        type: 'line',
        data: areaData,
        showSymbol: false,
        lineStyle: { width: 0 },
        areaStyle: { color: 'rgba(239, 68, 68, 0.2)' },
        z: 0
      }
    ]
  }

  navChart.setOption(option)
  navChart.resize()
}

// 2. 月度報酬熱圖
const renderMonthlyChart = () => {
  if (!detailedResults.value?.monthly_returns || !monthlyChartRef.value) return

  if (!window.echarts) {
    console.warn('ECharts not loaded yet')
    return
  }

  if (monthlyChart) {
    monthlyChart.dispose()
  }

  monthlyChart = window.echarts.init(monthlyChartRef.value)
  const data = detailedResults.value.monthly_returns

  // 轉換為熱圖格式 [year, month, return]
  const heatmapData = data.map((d: any) => {
    const [year, month] = d.month.split('-')
    return [parseInt(year), parseInt(month) - 1, d.return_pct]
  })

  const years = [...new Set(heatmapData.map((d: any) => d[0]))].sort()

  const option = {
    title: { text: '月度報酬熱圖', left: 'center' },
    tooltip: {
      formatter: (params: any) => {
        const [year, month, value] = params.data
        const monthName = ['1月', '2月', '3月', '4月', '5月', '6月',
                          '7月', '8月', '9月', '10月', '11月', '12月'][month]
        const color = value >= 0 ? '🟢' : '🔴'
        return `${color} ${year}年 ${monthName}<br/>報酬: ${value.toFixed(2)}%`
      }
    },
    grid: { left: 80, right: 20, top: 60, bottom: 100 },
    xAxis: {
      type: 'category',
      data: ['1月', '2月', '3月', '4月', '5月', '6月',
             '7月', '8月', '9月', '10月', '11月', '12月'],
      splitArea: { show: true }
    },
    yAxis: {
      type: 'category',
      data: years,
      splitArea: { show: true }
    },
    visualMap: {
      min: Math.min(...data.map((d: any) => d.return_pct)),
      max: Math.max(...data.map((d: any) => d.return_pct)),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 10,
      inRange: {
        color: ['#ef4444', '#f5f5f5', '#22c55e']
      }
    },
    series: [{
      type: 'heatmap',
      data: heatmapData,
      label: {
        show: true,
        formatter: (params: any) => params.data[2].toFixed(1) + '%'
      },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
      }
    }]
  }

  monthlyChart.setOption(option)
  monthlyChart.resize()
}

// 3. 交易分佈圖
const renderDistributionChart = () => {
  if (!detailedResults.value?.trade_distribution || !distributionChartRef.value) return

  if (!window.echarts) {
    console.warn('ECharts not loaded yet')
    return
  }

  if (distributionChart) {
    distributionChart.dispose()
  }

  distributionChart = window.echarts.init(distributionChartRef.value)
  const dist = detailedResults.value.trade_distribution

  const option = {
    title: { text: '交易損益分佈', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['獲利交易', '虧損交易'], bottom: 10 },
    grid: { left: 60, right: 60, top: 60, bottom: 80 },
    xAxis: {
      type: 'category',
      data: ['區間1', '區間2', '區間3', '區間4', '區間5',
             '區間6', '區間7', '區間8', '區間9', '區間10'],
      axisLabel: { rotate: 45 }
    },
    yAxis: { type: 'value', name: '交易次數' },
    series: [
      {
        name: '獲利交易',
        type: 'bar',
        data: dist.profit_bins,
        itemStyle: { color: '#22c55e' }
      },
      {
        name: '虧損交易',
        type: 'bar',
        data: dist.loss_bins,
        itemStyle: { color: '#ef4444' }
      }
    ]
  }

  distributionChart.setOption(option)
  distributionChart.resize()
}

// 4. 滾動夏普率圖
const renderRollingChart = () => {
  if (!detailedResults.value?.rolling_sharpe || !rollingChartRef.value) return

  if (!window.echarts) {
    console.warn('ECharts not loaded yet')
    return
  }

  if (rollingChart) {
    rollingChart.dispose()
  }

  rollingChart = window.echarts.init(rollingChartRef.value)
  const data = detailedResults.value.rolling_sharpe

  const dates = data.map((d: any) => d.date)
  const sharpe = data.map((d: any) => d.sharpe)

  const option = {
    title: { text: '滾動夏普率（30天窗口）', left: 'center' },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const date = params[0].axisValue
        const value = params[0].value
        const status = value > 1 ? '🟢 良好' : value > 0 ? '🟡 一般' : '🔴 不佳'
        return `${date}<br/>夏普率: ${value.toFixed(2)} ${status}`
      }
    },
    grid: { left: 60, right: 60, top: 60, bottom: 60 },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      name: '夏普率'
    },
    series: [{
      type: 'line',
      data: sharpe,
      smooth: true,
      lineStyle: { width: 2, color: '#6366f1' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(99, 102, 241, 0.3)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0.05)' }
          ]
        }
      },
      markLine: {
        data: [
          { yAxis: 0, label: { formatter: '基準線' }, lineStyle: { color: '#999', type: 'dashed' } },
          { yAxis: 1, label: { formatter: '良好 (1.0)' }, lineStyle: { color: '#22c55e', type: 'dashed' } }
        ]
      }
    }]
  }

  rollingChart.setOption(option)
  rollingChart.resize()
}

// 視窗大小改變時調整圖表
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
  // 調整視覺化圖表
  if (navChart) navChart.resize()
  if (monthlyChart) monthlyChart.resize()
  if (distributionChart) distributionChart.resize()
  if (rollingChart) rollingChart.resize()
}

// 監聽標籤頁切換，渲染對應圖表
watch(activeTab, (newTab) => {
  nextTick(() => {
    switch (newTab) {
      case 'nav':
        renderNavChart()
        break
      case 'monthly':
        renderMonthlyChart()
        break
      case 'distribution':
        renderDistributionChart()
        break
      case 'rolling':
        renderRollingChart()
        break
    }
  })
})

// 監聽資料變化，重新渲染當前圖表
watch(() => backtest.value?.result?.detailed_results, (newData) => {
  if (newData) {
    nextTick(() => {
      // 渲染當前標籤頁的圖表
      switch (activeTab.value) {
        case 'nav':
          renderNavChart()
          break
        case 'monthly':
          renderMonthlyChart()
          break
        case 'distribution':
          renderDistributionChart()
          break
        case 'rolling':
          renderRollingChart()
          break
      }
    })
  }
})

// 載入資料
onMounted(() => {
  loadUserInfo()

  if (process.client) {
    // 添加視窗大小監聽
    window.addEventListener('resize', handleResize)
  }

  loadBacktestDetail()
})

onUnmounted(() => {
  if (process.client) {
    window.removeEventListener('resize', handleResize)
  }

  // 清理交易圖表實例
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }

  // 清理視覺化圖表實例
  if (navChart) {
    navChart.dispose()
    navChart = null
  }
  if (monthlyChart) {
    monthlyChart.dispose()
    monthlyChart = null
  }
  if (distributionChart) {
    distributionChart.dispose()
    distributionChart = null
  }
  if (rollingChart) {
    rollingChart.dispose()
    rollingChart = null
  }
})

// 不再自動載入圖表，改為用戶手動點擊按鈕載入
// 這樣可以避免 DOM 時序問題
</script>

<style scoped lang="scss">
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

.back-button-container {
  margin-bottom: 2rem;
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: white;
  color: #6b7280;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s;

  &:hover {
    background: #f3f4f6;
    border-color: #3b82f6;
    color: #3b82f6;
  }
}

.loading-state {
  text-align: center;
  padding: 4rem 2rem;

  .spinner {
    width: 3rem;
    height: 3rem;
    border: 4px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  padding: 1rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  margin-bottom: 1rem;
}

.backtest-detail {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.info-card,
.metrics-card,
.trades-card {
  background: white;
  padding: 2rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 1.5rem 0;
}

// 交易圖表樣式
.trade-chart-section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;

  h3 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: #111827;
  }
}

.btn-refresh {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: white;
  color: #3b82f6;
  border: 1px solid #3b82f6;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: #3b82f6;
    color: white;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.trade-chart-canvas {
  width: 100%;
  height: 600px;  // 增加高度以容納縮放控制條
  background: white;
  border-radius: 0.5rem;
}

.chart-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #6b7280;

  .spinner {
    width: 2rem;
    height: 2rem;
    border: 3px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }
}

.chart-error {
  padding: 1rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  text-align: center;
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  background: white;
  border-radius: 0.5rem;
  border: 2px dashed #e5e7eb;
  color: #6b7280;

  .placeholder-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  p {
    margin: 0;
    font-size: 0.875rem;
  }
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 0.5rem;

  .info-label {
    color: #6b7280;
    font-weight: 500;
  }

  .info-value {
    color: #111827;
    font-weight: 600;
  }
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.875rem;
  font-weight: 500;

  &.status-pending {
    background: #f3f4f6;
    color: #6b7280;
  }

  &.status-running {
    background: #fef3c7;
    color: #92400e;
  }

  &.status-completed {
    background: #d1fae5;
    color: #065f46;
  }

  &.status-failed {
    background: #fee2e2;
    color: #991b1b;
  }
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.metric-item {
  text-align: center;
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 0.75rem;
  border: 2px solid #e5e7eb;
  transition: all 0.2s;

  &:hover {
    border-color: #3b82f6;
    transform: translateY(-2px);
  }

  .metric-label {
    color: #6b7280;
    font-size: 0.875rem;
    font-weight: 500;
    margin-bottom: 0.5rem;
  }

  .metric-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #111827;

    &.positive {
      color: #059669;
    }

    &.negative {
      color: #dc2626;
    }
  }
}

.trades-table-container {
  overflow-x: auto;
}

.trades-table {
  width: 100%;
  border-collapse: collapse;

  th {
    background: #f9fafb;
    padding: 0.75rem 1rem;
    text-align: left;
    font-weight: 600;
    color: #374151;
    border-bottom: 2px solid #e5e7eb;
  }

  td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #e5e7eb;
    color: #111827;
  }

  tr:hover {
    background: #f9fafb;
  }
}

.trade-type {
  padding: 0.25rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;

  &.buy {
    background: #d1fae5;
    color: #065f46;
  }

  &.sell {
    background: #fee2e2;
    color: #991b1b;
  }
}

.pnl {
  font-weight: 600;

  &.positive {
    color: #059669;
  }

  &.negative {
    color: #dc2626;
  }
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: stretch;
  }

  .nav-links {
    flex-direction: column;
  }

  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .trades-table {
    font-size: 0.875rem;

    th, td {
      padding: 0.5rem;
    }
  }
}

/* 引擎徽章樣式 */
.engine-badge {
  font-size: 0.875rem;
  padding: 0.375rem 0.875rem;
  border-radius: 16px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.engine-badge.backtrader {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.engine-badge.qlib {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

/* ===== 視覺化圖表樣式 ===== */
.charts-container {
  margin-top: 2rem;
  background: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tabs-nav {
  display: flex;
  gap: 0.5rem;
  border-bottom: 2px solid #e5e7eb;
  margin-bottom: 1.5rem;
  overflow-x: auto;

  /* 滾動條樣式 */
  &::-webkit-scrollbar {
    height: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: #d1d5db;
    border-radius: 2px;
  }
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #6b7280;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  margin-bottom: -2px;

  &:hover {
    color: #3b82f6;
    background: #eff6ff;
  }

  &.active {
    color: #3b82f6;
    border-bottom-color: #3b82f6;
    font-weight: 600;
  }
}

.tab-content {
  min-height: 400px;
}

.chart-panel {
  animation: fadeIn 0.3s ease-in-out;
}

.chart-canvas {
  width: 100%;
  height: 500px;
  min-height: 400px;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 響應式調整 */
@media (max-width: 768px) {
  .charts-container {
    padding: 1rem;
  }

  .chart-canvas {
    height: 350px;
    min-height: 300px;
  }

  .tab-button {
    padding: 0.5rem 0.875rem;
    font-size: 0.8125rem;
  }
}
</style>
