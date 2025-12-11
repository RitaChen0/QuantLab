<template>
  <div class="intraday-chart-container">
    <!-- 時間粒度選擇 -->
    <div class="controls">
      <div class="timeframe-selector">
        <label>時間粒度：</label>
        <div class="timeframe-buttons">
          <button
            v-for="tf in timeframes"
            :key="tf.value"
            @click="selectTimeframe(tf.value)"
            :class="['timeframe-btn', { active: timeframe === tf.value }]"
          >
            {{ tf.label }}
          </button>
        </div>
      </div>

      <div class="period-selector">
        <label>顯示範圍：</label>
        <div class="period-buttons">
          <button
            v-for="period in periods"
            :key="period.value"
            @click="selectPeriod(period.value)"
            :class="['period-btn', { active: selectedPeriod === period.value }]"
          >
            {{ period.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- 載入按鈕 -->
    <div class="load-section">
      <button @click="loadIntradayData" class="btn-load" :disabled="loading">
        {{ loading ? '載入中...' : '📊 載入分鐘線資料' }}
      </button>
      <span v-if="dataInfo" class="data-info">
        📊 {{ dataInfo }}
      </span>
    </div>

    <!-- 錯誤訊息 -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- 圖表容器 -->
    <div v-show="chartData" class="chart-wrapper">
      <div ref="chartRef" class="chart-canvas"></div>
    </div>

    <!-- 統計資訊 -->
    <div v-if="chartData && statistics" class="statistics">
      <h4>統計資訊</h4>
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-label">資料筆數：</span>
          <span class="stat-value">{{ statistics.count }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">時間範圍：</span>
          <span class="stat-value">{{ statistics.timeRange }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">最高價：</span>
          <span class="stat-value">{{ statistics.maxPrice }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">最低價：</span>
          <span class="stat-value">{{ statistics.minPrice }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">總成交量：</span>
          <span class="stat-value">{{ statistics.totalVolume }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  stockId: string
  stockName: string
}>()

const config = useRuntimeConfig()

// 時間粒度選項
const timeframes = [
  { label: '1 分鐘', value: '1min' },
  { label: '5 分鐘', value: '5min' },
  { label: '15 分鐘', value: '15min' },
  { label: '30 分鐘', value: '30min' },
  { label: '60 分鐘', value: '60min' }
]

// 顯示範圍選項
const periods = [
  { label: '今日', value: 1 },
  { label: '3 天', value: 3 },
  { label: '5 天', value: 5 },
  { label: '10 天', value: 10 },
  { label: '30 天', value: 30 }
]

// 狀態
const timeframe = ref('1min')
const selectedPeriod = ref(1)
const loading = ref(false)
const error = ref('')
const chartData = ref<any>(null)
const dataInfo = ref('')
const statistics = ref<any>(null)

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: any = null

// TypeScript 聲明
declare global {
  interface Window {
    echarts: any
  }
}

// 選擇時間粒度
const selectTimeframe = (value: string) => {
  timeframe.value = value
  if (chartData.value) {
    // 如果已有數據，自動重新載入
    loadIntradayData()
  }
}

// 選擇顯示範圍
const selectPeriod = (value: number) => {
  selectedPeriod.value = value
  if (chartData.value) {
    // 如果已有數據，自動重新載入
    loadIntradayData()
  }
}

// 載入分鐘級數據
const loadIntradayData = async () => {
  loading.value = true
  error.value = ''
  chartData.value = null
  dataInfo.value = ''
  statistics.value = null

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      throw new Error('未登入，請先登入')
    }

    // 計算日期範圍
    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - selectedPeriod.value)

    // 調用 API
    const response = await $fetch<any>(
      `${config.public.apiBase}/api/v1/intraday/ohlcv/${props.stockId}`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        params: {
          timeframe: timeframe.value,
          limit: 10000  // 最多取 10000 筆
        }
      }
    )

    console.log('Intraday data loaded:', response)

    if (!response.data || Object.keys(response.data).length === 0) {
      error.value = '無可用的分鐘級數據'
      return
    }

    chartData.value = response

    // 計算統計資訊
    calculateStatistics()

    // 顯示資料資訊
    dataInfo.value = `${response.count} 筆 ${timeframe.value} 數據`

    // 渲染圖表
    await renderChart()
  } catch (err: any) {
    console.error('Failed to load intraday data:', err)
    error.value = err.data?.detail || err.message || '載入分鐘級數據失敗'
  } finally {
    loading.value = false
  }
}

// 計算統計資訊
const calculateStatistics = () => {
  if (!chartData.value || !chartData.value.data) return

  const data = chartData.value.data
  const dates = Object.keys(data).sort()

  if (dates.length === 0) return

  let maxPrice = -Infinity
  let minPrice = Infinity
  let totalVolume = 0

  dates.forEach(date => {
    const item = data[date]
    maxPrice = Math.max(maxPrice, item.high)
    minPrice = Math.min(minPrice, item.low)
    totalVolume += item.volume
  })

  statistics.value = {
    count: dates.length,
    timeRange: `${formatDateTime(dates[0])} ~ ${formatDateTime(dates[dates.length - 1])}`,
    maxPrice: maxPrice.toFixed(2),
    minPrice: minPrice.toFixed(2),
    totalVolume: formatVolume(totalVolume)
  }
}

// 初始化 ECharts
const initChart = async () => {
  if (!process.client) return

  try {
    // 動態載入 ECharts
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
        script.onerror = () => reject(new Error('Failed to load ECharts'))
        setTimeout(() => reject(new Error('ECharts load timeout')), 10000)
      })
    }

    if (chartRef.value && window.echarts) {
      // 如果已有實例，先銷毀
      if (chartInstance) {
        chartInstance.dispose()
      }
      chartInstance = window.echarts.init(chartRef.value)

      // 調整大小
      setTimeout(() => {
        chartInstance?.resize()
      }, 100)
    }
  } catch (err) {
    console.error('Error initializing chart:', err)
    error.value = '圖表初始化失敗'
  }
}

