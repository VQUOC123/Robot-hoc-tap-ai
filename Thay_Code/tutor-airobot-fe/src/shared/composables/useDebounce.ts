import { useDebounce as _useDebounce } from '@vueuse/core'
import type { Ref } from 'vue'

export function useDebounce<T>(value: Ref<T>, delay = 300): Ref<T> {
  return _useDebounce(value, delay)
}
