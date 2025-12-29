import { beforeEach, afterEach, vi } from 'vitest'

// Mock fetch globally
global.fetch = vi.fn()

// Reset mocks before each test
beforeEach(() => {
  vi.clearAllMocks()
})

// Cleanup after each test
afterEach(() => {
  vi.clearAllTimers()
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

global.localStorage = localStorageMock as any

// Mock window.alert
global.alert = vi.fn()

// Export mocks for use in tests
export { localStorageMock }
