import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import { queryKeys } from '@/shared/utils'
import { settingsApi } from '../api/settings.api'
import type { SystemSettings } from '../types'

export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings.all(),
    queryFn: settingsApi.get,
    staleTime: 60_000,
  })
}

export function useUpdateSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<SystemSettings>) => settingsApi.update(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.settings.all() })
      toast.success('Đã lưu cài đặt')
    },
    onError: (e: any) => toast.error(e?.message ?? 'Lưu cài đặt thất bại'),
  })
}
