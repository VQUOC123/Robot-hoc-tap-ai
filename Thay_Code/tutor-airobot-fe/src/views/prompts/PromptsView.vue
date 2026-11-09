<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Plus } from 'lucide-vue-next'
import PageContainer from '@/shared/components/layout/PageContainer.vue'
import { Button } from '@/shared/components/ui/button'
import PromptTable from '@/features/prompts/components/PromptTable.vue'
import ErrorState from '@/shared/components/feedback/ErrorState.vue'
import { usePromptList } from '@/features/prompts/composables/usePrompts'

const router = useRouter()
const { data, isLoading, isError, refetch } = usePromptList()
</script>

<template>
  <PageContainer
    title="Prompts"
    description="Quản lý prompt template gửi đến AI để phân tích ảnh học sinh"
  >
    <template #actions>
      <Button @click="router.push('/prompts/new')">
        <Plus class="mr-2 size-4" />
        Thêm Prompt
      </Button>
    </template>

    <ErrorState
      v-if="isError"
      message="Không thể tải danh sách prompts"
      :on-retry="refetch"
    />
    <PromptTable
      v-else
      :data="data ?? []"
      :is-loading="isLoading"
      @edit="(id) => router.push(`/prompts/${id}`)"
    />
  </PageContainer>
</template>
