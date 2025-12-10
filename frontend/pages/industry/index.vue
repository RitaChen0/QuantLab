<template>
  <div class="dashboard-container">
    <!-- 頂部導航欄 -->
    <AppHeader />

    <!-- 主要內容區 -->
    <main class="dashboard-main">
      <div class="industry-page p-6">
        <!-- Header -->
        <div class="mb-6">
          <h1 class="text-3xl font-bold text-gray-900 mb-2">產業分析</h1>
          <p class="text-gray-600">台灣證交所產業分類與聚合分析</p>
        </div>

      <!-- Data Source Selector -->
      <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-sm p-6 mb-6 border-2 border-blue-200">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold text-gray-900 mb-2">數據源選擇</h2>
            <p class="text-sm text-gray-600">選擇不同的產業分類數據源進行分析</p>
          </div>
          <div class="flex gap-3">
            <button
              @click="switchDataSource('twse')"
              :class="[
                'px-6 py-3 rounded-lg font-medium transition-all duration-200',
                dataSource === 'twse'
                  ? 'bg-blue-600 text-white shadow-lg scale-105'
                  : 'bg-white text-gray-700 hover:bg-gray-50 border-2 border-gray-200'
              ]"
            >
              <span class="text-xl mr-2">🏢</span>
              TWSE 分類
              <span v-if="dataSource === 'twse'" class="ml-2">✓</span>
            </button>
            <button
              @click="switchDataSource('finmind')"
              :class="[
                'px-6 py-3 rounded-lg font-medium transition-all duration-200',
                dataSource === 'finmind'
                  ? 'bg-indigo-600 text-white shadow-lg scale-105'
                  : 'bg-white text-gray-700 hover:bg-gray-50 border-2 border-gray-200'
              ]"
            >
              <span class="text-xl mr-2">🔗</span>
              FinMind 產業鏈
              <span v-if="dataSource === 'finmind'" class="ml-2">✓</span>
            </button>
          </div>
        </div>

        <!-- Data Source Info -->
        <div v-if="dataSource === 'twse'" class="mt-4 p-4 bg-blue-100 rounded-lg">
          <div class="flex items-center gap-2 text-sm text-blue-900">
            <span class="font-semibold">📌 當前數據源：</span>
            台灣證券交易所官方產業分類 (3 層級階層結構)
          </div>
        </div>
        <div v-else-if="dataSource === 'finmind'" class="mt-4 p-4 bg-indigo-100 rounded-lg">
          <div class="flex items-center gap-2 text-sm text-indigo-900">
            <span class="font-semibold">📌 當前數據源：</span>
            FinMind 開源產業鏈分類 (需先同步數據)
            <button
              @click="syncFinmindData"
              :disabled="syncing"
              class="ml-auto px-3 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:bg-gray-400 text-xs"
            >
              {{ syncing ? '同步中...' : '同步數據' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Statistics Card -->
      <div v-if="statistics" class="stats-section">
        <h2 class="stats-title">
          資料庫統計
          <span class="stats-subtitle">
            ({{ dataSource === 'twse' ? 'TWSE' : 'FinMind' }})
          </span>
        </h2>
        <div class="stats-grid">
          <!-- 總產業數 -->
          <div class="stat-card stat-card-blue">
            <div class="stat-number">
              {{ dataSource === 'twse' ? statistics.total_industries : (statistics.total_chains || 0) }}
            </div>
            <div class="stat-label">
              {{ dataSource === 'twse' ? '總產業數' : '總產業鏈數' }}
            </div>
          </div>

          <!-- 大類產業 -->
          <div class="stat-card stat-card-green">
            <div class="stat-number">
              {{ dataSource === 'twse' ? (statistics.by_level?.level_1 || 0) : (statistics.total_chains || 0) }}
            </div>
            <div class="stat-label">
              {{ dataSource === 'twse' ? '大類產業' : '產業鏈分類' }}
            </div>
          </div>

          <!-- 中類產業 -->
          <div class="stat-card stat-card-purple">
            <div class="stat-number">
              {{ dataSource === 'twse' ? (statistics.by_level?.level_2 || 0) : '—' }}
            </div>
            <div class="stat-label">
              {{ dataSource === 'twse' ? '中類產業' : '—' }}
            </div>
          </div>

          <!-- 股票映射 -->
          <div class="stat-card stat-card-orange">
            <div class="stat-number">
              {{ dataSource === 'twse' ? statistics.total_stock_mappings : (statistics.total_mappings || 0) }}
            </div>
            <div class="stat-label">股票映射</div>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tabs-container mb-6">
        <button
          @click="activeTab = 'basic'"
          :class="['tab-btn', { active: activeTab === 'basic' }]"
        >
          <span class="tab-icon">📋</span>
          基本分析
        </button>
        <button
          @click="activeTab = 'charts'"
          :class="['tab-btn', { active: activeTab === 'charts' }]"
        >
          <span class="tab-icon">📊</span>
          進階圖表
        </button>
      </div>

      <!-- Basic Analysis Tab -->
      <div v-show="activeTab === 'basic'">
      <!-- Main Content -->
      <div class="grid grid-cols-12 gap-6">
        <!-- Left Panel: Industry Tree -->
        <div class="col-span-4 bg-white rounded-lg shadow-sm p-6">
          <div class="mb-6">
            <div class="flex items-center justify-between mb-3">
              <h2 class="industry-list-title">
                <span class="title-icon">{{ dataSource === 'twse' ? '🏢' : '🔗' }}</span>
                {{ dataSource === 'twse' ? '產業分類' : '產業鏈' }}
              </h2>
              <button
                @click="loadIndustryTree"
                class="reload-btn"
                :disabled="loading"
              >
                <span class="reload-icon">🔄</span>
                {{ loading ? '載入中...' : '重新載入' }}
              </button>
            </div>
            <div v-if="dataSource === 'twse' && displayedIndustries.length > 0" class="industry-count-badge">
              <span class="badge-icon">📊</span>
              顯示 <strong>{{ displayedIndustries.length }}</strong> 個有股票的產業
            </div>
          </div>

          <!-- Level Filter (TWSE only) -->
          <div v-if="dataSource === 'twse'" class="mb-6">
            <label class="filter-label">篩選層級</label>
            <select
              v-model="selectedLevel"
              @change="filterByLevel"
              class="level-select"
            >
              <option :value="null">📁 所有層級</option>
              <option :value="1">🔵 大類產業</option>
              <option :value="2">🟢 中類產業</option>
              <option :value="3">🟡 小類產業</option>
            </select>
          </div>

          <!-- Search Filter (FinMind) -->
          <div v-else class="mb-4">
            <input
              v-model="searchKeyword"
              @input="filterByKeyword"
              type="text"
              placeholder="搜尋產業鏈..."
              class="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <!-- Industry List -->
          <div class="max-h-[600px] overflow-y-auto pr-2">
            <!-- TWSE Industries Grid -->
            <div v-if="dataSource === 'twse'" class="industry-grid">
              <div
                v-for="industry in displayedIndustries"
                :key="industry.code"
                @click="selectIndustry(industry)"
                :class="[
                  'industry-card-compact',
                  selectedIndustry?.code === industry.code ? 'selected' : '',
                  `level-${industry.level}`
                ]"
              >
                <div class="industry-name">{{ industry.name_zh }}</div>
                <div class="industry-count">{{ industry.stock_count }} 檔</div>
              </div>
            </div>

            <!-- FinMind Industry Chains Grid -->
            <div v-else class="industry-grid">
              <div
                v-for="chain in displayedIndustries"
                :key="chain.id"
                @click="selectIndustry(chain)"
                :class="[
                  'industry-card-compact finmind',
                  selectedIndustry?.id === chain.id ? 'selected' : ''
                ]"
              >
                <div class="industry-name">{{ chain.chain_name }}</div>
                <div class="industry-count">{{ chain.stock_count }} 檔</div>
              </div>
            </div>

            <!-- Empty State -->
            <div v-if="displayedIndustries.length === 0" class="text-center py-8 text-gray-500">
              {{ dataSource === 'twse' ? '無符合條件的產業' : '無產業鏈數據，請先同步數據' }}
            </div>
          </div>
        </div>

        <!-- Right Panel: Industry Details -->
        <div class="col-span-8">
          <!-- Selected Industry Info -->
          <div v-if="selectedIndustry" class="bg-white rounded-lg shadow-sm p-6 mb-6">
            <!-- TWSE Industry Info -->
            <template v-if="dataSource === 'twse'">
              <h2 class="text-xl font-bold text-gray-900 mb-4">
                {{ selectedIndustry.name_zh }}
                <span class="text-gray-500 text-base font-normal ml-2">
                  {{ selectedIndustry.name_en }}
                </span>
              </h2>

              <div class="info-cards-container">
                <div class="info-card">
                  <div class="info-label">
                    <span class="info-icon">🏷️</span>
                    產業代碼
                  </div>
                  <div class="info-value">{{ selectedIndustry.code }}</div>
                </div>
                <div class="info-card">
                  <div class="info-label">
                    <span class="info-icon">📊</span>
                    產業層級
                  </div>
                  <div class="info-value">Level {{ selectedIndustry.level }}</div>
                </div>
                <div class="info-card">
                  <div class="info-label">
                    <span class="info-icon">📈</span>
                    股票數量
                  </div>
                  <div class="info-value">{{ selectedIndustry.stock_count }} 檔</div>
                </div>
              </div>
            </template>

            <!-- FinMind Chain Info -->
            <template v-else>
              <h2 class="text-xl font-bold text-gray-900 mb-4">
                {{ selectedIndustry.chain_name }}
              </h2>

              <div v-if="selectedIndustry.description" class="mb-4 p-3 bg-gray-50 rounded-lg">
                <div class="text-sm text-gray-700">{{ selectedIndustry.description }}</div>
              </div>

              <div class="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <div class="text-sm text-gray-600">數據源</div>
                  <div class="font-semibold">FinMind 產業鏈</div>
                </div>
                <div>
                  <div class="text-sm text-gray-600">股票數量</div>
                  <div class="font-semibold">{{ selectedIndustry.stock_count }} 檔</div>
                </div>
              </div>
            </template>

            <!-- Load Stocks Button -->
            <button
              @click="loadIndustryStocks"
              :disabled="loadingStocks"
              class="load-stocks-btn"
            >
              <span class="btn-icon">{{ loadingStocks ? '⏳' : '📋' }}</span>
              <span class="btn-text">{{ loadingStocks ? '載入中...' : '載入股票列表' }}</span>
            </button>
          </div>

          <!-- Stocks List -->
          <div v-if="industryStocks.length > 0" class="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h3 class="text-lg font-semibold mb-4">產業內股票 ({{ industryStocks.length }} 檔)</h3>
            <div class="stock-grid">
              <div
                v-for="stock in industryStocks"
                :key="stock.stock_id"
                class="stock-card"
                @click="viewStock(stock.stock_id)"
              >
                <div class="stock-name">{{ stock.stock_name }}</div>
                <div class="stock-code">{{ stock.stock_id }}</div>
              </div>
            </div>
          </div>

          <!-- Industry Metrics -->
          <div v-if="selectedIndustry" class="bg-white rounded-lg shadow-sm p-6">
            <div class="metrics-header">
              <h3 class="metrics-title">
                <span class="metrics-icon">📊</span>
                產業聚合指標
              </h3>
              <button
                @click="loadIndustryMetrics"
                :disabled="loadingMetrics"
                class="calculate-metrics-btn"
              >
                <span class="btn-icon">{{ loadingMetrics ? '⚙️' : '🧮' }}</span>
                <span class="btn-text">{{ loadingMetrics ? '計算中...' : '計算指標' }}</span>
              </button>
            </div>

            <!-- Metrics Display -->
            <div v-if="industryMetrics">
              <!-- Enhanced Data Info Card -->
              <div class="metrics-info-card">
                <div class="info-card-header">
                  <div class="header-icon">📊</div>
                  <div class="header-text">
                    <div class="header-title">數據概況</div>
                    <div class="header-subtitle">Industry Metrics Overview</div>
                  </div>
                </div>

                <div class="info-stats-grid">
                  <!-- 數據日期 -->
                  <div class="info-stat-item date">
                    <div class="stat-icon-wrapper">
                      <span class="stat-icon">📅</span>
                    </div>
                    <div class="stat-content">
                      <div class="stat-label">數據日期</div>
                      <div class="stat-value">{{ industryMetrics.date }}</div>
                      <div class="stat-desc">Data Period</div>
                    </div>
                  </div>

                  <!-- 計算基礎 -->
                  <div class="info-stat-item stocks">
                    <div class="stat-icon-wrapper">
                      <span class="stat-icon">🏢</span>
                    </div>
                    <div class="stat-content">
                      <div class="stat-label">產業規模</div>
                      <div class="stat-value">{{ industryMetrics.stocks_count }} 檔</div>
                      <div class="stat-desc">Total Stocks</div>
                    </div>
                  </div>

                  <!-- 有效樣本 -->
                  <div class="info-stat-item samples">
                    <div class="stat-icon-wrapper">
                      <span class="stat-icon">📊</span>
                    </div>
                    <div class="stat-content">
                      <div class="stat-label">有效樣本</div>
                      <div class="stat-value">{{ industryMetrics.stocks_with_data_count }} 檔</div>
                      <div class="stat-desc">Valid Samples</div>
                    </div>
                  </div>

                  <!-- 數據完整度 -->
                  <div class="info-stat-item coverage">
                    <div class="stat-icon-wrapper">
                      <span class="stat-icon">✅</span>
                    </div>
                    <div class="stat-content">
                      <div class="stat-label">數據完整度</div>
                      <div class="stat-value">
                        {{ ((industryMetrics.stocks_with_data_count / industryMetrics.stocks_count) * 100).toFixed(1) }}%
                      </div>
                      <div class="stat-desc">Data Coverage</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Radar Chart -->
              <div class="mb-6">
                <h4 class="text-md font-semibold mb-3">產業健康度雷達圖</h4>
                <div id="radarChart" style="width: 100%; height: 400px;"></div>
                <button
                  v-if="!radarChartLoaded"
                  @click="loadRadarChart"
                  class="mt-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                >
                  顯示雷達圖
                </button>
              </div>

              <!-- Historical Trend Chart -->
              <div class="mb-6">
                <div class="flex items-center justify-between mb-3">
                  <h4 class="text-md font-semibold">歷史趨勢分析</h4>
                  <div class="flex gap-2">
                    <select
                      v-model="selectedTrendMetric"
                      @change="loadTrendChart"
                      class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">選擇指標</option>
                      <option value="ROE稅後">ROE稅後</option>
                      <option value="ROA稅後息前">ROA稅後息前</option>
                      <option value="營業毛利率">營業毛利率</option>
                      <option value="營業利益率">營業利益率</option>
                      <option value="每股稅後淨利">每股稅後淨利</option>
                      <option value="營收成長率">營收成長率</option>
                      <option value="稅後淨利成長率">稅後淨利成長率</option>
                    </select>
                  </div>
                </div>
                <div v-if="selectedTrendMetric" id="trendChart" style="width: 100%; height: 350px;"></div>
                <div v-else class="text-center py-12 text-gray-400">
                  請選擇指標以查看歷史趨勢
                </div>
              </div>

              <!-- Enhanced Metric Cards -->
              <h4 class="text-md font-semibold mb-3">詳細指標</h4>
              <div class="grid grid-cols-2 gap-4">
                <div
                  v-for="(metric, name) in industryMetrics.metrics"
                  :key="name"
                  :class="['metric-card', getMetricColorClass(name, metric.average)]"
                >
                  <div class="flex items-start justify-between mb-2">
                    <div class="text-sm text-gray-600">{{ name }}</div>
                    <div v-if="metric.change_percent !== null" :class="['change-badge', metric.change_percent >= 0 ? 'positive' : 'negative']">
                      <span class="arrow">{{ metric.change_percent >= 0 ? '↗' : '↘' }}</span>
                      <span class="percent">{{ Math.abs(metric.change_percent).toFixed(1) }}%</span>
                    </div>
                  </div>
                  <div class="text-2xl font-bold mb-2">
                    {{ metric.average?.toFixed(2) || 'N/A' }}
                  </div>
                  <!-- Sparkline -->
                  <div v-if="metric.trend_data && metric.trend_data.length > 0" class="sparkline-container">
                    <svg class="sparkline" :id="`sparkline-${name}`" width="100%" height="40"></svg>
                  </div>
                  <div class="text-xs text-gray-500 mt-1">
                    樣本數: {{ metric.sample_size }}
                    <span v-if="metric.previous_value"> | 上季: {{ metric.previous_value.toFixed(2) }}</span>
                  </div>
                </div>
              </div>

              <!-- No Metrics -->
              <div v-if="Object.keys(industryMetrics.metrics).length === 0" class="text-center py-8">
                <div class="text-gray-500 mb-2">⚠️ 暫無可用指標數據</div>
                <div class="text-xs text-gray-400">
                  該產業內的股票尚無基本面資料<br>
                  目前系統僅有少數股票的財務指標資料
                </div>
              </div>

              <!-- Industry Comparison Section -->
              <div class="mt-6">
                <h4 class="text-md font-semibold mb-4">產業橫向對比</h4>

                <!-- Comparison Controls -->
                <div class="mb-4 space-y-3">
                  <div class="flex gap-2 flex-wrap">
                    <div class="flex-1 min-w-[300px]">
                      <label class="block text-sm text-gray-600 mb-1">選擇對比產業 (最多 5 個)</label>
                      <select
                        v-model="selectedComparisonIndustry"
                        @change="addComparisonIndustry"
                        class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        :disabled="comparisonIndustries.length >= 5"
                      >
                        <option value="">選擇產業...</option>
                        <option
                          v-for="industry in displayedIndustries.filter(i => i.level === 1)"
                          :key="industry.code"
                          :value="industry.code"
                          :disabled="comparisonIndustries.some(c => c.code === industry.code)"
                        >
                          {{ industry.name_zh }}
                        </option>
                      </select>
                    </div>

                    <div class="flex-1 min-w-[200px]">
                      <label class="block text-sm text-gray-600 mb-1">選擇對比指標</label>
                      <select
                        v-model="comparisonMetric"
                        class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="ROE稅後">ROE稅後</option>
                        <option value="ROA稅後息前">ROA稅後息前</option>
                        <option value="營業毛利率">營業毛利率</option>
                        <option value="營業利益率">營業利益率</option>
                        <option value="每股稅後淨利">每股稅後淨利</option>
                        <option value="營收成長率">營收成長率</option>
                        <option value="稅後淨利成長率">稅後淨利成長率</option>
                      </select>
                    </div>

                    <div class="flex items-end">
                      <button
                        @click="loadComparisonChart"
                        :disabled="comparisonIndustries.length < 2"
                        class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                      >
                        開始對比
                      </button>
                    </div>
                  </div>

                  <!-- Selected Industries -->
                  <div v-if="comparisonIndustries.length > 0" class="flex gap-2 flex-wrap">
                    <div
                      v-for="industry in comparisonIndustries"
                      :key="industry.code"
                      class="px-3 py-1.5 bg-blue-100 text-blue-800 rounded-full text-sm flex items-center gap-2"
                    >
                      <span>{{ industry.name }}</span>
                      <button
                        @click="removeComparisonIndustry(industry.code)"
                        class="hover:text-blue-900"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Comparison Chart -->
                <div v-if="comparisonChartData" id="comparisonChart" style="width: 100%; height: 400px;"></div>
                <div v-else class="text-center py-12 text-gray-400">
                  選擇至少 2 個產業並點擊「開始對比」查看對比圖表
                </div>
              </div>
            </div>

            <!-- Metrics Placeholder -->
            <div v-else class="text-center py-8 text-gray-500">
              點擊「計算指標」以查看產業聚合財務指標
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="!selectedIndustry" class="bg-white rounded-lg shadow-sm p-12 text-center">
            <div class="text-gray-400 mb-4">
              <svg class="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 class="text-lg font-medium text-gray-900 mb-2">選擇產業以查看詳情</h3>
            <p class="text-gray-500">從左側列表選擇一個產業以查看詳細資訊和分析</p>
          </div>
        </div>
      </div>
      </div>

      <!-- Advanced Charts Tab -->
      <div v-show="activeTab === 'charts'">
        <div class="space-y-6">
          <!-- Stock Distribution Heatmap -->
          <StockDistributionHeatmap />

          <!-- Industry Comparison Radar (only show if industries loaded) -->
          <IndustryComparisonRadar
            v-if="industries.length > 0"
            :available-industries="industries.filter(i => i.level === 1)"
          />

          <!-- Industry Trend Chart (only show if industry selected) -->
          <IndustryTrendChart
            v-if="selectedIndustry"
            :industry-code="selectedIndustry.code"
            :industry-name="selectedIndustry.name_zh"
          />

          <!-- Empty State -->
          <div v-if="!selectedIndustry" class="bg-white rounded-lg shadow-sm p-12 text-center">
            <div class="text-gray-400 mb-4">
              <svg class="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 class="text-lg font-medium text-gray-900 mb-2">選擇產業查看趨勢圖</h3>
            <p class="text-gray-500">切換到「基本分析」標籤選擇一個產業，即可在此查看該產業的歷史趨勢圖表</p>
          </div>
        </div>
      </div>

      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import IndustryTrendChart from '~/components/IndustryTrendChart.vue'
