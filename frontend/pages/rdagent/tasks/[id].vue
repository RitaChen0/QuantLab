<template>
  <div class="task-detail-page">
    <!-- 頂部導航欄 -->
    <AppHeader />

    <!-- 頁首麵包屑 -->
    <div class="breadcrumb">
      <NuxtLink to="/rdagent">自動研發</NuxtLink>
      <span class="separator">›</span>
      <NuxtLink to="/rdagent?tab=tasks">任務列表</NuxtLink>
      <span class="separator">›</span>
      <span class="current">任務 #{{ taskId }}</span>
    </div>

    <!-- 載入中 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>載入任務詳情中...</p>
    </div>

    <!-- 錯誤訊息 -->
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <NuxtLink to="/rdagent?tab=tasks" class="btn-back">返回任務列表</NuxtLink>
    </div>

    <!-- 任務詳情 -->
    <div v-else-if="task" class="task-content">
      <!-- 任務標題與狀態 -->
      <div class="task-header">
        <div class="header-left">
          <h1>任務 #{{ task.id }}</h1>
          <span :class="['status-badge', task.status]">{{ getStatusLabel(task.status) }}</span>
        </div>
        <div class="header-right">
          <span class="task-type">{{ getTypeLabel(task.task_type) }}</span>
        </div>
      </div>

      <!-- 任務時間資訊 -->
      <div class="time-info">
        <div class="time-item">
          <span class="label">創建時間：</span>
          <span class="value">{{ formatDate(task.created_at) }}</span>
        </div>
        <div class="time-item" v-if="task.started_at">
          <span class="label">開始時間：</span>
          <span class="value">{{ formatDate(task.started_at) }}</span>
        </div>
        <div class="time-item" v-if="task.completed_at">
          <span class="label">完成時間：</span>
          <span class="value">{{ formatDate(task.completed_at) }}</span>
        </div>
        <div class="time-item" v-if="task.started_at && task.completed_at">
          <span class="label">執行時長：</span>
          <span class="value">{{ calculateDuration(task.started_at, task.completed_at) }}</span>
        </div>
      </div>

      <!-- 輸入參數 -->
      <div class="section">
        <h2>📋 輸入參數</h2>
        <div class="params-grid">
          <div class="param-item" v-for="(value, key) in task.input_params" :key="key">
            <span class="param-key">{{ formatParamKey(key) }}</span>
            <span class="param-value">{{ formatParamValue(value) }}</span>
          </div>
        </div>
      </div>

      <!-- 執行結果 -->
      <div class="section" v-if="task.result">
        <h2>📊 執行結果</h2>
        <div class="result-summary">
          <div class="result-card" v-if="task.result.generated_factors_count !== undefined">
            <div class="result-label">生成因子數量</div>
            <div class="result-value">{{ task.result.generated_factors_count }} 個</div>
          </div>
          <div class="result-card" v-if="task.llm_calls">
            <div class="result-label">LLM API 調用</div>
            <div class="result-value">{{ task.llm_calls }} 次</div>
          </div>
          <div class="result-card" v-if="task.llm_cost">
            <div class="result-label">LLM 成本</div>
            <div class="result-value">${{ task.llm_cost.toFixed(4) }}</div>
          </div>
        </div>

        <!-- 生成的因子列表 -->
        <div v-if="task.result.factors && task.result.factors.length > 0" class="factors-list">
          <h3>生成的因子</h3>
          <div class="factor-item" v-for="(factor, index) in task.result.factors" :key="index">
            <div class="factor-header">
              <span class="factor-name">{{ factor.name }}</span>
              <span class="factor-category" v-if="factor.category">{{ factor.category }}</span>
            </div>
            <div class="factor-formula">
              <code>{{ factor.formula }}</code>
            </div>
          </div>
        </div>

        <!-- 其他結果訊息 -->
        <div v-if="task.result.message" class="result-message">
          <p>{{ task.result.message }}</p>
        </div>

        <!-- 日誌目錄 -->
        <div v-if="task.result.log_directory" class="log-directory">
          <span class="label">日誌目錄：</span>
          <code>{{ task.result.log_directory }}</code>
        </div>
      </div>

      <!-- 錯誤訊息 -->
      <div class="section error-section" v-if="task.error_message">
        <h2>❌ 錯誤訊息</h2>
        <div class="error-box">
          <pre>{{ task.error_message }}</pre>
        </div>
      </div>

      <!-- 操作按鈕 -->
      <div class="actions">
        <NuxtLink to="/rdagent?tab=tasks" class="btn-secondary">返回任務列表</NuxtLink>
        <button
          v-if="task.status === 'failed'"
          @click="retryTask"
          class="btn-primary"
          :disabled="isRetrying"
        >
          {{ isRetrying ? '重試中...' : '🔄 重試任務' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { loadUserInfo } = useUserInfo()
const config = useRuntimeConfig()

const taskId = ref(route.params.id)
const task = ref<any>(null)
const loading = ref(true)
const error = ref('')
const isRetrying = ref(false)

// 載入任務詳情
const loadTaskDetail = async () => {
  loading.value = true
  error.value = ''

  try {
    const token = localStorage.getItem('access_token')  // ✅ 修正：使用正確的 key
    if (!token) {
      router.push('/login')
      return
    }

    task.value = await $fetch(`${config.public.apiBase}/api/v1/rdagent/tasks/${taskId.value}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
  } catch (err: any) {
    error.value = err.data?.detail || '載入任務詳情失敗'
    console.error('Failed to load task detail:', err)
  } finally {
    loading.value = false
  }
}

// 重試失敗的任務
const retryTask = async () => {
  isRetrying.value = true

  try {
    const token = localStorage.getItem('access_token')  // ✅ 修正：使用正確的 key
    await $fetch(`${config.public.apiBase}/api/v1/rdagent/tasks/${taskId.value}/retry`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })

    alert('任務已重新提交！')
    loadTaskDetail()
  } catch (err: any) {
    alert('重試失敗：' + (err.data?.detail || err.message))
  } finally {
    isRetrying.value = false
  }
}

// 格式化日期
const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 計算執行時長
const calculateDuration = (startStr: string, endStr: string) => {
  const start = new Date(startStr).getTime()
  const end = new Date(endStr).getTime()
  const diffMs = end - start

  const hours = Math.floor(diffMs / 3600000)
  const minutes = Math.floor((diffMs % 3600000) / 60000)
  const seconds = Math.floor((diffMs % 60000) / 1000)

  if (hours > 0) {
    return `${hours} 小時 ${minutes} 分鐘`
  } else if (minutes > 0) {
    return `${minutes} 分鐘 ${seconds} 秒`
  } else {
    return `${seconds} 秒`
  }
}

// 格式化參數鍵
const formatParamKey = (key: string) => {
  const keyMap: Record<string, string> = {
    research_goal: '研究目標',
    stock_pool: '股票池',
    max_factors: '最多生成因子',
    llm_model: 'LLM 模型',
    max_iterations: '最大迭代次數'
  }
  return keyMap[key] || key
}

// 格式化參數值
const formatParamValue = (value: any) => {
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
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

onMounted(() => {
  loadUserInfo()
  loadTaskDetail()
})
</script>

<style scoped lang="scss">
.task-detail-page {
  min-height: 100vh;
  background: #f9fafb;
}

.breadcrumb {
  margin-bottom: 2rem;
  font-size: 0.9rem;
  color: #6b7280;

  a {
    color: #3b82f6;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  .separator {
    margin: 0 0.5rem;
  }

  .current {
    color: #111827;
    font-weight: 500;
  }
}

.loading-state,
.error-state {
  text-align: center;
  padding: 4rem 2rem;

  .spinner {
    width: 50px;
    height: 50px;
    margin: 0 auto 1rem;
    border: 4px solid #f3f4f6;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
}

.error-state {
  color: #dc2626;
}

.btn-back {
  display: inline-block;
  margin-top: 1rem;
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  text-decoration: none;
  border-radius: 0.375rem;

  &:hover {
    background: #2563eb;
  }
}

.task-content {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  border-bottom: 1px solid #e5e7eb;

  .header-left {
    display: flex;
    align-items: center;
    gap: 1rem;

    h1 {
      font-size: 1.75rem;
      font-weight: 700;
      margin: 0;
    }
  }

  .status-badge {
    padding: 0.375rem 0.75rem;
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

  .task-type {
    padding: 0.5rem 1rem;
    background: #f3f4f6;
    border-radius: 0.375rem;
    font-size: 0.9rem;
    font-weight: 500;
  }
}

.time-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  padding: 1.5rem 2rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;

  .time-item {
    .label {
      display: block;
      font-size: 0.875rem;
      color: #6b7280;
      margin-bottom: 0.25rem;
    }

    .value {
      font-weight: 500;
      color: #111827;
    }
  }
}

.section {
  padding: 2rem;
  border-bottom: 1px solid #e5e7eb;

  &:last-child {
    border-bottom: none;
  }

  h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1.5rem;
  }

  h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 1.5rem 0 1rem;
  }
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;

  .param-item {
    display: flex;
    flex-direction: column;
    padding: 1rem;
    background: #f9fafb;
    border-radius: 0.375rem;

    .param-key {
      font-size: 0.875rem;
      color: #6b7280;
      margin-bottom: 0.5rem;
    }

    .param-value {
      font-weight: 500;
      color: #111827;
      word-wrap: break-word;
    }
  }
}

.result-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;

  .result-card {
    padding: 1.5rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 0.5rem;
    color: white;

    .result-label {
      font-size: 0.875rem;
      opacity: 0.9;
      margin-bottom: 0.5rem;
    }

    .result-value {
      font-size: 1.75rem;
      font-weight: 700;
    }
  }
}

.factors-list {
  .factor-item {
    margin-bottom: 1.5rem;
    padding: 1rem;
    background: #f9fafb;
    border-radius: 0.375rem;
    border-left: 4px solid #3b82f6;

    .factor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;

      .factor-name {
        font-weight: 600;
        color: #111827;
      }

      .factor-category {
        padding: 0.25rem 0.75rem;
        background: #dbeafe;
        color: #1e40af;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
      }
    }

    .factor-formula {
      code {
        display: block;
        padding: 0.75rem;
        background: white;
        border-radius: 0.25rem;
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 0.875rem;
        color: #1f2937;
        overflow-x: auto;
      }
    }
  }
}

.result-message {
  padding: 1rem;
  background: #dbeafe;
  border-radius: 0.375rem;
  margin-bottom: 1rem;

  p {
    margin: 0;
    color: #1e40af;
  }
}

.log-directory {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #f3f4f6;
  border-radius: 0.375rem;

  .label {
    font-weight: 500;
    color: #6b7280;
  }

  code {
    flex: 1;
    padding: 0.5rem;
    background: white;
    border-radius: 0.25rem;
    font-family: 'Monaco', 'Courier New', monospace;
    font-size: 0.875rem;
    overflow-x: auto;
  }
}

.error-section {
  .error-box {
    padding: 1rem;
    background: #fee2e2;
    border-radius: 0.375rem;
    border-left: 4px solid #dc2626;

    pre {
      margin: 0;
      color: #991b1b;
      font-family: 'Monaco', 'Courier New', monospace;
      font-size: 0.875rem;
      white-space: pre-wrap;
      word-wrap: break-word;
    }
  }
}

.actions {
  display: flex;
  gap: 1rem;
  padding: 2rem;

  .btn-secondary,
  .btn-primary {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 0.375rem;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
    display: inline-block;
  }

  .btn-secondary {
    background: #f3f4f6;
    color: #374151;

    &:hover {
      background: #e5e7eb;
    }
  }

  .btn-primary {
    background: #3b82f6;
    color: white;

    &:hover:not(:disabled) {
      background: #2563eb;
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
}
</style>
