<template>
  <div class="fundamental-analysis">
    <!-- 財務指標選擇 -->
    <div class="indicator-selector">
      <div class="selector-header">
        <h3>📊 選擇財務指標</h3>
        <button @click="loadIndicators" class="btn-refresh" :disabled="loadingIndicators">
          {{ loadingIndicators ? '載入中...' : '🔄 重新載入' }}
        </button>
      </div>

      <!-- 分類選擇 -->
      <div class="category-tabs">
        <button
          v-for="cat in categories"
          :key="cat.key"
          @click="selectedCategory = cat.key"
          :class="['category-btn', { active: selectedCategory === cat.key }]"
        >
          {{ cat.label }}
        </button>
      </div>

      <!-- 指標選擇 -->
      <div v-if="filteredIndicators.length > 0" class="indicators-grid">
        <button
          v-for="indicator in filteredIndicators"
          :key="indicator.name"
          @click="toggleIndicator(indicator.name)"
          :class="['indicator-btn', { selected: selectedIndicators.includes(indicator.name) }]"
        >
          <span class="indicator-name">{{ indicator.name }}</span>
          <span class="indicator-name-en">{{ indicator.name_en }}</span>
        </button>
      </div>

      <div v-if="selectedIndicators.length > 0" class="selected-count">
        已選擇 {{ selectedIndicators.length }} 個指標
      </div>
    </div>

    <!-- 載入按鈕 -->
    <div class="action-section">
      <button
        @click="loadFundamentalData"
        class="btn-load-fundamental"
        :disabled="loadingData || selectedIndicators.length === 0"
      >
        {{ loadingData ? '載入中...' : '📈 載入財務數據' }}
      </button>
      <span v-if="selectedIndicators.length === 0" class="hint-text">
        💡 請至少選擇一個財務指標
      </span>
    </div>

    <!-- 錯誤訊息 -->
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>

    <!-- 圖表顯示 -->
    <div v-if="fundamentalData && Object.keys(fundamentalData).length > 0" class="chart-display">
      <div class="chart-header">
        <h3>📊 財務指標趨勢圖</h3>
      </div>
      <div ref="fundamentalChartRef" class="fundamental-chart-canvas"></div>

      <!-- 最新數據表格 -->
      <div class="latest-data-section">
        <h3>最新財務數據</h3>
        <div class="data-cards">
          <div
            v-for="(data, indicator) in fundamentalData"
            :key="indicator"
            v-show="data && data.length > 0"
            class="data-card"
          >
            <div class="card-indicator">{{ indicator }}</div>
            <div class="card-value">
              {{ getLatestValue(data) }}
            </div>
            <div class="card-date">
              {{ getLatestDate(data) }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  stockId: string
  stockName: string
  startDate: string
  endDate: string
}>()

const config = useRuntimeConfig()

// 狀態
const loadingIndicators = ref(false)
const loadingData = ref(false)
const errorMessage = ref('')

// 指標數據
const allIndicators = ref<any[]>([])
const selectedCategory = ref('all')
const selectedIndicators = ref<string[]>([])
const fundamentalData = ref<any>({})

// 圖表實例
const fundamentalChartRef = ref<HTMLElement | null>(null)
let chartInstance: any = null

// 分類定義
const categories = [
  { key: 'all', label: '全部' },
  { key: '獲利能力', label: '獲利能力' },
  { key: '成長性', label: '成長性' },
  { key: '經營效率', label: '經營效率' },
  { key: '財務結構', label: '財務結構' },
  { key: '每股指標', label: '每股指標' },
]

// 過濾指標
const filteredIndicators = computed(() => {
  if (selectedCategory.value === 'all') {
    return allIndicators.value
  }
  return allIndicators.value.filter(ind => ind.category === selectedCategory.value)
})

// 載入可用指標
const loadIndicators = async () => {
  loadingIndicators.value = true
  errorMessage.value = ''

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) return

    const response = await $fetch<any>(
      `${config.public.apiBase}/api/v1/data/fundamental/indicators`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    allIndicators.value = response.indicators || []
    console.log('Loaded indicators:', allIndicators.value.length)
  } catch (error: any) {
    console.error('Failed to load indicators:', error)
    errorMessage.value = '載入指標失敗'
  } finally {
    loadingIndicators.value = false
  }
}

// 切換指標選擇
const toggleIndicator = (indicator: string) => {
  const index = selectedIndicators.value.indexOf(indicator)
  if (index > -1) {
    selectedIndicators.value.splice(index, 1)
  } else {
    if (selectedIndicators.value.length >= 5) {
      alert('最多只能選擇 5 個指標')
      return
    }
    selectedIndicators.value.push(indicator)
  }
}

