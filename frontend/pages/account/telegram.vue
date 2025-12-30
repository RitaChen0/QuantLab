<template>
  <div class="telegram-container">
    <!-- 頂部導航欄 -->
    <AppHeader />

    <!-- 主要內容區 -->
    <main class="telegram-main">
      <div class="telegram-page">
        <!-- 頁面標題 -->
        <div class="page-header">
          <h1 class="page-title">📱 Telegram 通知設置</h1>
          <p class="page-subtitle">綁定您的 Telegram 帳號，即時接收回測結果和系統通知</p>
        </div>

        <!-- 綁定狀態卡片 -->
        <div class="binding-status-card" :class="{ 'is-bound': isBound }">
          <div class="status-icon">
            <span v-if="isBound">✅</span>
            <span v-else>📱</span>
          </div>
          <div class="status-content">
            <h3 class="status-title">
              {{ isBound ? 'Telegram 已綁定' : 'Telegram 未綁定' }}
            </h3>
            <p class="status-description" v-if="isBound">
              您的 Telegram 帳號已成功綁定，將接收所有通知
            </p>
            <p class="status-description" v-else>
              綁定 Telegram 後，您將即時收到回測完成通知和績效摘要
            </p>
            <div class="status-info" v-if="isBound && user">
              <div class="info-item">
                <span class="info-label">Telegram ID:</span>
                <span class="info-value">{{ user.telegram_id }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">綁定時間:</span>
                <span class="info-value">{{ formatDate(user.updated_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 綁定流程卡片 -->
        <div class="binding-process-card" v-if="!isBound">
          <h3 class="card-title">綁定流程</h3>

          <!-- 步驟 1: 生成驗證碼 -->
          <div class="step-card">
            <div class="step-number">1</div>
            <div class="step-content">
              <h4 class="step-title">生成驗證碼</h4>
              <p class="step-description">點擊下方按鈕生成綁定驗證碼</p>
              <button
                @click="requestBinding"
                :disabled="loading || !!verificationCode"
                class="btn btn-primary"
              >
                <span v-if="loading">⏳ 生成中...</span>
                <span v-else-if="verificationCode">✓ 已生成</span>
                <span v-else>🔑 生成驗證碼</span>
              </button>
            </div>
          </div>

          <!-- 步驟 2: 顯示驗證碼 -->
          <div class="step-card" v-if="verificationCode">
            <div class="step-number">2</div>
            <div class="step-content">
              <h4 class="step-title">您的驗證碼</h4>
              <div class="verification-code-display">
                <code class="verification-code">{{ verificationCode }}</code>
                <button @click="copyCode" class="btn btn-secondary btn-sm">
                  {{ copied ? '✓ 已複製' : '📋 複製' }}
                </button>
              </div>
              <div class="expiry-notice">
                ⏰ 驗證碼將在 <strong>10 分鐘</strong>後過期
              </div>
            </div>
          </div>

          <!-- 步驟 3: 綁定說明 -->
          <div class="step-card" v-if="verificationCode">
            <div class="step-number">3</div>
            <div class="step-content">
              <h4 class="step-title">在 Telegram 中綁定</h4>
              <ol class="binding-instructions">
                <li>在 Telegram 搜尋 <strong>@{{ botUsername }}</strong></li>
                <li>點擊 <strong>START</strong> 按鈕開始對話</li>
                <li>發送命令：<code>/bind {{ verificationCode }}</code></li>
                <li>等待綁定成功確認</li>
              </ol>
              <a
                :href="telegramBotUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="btn btn-success"
              >
                🚀 開啟 Telegram Bot
              </a>
            </div>
          </div>

          <!-- 綁定狀態檢查 -->
          <div class="binding-check" v-if="verificationCode">
            <div class="check-status">
              <div class="spinner" v-if="polling"></div>
              <span v-if="polling">⏳ 等待綁定中...</span>
              <span v-else>✓ 完成上述步驟後，系統將自動檢測綁定狀態</span>
            </div>
          </div>
        </div>

        <!-- 已綁定操作區 -->
        <div class="bound-actions-card" v-if="isBound">
          <h3 class="card-title">操作</h3>

          <div class="action-buttons">
            <!-- 測試通知 -->
            <button
              @click="sendTestNotification"
              :disabled="sending"
              class="btn btn-primary"
            >
              <span v-if="sending">⏳ 發送中...</span>
              <span v-else>🔔 發送測試通知</span>
            </button>

            <!-- 通知偏好 -->
            <button
              @click="navigateTo('/account/telegram/preferences')"
              class="btn btn-secondary"
            >
              ⚙️ 通知偏好設置
            </button>

            <!-- 通知歷史 -->
            <button
              @click="navigateTo('/account/telegram/history')"
              class="btn btn-secondary"
            >
              📜 通知歷史記錄
            </button>

            <!-- 解除綁定 -->
            <button
              @click="confirmUnbind"
              class="btn btn-danger"
            >
              🔓 解除綁定
            </button>
          </div>
        </div>

        <!-- 功能說明 -->
        <div class="features-card">
          <h3 class="card-title">通知功能</h3>
          <div class="features-grid">
            <div class="feature-item">
              <div class="feature-icon">📊</div>
              <div class="feature-content">
                <h4>回測完成通知</h4>
                <p>回測執行完成後，立即收到績效摘要和權益曲線圖表</p>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">🧠</div>
              <div class="feature-content">
                <h4>RD-Agent 結果</h4>
                <p>AI 因子挖掘完成時，接收新因子的評估報告</p>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">🔔</div>
              <div class="feature-content">
                <h4>自訂通知偏好</h4>
                <p>設定靜默時段、選擇通知類型、控制圖表顯示</p>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">🔒</div>
              <div class="feature-content">
                <h4>安全隱私保護</h4>
                <p>驗證碼加密傳輸，可隨時解除綁定，保護您的隱私</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const config = useRuntimeConfig()
const { getToken, isAuthenticated } = useAuth()

// 響應式數據
const loading = ref(false)
const polling = ref(false)
const sending = ref(false)
const copied = ref(false)
const isBound = ref(false)
const verificationCode = ref('')
const botUsername = ref('QuantLabBot')
const user = ref(null)
const pollingInterval = ref(null)

// 計算屬性
const telegramBotUrl = computed(() => {
  return `https://t.me/${botUsername.value}`
})

// 載入用戶資料
const loadUserData = async () => {
  try {
    const token = getToken()
    if (!token) {
      console.error('未找到認證 token')
      router.push('/login')
      return
    }

    const response = await fetch(`${config.public.apiBase}/api/v1/users/me`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.status === 401) {
      alert('⚠️ 登入已過期，請重新登入')
      router.push('/login')
      return
    }

    if (response.ok) {
      user.value = await response.json()
      isBound.value = !!user.value.telegram_id
    } else {
      console.error('載入用戶資料失敗:', await response.text())
    }
  } catch (error) {
    console.error('載入用戶資料失敗:', error)
  }
}

// 請求綁定驗證碼
const requestBinding = async () => {
  loading.value = true

  try {
    const token = getToken()
    if (!token) {
      alert('⚠️ 未登入，請先登入')
      router.push('/login')
      loading.value = false
      return
    }

    const response = await fetch(`${config.public.apiBase}/api/v1/telegram/request-binding`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })

    if (response.status === 401) {
      alert('⚠️ 登入已過期，請重新登入')
      router.push('/login')
      return
    }

    if (response.ok) {
      const data = await response.json()
      verificationCode.value = data.verification_code
      botUsername.value = data.bot_username

      // 開始輪詢檢查綁定狀態
      startPolling()

      alert('✅ 驗證碼已生成！請按照步驟在 Telegram 中綁定。')
    } else {
      const error = await response.json()
      alert(`❌ 生成驗證碼失敗：${error.detail || '未知錯誤'}`)
    }
  } catch (error) {
    console.error('請求綁定失敗:', error)
    alert('❌ 網路錯誤，請稍後再試')
  } finally {
    loading.value = false
  }
}

// 複製驗證碼
const copyCode = async () => {
  try {
    // 方法 1: 使用現代 Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(verificationCode.value)
      copied.value = true
      setTimeout(() => {
        copied.value = false
      }, 2000)
      return
    }

    // 方法 2: 降級方案 - 使用舊式 execCommand
    const textArea = document.createElement('textarea')
    textArea.value = verificationCode.value
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()

    try {
      const successful = document.execCommand('copy')
      if (successful) {
        copied.value = true
        setTimeout(() => {
          copied.value = false
        }, 2000)
      } else {
        alert('❌ 複製失敗，請手動複製驗證碼')
      }
    } catch (err) {
      console.error('execCommand 複製失敗:', err)
      alert('❌ 複製失敗，請手動複製驗證碼')
    } finally {
      document.body.removeChild(textArea)
    }
  } catch (error) {
    console.error('複製失敗:', error)
    alert('❌ 複製失敗，請手動複製驗證碼')
  }
}

// 開始輪詢綁定狀態
const startPolling = () => {
  polling.value = true

  pollingInterval.value = setInterval(async () => {
    try {
      const response = await fetch(`${config.public.apiBase}/api/v1/telegram/check-binding`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()

        if (data.is_bound) {
          // 綁定成功
          stopPolling()
          isBound.value = true
          verificationCode.value = ''
          await loadUserData()

          alert('🎉 綁定成功！您現在可以接收 Telegram 通知了。')
        }
      }
    } catch (error) {
      console.error('檢查綁定狀態失敗:', error)
    }
  }, 3000) // 每 3 秒檢查一次
}

// 停止輪詢
const stopPolling = () => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
    polling.value = false
  }
}

