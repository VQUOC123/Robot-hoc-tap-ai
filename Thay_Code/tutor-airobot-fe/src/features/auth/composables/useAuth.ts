import { useMutation } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth.store'
import type { LoginCredentials } from '../types'

export function useLogin() {
  const auth = useAuthStore()
  const router = useRouter()

  return useMutation({
    mutationFn: (credentials: LoginCredentials) => auth.login(credentials),
    onSuccess: () => {
      const redirect = router.currentRoute.value.query.redirect as string | undefined
      router.push(redirect ?? '/dashboard')
    },
  })
}

export function useLogout() {
  const auth = useAuthStore()
  const router = useRouter()

  return useMutation({
    mutationFn: () => auth.logout(),
    onSuccess: () => router.push('/login'),
  })
}
