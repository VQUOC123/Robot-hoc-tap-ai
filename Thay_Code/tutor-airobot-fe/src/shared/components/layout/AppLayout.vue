<script setup lang="ts">
import { ref } from 'vue'
import { RouterView } from 'vue-router'
import { Toaster } from 'vue-sonner'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import ErrorBoundary from '../ErrorBoundary.vue'

// Lazy-import Sheet to avoid circular deps before shadcn is installed
import { Sheet, SheetContent } from '@/shared/components/ui/sheet'

const sidebarOpen = ref(false)
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-background">
    <!-- Desktop sidebar (hidden on mobile) -->
    <aside class="hidden w-64 flex-shrink-0 border-r bg-sidebar md:flex md:flex-col">
      <Sidebar />
    </aside>

    <!-- Mobile sidebar (Sheet slide-over) -->
    <Sheet v-model:open="sidebarOpen">
      <SheetContent side="left" class="w-64 p-0">
        <Sidebar @navigate="sidebarOpen = false" />
      </SheetContent>
    </Sheet>

    <!-- Main content area -->
    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <Header @toggle-sidebar="sidebarOpen = !sidebarOpen" />
      <main class="flex-1 overflow-auto">
        <ErrorBoundary>
          <RouterView />
        </ErrorBoundary>
      </main>
    </div>

    <!-- Global overlays -->
    <ConfirmDialog />
    <Toaster position="top-right" richColors close-button />
  </div>
</template>