// 發送測試通知
const sendTestNotification = async () => {
  sending.value = true

  try {
    const response = await fetch(`${config.public.apiBase}/api/v1/telegram/test-notification`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        include_image: false
      })
    })

    if (response.ok) {
      const data = await response.json()

      if (data.success) {
        alert('✅ 測試通知已發送！請檢查您的 Telegram。')
      } else {
        alert(`❌ 發送失敗：${data.message}`)
      }
    } else {
      const error = await response.json()
      alert(`❌ 發送失敗：${error.detail || '未知錯誤'}`)
    }
  } catch (error) {
    console.error('發送測試通知失敗:', error)
    alert('❌ 網路錯誤，請稍後再試')
  } finally {
    sending.value = false
  }
}

// 確認解除綁定
const confirmUnbind = () => {
  if (confirm('確定要解除 Telegram 綁定嗎？\n解除後將不再接收通知。')) {
    unbind()
  }
}

// 解除綁定
const unbind = async () => {
  try {
    const response = await fetch(`${config.public.apiBase}/api/v1/telegram/unbind`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    })

    if (response.ok) {
      isBound.value = false
      user.value = null

      alert('✅ 已成功解除 Telegram 綁定')
      await loadUserData()
    } else {
      const error = await response.json()
      alert(`❌ 解除綁定失敗：${error.detail || '未知錯誤'}`)
    }
  } catch (error) {
    console.error('解除綁定失敗:', error)
    alert('❌ 網路錯誤，請稍後再試')
  }
}

