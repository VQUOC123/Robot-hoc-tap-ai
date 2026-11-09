<script setup lang="ts">
import { ref, computed } from 'vue'
import PageContainer from '@/shared/components/layout/PageContainer.vue'
import AnalysisFilters from '@/features/analyses/components/AnalysisFilters.vue'
import AnalysisTable from '@/features/analyses/components/AnalysisTable.vue'
import AnalysisDetail from '@/features/analyses/components/AnalysisDetail.vue'
import { useInfiniteAnalyses } from '@/features/analyses/composables/useAnalyses'
import type { Analysis, AnalysisFilters as Filters } from '@/features/analyses/types'

const activeFilters = ref<Omit<Filters, 'cursor'>>({})
const selectedAnalysis = ref<Analysis | null>(null)
const detailOpen = ref(false)

const { data, isLoading, isFetchingNextPage, hasMore, fetchNextPage } =
  useInfiniteAnalyses(activeFilters)

function onFiltersChange(filters: Filters) {
  activeFilters.value = filters
}

function openDetail(analysis: Analysis) {
  selectedAnalysis.value = analysis
  detailOpen.value = true
}
</script>

<template>
  <PageContainer
    title="Lịch sử phân tích"
    description="Kết quả AI phân tích hoạt động học sinh từ các thiết bị"
  >
    <AnalysisFilters @change="onFiltersChange" />

    <AnalysisTable
      :data="data"
      :is-loading="isLoading"
      :has-more="hasMore"
      :is-fetching-more="isFetchingNextPage"
      @load-more="fetchNextPage"
      @select="openDetail"
    />

    <AnalysisDetail
      v-model:open="detailOpen"
      :analysis="selectedAnalysis"
    />
  </PageContainer>
</template>
