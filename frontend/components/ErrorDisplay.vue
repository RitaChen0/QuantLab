<template>
  <div v-if="error" class="error-display" :class="errorClass">
    <!-- 錯誤標題 -->
    <div class="error-header">
      <div class="error-icon">
        <span v-if="error.error?.code === 'VALIDATION_ERROR'">⚠️</span>
        <span v-else-if="error.error?.code === 'DATABASE_ERROR'">💾</span>
        <span v-else-if="error.error?.code === 'BACKTEST_ERROR'">📊</span>
        <span v-else>❌</span>
      </div>
      <div class="error-title">
        <h3>{{ errorTitle }}</h3>
        <span class="error-code" v-if="error.error?.code">
          {{ error.error.code }}
        </span>
      </div>
      <button @click="collapsed = !collapsed" class="collapse-btn">
        {{ collapsed ? '▼ 展開詳情' : '▲ 收起詳情' }}
      </button>
    </div>

    <!-- 錯誤訊息 -->
    <div class="error-message">
      {{ error.error?.message || '發生未知錯誤' }}
    </div>

    <!-- 詳細信息（可折疊） -->
    <div v-if="!collapsed" class="error-details">
      <!-- 錯誤類型 -->
      <div class="detail-section" v-if="error.error?.type">
        <strong>錯誤類型：</strong>
        <code>{{ error.error.type }}</code>
      </div>

      <!-- 驗證錯誤詳情 -->
      <div class="detail-section" v-if="error.error?.details">
        <strong>詳細信息：</strong>
        <pre class="code-block">{{ JSON.stringify(error.error.details, null, 2) }}</pre>
      </div>

      <!-- 請求信息（開發環境） -->
      <div class="detail-section" v-if="error.request">
        <strong>請求信息：</strong>
        <ul>
          <li><code>{{ error.request.method }}</code> {{ error.request.url }}</li>
          <li v-if="error.request.client">客戶端 IP: {{ error.request.client }}</li>
        </ul>
      </div>

      <!-- 堆棧追蹤（開發環境） -->
      <div class="detail-section" v-if="error.error?.traceback">
        <strong>堆棧追蹤（Stack Trace）：</strong>
        <pre class="traceback">{{ error.error.traceback }}</pre>
        <button @click="copyToClipboard(error.error.traceback)" class="copy-btn">
          📋 複製堆棧追蹤
        </button>
      </div>

      <!-- 根本原因（如果有） -->
      <div class="detail-section" v-if="error.error?.cause">
        <strong>根本原因：</strong>
        <p>{{ error.error.cause.type }}: {{ error.error.cause.message }}</p>
      </div>
    </div>

    <!-- 操作按鈕 -->
    <div class="error-actions">
      <button @click="copyErrorJson" class="action-btn">
        📋 複製完整錯誤
      </button>
      <button @click="reportError" class="action-btn">
        📧 回報問題
      </button>
      <button @click="$emit('close')" class="action-btn close">
        ✕ 關閉
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  error: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close'])

const collapsed = ref(false)

const errorTitle = computed(() => {
  const code = props.error.error?.code
  const titles = {
    'VALIDATION_ERROR': '參數驗證錯誤',
    'DATABASE_ERROR': '資料庫錯誤',
    'BACKTEST_ERROR': '回測執行錯誤',
    'STRATEGY_ERROR': '策略錯誤',
    'HTTP_404': '資源不存在',
    'HTTP_403': '權限不足',
    'HTTP_401': '未授權',
  }
  return titles[code] || '系統錯誤'
})

const errorClass = computed(() => {
  const code = props.error.error?.code
  if (code?.startsWith('HTTP_4')) return 'error-warning'
  if (code === 'VALIDATION_ERROR') return 'error-warning'
  return 'error-critical'
})

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    // 複製成功後可以顯示簡單提示或保持靜默
    console.log('已複製到剪貼簿')
  } catch (err) {
    console.error('複製失敗:', err)
    alert('複製失敗，請手動複製')
  }
}

const copyErrorJson = () => {
  const errorJson = JSON.stringify(props.error, null, 2)
  copyToClipboard(errorJson)
}

const reportError = () => {
  const subject = encodeURIComponent(`QuantLab 錯誤回報: ${props.error.error?.code || 'UNKNOWN'}`)
  const body = encodeURIComponent(`
錯誤類型: ${props.error.error?.type}
錯誤訊息: ${props.error.error?.message}

詳細信息:
${JSON.stringify(props.error, null, 2)}
  `)

  // 可以改為您的問題回報 email 或 GitHub Issues URL
  window.open(`mailto:support@quantlab.tw?subject=${subject}&body=${body}`)
}
</script>

<style scoped>
.error-display {
  border-radius: 8px;
  padding: 20px;
  margin: 16px 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.error-critical {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%);
  border: 2px solid #ff4444;
}

.error-warning {
  background: linear-gradient(135deg, #fffbf0 0%, #fff4e0 100%);
  border: 2px solid #ffa500;
}

.error-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.error-icon {
  font-size: 32px;
}

.error-title {
  flex: 1;
}

.error-title h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}

.error-code {
  display: inline-block;
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  margin-left: 8px;
  color: #555;
}

.collapse-btn {
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.collapse-btn:hover {
  background: rgba(0, 0, 0, 0.1);
}

.error-message {
  background: white;
  padding: 12px;
  border-radius: 6px;
  border-left: 4px solid #ff4444;
  margin-bottom: 16px;
  font-size: 14px;
  line-height: 1.6;
  color: #333;
}

.error-details {
  background: white;
  padding: 16px;
  border-radius: 6px;
  margin-bottom: 16px;
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section strong {
  display: block;
  margin-bottom: 8px;
  color: #2c3e50;
  font-size: 14px;
}

.detail-section code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #e83e8c;
}

.detail-section ul {
  margin: 0;
  padding-left: 20px;
}

.detail-section li {
  margin: 4px 0;
  font-size: 13px;
}

.code-block {
  background: #2d2d2d;
  color: #f8f8f2;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  margin: 0;
}

.traceback {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 11px;
  line-height: 1.4;
  margin: 8px 0;
  max-height: 300px;
  overflow-y: auto;
}

.copy-btn {
  background: #4caf50;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  margin-top: 8px;
  transition: background 0.2s;
}

.copy-btn:hover {
  background: #45a049;
}

.error-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.action-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #0056b3;
  transform: translateY(-1px);
}

.action-btn.close {
  background: #6c757d;
}

.action-btn.close:hover {
  background: #5a6268;
}
</style>
