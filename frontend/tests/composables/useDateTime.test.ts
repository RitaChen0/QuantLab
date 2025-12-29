import { describe, it, expect } from 'vitest'
import { formatToTaiwanTime, formatRelativeTime } from '@/composables/useDateTime'

describe('useDateTime composable', () => {
  it('should format UTC datetime to Taiwan time', () => {
    const utcTime = '2025-12-22T07:30:00Z' // UTC time
    const result = formatToTaiwanTime(utcTime)

    // Taiwan is UTC+8, so 07:30 UTC = 15:30 Taiwan time
    // Format uses slashes: 2025/12/22
    expect(result).toContain('2025/12/22')
    expect(result).toContain('15:30')
  })

  it('should handle timezone-aware datetime strings', () => {
    const dateTime = '2025-12-22T15:30:00+08:00' // Already Taiwan time
    const result = formatToTaiwanTime(dateTime)

    expect(result).toContain('2025/12/22')
    expect(result).toContain('15:30')
  })

  it('should handle null input', () => {
    const result = formatToTaiwanTime(null)
    expect(result).toBe('-')
  })

  it('should handle undefined input', () => {
    const result = formatToTaiwanTime(undefined)
    expect(result).toBe('-')
  })

  it('should handle invalid date strings', () => {
    const result = formatToTaiwanTime('invalid-date')
    // Invalid dates return '-'
    expect(result).toBe('-')
  })

  it('should format date object correctly', () => {
    const date = new Date('2025-12-22T07:30:00Z')
    const result = formatToTaiwanTime(date.toISOString())

    expect(result).toContain('2025/12/22')
    expect(result).toContain('15:30')
  })

  it('should format with custom options - date only', () => {
    const utcTime = '2025-12-22T07:30:00Z'
    const result = formatToTaiwanTime(utcTime, { showDate: true, showTime: false })

    expect(result).toContain('2025/12/22')
    expect(result).not.toContain('15:30')
  })

  it('should format with custom options - time only', () => {
    const utcTime = '2025-12-22T07:30:00Z'
    const result = formatToTaiwanTime(utcTime, { showDate: false, showTime: true })

    expect(result).not.toContain('2025/12/22')
    expect(result).toContain('15:30')
  })

  it('should format without seconds', () => {
    const utcTime = '2025-12-22T07:30:45Z'
    const result = formatToTaiwanTime(utcTime, { showSeconds: false })

    expect(result).toContain('2025/12/22')
    expect(result).toContain('15:30')
    expect(result).not.toContain(':45')
  })
})

describe('formatRelativeTime', () => {
  it('should format time less than 60 seconds ago', () => {
    const now = new Date()
    const past = new Date(now.getTime() - 30 * 1000) // 30 seconds ago
    const result = formatRelativeTime(past.toISOString())

    expect(result).toContain('秒前')
  })

  it('should handle null input', () => {
    const result = formatRelativeTime(null)
    expect(result).toBe('-')
  })

  it('should handle undefined input', () => {
    const result = formatRelativeTime(undefined)
    expect(result).toBe('-')
  })
})
