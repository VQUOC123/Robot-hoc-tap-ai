<script setup lang="ts">
import { watch } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { Loader2 } from 'lucide-vue-next'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/shared/components/ui/form'
import { useUpdateSettings } from '../composables/useSettings'
import type { SystemSettings } from '../types'

const props = defineProps<{ settings: SystemSettings }>()

const schema = toTypedSchema(
  z.object({
    max_image_size_kb: z.coerce.number().int().min(100).max(10240),
    ai_timeout_sec: z.coerce.number().int().min(5).max(120),
    rate_limit_per_minute: z.coerce.number().int().min(1).max(1000),
    log_retention_days: z.coerce.number().int().min(1).max(365),
    allow_concurrent_requests: z.boolean(),
  }),
)

const { handleSubmit, setValues } = useForm({ validationSchema: schema })
const { mutate: updateSettings, isPending } = useUpdateSettings()

watch(() => props.settings, (s) => setValues(s), { immediate: true })

const onSubmit = handleSubmit((values) => updateSettings(values as SystemSettings))
</script>

<template>
  <form class="max-w-xl space-y-6" @submit="onSubmit">
    <div class="grid gap-5 sm:grid-cols-2">
      <!-- Max image size -->
      <FormField v-slot="{ componentField }" name="max_image_size_kb">
        <FormItem>
          <FormLabel>Kích thước ảnh tối đa (KB)</FormLabel>
          <FormControl>
            <Input type="number" min="100" max="10240" v-bind="componentField" />
          </FormControl>
          <FormDescription>Ảnh lớn hơn sẽ bị từ chối (100–10240 KB)</FormDescription>
          <FormMessage />
        </FormItem>
      </FormField>

      <!-- AI timeout -->
      <FormField v-slot="{ componentField }" name="ai_timeout_sec">
        <FormItem>
          <FormLabel>AI Timeout (giây)</FormLabel>
          <FormControl>
            <Input type="number" min="5" max="120" v-bind="componentField" />
          </FormControl>
          <FormDescription>Timeout mặc định cho AI calls</FormDescription>
          <FormMessage />
        </FormItem>
      </FormField>

      <!-- Rate limit -->
      <FormField v-slot="{ componentField }" name="rate_limit_per_minute">
        <FormItem>
          <FormLabel>Rate Limit (req/phút)</FormLabel>
          <FormControl>
            <Input type="number" min="1" max="1000" v-bind="componentField" />
          </FormControl>
          <FormDescription>Số request tối đa mỗi phút từ một thiết bị</FormDescription>
          <FormMessage />
        </FormItem>
      </FormField>

      <!-- Log retention -->
      <FormField v-slot="{ componentField }" name="log_retention_days">
        <FormItem>
          <FormLabel>Lưu log (ngày)</FormLabel>
          <FormControl>
            <Input type="number" min="1" max="365" v-bind="componentField" />
          </FormControl>
          <FormDescription>Tự động xóa log cũ hơn số ngày này</FormDescription>
          <FormMessage />
        </FormItem>
      </FormField>
    </div>

    <!-- Concurrent requests -->
    <FormField v-slot="{ value, handleChange }" name="allow_concurrent_requests" type="checkbox">
      <FormItem class="flex items-center gap-3">
        <FormControl>
          <input type="checkbox" class="size-4 rounded border-border" :checked="value" @change="handleChange" />
        </FormControl>
        <div>
          <FormLabel class="cursor-pointer">Cho phép xử lý đồng thời</FormLabel>
          <FormDescription>Xử lý nhiều ảnh cùng lúc (tăng tốc nhưng tốn tài nguyên)</FormDescription>
        </div>
      </FormItem>
    </FormField>

    <div class="flex justify-end">
      <Button type="submit" :disabled="isPending">
        <Loader2 v-if="isPending" class="mr-2 size-4 animate-spin" />
        Lưu cài đặt
      </Button>
    </div>
  </form>
</template>
