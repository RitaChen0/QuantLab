<template>
  <div class="model-predict-page">
    <AppHeader />

    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <h1>📊 模型预测</h1>
        <p v-if="model">模型：{{ model.name }}</p>
        <p v-if="latestJob" class="model-ic">测试 IC: {{ latestJob.test_ic?.toFixed(4) || 'N/A' }}</p>
      </div>
      <div class="header-actions">
        <button
          @click="showExportDialog"
          class="btn-primary"
          :disabled="!latestJob || latestJob.status !== 'COMPLETED'"
          :title="latestJob?.status !== 'COMPLETED' ? '请先完成模型训练' : '导出为 Qlib 策略'"
        >
          📦 导出为策略
        </button>
        <NuxtLink :to="`/rdagent/models/${modelId}/train`" class="btn-secondary">
          🎯 训练设置
        </NuxtLink>
        <NuxtLink to="/rdagent" class="btn-secondary">
          ← 返回
        </NuxtLink>
      </div>
    </div>

    <!-- 载入中 -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p>载入模型信息...</p>
    </div>

    <!-- 错误讯息 -->
    <div v-else-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- 主要内容 -->
    <div v-else class="predict-container">
      <!-- 左侧：预测配置 -->
      <div class="config-panel">
        <h2>⚙️ 预测配置</h2>

        <!-- 股票选择 -->
        <div class="config-section">
          <label>选择股票</label>
          <div class="stock-selection">
            <div class="preset-groups">
              <button
                @click="selectPreset('popular')"
                class="preset-btn"
                :class="{ active: isPresetActive('popular') }"
              >
                热门股票
              </button>
              <button
                @click="selectPreset('futures')"
                class="preset-btn"
                :class="{ active: isPresetActive('futures') }"
              >
                期货
              </button>
              <button
                @click="selectPreset('tech')"
                class="preset-btn"
                :class="{ active: isPresetActive('tech') }"
              >
                科技股
              </button>
            </div>

            <div class="manual-input">
              <input
                v-model="customSymbol"
                type="text"
                placeholder="手动输入股票代码（如：2330）"
                @keyup.enter="addCustomSymbol"
              />
              <button @click="addCustomSymbol" class="btn-small">添加</button>
            </div>

            <div class="selected-stocks">
              <div
                v-for="symbol in selectedSymbols"
                :key="symbol"
                class="stock-chip"
              >
                {{ symbol }}
                <button @click="removeSymbol(symbol)" class="remove-btn">×</button>
              </div>
            </div>

            <div class="selection-count">
              已选择 {{ selectedSymbols.length }} 支股票
            </div>
          </div>
        </div>

        <!-- 日期范围 -->
        <div class="config-section">
          <label>预测日期范围</label>
          <div class="date-inputs">
            <input v-model="startDate" type="date" />
            <span>至</span>
            <input v-model="endDate" type="date" />
          </div>
          <div class="date-presets">
            <button @click="setDateRange(7)" class="preset-date-btn">最近 7 天</button>
            <button @click="setDateRange(30)" class="preset-date-btn">最近 30 天</button>
            <button @click="setDateRange(90)" class="preset-date-btn">最近 90 天</button>
          </div>
        </div>

        <!-- 信号阈值 -->
        <div class="config-section">
          <label>交易信号阈值</label>
          <div class="threshold-inputs">
            <div class="threshold-item">
              <span>买入阈值</span>
              <input
                v-model.number="buyThreshold"
                type="number"
                step="0.01"
                min="0"
                max="1"
              />
              <span class="threshold-hint">预测值 &gt; {{ buyThreshold }}</span>
            </div>
            <div class="threshold-item">
              <span>卖出阈值</span>
              <input
                v-model.number="sellThreshold"
                type="number"
                step="0.01"
                min="-1"
                max="0"
              />
              <span class="threshold-hint">预测值 &lt; {{ sellThreshold }}</span>
            </div>
          </div>
        </div>

        <!-- 生成预测按钮 -->
        <button
          @click="generatePredictions"
          class="btn-primary btn-large"
          :disabled="predicting || selectedSymbols.length === 0"
        >
          <span v-if="predicting">
            <div class="spinner-small"></div>
            生成预测中...
          </span>
          <span v-else>
            🚀 生成预测
          </span>
        </button>
      </div>

      <!-- 右侧：预测结果 -->
      <div class="results-panel">
        <h2>📈 预测结果</h2>

        <!-- 未生成预测时的提示 -->
        <div v-if="!predictions && !predicting" class="empty-state">
          <div class="empty-icon">📊</div>
          <p>请配置参数后点击「生成预测」</p>
        </div>

        <!-- 预测结果 -->
        <div v-else-if="predictions" class="predictions-display">
          <!-- 汇总统计 -->
          <div class="summary-cards">
            <div class="summary-card">
              <div class="card-label">总预测天数</div>
              <div class="card-value">{{ totalDays }}</div>
            </div>
            <div class="summary-card buy">
              <div class="card-label">买入信号</div>
              <div class="card-value">{{ totalBuySignals }}</div>
              <div class="card-percent">{{ buySignalPercent }}%</div>
            </div>
            <div class="summary-card sell">
              <div class="card-label">卖出信号</div>
              <div class="card-value">{{ totalSellSignals }}</div>
              <div class="card-percent">{{ sellSignalPercent }}%</div>
            </div>
            <div class="summary-card">
              <div class="card-label">平均预测值</div>
              <div class="card-value">{{ avgPrediction }}</div>
            </div>
          </div>

          <!-- 全局热力图 -->
          <div v-if="predictions.length > 1" class="global-heatmap-section">
            <h3>📊 预测热力图</h3>
            <div class="global-heatmap"></div>
          </div>

          <!-- 各股票预测 -->
          <div
            v-for="stock in predictions"
            :key="stock.symbol"
            class="stock-predictions"
          >
            <div class="stock-header" @click="toggleStockExpand(stock.symbol)">
              <h3>{{ stock.symbol }}</h3>
              <div class="stock-stats">
                <span class="stat-item buy">买入: {{ stock.stats.buy_signals }}</span>
                <span class="stat-item sell">卖出: {{ stock.stats.sell_signals }}</span>
                <span class="stat-item">平均: {{ stock.stats.mean_prediction.toFixed(4) }}</span>
              </div>
              <button class="expand-btn">
                {{ expandedStocks.includes(stock.symbol) ? '▼' : '▶' }}
              </button>
            </div>

            <!-- 展开的详细信息 -->
            <div v-if="expandedStocks.includes(stock.symbol)" class="stock-details">
              <!-- 图表选项卡 -->
              <div class="chart-tabs">
                <button
                  v-for="chartType in chartTypes"
                  :key="chartType.id"
                  :class="['chart-tab', { active: selectedChartType[stock.symbol] === chartType.id }]"
                  @click="selectChartType(stock.symbol, chartType.id)"
                >
                  {{ chartType.icon }} {{ chartType.name }}
                </button>
              </div>

              <!-- 图表容器 -->
              <div class="chart-container">
                <!-- 折线图 -->
                <div
                  v-show="selectedChartType[stock.symbol] === 'line'"
                  :class="`chart-line-${stock.symbol} echart`"
                ></div>

                <!-- K线图 -->
                <div
                  v-show="selectedChartType[stock.symbol] === 'candlestick'"
                  :class="`chart-candlestick-${stock.symbol} echart`"
                ></div>

                <!-- 散点图 -->
                <div
                  v-show="selectedChartType[stock.symbol] === 'scatter'"
                  :class="`chart-scatter-${stock.symbol} echart`"
                ></div>

                <!-- 信号分布饼图 -->
                <div
                  v-show="selectedChartType[stock.symbol] === 'pie'"
                  :class="`chart-pie-${stock.symbol} echart`"
                ></div>
              </div>

              <!-- 预测表格 -->
              <div class="prediction-table-container">
                <table class="prediction-table">
                  <thead>
                    <tr>
                      <th>日期</th>
                      <th>预测值</th>
                      <th>信号</th>
                      <th>操作建议</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(pred, date) in getRecentPredictions(stock, 10)"
                      :key="date"
                      :class="getSignalClass(stock.signals[date])"
                    >
                      <td>{{ date }}</td>
                      <td :class="getPredictionClass(pred)">
                        {{ pred > 0 ? '+' : '' }}{{ pred.toFixed(4) }}
                      </td>
                      <td>
                        <span class="signal-badge" :class="getSignalBadgeClass(stock.signals[date])">
                          {{ getSignalText(stock.signals[date]) }}
                        </span>
                      </td>
                      <td>{{ getActionText(stock.signals[date]) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- 导出按钮 -->
              <div class="export-actions">
                <button @click="exportStockData(stock)" class="btn-secondary">
                  📥 导出 CSV
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 导出为策略对话框 -->
    <div v-if="exportDialogVisible" class="modal-overlay" @click.self="closeExportDialog">
      <div class="modal-dialog">
        <div class="modal-header">
          <h3>📦 导出为 Qlib 策略</h3>
          <button @click="closeExportDialog" class="close-btn">×</button>
        </div>

        <div class="modal-body">
          <p class="modal-description">
            将训练好的模型导出为 Qlib 策略，可以在回测中心使用。
          </p>

          <div class="form-group">
            <label>策略名称 <span class="required">*</span></label>
            <input
              v-model="strategyName"
              type="text"
              placeholder="例如：AI MLP 预测策略 v1"
              class="form-input"
              @keyup.enter="exportToStrategy"
            />
          </div>

          <div class="form-group">
            <label>买入阈值</label>
            <input
              v-model.number="exportBuyThreshold"
              type="number"
              step="0.01"
              class="form-input"
            />
            <p class="form-hint">预测收益率 &gt; {{ exportBuyThreshold }} 时买入</p>
          </div>

          <div class="form-group">
            <label>卖出阈值</label>
            <input
              v-model.number="exportSellThreshold"
              type="number"
              step="0.01"
              class="form-input"
            />
            <p class="form-hint">预测收益率 &lt; {{ exportSellThreshold }} 时卖出</p>
          </div>

          <div class="form-group">
            <label>策略描述（可选）</label>
            <textarea
              v-model="strategyDescription"
              placeholder="描述策略的特点和使用场景..."
              class="form-textarea"
              rows="3"
            ></textarea>
          </div>

          <div class="model-info-box">
            <h4>📊 模型信息</h4>
            <p><strong>模型名称：</strong>{{ model?.name }}</p>
            <p><strong>测试 IC：</strong>{{ latestJob?.test_ic?.toFixed(4) || 'N/A' }}</p>
            <p><strong>特征数量：</strong>179 个因子（Alpha158+）</p>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeExportDialog" class="btn-secondary">
            取消
          </button>
          <button
            @click="exportToStrategy"
            class="btn-primary"
            :disabled="exporting || !strategyName"
          >
            <span v-if="exporting">
              <div class="spinner-small"></div>
              导出中...
            </span>
            <span v-else>
              确认导出
            </span>
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'

const route = useRoute()
const router = useRouter()
const modelId = ref(route.params.id)
const { getToken } = useAuth()

// 数据状态
const loading = ref(true)
const error = ref(null)
const model = ref(null)
const latestJob = ref(null)

// 配置状态
const selectedSymbols = ref(['2330', 'TXCONT'])
const customSymbol = ref('')
const startDate = ref('')
const endDate = ref('')
const buyThreshold = ref(0.02)
const sellThreshold = ref(-0.02)

// 预测状态
const predicting = ref(false)
const predictions = ref(null)
const expandedStocks = ref([])

// 图表状态
const selectedChartType = ref({})
const chartInstances = ref({})

// 导出状态
const exportDialogVisible = ref(false)
const exporting = ref(false)
const strategyName = ref('')
const exportBuyThreshold = ref(0.02)
const exportSellThreshold = ref(-0.02)
const strategyDescription = ref('')

// 图表类型定义
const chartTypes = [
  { id: 'line', name: '折线图', icon: '📈' },
  { id: 'candlestick', name: 'K线图', icon: '📊' },
  { id: 'scatter', name: '散点图', icon: '🔵' },
  { id: 'pie', name: '信号分布', icon: '🥧' }
]

// 预设股票组
const presets = {
  popular: ['2330', '2317', '2454', '2308', '2412'],
  futures: ['TXCONT', 'MTXCONT'],
  tech: ['2330', '2454', '3008', '2382', '6505']
}

// 初始化日期（默认最近 30 天）
const initDates = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 30)

  endDate.value = end.toISOString().split('T')[0]
  startDate.value = start.toISOString().split('T')[0]
}

