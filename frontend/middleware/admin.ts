/**
 * Admin 權限中間件
 * 只允許 superuser 訪問後台管理頁面
 */
export default defineNuxtRouteMiddleware(async (to, from) => {
  // 只在客戶端執行
  if (!process.client) {
    return
  }

  const { getCurrentUser } = useAuth()
  const router = useRouter()

  // 1. 檢查是否有 token
  const token = localStorage.getItem('access_token')
  if (!token) {
    console.log('[Admin Middleware] No token, redirecting to login')
    return navigateTo('/login')
  }

  try {
    // 2. 獲取用戶資訊
    const result = await getCurrentUser()

    if (!result.success || !result.data) {
      console.error('[Admin Middleware] Failed to get user info:', result.error)
      return navigateTo('/login')
    }

    // 3. 檢查是否為管理員
    if (!result.data.is_superuser) {
      console.warn('[Admin Middleware] User is not superuser, access denied')

      // 使用 alert 提示（簡單直接）
      alert('權限不足：您沒有訪問後台管理的權限')

      // 重定向到儀表板
      return navigateTo('/dashboard')
    }

    // 4. 通過驗證，允許訪問
    console.log('[Admin Middleware] Superuser verified, access granted')
  } catch (error) {
    console.error('[Admin Middleware] Error:', error)
    return navigateTo('/login')
  }
})
