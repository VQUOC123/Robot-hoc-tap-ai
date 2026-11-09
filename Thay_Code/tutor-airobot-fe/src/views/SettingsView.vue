<script setup lang="ts">
import PageContainer from '@/shared/components/layout/PageContainer.vue'
import SettingsForm from '@/features/settings/components/SettingsForm.vue'
import LoadingSpinner from '@/shared/components/feedback/LoadingSpinner.vue'
import ErrorState from '@/shared/components/feedback/ErrorState.vue'
import { useSettings } from '@/features/settings/composables/useSettings'

const { data, isLoading, isError, refetch } = useSettings()
</script>

<template>
  <PageContainer
    title="Cài đặt"
    description="Cấu hình hệ thống: rate limit, timeout, log retention..."
  >
    <LoadingSpinner v-if="isLoading" text="Đang tải cài đặt..." />
    <ErrorState
      v-else-if="isError"
      message="Không thể tải cài đặt hệ thống"
      :on-retry="refetch"
    />
    <SettingsForm v-else-if="data" :settings="data" />
  </PageContainer>
</template>
