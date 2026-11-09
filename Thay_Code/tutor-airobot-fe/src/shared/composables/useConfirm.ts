import { ref } from 'vue'

export interface ConfirmOptions {
  title?: string
  description?: string
  confirmText?: string
  cancelText?: string
  variant?: 'default' | 'destructive'
}

// Global singleton state — ConfirmDialog.vue renders this
const isOpen = ref(false)
const confirmOptions = ref<Required<ConfirmOptions>>({
  title: 'Xác nhận',
  description: 'Bạn có chắc chắn muốn thực hiện thao tác này?',
  confirmText: 'Xác nhận',
  cancelText: 'Hủy',
  variant: 'default',
})

let _resolve: ((value: boolean) => void) | null = null

export function useConfirm() {
  function confirm(opts: ConfirmOptions = {}): Promise<boolean> {
    confirmOptions.value = {
      title: opts.title ?? 'Xác nhận',
      description: opts.description ?? 'Bạn có chắc chắn muốn thực hiện thao tác này?',
      confirmText: opts.confirmText ?? 'Xác nhận',
      cancelText: opts.cancelText ?? 'Hủy',
      variant: opts.variant ?? 'default',
    }
    isOpen.value = true
    return new Promise((resolve) => {
      _resolve = resolve
    })
  }

  function onConfirm() {
    isOpen.value = false
    _resolve?.(true)
    _resolve = null
  }

  function onCancel() {
    isOpen.value = false
    _resolve?.(false)
    _resolve = null
  }

  return { isOpen, confirmOptions, confirm, onConfirm, onCancel }
}
