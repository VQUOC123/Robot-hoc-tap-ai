<script setup lang="ts">
import { ref } from 'vue'
import { Plus } from 'lucide-vue-next'
import PageContainer from '@/shared/components/layout/PageContainer.vue'
import { Button } from '@/shared/components/ui/button'
import DeviceTable from '@/features/devices/components/DeviceTable.vue'
import CreateDeviceDialog from '@/features/devices/components/CreateDeviceDialog.vue'
import ErrorState from '@/shared/components/feedback/ErrorState.vue'
import { useDeviceList } from '@/features/devices/composables/useDevices'

const showCreate = ref(false)
const { data, isLoading, isError, refetch } = useDeviceList()
</script>

<template>
  <PageContainer
    title="Thiết bị"
    description="Quản lý thiết bị Raspberry Pi camera kết nối với hệ thống"
  >
    <template #actions>
      <Button @click="showCreate = true">
        <Plus class="mr-2 size-4" />
        Thêm thiết bị
      </Button>
    </template>

    <ErrorState
      v-if="isError"
      message="Không thể tải danh sách thiết bị"
      :on-retry="refetch"
    />
    <DeviceTable v-else :data="data ?? []" :is-loading="isLoading" />

    <CreateDeviceDialog v-model:open="showCreate" />
  </PageContainer>
</template>
