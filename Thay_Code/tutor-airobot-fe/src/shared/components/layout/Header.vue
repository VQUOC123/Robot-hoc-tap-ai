<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Menu } from 'lucide-vue-next'
import DarkModeToggle from './DarkModeToggle.vue'

defineEmits<{ 'toggle-sidebar': [] }>()

const route = useRoute()
const pageTitle = computed(() => (route.meta.title as string) ?? 'Tutor Admin')
</script>

<template>
  <header class="flex h-14 flex-shrink-0 items-center gap-3 border-b bg-card px-4">
    <!-- Mobile: sidebar toggle -->
    <button
      class="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent md:hidden"
      @click="$emit('toggle-sidebar')"
    >
      <Menu class="size-5" />
    </button>

    <!-- Page title -->
    <h1 class="flex-1 text-sm font-semibold">{{ pageTitle }}</h1>

    <!-- Right actions -->
    <DarkModeToggle />
  </header>
</template>
