<script setup lang="ts" generic="TData">
import {
  useVueTable,
  getCoreRowModel,
  getSortedRowModel,
  FlexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/vue-table'
import { ref } from 'vue'
import LoadingSpinner from '../feedback/LoadingSpinner.vue'
import EmptyState from '../feedback/EmptyState.vue'
import DataTableColumnHeader from './DataTableColumnHeader.vue'

interface Props {
  columns: ColumnDef<TData>[]
  data: TData[]
  isLoading?: boolean
  hasMore?: boolean
  onLoadMore?: () => void
  emptyTitle?: string
  emptyDescription?: string
}

const props = withDefaults(defineProps<Props>(), {
  isLoading: false,
  hasMore: false,
})

const sorting = ref<SortingState>([])

const table = useVueTable({
  get data() {
    return props.data
  },
  get columns() {
    return props.columns
  },
  state: {
    get sorting() {
      return sorting.value
    },
  },
  onSortingChange: (updater) => {
    sorting.value = typeof updater === 'function' ? updater(sorting.value) : updater
  },
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
})
</script>

<template>
  <div class="space-y-3">
    <!-- Toolbar slot (filters, search, actions) -->
    <slot name="toolbar" />

    <!-- Loading state -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <LoadingSpinner text="Đang tải dữ liệu..." />
    </div>

    <!-- Table -->
    <template v-else>
      <div class="overflow-hidden rounded-lg border">
        <table class="w-full caption-bottom text-sm">
          <thead class="border-b bg-muted/40">
            <tr v-for="hg in table.getHeaderGroups()" :key="hg.id">
              <DataTableColumnHeader
                v-for="header in hg.headers"
                :key="header.id"
                :header="header"
              />
            </tr>
          </thead>
          <tbody>
            <template v-if="table.getRowModel().rows.length">
              <tr
                v-for="row in table.getRowModel().rows"
                :key="row.id"
                class="border-b transition-colors hover:bg-muted/30 last:border-0"
              >
                <td
                  v-for="cell in row.getVisibleCells()"
                  :key="cell.id"
                  class="px-3 py-3 align-middle"
                >
                  <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
                </td>
              </tr>
            </template>
            <tr v-else>
              <td :colspan="columns.length">
                <EmptyState
                  :title="emptyTitle"
                  :description="emptyDescription"
                  class="py-10"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Load more (cursor pagination) -->
      <div v-if="hasMore" class="flex justify-center pt-2">
        <button
          class="rounded-md border px-4 py-1.5 text-sm hover:bg-accent transition-colors"
          @click="onLoadMore?.()"
        >
          Tải thêm
        </button>
      </div>
    </template>
  </div>
</template>