// 載入財務數據
const loadFundamentalData = async () => {
  if (selectedIndicators.value.length === 0) return

  loadingData.value = true
  errorMessage.value = ''

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) return

    console.log('Sending request with:', {
      stockId: props.stockId,
      indicators: selectedIndicators.value,
      startDate: props.startDate,
      endDate: props.endDate
    })

    const response = await $fetch<any>(
      `${config.public.apiBase}/api/v1/data/fundamental/${props.stockId}/batch`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: {
          stock_id: props.stockId,
          indicators: selectedIndicators.value,
          start_date: props.startDate,
          end_date: props.endDate
        }
      }
    )

    console.log('API Response:', response)
    console.log('Response indicators:', response.indicators)

    // 檢查每個指標的數據
    if (response.indicators) {
      Object.entries(response.indicators).forEach(([ind, data]: [string, any]) => {
        console.log(`Indicator ${ind}:`, Array.isArray(data) ? `${data.length} data points` : 'Not an array', data)
      })
    }

    fundamentalData.value = response.indicators || {}
    console.log('Loaded fundamental data:', Object.keys(fundamentalData.value).length, 'indicators')
    console.log('fundamentalData.value:', fundamentalData.value)

    // 檢查並統計有數據的指標
    const indicatorsWithData: string[] = []
    const indicatorsWithoutData: string[] = []

    Object.entries(fundamentalData.value).forEach(([ind, data]: [string, any]) => {
      if (data && Array.isArray(data) && data.length > 0) {
        indicatorsWithData.push(ind)
      } else {
        indicatorsWithoutData.push(ind)
      }
    })

    console.log(`✅ 有數據的指標 (${indicatorsWithData.length}):`, indicatorsWithData)
    if (indicatorsWithoutData.length > 0) {
      console.warn(`⚠️  無數據的指標 (${indicatorsWithoutData.length}):`, indicatorsWithoutData)
    }

    // 渲染圖表
    await renderFundamentalChart()
  } catch (error: any) {
    console.error('Failed to load fundamental data:', error)
    errorMessage.value = error.data?.detail || '載入財務數據失敗'
  } finally {
    loadingData.value = false
  }
}

// 初始化圖表
const initFundamentalChart = async () => {
  if (!process.client) return

  try {
    // 確保 ECharts 已載入
    if (!window.echarts) {
      console.log('Loading ECharts...')
      const script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'
      document.head.appendChild(script)

      await new Promise((resolve, reject) => {
        script.onload = resolve
        script.onerror = reject
        setTimeout(() => reject(new Error('ECharts load timeout')), 10000)
      })
    }

    if (fundamentalChartRef.value && window.echarts) {
      if (chartInstance) {
        chartInstance.dispose()
      }
      chartInstance = window.echarts.init(fundamentalChartRef.value)
    }
  } catch (error) {
    console.error('Error initializing chart:', error)
    errorMessage.value = '圖表初始化失敗'
  }
}

// 渲染財務指標圖表
const renderFundamentalChart = async () => {
  if (!fundamentalData.value || Object.keys(fundamentalData.value).length === 0) {
    console.log('No fundamental data to render')
    return
  }

  await nextTick()
  await initFundamentalChart()

  if (!chartInstance) {
    console.error('Chart instance not created')
    return
  }

  try {
    // 準備數據
    const allDates = new Set<string>()
    const seriesData: any[] = []
    const colors = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6']
    let colorIndex = 0

    console.log('Processing fundamental data:', fundamentalData.value)

    Object.entries(fundamentalData.value).forEach(([indicator, dataPoints]: [string, any]) => {
      console.log(`Processing indicator: ${indicator}, data points:`, dataPoints.length)

      // 跳過沒有數據的指標
      if (!dataPoints || dataPoints.length === 0) {
        console.warn(`Skipping indicator ${indicator}: no data points`)
        return
      }

      // 收集所有日期
      dataPoints.forEach((point: any) => {
        allDates.add(point.date)
      })

      // 創建時間序列
      const dataMap = new Map<string, number | null>()
      dataPoints.forEach((point: any) => {
        dataMap.set(point.date, point.value)
      })

      const sortedDates = Array.from(allDates).sort()
      const seriesValues = sortedDates.map(date => dataMap.get(date) ?? null)

      console.log(`${indicator} series data:`, seriesValues)

      seriesData.push({
        name: indicator,
        type: 'line',
        data: seriesValues,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: {
          width: 3,
          color: colors[colorIndex % colors.length]
        },
        itemStyle: {
          color: colors[colorIndex % colors.length]
        }
      })

      colorIndex++
    })

    const sortedDates = Array.from(allDates).sort()
    console.log('Chart dates:', sortedDates)
    console.log('Chart series:', seriesData.length)

    const option = {
      title: {
        text: `${props.stockName} 財務指標趨勢`,
        left: 'center',
        textStyle: {
          fontSize: 18,
          fontWeight: 'bold',
          color: '#111827'
        },
        top: 10
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        },
        formatter: (params: any) => {
          let result = `<div style="font-weight: bold; margin-bottom: 5px;">${params[0].axisValue}</div>`
          params.forEach((param: any) => {
            const value = param.value !== null ? param.value.toFixed(2) + '%' : '-'
            result += `<div style="margin: 2px 0;">
              <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${param.color};margin-right:5px;"></span>
              ${param.seriesName}: <strong>${value}</strong>
            </div>`
          })
          return result
        }
      },
      legend: {
        data: Object.keys(fundamentalData.value),
        top: 45,
        left: 'center',
        textStyle: {
          fontSize: 12,
          color: '#374151'
        }
      },
      grid: {
        left: '5%',
        right: '5%',
        bottom: '10%',
        top: '25%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: sortedDates,
        axisLabel: {
          rotate: 45,
          fontSize: 11,
          color: '#6b7280'
        },
        axisLine: {
          lineStyle: {
            color: '#e5e7eb'
          }
        }
      },
      yAxis: {
        type: 'value',
        name: '指標值 (%)',
        nameTextStyle: {
          color: '#6b7280',
          fontSize: 12,
          padding: [0, 0, 0, 10]
        },
        axisLabel: {
          formatter: '{value}%',
          fontSize: 11,
          color: '#6b7280'
        },
        splitLine: {
          lineStyle: {
            color: '#f3f4f6',
            type: 'dashed'
          }
        }
      },
      series: seriesData
    }

    console.log('Setting chart option with data:', {
      dates: sortedDates.length,
      series: seriesData.length,
      firstSeriesData: seriesData[0]?.data
    })

    chartInstance.setOption(option, true) // true = 不合併，完全替換
    console.log('Fundamental chart rendered successfully')

    // 多次調整大小，確保正確顯示
    setTimeout(() => {
      if (chartInstance) {
        chartInstance.resize()
        console.log('Chart resized (100ms)')
      }
    }, 100)

    setTimeout(() => {
      if (chartInstance) {
        chartInstance.resize()
        console.log('Chart resized (300ms)')
      }
    }, 300)

    setTimeout(() => {
      if (chartInstance) {
        chartInstance.resize()
        console.log('Chart resized (500ms)')
      }
    }, 500)
  } catch (error) {
    console.error('Error rendering fundamental chart:', error)
    errorMessage.value = '圖表渲染失敗: ' + (error as Error).message
  }
}

