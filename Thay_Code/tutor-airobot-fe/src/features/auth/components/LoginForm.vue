<script setup lang="ts">
import { ref } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { Eye, EyeOff, Loader2 } from 'lucide-vue-next'
import { useLogin } from '../composables/useAuth'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/shared/components/ui/form'

const loginSchema = z.object({
  email: z.string().email('Email không hợp lệ'),
  password: z.string().min(6, 'Mật khẩu phải có ít nhất 6 ký tự'),
})

const { handleSubmit } = useForm({
  validationSchema: toTypedSchema(loginSchema),
})

const showPassword = ref(false)
const { mutate: login, isPending, error } = useLogin()

const onSubmit = handleSubmit((values) => {
  login(values)
})
</script>

<template>
  <form class="space-y-5" novalidate @submit="onSubmit">
    <!-- Email -->
    <FormField v-slot="{ componentField }" name="email">
      <FormItem>
        <FormLabel>Email</FormLabel>
        <FormControl>
          <Input
            type="email"
            placeholder="admin@example.com"
            autocomplete="email"
            v-bind="componentField"
          />
        </FormControl>
        <FormMessage />
      </FormItem>
    </FormField>

    <!-- Password -->
    <FormField v-slot="{ componentField }" name="password">
      <FormItem>
        <FormLabel>Mật khẩu</FormLabel>
        <FormControl>
          <div class="relative">
            <Input
              :type="showPassword ? 'text' : 'password'"
              placeholder="••••••••"
              autocomplete="current-password"
              class="pr-10"
              v-bind="componentField"
            />
            <button
              type="button"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
              :title="showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'"
              @click="showPassword = !showPassword"
            >
              <Eye v-if="!showPassword" class="size-4" />
              <EyeOff v-else class="size-4" />
            </button>
          </div>
        </FormControl>
        <FormMessage />
      </FormItem>
    </FormField>

    <!-- API error -->
    <div
      v-if="error"
      class="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      {{ error?.message ?? 'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.' }}
    </div>

    <!-- Submit -->
    <Button type="submit" class="w-full" :disabled="isPending">
      <Loader2 v-if="isPending" class="mr-2 size-4 animate-spin" />
      {{ isPending ? 'Đang đăng nhập...' : 'Đăng nhập' }}
    </Button>
  </form>
</template>
