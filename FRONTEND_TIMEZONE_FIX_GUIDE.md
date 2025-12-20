# 前端時區修復指南

**創建日期**: 2025-12-20  
**適用範圍**: QuantLab 前端 Vue 頁面  
**問題**: 直接使用 `new Date()` 未經時區轉換

---

## 問題概述

前端有 30+ 處直接使用 `new Date()` 的情況，主要問題：

1. **顯示時間未轉換為台灣時區** - 後端返回 UTC 時間，前端應轉為台灣時間顯示
2. **日期選擇器未使用統一工具** - 手動操作日期容易出錯
3. **圖表標籤格式化不一致** - 不同頁面使用不同格式化方法

---

## 可用 Composables

系統已提供兩個完整的 composables：

### 1. useDateTime - 時間顯示轉換

```typescript
// frontend/composables/useDateTime.ts
import { useDateTime } from '@/composables/useDateTime'

const { formatToTaiwanTime, formatRelativeTime } = useDateTime()

// 將 UTC 時間轉為台灣時間顯示
const displayTime = formatToTaiwanTime('2025-12-20T00:18:21+00:00')
// 輸出: "2025/12/20 08:18:21"

// 只顯示日期
const displayDate = formatToTaiwanTime(dateStr, { showTime: false })
// 輸出: "2025/12/20"

// 相對時間
const relativeTime = formatRelativeTime(dateStr)
// 輸出: "3 分鐘前"
```

### 2. useDatePicker - 日期範圍選擇

```typescript
// frontend/composables/useDatePicker.ts
import { useDatePicker } from '@/composables/useDatePicker'

const { startDate, endDate, setDateRange } = useDatePicker(30) // 預設 30 天

// 設定日期範圍
setDateRange(7)   // 近 7 天
setDateRange(30)  // 近 30 天
setDateRange(90)  // 近 3 個月
```

---

## 修復模式

### 模式 1: 顯示後端返回的時間戳

**❌ 修復前**:
```vue
<template>
  <div>{{ new Date(backtest.created_at).toLocaleString() }}</div>
</template>
```

**✅ 修復後**:
```vue
<script setup>
import { useDateTime } from '@/composables/useDateTime'
const { formatToTaiwanTime } = useDateTime()
</script>

<template>
  <div>{{ formatToTaiwanTime(backtest.created_at) }}</div>
</template>
```

---

### 模式 2: 日期範圍選擇器

**❌ 修復前**:
```javascript
const setDateRange = (days: number) => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - days)
  
  endDate.value = end.toISOString().split('T')[0]
  startDate.value = start.toISOString().split('T')[0]
}
```

**✅ 修復後**:
```javascript
import { useDatePicker } from '@/composables/useDatePicker'

const { startDate, endDate, setDateRange } = useDatePicker(30)

// 直接使用 setDateRange(days)，startDate 和 endDate 會自動更新
```

---

### 模式 3: 圖表 X 軸標籤格式化

**❌ 修復前**:
```javascript
xAxis: {
  axisLabel: {
    formatter: (value: string) => {
      const date = new Date(value)
      return `${date.getMonth() + 1}/${date.getDate()}`
    }
  }
}
```

**✅ 修復後**:
```javascript
import { formatToTaiwanTime } from '@/composables/useDateTime'

xAxis: {
  axisLabel: {
    formatter: (value: string) => {
      // 假設 value 是 ISO 日期字串
      return formatToTaiwanTime(value, { 
        showTime: false 
      }).replace(/\//g, '/').substring(5) // "12/20"
    }
  }
}
```

或簡化版（如果只是日期，不涉及時區轉換）:
```javascript
xAxis: {
  axisLabel: {
    formatter: (value: string) => {
      // 如果 value 已經是 "YYYY-MM-DD" 格式
      const [year, month, day] = value.split('-')
      return `${month}/${day}`
    }
  }
}
```

---

### 模式 4: 自定義日期格式化函數

**❌ 修復前**:
```javascript
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}
```

**✅ 修復後**:
```javascript
import { formatToTaiwanTime } from '@/composables/useDateTime'

const formatDate = (dateStr: string) => {
  return formatToTaiwanTime(dateStr, { showTime: false })
}
```

---

## 需要修復的文件清單

