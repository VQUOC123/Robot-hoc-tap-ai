import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth.api'
import type { AdminUser, LoginCredentials } from '../types'

export const useAuthStore = defineStore('auth', () => {
  // Access token stays in memory only — never localStorage (security)
  const accessToken = ref<string | null>(null)
  const user = ref<AdminUser | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)

  async function login(credentials: LoginCredentials): Promise<void> {
    const res = await authApi.login(credentials)
    accessToken.value = res.access_token
    user.value = res.user
  }

  async function refresh(): Promise<boolean> {
    try {
      const res = await authApi.refresh()
      accessToken.value = res.access_token
      user.value = res.user
      return true
    } catch {
      accessToken.value = null
      user.value = null
      return false
    }
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } catch {
      // ignore — always clear local state
    } finally {
      accessToken.value = null
      user.value = null
    }
  }

  return { accessToken, user, isAuthenticated, login, refresh, logout }
})
