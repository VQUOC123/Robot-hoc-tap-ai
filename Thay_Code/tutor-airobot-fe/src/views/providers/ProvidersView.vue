<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Plus } from 'lucide-vue-next'
import PageContainer from '@/shared/components/layout/PageContainer.vue'
import { Button } from '@/shared/components/ui/button'
import ProviderTable from '@/features/providers/components/ProviderTable.vue'
import ErrorState from '@/shared/components/feedback/ErrorState.vue'
import { useProviderList } from '@/features/providers/composables/useProviders'

const router = useRouter()
const { data, isLoading, isError, refetch } = useProviderList()
</script>

<template>
  <PageContainer
    title="AI Providers"
    description="Quản lý nhà cung cấp AI: OpenAI, Claude, Gemini..."
  >
    <template #actions>
      <Button @click="router.push('/providers/new')">
        <Plus class="mr-2 size-4" />
        Thêm Provider
      </Button>
    </template>

    <ErrorState
      v-if="isError"
      message="Không thể tải danh sách providers"
      :on-retry="refetch"
    />
    <ProviderTable
      v-else
      :data="data ?? []"
      :is-loading="isLoading"
      @edit="(id) => router.push(`/providers/${id}`)"
    />
  </PageContainer>
</template>
