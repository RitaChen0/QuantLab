/**
 * 用戶資訊管理 Composable
 * 提供統一的用戶資訊載入和管理功能，消除跨頁面的代碼重複
 * 包含快取機制，避免重複 API 調用
 */

// 快取鍵名
const CACHE_KEY = 'user_info_cache'
const CACHE_EXPIRY_MS = 5 * 60 * 1000 // 5 分鐘快取

interface CachedUserInfo {
  username: string
  fullName: string
  email: string
  isSuperuser: boolean
  memberLevel: number
  createdAt: string | null
  lastLoginAt: string | null
  timestamp: number
}

export const useUserInfo = () => {
  const { getCurrentUser } = useAuth()

  // 用戶資訊狀態
  const username = ref('')
  const fullName = ref('')
  const email = ref('')
  const isSuperuser = ref(false)
  const memberLevel = ref(0)
  const createdAt = ref<string | null>(null)
  const lastLoginAt = ref<string | null>(null)
  const loading = ref(false)
  const error = ref('')
  const initialized = ref(false) // 追蹤是否已初始化

  /**
   * 從 localStorage 同步讀取快取的用戶資訊（僅返回數據，不修改狀態）
   * 用於組合式函數初始化時的快速載入
   */
  const loadFromCacheSync = (): CachedUserInfo | null => {
    if (!process.client) return null

    try {
      const cached = localStorage.getItem(CACHE_KEY)
      if (!cached) return null

      const data: CachedUserInfo = JSON.parse(cached)
      const now = Date.now()

      // 檢查快取是否過期
      if (now - data.timestamp > CACHE_EXPIRY_MS) {
        localStorage.removeItem(CACHE_KEY)
        return null
      }

      return data
    } catch (err) {
      console.error('Failed to load user info from cache:', err)
      return null
    }
  }

  // 在組合式函數初始化時立即嘗試從快取載入
  // 這樣可以避免頁面首次渲染時顯示「用戶」的閃爍
  if (process.client && !initialized.value) {
    const cached = loadFromCacheSync()
    if (cached) {
      username.value = cached.username
      fullName.value = cached.fullName
      email.value = cached.email
      isSuperuser.value = cached.isSuperuser || false
      memberLevel.value = cached.memberLevel || 0
      createdAt.value = cached.createdAt || null
      lastLoginAt.value = cached.lastLoginAt || null
      initialized.value = true
    }
  }

  /**
   * 從 localStorage 讀取快取的用戶資訊（修改狀態版本）
   */
  const loadFromCache = (): boolean => {
    const cached = loadFromCacheSync()
    if (!cached) return false

    // 使用快取數據
    username.value = cached.username
    fullName.value = cached.fullName
    email.value = cached.email
    isSuperuser.value = cached.isSuperuser || false
    memberLevel.value = cached.memberLevel || 0
    createdAt.value = cached.createdAt || null
    lastLoginAt.value = cached.lastLoginAt || null
    initialized.value = true
    return true
  }

  /**
   * 儲存用戶資訊到 localStorage 快取
   */
  const saveToCache = (
    usernameVal: string,
    fullNameVal: string,
    emailVal: string,
    isSuperuserVal: boolean,
    memberLevelVal: number,
    createdAtVal: string | null,
    lastLoginAtVal: string | null
  ) => {
    if (!process.client) return

    try {
      const data: CachedUserInfo = {
        username: usernameVal,
        fullName: fullNameVal,
        email: emailVal,
        isSuperuser: isSuperuserVal,
        memberLevel: memberLevelVal,
        createdAt: createdAtVal,
        lastLoginAt: lastLoginAtVal,
        timestamp: Date.now()
      }
      localStorage.setItem(CACHE_KEY, JSON.stringify(data))
    } catch (err) {
      console.error('Failed to save user info to cache:', err)
    }
  }

  /**
   * 載入當前用戶資訊
   * 優先使用快取，快取過期或不存在時才調用 API
   * @param forceRefresh - 強制刷新，忽略快取
   * @returns Promise<boolean> - 是否成功載入
   */
  const loadUserInfo = async (forceRefresh: boolean = false): Promise<boolean> => {
    // 如果不是強制刷新，先嘗試從快取載入
    if (!forceRefresh && loadFromCache()) {
      console.log('User info loaded from cache')
      return true
    }

    // 只有在實際進行 API 調用時才顯示 loading
    loading.value = true
    error.value = ''

    try {
      const result = await getCurrentUser()

      if (result.success && result.data) {
        username.value = result.data.username
        fullName.value = result.data.full_name
        email.value = result.data.email
        isSuperuser.value = result.data.is_superuser || false
        memberLevel.value = result.data.member_level || 0
        createdAt.value = result.data.created_at || null
        lastLoginAt.value = result.data.last_login || null
        initialized.value = true

        // 儲存到快取
        saveToCache(
          result.data.username,
          result.data.full_name,
          result.data.email,
          result.data.is_superuser || false,
          result.data.member_level || 0,
          result.data.created_at || null,
          result.data.last_login || null
        )

        return true
      } else {
        // 載入失敗但不是 401 錯誤（401 已在 getCurrentUser 中處理）
        if (result.error && !result.error.includes('expired')) {
          error.value = result.error
          console.warn('無法載入用戶資訊:', result.error)
        }
        return false
      }
    } catch (err: any) {
      console.error('Failed to load user info:', err)
      error.value = err.message || '載入用戶資訊失敗'
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * 清除用戶資訊和快取
   */
  const clearUserInfo = () => {
    username.value = ''
    fullName.value = ''
    email.value = ''
    isSuperuser.value = false
    memberLevel.value = 0
    createdAt.value = null
    lastLoginAt.value = null
    error.value = ''

    // 清除快取
    if (process.client) {
      localStorage.removeItem(CACHE_KEY)
    }
  }

  return {
    // 狀態
    username,
    fullName,
    email,
    isSuperuser,
    memberLevel,
    createdAt,
    lastLoginAt,
    loading,
    error,
    initialized,

    // 方法
    loadUserInfo,
    clearUserInfo,
  }
}