根據代碼審查，以下文件需要修復（優先級排序）：

### 高優先級（核心功能頁面）

1. ✅ **data/index.vue** - 7 處
   - 行 424-425: setDateRange 函數
   - 行 551: 圖表 X 軸標籤
   - 行 674: 圖表 X 軸標籤
   - 行 839: formatDate 函數

2. **backtest/index.vue** - 7 處
   - 日期選擇器
   - 時間戳顯示

3. **institutional/index.vue** - 2 處
   - 時間戳顯示

### 中優先級（輔助功能頁面）

4. **backtest/[id].vue** - 3 處
5. **options/index.vue** - 1 處
6. **dashboard/index.vue** - 2 處

### 低優先級（其他頁面）

7-21. 其他 15+ 個頁面

---

## 修復檢查清單

修復每個文件時，請檢查：

- [ ] 是否導入了 `useDateTime` 或 `useDatePicker`
- [ ] 所有 `new Date()` 用於**顯示**的地方都改用 `formatToTaiwanTime()`
- [ ] 日期範圍選擇使用 `useDatePicker()`
- [ ] 圖表標籤格式化一致
- [ ] 測試時間顯示正確（UTC → 台灣時間）

---

## 自動化檢查工具

使用以下命令檢查前端時區問題：

```bash
# 檢查所有使用 new Date() 的地方
bash scripts/check_frontend_timezone.sh

# 輸出格式：
# ❌ frontend/pages/data/index.vue:424: new Date()
# ✅ frontend/pages/account/profile.vue: 使用 formatToTaiwanTime
```

---

## 測試驗證

修復後，請驗證：

1. **視覺驗證**: 打開頁面，檢查時間顯示是否為台灣時間
   - 例如：UTC `2025-12-20T00:18:21+00:00` 應顯示為 `2025/12/20 08:18:21`

2. **邊界測試**: 檢查跨日期邊界的情況
   - UTC 23:59 應顯示為台灣時間次日 07:59

3. **圖表測試**: 檢查圖表 X 軸標籤格式是否一致

---

## 注意事項

### 何時不需要修復？

1. **純計算用途的 Date 對象** - 如果只是用於計算，不用於顯示，則可保留
2. **已經是本地日期的情況** - 例如日期選擇器的值（YYYY-MM-DD）
3. **已使用 timeZone: 'Asia/Taipei' 的情況** - 已正確處理時區

### 常見陷阱

1. **不要**在圖表數據中修改時間戳 - 只在顯示時轉換
2. **不要**修改 API 請求/響應的日期格式 - 保持 ISO 8601 格式
3. **不要**在日期比較中混用 naive 和 timezone-aware 日期

---

## 快速修復示例

### 示例 1: data/index.vue 修復

**位置**: 行 424-425

```diff
<script setup>
+ import { useDatePicker } from '@/composables/useDatePicker'

- const startDate = ref('')
- const endDate = ref('')
+ const { startDate, endDate, setDateRange } = useDatePicker(30)

- // 設定日期範圍
- const setDateRange = (days: number) => {
-   const end = new Date()
-   const start = new Date()
-   start.setDate(start.getDate() - days)
-   
-   endDate.value = end.toISOString().split('T')[0]
-   startDate.value = start.toISOString().split('T')[0]
- }
+ // setDateRange 已由 useDatePicker 提供
</script>
```

### 示例 2: 時間戳顯示修復

```diff
<script setup>
+ import { useDateTime } from '@/composables/useDateTime'
+ const { formatToTaiwanTime } = useDateTime()
</script>

<template>
- <div>{{ new Date(item.created_at).toLocaleString() }}</div>
+ <div>{{ formatToTaiwanTime(item.created_at) }}</div>
</template>
```

---

## 總結

**預估修復時間**: 每個文件 10-15 分鐘  
**總計**: 30+ 文件 × 15 分鐘 ≈ 8-12 小時

建議分批次修復：
1. 第一批：核心頁面（data, backtest, institutional）- 2-3 小時
2. 第二批：輔助頁面 - 3-4 小時
3. 第三批：其他頁面 - 3-5 小時

---

**文檔版本**: 1.0  
**最後更新**: 2025-12-20  
**維護者**: 開發團隊
