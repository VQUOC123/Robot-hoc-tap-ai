import { useInfiniteQuery, useQuery } from '@tanstack/vue-query'
import { computed, type Ref } from 'vue'
import { queryKeys } from '@/shared/utils'
import { analysesApi } from '../api/analyses.api'
import type { AnalysisFilters } from '../types'

export function useInfiniteAnalyses(filters: Ref<Omit<AnalysisFilters, 'cursor'>>) {
  const query = useInfiniteQuery({
    queryKey: computed(() => queryKeys.analyses.infinite(filters.value)),
    queryFn: ({ pageParam }) =>
      analysesApi.list({ ...filters.value, cursor: pageParam as string | undefined, limit: filters.value.limit ?? 20 }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.meta.has_more ? (lastPage.meta.cursor ?? undefined) : undefined,
  })

  const data = computed(() => query.data.value?.pages.flatMap((p) => p.data) ?? [])
  const hasMore = computed(
    () => query.data.value?.pages.at(-1)?.meta.has_more ?? false,
  )

  return { ...query, data, hasMore }
}

export function useAnalysis(id: string) {
  return useQuery({
    queryKey: queryKeys.analyses.detail(id),
    queryFn: () => analysesApi.getById(id),
    enabled: !!id,
  })
}

export function useOverviewStats() {
  return useQuery({
    queryKey: queryKeys.stats.overview(),
    queryFn: analysesApi.getOverviewStats,
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,  // refresh every 5 min
  })
}

export function useLatencyStats() {
  return useQuery({
    queryKey: queryKeys.stats.latency(),
    queryFn: analysesApi.getLatencyStats,
    staleTime: 60_000,
  })
}

export function useSubjectStats() {
  return useQuery({
    queryKey: queryKeys.stats.subjects(),
    queryFn: analysesApi.getSubjectStats,
    staleTime: 60_000,
  })
}
