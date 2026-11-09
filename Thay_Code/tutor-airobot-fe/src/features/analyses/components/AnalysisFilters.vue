<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Search, X } from 'lucide-vue-next'
import { Input } from '@/shared/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { useDebounce } from '@/shared/composables/useDebounce'
import type { AnalysisFilters } from '../types'

const emit = defineEmits<{ change: [filters: AnalysisFilters] }>()

const deviceSearch = ref('')
const debouncedDevice = useDebounce(deviceSearch)
const subject = ref('')
const doingHw = ref('')
const fromDate = ref('')
const toDate = ref('')

watch([debouncedDevice, subject, doingHw, fromDate, toDate], () => {
  const filters: AnalysisFilters = {}
  if (debouncedDevice.value) filters.device_id = debouncedDevice.value
  if (subject.value) filters.subject = subject.value
  if (doingHw.value !== '') filters.doing_hw = doingHw.value === 'true'
  if (fromDate.value) filters.from = fromDate.value
  if (toDate.value) filters.to = toDate.value
  emit('change', filters)
})

const hasFilters = computed(
  () => !!deviceSearch.value || !!subject.value || !!doingHw.value || !!fromDate.value || !!toDate.value,
)

function clearFilters() {
  deviceSearch.value = ''
  subject.value = ''
  doingHw.value = ''
  fromDate.value = ''
  toDate.value = ''
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <!-- Device search -->
    <div class="relative">
      <Search class="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
      <Input
        v-model="deviceSearch"
        placeholder="Tìm thiết bị..."
        class="h-8 w-40 pl-8 text-sm"
      />
    </div>

    <!-- Subject -->
    <Select v-model="subject">
      <SelectTrigger class="h-8 w-32 text-sm">
        <SelectValue placeholder="Môn học" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="">Tất cả</SelectItem>
        <SelectItem value="math">Toán</SelectItem>
        <SelectItem value="vietnamese">Văn</SelectItem>
        <SelectItem value="english">Anh</SelectItem>
        <SelectItem value="physics">Lý</SelectItem>
        <SelectItem value="chemistry">Hóa</SelectItem>
        <SelectItem value="biology">Sinh</SelectItem>
        <SelectItem value="other">Khác</SelectItem>
      </SelectContent>
    </Select>

    <!-- Doing HW -->
    <Select v-model="doingHw">
      <SelectTrigger class="h-8 w-36 text-sm">
        <SelectValue placeholder="Trạng thái" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="">Tất cả</SelectItem>
        <SelectItem value="true">Đang làm bài</SelectItem>
        <SelectItem value="false">Không làm bài</SelectItem>
      </SelectContent>
    </Select>

    <!-- Date range -->
    <Input v-model="fromDate" type="date" class="h-8 w-36 text-sm" title="Từ ngày" />
    <Input v-model="toDate" type="date" class="h-8 w-36 text-sm" title="Đến ngày" />

    <!-- Clear filters -->
    <button
      v-if="hasFilters"
      class="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs hover:bg-accent transition-colors"
      @click="clearFilters"
    >
      <X class="size-3" /> Xóa bộ lọc
    </button>
  </div>
</template>
