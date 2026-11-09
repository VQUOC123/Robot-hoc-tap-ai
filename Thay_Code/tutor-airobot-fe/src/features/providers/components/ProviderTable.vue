<script setup lang="ts">
import { h } from 'vue'
import type { ColumnDef } from '@tanstack/vue-table'
import { MoreHorizontal, Star, Wifi, WifiOff, Loader2 } from 'lucide-vue-next'
import DataTable from '@/shared/components/data-table/DataTable.vue'
import { Badge } from '@/shared/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/shared/components/ui/dropdown-menu'
import { useConfirm } from '@/shared/composables/useConfirm'
import { formatDate } from '@/shared/utils'
import {
  useDeleteProvider,
  useTestConnection,
  useSetDefaultProvider,
} from '../composables/useProviders'
import type { Provider } from '../types'

const props = defineProps<{ data: Provider[]; isLoading: boolean }>()
const emit = defineEmits<{ edit: [id: string] }>()

const { confirm } = useConfirm()
const { mutate: deleteProvider, isPending: isDeleting } = useDeleteProvider()
const { mutate: testConnection, isPending: isTesting } = useTestConnection()
const { mutate: setDefault } = useSetDefaultProvider()

async function handleDelete(provider: Provider) {
  const ok = await confirm({
    title: `Xóa "${provider.name}"?`,
    description: 'Thao tác này không thể hoàn tác. Các phân tích liên quan sẽ mất provider.',
    confirmText: 'Xóa',
    variant: 'destructive',
  })
  if (ok) deleteProvider(provider.id)
}

const columns: ColumnDef<Provider>[] = [
  {
    accessorKey: 'name',
    header: 'Tên Provider',
    cell: ({ row }) =>
      h('div', { class: 'flex items-center gap-2' }, [
        h('span', { class: 'font-medium' }, row.original.name),
        row.original.is_default
          ? h(Badge, { variant: 'secondary', class: 'text-xs' }, () => 'Default')
          : null,
      ]),
  },
  {
    accessorKey: 'model',
    header: 'Model',
    cell: ({ row }) => h('code', { class: 'text-xs bg-muted px-1.5 py-0.5 rounded' }, row.original.model),
  },
  {
    accessorKey: 'base_url',
    header: 'Base URL',
    cell: ({ row }) =>
      h('span', { class: 'max-w-48 truncate block text-sm text-muted-foreground', title: row.original.base_url }, row.original.base_url),
  },
  {
    accessorKey: 'timeout_sec',
    header: 'Timeout',
    cell: ({ row }) => h('span', { class: 'text-sm' }, `${row.original.timeout_sec}s`),
  },
  {
    accessorKey: 'is_active',
    header: 'Trạng thái',
    cell: ({ row }) =>
      row.original.is_active
        ? h(Badge, { variant: 'default' }, () => 'Hoạt động')
        : h(Badge, { variant: 'secondary' }, () => 'Vô hiệu'),
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
      h(
        DropdownMenu,
        {},
        {
          default: () => [
            h(DropdownMenuTrigger, { asChild: true }, () =>
              h(
                'button',
                { class: 'inline-flex size-7 items-center justify-center rounded-md hover:bg-accent' },
                h(MoreHorizontal, { class: 'size-4' }),
              ),
            ),
            h(DropdownMenuContent, { align: 'end' }, () => [
              h(DropdownMenuItem, { onClick: () => emit('edit', row.original.id) }, () => 'Chỉnh sửa'),
              h(
                DropdownMenuItem,
                { onClick: () => testConnection(row.original.id), disabled: isTesting.value },
                () => [isTesting.value ? h(Loader2, { class: 'mr-2 size-3 animate-spin' }) : h(Wifi, { class: 'mr-2 size-3' }), 'Test kết nối'],
              ),
              !row.original.is_default
                ? h(DropdownMenuItem, { onClick: () => setDefault(row.original.id) }, () => [h(Star, { class: 'mr-2 size-3' }), 'Đặt làm Default'])
                : null,
              h(DropdownMenuSeparator),
              h(
                DropdownMenuItem,
                {
                  class: 'text-destructive focus:text-destructive',
                  onClick: () => handleDelete(row.original),
                  disabled: isDeleting.value,
                },
                () => 'Xóa',
              ),
            ]),
          ],
        },
      ),
  },
]
</script>

<template>
  <DataTable
    :columns="columns"
    :data="data"
    :is-loading="isLoading"
    empty-title="Chưa có AI Provider"
    empty-description="Thêm provider đầu tiên để bắt đầu phân tích"
  />
</template>
