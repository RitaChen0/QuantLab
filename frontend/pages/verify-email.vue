<template>
  <div class="verify-page">
    <div class="verify-container">
      <div class="verify-card">
        <!-- Loading State -->
        <div v-if="verifying" class="state-container">
          <div class="spinner"></div>
          <h1 class="title">驗證中...</h1>
          <p class="message">請稍候，我們正在驗證您的郵箱</p>
        </div>

        <!-- Success State -->
        <div v-else-if="success" class="state-container success">
          <div class="icon success-icon">✓</div>
          <h1 class="title">驗證成功！</h1>
          <p class="message">您的郵箱已成功驗證，現在可以登入了</p>
          <button @click="goToLogin" class="btn-primary">
            前往登入
          </button>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="state-container error">
          <div class="icon error-icon">✗</div>
          <h1 class="title">驗證失敗</h1>
          <p class="message error-text">{{ errorMessage }}</p>
          <div class="action-buttons">
            <button @click="resendEmail" class="btn-secondary" :disabled="resending">
              {{ resending ? '發送中...' : '重新發送驗證郵件' }}
            </button>
            <button @click="goToRegister" class="btn-link">
              返回註冊頁面
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const config = useRuntimeConfig()

const verifying = ref(true)
const success = ref(false)
const error = ref(false)
const errorMessage = ref('')
const resending = ref(false)

// Get token from URL
const token = route.query.token as string

// Verify email on mount
onMounted(async () => {
  if (!token) {
    error.value = true
    errorMessage.value = '無效的驗證連結'
    verifying.value = false
    return
  }

  try {
    const response = await $fetch(`${config.public.apiBase}/api/v1/auth/verify-email?token=${token}`, {
      method: 'POST',
    })

    success.value = true
    verifying.value = false

    // Redirect to login after 2 seconds
    setTimeout(() => {
      router.push('/login')
    }, 2000)
  } catch (err: any) {
    verifying.value = false
    error.value = true

    if (err.data?.detail) {
      errorMessage.value = err.data.detail
    } else {
      errorMessage.value = '驗證失敗，請稍後再試'
    }
  }
})

const goToLogin = () => {
  router.push('/login')
}

const goToRegister = () => {
  router.push('/register')
}

const resendEmail = async () => {
  // This would need the user's email, which we don't have from the token
  // You might want to add an email input field for this
  alert('請返回登入頁面，使用「重新發送驗證郵件」功能')
}
</script>

<style scoped lang="scss">
.verify-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.verify-container {
  width: 100%;
  max-width: 500px;
  padding: 1rem;
}

.verify-card {
  background: white;
  padding: 3rem 2.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.state-container {
  text-align: center;
}

.spinner {
  width: 60px;
  height: 60px;
  border: 4px solid #f3f4f6;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1.5rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 3rem;
  font-weight: bold;
  margin: 0 auto 1.5rem;
}

.success-icon {
  background: #dcfce7;
  color: #16a34a;
}

.error-icon {
  background: #fee2e2;
  color: #dc2626;
}

.title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 1rem 0;
}

.message {
  color: #6b7280;
  font-size: 1rem;
  margin: 0 0 2rem 0;
  line-height: 1.5;
}

.error-text {
  color: #dc2626;
}

.btn-primary {
  width: 100%;
  padding: 0.75rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: #2563eb;
  }
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.btn-secondary {
  width: 100%;
  padding: 0.75rem;
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;

  &:hover:not(:disabled) {
    background: #e5e7eb;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.btn-link {
  width: 100%;
  padding: 0.75rem;
  background: transparent;
  color: #3b82f6;
  border: none;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.2s;

  &:hover {
    color: #2563eb;
    text-decoration: underline;
  }
}
</style>
