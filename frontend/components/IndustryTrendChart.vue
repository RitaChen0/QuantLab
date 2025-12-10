<template>
  <div class="trend-chart-container">
    <div class="chart-header">
      <h3 class="chart-title">{{ title }}</h3>
      <div class="chart-controls">
        <select v-model="selectedMetric" @change="loadData" class="metric-select">
          <option value="avg_ROE稅後">ROE稅後</option>
          <option value="avg_ROA稅後息前">ROA稅後息前</option>
          <option value="avg_營業毛利率">營業毛利率</option>
          <option value="avg_營業利益率">營業利益率</option>
          <option value="avg_每股稅後淨利">每股稅後淨利</option>
          <option value="avg_營收成長率">營收成長率</option>
        </select>
        <button @click="loadData" :disabled="loading" class="refresh-btn">
          {{ loading ? '載入中...' : '重新載入' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>載入歷史數據中...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button @click="loadData" class="retry-btn">重試</button>
    </div>

    <div v-else>
      <div ref="chartRef" class="echarts-container"></div>
      <div v-if="dataPoints.length === 0" class="empty-state">
        <p>暫無歷史數據</p>
        <p class="hint">請先計算產業指標以生成歷史記錄</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'

interface Props {
  industryCode: string
  industryName: string
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '產業指標歷史趨勢'
})

const config = useRuntimeConfig()
const chartRef = ref<HTMLElement | null>(null)
const selectedMetric = ref('avg_ROE稅後')
const loading = ref(false)
const error = ref('')
const dataPoints = ref<any[]>([])
let chartInstance: any = null

async function loadData() {
  if (!props.industryCode) return

  loading.value = true
  error.value = ''

  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(
      `${config.public.apiBase}/api/v1/industry/${props.industryCode}/metrics/historical?metric_name=${selectedMetric.value}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    if (response.ok) {
      const result = await response.json()
      dataPoints.value = result.data || []
      renderChart()
    } else {
      error.value = '載入數據失敗'
    }
  } catch (err) {
    console.error('Failed to load historical data:', err)
    error.value = '載入數據時發生錯誤'
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!chartRef.value || dataPoints.value.length === 0) return

  // Dynamically load ECharts
  if (typeof window !== 'undefined' && !(window as any).echarts) {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'
    script.onload = () => initChart()
    document.head.appendChild(script)
  } else {
    initChart()
  }
}

function initChart() {
  if (!chartRef.value) return

  const echarts = (window as any).echarts
  if (!echarts) return

  // Dispose previous instance
  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)

  // Prepare data
  const dates = dataPoints.value.map(d => d.date)
  const values = dataPoints.value.map(d => d.value)
  const stocksCounts = dataPoints.value.map(d => d.stocks_count)

  // Chart options
  const option = {
    title: {
      text: `${props.industryName} - ${selectedMetric.value.replace('avg_', '')}`,
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 600
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const point = params[0]
        const index = point.dataIndex
        return `
          <div style="padding: 8px;">
            <div style="font-weight: 600; margin-bottom: 4px;">${point.name}</div>
            <div style="color: #2563eb;">
              指標值: <strong>${point.value !== null ? point.value.toFixed(2) : 'N/A'}</strong>
            </div>
            <div style="color: #6b7280; font-size: 12px; margin-top: 4px;">
              樣本數: ${stocksCounts[index] || 'N/A'} 檔
            </div>
          </div>
        `
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45,
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      name: '指標值',
      axisLabel: {
        formatter: '{value}'
      }
    },
    series: [
      {
        name: selectedMetric.value.replace('avg_', ''),
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: {
          color: '#2563eb'
        },
        lineStyle: {
          width: 3,
          color: '#2563eb'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(37, 99, 235, 0.3)' },
              { offset: 1, color: 'rgba(37, 99, 235, 0.05)' }
            ]
          }
        }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      }
    ]
  }

  chartInstance.setOption(option)

  // Resize handler
  window.addEventListener('resize', handleResize)
}

function handleResize() {
  if (chartInstance) {
    chartInstance.resize()
  }
}

watch(() => props.industryCode, () => {
  if (props.industryCode) {
    loadData()
  }
})

onMounted(() => {
  if (props.industryCode) {
    loadData()
  }
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.trend-chart-container {
  background: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.chart-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
}

.chart-controls {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.metric-select {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  background: white;
  font-size: 0.875rem;
  cursor: pointer;

  &:focus {
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  }
}

.refresh-btn {
  padding: 0.5rem 1rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;

  &:hover:not(:disabled) {
    background: #1d4ed8;
  }

  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }
}

.echarts-container {
  width: 100%;
  height: 400px;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #6b7280;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  color: #dc2626;
  margin-bottom: 1rem;
}

.retry-btn {
  padding: 0.5rem 1.5rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;

  &:hover {
    background: #1d4ed8;
  }
}

.hint {
  font-size: 0.875rem;
  color: #9ca3af;
  margin-top: 0.5rem;
}
</style>
