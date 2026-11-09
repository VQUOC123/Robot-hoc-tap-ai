import axios, { type AxiosRequestConfig } from 'axios'
import type { ApiError } from './types'

// ─── Main client (with auth interceptors) ────────────────────────────────────
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 35_000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Refresh client (NO interceptors — avoids 401 retry loops) ───────────────
export const refreshClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 10_000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Auth hooks injected from main.ts (after Pinia init) ─────────────────────
let _getToken: (() => string | null) | null = null
let _refresh: (() => Promise<boolean>) | null = null
let _logout: (() => void) | null = null

export function setupAuthInterceptors(
  getToken: () => string | null,
  refresh: () => Promise<boolean>,
  logout: () => void,
): void {
  _getToken = getToken
  _refresh = refresh
  _logout = logout
}

// ─── Request: inject Bearer token ────────────────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = _getToken?.()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ─── Response: unwrap envelope + handle 401 ──────────────────────────────────
apiClient.interceptors.response.use(
  // Unwrap { data: T } envelope. When a `meta` field is present (cursor pagination)
  // return the full body so callers receive { data: T[], meta: {...} } intact.
  (res) => (res.data?.meta !== undefined ? res.data : (res.data?.data ?? res.data)),
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry && _refresh) {
      originalRequest._retry = true
      const ok = await _refresh()
      if (ok) {
        originalRequest.headers.Authorization = `Bearer ${_getToken?.()}`
        return apiClient(originalRequest)
      }
      _logout?.()
    }
    return Promise.reject(normalizeError(error))
  },
)

// ─── Typed helpers (resolve the interceptor unwrapping type mismatch) ─────────
export const api = {
  get: <T>(url: string, config?: AxiosRequestConfig) =>
    apiClient.get(url, config) as unknown as Promise<T>,
  post: <T = void>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    apiClient.post(url, data, config) as unknown as Promise<T>,
  put: <T = void>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    apiClient.put(url, data, config) as unknown as Promise<T>,
  patch: <T = void>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    apiClient.patch(url, data, config) as unknown as Promise<T>,
  delete: <T = void>(url: string, config?: AxiosRequestConfig) =>
    apiClient.delete(url, config) as unknown as Promise<T>,
}

function normalizeError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    return (
      error.response?.data?.error ?? {
        code: error.code ?? 'REQUEST_ERROR',
        message: error.message,
      }
    )
  }
  return { code: 'UNKNOWN', message: 'Lỗi không xác định' }
}
