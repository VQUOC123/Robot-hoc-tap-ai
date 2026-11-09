import { useClipboard } from '@vueuse/core'
import { toast } from 'vue-sonner'

export function useCopyToClipboard() {
  const { copy, copied } = useClipboard()

  async function copyToClipboard(text: string, label = 'Đã sao chép vào clipboard') {
    await copy(text)
    if (copied.value) toast.success(label)
  }

  return { copy: copyToClipboard, copied }
}
