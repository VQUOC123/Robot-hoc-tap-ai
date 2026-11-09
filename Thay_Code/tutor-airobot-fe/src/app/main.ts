import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import router from '@/router'
import App from '@/App.vue'
import { vueQueryPluginOptions } from '@/app/plugins/query'
import { setupAuthInterceptors } from '@/shared/api/client'
import { useAuthStore } from '@/features/auth/store/auth.store'
import './globals.css'

const pinia = createPinia()
const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(VueQueryPlugin, vueQueryPluginOptions)

// Wire up auth interceptors after Pinia is initialized
const auth = useAuthStore(pinia)
setupAuthInterceptors(
  () => auth.accessToken,
  () => auth.refresh(),
  () => { auth.logout() },
)

app.mount('#app')
