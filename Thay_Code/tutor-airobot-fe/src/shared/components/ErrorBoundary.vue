<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { AlertCircle, RefreshCw } from 'lucide-vue-next'

const error = ref<Error | null>(null)

onErrorCaptured((err) => {
  error.value = err instanceof Error ? err : new Error(String(err))
  return false // stop propagation
})

function reset() {
  error.value = null
}
</script>

<template>
  <template v-if="error">
    <div class="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
      <AlertCircle class="size-12 text-destructive opacity-70" />
      <div>
        <p class="text-base font-semibold">Đã xảy ra lỗi không mong muốn</p>
        <p class="mt-1 max-w-sm text-sm text-muted-foreground">{{ error.message }}</p>
      </div>
      <button
        class="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm hover:bg-accent transition-colors"
        @click="reset"
      >
        <RefreshCw class="size-4" />
        Thử lại
      </button>
    </div>
  </template>
  <slot v-else />
</template>
