<template>
  <div class="strategy-editor">
    <!-- 載入中 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>{{ isEditMode ? '載入策略中...' : '初始化編輯器...' }}</p>
    </div>

    <!-- 編輯表單 -->
    <div v-else class="edit-container">
      <div class="page-header">
        <div>
          <h1 class="page-title">{{ isEditMode ? '編輯策略' : '建立新策略' }}</h1>
          <p class="page-subtitle">{{ isEditMode ? '修改策略設定與代碼' : '選擇範本或從零開始' }}</p>
        </div>
        <NuxtLink to="/strategies" class="btn-secondary">
          <span class="icon">←</span>
          返回列表
        </NuxtLink>
      </div>

      <div class="edit-form-card">
        <form @submit.prevent="handleSave">
          <!-- 左右分欄佈局 -->
          <div class="create-strategy-layout">
            <!-- 左側：策略基本資訊 + 代碼編輯器 -->
            <div class="left-panel">
              <!-- 策略名稱 -->
              <div class="form-group">
                <label for="name">策略名稱 *</label>
                <input
                  id="name"
                  v-model="strategy.name"
                  type="text"
                  placeholder="例如：均線交叉策略"
                  required
                >
              </div>

              <!-- 描述 -->
              <div class="form-group">
                <label for="description">描述</label>
                <textarea
                  id="description"
                  v-model="strategy.description"
                  placeholder="描述您的策略邏輯..."
                  rows="3"
                ></textarea>
              </div>

              <!-- 策略代碼 -->
              <div class="form-group">
                <label for="code">策略代碼 *</label>
                <ClientCodeEditor
                  v-model="strategy.code"
                  language="python"
                  theme="vs-dark"
                  height="500px"
                />
              </div>
            </div>

            <!-- 右側：引擎類型、狀態與範本庫 -->
            <div class="right-panel">
              <!-- 狀態選擇 -->
              <div class="form-group">
                <label for="status">策略狀態</label>
                <select
                  id="status"
                  v-model="strategy.status"
                  class="status-selector"
                >
                  <option value="draft">📝 草稿</option>
                  <option value="active">✅ 啟用</option>
                  <option value="paused">⏸️ 暫停</option>
                  <option value="archived">📦 封存</option>
                </select>
              </div>

              <!-- 引擎類型選擇 -->
              <div class="form-group">
                <label>策略引擎類型</label>
                <div class="engine-type-selector">
                  <button
                    type="button"
                    @click="strategy.engine_type = 'backtrader'"
                    :class="['engine-type-btn', { active: strategy.engine_type === 'backtrader' }]"
                  >
                    <span class="engine-icon">📊</span>
                    <div class="engine-info">
                      <div class="engine-name">Backtrader</div>
                      <div class="engine-desc">技術指標策略</div>
                    </div>
                  </button>
                  <button
                    type="button"
                    @click="strategy.engine_type = 'qlib'"
                    :class="['engine-type-btn', { active: strategy.engine_type === 'qlib' }]"
                  >
                    <span class="engine-icon">🤖</span>
                    <div class="engine-info">
                      <div class="engine-name">Qlib ML</div>
                      <div class="engine-desc">機器學習模型</div>
                    </div>
                  </button>
                </div>
              </div>

              <!-- 策略範本 -->
              <div class="form-group">
                <label>策略範本</label>

                <!-- 範本類型切換 -->
                <div class="template-tabs">
                  <button
                    type="button"
                    @click="templateTab = 'general'"
                    :class="['template-tab', { active: templateTab === 'general' }]"
                  >
                    <span class="icon">📚</span>
                    通用範本
                  </button>
                  <button
                    type="button"
                    @click="templateTab = 'factor'"
                    :class="['template-tab', { active: templateTab === 'factor' }]"
                  >
                    <span class="icon">🧬</span>
                    RD-Agent 因子
                  </button>
                </div>

                <!-- 通用範本內容 -->
                <div v-show="templateTab === 'general'">
                  <StrategyTemplates v-if="strategy.engine_type === 'backtrader'" @select="insertTemplate" />
                  <QlibStrategyTemplates v-else @select="insertTemplate" />
                </div>

                <!-- 因子範本內容 -->
                <div v-show="templateTab === 'factor'">
                  <!-- RD-Agent 因子範本只支援 Qlib 引擎 -->
                  <FactorStrategyTemplates
                    v-if="strategy.engine_type === 'qlib'"
                    :engine-type="strategy.engine_type"
                    @select="insertTemplate"
                  />
                  <!-- Backtrader 引擎提示 -->
                  <div v-else class="engine-mismatch-warning">
                    <div class="warning-icon">⚠️</div>
                    <h3>RD-Agent 因子範本僅支援 Qlib 引擎</h3>
                    <p>RD-Agent 生成的因子使用 Qlib 表達式語法（如 <code>$close / Ref($close, 20) - 1</code>），無法直接在 Backtrader 引擎中使用。</p>
                    <div class="options">
                      <h4>您有兩個選擇：</h4>
                      <ol>
                        <li>
                          <strong>切換到 Qlib 引擎</strong>（推薦）
                          <br>
                          <small>在上方「引擎類型」選擇 <strong>Qlib</strong>，即可直接使用 RD-Agent 因子</small>
                        </li>
                        <li>
                          <strong>手動轉換語法</strong>
                          <br>
                          <small>將 Qlib 表達式轉換為 Backtrader 代碼：</small>
                          <ul>
                            <li><code>$close</code> → <code>self.data.close</code></li>
                            <li><code>Ref($close, 20)</code> → <code>self.data.close(-20)</code></li>
                            <li><code>Mean($close, 20)</code> → <code>bt.indicators.SMA(self.data.close, period=20)</code></li>
                          </ul>
                        </li>
                      </ol>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <!-- 右側面板結束 -->

          </div>
          <!-- 左右分欄佈局結束 -->

          <div class="form-actions">
            <NuxtLink to="/strategies" class="btn-secondary">
              取消
            </NuxtLink>
            <button
              type="submit"
              :disabled="saving"
              class="btn-primary"
            >
              {{ saving ? '儲存中...' : (isEditMode ? '儲存變更' : '建立策略') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 錯誤對話框 -->
    <ErrorDisplay
      v-if="currentError"
      :error="currentError"
      @close="clearError"
    />
  </div>
</template>

<script setup lang="ts">
import { useErrorHandler } from '@/composables/useErrorHandler'
import ErrorDisplay from '@/components/ErrorDisplay.vue'
// Props
const props = defineProps<{
  strategyId?: string | number  // 可選：有 ID 為編輯模式，無 ID 為建立模式
}>()

const router = useRouter()
const config = useRuntimeConfig()
const { currentError, handleError, clearError } = useErrorHandler()

// 判斷是編輯模式還是建立模式
const isEditMode = computed(() => !!props.strategyId)

// 狀態
const loading = ref(false)
const saving = ref(false)
const templateTab = ref('general') // 'general' | 'factor'

// 策略資料
const strategy = reactive({
  name: '',
  description: '',
  code: '',
  status: 'draft',
  engine_type: 'backtrader',
  parameters: {}
})

// 插入範本
const insertTemplate = (payload: string | { code: string; mode: string; template: any }) => {
  // 處理兩種格式：
  // 1. StrategyTemplates: 直接傳字串
  // 2. QlibStrategyTemplates: 傳物件 {code, mode, template}

  let templateCode = ''
  let insertMode = 'replace'

  if (typeof payload === 'string') {
    // StrategyTemplates 格式（字串）
    templateCode = payload
    insertMode = 'replace'
  } else {
    // QlibStrategyTemplates 格式（物件）
    templateCode = payload.code
    insertMode = payload.mode || 'replace'
  }

  // 根據插入模式處理
  if (insertMode === 'replace') {
    // 完全替換
    if (strategy.code && strategy.code.trim().length > 0) {
      if (!confirm('是否要用範本覆蓋現有代碼？此操作無法復原。')) {
        return
      }
    }
    strategy.code = templateCode
    if (process.client) {
      alert('✅ 範本已插入！您可以根據需求修改代碼。')
    }
  } else if (insertMode === 'factor') {
    // 只插入因子邏輯（智慧合併）
    if (strategy.code && strategy.code.trim().length > 0) {
      if (!confirm('是否要將因子代碼合併到現有策略中？')) {
        return
      }
      // 在現有代碼末尾添加分隔線和因子代碼
      strategy.code += '\n\n# ========== 新增因子 ==========\n' + templateCode
    } else {
      strategy.code = templateCode
    }
    if (process.client) {
      alert('⭐ 因子代碼已合併！請檢查並調整整合邏輯。')
    }
  } else if (insertMode === 'append') {
    // 追加到末尾
    if (strategy.code && strategy.code.trim().length > 0) {
      strategy.code += '\n\n' + templateCode
    } else {
      strategy.code = templateCode
    }
    if (process.client) {
      alert('➕ 代碼已追加到末尾！')
    }
  }
}

// 載入策略資料（編輯模式）
const loadStrategy = async () => {
  if (!isEditMode.value) {
    // 建立模式：不需要載入
    return
  }

  loading.value = true

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    console.log('Loading strategy:', props.strategyId)
    const response = await $fetch<any>(
      `${config.public.apiBase}/api/v1/strategies/${props.strategyId}`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    console.log('Strategy loaded:', response)

    // 填充表單
    strategy.name = response.name
    strategy.description = response.description || ''
    strategy.code = response.code
    strategy.status = response.status
    strategy.engine_type = response.engine_type || 'backtrader'
    strategy.parameters = response.parameters || {}

  } catch (error: any) {
    console.error('Failed to load strategy:', error)

    if (error.status === 401) {
      router.push('/login')
    } else {
      handleError(error, {
        showDialog: true,
        context: '載入策略'
      })
    }
  } finally {
    loading.value = false
  }
}

// 儲存變更（統一處理建立和編輯）
const handleSave = async () => {
  console.log('=== Saving strategy ===')
  console.log('Mode:', isEditMode.value ? 'Edit' : 'Create')
  console.log('Strategy data:', {
    name: strategy.name,
    description: strategy.description,
    codeLength: strategy.code?.length || 0,
    status: strategy.status,
    engine_type: strategy.engine_type
  })

  saving.value = true

  try {
    const token = process.client ? localStorage.getItem('access_token') : null
    if (!token) {
      router.push('/login')
      return
    }

    const apiUrl = isEditMode.value
      ? `${config.public.apiBase}/api/v1/strategies/${props.strategyId}`
      : `${config.public.apiBase}/api/v1/strategies/`

    const method = isEditMode.value ? 'PUT' : 'POST'

    console.log('Sending request:', method, apiUrl)
    const response = await $fetch<any>(apiUrl, {
      method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: {
        name: strategy.name,
        description: strategy.description,
        code: strategy.code,
        status: strategy.status,
        engine_type: strategy.engine_type,
        parameters: strategy.parameters
      }
    })

    console.log('✅ Strategy saved successfully:', response)

    // 顯示成功訊息並返回列表
    alert(isEditMode.value ? '✅ 策略更新成功！' : '✅ 策略建立成功！')
    router.push('/strategies')

  } catch (error: any) {
    console.error('❌ Failed to save strategy:', error)
    console.error('Error details:', {
      status: error.status,
      statusText: error.statusText,
      data: error.data,
      message: error.message
    })

    handleError(error, {
      showDialog: true,
      context: isEditMode.value ? '更新策略' : '建立策略'
    })
  } finally {
    saving.value = false
  }
}

// 載入資料
onMounted(() => {
  loadStrategy()
})
</script>

<style scoped lang="scss">
.strategy-editor {
  width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    color: #111827;
    margin: 0 0 0.5rem 0;
  }

  .page-subtitle {
    color: #6b7280;
    margin: 0;
  }
}

.loading-state {
  text-align: center;
  padding: 4rem 2rem;

  .spinner {
    width: 3rem;
    height: 3rem;
    border: 4px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  padding: 1rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  margin-bottom: 1rem;
}

.edit-container {
  max-width: 100%;
  margin: 0 auto;
}

.edit-form-card {
  background: white;
  padding: 2rem;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

// 左右分欄佈局
.create-strategy-layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 2rem;
  margin-bottom: 2rem;

  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: fit-content;
  position: sticky;
  top: 100px;
}

// 引擎類型選擇器
.engine-type-selector {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.engine-type-btn {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;

  &:hover {
    border-color: #3b82f6;
    background: #f0f9ff;
  }

  &.active {
    border-color: #3b82f6;
    background: #dbeafe;
    box-shadow: 0 4px 6px rgba(59, 130, 246, 0.1);
  }

  .engine-icon {
    font-size: 2rem;
    flex-shrink: 0;
  }

  .engine-info {
    flex: 1;

    .engine-name {
      font-size: 1rem;
      font-weight: 600;
      color: #111827;
      margin-bottom: 0.25rem;
    }

    .engine-desc {
      font-size: 0.875rem;
      color: #6b7280;
    }
  }
}

// 狀態選擇器樣式優化
.status-selector {
  padding: 0.75rem 1rem;
  font-size: 1rem;
  font-weight: 500;
}

.form-group {
  margin-bottom: 1.5rem;

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #374151;
  }

  input,
  textarea,
  select {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-family: inherit;

    &:focus {
      outline: none;
      border-color: #3b82f6;
    }
  }

  textarea {
    resize: vertical;
  }

  select {
    background: white;
    cursor: pointer;
    padding-right: 2.5rem;
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
    background-position: right 0.5rem center;
    background-repeat: no-repeat;
    background-size: 1.5em 1.5em;
    appearance: none;
  }
}

.template-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e5e7eb;
}

.template-tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: white;
  color: #6b7280;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  .icon {
    font-size: 1rem;
  }

  &:hover {
    background: #f9fafb;
    border-color: #d1d5db;
    color: #374151;
  }

  &.active {
    background: #3b82f6;
    color: white;
    border-color: #3b82f6;
    box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
  }

  &:active {
    transform: scale(0.98);
  }
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #e5e7eb;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  text-decoration: none;

  &:hover:not(:disabled) {
    background: #2563eb;
  }

  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }
}

