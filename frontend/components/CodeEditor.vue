<template>
  <div class="code-editor-wrapper">
    <div ref="editorContainer" class="code-editor-container"></div>
    <div v-if="loading" class="editor-loading">
      <div class="spinner"></div>
      <p>載入編輯器中...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type * as Monaco from 'monaco-editor'

// 動態導入 Monaco Editor（僅在客戶端）
let monaco: typeof Monaco | null = null

// Props
interface Props {
  modelValue: string
  language?: string
  theme?: string
  height?: string
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  language: 'python',
  theme: 'vs-dark',
  height: '500px',
  readonly: false
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'change': [value: string]
}>()

// Refs
const editorContainer = ref<HTMLDivElement | null>(null)
const loading = ref(true)
let editor: Monaco.editor.IStandaloneCodeEditor | null = null
let validationTimeout: NodeJS.Timeout | null = null

// API 配置
const config = useRuntimeConfig()
const apiBase = config.public.apiBase

// 語法驗證函數
const validateCode = async (code: string) => {
  if (!editor || !monaco) return

  try {
    // 獲取認證 token
    const token = localStorage.getItem('token')
    if (!token) return

    // 調用後端驗證 API
    const response = await fetch(`${apiBase}/api/v1/strategies/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ code })
    })

    const result = await response.json()

    // 獲取當前模型
    const model = editor.getModel()
    if (!model) return

    // 清除舊的錯誤標記
    monaco.editor.setModelMarkers(model, 'python-validator', [])

    // 如果驗證失敗，添加錯誤標記
    if (!result.valid && result.errors) {
      const markers: Monaco.editor.IMarkerData[] = result.errors.map((error: any) => ({
        severity: monaco.MarkerSeverity.Error,
        startLineNumber: error.line || 1,
        startColumn: error.column || 1,
        endLineNumber: error.line || 1,
        endColumn: error.column ? error.column + 10 : 100,
        message: error.message || '語法錯誤'
      }))

      monaco.editor.setModelMarkers(model, 'python-validator', markers)
    }
  } catch (error) {
    console.error('Code validation failed:', error)
  }
}

// 初始化編輯器
const initEditor = async () => {
  if (!process.client || !editorContainer.value) return

  try {
    loading.value = true

    // 動態導入 Monaco Editor（僅在客戶端執行）
    if (!monaco) {
      monaco = await import('monaco-editor')
    }

    // 配置 Monaco Editor
    monaco.languages.register({ id: 'python' })

    // Python 語法提示
    monaco.languages.registerCompletionItemProvider('python', {
      provideCompletionItems: (model, position) => {
        const suggestions: monaco.languages.CompletionItem[] = [
          // Backtrader 核心類別
          {
            label: 'bt.Strategy',
            kind: monaco.languages.CompletionItemKind.Class,
            documentation: 'Backtrader 策略基類',
            insertText: 'bt.Strategy',
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'bt.indicators',
            kind: monaco.languages.CompletionItemKind.Module,
            documentation: 'Backtrader 技術指標模組',
            insertText: 'bt.indicators.',
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'SimpleMovingAverage',
            kind: monaco.languages.CompletionItemKind.Function,
            documentation: '簡單移動平均線 (SMA)',
            insertText: 'SimpleMovingAverage(self.data.close, period=${1:20})',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'RSI',
            kind: monaco.languages.CompletionItemKind.Function,
            documentation: '相對強弱指標 (RSI)',
            insertText: 'RSI(self.data.close, period=${1:14})',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'MACD',
            kind: monaco.languages.CompletionItemKind.Function,
            documentation: 'MACD 指標',
            insertText: 'MACD(self.data.close, period_me1=${1:12}, period_me2=${2:26}, period_signal=${3:9})',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'BollingerBands',
            kind: monaco.languages.CompletionItemKind.Function,
            documentation: '布林通道',
            insertText: 'BollingerBands(self.data.close, period=${1:20}, devfactor=${2:2})',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          // 策略方法
          {
            label: '__init__',
            kind: monaco.languages.CompletionItemKind.Method,
            documentation: '策略初始化方法',
            insertText: 'def __init__(self):\n    ${1:pass}',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'next',
            kind: monaco.languages.CompletionItemKind.Method,
            documentation: '每個 bar 執行的方法',
            insertText: 'def next(self):\n    ${1:pass}',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'notify_order',
            kind: monaco.languages.CompletionItemKind.Method,
            documentation: '訂單狀態通知方法',
            insertText: 'def notify_order(self, order):\n    if order.status in [order.Completed]:\n        if order.isbuy():\n            ${1:pass}\n        elif order.issell():\n            ${2:pass}',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          // 交易操作
          {
            label: 'self.buy()',
            kind: monaco.languages.CompletionItemKind.Function,
            documentation: '買入',
            insertText: 'self.buy()',
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'self.sell()',
            kind: monaco.languages.CompletionItemKind.Function,
            documentation: '賣出',
            insertText: 'self.sell()',
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'self.close()',
            kind: monaco.languages.CompletionItemKind.Function,
            documentation: '平倉',
            insertText: 'self.close()',
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'self.position',
            kind: monaco.languages.CompletionItemKind.Property,
            documentation: '當前持倉',
            insertText: 'self.position',
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          // 數據訪問
          {
            label: 'self.data.close',
            kind: monaco.languages.CompletionItemKind.Property,
            documentation: '收盤價',
            insertText: 'self.data.close',
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'self.data.open',
            kind: monaco.languages.CompletionItemKind.Property,
            documentation: '開盤價',
            insertText: 'self.data.open',
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'self.data.high',
            kind: monaco.languages.CompletionItemKind.Property,
            documentation: '最高價',
            insertText: 'self.data.high',
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'self.data.low',
            kind: monaco.languages.CompletionItemKind.Property,
            documentation: '最低價',
            insertText: 'self.data.low',
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          },
          {
            label: 'self.data.volume',
            kind: monaco.languages.CompletionItemKind.Property,
            documentation: '成交量',
            insertText: 'self.data.volume',
            range: {
              startLineNumber: position.lineNumber,
              startColumn: position.column,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            }
          }
        ]

        return { suggestions }
      }
    })

    // 創建編輯器實例
    editor = monaco.editor.create(editorContainer.value, {
      value: props.modelValue,
      language: props.language,
      theme: props.theme,
      automaticLayout: true,
      minimap: {
        enabled: true
      },
      fontSize: 14,
      lineNumbers: 'on',
      roundedSelection: false,
      scrollBeyondLastLine: false,
      readOnly: props.readonly,
      tabSize: 4,
      wordWrap: 'on',
      folding: true,
      renderWhitespace: 'selection',
      suggest: {
        showKeywords: true,
        showSnippets: true
      },
      quickSuggestions: {
        other: true,
        comments: false,
        strings: false
      },
      parameterHints: {
        enabled: true
      },
      suggestOnTriggerCharacters: true,
      acceptSuggestionOnEnter: 'on',
      snippetSuggestions: 'top'
    })

    // 監聽內容變化
    editor.onDidChangeModelContent(() => {
      if (editor) {
        const value = editor.getValue()
        emit('update:modelValue', value)
        emit('change', value)

        // 即時語法檢查（防抖 1.5 秒）
        if (validationTimeout) {
          clearTimeout(validationTimeout)
        }
        validationTimeout = setTimeout(() => {
          validateCode(value)
        }, 1500)
      }
    })

    loading.value = false
  } catch (error) {
    console.error('Failed to initialize Monaco Editor:', error)
    loading.value = false
  }
}

// 更新編輯器內容（當 props 變化時）
watch(() => props.modelValue, (newValue) => {
  if (editor && editor.getValue() !== newValue) {
    editor.setValue(newValue)
  }
})

// 更新主題
watch(() => props.theme, (newTheme) => {
  if (editor) {
    monaco.editor.setTheme(newTheme)
  }
})

// 組件掛載時初始化編輯器
onMounted(() => {
  if (process.client) {
    initEditor()
  }
})

// 組件卸載時清理編輯器
onUnmounted(() => {
  // 清理驗證計時器
  if (validationTimeout) {
    clearTimeout(validationTimeout)
    validationTimeout = null
  }

  // 清理編輯器實例
  if (editor) {
    editor.dispose()
    editor = null
  }
})
</script>

<style scoped lang="scss">
.code-editor-wrapper {
  position: relative;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  overflow: hidden;
}

.code-editor-container {
  width: 100%;
  height: v-bind(height);
}

.editor-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.95);
  z-index: 10;

  .spinner {
    width: 2rem;
    height: 2rem;
    border: 3px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  p {
    color: #6b7280;
    font-size: 0.875rem;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
