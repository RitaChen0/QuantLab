<template>
  <div class="dashboard-container">
    <!-- 頂部導航欄 -->
    <AppHeader />

    <!-- 主要內容區 -->
    <main class="dashboard-main">
      <div class="page-container">
        <!-- 使用共享的 StrategyEditor 組件 -->
        <StrategyEditor :strategy-id="route.params.id" />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth'
})

const route = useRoute()
const { loadUserInfo } = useUserInfo()

// 載入資料
onMounted(() => {
  loadUserInfo()
})
</script>

<style scoped lang="scss">
.dashboard-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.dashboard-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.page-container {
  width: 100%;
}

// 響應式
@media (max-width: 768px) {
  .dashboard-main {
    padding: 1rem;
  }
}
</style>