// 加载模型信息
const loadModelInfo = async () => {
  try {
    loading.value = true
    const token = getToken()

    if (!token) {
      error.value = '请先登录'
      return
    }

    const headers = {
      'Authorization': `Bearer ${token}`
    }

    // 加载模型基本信息
    const modelRes = await $fetch(`/api/v1/rdagent/models/${modelId.value}`, { headers })
    model.value = modelRes

    // 加载最新训练任务
    const jobsRes = await $fetch(`/api/v1/rdagent/models/${modelId.value}/training-jobs?limit=1`, { headers })
    if (jobsRes.jobs && jobsRes.jobs.length > 0) {
      latestJob.value = jobsRes.jobs[0]

      // 检查训练状态
      if (latestJob.value.status !== 'COMPLETED') {
        error.value = `模型尚未训练完成。当前状态: ${latestJob.value.status}`
      }
    } else {
      error.value = '模型尚未训练，请先进行训练'
    }
  } catch (e) {
    error.value = `加载失败: ${e.message}`
  } finally {
    loading.value = false
  }
}

// 选择预设组
const selectPreset = (preset) => {
  selectedSymbols.value = [...presets[preset]]
}

const isPresetActive = (preset) => {
  const presetSymbols = presets[preset]
  return presetSymbols.every(s => selectedSymbols.value.includes(s)) &&
         selectedSymbols.value.length === presetSymbols.length
}

