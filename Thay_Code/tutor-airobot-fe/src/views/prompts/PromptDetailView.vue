<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import PageContainer from '@/shared/components/layout/PageContainer.vue'
import { Button } from '@/shared/components/ui/button'
import PromptForm from '@/features/prompts/components/PromptForm.vue'
import LoadingSpinner from '@/shared/components/feedback/LoadingSpinner.vue'
import {
  usePrompt,
  useCreatePrompt,
  useUpdatePrompt,
} from '@/features/prompts/composables/usePrompts'
import type { PromptFormValues } from '@/features/prompts/schemas/prompt.schema'

const route = useRoute()
const router = useRouter()

const id = computed(() => route.params.id as string | undefined)
const isNew = computed(() => !id.value || route.name === 'prompt-new')

const { data: prompt, isLoading } = usePrompt(id.value ?? '')
const { mutate: create, isPending: isCreating } = useCreatePrompt()
const { mutate: update, isPending: isUpdating } = useUpdatePrompt()

const isSubmitting = computed(() => isCreating.value || isUpdating.value)

function handleSubmit(values: PromptFormValues) {
  if (isNew.value) {
    create(values, { onSuccess: () => router.push('/prompts') })
  } else {
    update({ id: id.value!, data: values }, { onSuccess: () => router.push('/prompts') })
  }
}
</script>

<template>
  <PageContainer :title="isNew ? 'Thêm Prompt' : 'Chỉnh sửa Prompt'">
    <template #actions>
      <Button variant="outline" @click="router.push('/prompts')">
        <ArrowLeft class="mr-2 size-4" />
        Quay lại
      </Button>
    </template>

    <div class="max-w-2xl rounded-xl border bg-card p-6">
      <LoadingSpinner v-if="!isNew && isLoading" />
      <PromptForm
        v-else
        :prompt="prompt"
        :is-submitting="isSubmitting"
        @submit="handleSubmit"
        @cancel="router.push('/prompts')"
      />
    </div>
  </PageContainer>
</template>
