<script setup lang="ts">
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from 'chart.js'
import { format } from 'date-fns'
import { vi } from 'date-fns/locale'
import type { LatencyStat } from '../types'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

interface Props {
  stats: LatencyStat[]
}

const props = defineProps<Props>()

const chartData = computed(() => ({
  labels: props.stats.map((s) =>
    format(new Date(s.hour), 'HH:mm', { locale: vi }),
  ),
  datasets: [
    {
      label: 'Avg latency (ms)',
      data: props.stats.map((s) => s.avg_ms),
      backgroundColor: '#3b82f680',
      borderColor: '#3b82f6',
      borderWidth: 1,
      borderRadius: 4,
    },
  ],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx: { raw: unknown }) => ` ${ctx.raw}ms`,
      },
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: { font: { size: 11 } },
      grid: { color: 'rgba(0,0,0,0.06)' },
    },
    x: {
      ticks: { font: { size: 11 } },
      grid: { display: false },
    },
  },
}
</script>

<template>
  <div class="relative h-56">
    <Bar v-if="stats.length" :data="chartData" :options="chartOptions" />
    <div
      v-else
      class="flex h-full items-center justify-center text-sm text-muted-foreground"
    >
      Chưa có dữ liệu
    </div>
  </div>
</template>
