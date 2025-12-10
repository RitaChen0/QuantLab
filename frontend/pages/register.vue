<template>
  <div class="register-page">
    <div class="register-container">
      <div class="register-card">
        <h1 class="text-3xl font-bold text-center mb-8">註冊 QuantLab</h1>

        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <div v-if="successMessage" class="success-message">
          {{ successMessage }}
        </div>

        <form @submit.prevent="handleRegister">
          <div class="form-group">
            <label for="email">Email *</label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              placeholder="your@email.com"
              required
            >
          </div>

          <div class="form-group">
            <label for="username">用戶名 *</label>
            <input
              id="username"
              v-model="form.username"
              type="text"
              placeholder="username"
              required
              minlength="3"
            >
            <small class="text-gray-500">至少 3 個字元</small>
          </div>

          <div class="form-group">
            <label for="full_name">全名 *</label>
            <input
              id="full_name"
              v-model="form.full_name"
              type="text"
              placeholder="Your Name"
              required
            >
          </div>

          <div class="form-group">
            <label for="password">密碼 *</label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              placeholder="••••••••"
              required
              minlength="8"
            >
            <small class="text-gray-500">至少 8 個字元</small>
          </div>

          <div class="form-group">
            <label for="confirm_password">確認密碼 *</label>
            <input
              id="confirm_password"
              v-model="form.confirm_password"
              type="password"
              placeholder="••••••••"
              required
              minlength="8"
            >
          </div>

          <button
            type="submit"
            class="btn-submit"
            :disabled="isLoading"
          >
            {{ isLoading ? '註冊中...' : '註冊' }}
          </button>
        </form>

        <div class="text-center mt-6">
          <p class="text-gray-600">
            已經有帳號？
            <NuxtLink to="/login" class="text-primary-600 hover:text-primary-700">
              登入
            </NuxtLink>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const { register } = useAuth()
const router = useRouter()

const form = reactive({
  email: '',
  username: '',
  full_name: '',
  password: '',
  confirm_password: ''
})

const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const handleRegister = async () => {
  // 重置訊息
  errorMessage.value = ''
  successMessage.value = ''

  // 驗證密碼是否一致
  if (form.password !== form.confirm_password) {
    errorMessage.value = '密碼與確認密碼不一致'
    return
  }

  // 驗證密碼長度
  if (form.password.length < 8) {
    errorMessage.value = '密碼必須至少 8 個字元'
    return
  }

  // 驗證用戶名長度
  if (form.username.length < 3) {
    errorMessage.value = '用戶名必須至少 3 個字元'
    return
  }

  isLoading.value = true

  try {
    console.log('Sending registration request...')

    const result = await register({
      email: form.email,
      username: form.username,
      full_name: form.full_name,
      password: form.password
    })

    console.log('Registration result:', result)

    if (result.success) {
      successMessage.value = '註冊成功！我們已向您的郵箱發送驗證連結，請檢查您的郵箱（包括垃圾郵件箱）並點擊驗證連結。驗證後即可登入。'

      // 清空表單
      form.email = ''
      form.username = ''
      form.full_name = ''
      form.password = ''
      form.confirm_password = ''

      // 10 秒後跳轉到登入頁（給用戶時間閱讀訊息）
      setTimeout(() => {
        router.push('/login')
      }, 10000)
    } else {
      errorMessage.value = result.error || '註冊失敗，請稍後再試'
      console.error('Registration failed:', result.error)
    }
  } catch (error: any) {
    console.error('Register exception:', error)
    errorMessage.value = error?.message || '註冊過程發生錯誤，請稍後再試'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped lang="scss">
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-container {
  width: 100%;
  max-width: 500px;
  padding: 1rem;
}

.register-card {
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

    &:disabled {
      background-color: #f3f4f6;
      cursor: not-allowed;
    }
  }

  small {
    display: block;
    margin-top: 0.25rem;
    font-size: 0.875rem;
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

.success-message {
  padding: 1rem;
  margin-bottom: 1.5rem;
  background-color: #d1fae5;
  border: 1px solid #a7f3d0;
  border-radius: 0.5rem;
  color: #065f46;
  font-size: 0.875rem;
}

.text-primary-600 {
  color: #2563eb;
}

.text-primary-700 {
  color: #1d4ed8;
}

.text-gray-600 {
  color: #4b5563;
}

.text-gray-500 {
  color: #6b7280;
}
</style>
