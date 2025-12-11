<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-card">
        <h1 class="text-3xl font-bold text-center mb-8">登入 QuantLab</h1>

        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label for="username">用戶名或 Email</label>
            <input
              id="username"
              v-model="form.username"
              type="text"
              placeholder="username or email"
              required
            >
          </div>

          <div class="form-group">
            <label for="password">密碼</label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              placeholder="••••••••"
              required
            >
          </div>

          <button
            type="submit"
            class="btn-submit"
            :disabled="isLoading"
          >
            {{ isLoading ? '登入中...' : '登入' }}
          </button>
        </form>

        <div class="text-center mt-6">
          <p class="text-gray-600">
            還沒有帳號？
            <NuxtLink to="/register" class="text-primary-600 hover:text-primary-700">
              註冊
            </NuxtLink>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const { login } = useAuth()
const router = useRouter()

const form = reactive({
  username: '',
  password: ''
})

const isLoading = ref(false)
const errorMessage = ref('')

const handleLogin = async () => {
  console.log('=== Login button clicked ===')
  console.log('Username:', form.username)
  console.log('Password:', form.password ? '***' : '(empty)')

  // 驗證表單
  if (!form.username || !form.password) {
    errorMessage.value = '請輸入用戶名和密碼'
    console.error('Validation failed: empty fields')
    return
  }

  errorMessage.value = ''
  isLoading.value = true

  try {
    console.log('Calling login API...')
    const result = await login({
      username: form.username,
      password: form.password
    })

    console.log('Login result:', result)

    if (result.success) {
      console.log('Login successful! Redirecting to dashboard...')
      // 登入成功，強制刷新並跳轉到儀表板
      // 使用 window.location 而非 router.push 以確保完整重新載入
      window.location.href = '/dashboard'
    } else {
      console.error('Login failed:', result.error)

      // 檢查是否為郵箱未驗證錯誤
      if (result.error && result.error.includes('Email not verified')) {
        errorMessage.value = '郵箱尚未驗證。請檢查您的郵箱（包括垃圾郵件箱）並點擊驗證連結。'
      } else {
        errorMessage.value = result.error || '登入失敗，請檢查您的帳號密碼'
      }
    }
  } catch (error: any) {
    console.error('Login exception:', error)
    errorMessage.value = error?.message || '登入過程發生錯誤，請稍後再試'
  } finally {
    isLoading.value = false
    console.log('Login process complete, isLoading:', isLoading.value)
  }
}
</script>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-container {
  width: 100%;
  max-width: 400px;
  padding: 1rem;
}

.login-card {
  background: white;
  padding: 2.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 1.5rem;

  label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #374151;
  }

  input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.5rem;
    font-size: 1rem;
    transition: border-color 0.2s;

    &:focus {
      outline: none;
      border-color: #3b82f6;
    }
  }
}

.btn-submit {
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

  &:hover:not(:disabled) {
    background: #2563eb;
  }

  &:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }
}

.error-message {
  padding: 1rem;
  margin-bottom: 1.5rem;
  background-color: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  font-size: 0.875rem;
}
</style>
