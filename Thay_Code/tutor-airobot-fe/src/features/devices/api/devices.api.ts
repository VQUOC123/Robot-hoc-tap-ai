import { api } from '@/shared/api/client'
import type { Device, CreateDeviceResult } from '../types'

const BASE = '/api/v1/devices'

export const devicesApi = {
  list: () => api.get<Device[]>(BASE),

  getById: (id: string) => api.get<Device>(`${BASE}/${id}`),

  create: (data: { name: string; location?: string }) =>
    api.post<CreateDeviceResult>(BASE, data),

  revoke: (id: string) => api.delete(`${BASE}/${id}`),
}
