<script setup lang="ts">
import { h } from 'vue'
import type { ColumnDef } from '@tanstack/vue-table'
import { MoreHorizontal, Wifi, WifiOff } from 'lucide-vue-next'
import DataTable from '@/shared/components/data-table/DataTable.vue'
import { Badge } from '@/shared/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/shared/components/ui/dropdown-menu'
import { useConfirm } from '@/shared/composables/useConfirm'
import { formatDate, formatRelativeTime } from '@/shared/utils'
import { useRevokeDevice } from '../composables/useDevices'
import type { Device } from '../types'

defineProps<{ data: Device[]; isLoading: boolean }>()

const { confirm } = useConfirm()
const { mutate: revokeDevice, isPending } = useRevokeDevice()

async function handleRevoke(device: Device) {
  const ok = await confirm({
    title: `Thu hồi quyền "${device.name}"?`,
    description: 'Thiết bị sẽ không thể gửi dữ liệu cho đến khi được cấp token mới.',
    confirmText: 'Thu hồi',
    variant: 'destructive',
  })
  if (ok) revokeDevice(device.id)
}

const columns: ColumnDef<Device>[] = [
  {
    accessorKey: 'name',
    header: 'Tên thiết bị',
    cell: ({ row }) =>
      h('div', [
        h('p', { class: 'font-medium' }, row.original.name),
        row.original.last_ip
          ? h('p', { class: 'text-xs text-muted-foreground' }, row.original.last_ip)
          : null,
      ]),
  },
  {
    accessorKey: 'is_active',
    header: 'Trạng thái',
    cell: ({ row }) =>
      h('div', { class: 'flex items-center gap-1.5' }, [
        row.original.is_active
          ? h(Wifi, { class: 'size-3.5 text-green-500' })
          : h(WifiOff, { class: 'size-3.5 text-muted-foreground' }),
        row.original.is_active
          ? h(Badge, { variant: 'default' }, () => 'Hoạt động')
          : h(Badge, { variant: 'secondary' }, () => 'Bị thu hồi'),
      ]),
  },
  {
    accessorKey: 'last_used_at',
    header: 'Truy cập gần nhất',
    cell: ({ row }) =>
      row.original.last_used_at
        ? h('span', { class: 'text-sm text-muted-foreground' }, formatRelativeTime(row.original.last_used_at))
        : h('span', { class: 'text-sm text-muted-foreground' }, 'Chưa kết nối'),
  },
  {
    accessorKey: 'created_at',
    header: 'Tạo lúc',
    cell: ({ row }) =>
      h('span', { class: 'text-sm text-muted-foreground' }, formatDate(row.original.created_at)),
  },
  {
    id: 'actions',
    header: '',
    cell: ({ row }) =>
      h(DropdownMenu, {}, {
        default: () => [
          h(DropdownMenuTrigger, { asChild: true }, () =>
            h('button', { class: 'inline-flex size-7 items-center justify-center rounded-md hover:bg-accent' }, h(MoreHorizontal, { class: 'size-4' })),
          ),
          h(DropdownMenuContent, { align: 'end' }, () => [
            h(DropdownMenuItem, {
              class: 'text-destructive focus:text-destructive',
              onClick: () => handleRevoke(row.original),
              disabled: isPending.value || !row.original.is_active,
            }, () => 'Thu hồi quyền truy cập'),
          ]),
        ],
      }),
  },
]
</script>

<template>
  <DataTable
    :columns="columns"
    :data="data"
    :is-loading="isLoading"
    empty-title="Chưa có thiết bị"
    empty-description="Thêm thiết bị Raspberry Pi để bắt đầu nhận dữ liệu"
  />
</template>