// 添加自定义股票
const addCustomSymbol = () => {
  const symbol = customSymbol.value.trim().toUpperCase()
  if (symbol && !selectedSymbols.value.includes(symbol)) {
    selectedSymbols.value.push(symbol)
    customSymbol.value = ''
  }
}

// 移除股票
const removeSymbol = (symbol) => {
  selectedSymbols.value = selectedSymbols.value.filter(s => s !== symbol)
}

// 设置日期范围
const setDateRange = (days) => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - days)

  endDate.value = end.toISOString().split('T')[0]
  startDate.value = start.toISOString().split('T')[0]
}

// 生成预测
const generatePredictions = async () => {
  try {
    predicting.value = true
    error.value = null
    const token = getToken()

    if (!token) {
      error.value = '请先登录'
      return
    }

    const response = await $fetch(`/api/v1/rdagent/models/${modelId.value}/predict`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: {
        symbols: selectedSymbols.value,
        start_date: startDate.value,
        end_date: endDate.value,
        buy_threshold: buyThreshold.value,
        sell_threshold: sellThreshold.value
      }
    })

    predictions.value = response.predictions

    // 默认展开第一支股票并初始化图表类型
    if (predictions.value.length > 0) {
      const firstSymbol = predictions.value[0].symbol
      expandedStocks.value = [firstSymbol]
      selectedChartType.value[firstSymbol] = 'line'

      // 等待 DOM 更新后绘制图表
      await nextTick()
      drawChart(firstSymbol, 'line')

      // 绘制全局热力图
      if (predictions.value.length > 1) {
        drawGlobalHeatmap()
      }
    }
  } catch (e) {
    error.value = `预测失败: ${e.message}`
  } finally {
    predicting.value = false
  }
}