import IndustryComparisonRadar from '~/components/IndustryComparisonRadar.vue'
import StockDistributionHeatmap from '~/components/StockDistributionHeatmap.vue'

// ========== Configuration Constants ==========

// Chart Dimensions
const CHART_DIMENSIONS = {
  SPARKLINE_HEIGHT: 60,
  DATA_POINT_WIDTH: 20,
  MIN_WIDTH: 100,
  DEFAULT_MAX_WIDTH: 200,
  RADAR_RADIUS: '60%',
  RADAR_SPLIT_NUMBER: 5
} as const

// Chart Styling
const CHART_STYLES = {
  STROKE_WIDTH_THIN: 1,
  STROKE_WIDTH_THICK: 2,
  DATA_POINT_RADIUS: 2,
  FONT_SIZE_SMALL: 9,
  FONT_SIZE_MEDIUM: 10,
  FONT_SIZE_TOOLTIP: 11,
  FONT_SIZE_AXIS: 12
} as const

// Chart Padding
const CHART_PADDING = {
  SPARKLINE: { top: 5, right: 30, bottom: 15, left: 5 },
  LABEL_OFFSET_X: 2,
  LABEL_OFFSET_Y: 3
} as const

// Radar Chart Calculations
const RADAR_CONFIG = {
  PADDING_MULTIPLIER: 0.2,      // 20% padding on each side
  MIN_RANGE_MULTIPLIER: 0.3,    // 30% of default max for minimum range
  HALF_RANGE_MULTIPLIER: 0.15   // 15% of default max for half range
} as const

