<script setup lang="ts">
import { h } from 'vue'
import type { ColumnDef } from '@tanstack/vue-table'
import { MoreHorizontal } from 'lucide-vue-next'
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
import { formatDate, truncate } from '@/shared/utils'
import { useDeletePrompt } from '../composables/usePrompts'
import type { Prompt } from '../types'

defineProps<{ data: Prompt[]; isLoading: boolean }>()
const emit = defineEmits<{ edit: [id: string] }>()

const { confirm } = useConfirm()
const { mutate: deletePrompt, isPending: isDeleting } = useDeletePrompt()

async function handleDelete(prompt: Prompt) {
  const ok = await confirm({
    title: `Xóa prompt "${prompt.name}"?`,
    description: 'Thao tác này không thể hoàn tác.',
    confirmText: 'Xóa',
    variant: 'destructive',
  })
  if (ok) deletePrompt(prompt.id)
}

const columns: ColumnDef<Prompt>[] = [
  {
    accessorKey: 'name',
    header: 'Tên Prompt',
    cell: ({ row }) =>
      h('div', { class: 'flex items-center gap-2' }, [
        h('span', { class: 'font-medium' }, row.original.name),
        row.original.is_default ? h(Badge, { variant: 'secondary', class: 'text-xs' }, () => 'Default') : null,
      ]),
  },
  {
    accessorKey: 'description',
    header: 'Mô tả',
    cell: ({ row }) =>
      h('span', { class: 'text-sm text-muted-foreground' }, truncate(row.original.description ?? '—', 60)),
  },
  {
    accessorKey: 'content',
    header: 'Nội dung',
    cell: ({ row }) =>
      h('code', { class: 'text-xs text-muted-foreground' }, truncate(row.original.content, 50)),
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
    accessorKey: 'updated_at',
    header: 'Cập nhật',
    cell: ({ row }) =>
      h('span', { class: 'text-sm text-muted-foreground' }, formatDate(row.original.updated_at)),
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
            h(DropdownMenuItem, { onClick: () => emit('edit', row.original.id) }, () => 'Chỉnh sửa'),
            h(DropdownMenuSeparator),
            h(DropdownMenuItem, {
              class: 'text-destructive focus:text-destructive',
              onClick: () => handleDelete(row.original),
              disabled: isDeleting.value,
            }, () => 'Xóa'),
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
    empty-title="Chưa có Prompt"
    empty-description="Tạo prompt template để AI biết cách phân tích ảnh học sinh"
  />
</template>