// 渲染圖表
const renderChart = async () => {
  if (!chartData.value) return
  if (!process.client) return

  try {
    await nextTick()
    await initChart()

    if (!chartInstance) {
      console.error('Chart instance not created')
      return
    }

    const data = chartData.value.data
    const dates = Object.keys(data).sort()

    // 準備 K 線數據
    const klineData = dates.map(date => {
      const item = data[date]
      return [item.open, item.close, item.low, item.high]
    })

    // 準備成交量數據
    const volumes = dates.map(date => data[date].volume)

    // 格式化日期顯示
    const formattedDates = dates.map(date => {
      const d = new Date(date)
      return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
    })

    const option = {
      title: {
        text: `${props.stockName} 分鐘線 (${timeframe.value})`,
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
          const dateIndex = params[0].dataIndex
          const date = dates[dateIndex]
          const ohlc = params[0].data
          const volume = params[1]?.data || 0
          return `${formatDateTime(date)}<br/>` +
                 `開: ${ohlc[0]?.toFixed(2)}<br/>` +
                 `收: ${ohlc[1]?.toFixed(2)}<br/>` +
                 `低: ${ohlc[2]?.toFixed(2)}<br/>` +
                 `高: ${ohlc[3]?.toFixed(2)}<br/>` +
                 `量: ${formatVolume(volume)}`
        }
      },
      grid: [{
        left: '3%',
        right: '4%',
        height: '60%',
        top: '15%'
      }, {
        left: '3%',
        right: '4%',
        top: '78%',
        height: '15%'
      }],
      xAxis: [{
        type: 'category',
        data: formattedDates,
        gridIndex: 0,
        axisLabel: {
          show: false
        }
      }, {
        type: 'category',
        data: formattedDates,
        gridIndex: 1,
        axisLabel: {
          rotate: 45,
          interval: Math.floor(dates.length / 10) || 1
        }
      }],
      yAxis: [{
        type: 'value',
        name: '價格 (TWD)',
        gridIndex: 0,
        scale: true,
        splitLine: {
          lineStyle: {
            color: '#e5e7eb'
          }
        }
      }, {
        type: 'value',
        name: '成交量',
        gridIndex: 1,
        scale: true,
        splitLine: {
          show: false
        }
      }],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: dates.length > 100 ? 70 : 0,
          end: 100
        },
        {
          type: 'slider',
          xAxisIndex: [0, 1],
          start: dates.length > 100 ? 70 : 0,
          end: 100,
          bottom: '2%',
          height: 20
        }
      ],
      series: [{
        name: 'K線',
        type: 'candlestick',
        data: klineData,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#ef4444',    // 漲（紅）
          color0: '#22c55e',   // 跌（綠）
          borderColor: '#ef4444',
          borderColor0: '#22c55e'
        }
      }, {
        name: '成交量',
        type: 'bar',
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: {
          color: '#94a3b8'
        }
      }]
    }

    chartInstance.setOption(option)

    // 確保圖表正確渲染
    setTimeout(() => {
      chartInstance?.resize()
    }, 100)

    console.log('Intraday chart rendered successfully')
  } catch (err) {
    console.error('Error rendering chart:', err)
    error.value = '圖表渲染失敗'
  }
}

// 格式化日期時間
const formatDateTime = (dateStr: string) => {
  const date = new Date(dateStr)
  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`
}

// 格式化成交量
const formatVolume = (volume: any) => {
  if (volume === null || volume === undefined) return '-'
  const numVolume = typeof volume === 'string' ? parseFloat(volume) : volume
  if (isNaN(numVolume)) return '-'
  if (numVolume >= 1000000) {
    return (numVolume / 1000000).toFixed(2) + 'M'
  } else if (numVolume >= 1000) {
    return (numVolume / 1000).toFixed(2) + 'K'
  }
  return numVolume.toString()
}

// 監聽窗口大小變化
onMounted(() => {
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
</script>

<style scoped lang="scss">
.intraday-chart-container {
  margin-top: 1rem;
}

.controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 0.5rem;
}

.timeframe-selector,
.period-selector {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

  label {
    font-weight: 600;
    color: #374151;
    font-size: 0.875rem;
  }
}

.timeframe-buttons,
.period-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.timeframe-btn,
.period-btn {
  padding: 0.5rem 1rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
  font-size: 0.875rem;

  &:hover {
    border-color: #3b82f6;
    background: #eff6ff;
  }

  &.active {
    background: #3b82f6;
    color: white;
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

.data-info {
  color: #059669;
  font-size: 0.875rem;
  font-weight: 500;
}

.error-message {
  padding: 1rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  margin-bottom: 1rem;
}

.chart-wrapper {
  margin-bottom: 2rem;
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-canvas {
  width: 100%;
  height: 600px;
}

.statistics {
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 0.5rem;

  h4 {
    margin: 0 0 1rem 0;
    color: #111827;
    font-size: 1rem;
    font-weight: 600;
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
    font-size: 0.875rem;
  }

  .stat-value {
    font-weight: 600;
    color: #111827;
    font-size: 0.875rem;
  }
}

@media (max-width: 768px) {
  .controls {
    padding: 1rem;
  }

  .chart-canvas {
    height: 400px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
