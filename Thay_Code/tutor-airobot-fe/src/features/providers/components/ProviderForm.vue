<script setup lang="ts">
import { watch } from 'vue'
import { useForm } from 'vee-validate'
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
import { providerVeeSchema, type ProviderFormValues } from '../schemas/provider.schema'
import type { Provider } from '../types'

interface Props {
  provider?: Provider    // when editing
  isSubmitting: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{ submit: [values: ProviderFormValues]; cancel: [] }>()

const { handleSubmit, setValues } = useForm<ProviderFormValues>({
  validationSchema: providerVeeSchema,
  initialValues: {
    name: '',
    base_url: '',
    api_key: '',
    model: '',
    timeout_sec: 30,
    is_default: false,
  },
})

// Populate form when editing
watch(
  () => props.provider,
  (p) => {
    if (!p) return
    setValues({
      name: p.name,
      base_url: p.base_url,
      api_key: '',         // never pre-fill api_key
      model: p.model,
      timeout_sec: p.timeout_sec,
      is_default: p.is_default,
    })
  },
  { immediate: true },
)

const onSubmit = handleSubmit((values) => emit('submit', values))
</script>

<template>
  <form class="space-y-5" @submit="onSubmit">
    <!-- Name -->
    <FormField v-slot="{ componentField }" name="name">
      <FormItem>
        <FormLabel>Tên Provider *</FormLabel>
        <FormControl>
          <Input placeholder="OpenAI Production" v-bind="componentField" />
        </FormControl>
        <FormMessage />
      </FormItem>
    </FormField>

    <!-- Base URL -->
    <FormField v-slot="{ componentField }" name="base_url">
      <FormItem>
        <FormLabel>Base URL *</FormLabel>
        <FormControl>
          <Input placeholder="https://api.openai.com/v1" v-bind="componentField" />
        </FormControl>
        <FormMessage />
      </FormItem>
    </FormField>

    <!-- API Key -->
    <FormField v-slot="{ componentField }" name="api_key">
      <FormItem>
        <FormLabel>API Key *</FormLabel>
        <FormControl>
          <Input
            type="password"
            :placeholder="provider ? '••••••• (để trống để giữ nguyên)' : 'sk-...'"
            autocomplete="off"
            v-bind="componentField"
          />
        </FormControl>
        <FormDescription v-if="provider">
          Chỉ nhập nếu muốn thay API key. Hiện tại: {{ provider.api_key }}
        </FormDescription>
        <FormMessage />
      </FormItem>
    </FormField>

    <!-- Model -->
    <FormField v-slot="{ componentField }" name="model">
      <FormItem>
        <FormLabel>Model *</FormLabel>
        <FormControl>
          <Input placeholder="gpt-4o-mini / claude-3-5-haiku / gemini-1.5-flash" v-bind="componentField" />
        </FormControl>
        <FormMessage />
      </FormItem>
    </FormField>

    <!-- Timeout -->
    <FormField v-slot="{ componentField }" name="timeout_sec">
      <FormItem>
        <FormLabel>Timeout (giây)</FormLabel>
        <FormControl>
          <Input type="number" min="5" max="120" v-bind="componentField" />
        </FormControl>
        <FormDescription>Thời gian chờ tối đa cho mỗi request (5–120s)</FormDescription>
        <FormMessage />
      </FormItem>
    </FormField>

    <!-- Is Default -->
    <FormField v-slot="{ value, handleChange }" name="is_default" type="checkbox">
      <FormItem class="flex items-center gap-3">
        <FormControl>
          <input
            type="checkbox"
            class="size-4 rounded border-border"
            :checked="value"
            @change="handleChange"
          />
        </FormControl>
        <div>
          <FormLabel class="cursor-pointer">Đặt làm provider mặc định</FormLabel>
          <FormDescription>Sẽ được dùng khi không chỉ định provider cụ thể</FormDescription>
        </div>
      </FormItem>
    </FormField>

    <!-- Actions -->
    <div class="flex justify-end gap-3 pt-2">
      <Button type="button" variant="outline" @click="$emit('cancel')">Hủy</Button>
      <Button type="submit" :disabled="isSubmitting">
        <Loader2 v-if="isSubmitting" class="mr-2 size-4 animate-spin" />
        {{ provider ? 'Cập nhật' : 'Tạo mới' }}
      </Button>
    </div>
  </form>
</template>
