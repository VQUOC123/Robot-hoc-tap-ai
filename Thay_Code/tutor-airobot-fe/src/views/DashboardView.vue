<script setup lang="ts">
import { computed } from 'vue'
import { BarChart3, Activity, Cpu, Monitor, BookOpen, Clock } from 'lucide-vue-next'
import PageContainer from '@/shared/components/layout/PageContainer.vue'
import SubjectChart from '@/features/analyses/components/SubjectChart.vue'
import LatencyChart from '@/features/analyses/components/LatencyChart.vue'
import AnalysisTable from '@/features/analyses/components/AnalysisTable.vue'
import {
  useOverviewStats,
  useLatencyStats,
  useSubjectStats,
  useInfiniteAnalyses,
} from '@/features/analyses/composables/useAnalyses'
import { formatMs, formatConfidence } from '@/shared/utils'
import { ref } from 'vue'

const { data: overview, isLoading: statsLoading } = useOverviewStats()
const { data: latencyStats } = useLatencyStats()
const { data: subjectStats } = useSubjectStats()

// Recent analyses — just first page, limit 8
const recentFilters = ref({ limit: 8 })
const { data: recentData, isLoading: recentLoading } = useInfiniteAnalyses(recentFilters)

const statCards = computed(() => [
  {
    label: 'Tổng phân tích',
    value: overview.value?.total_analyses?.toLocaleString() ?? '—',
    icon: BarChart3,
    color: 'text-blue-500',
    bg: 'bg-blue-50 dark:bg-blue-950/30',
  },
  {
    label: 'Hôm nay',
    value: overview.value?.today_total?.toLocaleString() ?? '—',
    icon: Activity,
    color: 'text-green-500',
    bg: 'bg-green-50 dark:bg-green-950/30',
  },
  {
    label: 'Tỉ lệ làm bài',
    value: overview.value != null
      ? formatConfidence(overview.value.homework_rate)
      : '—',
    icon: BookOpen,
    color: 'text-amber-500',
    bg: 'bg-amber-50 dark:bg-amber-950/30',
  },
  {
    label: 'Avg latency',
    value: overview.value != null
      ? formatMs(overview.value.avg_latency_ms)
      : '—',
    icon: Clock,
    color: 'text-purple-500',
    bg: 'bg-purple-50 dark:bg-purple-950/30',
  },
  {
    label: 'AI Providers',
    value: overview.value?.active_providers?.toLocaleString() ?? '—',
    icon: Cpu,
    color: 'text-indigo-500',
    bg: 'bg-indigo-50 dark:bg-indigo-950/30',
  },
  {
    label: 'Thiết bị kết nối',
    value: overview.value?.active_devices?.toLocaleString() ?? '—',
    icon: Monitor,
    color: 'text-orange-500',
    bg: 'bg-orange-50 dark:bg-orange-950/30',
  },
])
</script>

<template>
  <PageContainer title="Dashboard" description="Tổng quan hệ thống Tutor AI Robot">
    <!-- KPI Cards -->
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      <div
        v-for="card in statCards"
        :key="card.label"
        class="flex items-center gap-3 rounded-xl border bg-card p-4"
      >
        <div
          :class="[
            'flex size-9 flex-shrink-0 items-center justify-center rounded-lg',
            card.bg,
          ]"
        >
          <component :is="card.icon" :class="['size-4', card.color]" />
        </div>
        <div class="min-w-0">
          <p class="truncate text-xs text-muted-foreground">{{ card.label }}</p>
          <p class="text-xl font-bold leading-tight">
            <span v-if="statsLoading" class="inline-block h-5 w-12 animate-pulse rounded bg-muted" />
            <template v-else>{{ card.value }}</template>
          </p>
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div class="grid gap-4 md:grid-cols-2">
      <div class="rounded-xl border bg-card p-4">
        <h3 class="mb-3 text-sm font-semibold">Phân bố môn học</h3>
        <SubjectChart :stats="subjectStats ?? []" />
      </div>
      <div class="rounded-xl border bg-card p-4">
        <h3 class="mb-3 text-sm font-semibold">Latency AI (24h)</h3>
        <LatencyChart :stats="latencyStats ?? []" />
      </div>
    </div>

    <!-- Recent analyses -->
    <div class="rounded-xl border bg-card">
      <div class="border-b px-4 py-3">
        <h3 class="text-sm font-semibold">Phân tích gần đây</h3>
      </div>
      <div class="p-4">
        <AnalysisTable
          :data="recentData"
          :is-loading="recentLoading"
          :has-more="false"
        />
      </div>
    </div>
  </PageContainer>
</template>
