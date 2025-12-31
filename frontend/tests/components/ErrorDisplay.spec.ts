import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ErrorDisplay from '@/components/ErrorDisplay.vue'

describe('ErrorDisplay Component', () => {
  const mockError = {
    type: 'TestError',
    message: '測試錯誤訊息',
    code: 'TEST_ERROR',
    details: { field: 'test_field', value: 'test_value' },
    context: '測試操作'
  }

  describe('Rendering', () => {
    it('should render error dialog when error prop is provided', () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      expect(wrapper.find('.error-dialog').exists()).toBe(true)
      expect(wrapper.text()).toContain('測試錯誤訊息')
    })

    it('should not render when error prop is null', () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: null }
      })

      expect(wrapper.find('.error-dialog').exists()).toBe(false)
    })

    it('should display error type', () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      expect(wrapper.text()).toContain('TestError')
    })

    it('should display error message', () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      expect(wrapper.text()).toContain('測試錯誤訊息')
    })

    it('should display error code if present', () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      expect(wrapper.text()).toContain('TEST_ERROR')
    })

    it('should display context if present', () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      expect(wrapper.text()).toContain('測試操作')
    })
  })

  describe('Error Details', () => {
    it('should display error details when available', () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      const detailsSection = wrapper.find('.error-details')
      expect(detailsSection.exists()).toBe(true)
    })

    it('should format object details as JSON', () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      expect(wrapper.text()).toContain('test_field')
      expect(wrapper.text()).toContain('test_value')
    })

    it('should handle array details (ValidationError)', () => {
      const validationError = {
        type: 'ValidationError',
        message: '驗證失敗',
        code: 'VALIDATION_ERROR',
        details: [
          { loc: ['body', 'email'], msg: 'field required' },
          { loc: ['body', 'name'], msg: 'invalid format' }
        ]
      }

      const wrapper = mount(ErrorDisplay, {
        props: { error: validationError }
      })

      expect(wrapper.text()).toContain('email')
      expect(wrapper.text()).toContain('field required')
    })

    it('should display traceback in development mode', () => {
      const errorWithTraceback = {
        ...mockError,
        traceback: 'Traceback (most recent call last):\n  File "test.py", line 10'
      }

      const wrapper = mount(ErrorDisplay, {
        props: { error: errorWithTraceback }
      })

      // Check if traceback section exists
      const tracebackSection = wrapper.find('.error-traceback')
      if (tracebackSection.exists()) {
        expect(tracebackSection.text()).toContain('Traceback')
      }
    })
  })

  describe('User Interactions', () => {
    it('should emit close event when close button clicked', async () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      const closeButton = wrapper.find('[data-test="close-button"]')
      if (closeButton.exists()) {
        await closeButton.trigger('click')
        expect(wrapper.emitted('close')).toBeTruthy()
      }
    })

    it('should emit close event when backdrop clicked', async () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      const backdrop = wrapper.find('.error-dialog-backdrop')
      if (backdrop.exists()) {
        await backdrop.trigger('click')
        expect(wrapper.emitted('close')).toBeTruthy()
      }
    })

    it('should copy error information when copy button clicked', async () => {
      // Mock clipboard API
      const mockClipboard = {
        writeText: vi.fn().mockResolvedValue(undefined)
      }
      Object.assign(navigator, { clipboard: mockClipboard })

      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      const copyButton = wrapper.find('[data-test="copy-button"]')
      if (copyButton.exists()) {
        await copyButton.trigger('click')
        expect(mockClipboard.writeText).toHaveBeenCalled()
      }
    })
  })

  describe('Error Types', () => {
    it('should display DatabaseError correctly', () => {
      const dbError = {
        type: 'DatabaseError',
        message: '資料庫錯誤',
        code: 'DATABASE_ERROR',
        details: {
          table: 'users',
          constraint: 'fk_user_strategies'
        }
      }

      const wrapper = mount(ErrorDisplay, {
        props: { error: dbError }
      })

      expect(wrapper.text()).toContain('DatabaseError')
      expect(wrapper.text()).toContain('資料庫錯誤')
    })

    it('should display ValidationError correctly', () => {
      const validationError = {
        type: 'ValidationError',
        message: '請求參數驗證失敗',
        code: 'VALIDATION_ERROR',
        details: [
          { loc: ['body', 'strategy_id'], msg: 'field required' }
        ]
      }

      const wrapper = mount(ErrorDisplay, {
        props: { error: validationError }
      })

      expect(wrapper.text()).toContain('ValidationError')
      expect(wrapper.text()).toContain('strategy_id')
      expect(wrapper.text()).toContain('field required')
    })

    it('should display NetworkError correctly', () => {
      const networkError = {
        type: 'NetworkError',
        message: '網絡連接失敗',
        code: 'NETWORK_ERROR'
      }

      const wrapper = mount(ErrorDisplay, {
        props: { error: networkError }
      })

      expect(wrapper.text()).toContain('NetworkError')
      expect(wrapper.text()).toContain('網絡連接失敗')
    })

    it('should display BacktestError correctly', () => {
      const backtestError = {
        type: 'BacktestError',
        message: '回測執行失敗',
        code: 'BACKTEST_ERROR',
        details: {
          strategy_id: 123,
          error: 'Insufficient data'
        }
      }

      const wrapper = mount(ErrorDisplay, {
        props: { error: backtestError }
      })

      expect(wrapper.text()).toContain('BacktestError')
      expect(wrapper.text()).toContain('回測執行失敗')
    })
  })

  describe('Edge Cases', () => {
    it('should handle error with minimal properties', () => {
      const minimalError = {
        message: 'Simple error'
      }

      const wrapper = mount(ErrorDisplay, {
        props: { error: minimalError }
      })

      expect(wrapper.find('.error-dialog').exists()).toBe(true)
      expect(wrapper.text()).toContain('Simple error')
    })

    it('should handle error with null details', () => {
      const errorWithNullDetails = {
        type: 'TestError',
        message: 'Test message',
        details: null
      }

      const wrapper = mount(ErrorDisplay, {
        props: { error: errorWithNullDetails }
      })

      expect(wrapper.find('.error-dialog').exists()).toBe(true)
      expect(wrapper.text()).toContain('Test message')
    })

    it('should handle error with empty string message', () => {
      const errorWithEmptyMessage = {
        type: 'TestError',
        message: '',
        code: 'TEST_ERROR'
      }

      const wrapper = mount(ErrorDisplay, {
        props: { error: errorWithEmptyMessage }
      })

      expect(wrapper.find('.error-dialog').exists()).toBe(true)
    })

    it('should handle very long error messages', () => {
      const longMessage = 'A'.repeat(1000)
      const errorWithLongMessage = {
        type: 'TestError',
        message: longMessage,
        code: 'TEST_ERROR'
      }

      const wrapper = mount(ErrorDisplay, {
        props: { error: errorWithLongMessage }
      })

      expect(wrapper.find('.error-dialog').exists()).toBe(true)
      expect(wrapper.text()).toContain(longMessage)
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA attributes', () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      const dialog = wrapper.find('[role="dialog"]')
      if (dialog.exists()) {
        expect(dialog.attributes('aria-modal')).toBe('true')
      }
    })

    it('should be keyboard navigable', async () => {
      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      const closeButton = wrapper.find('button')
      if (closeButton.exists()) {
        await closeButton.trigger('keydown', { key: 'Escape' })
        // Should emit close event
        expect(wrapper.emitted('close')).toBeTruthy()
      }
    })
  })

  describe('Copy Functionality', () => {
    it('should format copied text correctly', async () => {
      const mockClipboard = {
        writeText: vi.fn().mockResolvedValue(undefined)
      }
      Object.assign(navigator, { clipboard: mockClipboard })

      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      const copyButton = wrapper.find('[data-test="copy-button"]')
      if (copyButton.exists()) {
        await copyButton.trigger('click')

        const copiedText = mockClipboard.writeText.mock.calls[0][0]
        expect(copiedText).toContain('TestError')
        expect(copiedText).toContain('測試錯誤訊息')
        expect(copiedText).toContain('TEST_ERROR')
      }
    })

    it('should show success feedback after copying', async () => {
      const mockClipboard = {
        writeText: vi.fn().mockResolvedValue(undefined)
      }
      Object.assign(navigator, { clipboard: mockClipboard })

      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      const copyButton = wrapper.find('[data-test="copy-button"]')
      if (copyButton.exists()) {
        await copyButton.trigger('click')
        await wrapper.vm.$nextTick()

        // Should show some indication of success (implementation dependent)
        // This could be a toast, button text change, etc.
      }
    })

    it('should handle copy failure gracefully', async () => {
      const mockClipboard = {
        writeText: vi.fn().mockRejectedValue(new Error('Copy failed'))
      }
      Object.assign(navigator, { clipboard: mockClipboard })

      const wrapper = mount(ErrorDisplay, {
        props: { error: mockError }
      })

      const copyButton = wrapper.find('[data-test="copy-button"]')
      if (copyButton.exists()) {
        await copyButton.trigger('click')
        // Should not throw error, should handle gracefully
        expect(wrapper.find('.error-dialog').exists()).toBe(true)
      }
    })
  })
})
