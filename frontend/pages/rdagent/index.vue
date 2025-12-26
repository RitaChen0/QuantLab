<template>
  <div class="rdagent-page">
    <!-- 頂部導航欄 -->
    <AppHeader />

    <div class="page-header">
      <h1>🤖 自動研發</h1>
      <p>使用 AI 自動生成交易因子與優化策略</p>
    </div>

    <div class="tabs">
      <button
        :class="['tab', { active: activeTab === 'factor-mining' }]"
        @click="activeTab = 'factor-mining'"
      >
        因子挖掘
      </button>
      <button
        :class="['tab', { active: activeTab === 'strategy-optimization' }]"
        @click="activeTab = 'strategy-optimization'"
      >
        策略優化
      </button>
      <button
        :class="['tab', { active: activeTab === 'tasks' }]"
        @click="activeTab = 'tasks'"
      >
        任務列表
      </button>
      <button
        :class="['tab', { active: activeTab === 'factors' }]"
        @click="activeTab = 'factors'"
      >
        生成的因子
      </button>
      <button
        :class="['tab', { active: activeTab === 'models' }]"
        @click="activeTab = 'models'"
      >
        生成的模型
      </button>
    </div>

    <!-- 因子挖掘表單 -->
    <div v-if="activeTab === 'factor-mining'" class="section">
      <h2>✨ 自動因子挖掘</h2>
      <form @submit.prevent="submitFactorMining" class="mining-form">
        <div class="form-group">
          <label>研究目標</label>
          <textarea
            v-model="miningForm.research_goal"
            placeholder="例如：尋找能預測未來5日報酬率的動量因子，結合成交量指標..."
            rows="4"
            required
          ></textarea>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>最多生成因子數</label>
            <input type="number" v-model.number="miningForm.max_factors" min="1" max="20" />
          </div>

          <div class="form-group">
            <label>LLM 模型</label>
            <select v-model="miningForm.llm_model">
              <option value="gpt-4">GPT-4</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
              <option value="claude-3-opus">Claude 3 Opus</option>
              <option value="claude-3-sonnet">Claude 3 Sonnet</option>
            </select>
          </div>

          <div class="form-group">
            <label>最大迭代次數</label>
            <input type="number" v-model.number="miningForm.max_iterations" min="1" max="10" />
          </div>
        </div>

        <button type="submit" class="btn-primary" :disabled="isSubmitting">
          {{ isSubmitting ? '提交中...' : '🚀 開始挖掘' }}
        </button>
      </form>
    </div>

    <!-- 策略優化表單 -->
    <div v-if="activeTab === 'strategy-optimization'" class="section">
      <h2>🎯 策略優化</h2>
      <p class="section-description">使用 AI 分析策略代碼和回測結果，提供專業優化建議</p>

      <form @submit.prevent="submitStrategyOptimization" class="optimization-form">
        <!-- 策略選擇 -->
        <div class="form-group">
          <label>
            選擇要優化的策略
            <span class="label-hint">（必須有至少一次完成的回測記錄）</span>
          </label>
          <select v-model.number="optimizationForm.strategy_id" required>
            <option value="">-- 請選擇策略 --</option>
            <option v-for="strategy in strategiesWithBacktests" :key="strategy.id" :value="strategy.id">
              {{ strategy.name }} ({{ strategy.engine_type }}) - 最近回測: {{ formatStrategyBacktestInfo(strategy) }}
            </option>
          </select>
        </div>

        <!-- 當前績效顯示 -->
        <div v-if="selectedStrategyPerformance" class="current-performance-preview">
          <h4>📊 當前績效</h4>
          <div class="metrics-row">
            <div class="metric-item">
              <span class="metric-label">Sharpe Ratio</span>
              <span class="metric-value">{{ formatNumber(selectedStrategyPerformance.sharpe_ratio, 2) }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">年化報酬率</span>
              <span class="metric-value">{{ formatPercent(selectedStrategyPerformance.annual_return) }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">最大回撤</span>
              <span class="metric-value">{{ formatPercent(selectedStrategyPerformance.max_drawdown) }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">勝率</span>
              <span class="metric-value">{{ formatPercent(selectedStrategyPerformance.win_rate) }}</span>
            </div>
          </div>
        </div>

        <!-- 優化目標 -->
        <div class="form-group">
          <label>優化目標</label>
          <textarea
            v-model="optimizationForm.optimization_goal"
            placeholder="例如：提升 Sharpe Ratio 至 2.0 以上，同時降低最大回撤至 15% 以內"
            rows="3"
            required
          ></textarea>
          <p class="field-hint">💡 具體描述您的優化目標，AI 會根據目標提供針對性建議</p>
        </div>

        <!-- 高級選項 -->
        <div class="form-row">
          <div class="form-group">
            <label>LLM 模型</label>
            <select v-model="optimizationForm.llm_model">
              <option value="gpt-4-turbo">GPT-4 Turbo（推薦）</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo（省成本）</option>
            </select>
          </div>

          <div class="form-group">
            <label>分析深度</label>
            <select v-model.number="optimizationForm.max_iterations">
              <option value="1">基礎分析（約 $0.05-0.10）</option>
              <option value="3">深度分析（約 $0.15-0.30）</option>
              <option value="5">完整分析（約 $0.30-0.50）</option>
            </select>
          </div>
        </div>

        <button type="submit" class="btn-primary" :disabled="isSubmitting || !optimizationForm.strategy_id">
          {{ isSubmitting ? '分析中...' : '🔍 開始優化分析' }}
        </button>
      </form>
    </div>

    <!-- 任務列表 -->
    <div v-if="activeTab === 'tasks'" class="section">
      <h2>📋 任務列表</h2>
      <div v-if="tasks.length === 0" class="empty-state">
        尚無任務記錄
      </div>
      <div v-else class="tasks-grid">
        <div v-for="task in tasks" :key="task.id" class="task-card">
          <div class="task-header">
            <span class="task-id">#{{ task.id }}</span>
            <span :class="['status', task.status]">{{ getStatusLabel(task.status) }}</span>
          </div>
          <div class="task-body">
            <p><strong>類型：</strong>{{ getTypeLabel(task.task_type) }}</p>
            <p><strong>創建時間：</strong>{{ formatDate(task.created_at) }}</p>
            <p v-if="task.llm_cost"><strong>LLM 成本：</strong>${{ task.llm_cost.toFixed(2) }}</p>
          </div>
          <div class="task-actions">
            <button @click="viewTaskDetail(task.id)" class="btn-view">查看詳情</button>
            <button @click="deleteTask(task.id)" class="btn-delete">🗑️ 刪除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 生成的因子 -->
    <div v-if="activeTab === 'factors'" class="section">
      <h2>🧬 生成的因子</h2>
      <div v-if="factors.length === 0" class="empty-state">
        尚無生成的因子
      </div>
      <div v-else class="factors-grid">
        <div v-for="factor in factors" :key="factor.id" class="factor-card">
          <div class="factor-header">
            <div v-if="editingFactorId === factor.id" class="factor-name-edit">
              <input
                v-model="editingFactorName"
                type="text"
                class="factor-name-input"
                @keyup.enter="saveFactorName(factor.id)"
                @keyup.esc="cancelEditFactorName"
              />
              <div class="factor-edit-actions">
                <button @click="saveFactorName(factor.id)" class="btn-save">✓</button>
                <button @click="cancelEditFactorName" class="btn-cancel">✕</button>
              </div>
            </div>
            <div v-else class="factor-name-display">
              <h3>{{ factor.name }}</h3>
              <button @click="startEditFactorName(factor)" class="btn-edit-factor">✏️</button>
            </div>
          </div>
          <p class="factor-description">{{ factor.description }}</p>
          <div class="factor-formula">
            <strong>公式：</strong>
            <code>{{ factor.formula }}</code>
          </div>
          <div v-if="factor.ic" class="factor-metrics">
            <span>IC: {{ factor.ic.toFixed(3) }}</span>
            <span v-if="factor.sharpe_ratio">Sharpe: {{ factor.sharpe_ratio.toFixed(2) }}</span>
          </div>
          <div v-if="factor.code" class="factor-code-section">
            <button
              type="button"
              @click="toggleFactorCode(factor.id)"
              class="btn-toggle-code"
            >
              {{ expandedFactors.has(factor.id) ? '隱藏代碼 ▲' : '查看代碼 ▼' }}
            </button>
            <div v-show="expandedFactors.has(factor.id)" class="factor-code">
              <pre><code>{{ factor.code }}</code></pre>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 生成的模型 -->
    <div v-if="activeTab === 'models'" class="section">
      <h2>🧠 生成的模型</h2>
      <div v-if="models.length === 0" class="empty-state">
        尚無生成的模型
      </div>
      <div v-else class="models-grid">
        <div v-for="model in models" :key="model.id" class="model-card">
          <div class="model-header">
            <div class="model-title">
              <h3>{{ model.name }}</h3>
              <span class="model-type-badge">{{ model.model_type }}</span>
            </div>
            <div class="model-meta">
              <span class="model-date">{{ formatDate(model.created_at) }}</span>
            </div>
          </div>

          <p v-if="model.description" class="model-description">{{ model.description }}</p>

          <!-- 評估指標 -->
          <div v-if="model.sharpe_ratio || model.annual_return" class="model-metrics">
            <div v-if="model.sharpe_ratio" class="metric-item">
              <span class="metric-label">Sharpe Ratio</span>
              <span class="metric-value">{{ model.sharpe_ratio.toFixed(2) }}</span>
            </div>
            <div v-if="model.annual_return" class="metric-item">
              <span class="metric-label">年化報酬率</span>
              <span class="metric-value">{{ (model.annual_return * 100).toFixed(2) }}%</span>
            </div>
            <div v-if="model.max_drawdown" class="metric-item">
              <span class="metric-label">最大回撤</span>
              <span class="metric-value">{{ (model.max_drawdown * 100).toFixed(2) }}%</span>
            </div>
          </div>

          <!-- 架構描述 -->
          <div v-if="model.architecture" class="model-architecture">
            <strong>架構：</strong>
            <p>{{ model.architecture }}</p>
          </div>

          <!-- 數學公式 -->
          <div v-if="model.formulation" class="model-formulation">
            <strong>數學公式：</strong>
            <pre><code>{{ model.formulation }}</code></pre>
          </div>

          <!-- 超參數 -->
          <div v-if="model.hyperparameters && Object.keys(model.hyperparameters).length > 0" class="model-hyperparameters">
            <button
              type="button"
              @click="toggleModelSection(model.id, 'hyperparameters')"
              class="btn-toggle-section"
            >
              {{ expandedSections.has(`${model.id}-hyperparameters`) ? '隱藏超參數 ▲' : '查看超參數 ▼' }}
            </button>
            <div v-show="expandedSections.has(`${model.id}-hyperparameters`)" class="section-content">
              <pre><code>{{ JSON.stringify(model.hyperparameters, null, 2) }}</code></pre>
            </div>
          </div>

          <!-- 模型代碼 -->
          <div v-if="model.code" class="model-code-section">
            <button
              type="button"
              @click="toggleModelSection(model.id, 'code')"
              class="btn-toggle-section"
            >
              {{ expandedSections.has(`${model.id}-code`) ? '隱藏代碼 ▲' : '查看代碼 ▼' }}
            </button>
            <div v-show="expandedSections.has(`${model.id}-code`)" class="section-content">
              <pre><code>{{ model.code }}</code></pre>
            </div>
          </div>

          <!-- Qlib 配置 -->
          <div v-if="model.qlib_config && Object.keys(model.qlib_config).length > 0" class="model-qlib-config">
            <button
              type="button"
              @click="toggleModelSection(model.id, 'qlib_config')"
              class="btn-toggle-section"
            >
              {{ expandedSections.has(`${model.id}-qlib_config`) ? '隱藏 Qlib 配置 ▲' : '查看 Qlib 配置 ▼' }}
            </button>
            <div v-show="expandedSections.has(`${model.id}-qlib_config`)" class="section-content">
              <pre><code>{{ JSON.stringify(model.qlib_config, null, 2) }}</code></pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'

const config = useRuntimeConfig()
const router = useRouter()
const { loadUserInfo, memberLevel } = useUserInfo()
const activeTab = ref('factor-mining')
const isSubmitting = ref(false)

const miningForm = ref({
  research_goal: '',
  max_factors: 5,
  llm_model: 'gpt-4',
  max_iterations: 3
})

const optimizationForm = ref({
  strategy_id: '',
  optimization_goal: '提升 Sharpe Ratio 至 2.0 以上，同時降低最大回撤至 15% 以內',
  llm_model: 'gpt-4-turbo',
  max_iterations: 1
})

const tasks = ref([])
const factors = ref([])
const models = ref([])
const strategiesWithBacktests = ref([])
const expandedFactors = ref(new Set())
const expandedSections = ref(new Set())
const editingFactorId = ref(null)
const editingFactorName = ref('')

// 選中策略的當前績效
const selectedStrategyPerformance = computed(() => {
  if (!optimizationForm.value.strategy_id) return null

  const strategy = strategiesWithBacktests.value.find(
    s => s.id === optimizationForm.value.strategy_id
  )

  if (!strategy || !strategy.latest_backtest_result) return null

  return strategy.latest_backtest_result
})

// 切換因子代碼顯示
const toggleFactorCode = (factorId: number) => {
  if (expandedFactors.value.has(factorId)) {
    expandedFactors.value.delete(factorId)
  } else {
    expandedFactors.value.add(factorId)
  }
  // 強制更新視圖
  expandedFactors.value = new Set(expandedFactors.value)
}

// 開始編輯因子名稱
const startEditFactorName = (factor: any) => {
  editingFactorId.value = factor.id
  editingFactorName.value = factor.name
}

// 取消編輯因子名稱
const cancelEditFactorName = () => {
  editingFactorId.value = null
  editingFactorName.value = ''
}

// 儲存因子名稱
const saveFactorName = async (factorId: number) => {
  if (!editingFactorName.value.trim()) {
    alert('因子名稱不能為空')
    return
  }

  try {
    const token = localStorage.getItem('access_token')
    await $fetch(`${config.public.apiBase}/api/v1/rdagent/factors/${factorId}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: {
        name: editingFactorName.value
      }
    })

    // 更新成功，刷新因子列表
    await loadFactors()
    cancelEditFactorName()
  } catch (error: any) {
    alert('更新失敗：' + (error.data?.detail || error.message))
  }
}

// 提交因子挖掘
const submitFactorMining = async () => {
  isSubmitting.value = true
  try {
    const token = localStorage.getItem('access_token')  // ✅ 修正：使用正確的 key
    const response = await $fetch(`${config.public.apiBase}/api/v1/rdagent/factor-mining`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: miningForm.value
    })

    alert('因子挖掘任務已提交！任務 ID: ' + response.id)
    activeTab.value = 'tasks'
    loadTasks()
  } catch (error: any) {
    alert('提交失敗：' + (error.data?.detail || error.message))
  } finally {
    isSubmitting.value = false
  }
}

// 提交策略優化
const submitStrategyOptimization = async () => {
  if (!optimizationForm.value.strategy_id) {
    alert('請選擇要優化的策略')
    return
  }

  isSubmitting.value = true
  try {
    const token = localStorage.getItem('access_token')
    const response = await $fetch(`${config.public.apiBase}/api/v1/rdagent/strategy-optimization`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: optimizationForm.value
    })

    alert('策略優化任務已提交！任務 ID: ' + response.id + '\n\n分析通常需要 30-60 秒，請稍後在「任務列表」查看結果。')
    activeTab.value = 'tasks'
    loadTasks()
  } catch (error: any) {
    alert('提交失敗：' + (error.data?.detail || error.message))
  } finally {
    isSubmitting.value = false
  }
}

// 載入有回測記錄的策略列表
const loadStrategiesWithBacktests = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const strategies = await $fetch(`${config.public.apiBase}/api/v1/strategies?limit=100`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    // 為每個策略載入最近的回測結果
    const strategiesWithResults = []
    for (const strategy of strategies) {
      try {
        // 獲取該策略最近的完成回測
        const backtests = await $fetch(
          `${config.public.apiBase}/api/v1/backtests?strategy_id=${strategy.id}&status=COMPLETED&limit=1`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        )

        if (backtests && backtests.length > 0) {
          const backtest = backtests[0]
          strategiesWithResults.push({
            ...strategy,
            latest_backtest_id: backtest.id,
            latest_backtest_result: backtest.result || null,
            latest_backtest_date: backtest.completed_at
          })
        }
      } catch (error) {
        // 忽略單個策略的錯誤
        console.error(`Failed to load backtests for strategy ${strategy.id}:`, error)
      }
    }

    strategiesWithBacktests.value = strategiesWithResults
  } catch (error) {
    console.error('Failed to load strategies:', error)
  }
}

// 格式化策略回測資訊
const formatStrategyBacktestInfo = (strategy: any) => {
  if (!strategy.latest_backtest_result) return '無回測記錄'

  const result = strategy.latest_backtest_result
  const sharpe = result.sharpe_ratio != null ? result.sharpe_ratio.toFixed(2) : 'N/A'
  const returnPct = result.annual_return != null ? (result.annual_return * 100).toFixed(2) + '%' : 'N/A'

  return `Sharpe ${sharpe}, 年化 ${returnPct}`
}

// 格式化數字
const formatNumber = (value: number | null | undefined, decimals: number = 2): string => {
  if (value == null) return 'N/A'
  return value.toFixed(decimals)
}

// 格式化百分比
const formatPercent = (value: number | null | undefined): string => {
  if (value == null) return 'N/A'
  return (value * 100).toFixed(2) + '%'
}

// 載入任務列表
const loadTasks = async () => {
  try {
    const token = localStorage.getItem('access_token')  // ✅ 修正：使用正確的 key
    tasks.value = await $fetch(`${config.public.apiBase}/api/v1/rdagent/tasks`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
  } catch (error) {
    console.error('Failed to load tasks:', error)
  }
}

// 載入因子列表
const loadFactors = async () => {
  try {
    const token = localStorage.getItem('access_token')  // ✅ 修正：使用正確的 key
    factors.value = await $fetch(`${config.public.apiBase}/api/v1/rdagent/factors`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
  } catch (error) {
    console.error('Failed to load factors:', error)
  }
}

// 載入模型列表
const loadModels = async () => {
  try {
    const token = localStorage.getItem('access_token')
    models.value = await $fetch(`${config.public.apiBase}/api/v1/rdagent/models`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
  } catch (error) {
    console.error('Failed to load models:', error)
  }
}

// 切換模型區段顯示
const toggleModelSection = (modelId: number, section: string) => {
  const key = `${modelId}-${section}`
  if (expandedSections.value.has(key)) {
    expandedSections.value.delete(key)
  } else {
    expandedSections.value.add(key)
  }
  // 強制更新視圖
  expandedSections.value = new Set(expandedSections.value)
}

// 查看任務詳情
const viewTaskDetail = (taskId: number) => {
  navigateTo(`/rdagent/tasks/${taskId}`)
}

// 刪除任務
const deleteTask = async (taskId: number) => {
  if (!confirm('確定要刪除此任務嗎？此操作無法復原。')) {
    return
  }

  try {
    const token = localStorage.getItem('access_token')
    await $fetch(`${config.public.apiBase}/api/v1/rdagent/tasks/${taskId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })

    alert('任務已成功刪除')
    loadTasks()  // 重新載入任務列表
  } catch (error: any) {
    alert('刪除失敗：' + (error.data?.detail || error.message))
  }
}

// 格式化日期（使用台灣時區）
const { formatToTaiwanTime } = useDateTime()
const formatDate = (dateStr: string) => {
  return formatToTaiwanTime(dateStr)
}

// 狀態標籤
const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: '等待中',
    running: '執行中',
    completed: '已完成',
    failed: '失敗',
    cancelled: '已取消'
  }
  return labels[status] || status
}

// 類型標籤
const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    factor_mining: '因子挖掘',
    strategy_optimization: '策略優化',
    model_extraction: '模型提取'
  }
  return labels[type] || type
}