// Number Formatting Thresholds
const NUMBER_FORMATS = {
  THRESHOLD_THOUSANDS: 1000,
  THRESHOLD_HUNDREDS: 100,
  THRESHOLD_TENS: 10,
  THRESHOLD_ONES: 1,
  ROUNDING_LARGE: 50,
  ROUNDING_MEDIUM: 10,
  DECIMAL_PRECISION_NONE: 0,
  DECIMAL_PRECISION_ONE: 1,
  DECIMAL_PRECISION_TWO: 2
} as const

// Timing Constants
const TIMING = {
  CHART_RESIZE_DELAY: 100  // milliseconds
} as const

// Indicator Default Maximum Values
const INDICATOR_DEFAULTS = {
  ROE稅後: 30,
  ROA稅後息前: 20,
  營業毛利率: 50,
  營業利益率: 30,
  每股稅後淨利: 10,
  營收成長率: 50,
  稅後淨利成長率: 50
} as const

// Metric Quality Thresholds
const METRIC_THRESHOLDS = {
  ROE稅後: { good: 15, ok: 8 },
  ROA稅後息前: { good: 10, ok: 5 },
  營業毛利率: { good: 30, ok: 15 },
  營業利益率: { good: 15, ok: 8 },
  每股稅後淨利: { good: 3, ok: 1 },
  營收成長率: { good: 10, ok: 0 },
  稅後淨利成長率: { good: 10, ok: 0 }
} as const

// ========== End of Constants ==========

const router = useRouter()
const config = useRuntimeConfig()
const { loadUserInfo } = useUserInfo()

