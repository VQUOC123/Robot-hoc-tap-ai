<script setup lang="ts">
import { AlertCircle } from 'lucide-vue-next'

interface Props {
  title?: string
  message?: string
  onRetry?: () => void
}

withDefaults(defineProps<Props>(), {
  title: 'Đã xảy ra lỗi',
  message: 'Vui lòng thử lại sau.',
})
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-8 text-center">
    <AlertCircle class="size-10 text-destructive" />
    <div>
      <p class="font-medium">{{ title }}</p>
      <p class="mt-0.5 text-sm text-muted-foreground">{{ message }}</p>
    </div>
    <button
      v-if="onRetry"
      class="rounded-md border px-3 py-1.5 text-sm hover:bg-accent transition-colors"
      @click="onRetry()"
    >
      Thử lại
    </button>
  </div>
</template>
