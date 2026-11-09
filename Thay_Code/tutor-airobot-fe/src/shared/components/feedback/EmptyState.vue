<script setup lang="ts">
import { FolderOpen } from 'lucide-vue-next'

interface Props {
  title?: string
  description?: string
  icon?: object
}

withDefaults(defineProps<Props>(), {
  title: 'Chưa có dữ liệu',
  description: 'Dữ liệu sẽ xuất hiện ở đây khi có.',
})
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2 py-8 text-center text-muted-foreground">
    <component :is="icon ?? FolderOpen" class="size-10 opacity-40" />
    <div>
      <p class="text-sm font-medium">{{ title }}</p>
      <p class="mt-0.5 text-xs">{{ description }}</p>
    </div>
    <slot />
  </div>
</template>