// 切换股票展开/收起
const toggleStockExpand = async (symbol) => {
  const index = expandedStocks.value.indexOf(symbol)
  if (index > -1) {
    expandedStocks.value.splice(index, 1)
  } else {
    expandedStocks.value.push(symbol)

    // 初始化默认图表类型
    if (!selectedChartType.value[symbol]) {
      selectedChartType.value[symbol] = 'line'
    }

    // 等待 DOM 更新后绘制图表
    await nextTick()
    drawChart(symbol, selectedChartType.value[symbol])
  }
}

// 选择图表类型
const selectChartType = (symbol, chartType) => {
  selectedChartType.value[symbol] = chartType
  nextTick(() => {
    drawChart(symbol, chartType)
  })
}

// 绘制所有图表
const drawCharts = () => {
  predictions.value.forEach(stock => {
    if (expandedStocks.value.includes(stock.symbol)) {
      const chartType = selectedChartType.value[stock.symbol] || 'line'
      drawChart(stock.symbol, chartType)
    }
  })
}

// 绘制单个股票图表
const drawChart = (symbol, chartType) => {
  const stock = predictions.value.find(s => s.symbol === symbol)
  if (!stock) return

  // 使用 class 选择器而不是 ref
  const containerClass = `chart-${chartType}-${symbol}`
  const container = document.querySelector(`.${containerClass}`)
  if (!container) {
    console.warn(`Container not found: ${containerClass}`)
    return
  }

  // 销毁旧图表实例
  const chartKey = `${symbol}-${chartType}`
  if (chartInstances.value[chartKey]) {
    chartInstances.value[chartKey].dispose()
  }

  // 创建新图表
  const chartInstance = echarts.init(container)
  chartInstances.value[chartKey] = chartInstance

  // 根据图表类型绘制
  switch (chartType) {
    case 'line':
      drawLineChart(chartInstance, stock)
      break
    case 'candlestick':
      drawCandlestickChart(chartInstance, stock)
      break
    case 'scatter':
      drawScatterChart(chartInstance, stock)
      break
    case 'pie':
      drawPieChart(chartInstance, stock)
      break
  }

  // 响应式调整
  window.addEventListener('resize', () => {
    chartInstance.resize()
  })
}

// 折线图
const drawLineChart = (chart, stock) => {
  const dates = Object.keys(stock.predictions).sort()
  const predValues = dates.map(date => stock.predictions[date])
  const signals = dates.map(date => stock.signals[date])

  // 标记买入/卖出点
  const buyPoints = []
  const sellPoints = []
  dates.forEach((date, idx) => {
    if (signals[idx] === 1) buyPoints.push([date, predValues[idx]])
    if (signals[idx] === -1) sellPoints.push([date, predValues[idx]])
  })

  const option = {
    title: {
      text: `${stock.symbol} 预测值走势`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const date = params[0].axisValue
        const pred = params[0].value
        const signal = stock.signals[date]
        return `${date}<br/>预测值: ${pred > 0 ? '+' : ''}${pred.toFixed(4)}<br/>信号: ${getSignalText(signal)}`
      }
    },
    legend: {
      data: ['预测值', '买入阈值', '卖出阈值', '买入信号', '卖出信号'],
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
      data: dates,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (value) => value > 0 ? `+${value.toFixed(3)}` : value.toFixed(3)
      }
    },
    series: [
      {
        name: '预测值',
        type: 'line',
        data: predValues,
        smooth: true,
        itemStyle: {
          color: '#2196F3'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(33, 150, 243, 0.3)' },
            { offset: 1, color: 'rgba(33, 150, 243, 0.1)' }
          ])
        }
      },
      {
        name: '买入阈值',
        type: 'line',
        data: Array(dates.length).fill(buyThreshold.value),
        lineStyle: {
          type: 'dashed',
          color: '#4CAF50'
        },
        itemStyle: {
          opacity: 0
        }
      },
      {
        name: '卖出阈值',
        type: 'line',
        data: Array(dates.length).fill(sellThreshold.value),
        lineStyle: {
          type: 'dashed',
          color: '#F44336'
        },
        itemStyle: {
          opacity: 0
        }
      },
      {
        name: '买入信号',
        type: 'scatter',
        data: buyPoints,
        symbolSize: 15,
        itemStyle: {
          color: '#4CAF50'
        },
        z: 10
      },
      {
        name: '卖出信号',
        type: 'scatter',
        data: sellPoints,
        symbolSize: 15,
        itemStyle: {
          color: '#F44336'
        },
        z: 10
      }
    ]
  }

  chart.setOption(option)
}

