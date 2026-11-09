import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import { queryKeys } from '@/shared/utils'
import { providersApi } from '../api/providers.api'
import type { ProviderFormValues } from '../schemas/provider.schema'

export function useProviderList() {
  return useQuery({
    queryKey: queryKeys.providers.list(),
    queryFn: providersApi.list,
    staleTime: 30_000,
  })
}

export function useProvider(id: string) {
  return useQuery({
    queryKey: queryKeys.providers.detail(id),
    queryFn: () => providersApi.getById(id),
    enabled: !!id,
  })
}

export function useCreateProvider() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ProviderFormValues) => providersApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.providers.all() })
      toast.success('Đã tạo provider thành công')
    },
    onError: (e: any) => toast.error(e?.message ?? 'Tạo provider thất bại'),
  })
}

export function useUpdateProvider() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ProviderFormValues> }) =>
      providersApi.update(id, data),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: queryKeys.providers.all() })
      qc.invalidateQueries({ queryKey: queryKeys.providers.detail(id) })
      toast.success('Đã cập nhật provider')
    },
    onError: (e: any) => toast.error(e?.message ?? 'Cập nhật thất bại'),
  })
}

export function useDeleteProvider() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => providersApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.providers.all() })
      toast.success('Đã xóa provider')
    },
    onError: (e: any) => toast.error(e?.message ?? 'Xóa thất bại'),
  })
}

export function useTestConnection() {
  return useMutation({
    mutationFn: (id: string) => providersApi.testConnection(id),
    onSuccess: (result) => {
      if (result.success) {
        toast.success(`Kết nối thành công (${result.latency_ms}ms)`)
      } else {
        toast.error(`Kết nối thất bại: ${result.error}`)
      }
    },
    onError: (e: any) => toast.error(e?.message ?? 'Test kết nối thất bại'),
  })
}

export function useSetDefaultProvider() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => providersApi.setDefault(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.providers.all() })
      toast.success('Đã đặt làm provider mặc định')
    },
    onError: (e: any) => toast.error(e?.message ?? 'Thao tác thất bại'),
  })
}
