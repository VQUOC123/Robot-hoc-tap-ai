import { api } from '@/shared/api/client'
import type { Prompt } from '../types'
import type { PromptFormValues } from '../schemas/prompt.schema'

const BASE = '/api/v1/prompts'

export const promptsApi = {
  list: () => api.get<Prompt[]>(BASE),

  getById: (id: string) => api.get<Prompt>(`${BASE}/${id}`),

  create: (data: PromptFormValues) => api.post<Prompt>(BASE, data),

  update: (id: string, data: Partial<PromptFormValues>) =>
    api.put<Prompt>(`${BASE}/${id}`, data),

  delete: (id: string) => api.delete(`${BASE}/${id}`),

  setDefault: (id: string) => api.post(`${BASE}/${id}/default`),
}
