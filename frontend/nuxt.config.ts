// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: false },

  modules: [
    '@pinia/nuxt'
  ],

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
      wsBase: process.env.NUXT_PUBLIC_WS_BASE || 'ws://localhost:8000'
    }
  },

  app: {
    head: {
      title: 'QuantLab - 量化交易實驗室',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: '開源的台股量化交易平台' }
      ]
    }
  },

  typescript: {
    strict: false,
    typeCheck: false
  },

  vite: {
    optimizeDeps: {
      include: ['monaco-editor']
    },
    ssr: {
      noExternal: []
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: (id) => {
            // Monaco Editor 單獨分塊（最大的依賴）
            if (id.includes('monaco-editor')) {
              return 'monaco-editor'
            }
            // Node modules 分塊
            if (id.includes('node_modules')) {
              // Vue 相關
              if (id.includes('vue') || id.includes('@vue')) {
                return 'vue-vendor'
              }
              // Pinia 狀態管理
              if (id.includes('pinia')) {
                return 'pinia-vendor'
              }
              // 其他第三方庫
              return 'vendor'
            }
          },
          // 設定 chunk 大小限制警告為 1000 KB
          chunkFileNames: (chunkInfo) => {
            const facadeModuleId = chunkInfo.facadeModuleId ? chunkInfo.facadeModuleId.split('/').pop() : 'chunk'
            return `_nuxt/[name]-[hash].js`
          }
        }
      },
      chunkSizeWarningLimit: 1000
    }
  },

  // 路由懶加載配置
  router: {
    options: {
      strict: false
    }
  },

  compatibilityDate: '2024-01-01'
})
