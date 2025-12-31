import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useErrorHandler } from '@/composables/useErrorHandler'

describe('useErrorHandler composable', () => {
  beforeEach(() => {
    // Clear any previous errors
    const { clearError } = useErrorHandler()
    clearError()
  })

  describe('handleError', () => {
    it('should handle basic error object', () => {
      const { currentError, handleError } = useErrorHandler()

      const error = new Error('Test error message')
      handleError(error, { showDialog: true })

      expect(currentError.value).not.toBeNull()
      expect(currentError.value?.type).toBe('Error')
      expect(currentError.value?.message).toBe('Test error message')
    })

    it('should handle API error with data property', () => {
      const { currentError, handleError } = useErrorHandler()

      const apiError = {
        status: 400,
        data: {
          error: {
            type: 'ValidationError',
            message: '請求參數驗證失敗',
            code: 'VALIDATION_ERROR',
            details: [
              { loc: ['body', 'email'], msg: 'field required' }
            ]
          }
        }
      }

      handleError(apiError, { showDialog: true })

      expect(currentError.value).not.toBeNull()
      expect(currentError.value?.type).toBe('ValidationError')
      expect(currentError.value?.message).toBe('請求參數驗證失敗')
      expect(currentError.value?.code).toBe('VALIDATION_ERROR')
      expect(currentError.value?.details).toBeDefined()
    })

    it('should handle network error', () => {
      const { currentError, handleError } = useErrorHandler()

      const networkError = {
        name: 'FetchError',
        message: 'Network request failed'
      }

      handleError(networkError, { showDialog: true })

      expect(currentError.value).not.toBeNull()
      expect(currentError.value?.type).toBe('NetworkError')
      expect(currentError.value?.message).toContain('網絡連接失敗')
    })

    it('should handle error with context', () => {
      const { currentError, handleError } = useErrorHandler()

      const error = new Error('Delete failed')
      handleError(error, {
        showDialog: true,
        context: '刪除用戶'
      })

      expect(currentError.value).not.toBeNull()
      expect(currentError.value?.context).toBe('刪除用戶')
    })

    it('should not set currentError when showDialog is false', () => {
      const { currentError, handleError } = useErrorHandler()

      const error = new Error('Test error')
      handleError(error, { showDialog: false })

      expect(currentError.value).toBeNull()
    })

    it('should handle string error', () => {
      const { currentError, handleError } = useErrorHandler()

      handleError('Simple error string', { showDialog: true })

      expect(currentError.value).not.toBeNull()
      expect(currentError.value?.message).toBe('Simple error string')
    })

    it('should handle DatabaseError from backend', () => {
      const { currentError, handleError } = useErrorHandler()

      const dbError = {
        status: 500,
        data: {
          success: false,
          error: {
            type: 'DatabaseError',
            message: '資料庫操作失敗',
            code: 'DATABASE_ERROR',
            details: {
              table: 'users',
              constraint: 'fk_user_strategies'
            }
          }
        }
      }

      handleError(dbError, { showDialog: true })

      expect(currentError.value).not.toBeNull()
      expect(currentError.value?.type).toBe('DatabaseError')
      expect(currentError.value?.code).toBe('DATABASE_ERROR')
      expect(currentError.value?.details).toEqual({
        table: 'users',
        constraint: 'fk_user_strategies'
      })
    })

    it('should handle 401 unauthorized error', () => {
      const { currentError, handleError } = useErrorHandler()

      const unauthorizedError = {
        status: 401,
        statusText: 'Unauthorized',
        data: { detail: 'Not authenticated' }
      }

      handleError(unauthorizedError, { showDialog: true })

      expect(currentError.value).not.toBeNull()
      expect(currentError.value?.type).toContain('401')
    })

    it('should preserve traceback if present', () => {
      const { currentError, handleError } = useErrorHandler()

      const errorWithTraceback = {
        status: 500,
        data: {
          error: {
            type: 'BacktestError',
            message: '回測執行失敗',
            code: 'BACKTEST_ERROR',
            traceback: 'Traceback (most recent call last):\n  File "test.py", line 10'
          }
        }
      }

      handleError(errorWithTraceback, { showDialog: true })

      expect(currentError.value).not.toBeNull()
      expect(currentError.value?.traceback).toContain('Traceback')
    })
  })

  describe('clearError', () => {
    it('should clear current error', () => {
      const { currentError, handleError, clearError } = useErrorHandler()

      handleError(new Error('Test'), { showDialog: true })
      expect(currentError.value).not.toBeNull()

      clearError()
      expect(currentError.value).toBeNull()
    })

    it('should handle clearing when no error exists', () => {
      const { currentError, clearError } = useErrorHandler()

      expect(currentError.value).toBeNull()
      clearError()
      expect(currentError.value).toBeNull()
    })
  })

  describe('ValidationError formatting', () => {
    it('should format Pydantic validation errors', () => {
      const { currentError, handleError } = useErrorHandler()

      const validationError = {
        status: 422,
        data: {
          error: {
            type: 'ValidationError',
            message: '請求參數驗證失敗',
            code: 'VALIDATION_ERROR',
            details: [
              { loc: ['body', 'name'], msg: 'field required', type: 'value_error.missing' },
              { loc: ['body', 'email'], msg: 'invalid email format', type: 'value_error.email' }
            ]
          }
        }
      }

      handleError(validationError, { showDialog: true })

      expect(currentError.value).not.toBeNull()
      expect(currentError.value?.type).toBe('ValidationError')
      expect(currentError.value?.details).toBeDefined()
      expect(Array.isArray(currentError.value?.details)).toBe(true)
    })
  })

  describe('Error type detection', () => {
    it('should detect network timeout', () => {
      const { currentError, handleError } = useErrorHandler()

      const timeoutError = {
        name: 'AbortError',
        message: 'The operation was aborted'
      }

      handleError(timeoutError, { showDialog: true })

      expect(currentError.value).not.toBeNull()
      expect(currentError.value?.type).toContain('Error')
    })

    it('should handle error without status code', () => {
      const { currentError, handleError } = useErrorHandler()

      const genericError = {
        message: 'Something went wrong'
      }

      handleError(genericError, { showDialog: true })

      expect(currentError.value).not.toBeNull()
      expect(currentError.value?.message).toBe('Something went wrong')
    })
  })

  describe('Multiple errors', () => {
    it('should replace previous error with new one', () => {
      const { currentError, handleError } = useErrorHandler()

      handleError(new Error('First error'), { showDialog: true })
      expect(currentError.value?.message).toBe('First error')

      handleError(new Error('Second error'), { showDialog: true })
      expect(currentError.value?.message).toBe('Second error')
    })
  })
})