// State
const activeTab = ref('basic')
const dataSource = ref<'twse' | 'finmind'>('twse')  // 數據源選擇
const loading = ref(false)
const loadingStocks = ref(false)
const loadingMetrics = ref(false)
const syncing = ref(false)  // FinMind 同步狀態
const industries = ref<any[]>([])
const statistics = ref<any>(null)
const selectedLevel = ref<number | null>(null)
const searchKeyword = ref('')  // FinMind 搜尋關鍵字
const selectedIndustry = ref<any>(null)
const industryStocks = ref<Array<{stock_id: string, stock_name: string}>>([])
const industryMetrics = ref<any>(null)
const radarChartLoaded = ref(false)
const selectedTrendMetric = ref('')
const trendChartData = ref<any>(null)
const comparisonIndustries = ref<Array<{code: string, name: string}>>([])
const selectedComparisonIndustry = ref('')
const comparisonMetric = ref('ROE稅後')
const comparisonChartData = ref<any>(null)
let radarChartInstance: any = null
let trendChartInstance: any = null
let comparisonChartInstance: any = null

// Resize handlers for cleanup
let radarResizeHandler: (() => void) | null = null
let trendResizeHandler: (() => void) | null = null
let comparisonResizeHandler: (() => void) | null = null

// Computed
const displayedIndustries = computed(() => {
  // Filter for FinMind keyword search
  if (dataSource.value === 'finmind' && searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    return industries.value.filter(chain =>
      chain.chain_name?.toLowerCase().includes(keyword) ||
      chain.description?.toLowerCase().includes(keyword)
    )
  }

  // Filter out industries with 0 stocks for TWSE
  if (dataSource.value === 'twse') {
    return industries.value.filter(industry =>
      industry.stock_count && industry.stock_count > 0
    )
  }

  return industries.value
})

// Helper function to get industry icons
function getIndustryIcon(code: string): string {
  const iconMap: Record<string, string> = {
    'M01': '🏗️',  // 水泥工業
    'M02': '🍜',  // 食品工業
    'M03': '🧪',  // 塑膠工業
    'M04': '🧵',  // 紡織纖維
    'M05': '⚙️',  // 電機機械
    'M06': '🔌',  // 電器電纜
    'M07': '🧬',  // 化學生技醫療
    'M08': '🪟',  // 玻璃陶瓷
    'M09': '📄',  // 造紙工業
    'M10': '⚒️',  // 鋼鐵工業
    'M11': '🛞',  // 橡膠工業
    'M12': '🚗',  // 汽車工業
    'M13': '💻',  // 電子工業
    'M1301': '💾',  // 半導體業
    'M130101': '🎨',  // IC設計
    'M130102': '🏭',  // IC製造
    'M130103': '📦',  // IC封測
    'M130104': '🚚',  // IC通路
    'M130105': '🔧',  // IC其他
    'M1302': '🖥️',  // 電腦及週邊設備業
    'M1303': '💡',  // 光電業
    'M1304': '📡',  // 通信網路業
    'M1305': '🔩',  // 電子零組件業
    'M1306': '🏪',  // 電子通路業
    'M1307': '☁️',  // 資訊服務業
    'M1308': '⚡',  // 其他電子業
    'M14': '🏢',  // 建材營造
    'M15': '🚢',  // 航運業
    'M16': '🏨',  // 觀光事業
    'M17': '🏦',  // 金融保險
    'M1701': '🏛️',  // 銀行業
    'M1702': '📈',  // 證券業
    'M1703': '🛡️',  // 保險業
    'M1704': '💼',  // 金融控股
    'M1705': '💰',  // 其他金融
    'M18': '🛒',  // 貿易百貨
    'M19': '🌐',  // 綜合企業
    'M20': '📋',  // 其他
    'M21': '🎭',  // 文化創意業
    'M22': '🌾',  // 農業科技
    'M23': '🛍️',  // 電子商務
  }

  return iconMap[code] || '🏭'
}

// Methods
async function switchDataSource(source: 'twse' | 'finmind') {
  if (dataSource.value === source) return

  dataSource.value = source
  selectedIndustry.value = null
  industryStocks.value = []
  industryMetrics.value = []
  selectedLevel.value = null
  searchKeyword.value = ''

  // 重新載入數據
  await loadStatistics()
  await loadIndustries()
}

async function loadStatistics() {
  try {
    const token = localStorage.getItem('access_token')
    let url = ''

    if (dataSource.value === 'twse') {
      url = `${config.public.apiBase}/api/v1/industry/statistics/overview`
    } else {
      url = `${config.public.apiBase}/api/v1/industry-chain/statistics`
    }

    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.ok) {
      statistics.value = await response.json()
    } else if (response.status === 401) {
      // Token expired or invalid, redirect to login
      alert('登入已過期，請重新登入')
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      router.push('/login')
    }
  } catch (error) {
    console.error('Failed to load statistics:', error)
  }
}

async function loadIndustries() {
  loading.value = true
  try {
    const token = localStorage.getItem('access_token')
    let url = ''

    if (dataSource.value === 'twse') {
      url = `${config.public.apiBase}/api/v1/industry/`
      if (selectedLevel.value) {
        url += `?level=${selectedLevel.value}`
      }
    } else {
      url = `${config.public.apiBase}/api/v1/industry-chain/`
    }

    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.ok) {
      const data = await response.json()
      if (dataSource.value === 'twse') {
        industries.value = data.industries || []
      } else {
        industries.value = data || []
      }
    } else if (response.status === 401) {
      // Token expired or invalid, redirect to login
      alert('登入已過期，請重新登入')
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      router.push('/login')
    } else {
      alert(`載入${dataSource.value === 'twse' ? '產業' : '產業鏈'}列表失敗: ${response.status}`)
    }
  } catch (error) {
    console.error('Failed to load industries:', error)
    alert(`載入${dataSource.value === 'twse' ? '產業' : '產業鏈'}列表時發生錯誤`)
  } finally {
    loading.value = false
  }
}

async function syncFinmindData() {
  if (syncing.value) return

  syncing.value = true
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(
      `${config.public.apiBase}/api/v1/industry-chain/sync`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    if (response.ok) {
      const result = await response.json()

      // 檢查後端返回的狀態
      if (result.status === 'error') {
        // FinMind API 呼叫失敗
        alert(`❌ 同步失敗\n\n${result.message}\n\n新增產業鏈：${result.chains_added}\n新增股票關聯：${result.stocks_added}`)
      } else if (result.status === 'warning') {
        // FinMind API 返回空數據
        alert(`⚠️  同步警告\n\n${result.message}\n\n新增產業鏈：${result.chains_added}\n新增股票關聯：${result.stocks_added}`)
      } else {
        // 同步成功
        alert(`✅ 同步成功！\n\n新增 ${result.chains_added} 個產業鏈\n新增 ${result.stocks_added} 個股票關聯`)
        await loadStatistics()
        await loadIndustries()
      }
    } else {
      const error = await response.json()
      alert(`同步失敗：${error.message || error.detail || '未知錯誤'}`)
    }
  } catch (error) {
    console.error('Failed to sync FinMind data:', error)
    alert('同步數據時發生錯誤')
  } finally {
    syncing.value = false
  }
}

function filterByKeyword() {
  // FinMind 搜尋會在 computed 中處理
}

async function loadIndustryTree() {
  await loadIndustries()
}

function filterByLevel() {
  loadIndustries()
}

function selectIndustry(industry: any) {
  selectedIndustry.value = industry
  industryStocks.value = []
  industryMetrics.value = null
}

async function loadIndustryStocks() {
  if (!selectedIndustry.value) return

  loadingStocks.value = true
  try {
    const token = localStorage.getItem('access_token')
    let url = ''

    if (dataSource.value === 'twse') {
      url = `${config.public.apiBase}/api/v1/industry/${selectedIndustry.value.code}/stocks`
    } else {
      url = `${config.public.apiBase}/api/v1/industry-chain/${selectedIndustry.value.chain_name}/stocks`
    }

    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.ok) {
      const data = await response.json()
      if (dataSource.value === 'twse') {
        industryStocks.value = data.stocks || []
      } else {
        industryStocks.value = data || []
      }
    } else if (response.status === 401) {
      alert('登入已過期，請重新登入')
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      router.push('/login')
    } else {
      alert('載入股票列表失敗')
    }
  } catch (error) {
    console.error('Failed to load stocks:', error)
    alert('載入股票列表時發生錯誤')
  } finally {
    loadingStocks.value = false
  }
}