onMounted(async () => {
  // 強制刷新用戶資訊（跳過快取，確保獲取最新的會員等級）
  await loadUserInfo(true)

  // 檢查會員等級
  if (memberLevel.value < 1) {
    alert('此功能僅限會員等級 1 以上使用，請聯繫管理員升級您的會員等級。')
    router.push('/dashboard')
    return
  }

  loadTasks()
  loadFactors()
  loadModels()
  loadStrategiesWithBacktests()
})

// 當切換到策略優化標籤時，重新載入策略列表
watch(activeTab, (newTab) => {
  if (newTab === 'strategy-optimization') {
    loadStrategiesWithBacktests()
  }
})
</script>

<style scoped lang="scss">
.rdagent-page {
  min-height: 100vh;
  background: #f9fafb;
}

.page-header {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 2rem 1rem;
}

.page-header {
  margin-bottom: 2rem;

  h1 {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }

  p {
    color: #6b7280;
    font-size: 1rem;
  }
}

.tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  border-bottom: 2px solid #e5e7eb;

  .tab {
    padding: 0.75rem 1.5rem;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    font-size: 1rem;
    font-weight: 500;
    color: #6b7280;
    transition: all 0.2s;

    &.active {
      color: #3b82f6;
      border-bottom-color: #3b82f6;
    }

    &:hover {
      color: #3b82f6;
    }
  }
}

