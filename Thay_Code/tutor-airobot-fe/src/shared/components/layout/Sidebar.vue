<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import {
  LayoutDashboard,
  Cpu,
  MessageSquare,
  BarChart3,
  Monitor,
  Settings,
  LogOut,
  Bot,
} from 'lucide-vue-next'
import { useLogout } from '@/features/auth/composables/useAuth'
import { useAuthStore } from '@/features/auth/store/auth.store'
import { cn } from '@/shared/utils'

defineEmits<{ navigate: [] }>()

const route = useRoute()
const auth = useAuthStore()
const { mutate: logout, isPending: isLoggingOut } = useLogout()

const navItems = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'AI Providers', to: '/providers', icon: Cpu },
  { label: 'Prompts', to: '/prompts', icon: MessageSquare },
  { label: 'Phân tích', to: '/analyses', icon: BarChart3 },
  { label: 'Thiết bị', to: '/devices', icon: Monitor },
  { label: 'Cài đặt', to: '/settings', icon: Settings },
] as const

function isActive(to: string): boolean {
  return route.path === to || route.path.startsWith(to + '/')
}

const userInitial = computed(
  () =>
    auth.user?.name?.charAt(0).toUpperCase() ??
    auth.user?.email?.charAt(0).toUpperCase() ??
    'A',
)
</script>

<template>
  <div class="flex h-full flex-col">
    <!-- Brand -->
    <div class="flex h-14 items-center gap-2.5 border-b px-4">
      <div
        class="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground"
      >
        <Bot class="size-4" />
      </div>
      <span class="text-sm font-semibold">Tutor Admin</span>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 space-y-0.5 overflow-y-auto p-3">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        :class="
          cn(
            'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
            isActive(item.to)
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
          )
        "
        @click="$emit('navigate')"
      >
        <component :is="item.icon" class="size-4 flex-shrink-0" />
        {{ item.label }}
      </RouterLink>
    </nav>

    <!-- User section -->
    <div class="border-t p-3">
      <!-- User info -->
      <div class="mb-1 flex items-center gap-2.5 rounded-md px-3 py-2">
        <div
          class="flex size-7 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary"
        >
          {{ userInitial }}
        </div>
        <div class="min-w-0 flex-1">
          <p class="truncate text-xs font-medium">
            {{ auth.user?.name ?? auth.user?.email }}
          </p>
          <p class="truncate text-xs capitalize text-muted-foreground">
            {{ auth.user?.role }}
          </p>
        </div>
      </div>
      <!-- Logout -->
      <button
        :disabled="isLoggingOut"
        class="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
        @click="logout()"
      >
        <LogOut class="size-4" />
        {{ isLoggingOut ? 'Đang đăng xuất...' : 'Đăng xuất' }}
      </button>
    </div>
  </div>
</template>
