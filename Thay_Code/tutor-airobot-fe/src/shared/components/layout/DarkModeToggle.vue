<script setup lang="ts">
import { Sun, Moon } from 'lucide-vue-next'
import { useColorMode } from '@vueuse/core'

const mode = useColorMode({
  attribute: 'class',
  modes: { dark: 'dark', light: '' },
  storageKey: 'tutor-admin-color-mode',
})

function toggle() {
  mode.value = mode.value === 'dark' ? 'light' : 'dark'
}
</script>

<template>
  <button
    class="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
    :title="mode === 'dark' ? 'Chế độ sáng' : 'Chế độ tối'"
    @click="toggle"
  >
    <Sun v-if="mode === 'dark'" class="size-4" />
    <Moon v-else class="size-4" />
  </button>
</template>