async function loadIndustryMetrics() {
  if (!selectedIndustry.value) return

  loadingMetrics.value = true
  radarChartLoaded.value = false
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(
      `${config.public.apiBase}/api/v1/industry/${selectedIndustry.value.code}/metrics`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    if (response.ok) {
      industryMetrics.value = await response.json()

      // Auto-render Sparklines after metrics loaded
      setTimeout(() => {
        renderSparklines()
      }, 100)
    } else if (response.status === 401) {
      alert('登入已過期，請重新登入')
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      router.push('/login')
    } else {
      alert('計算指標失敗')
    }
  } catch (error) {
    console.error('Failed to calculate metrics:', error)
    alert('計算指標時發生錯誤')
  } finally {
    loadingMetrics.value = false
  }
}

// Load and render radar chart
async function loadRadarChart() {
  if (!process.client || !industryMetrics.value) return

  try {
    // Dynamically load ECharts
    if (!window.echarts) {
      const script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'
      script.onload = () => {
        initRadarChart()
      }
      document.head.appendChild(script)
    } else {
      initRadarChart()
    }
  } catch (error) {
    console.error('Failed to load radar chart:', error)
    alert('載入雷達圖失敗')
  }
}

function initRadarChart() {
  if (!window.echarts || !industryMetrics.value) return

  const chartDom = document.getElementById('radarChart')
  if (!chartDom) return

  radarChartInstance = window.echarts.init(chartDom)

  // Prepare data for radar chart
  const metrics = industryMetrics.value.metrics

  // Define indicator names with default max values (as fallback)
  const indicatorNames = [
    { name: 'ROE稅後', defaultMax: INDICATOR_DEFAULTS.ROE稅後 },
    { name: 'ROA稅後息前', defaultMax: INDICATOR_DEFAULTS.ROA稅後息前 },
    { name: '營業毛利率', defaultMax: INDICATOR_DEFAULTS.營業毛利率 },
    { name: '營業利益率', defaultMax: INDICATOR_DEFAULTS.營業利益率 },
    { name: '每股稅後淨利', defaultMax: INDICATOR_DEFAULTS.每股稅後淨利 },
    { name: '營收成長率', defaultMax: INDICATOR_DEFAULTS.營收成長率 },
    { name: '稅後淨利成長率', defaultMax: INDICATOR_DEFAULTS.稅後淨利成長率 }
  ]

  // Calculate values and dynamic max for each indicator
  const values = indicatorNames.map(ind => {
    const metricData = metrics[ind.name]
    return metricData ? metricData.average : 0
  })

  // Calculate dynamic min/max values for each indicator
  const indicators = indicatorNames.map((ind, index) => {
    const value = values[index]
    const metricData = metrics[ind.name]

    // Collect all values for this indicator (current, previous, trend)
    const allValues = [value]
    if (metricData?.previous_value !== null && metricData?.previous_value !== undefined) {
      allValues.push(metricData.previous_value)
    }
    if (metricData?.trend_data) {
      allValues.push(...metricData.trend_data.filter((v: number | null) => v !== null))
    }

    // Calculate min and max from all collected values
    let dataMin = Math.min(...allValues)
    let dataMax = Math.max(...allValues)

    // For growth rates, ensure we can show both positive and negative
    const isGrowthRate = ind.name.includes('成長率')

    // Add padding to min/max
    const range = dataMax - dataMin
    const padding = range * RADAR_CONFIG.PADDING_MULTIPLIER

    let min = dataMin - padding
    let max = dataMax + padding

    // For non-growth metrics (which should always be >= 0), set min to 0
    if (!isGrowthRate && min > 0) {
      min = 0
    }

    // Ensure minimum range for readability
    if (Math.abs(max - min) < ind.defaultMax * RADAR_CONFIG.MIN_RANGE_MULTIPLIER) {
      const center = (max + min) / 2
      const halfRange = ind.defaultMax * RADAR_CONFIG.HALF_RANGE_MULTIPLIER
      min = center - halfRange
      max = center + halfRange
    }

    // Round to nice numbers
    const roundValue = (val: number, isMax: boolean) => {
      const absVal = Math.abs(val)
      let rounded: number

      if (absVal > NUMBER_FORMATS.THRESHOLD_HUNDREDS) {
        rounded = Math[isMax ? 'ceil' : 'floor'](val / NUMBER_FORMATS.ROUNDING_LARGE) * NUMBER_FORMATS.ROUNDING_LARGE
      } else if (absVal > NUMBER_FORMATS.THRESHOLD_TENS) {
        rounded = Math[isMax ? 'ceil' : 'floor'](val / NUMBER_FORMATS.ROUNDING_MEDIUM) * NUMBER_FORMATS.ROUNDING_MEDIUM
      } else if (absVal > NUMBER_FORMATS.THRESHOLD_ONES) {
        rounded = Math[isMax ? 'ceil' : 'floor'](val)
      } else {
        rounded = Math[isMax ? 'ceil' : 'floor'](val * NUMBER_FORMATS.ROUNDING_MEDIUM) / NUMBER_FORMATS.ROUNDING_MEDIUM
      }

      return rounded
    }

    const roundedMin = roundValue(min, false)
    const roundedMax = roundValue(max, true)

    return {
      name: ind.name,
      min: roundedMin,
      max: roundedMax
    }
  })

  const option = {
    title: {
      text: `${selectedIndustry.value.name_zh} 產業健康度`,
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const dataIndex = params.dataIndex
        const indicator = indicators[dataIndex]
        const value = values[dataIndex]
        const metricData = metrics[indicator.name]

        let html = `<strong>${indicator.name}</strong><br/>`
        html += `當前值: <strong>${value.toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_TWO)}</strong><br/>`
        html += `<span style="color: #999; font-size: ${CHART_STYLES.FONT_SIZE_TOOLTIP}px;">範圍: ${indicator.min.toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_ONE)} ~ ${indicator.max.toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_ONE)}</span><br/>`

        if (metricData?.change_percent !== null && metricData?.change_percent !== undefined) {
          const arrow = metricData.change_percent >= 0 ? '↗' : '↘'
          const color = metricData.change_percent >= 0 ? '#22c55e' : '#ef4444'
          html += `<span style="color: ${color}">${arrow} ${Math.abs(metricData.change_percent).toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_ONE)}% vs 上季</span><br/>`
        }

        if (metricData?.sample_size) {
          html += `<span style="color: #999; font-size: ${CHART_STYLES.FONT_SIZE_TOOLTIP}px;">樣本數: ${metricData.sample_size}</span>`
        }

        return html
      }
    },
    radar: {
      indicator: indicators,
      radius: CHART_DIMENSIONS.RADAR_RADIUS,
      splitNumber: CHART_DIMENSIONS.RADAR_SPLIT_NUMBER,
      axisName: {
        color: '#666',
        fontSize: CHART_STYLES.FONT_SIZE_AXIS
      },
      axisLabel: {
        show: true,
        fontSize: CHART_STYLES.FONT_SIZE_MEDIUM,
        color: '#999',
        formatter: (value: number, index: number) => {
          // Format large numbers with K/M suffix
          if (Math.abs(value) >= NUMBER_FORMATS.THRESHOLD_THOUSANDS) {
            return (value / NUMBER_FORMATS.THRESHOLD_THOUSANDS).toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_NONE) + 'K'
          } else if (Math.abs(value) >= NUMBER_FORMATS.THRESHOLD_HUNDREDS) {
            return value.toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_NONE)
          } else if (Math.abs(value) >= NUMBER_FORMATS.THRESHOLD_TENS) {
            return value.toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_NONE)
          } else {
            return value.toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_ONE)
          }
        }
      },
      splitLine: {
        lineStyle: {
          color: ['#e5e7eb', '#e5e7eb', '#e5e7eb', '#e5e7eb', '#e5e7eb'].reverse()
        }
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['rgba(99, 102, 241, 0.03)', 'rgba(99, 102, 241, 0.06)', 'rgba(99, 102, 241, 0.09)']
        }
      }
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: values,
            name: selectedIndustry.value.name_zh,
            areaStyle: {
              color: 'rgba(99, 102, 241, 0.3)'
            },
            lineStyle: {
              color: '#6366f1',
              width: 2
            },
            itemStyle: {
              color: '#6366f1'
            }
          }
        ]
      }
    ]
  }

  radarChartInstance.setOption(option)
  radarChartLoaded.value = true

  // Handle resize - remove old listener first to prevent memory leak
  if (radarResizeHandler) {
    window.removeEventListener('resize', radarResizeHandler)
  }
  radarResizeHandler = () => radarChartInstance?.resize()
  window.addEventListener('resize', radarResizeHandler)

  // Initial resize to ensure correct size
  setTimeout(() => {
    radarChartInstance?.resize()
  }, TIMING.CHART_RESIZE_DELAY)
}

