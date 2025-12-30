<template>
  <div class="model-training-page">
    <AppHeader />

    <!-- 頁面標題 -->
    <div class="page-header">
      <div class="header-content">
        <h1>🎯 模型訓練</h1>
        <p v-if="model">訓練模型：{{ model.name }}</p>
      </div>
      <NuxtLink to="/rdagent" class="btn-secondary">
        ← 返回
      </NuxtLink>
    </div>

    <!-- 載入中 -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p>載入模型資訊...</p>
    </div>

    <!-- 錯誤訊息 -->
    <div v-else-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- 主要內容 -->
    <div v-else class="training-container">
      <!-- 左側：因子選擇和訓練配置 -->
      <div class="config-panel">
        <!-- 因子選擇 -->
        <div class="section">
          <h2>📊 選擇訓練因子</h2>
          <p class="section-description">選擇因子作為模型的輸入特徵</p>

          <!-- Alpha158 選項 -->
          <div class="alpha158-option">
            <label class="alpha158-checkbox">
              <input
                type="checkbox"
                v-model="useAlpha158"
                @change="onAlpha158Change"
              />
              <span class="checkbox-label">
                <strong>使用 Alpha158+ 增強因子集</strong>
                <span class="alpha158-desc">（179個量化因子，含增強版 Rolling 指標）</span>
              </span>
            </label>
          </div>

          <!-- 手動選因子（Alpha158 未啟用時顯示） -->
          <div v-if="!useAlpha158">
            <div v-if="loadingFactors" class="loading-small">載入因子列表...</div>

            <div v-else-if="availableFactors.length === 0" class="empty-message">
              沒有可用的因子。請先執行<NuxtLink to="/rdagent">因子挖掘</NuxtLink>。
            </div>

            <div v-else class="factors-list">
              <div
                v-for="factor in availableFactors"
                :key="factor.id"
                class="factor-item"
                :class="{ selected: selectedFactorIds.includes(factor.id) }"
                @click="toggleFactor(factor.id)"
              >
                <div class="factor-checkbox">
                  <input
                    type="checkbox"
                    :checked="selectedFactorIds.includes(factor.id)"
                    @click.stop="toggleFactor(factor.id)"
                  />
                </div>
                <div class="factor-info">
                  <div class="factor-name">{{ factor.name }}</div>
                  <div class="factor-formula">{{ factor.formula }}</div>
                  <div class="factor-metrics" v-if="factor.ic">
                    <span class="metric">IC: {{ factor.ic.toFixed(4) }}</span>
                    <span class="metric" v-if="factor.icir">ICIR: {{ factor.icir.toFixed(2) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="selection-summary">
              已選擇 {{ selectedFactorIds.length }} / 50 個因子
            </div>
          </div>

          <!-- Alpha158 啟用提示 -->
          <div v-else class="alpha158-active">
            <div class="info-box">
              <h3>🎯 Alpha158+ 增強因子集</h3>
              <p>將使用 179 個量化因子進行訓練：</p>
              <ul>
                <li><strong>9 個 KBar 因子</strong>：K線形態特徵（實體、影線等）</li>
                <li><strong>20 個 Price 因子</strong>：歷史價格序列</li>
                <li><strong>5 個 Volume 因子</strong>：成交量序列</li>
                <li><strong>145 個 Rolling 因子</strong>：增強版滾動技術指標（動量、波動率、相關性、成交量分析等）</li>
              </ul>
              <p class="warning">⚠️ 注意：Alpha158+ 訓練時間較長，建議使用台股50以上的股票池。</p>
            </div>
          </div>
        </div>

        <!-- 訓練配置 -->
        <div class="section">
          <h2>⚙️ 訓練配置</h2>

          <div class="config-tabs">
            <button
              :class="['config-tab', { active: configTab === 'dataset' }]"
              @click="configTab = 'dataset'"
            >
              數據集
            </button>
            <button
              :class="['config-tab', { active: configTab === 'params' }]"
              @click="configTab = 'params'"
            >
              訓練參數
            </button>
          </div>

          <!-- 數據集配置 -->
          <div v-if="configTab === 'dataset'" class="config-form">
            <div class="form-group">
              <label>股票池</label>
              <select v-model="datasetConfig.instruments">
                <option value="台股30">台股30（成交量前30支，訓練快）</option>
                <option value="台股50">台股50（成交量前50支，推薦）</option>
                <option value="台股100">台股100（成交量前100支）</option>
                <option value="台股150">台股150（成交量前150支）</option>
                <option value="台股200">台股200（成交量前200支）</option>
              </select>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>開始日期</label>
                <input type="date" v-model="datasetConfig.start_time" />
              </div>
              <div class="form-group">
                <label>結束日期</label>
                <input type="date" v-model="datasetConfig.end_time" />
              </div>
            </div>

            <div class="form-group">
              <label>訓練集比例</label>
              <input
                type="range"
                v-model.number="datasetConfig.train_ratio"
                min="0.5"
                max="0.9"
                step="0.05"
              />
              <span class="range-value">{{ (datasetConfig.train_ratio * 100).toFixed(0) }}%</span>
            </div>

            <div class="form-group">
              <label>驗證集比例</label>
              <input
                type="range"
                v-model.number="datasetConfig.valid_ratio"
                min="0.05"
                max="0.3"
                step="0.05"
              />
              <span class="range-value">{{ (datasetConfig.valid_ratio * 100).toFixed(0) }}%</span>
            </div>

            <div class="form-group">
              <label>測試集比例</label>
              <input
                type="range"
                v-model.number="datasetConfig.test_ratio"
                min="0.05"
                max="0.3"
                step="0.05"
              />
              <span class="range-value">{{ (datasetConfig.test_ratio * 100).toFixed(0) }}%</span>
            </div>

            <div class="ratio-warning" v-if="ratioSum !== 1.0">
              ⚠️ 比例總和應為 100%（目前：{{ (ratioSum * 100).toFixed(0) }}%）
            </div>
          </div>

          <!-- 訓練參數配置 -->
          <div v-if="configTab === 'params'" class="config-form">
            <div class="form-group">
              <label>訓練輪數 (Epochs)</label>
              <input
                type="number"
                v-model.number="trainingParams.num_epochs"
                min="1"
                max="1000"
              />
            </div>

            <div class="form-group">
              <label>批次大小 (Batch Size)</label>
              <select v-model.number="trainingParams.batch_size">
                <option :value="256">256</option>
                <option :value="512">512</option>
                <option :value="800">800</option>
                <option :value="1024">1024</option>
                <option :value="2048">2048</option>
              </select>
            </div>

            <div class="form-group">
              <label>學習率 (Learning Rate)</label>
              <select v-model.number="trainingParams.learning_rate">
                <option :value="0.0001">0.0001</option>
                <option :value="0.001">0.001 (推薦)</option>
                <option :value="0.01">0.01</option>
              </select>
            </div>

            <div class="form-group">
              <label>早停輪數 (Early Stopping)</label>
              <input
                type="number"
                v-model.number="trainingParams.early_stop_rounds"
                min="5"
                max="100"
              />
              <small>連續 N 輪驗證損失未改善時停止訓練</small>
            </div>

            <div class="form-group">
              <label>優化器</label>
              <select v-model="trainingParams.optimizer">
                <option value="adam">Adam (推薦)</option>
                <option value="sgd">SGD</option>
                <option value="rmsprop">RMSprop</option>
              </select>
            </div>

            <div class="form-group">
              <label>損失函數</label>
              <select v-model="trainingParams.loss_function">
                <option value="mse">MSE (均方誤差)</option>
                <option value="mae">MAE (平均絕對誤差)</option>
                <option value="huber">Huber Loss</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 訓練按鈕 -->
        <div class="action-buttons">
          <button
            class="btn-primary btn-large"
            @click="startTraining"
            :disabled="!canStartTraining || isTraining"
          >
            {{ isTraining ? '訓練中...' : '🚀 開始訓練' }}
          </button>
        </div>
      </div>

      <!-- 右側：訓練進度和日誌 -->
      <div class="progress-panel">
        <!-- 當前訓練任務 -->
        <div v-if="currentJob" class="section">
          <h2>📈 訓練進度</h2>

          <!-- 狀態徽章 -->
          <div class="status-badge" :class="currentJob.status.toLowerCase()">
            {{ getStatusText(currentJob.status) }}
          </div>

          <!-- 進度條 -->
          <div class="progress-bar-container">
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: (currentJob.progress * 100) + '%' }"
              ></div>
            </div>
            <div class="progress-text">
              {{ (currentJob.progress * 100).toFixed(1) }}%
            </div>
          </div>

          <!-- 當前步驟 -->
          <div class="current-step" v-if="currentJob.current_step">
            <div class="step-icon">⚡</div>
            <div class="step-text">{{ currentJob.current_step }}</div>
          </div>

          <!-- 訓練指標 -->
          <div class="metrics-grid" v-if="currentJob.current_epoch">
            <div class="metric-card">
              <div class="metric-label">訓練輪數</div>
              <div class="metric-value">
                {{ currentJob.current_epoch }} / {{ currentJob.total_epochs }}
              </div>
            </div>
            <div class="metric-card" v-if="currentJob.train_loss">
              <div class="metric-label">訓練損失</div>
              <div class="metric-value">{{ currentJob.train_loss.toFixed(6) }}</div>
            </div>
            <div class="metric-card" v-if="currentJob.valid_loss">
              <div class="metric-label">驗證損失</div>
              <div class="metric-value">{{ currentJob.valid_loss.toFixed(6) }}</div>
            </div>
            <div class="metric-card" v-if="currentJob.test_ic">
              <div class="metric-label">測試 IC</div>
              <div class="metric-value">{{ currentJob.test_ic.toFixed(4) }}</div>
            </div>
          </div>

          <!-- 訓練日誌 -->
          <div class="training-log-section">
            <h3>📋 訓練日誌</h3>
            <div class="training-log" ref="trainingLog">
              <pre v-if="currentJob.training_log">{{ currentJob.training_log }}</pre>
              <p v-else class="log-empty">暫無日誌...</p>
            </div>
          </div>

          <!-- 錯誤訊息 -->
          <div v-if="currentJob.error_message" class="error-message">
            <strong>錯誤訊息：</strong>
            <pre>{{ currentJob.error_message }}</pre>
          </div>

          <!-- 操作按鈕 -->
          <div class="job-actions" v-if="currentJob.status === 'RUNNING' || currentJob.status === 'PENDING'">
            <button class="btn-danger" @click="cancelTraining">
              🚫 取消訓練
            </button>
          </div>
        </div>

        <!-- 歷史訓練列表 -->
        <div class="section">
          <h2>📜 訓練歷史</h2>

          <div v-if="loadingHistory" class="loading-small">載入歷史...</div>

          <div v-else-if="trainingHistory.length === 0" class="empty-message">
            尚無訓練記錄
          </div>

          <div v-else class="history-list">
            <div
              v-for="job in trainingHistory"
              :key="job.id"
              class="history-item"
              :class="{ active: currentJob && currentJob.id === job.id }"
              @click="loadTrainingJob(job.id)"
            >
              <div class="history-header">
                <span class="job-id">Job #{{ job.id }}</span>
                <span class="job-status" :class="job.status.toLowerCase()">
                  {{ getStatusText(job.status) }}
                </span>
              </div>
              <div class="history-details">
                <div class="history-progress">
                  進度: {{ (job.progress * 100).toFixed(0) }}%
                </div>
                <div class="history-time">
                  {{ formatDateTime(job.created_at) }}
                </div>
              </div>
              <div v-if="job.test_ic" class="history-result">
                測試 IC: {{ job.test_ic.toFixed(4) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const config = useRuntimeConfig()
const { getToken } = useAuth()
const modelId = parseInt(route.params.id as string)

// 狀態
const loading = ref(true)
const loadingFactors = ref(false)
const loadingHistory = ref(false)
const error = ref('')
const isTraining = ref(false)

// 模型資訊
const model = ref<any>(null)

// 因子相關
const availableFactors = ref<any[]>([])
const selectedFactorIds = ref<number[]>([])
const useAlpha158 = ref(false)

// 配置 tabs
const configTab = ref('dataset')

// 數據集配置
const datasetConfig = ref({
  instruments: '台股50',
  start_time: '2023-01-01',
  end_time: '2024-12-31',
  train_ratio: 0.7,
  valid_ratio: 0.15,
  test_ratio: 0.15
})

// 訓練參數
const trainingParams = ref({
  num_epochs: 100,
  batch_size: 800,
  learning_rate: 0.001,
  early_stop_rounds: 20,
  optimizer: 'adam',
  loss_function: 'mse'
})

// 訓練任務
const currentJob = ref<any>(null)
const trainingHistory = ref<any[]>([])

// 輪詢定時器
let pollInterval: NodeJS.Timeout | null = null

// 計算屬性
const ratioSum = computed(() => {
  return datasetConfig.value.train_ratio +
         datasetConfig.value.valid_ratio +
         datasetConfig.value.test_ratio
})

const canStartTraining = computed(() => {
  // 如果使用 Alpha158，不需要選擇因子
  const hasFactors = useAlpha158.value || (selectedFactorIds.value.length > 0 && selectedFactorIds.value.length <= 50)
  return hasFactors && Math.abs(ratioSum.value - 1.0) < 0.01
})

// 方法
const onAlpha158Change = () => {
  // 切換到 Alpha158 時，清空手動選擇的因子
  if (useAlpha158.value) {
    selectedFactorIds.value = []
  }
}

const toggleFactor = (factorId: number) => {
  const index = selectedFactorIds.value.indexOf(factorId)
  if (index > -1) {
    selectedFactorIds.value.splice(index, 1)
  } else {
    if (selectedFactorIds.value.length < 50) {
      selectedFactorIds.value.push(factorId)
    }
  }
}

const loadModel = async () => {
  try {
    const token = getToken()
    if (!token) {
      router.push('/login')
      return
    }

    const data = await $fetch(`${config.public.apiBase}/api/v1/rdagent/models`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (data) {
      const models = data as any[]
      model.value = models.find(m => m.id === modelId)
      if (!model.value) {
        error.value = '模型不存在'
      }
    }
  } catch (err: any) {
    error.value = err.message || '載入模型失敗'
  }
}

const loadFactors = async () => {
  loadingFactors.value = true
  try {
    const token = getToken()
    if (!token) {
      router.push('/login')
      return
    }

    const data = await $fetch(`${config.public.apiBase}/api/v1/rdagent/factors?limit=100`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (data) {
      availableFactors.value = data as any[]
    }
  } catch (err: any) {
    console.error('載入因子失敗:', err)
  } finally {
    loadingFactors.value = false
  }
}

const loadTrainingHistory = async () => {
  loadingHistory.value = true
  try {
    const token = getToken()
    if (!token) {
      router.push('/login')
      return
    }

    const data = await $fetch(`${config.public.apiBase}/api/v1/rdagent/models/${modelId}/training-jobs?limit=10`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (data) {
      const response = data as any
      trainingHistory.value = response.jobs || []
    }
  } catch (err: any) {
    console.error('載入訓練歷史失敗:', err)
  } finally {
    loadingHistory.value = false
  }
}

const startTraining = async () => {
  if (!canStartTraining.value) return

  isTraining.value = true
  try {
    const token = getToken()
    if (!token) {
      router.push('/login')
      return
    }

    const data = await $fetch(
      `${config.public.apiBase}/api/v1/rdagent/models/${modelId}/train`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: {
          factor_ids: selectedFactorIds.value,
          dataset_config: datasetConfig.value,
          training_params: trainingParams.value,
          use_alpha158: useAlpha158.value
        }
      }
    )

    if (data) {
      currentJob.value = data
      startPolling()
    }
  } catch (err: any) {
    alert('訓練啟動失敗：' + (err.message || err.data?.detail || '未知錯誤'))
  } finally {
    isTraining.value = false
  }
}

const loadTrainingJob = async (jobId: number) => {
  try {
    const token = getToken()
    if (!token) {
      router.push('/login')
      return
    }

    const data = await $fetch(`${config.public.apiBase}/api/v1/rdagent/training-jobs/${jobId}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (data) {
      currentJob.value = data

      // 如果任務正在運行，開始輪詢
      if (currentJob.value.status === 'RUNNING' || currentJob.value.status === 'PENDING') {
        startPolling()
      }
    }
  } catch (err: any) {
    console.error('載入訓練任務失敗:', err)
  }
}

const startPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }

  pollInterval = setInterval(async () => {
    if (!currentJob.value) return

    try {
      const token = getToken()
      if (!token) {
        stopPolling()
        router.push('/login')
        return
      }

      const data = await $fetch(`${config.public.apiBase}/api/v1/rdagent/training-jobs/${currentJob.value.id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (data) {
        currentJob.value = data

        // 自動滾動日誌到底部
        nextTick(() => {
          const logElement = (this as any).$refs.trainingLog
          if (logElement) {
            logElement.scrollTop = logElement.scrollHeight
          }
        })

        // 如果訓練完成或失敗，停止輪詢
        if (currentJob.value.status === 'COMPLETED' ||
            currentJob.value.status === 'FAILED' ||
            currentJob.value.status === 'CANCELLED') {
          stopPolling()
          loadTrainingHistory() // 刷新歷史列表
        }
      }
    } catch (err: any) {
      console.error('輪詢訓練進度失敗:', err)
    }
  }, 5000) // 每 5 秒輪詢一次
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

const cancelTraining = async () => {
  if (!currentJob.value) return

  if (!confirm('確定要取消訓練嗎？')) return

  try {
    const token = getToken()
    if (!token) {
      router.push('/login')
      return
    }

    await $fetch(`${config.public.apiBase}/api/v1/rdagent/training-jobs/${currentJob.value.id}/cancel`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    alert('取消訓練指令已發送')
  } catch (err: any) {
    alert('取消訓練失敗：' + (err.message || '未知錯誤'))
  }
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'PENDING': '等待中',
    'RUNNING': '訓練中',
    'COMPLETED': '已完成',
    'FAILED': '失敗',
    'CANCELLED': '已取消'
  }
  return statusMap[status] || status
}

const formatDateTime = (datetime: string) => {
  return new Date(datetime).toLocaleString('zh-TW')
}

// 生命週期
onMounted(async () => {
  await Promise.all([
    loadModel(),
    loadFactors(),
    loadTrainingHistory()
  ])
  loading.value = false
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.model-training-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding-bottom: 50px;
}

.page-header {
  background: white;
  padding: 30px;
  margin: 20px;
  border-radius: 15px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h1 {
  margin: 0 0 10px 0;
  font-size: 28px;
  color: #2d3748;
}

.header-content p {
  margin: 0;
  color: #718096;
}

.training-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin: 20px;
}

.config-panel,
.progress-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section {
  background: white;
  padding: 25px;
  border-radius: 15px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.section h2 {
  margin: 0 0 15px 0;
  font-size: 20px;
  color: #2d3748;
}

.section-description {
  color: #718096;
  margin-bottom: 20px;
}

/* 因子列表 */
.factors-list {
  max-height: 400px;
  overflow-y: auto;
  margin-bottom: 15px;
}

.factor-item {
  display: flex;
  gap: 15px;
  padding: 15px;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.factor-item:hover {
  border-color: #667eea;
  background: #f7fafc;
}

.factor-item.selected {
  border-color: #667eea;
  background: #edf2f7;
}

.factor-checkbox input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.factor-info {
  flex: 1;
}

.factor-name {
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 5px;
}

.factor-formula {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #4a5568;
  margin-bottom: 5px;
}

.factor-metrics {
  display: flex;
  gap: 15px;
}

.metric {
  font-size: 12px;
  color: #718096;
}

.selection-summary {
  text-align: center;
  padding: 10px;
  background: #edf2f7;
  border-radius: 8px;
  font-weight: 600;
  color: #2d3748;
}

/* 配置表單 */
.config-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e2e8f0;
}

.config-tab {
  padding: 10px 20px;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  font-weight: 600;
  color: #718096;
  transition: all 0.2s;
}

.config-tab.active {
  color: #667eea;
  border-bottom-color: #667eea;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 600;
  color: #2d3748;
}

.form-group small {
  font-size: 12px;
  color: #718096;
}

.form-group input[type="date"],
.form-group input[type="number"],
.form-group select {
  padding: 10px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
}

.form-group input[type="range"] {
  width: 100%;
}

.range-value {
  font-weight: 600;
  color: #667eea;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.ratio-warning {
  padding: 10px;
  background: #fff5f5;
  border: 2px solid #fc8181;
  border-radius: 8px;
  color: #c53030;
  font-size: 14px;
}

/* 操作按鈕 */
.action-buttons {
  display: flex;
  justify-content: center;
  padding-top: 10px;
}

.btn-large {
  padding: 15px 40px;
  font-size: 18px;
  font-weight: 600;
}

/* 進度面板 */
.status-badge {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 20px;
}

.status-badge.pending {
  background: #e2e8f0;
  color: #4a5568;
}

.status-badge.running {
  background: #bee3f8;
  color: #2c5282;
}

.status-badge.completed {
  background: #c6f6d5;
  color: #276749;
}

.status-badge.failed {
  background: #fed7d7;
  color: #9b2c2c;
}

.status-badge.cancelled {
  background: #feebc8;
  color: #7c2d12;
}

/* 進度條 */
.progress-bar-container {
  margin-bottom: 20px;
}

.progress-bar {
  height: 30px;
  background: #e2e8f0;
  border-radius: 15px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.5s ease;
}

.progress-text {
  text-align: center;
  font-weight: 600;
  color: #2d3748;
  font-size: 18px;
}

/* 當前步驟 */
.current-step {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: #edf2f7;
  border-radius: 10px;
  margin-bottom: 20px;
}

.step-icon {
  font-size: 24px;
}

.step-text {
  font-weight: 600;
  color: #2d3748;
  font-size: 16px;
}

/* 指標網格 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  margin-bottom: 20px;
}

.metric-card {
  padding: 15px;
  background: #f7fafc;
  border-radius: 10px;
  border-left: 4px solid #667eea;
}

.metric-label {
  font-size: 12px;
  color: #718096;
  margin-bottom: 5px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: #2d3748;
}

/* 訓練日誌 */
.training-log-section h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #2d3748;
}

.training-log {
  max-height: 300px;
  overflow-y: auto;
  background: #2d3748;
  color: #e2e8f0;
  padding: 15px;
  border-radius: 8px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.training-log pre {
  margin: 0;
  white-space: pre-wrap;
}

.log-empty {
  color: #a0aec0;
  font-style: italic;
}

/* 歷史列表 */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.history-item {
  padding: 15px;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  border-color: #667eea;
  background: #f7fafc;
}

.history-item.active {
  border-color: #667eea;
  background: #edf2f7;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.job-id {
  font-weight: 600;
  color: #2d3748;
}

.job-status {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.job-status.running {
  background: #bee3f8;
  color: #2c5282;
}

.job-status.completed {
  background: #c6f6d5;
  color: #276749;
}

.job-status.failed {
  background: #fed7d7;
  color: #9b2c2c;
}

.history-details {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #718096;
  margin-bottom: 5px;
}

.history-result {
  font-size: 14px;
  font-weight: 600;
  color: #667eea;
}

/* 通用樣式 */
.loading-container,
.loading-small {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #718096;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-message {
  text-align: center;
  padding: 40px;
  color: #a0aec0;
}

.error-message {
  background: #fff5f5;
  border: 2px solid #fc8181;
  border-radius: 8px;
  padding: 15px;
  color: #c53030;
  margin-bottom: 20px;
}

.error-message pre {
  margin-top: 10px;
  white-space: pre-wrap;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.btn-primary,
.btn-secondary,
.btn-danger {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #e2e8f0;
  color: #2d3748;
}

.btn-secondary:hover {
  background: #cbd5e0;
}

.btn-danger {
  background: #fc8181;
  color: white;
}

.btn-danger:hover {
  background: #f56565;
}

.job-actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

@media (max-width: 1200px) {
  .training-container {
    grid-template-columns: 1fr;
  }
}

/* Alpha158 樣式 */
.alpha158-option {
  margin-bottom: 20px;
  padding: 15px;
  background: #f7fafc;
  border-radius: 8px;
  border: 2px solid #e2e8f0;
}

.alpha158-checkbox {
  display: flex;
  align-items: flex-start;
  cursor: pointer;
  user-select: none;
}

.alpha158-checkbox input[type="checkbox"] {
  margin-right: 12px;
  margin-top: 3px;
  cursor: pointer;
  width: 18px;
  height: 18px;
}

.checkbox-label {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.alpha158-desc {
  font-size: 13px;
  color: #718096;
  font-weight: normal;
}

.alpha158-active {
  margin-top: 15px;
}

.info-box {
  background: #ebf8ff;
  border: 1px solid #90cdf4;
  border-radius: 8px;
  padding: 20px;
}

.info-box h3 {
  margin: 0 0 15px 0;
  color: #2c5282;
  font-size: 18px;
}

.info-box p {
  margin: 10px 0;
  color: #2d3748;
  line-height: 1.6;
}

.info-box ul {
  margin: 15px 0;
  padding-left: 25px;
  color: #2d3748;
}

.info-box li {
  margin: 8px 0;
  line-height: 1.6;
}

.info-box .warning {
  margin-top: 15px;
  padding: 12px;
  background: #fef5e7;
  border-left: 4px solid #f59e0b;
  border-radius: 4px;
  color: #92400e;
  font-weight: 500;
}
</style>
