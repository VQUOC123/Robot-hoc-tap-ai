import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { useAuthStore } from '@/features/auth/store/auth.store'

export async function authGuard(
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext,
): Promise<void> {
  // Public routes (login page)
  if (to.meta.public) return next()

  const auth = useAuthStore()

  // Already authenticated
  if (auth.isAuthenticated) return next()

  // Try silent refresh via httpOnly cookie
  const ok = await auth.refresh()
  if (ok) return next()

  // No valid session — redirect to login
  next({ name: 'login', query: { redirect: to.fullPath } })
}
