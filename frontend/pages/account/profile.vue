<template>
  <div class="profile-page">
    <AppHeader />

    <div class="profile-container">
      <div class="profile-header">
        <h1>👤 用戶資料編輯</h1>
        <p class="subtitle">管理您的個人資料和偏好設定</p>
      </div>

      <div class="profile-content">
        <!-- 基本資料卡片 -->
        <div class="profile-card">
          <div class="card-header">
            <h2>基本資料</h2>
          </div>

          <div class="card-body">
            <div class="form-group">
              <label>用戶名稱</label>
              <input
                type="text"
                :value="username"
                disabled
                class="form-input disabled"
              />
              <p class="field-hint">用戶名稱無法修改</p>
            </div>

            <div class="form-group">
              <label>Email</label>
              <input
                v-model="formData.email"
                type="email"
                class="form-input"
                placeholder="請輸入 Email"
              />
            </div>

            <div class="form-group">
              <label>全名</label>
              <input
                v-model="formData.fullName"
                type="text"
                class="form-input"
                placeholder="請輸入全名"
              />
            </div>

            <div class="form-actions">
              <button @click="handleUpdateProfile" class="btn-primary" :disabled="isUpdating">
                <span v-if="!isUpdating">💾 儲存變更</span>
                <span v-else>⏳ 儲存中...</span>
              </button>
              <button @click="handleReset" class="btn-secondary">
                🔄 重置
              </button>
            </div>

            <div v-if="updateMessage" class="message" :class="updateSuccess ? 'success' : 'error'">
              {{ updateMessage }}
            </div>
          </div>
        </div>

        <!-- 會員資訊卡片 -->
        <div class="profile-card">
          <div class="card-header">
            <h2>會員資訊</h2>
          </div>

          <div class="card-body">
            <div class="info-row">
              <span class="info-label">會員等級</span>
              <span class="info-value">
                <span class="member-badge" :class="memberLevelClass">
                  {{ memberLevelText }}
                </span>
              </span>
            </div>

            <div class="info-row">
              <span class="info-label">權限</span>
              <span class="info-value">
                <span v-if="isSuperuser" class="admin-badge">管理者</span>
                <span v-else class="user-badge">一般用戶</span>
              </span>
            </div>

            <div class="info-row">
              <span class="info-label">註冊日期</span>
              <span class="info-value">{{ formatDate(createdAt) }}</span>
            </div>

            <div class="info-row">
              <span class="info-label">最後登入</span>
              <span class="info-value">{{ formatDate(lastLoginAt) }}</span>
            </div>
          </div>
        </div>

        <!-- 修改密碼卡片 -->
        <div class="profile-card">
          <div class="card-header">
            <h2>修改密碼</h2>
          </div>

          <div class="card-body">
            <div class="form-group">
              <label>目前密碼</label>
              <input
                v-model="passwordData.currentPassword"
                type="password"
                class="form-input"
                placeholder="請輸入目前密碼"
              />
            </div>

            <div class="form-group">
              <label>新密碼</label>
              <input
                v-model="passwordData.newPassword"
                type="password"
                class="form-input"
                placeholder="請輸入新密碼（至少 8 個字元）"
              />
            </div>

            <div class="form-group">
              <label>確認新密碼</label>
              <input
                v-model="passwordData.confirmPassword"
                type="password"
                class="form-input"
                placeholder="請再次輸入新密碼"
              />
            </div>

            <div class="form-actions">
              <button @click="handleUpdatePassword" class="btn-primary" :disabled="isUpdatingPassword">
                <span v-if="!isUpdatingPassword">🔐 更新密碼</span>
                <span v-else>⏳ 更新中...</span>
              </button>
            </div>

            <div v-if="passwordMessage" class="message" :class="passwordSuccess ? 'success' : 'error'">
              {{ passwordMessage }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const { username, fullName, email, isSuperuser, memberLevel, createdAt, lastLoginAt, loadUserInfo } = useUserInfo()

// 載入用戶資料
onMounted(async () => {
  await loadUserInfo()
})

// 表單資料
const formData = ref({
  email: email.value || '',
  fullName: fullName.value || ''
})

// 密碼表單
const passwordData = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 狀態
const isUpdating = ref(false)
const isUpdatingPassword = ref(false)
const updateMessage = ref('')
const updateSuccess = ref(false)
const passwordMessage = ref('')
const passwordSuccess = ref(false)

// 監聽用戶資料變化
watch([email, fullName], () => {
  formData.value.email = email.value || ''
  formData.value.fullName = fullName.value || ''
})

// 會員等級樣式
const memberLevelClass = computed(() => {
  const level = memberLevel.value || 0
  if (level >= 7) return 'creator'      // 7-9: 系統管理員/創造者
  if (level >= 5) return 'admin'        // 5-6: 系統推廣/管理員
  if (level >= 4) return 'vip'          // 4: VIP會員
  if (level >= 3) return 'premium'      // 3: 高階會員
  if (level >= 2) return 'pro'          // 2: 中階會員
  if (level >= 1) return 'basic'        // 1: 普通會員
  return 'free'                         // 0: 註冊會員
})

const memberLevelText = computed(() => {
  const level = memberLevel.value || 0
  const levels = [
    '註冊會員',      // 0
    '普通會員',      // 1
    '中階會員',      // 2
    '高階會員',      // 3
    'VIP會員',       // 4
    '系統推廣會員',  // 5
    '系統管理員1',   // 6
    '系統管理員2',   // 7
    '系統管理員3',   // 8
    '創造者等級'     // 9
  ]
  return levels[level] || `未知等級 (${level})`
})

// 格式化日期（使用台灣時區）
const { formatToTaiwanTime } = useDateTime()
const formatDate = (date: any) => {
  if (!date) return '未知'
  return formatToTaiwanTime(date, { showSeconds: false })
}

// 更新個人資料
const handleUpdateProfile = async () => {
  try {
    isUpdating.value = true
    updateMessage.value = ''

    const config = useRuntimeConfig()
    const token = localStorage.getItem('token')

    const response = await fetch(`${config.public.apiBase}/api/v1/users/me`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        email: formData.value.email,
        full_name: formData.value.fullName
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '更新失敗')
    }

    updateSuccess.value = true
    updateMessage.value = '✅ 個人資料更新成功！'

    // 3 秒後清除訊息
    setTimeout(() => {
      updateMessage.value = ''
    }, 3000)

  } catch (error: any) {
    updateSuccess.value = false
    updateMessage.value = `❌ ${error.message}`
  } finally {
    isUpdating.value = false
  }
}

