<script setup lang="ts">
import { ref } from 'vue'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { Copy, Loader2, CheckCircle } from 'lucide-vue-next'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/shared/components/ui/form'
import { useCopyToClipboard } from '@/shared/composables/useCopyToClipboard'
import { useCreateDevice } from '../composables/useDevices'
import type { CreateDeviceResult } from '../types'

const model = defineModel<boolean>('open', { default: false })

const schema = toTypedSchema(z.object({
  name: z.string().min(1, 'Tên không được trống').max(100),
}))

const { handleSubmit, resetForm } = useForm({ validationSchema: schema })
const { mutateAsync: createDevice, isPending } = useCreateDevice()
const { copy } = useCopyToClipboard()

const createdResult = ref<CreateDeviceResult | null>(null)

const onSubmit = handleSubmit(async (values) => {
  const result = await createDevice(values)
  createdResult.value = result
})

function handleClose() {
  model.value = false
  createdResult.value = null
  resetForm()
}
</script>

<template>
  <Dialog :open="model" @update:open="handleClose">
    <DialogContent class="max-w-md">
      <!-- Step 1: Form -->
      <template v-if="!createdResult">
        <DialogHeader>
          <DialogTitle>Thêm thiết bị mới</DialogTitle>
          <DialogDescription>
            Tạo token xác thực cho Raspberry Pi camera kết nối vào hệ thống.
          </DialogDescription>
        </DialogHeader>

        <form class="space-y-4" @submit="onSubmit">
          <FormField v-slot="{ componentField }" name="name">
            <FormItem>
              <FormLabel>Tên thiết bị *</FormLabel>
              <FormControl>
                <Input placeholder="RPi Camera - Phòng học A101" v-bind="componentField" />
              </FormControl>
              <FormMessage />
            </FormItem>
          </FormField>

          <DialogFooter>
            <Button type="button" variant="outline" @click="handleClose">Hủy</Button>
            <Button type="submit" :disabled="isPending">
              <Loader2 v-if="isPending" class="mr-2 size-4 animate-spin" />
              Tạo thiết bị
            </Button>
          </DialogFooter>
        </form>
      </template>

      <!-- Step 2: Show raw token (one time only) -->
      <template v-else>
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2">
            <CheckCircle class="size-5 text-green-500" />
            Thiết bị đã được tạo
          </DialogTitle>
          <DialogDescription>
            Sao chép token bên dưới và cấu hình vào thiết bị Raspberry Pi.
            <strong class="text-destructive">Token chỉ hiển thị một lần duy nhất!</strong>
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-3">
          <div>
            <p class="mb-1 text-sm font-medium">Tên thiết bị</p>
            <p class="text-sm text-muted-foreground">{{ createdResult.name }}</p>
          </div>
          <div>
            <p class="mb-1 text-sm font-medium">Token xác thực</p>
            <div class="flex items-center gap-2">
              <code class="flex-1 overflow-auto rounded-md border bg-muted px-3 py-2 text-xs break-all">
                {{ createdResult.token }}
              </code>
              <Button
                variant="outline"
                size="icon"
                @click="copy(createdResult!.token, 'Đã sao chép token')"
              >
                <Copy class="size-4" />
              </Button>
            </div>
          </div>
          <p class="text-xs text-muted-foreground">
            Cấu hình vào file .env của Raspberry Pi: <code>DEVICE_TOKEN=&lt;token&gt;</code>
          </p>
        </div>

        <DialogFooter>
          <Button @click="handleClose">Đóng</Button>
        </DialogFooter>
      </template>
    </DialogContent>
  </Dialog>
</template>
