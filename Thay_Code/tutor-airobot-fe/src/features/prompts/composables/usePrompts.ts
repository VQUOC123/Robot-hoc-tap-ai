import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import { queryKeys } from '@/shared/utils'
import { promptsApi } from '../api/prompts.api'
import type { PromptFormValues } from '../schemas/prompt.schema'

export function usePromptList() {
  return useQuery({
    queryKey: queryKeys.prompts.list(),
    queryFn: promptsApi.list,
    staleTime: 30_000,
  })
}

export function usePrompt(id: string) {
  return useQuery({
    queryKey: queryKeys.prompts.detail(id),
    queryFn: () => promptsApi.getById(id),
    enabled: !!id,
  })
}

export function useCreatePrompt() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: PromptFormValues) => promptsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.prompts.all() })
      toast.success('Đã tạo prompt thành công')
    },
    onError: (e: any) => toast.error(e?.message ?? 'Tạo prompt thất bại'),
  })
}

export function useUpdatePrompt() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<PromptFormValues> }) =>
      promptsApi.update(id, data),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: queryKeys.prompts.all() })
      qc.invalidateQueries({ queryKey: queryKeys.prompts.detail(id) })
      toast.success('Đã cập nhật prompt')
    },
    onError: (e: any) => toast.error(e?.message ?? 'Cập nhật thất bại'),
  })
}

export function useDeletePrompt() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => promptsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.prompts.all() })
      toast.success('Đã xóa prompt')
    },
    onError: (e: any) => toast.error(e?.message ?? 'Xóa thất bại'),
  })
}
