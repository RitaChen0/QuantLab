<template>
  <div class="radar-chart-container">
    <div class="chart-header">
      <h3 class="chart-title">{{ title }}</h3>
      <div class="chart-controls">
        <button @click="showIndustrySelector = !showIndustrySelector" class="select-btn">
          選擇產業 ({{ selectedIndustries.length }}/{{ maxIndustries }})
        </button>
        <button @click="loadData" :disabled="loading || selectedIndustries.length === 0" class="refresh-btn">
          {{ loading ? '計算中...' : '更新對比' }}
        </button>
      </div>
    </div>

    <!-- Industry Selector Modal -->
    <div v-if="showIndustrySelector" class="modal-overlay" @click="showIndustrySelector = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h4>選擇要對比的產業</h4>
          <button @click="showIndustrySelector = false" class="close-btn">✕</button>
        </div>
        <div class="modal-body">
          <div class="industry-grid">
            <label
              v-for="industry in availableIndustries"
              :key="industry.code"
              class="industry-checkbox"
            >
              <input
                type="checkbox"
                :value="industry.code"
                v-model="selectedIndustries"
                :disabled="!selectedIndustries.includes(industry.code) && selectedIndustries.length >= maxIndustries"
              />
              <span class="industry-label">
                {{ industry.name_zh }}
                <span class="industry-code">({{ industry.code }})</span>
              </span>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showIndustrySelector = false" class="btn-secondary">完成</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>計算產業指標中...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button @click="loadData" class="retry-btn">重試</button>
    </div>

    <div v-else-if="selectedIndustries.length === 0" class="empty-state">
      <p>請選擇要對比的產業</p>
      <button @click="showIndustrySelector = true" class="select-btn">選擇產業</button>
    </div>

    <div v-else-if="industryMetrics.length === 0" class="empty-state">
      <p>點擊「更新對比」按鈕以載入數據</p>
    </div>

    <div v-else>
      <div ref="chartRef" class="echarts-container"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted, nextTick } from 'vue'

interface Props {
  availableIndustries: any[]
  title?: string
  maxIndustries?: number
}

const props = withDefaults(defineProps<Props>(), {
  title: '產業指標對比雷達圖',
  maxIndustries: 5
})

const config = useRuntimeConfig()
const chartRef = ref<HTMLElement | null>(null)
const selectedIndustries = ref<string[]>([])
const showIndustrySelector = ref(false)
const loading = ref(false)
const error = ref('')
const industryMetrics = ref<any[]>([])
let chartInstance: any = null

async function loadData() {
  if (selectedIndustries.value.length === 0) {
    error.value = '請至少選擇一個產業'
    return
  }

  loading.value = true
  error.value = ''
  industryMetrics.value = []

  try {
    const token = localStorage.getItem('access_token')

    if (!token) {
      error.value = '請先登入'
      return
    }

    console.log('[IndustryComparisonRadar] Loading data for industries:', selectedIndustries.value)

    // Load metrics for all selected industries
    const promises = selectedIndustries.value.map(code =>
      fetch(
        `${config.public.apiBase}/api/v1/industry/${code}/metrics`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      ).then(async res => {
        if (!res.ok) {
          const errorText = await res.text()
          console.error(`[IndustryComparisonRadar] API error for ${code}:`, res.status, errorText)
          throw new Error(`API error: ${res.status}`)
        }
        return res.json()
      })
    )

    const results = await Promise.all(promises)
    console.log('[IndustryComparisonRadar] Loaded metrics:', results)

    industryMetrics.value = results

    // Check if we have valid data
    if (results.length === 0) {
      error.value = '無法載入產業指標數據'
      loading.value = false
      return
    }

    // Set loading to false BEFORE nextTick so DOM can update
    loading.value = false
    console.log('[IndustryComparisonRadar] Loading complete, waiting for DOM update...')

    // Wait for DOM to update (chart container to be rendered)
    await nextTick()
    console.log('[IndustryComparisonRadar] DOM updated, rendering chart...')

    renderChart()
  } catch (err) {
    console.error('[IndustryComparisonRadar] Failed to load industry metrics:', err)
    error.value = `載入數據時發生錯誤: ${err instanceof Error ? err.message : String(err)}`
    loading.value = false
  }
}

function renderChart() {
  if (!chartRef.value) {
    console.error('[IndustryComparisonRadar] Chart container not found')
    error.value = '圖表容器未找到'
    return
  }

  if (industryMetrics.value.length === 0) {
    console.error('[IndustryComparisonRadar] No metrics data')
    error.value = '沒有可用的指標數據'
    return
  }

  console.log('[IndustryComparisonRadar] Rendering chart with', industryMetrics.value.length, 'industries')

  // Dynamically load ECharts
  if (typeof window !== 'undefined' && !(window as any).echarts) {
    console.log('[IndustryComparisonRadar] Loading ECharts from CDN...')
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'
    script.onload = () => {
      console.log('[IndustryComparisonRadar] ECharts loaded successfully')
      initChart()
    }
    script.onerror = () => {
      console.error('[IndustryComparisonRadar] Failed to load ECharts from CDN')
      error.value = 'ECharts 載入失敗，請檢查網路連線'
    }
    document.head.appendChild(script)
  } else {
    console.log('[IndustryComparisonRadar] ECharts already loaded')
    initChart()
  }
}

