/**
 * 錯誤處理 Composable
 * 統一處理 API 錯誤並顯示詳細錯誤信息
 */

import { ref } from 'vue'

export interface ErrorDetail {
  success: false
  error: {
    type: string
    message: string
    code?: string
    details?: any
    traceback?: string
    cause?: {
      type: string
      message: string
    }
  }
  request?: {
    method: string
    url: string
    client?: string
  }
}

export const useErrorHandler = () => {
  const currentError = ref<ErrorDetail | null>(null)
  const showErrorDialog = ref(false)

  /**
   * 處理 API 錯誤
   */
  const handleError = (error: any, options: {
    showToast?: boolean
    showDialog?: boolean
    customMessage?: string
    context?: string
  } = {}) => {
    const {
      showToast = false,  // Toast 通知預設關閉，使用 ErrorDisplay 組件代替
      showDialog = false,
      customMessage,
      context
    } = options

    // 解析錯誤
    let errorDetail: ErrorDetail | null = null

    if (error.response?.data) {
      // FastAPI 錯誤響應
      errorDetail = error.response.data
    } else if (error.data) {
      // Nuxt useFetch 錯誤
      errorDetail = error.data
    } else if (error.message) {
      // 網絡錯誤或其他 JS 錯誤
      errorDetail = {
        success: false,
        error: {
          type: 'NetworkError',
          message: error.message,
          code: 'NETWORK_ERROR'
        }
      }
    } else {
      // 未知錯誤
      errorDetail = {
        success: false,
        error: {
          type: 'UnknownError',
          message: '發生未知錯誤',
          code: 'UNKNOWN_ERROR'
        }
      }
    }

    // 儲存當前錯誤
    currentError.value = errorDetail

    // 顯示詳細錯誤對話框
    if (showDialog) {
      showErrorDialog.value = true
    }

    // 記錄到控制台（開發環境）
    if (process.env.NODE_ENV === 'development') {
      console.group('🔴 API Error Details')
      console.error('Error Type:', errorDetail.error.type)
      console.error('Error Message:', errorDetail.error.message)
      console.error('Error Code:', errorDetail.error.code)

      if (errorDetail.error.details) {
        console.error('Error Details:', errorDetail.error.details)
      }

      if (errorDetail.error.traceback) {
        console.error('Stack Trace:')
        console.error(errorDetail.error.traceback)
      }

      if (errorDetail.request) {
        console.error('Request:', errorDetail.request)
      }

      console.groupEnd()
    }

    return errorDetail
  }

  /**
   * 清除當前錯誤
   */
  const clearError = () => {
    currentError.value = null
    showErrorDialog.value = false
  }

  /**
   * 包裝 async 函數，自動處理錯誤
   */
  const withErrorHandling = async <T>(
    fn: () => Promise<T>,
    options?: {
      showToast?: boolean
      showDialog?: boolean
      customMessage?: string
      onError?: (error: ErrorDetail) => void
    }
  ): Promise<T | null> => {
    try {
      return await fn()
    } catch (error) {
      const errorDetail = handleError(error, options)

      if (options?.onError) {
        options.onError(errorDetail)
      }

      return null
    }
  }

  /**
   * 檢查錯誤類型
   */
  const isValidationError = (error: ErrorDetail) => {
    return error.error.code === 'VALIDATION_ERROR'
  }

  const isDatabaseError = (error: ErrorDetail) => {
    return error.error.code === 'DATABASE_ERROR'
  }

  const isBacktestError = (error: ErrorDetail) => {
    return error.error.code === 'BACKTEST_ERROR'
  }

  const isNetworkError = (error: ErrorDetail) => {
    return error.error.code === 'NETWORK_ERROR'
  }

  return {
    currentError,
    showErrorDialog,
    handleError,
    clearError,
    withErrorHandling,
    isValidationError,
    isDatabaseError,
    isBacktestError,
    isNetworkError
  }
}
