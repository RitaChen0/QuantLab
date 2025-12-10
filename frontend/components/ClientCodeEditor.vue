<template>
  <ClientOnly>
    <CodeEditor
      v-bind="$attrs"
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      @change="$emit('change', $event)"
    />
    <template #fallback>
      <div class="editor-loading">
        <div class="spinner"></div>
        <p>載入編輯器中...</p>
      </div>
    </template>
  </ClientOnly>
</template>

<script setup lang="ts">
// Props
interface Props {
  modelValue: string
}

defineProps<Props>()

// Emits
defineEmits<{
  'update:modelValue': [value: string]
  'change': [value: string]
}>()
</script>

<style scoped lang="scss">
.editor-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  background: #1e1e1e;
  border-radius: 0.5rem;
  min-height: 500px;

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
    color: #9ca3af;
    font-size: 0.875rem;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
