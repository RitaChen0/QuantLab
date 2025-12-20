/**
 * 時間格式化工具
 *
 * 用途：將後端返回的 UTC 時間轉換為台灣時間顯示
 * 背景：後端統一使用 UTC 儲存，前端顯示時需轉換為台灣時區
 */

/**
 * 格式化日期時間為台灣時區
 * @param dateStr - ISO 8601 格式的日期字串（UTC）
 * @param options - 可選的格式化選項
 * @returns 台灣時區的格式化字串
 *
 * @example
 * formatToTaiwanTime('2025-12-20T00:18:21+00:00')
 * // 輸出: "2025/12/20 08:18:21"
 */
export function formatToTaiwanTime(
  dateStr: string | null | undefined,
  options?: {
    showSeconds?: boolean
    showDate?: boolean
    showTime?: boolean
  }
): string {
  if (!dateStr) return '-'

  const date = new Date(dateStr)

  // 檢查日期是否有效
  if (isNaN(date.getTime())) {
    console.warn('Invalid date:', dateStr)
    return '-'
  }

  const defaultOptions = {
    showSeconds: true,
    showDate: true,
    showTime: true,
    ...options
  }

  // 完整日期時間格式
  if (defaultOptions.showDate && defaultOptions.showTime) {
    return date.toLocaleString('zh-TW', {
      timeZone: 'Asia/Taipei',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: defaultOptions.showSeconds ? '2-digit' : undefined,
      hour12: false
    })
  }

  // 只顯示日期
  if (defaultOptions.showDate && !defaultOptions.showTime) {
    return date.toLocaleDateString('zh-TW', {
      timeZone: 'Asia/Taipei',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  }

  // 只顯示時間
  if (!defaultOptions.showDate && defaultOptions.showTime) {
    return date.toLocaleTimeString('zh-TW', {
      timeZone: 'Asia/Taipei',
      hour: '2-digit',
      minute: '2-digit',
      second: defaultOptions.showSeconds ? '2-digit' : undefined,
      hour12: false
    })
  }

  return '-'
}

/**
 * 格式化為相對時間（例如：3 分鐘前、2 小時前）
 * @param dateStr - ISO 8601 格式的日期字串（UTC）
 * @returns 相對時間字串
 */
export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'

  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  if (diffSec < 60) {
    return `${diffSec} 秒前`
  } else if (diffMin < 60) {
    return `${diffMin} 分鐘前`
  } else if (diffHour < 24) {
    return `${diffHour} 小時前`
  } else if (diffDay < 7) {
    return `${diffDay} 天前`
  } else {
    // 超過 7 天顯示完整日期
    return formatToTaiwanTime(dateStr, { showSeconds: false })
  }
}

/**
 * Composable: 提供時間格式化函數
 */
export function useDateTime() {
  return {
    formatToTaiwanTime,
    formatRelativeTime
  }
}