// 格式化日期（使用台灣時區）
const { formatToTaiwanTime } = useDateTime()
const formatDate = (dateString) => {
  if (!dateString) return '未知'
  return formatToTaiwanTime(dateString)
}

// 導航
const navigateTo = (path) => {
  router.push(path)
}

// 生命週期
onMounted(() => {
  // 檢查登入狀態
  if (!isAuthenticated()) {
    alert('⚠️ 請先登入')
    router.push('/login')
    return
  }

  loadUserData()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.telegram-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.telegram-main {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.telegram-page {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.page-header {
  margin-bottom: 2rem;
  text-align: center;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #2d3748;
  margin-bottom: 0.5rem;
}

.page-subtitle {
  font-size: 1rem;
  color: #718096;
}

/* 綁定狀態卡片 */
.binding-status-card {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 2rem;
  background: #f7fafc;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  margin-bottom: 2rem;
  transition: all 0.3s;
}

.binding-status-card.is-bound {
  background: #f0fff4;
  border-color: #48bb78;
}

.status-icon {
  font-size: 3rem;
}

.status-content {
  flex: 1;
}

.status-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 0.5rem;
}

.status-description {
  color: #718096;
  margin-bottom: 1rem;
}

.status-info {
  display: flex;
  gap: 2rem;
  margin-top: 1rem;
}

.info-item {
  display: flex;
  gap: 0.5rem;
}

.info-label {
  font-weight: 600;
  color: #4a5568;
}

.info-value {
  color: #718096;
}

/* 步驟卡片 */
.binding-process-card,
.bound-actions-card,
.features-card {
  margin-bottom: 2rem;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e2e8f0;
}

.step-card {
  display: flex;
  gap: 1.5rem;
  padding: 1.5rem;
  background: #f7fafc;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.step-number {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #667eea;
  color: white;
  border-radius: 50%;
  font-weight: 700;
  font-size: 1.25rem;
}

.step-content {
  flex: 1;
}

.step-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 0.5rem;
}

.step-description {
  color: #718096;
  margin-bottom: 1rem;
}

/* 驗證碼顯示 */
.verification-code-display {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.verification-code {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  padding: 1rem 1.5rem;
  background: white;
  border: 2px solid #667eea;
  border-radius: 8px;
  color: #667eea;
}

.expiry-notice {
  padding: 0.75rem;
  background: #fff5f5;
  border-left: 4px solid #fc8181;
  border-radius: 4px;
  color: #c53030;
}

/* 綁定說明 */
.binding-instructions {
  margin: 1rem 0;
  padding-left: 1.5rem;
}

.binding-instructions li {
  margin-bottom: 0.5rem;
  color: #4a5568;
}

.binding-instructions strong,
.binding-instructions code {
  color: #667eea;
  font-weight: 600;
}

/* 綁定檢查 */
.binding-check {
  padding: 1.5rem;
  background: #fffaf0;
  border: 2px solid #fbd38d;
  border-radius: 8px;
  text-align: center;
}

.check-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 3px solid #e2e8f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 按鈕 */
.btn {
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 1rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5a67d8;
}

.btn-secondary {
  background: #cbd5e0;
  color: #2d3748;
}

.btn-secondary:hover:not(:disabled) {
  background: #a0aec0;
}

.btn-success {
  background: #48bb78;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #38a169;
}

.btn-danger {
  background: #f56565;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #e53e3e;
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

/* 操作按鈕 */
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

/* 功能網格 */
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.feature-item {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  background: #f7fafc;
  border-radius: 8px;
  transition: transform 0.2s;
}

.feature-item:hover {
  transform: translateY(-2px);
}

.feature-icon {
  font-size: 2rem;
}

.feature-content h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 0.5rem;
}

.feature-content p {
  font-size: 0.875rem;
  color: #718096;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .telegram-page {
    padding: 1rem;
  }

  .page-header {
    .page-title {
      font-size: 1.75rem;
    }

    .page-subtitle {
      font-size: 0.9rem;
    }
  }

  .binding-status-card {
    flex-direction: column;
    text-align: center;

    .status-icon {
      font-size: 3rem;
    }
  }

  .step-card {
    flex-direction: column;
    align-items: flex-start;

    .step-number {
      margin-bottom: 1rem;
    }
  }

  .verification-code-display {
    flex-direction: column;
    align-items: stretch;

    .verification-code {
      font-size: 1.25rem;
      padding: 0.75rem;
    }

    .btn-sm {
      width: 100%;
    }
  }

  .binding-instructions {
    font-size: 0.9rem;

    code {
      font-size: 0.85rem;
      padding: 0.25rem 0.5rem;
    }
  }

  .action-buttons {
    flex-direction: column;

    .btn {
      width: 100%;
    }
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }
}

@media (max-width: 480px) {
  .telegram-page {
    padding: 0.75rem;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .binding-status-card,
  .binding-process-card,
  .features-card {
    padding: 1.25rem;
  }

  .card-title {
    font-size: 1.125rem;
  }

  .btn {
    padding: 0.65rem 1rem;
    font-size: 0.9rem;
  }
}
</style>
