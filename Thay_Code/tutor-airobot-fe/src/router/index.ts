import { createRouter, createWebHistory } from 'vue-router'
import { authGuard } from './guards/auth.guard'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: 'Đăng nhập', public: true },
    },
    {
      path: '/',
      component: () => import('@/shared/components/layout/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/dashboard' },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: 'Dashboard' },
        },
        {
          path: 'providers',
          name: 'providers',
          component: () => import('@/views/providers/ProvidersView.vue'),
          meta: { title: 'AI Providers' },
        },
        {
          path: 'providers/new',
          name: 'provider-new',
          component: () => import('@/views/providers/ProviderDetailView.vue'),
          meta: { title: 'Thêm Provider' },
        },
        {
          path: 'providers/:id',
          name: 'provider-edit',
          component: () => import('@/views/providers/ProviderDetailView.vue'),
          meta: { title: 'Chỉnh sửa Provider' },
        },
        {
          path: 'prompts',
          name: 'prompts',
          component: () => import('@/views/prompts/PromptsView.vue'),
          meta: { title: 'Prompts' },
        },
        {
          path: 'prompts/new',
          name: 'prompt-new',
          component: () => import('@/views/prompts/PromptDetailView.vue'),
          meta: { title: 'Thêm Prompt' },
        },
        {
          path: 'prompts/:id',
          name: 'prompt-edit',
          component: () => import('@/views/prompts/PromptDetailView.vue'),
          meta: { title: 'Chỉnh sửa Prompt' },
        },
        {
          path: 'analyses',
          name: 'analyses',
          component: () => import('@/views/AnalysesView.vue'),
          meta: { title: 'Lịch sử phân tích' },
        },
        {
          path: 'devices',
          name: 'devices',
          component: () => import('@/views/DevicesView.vue'),
          meta: { title: 'Thiết bị' },
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue'),
          meta: { title: 'Cài đặt' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach(authGuard)

export default router
