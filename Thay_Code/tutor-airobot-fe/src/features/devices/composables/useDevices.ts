import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import { queryKeys } from '@/shared/utils'
import { devicesApi } from '../api/devices.api'

export function useDeviceList() {
  return useQuery({
    queryKey: queryKeys.devices.list(),
    queryFn: devicesApi.list,
    staleTime: 30_000,
  })
}

export function useCreateDevice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; location?: string }) => devicesApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.devices.all() })
      // raw_token is returned in result — caller shows it in dialog
    },
    onError: (e: any) => toast.error(e?.message ?? 'Tạo thiết bị thất bại'),
  })
}

export function useRevokeDevice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => devicesApi.revoke(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.devices.all() })
      toast.success('Đã thu hồi quyền truy cập thiết bị')
    },
    onError: (e: any) => toast.error(e?.message ?? 'Thu hồi thất bại'),
  })
}
