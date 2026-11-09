<script setup lang="ts">
import { computed } from 'vue'
import { CheckCircle, XCircle } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import { Badge } from '@/shared/components/ui/badge'
import { Separator } from '@/shared/components/ui/separator'
import {
  formatDate,
  formatMs,
  formatSubject,
  formatConfidence,
} from '@/shared/utils'
import type { Analysis } from '../types'

interface Props {
  analysis: Analysis | null
}

const props = defineProps<Props>()
const model = defineModel<boolean>('open', { default: false })

const hwTypeLabel: Record<string, string> = {
  exercises: 'Bài tập',
  theory: 'Lý thuyết',
  reading: 'Đọc hiểu',
}

const subjectLabel = computed(() =>
  props.analysis?.subject ? formatSubject(props.analysis.subject) : '—',
)
</script>

<template>
  <Dialog :open="model" @update:open="(v) => (model = v)">
    <DialogContent class="max-w-lg">
      <DialogHeader>
        <DialogTitle>Chi tiết phân tích</DialogTitle>
      </DialogHeader>

      <div v-if="analysis" class="space-y-4">
        <!-- Main result -->
        <div class="grid grid-cols-2 gap-3">
          <div class="rounded-lg border p-3">
            <p class="text-xs text-muted-foreground">Làm bài tập</p>
            <div class="mt-1 flex items-center gap-1.5">
              <template v-if="analysis.doing_hw != null">
                <CheckCircle v-if="analysis.doing_hw" class="size-4 text-green-500" />
                <XCircle v-else class="size-4 text-muted-foreground" />
                <span class="font-medium">{{ analysis.doing_hw ? 'Có' : 'Không' }}</span>
              </template>
              <span v-else class="text-muted-foreground">—</span>
            </div>
          </div>
          <div class="rounded-lg border p-3">
            <p class="text-xs text-muted-foreground">Môn học</p>
            <p class="mt-1 font-medium">{{ subjectLabel }}</p>
          </div>
          <div class="rounded-lg border p-3">
            <p class="text-xs text-muted-foreground">Lớp</p>
            <p class="mt-1 font-medium">{{ analysis.grade ?? '—' }}</p>
          </div>
          <div class="rounded-lg border p-3">
            <p class="text-xs text-muted-foreground">Loại bài</p>
            <p class="mt-1 font-medium">{{ hwTypeLabel[analysis.hw_type ?? ''] ?? '—' }}</p>
          </div>
        </div>

        <!-- Progress -->
        <div v-if="analysis.progress !== undefined" class="space-y-1">
          <div class="flex justify-between text-sm">
            <span class="text-muted-foreground">Tiến độ</span>
            <span class="font-medium">{{ analysis.progress }}%</span>
          </div>
          <div class="h-2 w-full rounded-full bg-muted overflow-hidden">
            <div
              class="h-full rounded-full bg-primary transition-all"
              :style="{ width: `${analysis.progress}%` }"
            />
          </div>
        </div>

        <!-- AI suggestion -->
        <div v-if="analysis.hints" class="rounded-lg border bg-muted/40 p-3">
          <p class="mb-1 text-xs font-medium text-muted-foreground">Gợi ý AI</p>
          <p class="text-sm">{{ analysis.hints }}</p>
        </div>

        <Separator />

        <!-- Metadata -->
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span class="text-muted-foreground">Thiết bị:</span>
            <span class="ml-1 font-medium">{{ analysis.device_name }}</span>
          </div>
          <div>
            <span class="text-muted-foreground">Provider:</span>
            <span class="ml-1">{{ analysis.provider_name }}</span>
          </div>
          <div>
            <span class="text-muted-foreground">Confidence:</span>
            <span class="ml-1">{{ analysis.confidence != null ? formatConfidence(analysis.confidence) : '—' }}</span>
          </div>
          <div>
            <span class="text-muted-foreground">Latency:</span>
            <span class="ml-1">{{ analysis.latency_ms != null ? formatMs(analysis.latency_ms) : '—' }}</span>
          </div>
          <div class="col-span-2">
            <span class="text-muted-foreground">Thời gian:</span>
            <span class="ml-1">{{ formatDate(analysis.created_at) }}</span>
          </div>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