.btn-secondary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  text-decoration: none;

  .icon {
    font-size: 1.25rem;
  }

  &:hover {
    background: #e5e7eb;
  }
}

// 引擎不匹配警告
.engine-mismatch-warning {
  background: #fffbeb;
  border: 2px solid #fbbf24;
  border-radius: 0.75rem;
  padding: 2rem;
  margin: 1.5rem 0;
  color: #78350f;

  .warning-icon {
    font-size: 3rem;
    text-align: center;
    margin-bottom: 1rem;
  }

  h3 {
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 1rem;
    color: #92400e;
  }

  p {
    font-size: 1rem;
    line-height: 1.6;
    margin-bottom: 1.5rem;
    color: #78350f;
  }

  code {
    background: #fef3c7;
    padding: 0.2rem 0.5rem;
    border-radius: 0.25rem;
    font-family: 'Monaco', 'Courier New', monospace;
    font-size: 0.875rem;
    color: #92400e;
    border: 1px solid #fbbf24;
  }

  .options {
    background: white;
    border-radius: 0.5rem;
    padding: 1.5rem;
    margin-top: 1.5rem;
    border: 1px solid #fbbf24;

    h4 {
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 1rem;
      color: #92400e;
    }

    ol {
      list-style: decimal;
      padding-left: 1.5rem;
      margin: 0;

      li {
        margin-bottom: 1.25rem;
        line-height: 1.6;
        color: #78350f;

        &:last-child {
          margin-bottom: 0;
        }

        strong {
          color: #92400e;
          font-weight: 700;
        }

        small {
          display: block;
          margin-top: 0.5rem;
          color: #a16207;
          font-size: 0.875rem;
        }

        ul {
          list-style: disc;
          padding-left: 1.5rem;
          margin-top: 0.75rem;

          li {
            margin-bottom: 0.5rem;
            font-size: 0.875rem;

            code {
              font-size: 0.8125rem;
            }
          }
        }
      }
    }
  }
}

// 響應式
@media (max-width: 768px) {
  .create-strategy-layout {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .right-panel {
    position: static;
  }

  .template-tabs {
    flex-direction: column;
  }

  .form-actions {
    flex-direction: column;
  }
}
</style>
