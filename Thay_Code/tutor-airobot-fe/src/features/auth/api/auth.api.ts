import { api, refreshClient } from '@/shared/api/client'
import type { LoginCredentials, TokenResponse } from '../types'

export const authApi = {
  login: (credentials: LoginCredentials) =>
    api.post<TokenResponse>('/api/v1/auth/login', credentials),

  // Uses refreshClient (no interceptors) to avoid 401 retry loops
  refresh: (): Promise<TokenResponse> =>
    refreshClient
      .post('/api/v1/auth/refresh')
      .then((r) => (r.data?.data ?? r.data) as TokenResponse),

  logout: () => api.post('/api/v1/auth/logout'),
}
