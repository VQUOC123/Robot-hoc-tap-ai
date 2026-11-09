<script setup lang="ts">
import { watch } from 'vue'
import { useForm } from 'vee-validate'
import { Loader2 } from 'lucide-vue-next'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Textarea } from '@/shared/components/ui/textarea'
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/shared/components/ui/form'
import { promptVeeSchema, type PromptFormValues } from '../schemas/prompt.schema'
import type { Prompt } from '../types'

interface Props {
  prompt?: Prompt
  isSubmitting: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{ submit: [values: PromptFormValues]; cancel: [] }>()

const { handleSubmit, setValues } = useForm<PromptFormValues>({
  validationSchema: promptVeeSchema,
  initialValues: { name: '', description: '', content: '', is_default: false },
})

watch(
  () => props.prompt,
  (p) => {
    if (!p) return
    setValues({ name: p.name, description: p.description ?? '', content: p.content, is_default: p.is_default })
  },
  { immediate: true },
)

const onSubmit = handleSubmit((values) => emit('submit', values))

// JSON schema preview
const EXPECTED_OUTPUT = `{
  "doing_hw": true,
  "subject": "math",
  "grade": "10",
  "hw_type": "exercises",
  "progress": 60,
  "correct": true,
  "help": "Bài 3 sai công thức",
  "confidence": 0.85
}`
</script>

<template>
  <form class="space-y-5" @submit="onSubmit">
    <!-- Name -->
    <FormField v-slot="{ componentField }" name="name">
      <FormItem>
        <FormLabel>Tên Prompt *</FormLabel>
        <FormControl>
          <Input placeholder="Phân tích bài tập toán" v-bind="componentField" />
        </FormControl>
        <FormMessage />
      </FormItem>
    </FormField>

    <!-- Description -->
    <FormField v-slot="{ componentField }" name="description">
      <FormItem>
        <FormLabel>Mô tả</FormLabel>
        <FormControl>
          <Input placeholder="Dùng để phân tích ảnh học sinh làm bài tập..." v-bind="componentField" />
        </FormControl>
        <FormMessage />
      </FormItem>
    </FormField>

    <!-- Content -->
    <FormField v-slot="{ componentField }" name="content">
      <FormItem>
        <FormLabel>Nội dung Prompt *</FormLabel>
        <FormControl>
          <Textarea
            placeholder="Analyze the image and return JSON..."
            class="min-h-48 font-mono text-sm"
            v-bind="componentField"
          />
        </FormControl>
        <FormDescription>Prompt gửi đến AI. Output phải là JSON theo schema bên phải.</FormDescription>
        <FormMessage />
      </FormItem>
    </FormField>

    <!-- Expected output preview -->
    <div class="rounded-lg border bg-muted/40 p-3">
      <p class="mb-2 text-xs font-semibold text-muted-foreground">Expected JSON Output Schema</p>
      <pre class="text-xs leading-relaxed overflow-auto">{{ EXPECTED_OUTPUT }}</pre>
    </div>

    <!-- Is Default -->
    <FormField v-slot="{ value, handleChange }" name="is_default" type="checkbox">
      <FormItem class="flex items-center gap-3">
        <FormControl>
          <input type="checkbox" class="size-4 rounded border-border" :checked="value" @change="handleChange" />
        </FormControl>
        <FormLabel class="cursor-pointer">Đặt làm prompt mặc định</FormLabel>
      </FormItem>
    </FormField>

    <!-- Actions -->
    <div class="flex justify-end gap-3 pt-2">
      <Button type="button" variant="outline" @click="$emit('cancel')">Hủy</Button>
      <Button type="submit" :disabled="isSubmitting">
        <Loader2 v-if="isSubmitting" class="mr-2 size-4 animate-spin" />
        {{ prompt ? 'Cập nhật' : 'Tạo mới' }}
      </Button>
    </div>
  </form>
</template>
