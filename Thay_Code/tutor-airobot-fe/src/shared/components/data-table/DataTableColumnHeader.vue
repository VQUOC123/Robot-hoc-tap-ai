<script setup lang="ts" generic="TData, TValue">
import type { Header } from '@tanstack/vue-table'
import { FlexRender } from '@tanstack/vue-table'
import { ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-vue-next'

interface Props {
  header: Header<TData, TValue>
}

const props = defineProps<Props>()
</script>

<template>
  <th
    :style="{ width: `${header.getSize()}px` }"
    class="h-10 px-3 text-left align-middle text-xs font-medium text-muted-foreground"
  >
    <template v-if="!props.header.isPlaceholder">
      <button
        v-if="props.header.column.getCanSort()"
        class="inline-flex items-center gap-1 rounded hover:text-foreground transition-colors"
        @click="props.header.column.toggleSorting()"
      >
        <FlexRender
          :render="props.header.column.columnDef.header"
          :props="props.header.getContext()"
        />
        <ArrowUp v-if="props.header.column.getIsSorted() === 'asc'" class="size-3" />
        <ArrowDown v-else-if="props.header.column.getIsSorted() === 'desc'" class="size-3" />
        <ArrowUpDown v-else class="size-3 opacity-40" />
      </button>
      <FlexRender
        v-else
        :render="props.header.column.columnDef.header"
        :props="props.header.getContext()"
      />
    </template>
  </th>
</template>
