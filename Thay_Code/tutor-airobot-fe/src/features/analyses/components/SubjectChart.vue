<script setup lang="ts">
import { computed } from 'vue'
import { Pie } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js'
import { formatSubject } from '@/shared/utils'
import type { SubjectStat } from '../types'

ChartJS.register(ArcElement, Tooltip, Legend)

interface Props {
  stats: SubjectStat[]
}

const props = defineProps<Props>()

const COLORS = [
  '#3b82f6', // blue  — math
  '#f59e0b', // amber — vietnamese
  '#10b981', // green — english
  '#8b5cf6', // violet — physics
  '#ef4444', // red   — chemistry
  '#06b6d4', // cyan  — biology
  '#f97316', // orange — history
  '#6366f1', // indigo — geography
  '#64748b', // slate — other
]

const chartData = computed(() => ({
  labels: props.stats.map((s) => formatSubject(s.subject)),
  datasets: [
    {
      data: props.stats.map((s) => s.count),
      backgroundColor: COLORS.slice(0, props.stats.length),
      borderWidth: 2,
      borderColor: 'transparent',
      hoverBorderColor: '#fff',
    },
  ],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom' as const,
      labels: {
        padding: 12,
        usePointStyle: true,
        pointStyleWidth: 8,
        font: { size: 12 },
      },
    },
    tooltip: {
      callbacks: {
        label: (ctx: { label: string; raw: unknown; dataset: { data: number[] } }) => {
          const total = ctx.dataset.data.reduce((a, b) => a + b, 0)
          const pct = total > 0 ? Math.round(((ctx.raw as number) / total) * 100) : 0
          return ` ${ctx.label}: ${ctx.raw} (${pct}%)`
        },
      },
    },
  },
}
</script>

<template>
  <div class="relative h-56">
    <Pie v-if="stats.length" :data="chartData" :options="chartOptions" />
    <div
      v-else
      class="flex h-full items-center justify-center text-sm text-muted-foreground"
    >
      Chưa có dữ liệu
    </div>
  </div>
</template>
