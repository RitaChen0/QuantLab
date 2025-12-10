# 回測結果視覺化實作指南

## 📊 功能總覽

已完成**後端**所有必要改造，支援以下視覺化：
1. ✅ 淨值曲線圖（含回撤陰影）
2. ✅ 月度報酬熱圖
3. ✅ 交易分佈直方圖
4. ✅ 滾動夏普率曲線
5. ✅ 回撤時間序列

## 🔧 後端已完成內容

### 1. 資料庫架構
- 新增 `backtest_results.detailed_results` (JSON) 欄位
- Alembic 遷移: `3b90289c6cf0`

### 2. 回測引擎升級

#### 新增 Observer
```python
# backend/app/services/backtest_engine.py:29-65
class DailyValueObserver(bt.Observer):
    """記錄每日淨值、現金、股票價值"""
    lines = ('value', 'cash', 'stock_value')
```

#### 新增計算方法
- `_extract_daily_nav()` - 提取每日淨值
- `_calculate_monthly_returns()` - 計算月度報酬
- `_calculate_rolling_sharpe()` - 滾動夏普率（30天）
- `_calculate_drawdown_series()` - 回撤序列
- `_calculate_trade_distribution()` - 交易分佈

### 3. API 數據格式

獲取回測結果時（`GET /api/v1/backtest/{id}/result`），新增欄位：

```json
{
  "result": {
    "id": 1,
    "total_return": 15.30,
    "sharpe_ratio": 1.24,
    ...
    "detailed_results": {
      "daily_nav": [
        {
          "date": "2024-01-02",
          "value": 1000000,
          "cash": 500000,
          "stock_value": 500000
        },
        ...
      ],
      "monthly_returns": [
        {"month": "2024-01", "return_pct": 5.2},
        {"month": "2024-02", "return_pct": -2.1},
        ...
      ],
      "rolling_sharpe": [
        {"date": "2024-02-15", "sharpe": 1.24},
        ...
      ],
      "drawdown_series": [
        {"date": "2024-01-05", "drawdown_pct": -2.5},
        ...
      ],
      "trade_distribution": {
        "profit_bins": [5, 8, 12, 7, 3, 2, 1, 0, 0, 0],
        "loss_bins": [0, 1, 2, 4, 6, 3, 1, 0, 0, 0],
        "holding_days_dist": {
          "0-1 days": 10,
          "2-5 days": 25,
          "6-10 days": 15,
          "11-20 days": 8,
          "21+ days": 5
        }
      }
    }
  }
}
```

## 🎨 前端實作步驟

### 步驟 1：修改頁面結構

在 `frontend/pages/backtest/[id].vue` 的績效指標之後添加標籤頁：

```vue
<template>
  <!-- ... 現有的基本信息和績效指標 ... -->

  <!-- 詳細視覺化圖表（新增） -->
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

  <!-- ... 現有的交易記錄表格 ... -->
</template>
```

### 步驟 2：添加標籤頁狀態管理

```typescript
// Script setup
const activeTab = ref('nav')

const chartTabs = [
  { id: 'nav', label: '淨值曲線', icon: '📈' },
  { id: 'monthly', label: '月度報酬', icon: '📅' },
  { id: 'distribution', label: '交易分佈', icon: '📊' },
  { id: 'rolling', label: '滾動指標', icon: '🔄' }
]

// Chart refs
const navChartRef = ref<HTMLElement | null>(null)
const monthlyChartRef = ref<HTMLElement | null>(null)
const distributionChartRef = ref<HTMLElement | null>(null)
const rollingChartRef = ref<HTMLElement | null>(null)

const detailedResults = computed(() => backtest.value?.result?.detailed_results)
```

### 步驟 3：實作淨值曲線圖