// 重置表單
const handleReset = () => {
  formData.value.email = email.value || ''
  formData.value.fullName = fullName.value || ''
  updateMessage.value = ''
}

// 更新密碼
const handleUpdatePassword = async () => {
  try {
    isUpdatingPassword.value = true
    passwordMessage.value = ''

    // 驗證
    if (!passwordData.value.currentPassword || !passwordData.value.newPassword || !passwordData.value.confirmPassword) {
      throw new Error('請填寫所有欄位')
    }

    if (passwordData.value.newPassword.length < 8) {
      throw new Error('新密碼至少需要 8 個字元')
    }

    if (passwordData.value.newPassword !== passwordData.value.confirmPassword) {
      throw new Error('新密碼與確認密碼不一致')
    }

    const config = useRuntimeConfig()
    const token = localStorage.getItem('token')

    const response = await fetch(`${config.public.apiBase}/api/v1/users/me/password`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        current_password: passwordData.value.currentPassword,
        new_password: passwordData.value.newPassword
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '更新失敗')
    }

    passwordSuccess.value = true
    passwordMessage.value = '✅ 密碼更新成功！'

    // 清空表單
    passwordData.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    }

    // 3 秒後清除訊息
    setTimeout(() => {
      passwordMessage.value = ''
    }, 3000)

  } catch (error: any) {
    passwordSuccess.value = false
    passwordMessage.value = `❌ ${error.message}`
  } finally {
    isUpdatingPassword.value = false
  }
}
</script>

<style scoped lang="scss">
.profile-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.profile-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
}

.profile-header {
  text-align: center;
  margin-bottom: 2rem;
  color: white;

  h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
  }

  .subtitle {
    font-size: 1rem;
    opacity: 0.9;
  }
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.profile-card {
  background: white;
  border-radius: 1rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.card-header {
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;

  h2 {
    font-size: 1.25rem;
    margin: 0;
  }
}

.card-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;

  &:last-child {
    margin-bottom: 0;
  }

  label {
    display: block;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #333;
  }
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 0.5rem;
  font-size: 1rem;
  transition: all 0.2s;

  &:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  &.disabled {
    background: #f5f5f5;
    color: #999;
    cursor: not-allowed;
  }
}

.field-hint {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #666;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.btn-primary,
.btn-secondary {
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }
}

.btn-secondary {
  background: #f5f5f5;
  color: #333;

  &:hover:not(:disabled) {
    background: #e0e0e0;
  }
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  border-bottom: 1px solid #f0f0f0;

  &:last-child {
    border-bottom: none;
  }
}

.info-label {
  font-weight: 600;
  color: #666;
}

.info-value {
  color: #333;
  font-weight: 500;
}

.member-badge {
  padding: 0.4rem 1rem;
  border-radius: 1rem;
  font-size: 0.9rem;
  font-weight: 600;

  &.free {
    background: #e0e0e0;
    color: #666;
  }

  &.basic {
    background: #e3f2fd;
    color: #1976d2;
  }

  &.pro {
    background: #f3e5f5;
    color: #7b1fa2;
  }

  &.premium {
    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
    color: #fff;
  }

  &.vip {
    background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%);
    color: #fff;
    font-weight: 700;
  }

  &.admin {
    background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
    color: #fff;
    font-weight: 700;
  }

  &.creator {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    color: #fff;
    font-weight: 700;
    box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
  }
}

.admin-badge {
  padding: 0.4rem 1rem;
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  color: #333;
  border-radius: 1rem;
  font-size: 0.9rem;
  font-weight: 600;
}

.user-badge {
  padding: 0.4rem 1rem;
  background: #e3f2fd;
  color: #1976d2;
  border-radius: 1rem;
  font-size: 0.9rem;
  font-weight: 600;
}

.message {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 0.5rem;
  font-weight: 500;

  &.success {
    background: #e8f5e9;
    color: #2e7d32;
    border: 1px solid #4caf50;
  }

  &.error {
    background: #ffebee;
    color: #c62828;
    border: 1px solid #f44336;
  }
}

@media (max-width: 768px) {
  .profile-container {
    padding: 1rem;
  }

  .profile-header {
    h1 {
      font-size: 1.5rem;
    }
  }

  .form-actions {
    flex-direction: column;
  }

  .info-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>
