// Fix for Vue Router devtools hydration error
// This plugin runs on client-side only to patch the devtools hook
// MUST run before Vue Router initializes

// Inject the fix immediately when this module loads
if (process.client && typeof window !== 'undefined') {
  if (!window.__VUE_DEVTOOLS_GLOBAL_HOOK__) {
    (window as any).__VUE_DEVTOOLS_GLOBAL_HOOK__ = {
      enabled: false,
      emit: () => {},
      on: () => {},
      once: () => {},
      off: () => {},
      apps: []
    }
  }
}

export default defineNuxtPlugin({
  name: 'devtools-fix',
  enforce: 'pre', // Run before other plugins
})
