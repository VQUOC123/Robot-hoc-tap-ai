<script setup lang="ts">
import { h } from 'vue'
import type { ColumnDef } from '@tanstack/vue-table'
import { CheckCircle, XCircle, ExternalLink } from 'lucide-vue-next'
import DataTable from '@/shared/components/data-table/DataTable.vue'
import DataTablePagination from '@/shared/components/data-table/DataTablePagination.vue'
import { Badge } from '@/shared/components/ui/badge'
import { formatDate, formatMs, formatSubject, formatConfidence } from '@/shared/utils'
import type { Analysis } from '../types'

interface Props {
  data: Analysis[]
  isLoading: boolean
  hasMore: boolean
  isFetchingMore?: boolean
}

const props = withDefaults(defineProps<Props>(), { isFetchingMore: false })
const emit = defineEmits<{ loadMore: []; select: [analysis: Analysis] }>()

const columns: ColumnDef<Analysis>[] = [
  {
    accessorKey: 'created_at',
    header: 'Thời gian',
    cell: ({ row }) =>
      h('span', { class: 'text-sm whitespace-nowrap' }, formatDate(row.original.created_at)),
  },
  {
    accessorKey: 'device_name',
    header: 'Thiết bị',
    cell: ({ row }) =>
      h('span', { class: 'text-sm font-medium' }, row.original.device_name),
  },
  {
    accessorKey: 'doing_hw',
    header: 'Làm bài',
    cell: ({ row }) => {
      const v = row.original.doing_hw
      if (v == null) return h('span', { class: 'text-muted-foreground text-xs' }, '—')
      return v
        ? h('div', { class: 'flex items-center gap-1 text-green-600' }, [
            h(CheckCircle, { class: 'size-3.5' }),
            h('span', { class: 'text-xs font-medium' }, 'Có'),
          ])
        : h('div', { class: 'flex items-center gap-1 text-muted-foreground' }, [
            h(XCircle, { class: 'size-3.5' }),
            h('span', { class: 'text-xs' }, 'Không'),
          ])
    },
  },
  {
    accessorKey: 'subject',
    header: 'Môn',
    cell: ({ row }) =>
      row.original.subject
        ? h(Badge, { variant: 'secondary', class: 'text-xs' }, () => formatSubject(row.original.subject!))
        : h('span', { class: 'text-muted-foreground text-xs' }, '—'),
  },
  {
    accessorKey: 'progress',
    header: 'Tiến độ',
    cell: ({ row }) => {
      const p = row.original.progress
      if (p === undefined || p === null) return h('span', { class: 'text-muted-foreground text-xs' }, '—')
      return h('div', { class: 'flex items-center gap-2' }, [
        h('div', { class: 'h-1.5 w-16 rounded-full bg-muted overflow-hidden' }, [
          h('div', { class: 'h-full rounded-full bg-primary transition-all', style: { width: `${p}%` } }),
        ]),
        h('span', { class: 'text-xs text-muted-foreground' }, `${p}%`),
      ])
    },
  },
  {
    accessorKey: 'confidence',
    header: 'Confidence',
    cell: ({ row }) =>
      h('span', { class: 'text-sm' }, row.original.confidence != null ? formatConfidence(row.original.confidence) : '—'),
  },
  {
    accessorKey: 'latency_ms',
    header: 'Latency',
    cell: ({ row }) =>
      h('span', { class: 'text-sm text-muted-foreground' }, row.original.latency_ms != null ? formatMs(row.original.latency_ms) : '—'),
  },
  {
    id: 'detail',
    header: '',
    cell: ({ row }) =>
      h(
        'button',
        {
          class: 'inline-flex size-7 items-center justify-center rounded-md hover:bg-accent text-muted-foreground',
          onClick: () => emit('select', row.original),
        },
        h(ExternalLink, { class: 'size-3.5' }),
      ),
  },
]
</script>

<template>
  <div class="space-y-3">
    <DataTable
      :columns="columns"
      :data="data"
      :is-loading="isLoading"
      empty-title="Chưa có dữ liệu phân tích"
      empty-description="Kết quả phân tích từ thiết bị sẽ xuất hiện ở đây"
    />
    <DataTablePagination
      :has-more="hasMore"
      :is-fetching-more="isFetchingMore"
      :total-loaded="data.length"
      @load-more="$emit('loadMore')"
    />
  </div>
</template>
