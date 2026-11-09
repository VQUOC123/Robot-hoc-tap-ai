<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

interface Props {
  hasMore: boolean
  isFetchingMore?: boolean
  totalLoaded?: number
}

withDefaults(defineProps<Props>(), { isFetchingMore: false })

defineEmits<{ loadMore: [] }>()
</script>

<template>
  <div class="flex items-center justify-between py-2 text-sm text-muted-foreground">
    <span v-if="totalLoaded !== undefined">Đang hiển thị {{ totalLoaded }} kết quả</span>
    <div v-if="hasMore" class="ml-auto">
      <button
        :disabled="isFetchingMore"
        class="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-accent transition-colors disabled:opacity-50"
        @click="$emit('loadMore')"
      >
        <Loader2 v-if="isFetchingMore" class="size-3.5 animate-spin" />
        Tải thêm
      </button>
    </div>
  </div>
</template>
