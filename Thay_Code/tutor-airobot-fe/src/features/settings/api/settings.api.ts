import { api } from '@/shared/api/client'
import type { SystemSettings } from '../types'

const BASE = '/api/v1/settings'

export const settingsApi = {
  get: () => api.get<SystemSettings>(BASE),
  update: (data: Partial<SystemSettings>) => api.put<SystemSettings>(BASE, data),
}
