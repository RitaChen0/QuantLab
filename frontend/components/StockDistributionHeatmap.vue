<template>
  <div class="heatmap-container">
    <div class="chart-header">
      <h3 class="chart-title">{{ title }}</h3>
      <div class="chart-controls">
        <select v-model="viewMode" @change="renderChart" class="mode-select">
          <option value="count">股票數量</option>
          <option value="level">產業層級</option>
        </select>
        <button @click="loadData" :disabled="loading" class="refresh-btn">
          {{ loading ? '載入中...' : '重新載入' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>載入產業分佈數據中...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button @click="loadData" class="retry-btn">重試</button>
    </div>

    <div v-else>
      <div ref="chartRef" class="echarts-container"></div>
      <div class="legend-container">
        <div class="legend-item">
          <div class="legend-color" style="background: linear-gradient(to right, #eff6ff, #2563eb);"></div>
          <span class="legend-label">股票數量：少 → 多</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface Props {
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '產業股票分佈熱力圖'
})

const config = useRuntimeConfig()
const chartRef = ref<HTMLElement | null>(null)
const viewMode = ref('count')
const loading = ref(false)
const error = ref('')
const industries = ref<any[]>([])
let chartInstance: any = null

async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(
      `${config.public.apiBase}/api/v1/industry/`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    if (response.ok) {
      const data = await response.json()
      industries.value = data.industries || []
      renderChart()
    } else {
      error.value = '載入數據失敗'
    }
  } catch (err) {
    console.error('Failed to load industries:', err)
    error.value = '載入數據時發生錯誤'
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!chartRef.value || industries.value.length === 0) return

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

  // Group industries by level
  const level1 = industries.value.filter(i => i.level === 1)
  const level2 = industries.value.filter(i => i.level === 2)
  const level3 = industries.value.filter(i => i.level === 3)

  // Prepare treemap data
  const data = level1.map(l1 => {
    const children = level2
      .filter(l2 => l2.parent_code === l1.code)
      .map(l2 => {
        const grandchildren = level3
          .filter(l3 => l3.parent_code === l2.code)
          .map(l3 => ({
            name: l3.name_zh,
            value: viewMode.value === 'count' ? l3.stock_count : 1,
            code: l3.code,
            level: 3,
            stock_count: l3.stock_count,
            itemStyle: {
              borderColor: '#fff',
              borderWidth: 2,
              gapWidth: 2
            }
          }))

        return {
          name: l2.name_zh,
          value: viewMode.value === 'count' ? l2.stock_count : grandchildren.length || 1,
          code: l2.code,
          level: 2,
          stock_count: l2.stock_count,
          children: grandchildren.length > 0 ? grandchildren : undefined,
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 3,
            gapWidth: 3
          }
        }
      })

    return {
      name: l1.name_zh,
      value: viewMode.value === 'count' ? l1.stock_count : children.length || 1,
      code: l1.code,
      level: 1,
      stock_count: l1.stock_count,
      children: children.length > 0 ? children : undefined,
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 4,
        gapWidth: 4
      }
    }
  })

  // Chart options
  const option = {
    title: {
      text: '產業分類股票分佈',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 600
      }
    },
    tooltip: {
      formatter: (params: any) => {
        const data = params.data
        return `
          <div style="padding: 8px;">
            <div style="font-weight: 600; margin-bottom: 4px;">${data.name}</div>
            <div style="color: #6b7280; font-size: 12px;">
              代碼: ${data.code || 'N/A'}
            </div>
            <div style="color: #2563eb; margin-top: 4px;">
              股票數量: <strong>${data.stock_count || 0}</strong> 檔
            </div>
            <div style="color: #6b7280; font-size: 12px; margin-top: 2px;">
              層級: Level ${data.level}
            </div>
          </div>
        `
      }
    },
    series: [
      {
        type: 'treemap',
        data: data,
        width: '100%',
        height: '100%',
        top: 60,
        bottom: 20,
        roam: false,
        nodeClick: 'zoomToNode',
        breadcrumb: {
          show: true,
          height: 30,
          bottom: 0,
          itemStyle: {
            color: '#f3f4f6',
            borderColor: '#d1d5db',
            borderWidth: 1,
            textStyle: {
              color: '#374151'
            }
          }
        },
        label: {
          show: true,
          formatter: (params: any) => {
            const data = params.data
            if (data.stock_count > 0) {
              return `{name|${data.name}}\n{count|${data.stock_count} 檔}`
            }
            return `{name|${data.name}}`
          },
          rich: {
            name: {
              fontSize: 14,
              fontWeight: 600,
              color: '#111827',
              lineHeight: 20
            },
            count: {
              fontSize: 12,
              color: '#6b7280',
              lineHeight: 18
            }
          }
        },
        upperLabel: {
          show: true,
          height: 30,
          color: '#111827',
          fontSize: 13,
          fontWeight: 600
        },
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 2,
          gapWidth: 2
        },
        levels: [
          {
            itemStyle: {
              borderWidth: 0,
              gapWidth: 5
            }
          },
          {
            itemStyle: {
              borderWidth: 3,
              gapWidth: 3,
              borderColorSaturation: 0.6
            }
          },
          {
            itemStyle: {
              borderWidth: 2,
              gapWidth: 2,
              borderColorSaturation: 0.5
            },
            colorSaturation: [0.3, 0.6]
          },
          {
            itemStyle: {
              borderWidth: 1,
              gapWidth: 1,
              borderColorSaturation: 0.4
            },
            colorSaturation: [0.3, 0.5]
          }
        ],
        visualMin: 0,
        visualMax: Math.max(...data.map(d => d.stock_count || 0)),
        colorAlpha: [0.5, 1],
        color: [
          '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd',
          '#10b981', '#34d399', '#6ee7b7',
          '#f59e0b', '#fbbf24', '#fcd34d',
          '#ef4444', '#f87171', '#fca5a5',
          '#8b5cf6', '#a78bfa', '#c4b5fd'
        ]
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

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.heatmap-container {
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

.mode-select {
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
  height: 600px;
}

.legend-container {
  display: flex;
  justify-content: center;
  margin-top: 1rem;
  gap: 2rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.legend-color {
  width: 100px;
  height: 20px;
  border-radius: 0.25rem;
  border: 1px solid #d1d5db;
}

.legend-label {
  font-size: 0.875rem;
  color: #6b7280;
}

.loading-state,
.error-state {
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
</style>