// K线图（模拟）
const drawCandlestickChart = (chart, stock) => {
  const dates = Object.keys(stock.predictions).sort()
  const candleData = dates.map(date => {
    const pred = stock.predictions[date]
    const absValue = Math.abs(pred)
    // 模拟 OHLC 数据
    const open = 0
    const close = pred
    const high = pred > 0 ? pred + absValue * 0.2 : absValue * 0.2
    const low = pred < 0 ? pred - absValue * 0.2 : -absValue * 0.2
    return [open, close, low, high]
  })

  const option = {
    title: {
      text: `${stock.symbol} 预测值 K 线图`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params) => {
        const data = params[0].data
        const date = params[0].axisValue
        return `${date}<br/>
                开: ${data[1].toFixed(4)}<br/>
                收: ${data[2].toFixed(4)}<br/>
                低: ${data[3].toFixed(4)}<br/>
                高: ${data[4].toFixed(4)}`
      }
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: dates,
      scale: true,
      boundaryGap: false,
      axisLine: { onZero: false },
      splitLine: { show: false },
      splitNumber: 20,
      min: 'dataMin',
      max: 'dataMax',
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      scale: true,
      splitArea: {
        show: true
      },
      axisLabel: {
        formatter: (value) => value > 0 ? `+${value.toFixed(3)}` : value.toFixed(3)
      }
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        show: true,
        type: 'slider',
        top: '90%',
        start: 0,
        end: 100
      }
    ],
    series: [
      {
        name: '预测值',
        type: 'candlestick',
        data: candleData,
        itemStyle: {
          color: '#4CAF50',
          color0: '#F44336',
          borderColor: '#4CAF50',
          borderColor0: '#F44336'
        },
        markLine: {
          symbol: ['none', 'none'],
          data: [
            {
              name: '买入阈值',
              yAxis: buyThreshold.value,
              lineStyle: {
                type: 'dashed',
                color: '#4CAF50'
              }
            },
            {
              name: '卖出阈值',
              yAxis: sellThreshold.value,
              lineStyle: {
                type: 'dashed',
                color: '#F44336'
              }
            }
          ]
        }
      }
    ]
  }

  chart.setOption(option)
}

// 散点图
const drawScatterChart = (chart, stock) => {
  const dates = Object.keys(stock.predictions).sort()
  const scatterData = dates.map((date, idx) => {
    const pred = stock.predictions[date]
    const signal = stock.signals[date]
    return {
      value: [idx, pred],
      itemStyle: {
        color: signal === 1 ? '#4CAF50' : signal === -1 ? '#F44336' : '#9E9E9E'
      }
    }
  })

  const option = {
    title: {
      text: `${stock.symbol} 预测值分布`,
      left: 'center'
    },
    tooltip: {
      formatter: (params) => {
        const date = dates[params.value[0]]
        const pred = params.value[1]
        const signal = stock.signals[date]
        return `${date}<br/>预测值: ${pred > 0 ? '+' : ''}${pred.toFixed(4)}<br/>信号: ${getSignalText(signal)}`
      }
    },
    grid: {
      left: '3%',
      right: '7%',
      bottom: '7%',
      containLabel: true
    },
    xAxis: {
      name: '时间序列',
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    yAxis: {
      name: '预测值',
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      },
      scale: true,
      axisLabel: {
        formatter: (value) => value > 0 ? `+${value.toFixed(3)}` : value.toFixed(3)
      }
    },
    visualMap: {
      min: Math.min(...Object.values(stock.predictions)),
      max: Math.max(...Object.values(stock.predictions)),
      dimension: 1,
      orient: 'vertical',
      right: 10,
      top: 'center',
      text: ['HIGH', 'LOW'],
      calculable: true,
      inRange: {
        color: ['#F44336', '#9E9E9E', '#4CAF50']
      }
    },
    series: [
      {
        name: '预测值',
        type: 'scatter',
        symbolSize: 10,
        data: scatterData
      }
    ]
  }

  chart.setOption(option)
}

