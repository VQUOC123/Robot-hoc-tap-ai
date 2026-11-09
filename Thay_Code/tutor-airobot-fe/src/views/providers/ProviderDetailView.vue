<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import PageContainer from '@/shared/components/layout/PageContainer.vue'
import { Button } from '@/shared/components/ui/button'
import ProviderForm from '@/features/providers/components/ProviderForm.vue'
import LoadingSpinner from '@/shared/components/feedback/LoadingSpinner.vue'
import {
  useProvider,
  useCreateProvider,
  useUpdateProvider,
} from '@/features/providers/composables/useProviders'
import type { ProviderFormValues } from '@/features/providers/schemas/provider.schema'

const route = useRoute()
const router = useRouter()

const id = computed(() => route.params.id as string | undefined)
const isNew = computed(() => !id.value || route.name === 'provider-new')

const { data: provider, isLoading } = useProvider(id.value ?? '')
const { mutate: create, isPending: isCreating } = useCreateProvider()
const { mutate: update, isPending: isUpdating } = useUpdateProvider()

const isSubmitting = computed(() => isCreating.value || isUpdating.value)

function handleSubmit(values: ProviderFormValues) {
  if (isNew.value) {
    create(values, { onSuccess: () => router.push('/providers') })
  } else {
    update({ id: id.value!, data: values }, { onSuccess: () => router.push('/providers') })
  }
}
</script>

<template>
  <PageContainer :title="isNew ? 'Thêm Provider' : 'Chỉnh sửa Provider'">
    <template #actions>
      <Button variant="outline" @click="router.push('/providers')">
        <ArrowLeft class="mr-2 size-4" />
        Quay lại
      </Button>
    </template>

    <div class="max-w-xl rounded-xl border bg-card p-6">
      <LoadingSpinner v-if="!isNew && isLoading" />
      <ProviderForm
        v-else
        :provider="provider"
        :is-submitting="isSubmitting"
        @submit="handleSubmit"
        @cancel="router.push('/providers')"
      />
    </div>
  </PageContainer>
</template>