.section {
  background: white;
  border-radius: 0.5rem;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.mining-form {
  .form-group {
    margin-bottom: 1.5rem;

    label {
      display: block;
      font-weight: 500;
      margin-bottom: 0.5rem;
      color: #374151;
    }

    textarea,
    input,
    select {
      width: 100%;
      padding: 0.75rem;
      border: 1px solid #d1d5db;
      border-radius: 0.375rem;
      font-size: 1rem;

      &:focus {
        outline: none;
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
      }
    }

    textarea {
      resize: vertical;
      font-family: inherit;
    }
  }

  .form-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }

  .btn-primary {
    padding: 0.75rem 2rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 0.375rem;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;

    &:hover:not(:disabled) {
      background: #2563eb;
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
}

.tasks-grid,
.factors-grid,
.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.task-card,
.factor-card {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1.5rem;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .factor-header {
    margin-bottom: 1rem;
  }

  .factor-name-display {
    display: flex;
    align-items: center;
    gap: 0.5rem;

    h3 {
      margin: 0;
      flex: 1;
    }

    .btn-edit-factor {
      padding: 0.25rem 0.5rem;
      background: transparent;
      border: none;
      cursor: pointer;
      font-size: 1rem;
      opacity: 0.6;
      transition: opacity 0.2s;

      &:hover {
        opacity: 1;
      }
    }
  }

  .factor-name-edit {
    display: flex;
    gap: 0.5rem;
    align-items: center;

    .factor-name-input {
      flex: 1;
      padding: 0.5rem;
      border: 2px solid #3b82f6;
      border-radius: 0.375rem;
      font-size: 1rem;
      font-weight: 600;

      &:focus {
        outline: none;
        border-color: #2563eb;
      }
    }

    .factor-edit-actions {
      display: flex;
      gap: 0.25rem;

      button {
        padding: 0.5rem 0.75rem;
        border: none;
        border-radius: 0.375rem;
        cursor: pointer;
        font-size: 1rem;
        font-weight: 600;
        transition: all 0.2s;
      }

      .btn-save {
        background: #22c55e;
        color: white;

        &:hover {
          background: #16a34a;
        }
      }

      .btn-cancel {
        background: #ef4444;
        color: white;

        &:hover {
          background: #dc2626;
        }
      }
    }
  }
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;

  .task-id {
    font-weight: 600;
    color: #374151;
  }

  .status {
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;

    &.pending {
      background: #fef3c7;
      color: #92400e;
    }

    &.running {
      background: #dbeafe;
      color: #1e40af;
    }

    &.completed {
      background: #d1fae5;
      color: #065f46;
    }

    &.failed {
      background: #fee2e2;
      color: #991b1b;
    }
  }
}

.task-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-view {
  flex: 1;
  padding: 0.5rem;
  background: #f3f4f6;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;

  &:hover {
    background: #e5e7eb;
  }
}

.btn-delete {
  padding: 0.5rem 1rem;
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
  border-radius: 0.375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #fecaca;
    border-color: #fca5a5;
  }
}

.factor-formula {
  background: #f9fafb;
  padding: 0.75rem;
  border-radius: 0.375rem;
  margin: 0.75rem 0;
  overflow-x: auto;

  strong {
    display: block;
    margin-bottom: 0.5rem;
    color: #374151;
    font-size: 0.875rem;
  }

  code {
    font-family: 'Monaco', 'Courier New', monospace;
    font-size: 0.875rem;
    color: #1f2937;
  }
}

.factor-metrics {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.75rem;
}

.factor-code-section {
  margin-top: 1rem;
}

.btn-toggle-code {
  width: 100%;
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;

  &:hover {
    background: #e5e7eb;
    border-color: #9ca3af;
  }
}

.factor-code {
  margin-top: 0.75rem;
  background: #1f2937;
  border-radius: 0.375rem;
  overflow: hidden;

  pre {
    margin: 0;
    padding: 1rem;
    overflow-x: auto;

    code {
      font-family: 'Monaco', 'Courier New', monospace;
      font-size: 0.8125rem;
      line-height: 1.6;
      color: #e5e7eb;
    }
  }
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #9ca3af;
}

// ========== 模型卡片樣式 ==========
.model-card {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1.5rem;
  background: white;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
}

.model-header {
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #f3f4f6;

  .model-title {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;

    h3 {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 600;
      color: #111827;
      flex: 1;
    }

    .model-type-badge {
      padding: 0.25rem 0.75rem;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.025em;
    }
  }

  .model-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;

    .model-date {
      font-size: 0.875rem;
      color: #6b7280;
    }
  }
}