// 饼图（信号分布）
const drawPieChart = (chart, stock) => {
  const buyCount = stock.stats.buy_signals
  const sellCount = stock.stats.sell_signals
  const holdCount = stock.stats.hold_signals

  const option = {
    title: {
      text: `${stock.symbol} 信号分布`,
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'center'
    },
    series: [
      {
        name: '交易信号',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {c}\n({d}%)'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: true
        },
        data: [
          {
            value: buyCount,
            name: '买入信号',
            itemStyle: { color: '#4CAF50' }
          },
          {
            value: sellCount,
            name: '卖出信号',
            itemStyle: { color: '#F44336' }
          },
          {
            value: holdCount,
            name: '持有观望',
            itemStyle: { color: '#9E9E9E' }
          }
        ]
      }
    ]
  }

  chart.setOption(option)
}

// 全局热力图
const drawGlobalHeatmap = () => {
  const container = document.querySelector('.global-heatmap')
  if (!container) return

  const heatmapInstance = echarts.init(container)

  // 准备数据
  const symbols = predictions.value.map(p => p.symbol)
  const allDates = [...new Set(
    predictions.value.flatMap(p => Object.keys(p.predictions))
  )].sort()

  // 限制显示最近 30 天
  const displayDates = allDates.slice(-30)

  const heatmapData = []
  predictions.value.forEach((stock, symbolIdx) => {
    displayDates.forEach((date, dateIdx) => {
      const pred = stock.predictions[date]
      if (pred !== undefined) {
        heatmapData.push([dateIdx, symbolIdx, pred])
      }
    })
  })

  const option = {
    title: {
      text: '多股票预测热力图',
      left: 'center'
    },
    tooltip: {
      position: 'top',
      formatter: (params) => {
        const date = displayDates[params.value[0]]
        const symbol = symbols[params.value[1]]
        const pred = params.value[2]
        return `${symbol}<br/>${date}<br/>预测值: ${pred > 0 ? '+' : ''}${pred.toFixed(4)}`
      }
    },
    grid: {
      height: symbols.length * 50,
      top: '10%',
      left: '10%'
    },
    xAxis: {
      type: 'category',
      data: displayDates,
      splitArea: {
        show: true
      },
      axisLabel: {
        rotate: 45,
        interval: Math.floor(displayDates.length / 10)
      }
    },
    yAxis: {
      type: 'category',
      data: symbols,
      splitArea: {
        show: true
      }
    },
    visualMap: {
      min: -0.05,
      max: 0.05,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#F44336', '#FFFFFF', '#4CAF50']
      },
      text: ['强看多', '强看空'],
      textStyle: {
        color: '#000'
      }
    },
    series: [
      {
        name: '预测值',
        type: 'heatmap',
        data: heatmapData,
        label: {
          show: false
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }

  heatmapInstance.setOption(option)

  // 响应式调整
  window.addEventListener('resize', () => {
    heatmapInstance.resize()
  })
}

// 获取最近 N 条预测
const getRecentPredictions = (stock, limit = 10) => {
  const dates = Object.keys(stock.predictions).sort().reverse().slice(0, limit)
  const result = {}
  dates.forEach(date => {
    result[date] = stock.predictions[date]
  })
  return result
}

// 样式辅助函数
const getSignalClass = (signal) => {
  if (signal === 1) return 'signal-buy'
  if (signal === -1) return 'signal-sell'
  return ''
}

const getPredictionClass = (pred) => {
  if (pred > buyThreshold.value) return 'pred-positive'
  if (pred < sellThreshold.value) return 'pred-negative'
  return ''
}

const getSignalBadgeClass = (signal) => {
  if (signal === 1) return 'badge-buy'
  if (signal === -1) return 'badge-sell'
  return 'badge-hold'
}

const getSignalText = (signal) => {
  if (signal === 1) return '买入'
  if (signal === -1) return '卖出'
  return '持有'
}

const getActionText = (signal) => {
  if (signal === 1) return '建议买入'
  if (signal === -1) return '建议卖出'
  return '观望'
}

// 导出 CSV
const exportStockData = (stock) => {
  const dates = Object.keys(stock.predictions).sort()

  let csv = 'Date,Prediction,Signal,Action\n'
  dates.forEach(date => {
    const pred = stock.predictions[date]
    const signal = stock.signals[date]
    csv += `${date},${pred},${signal},${getActionText(signal)}\n`
  })

  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${stock.symbol}_predictions.csv`
  a.click()
}

// 导出为策略对话框
const showExportDialog = () => {
  // 初始化导出参数（使用当前预测参数）
  exportBuyThreshold.value = buyThreshold.value
  exportSellThreshold.value = sellThreshold.value
  strategyName.value = model.value?.name ? `${model.value.name} 策略` : ''
  strategyDescription.value = ''
  exportDialogVisible.value = true
}

const closeExportDialog = () => {
  exportDialogVisible.value = false
  strategyName.value = ''
  strategyDescription.value = ''
}

const exportToStrategy = async () => {
  if (!strategyName.value || !strategyName.value.trim()) {
    alert('请输入策略名称')
    return
  }

  try {
    exporting.value = true
    const token = getToken()

    if (!token) {
      alert('请先登录')
      return
    }

    const headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }

    const body = {
      strategy_name: strategyName.value.trim(),
      buy_threshold: exportBuyThreshold.value,
      sell_threshold: exportSellThreshold.value,
      description: strategyDescription.value || null
    }

    const response = await $fetch(`/api/v1/rdagent/models/${modelId.value}/export-strategy`, {
      method: 'POST',
      headers,
      body
    })

    console.log('✅ Export response:', response)

    // 关闭对话框
    closeExportDialog()

    // 成功提示并询问是否跳转
    const shouldNavigate = confirm(
      `✅ ${response.message}\n\n` +
      `策略 ID: ${response.strategy_id}\n\n` +
      `是否立即跳转到回测中心？\n` +
      `(点击"取消"留在当前页面)`
    )

    if (shouldNavigate) {
      // 使用 router.push 进行客户端导航（不会刷新页面）
      router.push('/backtest')
    }

  } catch (err) {
    console.error('❌ Export failed:', err)
    if (err.data?.detail) {
      alert(`导出失败: ${err.data.detail}`)
    } else {
      alert(`导出失败: ${err.message || '未知错误'}`)
    }
  } finally {
    exporting.value = false
  }
}

// 计算统计
const totalDays = computed(() => {
  if (!predictions.value) return 0
  return predictions.value.reduce((sum, stock) => sum + stock.stats.total_days, 0)
})

const totalBuySignals = computed(() => {
  if (!predictions.value) return 0
  return predictions.value.reduce((sum, stock) => sum + stock.stats.buy_signals, 0)
})

const totalSellSignals = computed(() => {
  if (!predictions.value) return 0
  return predictions.value.reduce((sum, stock) => sum + stock.stats.sell_signals, 0)
})

const buySignalPercent = computed(() => {
  if (totalDays.value === 0) return 0
  return ((totalBuySignals.value / totalDays.value) * 100).toFixed(1)
})

const sellSignalPercent = computed(() => {
  if (totalDays.value === 0) return 0
  return ((totalSellSignals.value / totalDays.value) * 100).toFixed(1)
})

const avgPrediction = computed(() => {
  if (!predictions.value) return '0.0000'
  const total = predictions.value.reduce((sum, stock) => sum + stock.stats.mean_prediction, 0)
  return (total / predictions.value.length).toFixed(4)
})

onMounted(() => {
  initDates()
  loadModelInfo()
})
</script>

<style scoped>
/* 基础布局 */
.model-predict-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding-bottom: 2rem;
}

.page-header {
  background: white;
  padding: 2rem;
  margin: 2rem;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h1 {
  margin: 0 0 0.5rem 0;
  font-size: 2rem;
  color: #333;
}

.header-content p {
  margin: 0.25rem 0;
  color: #666;
}

.model-ic {
  font-weight: 600;
  color: #667eea;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

/* 主容器 */
.predict-container {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 2rem;
  margin: 0 2rem;
}

/* 配置面板 */
.config-panel {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  height: fit-content;
}

.config-panel h2 {
  margin: 0 0 1.5rem 0;
  font-size: 1.5rem;
  color: #333;
}

.config-section {
  margin-bottom: 2rem;
}

.config-section label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
}

/* 股票选择 */
.preset-groups {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.preset-btn {
  flex: 1;
  padding: 0.5rem;
  border: 2px solid #e0e0e0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.preset-btn:hover {
  border-color: #667eea;
  background: #f5f7ff;
}

.preset-btn.active {
  border-color: #667eea;
  background: #667eea;
  color: white;
}

.manual-input {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.manual-input input {
  flex: 1;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 1rem;
}

.selected-stocks {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  min-height: 40px;
}

.stock-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #667eea;
  color: white;
  border-radius: 20px;
  font-size: 0.9rem;
}

.remove-btn {
  background: none;
  border: none;
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.selection-count {
  font-size: 0.9rem;
  color: #666;
}

/* 日期输入 */
.date-inputs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.date-inputs input {
  flex: 1;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 1rem;
}

.date-presets {
  display: flex;
  gap: 0.5rem;
}

.preset-date-btn {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #e0e0e0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}

.preset-date-btn:hover {
  background: #f5f5f5;
}

/* 阈值输入 */
.threshold-inputs {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.threshold-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.threshold-item input {
  width: 80px;
  padding: 0.5rem;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
}

.threshold-hint {
  font-size: 0.85rem;
  color: #999;
}

/* 按钮 */
.btn-primary {
  width: 100%;
  padding: 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: white;
  color: #667eea;
  border: 2px solid #667eea;
  border-radius: 8px;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-secondary:hover {
  background: #667eea;
  color: white;
}

/* 结果面板 */
.results-panel {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.results-panel h2 {
  margin: 0 0 1.5rem 0;
  font-size: 1.5rem;
  color: #333;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #999;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

/* 汇总卡片 */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.summary-card {
  background: #f5f5f5;
  padding: 1.5rem;
  border-radius: 8px;
  text-align: center;
}

.summary-card.buy {
  background: linear-gradient(135deg, #4caf50 0%, #66bb6a 100%);
  color: white;
}

.summary-card.sell {
  background: linear-gradient(135deg, #f44336 0%, #ef5350 100%);
  color: white;
}

.card-label {
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
  opacity: 0.8;
}

.card-value {
  font-size: 2rem;
  font-weight: 700;
}

.card-percent {
  font-size: 0.9rem;
  margin-top: 0.25rem;
  opacity: 0.9;
}

/* 股票预测 */
.stock-predictions {
  margin-bottom: 2rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.stock-header {
  background: #f5f5f5;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  cursor: pointer;
  transition: background 0.3s;
}

.stock-header:hover {
  background: #eeeeee;
}

.stock-header h3 {
  margin: 0;
  font-size: 1.3rem;
  color: #333;
}

.stock-stats {
  flex: 1;
  display: flex;
  gap: 1rem;
}

.stat-item {
  padding: 0.25rem 0.75rem;
  background: white;
  border-radius: 4px;
  font-size: 0.9rem;
}

.stat-item.buy {
  background: #4caf50;
  color: white;
}

.stat-item.sell {
  background: #f44336;
  color: white;
}

.expand-btn {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
}

.stock-details {
  padding: 1.5rem;
}

/* 图表选项卡 */
.chart-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 0.5rem;
}

.chart-tab {
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  font-size: 0.95rem;
  color: #666;
  transition: all 0.3s;
  position: relative;
  bottom: -2px;
}

.chart-tab:hover {
  color: #667eea;
  background: #f5f7ff;
}

.chart-tab.active {
  color: #667eea;
  border-bottom-color: #667eea;
  font-weight: 600;
}

/* 图表容器 */
.chart-container {
  margin-bottom: 2rem;
}

.echart {
  width: 100%;
  height: 400px;
}

/* 全局热力图 */
.global-heatmap-section {
  margin: 2rem 0;
  padding: 1.5rem;
  background: #f9f9f9;
  border-radius: 8px;
}

.global-heatmap-section h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  color: #333;
}

.global-heatmap {
  width: 100%;
  min-height: 300px;
  height: auto;
}

/* 表格 */
.prediction-table-container {
  overflow-x: auto;
  margin-bottom: 1rem;
}

.prediction-table {
  width: 100%;
  border-collapse: collapse;
}

.prediction-table th,
.prediction-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.prediction-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #333;
}

.prediction-table tr.signal-buy {
  background: rgba(76, 175, 80, 0.05);
}

.prediction-table tr.signal-sell {
  background: rgba(244, 67, 54, 0.05);
}

.pred-positive {
  color: #4caf50;
  font-weight: 600;
}

.pred-negative {
  color: #f44336;
  font-weight: 600;
}

.signal-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
}

.badge-buy {
  background: #4caf50;
  color: white;
}

.badge-sell {
  background: #f44336;
  color: white;
}

.badge-hold {
  background: #9e9e9e;
  color: white;
}

.export-actions {
  display: flex;
  justify-content: flex-end;
}

/* 加载和错误 */
.loading-container,
.error-message {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  margin: 2rem;
  border-radius: 12px;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

.spinner-small {
  display: inline-block;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #667eea;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
  margin-right: 0.5rem;
  vertical-align: middle;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  color: #f44336;
}

/* 导出对话框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-dialog {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.close-btn:hover {
  background-color: #f0f0f0;
  color: #333;
}

.modal-body {
  padding: 1.5rem;
}

.modal-description {
  color: #666;
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #333;
}

.required {
  color: #f44336;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
  transition: border-color 0.2s;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: #667eea;
}

.form-hint {
  font-size: 0.85rem;
  color: #999;
  margin-top: 0.25rem;
  margin-bottom: 0;
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
}

.model-info-box {
  background-color: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1rem;
  margin-top: 1rem;
}

.model-info-box h4 {
  margin: 0 0 0.75rem 0;
  font-size: 1rem;
  color: #333;
}

.model-info-box p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
  color: #666;
}

.model-info-box strong {
  color: #333;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid #e0e0e0;
}

.modal-footer button {
  padding: 0.75rem 1.5rem;
}
</style>