// 獲取最新值
const getLatestValue = (dataPoints: any[]) => {
  if (!dataPoints || dataPoints.length === 0) return '-'
  const validPoints = dataPoints.filter(p => p.value !== null)
  if (validPoints.length === 0) return '-'
  const latest = validPoints[validPoints.length - 1]
  return typeof latest.value === 'number' ? latest.value.toFixed(2) + '%' : '-'
}

// 獲取最新日期
const getLatestDate = (dataPoints: any[]) => {
  if (!dataPoints || dataPoints.length === 0) return '-'
  const validPoints = dataPoints.filter(p => p.value !== null)
  if (validPoints.length === 0) return '-'
  return validPoints[validPoints.length - 1].date
}

// 清理
onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
})

// 暴露方法給父組件
defineExpose({
  loadIndicators,
  loadFundamentalData
})

// 自動載入指標列表
onMounted(() => {
  if (process.client) {
    loadIndicators()
  }
})

// TypeScript 聲明
declare global {
  interface Window {
    echarts: any
  }
}
</script>

<style scoped lang="scss">
.fundamental-analysis {
  margin-top: 2rem;
}

.indicator-selector {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;

  h3 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #111827;
  }
}

.btn-refresh {
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;

  &:hover:not(:disabled) {
    background: #e5e7eb;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.category-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.category-btn {
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  border: 2px solid transparent;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
  font-size: 0.875rem;

  &:hover {
    background: #e5e7eb;
  }

  &.active {
    background: #dbeafe;
    color: #1e40af;
    border-color: #3b82f6;
  }
}

.indicators-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.indicator-btn {
  padding: 0.75rem;
  background: #f9fafb;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;

  &:hover {
    border-color: #3b82f6;
    background: #eff6ff;
  }

  &.selected {
    background: #dbeafe;
    border-color: #3b82f6;
    color: #1e40af;
  }

  .indicator-name {
    display: block;
    font-weight: 600;
    margin-bottom: 0.25rem;
  }

  .indicator-name-en {
    display: block;
    font-size: 0.75rem;
    color: #6b7280;
  }
}

.selected-count {
  padding: 0.75rem;
  background: #eff6ff;
  border-left: 3px solid #3b82f6;
  border-radius: 0.25rem;
  color: #1e40af;
  font-size: 0.875rem;
  font-weight: 500;
}

.action-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.btn-load-fundamental {
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

.hint-text {
  color: #6b7280;
  font-size: 0.875rem;
}

.error-message {
  padding: 1rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  margin-bottom: 1rem;
}

.chart-display {
  background: white;
  padding: 2rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-top: 2rem;
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

.fundamental-chart-canvas {
  width: 100%;
  min-height: 500px;
  height: 500px;
  margin-bottom: 2rem;
  background: #fafafa;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
}

.latest-data-section {
  margin-top: 2rem;

  h3 {
    margin: 0 0 1rem 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: #111827;
  }
}

.data-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.data-card {
  padding: 1rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  text-align: center;

  .card-indicator {
    font-size: 0.875rem;
    font-weight: 600;
    color: #374151;
    margin-bottom: 0.5rem;
  }

  .card-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #059669;
    margin-bottom: 0.25rem;
  }

  .card-date {
    font-size: 0.75rem;
    color: #6b7280;
  }
}
</style>
