/**
 * Nuxt 日誌插件 - 添加時間戳
 *
 * 用途：為 console.log/warn/error 添加 UTC 時間戳
 */
export default defineNuxtPlugin(() => {
  // 只在客戶端運行
  if (process.client) {
    return
  }

  // 格式化時間戳（UTC）
  const getTimestamp = (): string => {
    const now = new Date()
    return now.toISOString().replace('T', ' ').substring(0, 23) // 2025-12-27 13:00:00.123
  }

  // 保存原始方法
  const originalLog = console.log
  const originalWarn = console.warn
  const originalError = console.error

  // 重寫 console.log
  console.log = function (...args: any[]) {
    originalLog(`[${getTimestamp()}]`, ...args)
  }

  // 重寫 console.warn
  console.warn = function (...args: any[]) {
    originalWarn(`[${getTimestamp()}]`, ...args)
  }

  // 重寫 console.error
  console.error = function (...args: any[]) {
    originalError(`[${getTimestamp()}]`, ...args)
  }
})
