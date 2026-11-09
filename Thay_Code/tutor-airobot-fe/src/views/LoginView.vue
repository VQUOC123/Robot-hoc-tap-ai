<script setup lang="ts">
import LoginForm from '@/features/auth/components/LoginForm.vue'
import { Bot } from 'lucide-vue-next'
</script>

<template>
  <div
    class="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12"
  >
    <div class="w-full max-w-sm">
      <!-- Brand -->
      <div class="mb-8 text-center">
        <div
          class="mx-auto mb-4 flex size-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-md"
        >
          <Bot class="size-6" />
        </div>
        <h1 class="text-2xl font-bold tracking-tight">Tutor Admin</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Quản lý hệ thống giám sát học tập AI
        </p>
      </div>

      <!-- Login card -->
      <div class="rounded-xl border bg-card p-6 shadow-sm">
        <div class="mb-6">
          <h2 class="text-lg font-semibold">Đăng nhập</h2>
          <p class="mt-0.5 text-sm text-muted-foreground">
            Nhập thông tin tài khoản để tiếp tục
          </p>
        </div>
        <LoginForm />
      </div>

      <p class="mt-6 text-center text-xs text-muted-foreground">
        Tutor AI Robot © {{ new Date().getFullYear() }}
      </p>
    </div>
  </div>
</template>
