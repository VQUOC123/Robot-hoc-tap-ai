<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

interface Props {
  size?: 'sm' | 'md' | 'lg'
  text?: string
}

const props = withDefaults(defineProps<Props>(), { size: 'md' })

const sizeClass = { sm: 'size-4', md: 'size-6', lg: 'size-10' }
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2 text-muted-foreground">
    <Loader2 :class="[sizeClass[props.size], 'animate-spin']" />
    <span v-if="text" class="text-sm">{{ text }}</span>
  </div>
</template>