// Render sparklines for each metric
function renderSparklines() {
  if (!industryMetrics.value) return

  const metrics = industryMetrics.value.metrics

  Object.keys(metrics).forEach(metricName => {
    const metricData = metrics[metricName]
    if (!metricData.trend_data || metricData.trend_data.length === 0) return

    const svgId = `sparkline-${metricName}`
    const svg = document.getElementById(svgId)
    if (!svg) return

    // Filter out null values and get valid data points
    const data = metricData.trend_data.filter((v: number | null) => v !== null).reverse()
    if (data.length === 0) return

    // Calculate dimensions based on data points
    const maxWidth = svg.clientWidth || CHART_DIMENSIONS.DEFAULT_MAX_WIDTH
    const dataPointWidth = CHART_DIMENSIONS.DATA_POINT_WIDTH
    const minWidth = CHART_DIMENSIONS.MIN_WIDTH
    const calculatedWidth = Math.max(minWidth, Math.min(maxWidth, data.length * dataPointWidth))

    const height = CHART_DIMENSIONS.SPARKLINE_HEIGHT
    const padding = CHART_PADDING.SPARKLINE
    const chartHeight = height - padding.top - padding.bottom
    const chartWidth = calculatedWidth - padding.left - padding.right

    const max = Math.max(...data)
    const min = Math.min(...data)
    const range = max - min || 1

    // Generate path
    const points = data.map((value: number, index: number) => {
      const x = padding.left + (chartWidth / (data.length - 1 || 1)) * index
      const y = padding.top + chartHeight - ((value - min) / range) * chartHeight
      return `${x},${y}`
    }).join(' ')

    const pathD = `M ${points.split(' ').join(' L ')}`

    // Format number for display
    const formatNum = (num: number) => {
      if (Math.abs(num) >= NUMBER_FORMATS.THRESHOLD_THOUSANDS) {
        return (num / NUMBER_FORMATS.THRESHOLD_THOUSANDS).toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_ONE) + 'K'
      }
      if (Math.abs(num) >= NUMBER_FORMATS.THRESHOLD_HUNDREDS) {
        return num.toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_NONE)
      }
      if (Math.abs(num) >= NUMBER_FORMATS.THRESHOLD_ONES) {
        return num.toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_ONE)
      }
      return num.toFixed(NUMBER_FORMATS.DECIMAL_PRECISION_TWO)
    }

    // Set SVG width
    svg.setAttribute('width', calculatedWidth.toString())
    svg.setAttribute('height', height.toString())

    // Draw chart with axes and labels
    svg.innerHTML = `
      <!-- Horizontal grid line -->
      <line
        x1="${padding.left}"
        y1="${padding.top + chartHeight / 2}"
        x2="${padding.left + chartWidth}"
        y2="${padding.top + chartHeight / 2}"
        stroke="#e5e7eb"
        stroke-width="${CHART_STYLES.STROKE_WIDTH_THIN}"
        stroke-dasharray="2,2"
      />

      <!-- Main trend line -->
      <path
        d="${pathD}"
        fill="none"
        stroke="#6366f1"
        stroke-width="${CHART_STYLES.STROKE_WIDTH_THICK}"
        stroke-linecap="round"
        stroke-linejoin="round"
      />

      <!-- Data points -->
      ${data.map((value: number, index: number) => {
        const x = padding.left + (chartWidth / (data.length - 1 || 1)) * index
        const y = padding.top + chartHeight - ((value - min) / range) * chartHeight
        return `<circle cx="${x}" cy="${y}" r="${CHART_STYLES.DATA_POINT_RADIUS}" fill="#6366f1" />`
      }).join('')}

      <!-- Y-axis labels -->
      <text
        x="${calculatedWidth - CHART_PADDING.LABEL_OFFSET_X}"
        y="${padding.top + CHART_PADDING.LABEL_OFFSET_Y}"
        text-anchor="end"
        font-size="${CHART_STYLES.FONT_SIZE_SMALL}"
        fill="#999"
      >${formatNum(max)}</text>

      <text
        x="${calculatedWidth - CHART_PADDING.LABEL_OFFSET_X}"
        y="${height - padding.bottom + CHART_PADDING.LABEL_OFFSET_Y}"
        text-anchor="end"
        font-size="${CHART_STYLES.FONT_SIZE_SMALL}"
        fill="#999"
      >${formatNum(min)}</text>

      <!-- X-axis labels (first and last) -->
      <text
        x="${padding.left}"
        y="${height - CHART_PADDING.LABEL_OFFSET_X}"
        text-anchor="start"
        font-size="${CHART_STYLES.FONT_SIZE_SMALL}"
        fill="#999"
      >最舊</text>

      <text
        x="${padding.left + chartWidth}"
        y="${height - CHART_PADDING.LABEL_OFFSET_X}"
        text-anchor="end"
        font-size="${CHART_STYLES.FONT_SIZE_SMALL}"
        fill="#999"
      >最新</text>
    `
  })
}

// Get color class based on metric value
function getMetricColorClass(metricName: string, value: number): string {
  const threshold = METRIC_THRESHOLDS[metricName as keyof typeof METRIC_THRESHOLDS]
  if (!threshold) return ''

  if (value >= threshold.good) return 'metric-good'
  if (value >= threshold.ok) return 'metric-ok'
  return 'metric-poor'
}

// Load and render trend chart
async function loadTrendChart() {
  if (!selectedIndustry.value || !selectedTrendMetric.value) return

  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(
      `${config.public.apiBase}/api/v1/industry/${selectedIndustry.value.code}/metrics/historical?metric_name=${encodeURIComponent(selectedTrendMetric.value)}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    if (response.ok) {
      trendChartData.value = await response.json()

      // Ensure ECharts is loaded
      if (!window.echarts) {
        const script = document.createElement('script')
        script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'
        script.onload = () => {
          initTrendChart()
        }
        document.head.appendChild(script)
      } else {
        initTrendChart()
      }
    } else if (response.status === 401) {
      alert('登入已過期，請重新登入')
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      router.push('/login')
    } else {
      alert('載入歷史數據失敗')
    }
  } catch (error) {
    console.error('Failed to load trend data:', error)
    alert('載入歷史數據時發生錯誤')
  }
}

function initTrendChart() {
  if (!window.echarts || !trendChartData.value) return

  const chartDom = document.getElementById('trendChart')
  if (!chartDom) return

  // Destroy previous instance if exists
  if (trendChartInstance) {
    trendChartInstance.dispose()
  }

  trendChartInstance = window.echarts.init(chartDom)

  // Prepare data (backend already returns in chronological order: oldest to newest)
  const data = trendChartData.value.data || []
  const dates = data.map((d: any) => d.date)
  const values = data.map((d: any) => d.value)

  const option = {
    title: {
      text: `${selectedIndustry.value.name_zh} - ${selectedTrendMetric.value} 歷史趨勢`,
      left: 'center',
      textStyle: {
        fontSize: 16
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const param = params[0]
        return `${param.axisValue}<br/>${selectedTrendMetric.value}: <strong>${param.value?.toFixed(2) || 'N/A'}</strong>`
      }
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
        rotate: 45,
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      name: selectedTrendMetric.value,
      axisLabel: {
        formatter: (value: number) => value.toFixed(1)
      }
    },
    series: [
      {
        name: selectedTrendMetric.value,
        type: 'line',
        data: values,
        smooth: true,
        lineStyle: {
          color: '#3b82f6',
          width: 3
        },
        itemStyle: {
          color: '#3b82f6'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
              { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
            ]
          }
        },
        markLine: {
          silent: true,
          lineStyle: {
            color: '#ef4444',
            type: 'dashed'
          },
          data: [
            { type: 'average', name: '平均值' }
          ]
        }
      }
    ]
  }

  trendChartInstance.setOption(option)

  // Handle resize - remove old listener first to prevent memory leak
  if (trendResizeHandler) {
    window.removeEventListener('resize', trendResizeHandler)
  }
  trendResizeHandler = () => trendChartInstance?.resize()
  window.addEventListener('resize', trendResizeHandler)

  setTimeout(() => {
    trendChartInstance?.resize()
  }, 100)
}

// Industry Comparison Methods
function addComparisonIndustry() {
  if (!selectedComparisonIndustry.value || comparisonIndustries.value.length >= 5) return

  const industry = industries.value.find(i => i.code === selectedComparisonIndustry.value)
  if (industry && !comparisonIndustries.value.some(c => c.code === industry.code)) {
    comparisonIndustries.value.push({
      code: industry.code,
      name: industry.name_zh
    })
  }

  selectedComparisonIndustry.value = ''
}

function removeComparisonIndustry(code: string) {
  comparisonIndustries.value = comparisonIndustries.value.filter(i => i.code !== code)
  if (comparisonIndustries.value.length < 2) {
    comparisonChartData.value = null
    if (comparisonChartInstance) {
      comparisonChartInstance.dispose()
      comparisonChartInstance = null
    }
  }
}

async function loadComparisonChart() {
  if (comparisonIndustries.value.length < 2) {
    alert('請選擇至少 2 個產業進行對比')
    return
  }

  try {
    const token = localStorage.getItem('access_token')
    const codes = comparisonIndustries.value.map(i => i.code)
    const queryParams = codes.map(code => `industry_codes=${code}`).join('&')

    const response = await fetch(
      `${config.public.apiBase}/api/v1/industry/compare?${queryParams}&metric_name=${comparisonMetric.value}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    )

    if (response.ok) {
      comparisonChartData.value = await response.json()

      // Ensure ECharts is loaded
      if (!window.echarts) {
        const script = document.createElement('script')
        script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'
        script.onload = () => {
          initComparisonChart()
        }
        document.head.appendChild(script)
      } else {
        initComparisonChart()
      }
    } else if (response.status === 401) {
      alert('登入已過期，請重新登入')
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      router.push('/login')
    } else {
      alert('載入對比數據失敗')
    }
  } catch (error) {
    console.error('Failed to load comparison data:', error)
    alert('載入對比數據時發生錯誤')
  }
}

