import { api } from '@/shared/api/client'
import type { Provider, TestResult } from '../types'
import type { ProviderFormValues } from '../schemas/provider.schema'

const BASE = '/api/v1/providers'

export const providersApi = {
  list: () => api.get<Provider[]>(BASE),

  getById: (id: string) => api.get<Provider>(`${BASE}/${id}`),

  create: (data: ProviderFormValues) => api.post<Provider>(BASE, data),

  update: (id: string, data: Partial<ProviderFormValues>) =>
    api.put<Provider>(`${BASE}/${id}`, data),

  delete: (id: string) => api.delete(`${BASE}/${id}`),

  testConnection: (id: string) => api.post<TestResult>(`${BASE}/${id}/test`),

  setDefault: (id: string) => api.put<Provider>(`${BASE}/${id}`, { is_default: true }),
}
