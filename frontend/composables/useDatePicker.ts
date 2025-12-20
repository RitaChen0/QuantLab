/**
 * Date Picker Composable
 *
 * Provides timezone-aware date utilities for date picker components.
 *
 * IMPORTANT: Date Picker Timezone Strategy
 * ----------------------------------------
 * 1. Date pickers use local timezone (browser's timezone)
 * 2. For Taiwan users, this is typically Asia/Taipei (UTC+8)
 * 3. Date values are in YYYY-MM-DD format (no timezone info)
 * 4. Backend receives date strings and interprets them as Taiwan dates
 *
 * This approach is correct because:
 * - Dates are calendar dates, not timestamps
 * - Users expect to see and select local dates
 * - Backend handles Taiwan market data based on Taiwan calendar dates
 */

/**
 * Get today's date in YYYY-MM-DD format (local timezone)
 *
 * @returns Date string in YYYY-MM-DD format
 *
 * @example
 * ```ts
 * const today = getTodayDate()
 * console.log(today) // "2025-12-20"
 * ```
 */
export function getTodayDate(): string {
  const now = new Date()
  return formatDateToISO(now)
}

/**
 * Format a Date object to YYYY-MM-DD string
 *
 * @param date - Date object to format
 * @returns Date string in YYYY-MM-DD format
 *
 * @example
 * ```ts
 * const date = new Date(2025, 11, 20) // Note: month is 0-indexed
 * const formatted = formatDateToISO(date)
 * console.log(formatted) // "2025-12-20"
 * ```
 */
export function formatDateToISO(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Get date N days ago in YYYY-MM-DD format
 *
 * @param daysAgo - Number of days to go back
 * @returns Date string in YYYY-MM-DD format
 *
 * @example
 * ```ts
 * // Get date 7 days ago
 * const lastWeek = getDateDaysAgo(7)
 * console.log(lastWeek) // "2025-12-13" (if today is 2025-12-20)
 * ```
 */
export function getDateDaysAgo(daysAgo: number): string {
  const date = new Date()
  date.setDate(date.getDate() - daysAgo)
  return formatDateToISO(date)
}

/**
 * Get date range (start and end dates) for common periods
 *
 * @param days - Number of days to go back from today
 * @returns Object with startDate and endDate in YYYY-MM-DD format
 *
 * @example
 * ```ts
 * // Get last 30 days range
 * const { startDate, endDate } = getDateRange(30)
 * console.log(startDate) // "2025-11-20"
 * console.log(endDate)   // "2025-12-20"
 * ```
 */
export function getDateRange(days: number): { startDate: string; endDate: string } {
  return {
    startDate: getDateDaysAgo(days),
    endDate: getTodayDate()
  }
}

/**
 * Composable for date picker with common date ranges
 *
 * @returns Object with reactive date refs and helper functions
 *
 * @example
 * ```vue
 * <script setup>
 * const { startDate, endDate, setDateRange } = useDatePicker()
 *
 * // Set to last 30 days
 * setDateRange(30)
 * </script>
 *
 * <template>
 *   <input v-model="startDate" type="date">
 *   <input v-model="endDate" type="date">
 *   <button @click="setDateRange(7)">近 7 天</button>
 *   <button @click="setDateRange(30)">近 30 天</button>
 * </template>
 * ```
 */
export function useDatePicker(initialDays: number = 30) {
  const startDate = ref('')
  const endDate = ref('')

  /**
   * Set date range to N days before today
   *
   * @param days - Number of days to go back
   */
  const setDateRange = (days: number) => {
    const range = getDateRange(days)
    startDate.value = range.startDate
    endDate.value = range.endDate
  }

  /**
   * Reset to initial date range
   */
  const resetDateRange = () => {
    setDateRange(initialDays)
  }

  /**
   * Clear date range
   */
  const clearDateRange = () => {
    startDate.value = ''
    endDate.value = ''
  }

  /**
   * Validate date range (start must be before end)
   *
   * @returns true if valid, false otherwise
   */
  const isValidDateRange = computed(() => {
    if (!startDate.value || !endDate.value) return false
    return startDate.value <= endDate.value
  })

  // Initialize with default range
  onMounted(() => {
    resetDateRange()
  })

  return {
    startDate,
    endDate,
    setDateRange,
    resetDateRange,
    clearDateRange,
    isValidDateRange
  }
}

/**
 * Common date range presets for Taiwan market
 */
export const DATE_RANGE_PRESETS = [
  { label: '近 7 天', days: 7 },
  { label: '近 30 天', days: 30 },
  { label: '近 3 個月', days: 90 },
  { label: '近 6 個月', days: 180 },
  { label: '近 1 年', days: 365 }
] as const