.model-description {
  color: #4b5563;
  line-height: 1.6;
  margin-bottom: 1rem;
  font-size: 0.95rem;
}

.model-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
  border-radius: 0.5rem;

  .metric-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;

    .metric-label {
      font-size: 0.75rem;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 500;
    }

    .metric-value {
      font-size: 1.25rem;
      font-weight: 700;
      color: #667eea;
    }
  }
}

.model-architecture,
.model-formulation {
  margin-bottom: 1rem;

  strong {
    display: block;
    margin-bottom: 0.5rem;
    color: #374151;
    font-size: 0.875rem;
  }

  p {
    color: #4b5563;
    line-height: 1.6;
    margin: 0;
  }

  pre {
    background: #f9fafb;
    padding: 0.75rem;
    border-radius: 0.375rem;
    overflow-x: auto;
    margin: 0;

    code {
      font-family: 'Monaco', 'Courier New', monospace;
      font-size: 0.875rem;
      color: #1f2937;
    }
  }
}

.model-hyperparameters,
.model-code-section,
.model-qlib-config {
  margin-top: 1rem;
}

.btn-toggle-section {
  width: 100%;
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;

  &:hover {
    background: #e5e7eb;
    border-color: #9ca3af;
  }
}

.section-content {
  margin-top: 0.75rem;
  background: #1f2937;
  border-radius: 0.375rem;
  overflow: hidden;

  pre {
    margin: 0;
    padding: 1rem;
    overflow-x: auto;

    code {
      font-family: 'Monaco', 'Courier New', monospace;
      font-size: 0.8125rem;
      line-height: 1.6;
      color: #e5e7eb;
    }
  }
}
</style>