function initComparisonChart() {
  if (!window.echarts || !comparisonChartData.value) return

  const chartDom = document.getElementById('comparisonChart')
  if (!chartDom) return

  // Destroy previous instance if exists
  if (comparisonChartInstance) {
    comparisonChartInstance.dispose()
  }

  comparisonChartInstance = window.echarts.init(chartDom)

  // Prepare data
  const data = comparisonChartData.value.industries || []
  const industryNames = data.map((d: any) => d.industry_name)
  const values = data.map((d: any) => d.value || 0)

  // Color by value (green = good, yellow = ok, red = poor)
  const colors = values.map((value: number) => {
    if (value >= 15) return '#22c55e'  // Green
    if (value >= 8) return '#eab308'   // Yellow
    return '#ef4444'  // Red
  })

  const option = {
    title: {
      text: `產業對比 - ${comparisonMetric.value}`,
      subtext: `數據日期: ${comparisonChartData.value.date}`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const param = params[0]
        const industryData = data[param.dataIndex]
        return `<strong>${param.name}</strong><br/>${comparisonMetric.value}: ${param.value?.toFixed(2) || 'N/A'}<br/>樣本數: ${industryData.sample_size}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: industryNames,
      axisLabel: {
        rotate: 30,
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      name: comparisonMetric.value,
      axisLabel: {
        formatter: (value: number) => value.toFixed(1)
      }
    },
    series: [
      {
        name: comparisonMetric.value,
        type: 'bar',
        data: values.map((value: number, index: number) => ({
          value: value,
          itemStyle: {
            color: colors[index]
          }
        })),
        label: {
          show: true,
          position: 'top',
          formatter: (params: any) => params.value?.toFixed(2) || 'N/A',
          fontSize: 12
        },
        barWidth: '60%'
      }
    ]
  }

  comparisonChartInstance.setOption(option)

  // Handle resize - remove old listener first to prevent memory leak
  if (comparisonResizeHandler) {
    window.removeEventListener('resize', comparisonResizeHandler)
  }
  comparisonResizeHandler = () => comparisonChartInstance?.resize()
  window.addEventListener('resize', comparisonResizeHandler)

  setTimeout(() => {
    comparisonChartInstance?.resize()
  }, 100)
}

function viewStock(stockId: string) {
  router.push(`/data?stock=${stockId}`)
}

// Lifecycle
onMounted(() => {
  loadUserInfo()
  loadStatistics()
  loadIndustries()
})

// Cleanup event listeners on component unmount
onUnmounted(() => {
  if (radarResizeHandler) {
    window.removeEventListener('resize', radarResizeHandler)
    radarResizeHandler = null
  }
  if (trendResizeHandler) {
    window.removeEventListener('resize', trendResizeHandler)
    trendResizeHandler = null
  }
  if (comparisonResizeHandler) {
    window.removeEventListener('resize', comparisonResizeHandler)
    comparisonResizeHandler = null
  }

  // Dispose chart instances
  if (radarChartInstance) {
    radarChartInstance.dispose()
    radarChartInstance = null
  }
  if (trendChartInstance) {
    trendChartInstance.dispose()
    trendChartInstance = null
  }
  if (comparisonChartInstance) {
    comparisonChartInstance.dispose()
    comparisonChartInstance = null
  }
})
</script>

<style scoped lang="scss">
/* Dashboard Layout */
.dashboard-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
}

.dashboard-main {
  flex: 1;
  max-width: 1536px;
  width: 100%;
  margin: 0 auto;
}

.industry-page {
  background: #f9fafb;
}

/* Industry List Header */
.industry-list-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.125rem;
  font-weight: 700;
  color: #111827;

  .title-icon {
    font-size: 1.5rem;
  }
}

.reload-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);

  .reload-icon {
    font-size: 1rem;
    display: inline-block;
    transition: transform 0.3s ease;
  }

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
    transform: translateY(-1px);

    .reload-icon {
      transform: rotate(180deg);
    }
  }

  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
    box-shadow: none;

    .reload-icon {
      animation: spin 1s linear infinite;
    }
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.industry-count-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  border: 1px solid #93c5fd;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  color: #1e40af;

  .badge-icon {
    font-size: 1rem;
  }

  strong {
    font-weight: 700;
    color: #1e3a8a;
  }
}

.filter-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.5rem;
}

.level-select {
  width: 100%;
  padding: 0.75rem 1rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  font-size: 0.9375rem;
  font-weight: 500;
  color: #111827;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

  &:hover {
    border-color: #3b82f6;
    box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
  }

  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  option {
    padding: 0.5rem;
    font-weight: 500;
  }
}

/* Industry Info Cards */
.info-cards-container {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.info-card {
  flex: 0 1 auto;
  min-width: 180px;
  max-width: 220px;
  padding: 1rem;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 2px solid #e2e8f0;
  border-radius: 0.75rem;
  transition: all 0.2s ease;

  &:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
    transform: translateY(-2px);
  }

  .info-label {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.5rem;

    .info-icon {
      font-size: 1rem;
    }
  }

  .info-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1e293b;
    line-height: 1.2;
  }
}

/* Load Stocks Button */
.load-stocks-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(59, 130, 246, 0.25);

  .btn-icon {
    font-size: 1.25rem;
    transition: transform 0.3s ease;
  }

  .btn-text {
    font-weight: 600;
  }

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    box-shadow: 0 6px 12px rgba(59, 130, 246, 0.35);
    transform: translateY(-2px);

    .btn-icon {
      transform: scale(1.1);
    }
  }

  &:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
  }

  &:disabled {
    background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%);
    cursor: not-allowed;
    box-shadow: none;

    .btn-icon {
      animation: pulse 1.5s ease-in-out infinite;
    }
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.1);
  }
}

/* Tabs */
.tabs-container {
  display: flex;
  gap: 0.5rem;
  background: white;
  padding: 0.5rem;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #f3f4f6;
    color: #374151;
  }

  &.active {
    background: #2563eb;
    color: white;
    box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.3);
  }
}

.tab-icon {
  font-size: 1.25rem;
}

/* Industry Grid Layout */
.industry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
}

/* Compact Industry Card */
.industry-card-compact {
  padding: 0.875rem;
  border-radius: 0.75rem;
  border: 2px solid;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.industry-card-compact:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
}

.industry-card-compact:active {
  transform: scale(0.97);
}

.industry-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 0.5rem;
  line-height: 1.3;
  min-height: 2.6rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.industry-count {
  font-size: 0.75rem;
  font-weight: 500;
  color: #6b7280;
  padding: 0.25rem 0.5rem;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 0.375rem;
  display: inline-block;
}

/* Level 1 - 大類產業 (藍色系) */
.industry-card-compact.level-1 {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #bfdbfe;
}

.industry-card-compact.level-1:hover {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  border-color: #93c5fd;
}

/* Level 2 - 中類產業 (紫色系) */
.industry-card-compact.level-2 {
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border-color: #e9d5ff;
}

.industry-card-compact.level-2:hover {
  background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%);
  border-color: #d8b4fe;
}

/* Level 3 - 小類產業 (橙色系) */
.industry-card-compact.level-3 {
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
  border-color: #fed7aa;
}

.industry-card-compact.level-3:hover {
  background: linear-gradient(135deg, #ffedd5 0%, #fed7aa 100%);
  border-color: #fdba74;
}

/* FinMind Cards (天藍色系) */
.industry-card-compact.finmind {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-color: #bae6fd;
}

.industry-card-compact.finmind:hover {
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
  border-color: #7dd3fc;
}

/* Selected State */
.industry-card-compact.selected {
  border-color: #3b82f6 !important;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(147, 51, 234, 0.2) 100%) !important;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
}

.industry-card-compact.selected .industry-name {
  color: #1e40af;
  font-weight: 700;
}

.industry-card-compact.selected .industry-count {
  background: #3b82f6;
  color: white;
}

/* SVG Icon Size Constraints */
svg.w-3 {
  width: 0.75rem !important;
  height: 0.75rem !important;
  flex-shrink: 0;
}

svg.w-4 {
  width: 1rem !important;
  height: 1rem !important;
  flex-shrink: 0;
}

svg.w-16 {
  width: 4rem !important;
  height: 4rem !important;
  flex-shrink: 0;
}

/* ========== Enhanced Metrics Info Card ========== */
.metrics-info-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border: 2px solid #e2e8f0;
  border-radius: 1rem;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.metrics-info-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

/* Card Header */
.info-card-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e2e8f0;
}

.header-icon {
  font-size: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-radius: 0.75rem;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  animation: pulse-icon 2s ease-in-out infinite;
}

@keyframes pulse-icon {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
  }
}

.header-text {
  flex: 1;
}

.header-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.025em;
  line-height: 1.2;
}

.header-subtitle {
  font-size: 0.75rem;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 0.25rem;
}

/* Stats Grid */
.info-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

@media (max-width: 1024px) {
  .info-stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .info-stats-grid {
    grid-template-columns: 1fr;
  }
}

/* Individual Stat Item */
.info-stat-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 0.75rem;
  border: 2px solid;
  transition: all 0.3s ease;
  overflow: hidden;
}

.info-stat-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.info-stat-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}

.info-stat-item:hover::before {
  opacity: 0.05;
}

/* Stat Item - Date (藍色主題) */
.info-stat-item.date {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #93c5fd;
}

.info-stat-item.date::before {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
}

.info-stat-item.date .stat-icon-wrapper {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.25);
}

/* Stat Item - Stocks (綠色主題) */
.info-stat-item.stocks {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border-color: #86efac;
}

.info-stat-item.stocks::before {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
}

.info-stat-item.stocks .stat-icon-wrapper {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  box-shadow: 0 4px 8px rgba(34, 197, 94, 0.25);
}

/* Stat Item - Samples (紫色主題) */
.info-stat-item.samples {
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border-color: #c084fc;
}

.info-stat-item.samples::before {
  background: linear-gradient(135deg, #a855f7 0%, #9333ea 100%);
}

.info-stat-item.samples .stat-icon-wrapper {
  background: linear-gradient(135deg, #a855f7 0%, #9333ea 100%);
  box-shadow: 0 4px 8px rgba(168, 85, 247, 0.25);
}

/* Stat Item - Coverage (橙色主題) */
.info-stat-item.coverage {
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
  border-color: #fdba74;
}

.info-stat-item.coverage::before {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
}

.info-stat-item.coverage .stat-icon-wrapper {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  box-shadow: 0 4px 8px rgba(249, 115, 22, 0.25);
}

/* Icon Wrapper */
.stat-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.625rem;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.info-stat-item:hover .stat-icon-wrapper {
  transform: scale(1.1) rotate(5deg);
}

.stat-icon {
  font-size: 1.25rem;
  line-height: 1;
}

/* Stat Content */
.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 0.6875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
  line-height: 1.2;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.2;
  margin-bottom: 0.125rem;
}

.stat-desc {
  font-size: 0.625rem;
  font-weight: 500;
  color: #94a3b8;
  line-height: 1.2;
}

/* ========== End Enhanced Metrics Info Card ========== */

/* Enhanced Metric Cards */
.metric-card {
  padding: 1rem;
  border-radius: 0.5rem;
  transition: all 0.3s;
  border: 2px solid transparent;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* Color Coding */
.metric-good {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border-color: #86efac;
}

.metric-good .text-2xl {
  color: #16a34a;
}

.metric-ok {
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border-color: #fde047;
}

.metric-ok .text-2xl {
  color: #ca8a04;
}

.metric-poor {
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border-color: #fca5a5;
}

.metric-poor .text-2xl {
  color: #dc2626;
}

/* Change Badge */
.change-badge {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.change-badge.positive {
  background: #dcfce7;
  color: #16a34a;
}

.change-badge.negative {
  background: #fee2e2;
  color: #dc2626;
}

.change-badge .arrow {
  font-size: 1rem;
  line-height: 1;
}

.change-badge .percent {
  font-weight: 700;
}

/* Sparkline Container */
/* Note: Height values should match CHART_DIMENSIONS.SPARKLINE_HEIGHT (60px) and MIN_WIDTH (100px) */
.sparkline-container {
  margin-top: 0.5rem;
  height: 60px; /* Must match CHART_DIMENSIONS.SPARKLINE_HEIGHT */
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
}

.sparkline {
  display: block;
  height: 60px; /* Must match CHART_DIMENSIONS.SPARKLINE_HEIGHT */
  min-width: 100px; /* Must match CHART_DIMENSIONS.MIN_WIDTH */
}

/* Custom scrollbar */
.overflow-y-auto::-webkit-scrollbar {
  width: 8px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #a78bfa 0%, #8b5cf6 100%);
  border-radius: 4px;
}

/* Stock Grid Layout */
.stock-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 0.75rem;
}

.stock-card {
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 2px solid #bae6fd;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  min-height: 70px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.25rem;
}

.stock-card:hover {
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
  border-color: #7dd3fc;
  transform: translateY(-3px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
}

.stock-card:active {
  transform: scale(0.97);
}

.stock-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e40af;
  line-height: 1.3;
}

.stock-code {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 0.75rem;
  font-weight: 500;
  color: #0369a1;
}

/* Statistics Section */
.stats-section {
  margin-bottom: 1.5rem;
}

.stats-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #111827;
}

.stats-subtitle {
  font-size: 0.875rem;
  font-weight: 400;
  color: #6b7280;
  margin-left: 0.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
}

.stat-card {
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  text-align: center;
  transition: all 0.3s;
  border: 2px solid;
}

.stat-card:hover {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.stat-card-blue {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #bfdbfe;
}

.stat-card-green {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border-color: #bbf7d0;
}

.stat-card-purple {
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border-color: #e9d5ff;
}

.stat-card-orange {
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
  border-color: #fed7aa;
}

.stat-number {
  font-size: 2.25rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.stat-card-blue .stat-number {
  color: #2563eb;
}

.stat-card-green .stat-number {
  color: #16a34a;
}

.stat-card-purple .stat-number {
  color: #9333ea;
}

.stat-card-orange .stat-number {
  color: #ea580c;
}

.stat-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #8b5cf6 0%, #7c3aed 100%);
}

/* Smooth animations */
* {
  scroll-behavior: smooth;
}
</style>
