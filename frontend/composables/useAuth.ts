export const useAuth = () => {
  const config = useRuntimeConfig()
  const router = useRouter()

  interface LoginCredentials {
    username: string
    password: string
  }

  interface RegisterData {
    email: string
    username: string
    password: string
    full_name: string
  }

  interface AuthResponse {
    access_token: string
    refresh_token: string
    token_type: string
  }

  interface User {
    id: number
    email: string
    username: string
    full_name: string
    is_active: boolean
    is_superuser: boolean
    member_level: number
    created_at: string
  }

  // 登入
  const login = async (credentials: LoginCredentials) => {
    try {
      const response = await $fetch<AuthResponse>(`${config.public.apiBase}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: credentials,
      })

      // 儲存 token 到 localStorage
      if (process.client) {
        localStorage.setItem('access_token', response.access_token)
        localStorage.setItem('refresh_token', response.refresh_token)

        // 清除舊用戶的信息緩存，確保載入新用戶資訊
        localStorage.removeItem('user_info_cache')
      }

      return { success: true, data: response }
    } catch (error: any) {
      console.error('Login error:', error)
      console.error('Error data:', error.data)
      console.error('Error detail:', error.data?.detail)

      let errorMessage = 'Login failed. Please check your credentials.'

      // 處理具體的錯誤訊息
      if (error.data?.detail) {
        if (typeof error.data.detail === 'string') {
          errorMessage = error.data.detail
        } else if (Array.isArray(error.data.detail)) {
          errorMessage = error.data.detail.map((err: any) => {
            const field = err.loc ? err.loc.join('.') : ''
            const msg = err.msg || err.message || ''
            return field ? `${field}: ${msg}` : msg
          }).join('; ')
        }
      } else if (error.message) {
        errorMessage = error.message
      } else if (error.statusMessage) {
        errorMessage = error.statusMessage
      }

      // 翻譯常見錯誤訊息
      if (errorMessage.includes('Incorrect username or password')) {
        errorMessage = '用戶名或密碼錯誤'
      }

      return { success: false, error: errorMessage }
    }
  }

  // 註冊
  const register = async (data: RegisterData) => {
    try {
      const response = await $fetch<User>(`${config.public.apiBase}/api/v1/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: data,
      })

      return { success: true, data: response }
    } catch (error: any) {
      console.error('Register error:', error)
      console.error('Error data:', error.data)
      console.error('Error detail:', error.data?.detail)

      let errorMessage = 'Registration failed. Please try again.'

      // 處理具體的錯誤訊息
      if (error.data?.detail) {
        if (typeof error.data.detail === 'string') {
          errorMessage = error.data.detail
        } else if (Array.isArray(error.data.detail)) {
          // Pydantic 驗證錯誤
          errorMessage = error.data.detail.map((err: any) => {
            const field = err.loc ? err.loc.join('.') : ''
            const msg = err.msg || err.message || ''
            return field ? `${field}: ${msg}` : msg
          }).join('; ')
        } else if (typeof error.data.detail === 'object') {
          // 處理物件格式的錯誤
          errorMessage = JSON.stringify(error.data.detail)
        }
      } else if (error.message) {
        errorMessage = error.message
      } else if (error.statusMessage) {
        errorMessage = error.statusMessage
      }

      // 翻譯常見錯誤訊息
      if (errorMessage.includes('Email already registered')) {
        errorMessage = '此 Email 已被註冊'
      } else if (errorMessage.includes('Username already exists')) {
        errorMessage = '此用戶名已存在'
      }

      return { success: false, error: errorMessage }
    }
  }

  // 登出
  const logout = () => {
    if (process.client) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
    router.push('/login')
  }

  // 獲取當前 token
  const getToken = () => {
    if (process.client) {
      return localStorage.getItem('access_token')
    }
    return null
  }

  // 檢查 token 是否過期
  const isTokenExpired = (token: string): boolean => {
    try {
      // JWT token 格式: header.payload.signature
      const payload = JSON.parse(atob(token.split('.')[1]))
      const exp = payload.exp

      if (!exp) {
        return true  // 沒有過期時間，視為已過期
      }

      // exp 是 Unix timestamp (秒)，Date.now() 是毫秒
      return Date.now() >= exp * 1000
    } catch (error) {
      console.error('Failed to parse token:', error)
      return true  // 解析失敗，視為已過期
    }
  }

  // 檢查是否已登入（檢查 token 存在且未過期）
  const isAuthenticated = () => {
    const token = getToken()
    if (!token) {
      return false
    }

    // 檢查 token 是否過期
    if (isTokenExpired(token)) {
      // Token 已過期，清除並返回 false
      if (process.client) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      }
      return false
    }

    return true
  }

  // 獲取當前用戶資訊
  const getCurrentUser = async () => {
    // SSR 防護：僅在客戶端執行
    if (!process.client) {
      return { success: false, error: 'Cannot get user info in SSR mode' }
    }

    try {
      const token = getToken()
      if (!token) {
        return { success: false, error: 'No token found' }
      }

      const response = await $fetch<User>(`${config.public.apiBase}/api/v1/auth/me`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      return { success: true, data: response }
    } catch (error: any) {
      console.error('Get current user error:', error)

      // 處理 401 Unauthorized - token 過期或無效
      if (error.status === 401 || error.statusCode === 401) {
        console.warn('Token expired or invalid, clearing tokens')
        // 清除過期的 tokens
        if (process.client) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        }
        // 重定向到登入頁面
        router.push('/login')
        return { success: false, error: 'Token expired or invalid' }
      }

      // 其他錯誤
      let errorMessage = 'Failed to get user info'
      if (error.data?.detail) {
        errorMessage = typeof error.data.detail === 'string' ? error.data.detail : JSON.stringify(error.data.detail)
      } else if (error.message) {
        errorMessage = error.message
      }

      return { success: false, error: errorMessage }
    }
  }

  return {
    login,
    register,
    logout,
    getToken,
    isAuthenticated,
    getCurrentUser,
  }
}