```typescript
const renderNavChart = () => {
  if (!detailedResults.value?.daily_nav || !navChartRef.value) return

  const chart = window.echarts.init(navChartRef.value)
  const data = detailedResults.value.daily_nav

  const dates = data.map((d: any) => d.date)
  const values = data.map((d: any) => d.value)
  const drawdowns = detailedResults.value.drawdown_series || []

  // 計算回撤區域（陰影）
  const areaData = drawdowns.map((d: any, i: number) => {
    return d.drawdown_pct < 0 ? values[i] : null
  })

  const option = {
    title: { text: '淨值曲線與回撤', left: 'center' },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const date = params[0].axisValue
        const nav = params[0].value
        const dd = drawdowns.find((d: any) => d.date === date)
        return `
          <b>${date}</b><br/>
          淨值: ${nav.toLocaleString()}<br/>
          ${dd ? `回撤: ${dd.drawdown_pct.toFixed(2)}%` : ''}
        `
      }
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '淨值',
        type: 'line',
        data: values,
        smooth: true,
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

  chart.setOption(option)
  chart.resize()
}
```

### 步驟 4：實作月度報酬熱圖

```typescript
const renderMonthlyChart = () => {
  if (!detailedResults.value?.monthly_returns || !monthlyChartRef.value) return

  const chart = window.echarts.init(monthlyChartRef.value)
  const data = detailedResults.value.monthly_returns

  // 轉換為熱圖格式 [year, month, return]
  const heatmapData = data.map((d: any) => {
    const [year, month] = d.month.split('-')
    return [parseInt(year), parseInt(month) - 1, d.return_pct]
  })

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
    grid: { left: 80, right: 20, top: 60, bottom: 60 },
    xAxis: {
      type: 'category',
      data: ['1月', '2月', '3月', '4月', '5月', '6月',
             '7月', '8月', '9月', '10月', '11月', '12月'],
      splitArea: { show: true }
    },
    yAxis: {
      type: 'category',
      data: [...new Set(heatmapData.map((d: any) => d[0]))].sort(),
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
      label: { show: true, formatter: (params: any) => params.data[2].toFixed(1) + '%' },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
      }
    }]
  }

  chart.setOption(option)
  chart.resize()
}
```

### 步驟 5：實作交易分佈圖

```typescript
const renderDistributionChart = () => {
  if (!detailedResults.value?.trade_distribution || !distributionChartRef.value) return

  const chart = window.echarts.init(distributionChartRef.value)
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

  chart.setOption(option)
  chart.resize()
}
```

### 步驟 6：實作滾動夏普率圖

```typescript
const renderRollingChart = () => {
  if (!detailedResults.value?.rolling_sharpe || !rollingChartRef.value) return

  const chart = window.echarts.init(rollingChartRef.value)
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
      lineStyle: { width: 2 },
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

  chart.setOption(option)
  chart.resize()
}
```

### 步驟 7：監聽標籤切換

```typescript
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

// 在 loadBacktestDetail 成功後初始化圖表
onMounted(() => {
  nextTick(() => {
    if (detailedResults.value) {
      renderNavChart() // 預設顯示淨值曲線
    }
  })
})
```

### 步驟 8：添加 CSS 樣式

```scss
<style scoped>
.charts-container {
  margin: 2rem 0;
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.section-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  color: #1f2937;
}

.tabs-nav {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #e5e7eb;
}

.tab-button {
  padding: 0.75rem 1.5rem;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 1rem;
  color: #6b7280;
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
}

.tab-button:hover {
  color: #3b82f6;
  background: #eff6ff;
}

.tab-button.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}

.tab-content {
  min-height: 400px;
}

.chart-panel {
  animation: fadeIn 0.3s;
}

.chart-canvas {
  width: 100%;
  height: 450px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
```

## ⚠️ 注意事項

1. **舊回測無數據**：只有執行新回測後才會有 `detailed_results` 數據
2. **性能考慮**：大量數據點（>1000）可能需要降採樣
3. **響應式設計**：圖表需要監聽窗口 resize 事件
4. **錯誤處理**：檢查 `detailed_results` 是否存在再渲染圖表

## 🧪 測試步驟

1. 執行一個新回測（選擇較長的時間範圍，如 2024-01-01 ~ 2024-12-31）
2. 等待回測完成
3. 進入回測詳情頁面
4. 確認「詳細分析圖表」區塊出現
5. 切換標籤頁，驗證各個圖表正常顯示

## 📚 相關文件

- 後端實作：`backend/app/services/backtest_engine.py`
- 資料庫模型：`backend/app/models/backtest_result.py`
- API schemas：`backend/app/schemas/backtest_result.py`