function initChart() {
  if (!chartRef.value) {
    console.error('[IndustryComparisonRadar] Chart ref not available in initChart')
    return
  }

  const echarts = (window as any).echarts
  if (!echarts) {
    console.error('[IndustryComparisonRadar] ECharts not available')
    error.value = 'ECharts 未載入'
    return
  }

  console.log('[IndustryComparisonRadar] Initializing chart...')

  // Dispose previous instance
  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)
  console.log('[IndustryComparisonRadar] Chart instance created')

  // Define indicators (radar axes)
  const indicators = [
    { name: 'ROE稅後', max: 30 },
    { name: 'ROA稅後息前', max: 20 },
    { name: '營業毛利率', max: 60 },
    { name: '營業利益率', max: 40 },
    { name: '每股稅後淨利', max: 10 },
    { name: '營收成長率', max: 50 }
  ]

  // Prepare series data
  const series = industryMetrics.value.map((data, index) => {
    const industry = props.availableIndustries.find(i => i.code === data.industry_code)
    const metrics = data.metrics || {}

    return {
      name: industry?.name_zh || data.industry_code,
      value: [
        metrics['ROE稅後']?.average || 0,
        metrics['ROA稅後息前']?.average || 0,
        metrics['營業毛利率']?.average || 0,
        metrics['營業利益率']?.average || 0,
        metrics['每股稅後淨利']?.average || 0,
        metrics['營收成長率']?.average || 0
      ]
    }
  })

  // Chart options
  const option = {
    title: {
      text: '產業財務指標對比',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 600
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const values = params.value
        return `
          <div style="padding: 8px;">
            <div style="font-weight: 600; margin-bottom: 8px;">${params.name}</div>
            <div style="display: grid; gap: 4px;">
              ${indicators.map((ind, i) => `
                <div style="display: flex; justify-content: space-between; gap: 16px;">
                  <span style="color: #6b7280;">${ind.name}:</span>
                  <span style="color: #2563eb; font-weight: 600;">${values[i].toFixed(2)}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `
      }
    },
    legend: {
      bottom: 10,
      data: series.map(s => s.name)
    },
    radar: {
      indicator: indicators,
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: '#374151',
        fontSize: 12,
        fontWeight: 500
      },
      splitLine: {
        lineStyle: {
          color: '#e5e7eb'
        }
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(37, 99, 235, 0.05)', 'rgba(37, 99, 235, 0.02)']
        }
      }
    },
    series: [
      {
        type: 'radar',
        data: series,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          width: 2
        },
        areaStyle: {
          opacity: 0.2
        }
      }
    ],
    color: ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
  }

  chartInstance.setOption(option)
  console.log('[IndustryComparisonRadar] Chart rendered successfully with', series.length, 'series')

  // Trigger resize after a short delay
  setTimeout(() => {
    if (chartInstance) {
      chartInstance.resize()
      console.log('[IndustryComparisonRadar] Chart resized')
    }
  }, 100)

  // Resize handler
  window.addEventListener('resize', handleResize)
}

function handleResize() {
  if (chartInstance) {
    chartInstance.resize()
  }
}

onMounted(() => {
  console.log('[IndustryComparisonRadar] Component mounted')
  console.log('[IndustryComparisonRadar] Available industries:', props.availableIndustries.length)

  // Auto-select first few industries if available
  if (props.availableIndustries.length > 0) {
    selectedIndustries.value = props.availableIndustries
      .slice(0, Math.min(3, props.maxIndustries))
      .map(i => i.code)
    console.log('[IndustryComparisonRadar] Auto-selected industries:', selectedIndustries.value)

    // Add a small delay to ensure DOM is ready
    setTimeout(() => {
      loadData()
    }, 100)
  } else {
    console.warn('[IndustryComparisonRadar] No available industries to display')
    error.value = '沒有可用的產業資料'
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
.radar-chart-container {
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
}

.select-btn {
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #e5e7eb;
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
  height: 500px;
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

/* Modal Styles */
.modal-overlay {
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
}

.modal-content {
  background: white;
  border-radius: 0.5rem;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;

  h4 {
    font-size: 1.125rem;
    font-weight: 600;
    color: #111827;
  }
}

.close-btn {
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 1.5rem;
  color: #6b7280;

  &:hover {
    background: #f3f4f6;
  }
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.industry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}

.industry-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #f9fafb;
    border-color: #2563eb;
  }

  input[type="checkbox"] {
    width: 1rem;
    height: 1rem;
    cursor: pointer;

    &:disabled {
      cursor: not-allowed;
      opacity: 0.5;
    }
  }
}

.industry-label {
  font-size: 0.875rem;
  color: #374151;
}

.industry-code {
  color: #6b7280;
  font-size: 0.75rem;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
}

.btn-secondary {
  padding: 0.5rem 1.5rem;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-weight: 500;
  cursor: pointer;

  &:hover {
    background: #e5e7eb;
  }
}
</style>
