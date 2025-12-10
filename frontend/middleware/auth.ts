export default defineNuxtRouteMiddleware((to, from) => {
  // 只在客戶端執行
  if (process.client) {
    const token = localStorage.getItem('access_token')

    // 如果沒有 token，重定向到登入頁
    if (!token) {
      console.log('No token found, redirecting to login...')
      return navigateTo('/login')
    }

    console.log('Auth middleware: Token found, allowing access')
  }
})
