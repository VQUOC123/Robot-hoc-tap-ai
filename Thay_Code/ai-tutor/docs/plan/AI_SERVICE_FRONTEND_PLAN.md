# Tutor Admin Frontend — Vue 3 + Vite 6 + shadcn-vue

**Stack:** Vue 3.5 · TypeScript 5 · Vite 6 · shadcn-vue · Pinia · TanStack Query · TanStack Table
**Repo:** `tutor-admin/` (project độc lập, deploy riêng)
**Domain:** `https://admin.tutor.your-domain.com`

> **Lý do chọn Vue 3:** Đồng nhất với project Vue 3 + Vite 6 khác của team.
> Có thể chia sẻ design system, utils, conventions.
> shadcn-vue (shadcn-vue.com) là Vue port chính thức của shadcn/ui — component set tương đương.

---

## 1. Kiến trúc tổng quan

**Feature-based architecture** — không flat layer-by-type.
Mỗi feature tự chứa API calls, composables, components, types riêng.

```
src/
├── app/           # App-level: router, plugins, global layout
├── features/      # Business features — mỗi feature tự đủ
│   ├── auth/
│   ├── dashboard/
│   ├── providers/
│   ├── prompts/
│   ├── analyses/
│   ├── devices/
│   └── settings/
└── shared/        # Code dùng ở ≥2 features
    ├── api/       # Axios instance, interceptors, base types
    ├── components/ # Layout, DataTable wrapper, feedback states
    ├── composables/ # Generic composables (usePagination, useDebounce,...)
    └── utils/     # Pure functions (format, cn, validators)
```

**Nguyên tắc:**
- **KISS:** Composable gọi trực tiếp API — không thêm abstraction layer không cần thiết
- **DRY:** Shared chỉ chứa code dùng thật sự ở nhiều feature; không pre-abstract
- **Colocation:** API, composable, component của 1 feature nằm cùng thư mục
- **Single source of truth:** Server state qua TanStack Query, UI state qua Pinia (tối giản)

---

## 2. Tech Stack chi tiết

| Thư viện | Version | Mục đích | Lý do |
|---|---|---|---|
| **Vue** | 3.5 | UI framework | Composition API sạch, Vapor Mode (2025) |
| **TypeScript** | 5.5+ | Type safety | Generic composables, type-safe API |
| **Vite** | 6 | Build tool | Cùng version project khác, HMR <100ms |
| **shadcn-vue** | latest | UI components | Vue port của shadcn/ui — copy vào project, Tailwind-based |
| **Vue Router** | 4 | Routing | Chính thức, navigation guards cho auth |
| **Pinia** | 2 | State management | Chính thức Vue, đơn giản hơn Vuex |
| **@tanstack/vue-query** | v5 | Server state | Cache, background refetch, loading states |
| **@tanstack/vue-table** | v8 | Data tables | Headless, performant, flexible |
| **VeeValidate** | v4 | Form validation | Native Vue integration |
| **Zod** | v3 | Schema validation | Dùng chung với VeeValidate |
| **Axios** | v1 | HTTP client | Interceptors, cancel, cùng pattern project khác |
| **VueUse** | v11 | Utility composables | 200+ composables, tránh viết lại |
| **vue-chartjs** | v5 | Charts | Chart.js wrapper cho Vue, đủ cho dashboard |
| **Tailwind CSS** | v4 | Styling | Cùng config project khác → share preset |
| **date-fns** | v3 | Date format | Tree-shakeable, không cần moment.js |

---

## 3. Cấu trúc thư mục chi tiết

```
tutor-admin/
│
├── src/
│   │
│   ├── app/
│   │   ├── main.ts                    # createApp + plugins mount
│   │   ├── plugins/
│   │   │   ├── query.ts               # QueryClient setup (TanStack Query)
│   │   │   ├── router.ts              # Vue Router instance
│   │   │   └── pinia.ts               # Pinia instance
│   │   └── globals.css                # Tailwind directives + shadcn-vue CSS vars
│   │
│   ├── router/
│   │   ├── index.ts                   # Route definitions + navigation guards
│   │   └── guards/
│   │       └── auth.guard.ts          # Redirect /login nếu chưa auth
│   │
│   ├── features/
│   │   │
│   │   ├── auth/
│   │   │   ├── api/
│   │   │   │   └── auth.api.ts        # login(), refresh(), logout()
│   │   │   ├── composables/
│   │   │   │   └── useAuth.ts         # useLogin(), useLogout()
│   │   │   ├── components/
│   │   │   │   └── LoginForm.vue
│   │   │   ├── store/
│   │   │   │   └── auth.store.ts      # Pinia: accessToken, user, isAuthenticated
│   │   │   └── types.ts
│   │   │
│   │   ├── dashboard/
│   │   │   ├── api/
│   │   │   │   └── stats.api.ts       # getOverview(), getLatencyStats()
│   │   │   ├── composables/
│   │   │   │   └── useStats.ts        # useOverviewStats(), useLatencyStats()
│   │   │   └── components/
│   │   │       ├── StatsCards.vue     # 4 KPI cards
│   │   │       ├── SubjectChart.vue   # vue-chartjs Pie
│   │   │       ├── LatencyChart.vue   # vue-chartjs Bar
│   │   │       └── RecentAnalyses.vue # Mini table 10 rows
│   │   │
│   │   ├── providers/
│   │   │   ├── api/
│   │   │   │   └── providers.api.ts   # CRUD + testConnection()
│   │   │   ├── composables/
│   │   │   │   ├── useProviders.ts    # useProviderList(), useProvider()
│   │   │   │   └── useProviderMutation.ts # useCreateProvider(), ...
│   │   │   ├── components/
│   │   │   │   ├── ProviderTable.vue
│   │   │   │   ├── ProviderForm.vue   # VeeValidate + Zod schema
│   │   │   │   └── TestConnectionBtn.vue
│   │   │   ├── schemas/
│   │   │   │   └── provider.schema.ts # Zod schema
│   │   │   └── types.ts
│   │   │
│   │   ├── prompts/
│   │   │   ├── api/
│   │   │   │   └── prompts.api.ts
│   │   │   ├── composables/
│   │   │   │   └── usePrompts.ts
│   │   │   ├── components/
│   │   │   │   ├── PromptTable.vue
│   │   │   │   ├── PromptForm.vue     # Textarea lớn, monospace
│   │   │   │   └── PromptPreview.vue  # Preview JSON schema output
│   │   │   ├── schemas/
│   │   │   │   └── prompt.schema.ts
│   │   │   └── types.ts
│   │   │
│   │   ├── analyses/
│   │   │   ├── api/
│   │   │   │   └── analyses.api.ts    # list() cursor pagination, getById()
│   │   │   ├── composables/
│   │   │   │   ├── useAnalyses.ts     # useInfiniteQuery cursor pagination
│   │   │   │   └── useAnalysis.ts
│   │   │   ├── components/
│   │   │   │   ├── AnalysisTable.vue
│   │   │   │   ├── AnalysisFilters.vue # date range, subject, device, doing_hw
│   │   │   │   └── AnalysisDetail.vue  # Drawer: full data + thumbnail
│   │   │   └── types.ts
│   │   │
│   │   ├── devices/
│   │   │   ├── api/
│   │   │   │   └── devices.api.ts
│   │   │   ├── composables/
│   │   │   │   └── useDevices.ts
│   │   │   ├── components/
│   │   │   │   ├── DeviceTable.vue
│   │   │   │   ├── CreateDeviceDialog.vue # Raw token hiển thị 1 lần
│   │   │   │   └── RevokeDeviceDialog.vue
│   │   │   └── types.ts
│   │   │
│   │   └── settings/
│   │       ├── api/
│   │       │   └── settings.api.ts
│   │       ├── composables/
│   │       │   └── useSettings.ts
│   │       └── components/
│   │           └── SettingsForm.vue
│   │
│   ├── shared/
│   │   │
│   │   ├── api/
│   │   │   ├── client.ts              # Axios instance: baseURL, interceptors
│   │   │   ├── interceptors/
│   │   │   │   ├── auth.interceptor.ts    # Inject Bearer token
│   │   │   │   └── refresh.interceptor.ts # 401 → refresh → retry
│   │   │   └── types.ts               # ApiResponse<T>, PaginatedResponse<T>, CursorMeta
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn-vue components (DO NOT EDIT manually)
│   │   │   │   ├── button/
│   │   │   │   ├── input/
│   │   │   │   ├── dialog/
│   │   │   │   ├── table/
│   │   │   │   ├── badge/
│   │   │   │   ├── card/
│   │   │   │   ├── form/
│   │   │   │   ├── select/
│   │   │   │   ├── toast/
│   │   │   │   └── ...
│   │   │   ├── layout/
│   │   │   │   ├── AppLayout.vue      # Sidebar + main
│   │   │   │   ├── Sidebar.vue        # Nav links, active state
│   │   │   │   ├── Header.vue         # Page title + user menu
│   │   │   │   └── PageContainer.vue  # Max-width wrapper
│   │   │   ├── data-table/
│   │   │   │   ├── DataTable.vue      # TanStack Table wrapper — dùng cho mọi table
│   │   │   │   ├── DataTablePagination.vue  # Load more (cursor)
│   │   │   │   ├── DataTableToolbar.vue     # Slot cho filter bar
│   │   │   │   └── DataTableColumnHeader.vue # Sortable header
│   │   │   └── feedback/
│   │   │       ├── LoadingSpinner.vue
│   │   │       ├── ErrorState.vue     # Error + retry
│   │   │       └── EmptyState.vue
│   │   │
│   │   ├── composables/
│   │   │   ├── useDebounce.ts         # VueUse: useDebounce wrapper
│   │   │   ├── useCopyToClipboard.ts  # VueUse: useClipboard wrapper
│   │   │   └── useConfirm.ts          # Reusable confirm dialog composable
│   │   │
│   │   └── utils/
│   │       ├── cn.ts                  # clsx + tailwind-merge (shadcn-vue convention)
│   │       ├── format.ts              # formatDate, formatMs, formatSubject, truncate
│   │       └── query-keys.ts          # Centralized TanStack Query key factory
│   │
│   └── views/                         # Route-level components (thin wrappers)
│       ├── LoginView.vue
│       ├── DashboardView.vue
│       ├── providers/
│       │   ├── ProvidersView.vue      # List
│       │   └── ProviderDetailView.vue # Create / Edit
│       ├── prompts/
│       │   ├── PromptsView.vue
│       │   └── PromptDetailView.vue
│       ├── AnalysesView.vue
│       ├── DevicesView.vue
│       └── SettingsView.vue
│
├── scripts/
│   ├── dev.sh
│   └── build.sh
│
├── public/
│   └── favicon.ico
│
├── .env.development
├── .env.production
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── components.json                    # shadcn-vue config
└── package.json
```

---

## 4. Shared API Client

```typescript
// shared/api/client.ts
import axios from 'axios'
import { useAuthStore } from '@/features/auth/store/auth.store'

export const apiClient = axios.create({
    baseURL : import.meta.env.VITE_API_URL,
    timeout : 35_000,
    headers : { 'Content-Type': 'application/json' },
})

// Request: inject token
apiClient.interceptors.request.use((config) => {
    const token = useAuthStore().accessToken
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
})

// Response: unwrap envelope + handle 401
apiClient.interceptors.response.use(
    (res) => res.data.data,           // unwrap {data: ...} tự động
    async (error) => {
        if (error.response?.status === 401) {
            const auth = useAuthStore()
            const ok = await auth.refresh()
            if (ok) return apiClient(error.config)   // retry
            auth.logout()
        }
        return Promise.reject(normalizeError(error))
    }
)

function normalizeError(error: unknown): ApiError {
    if (axios.isAxiosError(error)) {
        return error.response?.data?.error ?? { code: 'NETWORK_ERROR', message: error.message }
    }
    return { code: 'UNKNOWN', message: 'Lỗi không xác định' }
}
```

---

## 5. Query Key Factory (DRY)

```typescript
// shared/utils/query-keys.ts
export const queryKeys = {
    providers: {
        all:    ()             => ['providers'] as const,
        list:   (p?: object)  => ['providers', 'list', p] as const,
        detail: (id: string)  => ['providers', 'detail', id] as const,
    },
    prompts: {
        all:    ()             => ['prompts'] as const,
        list:   (p?: object)  => ['prompts', 'list', p] as const,
        detail: (id: string)  => ['prompts', 'detail', id] as const,
    },
    analyses: {
        all:      ()              => ['analyses'] as const,
        infinite: (f: object)    => ['analyses', 'infinite', f] as const,
        detail:   (id: string)   => ['analyses', 'detail', id] as const,
    },
    stats: {
        overview: () => ['stats', 'overview'] as const,
        latency:  () => ['stats', 'latency']  as const,
    },
} as const
```

---

## 6. Feature mẫu: Providers

```typescript
// features/providers/schemas/provider.schema.ts
import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'

export const providerSchema = z.object({
    name        : z.string().min(1).max(100),
    base_url    : z.string().url('URL không hợp lệ'),
    api_key     : z.string().min(10, 'API key quá ngắn'),
    model       : z.string().min(1),
    timeout_sec : z.number().int().min(5).max(120).default(30),
    is_default  : z.boolean().default(false),
})
export const providerVeeSchema = toTypedSchema(providerSchema)
export type ProviderFormValues = z.infer<typeof providerSchema>

// features/providers/api/providers.api.ts
import { apiClient } from '@/shared/api/client'
import type { Provider, TestResult } from '../types'

export const providersApi = {
    list:            ()                            => apiClient.get<Provider[]>('/api/v1/providers'),
    getById:         (id: string)                  => apiClient.get<Provider>(`/api/v1/providers/${id}`),
    create:          (data: ProviderFormValues)    => apiClient.post<Provider>('/api/v1/providers', data),
    update:          (id: string, data: Partial<ProviderFormValues>) =>
                         apiClient.put<Provider>(`/api/v1/providers/${id}`, data),
    delete:          (id: string)                  => apiClient.delete(`/api/v1/providers/${id}`),
    testConnection:  (id: string)                  => apiClient.post<TestResult>(`/api/v1/providers/${id}/test`),
    setDefault:      (id: string)                  => apiClient.post(`/api/v1/providers/${id}/default`),
}

// features/providers/composables/useProviders.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { queryKeys } from '@/shared/utils/query-keys'
import { providersApi } from '../api/providers.api'

export function useProviderList() {
    return useQuery({
        queryKey  : queryKeys.providers.list(),
        queryFn   : providersApi.list,
        staleTime : 30_000,
    })
}

export function useDeleteProvider() {
    const qc = useQueryClient()
    return useMutation({
        mutationFn : providersApi.delete,
        onSuccess  : () => qc.invalidateQueries({ queryKey: queryKeys.providers.all() }),
    })
}
```

---

## 7. Pinia Auth Store

```typescript
// features/auth/store/auth.store.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth.api'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
    // State — access token chỉ trong memory (không localStorage)
    const accessToken = ref<string | null>(null)
    const user        = ref<AdminUser | null>(null)

    // Getters
    const isAuthenticated = computed(() => !!accessToken.value)

    // Actions
    async function login(email: string, password: string) {
        const res = await authApi.login({ email, password })
        accessToken.value = res.access_token
        user.value        = res.user
        router.push('/dashboard')
    }

    async function refresh(): Promise<boolean> {
        try {
            const res = await authApi.refresh()   // cookie refresh token tự gửi
            accessToken.value = res.access_token
            return true
        } catch {
            accessToken.value = null
            return false
        }
    }

    async function logout() {
        try { await authApi.logout() } catch {}
        accessToken.value = null
        user.value        = null
        router.push('/login')
    }

    return { accessToken, user, isAuthenticated, login, refresh, logout }
})
```

---

## 8. DataTable wrapper (DRY cho tất cả tables)

```vue
<!-- shared/components/data-table/DataTable.vue -->
<script setup lang="ts" generic="TData">
import {
    useVueTable, getCoreRowModel, getSortedRowModel,
    type ColumnDef, type SortingState,
} from '@tanstack/vue-table'
import { ref } from 'vue'

interface Props {
    columns   : ColumnDef<TData>[]
    data      : TData[]
    isLoading?: boolean
    toolbar?  : boolean        // slot
    hasMore?  : boolean
    onLoadMore?: () => void
}
const props = defineProps<Props>()

const sorting = ref<SortingState>([])
const table = useVueTable({
    get data()    { return props.data },
    get columns() { return props.columns },
    state         : { get sorting() { return sorting.value } },
    onSortingChange: (updater) => {
        sorting.value = typeof updater === 'function' ? updater(sorting.value) : updater
    },
    getCoreRowModel:   getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
})
</script>

<template>
  <div class="space-y-4">
    <slot name="toolbar" />
    <div v-if="isLoading"><LoadingSpinner /></div>
    <template v-else>
      <div class="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow v-for="hg in table.getHeaderGroups()" :key="hg.id">
              <DataTableColumnHeader
                v-for="header in hg.headers"
                :key="header.id"
                :header="header"
              />
            </TableRow>
          </TableHeader>
          <TableBody>
            <template v-if="table.getRowModel().rows.length">
              <TableRow v-for="row in table.getRowModel().rows" :key="row.id">
                <TableCell v-for="cell in row.getVisibleCells()" :key="cell.id">
                  <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
                </TableCell>
              </TableRow>
            </template>
            <TableRow v-else>
              <TableCell :colspan="columns.length"><EmptyState /></TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
      <div v-if="hasMore" class="flex justify-center">
        <Button variant="outline" @click="onLoadMore">Load thêm</Button>
      </div>
    </template>
  </div>
</template>
```

---

## 9. Router + Auth Guard

```typescript
// router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { authGuard } from './guards/auth.guard'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: '/login', component: () => import('@/views/LoginView.vue') },
        {
            path: '/',
            component: () => import('@/shared/components/layout/AppLayout.vue'),
            meta: { requiresAuth: true },
            children: [
                { path: '',          redirect: '/dashboard' },
                { path: 'dashboard', component: () => import('@/views/DashboardView.vue') },
                { path: 'providers', component: () => import('@/views/providers/ProvidersView.vue') },
                { path: 'providers/new',  component: () => import('@/views/providers/ProviderDetailView.vue') },
                { path: 'providers/:id',  component: () => import('@/views/providers/ProviderDetailView.vue') },
                { path: 'prompts',        component: () => import('@/views/prompts/PromptsView.vue') },
                { path: 'prompts/new',    component: () => import('@/views/prompts/PromptDetailView.vue') },
                { path: 'prompts/:id',    component: () => import('@/views/prompts/PromptDetailView.vue') },
                { path: 'analyses',       component: () => import('@/views/AnalysesView.vue') },
                { path: 'analyses/:id',   component: () => import('@/views/AnalysesView.vue') },
                { path: 'devices',        component: () => import('@/views/DevicesView.vue') },
                { path: 'settings',       component: () => import('@/views/SettingsView.vue') },
            ]
        },
    ]
})

router.beforeEach(authGuard)
export default router

// router/guards/auth.guard.ts
import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { useAuthStore } from '@/features/auth/store/auth.store'

export async function authGuard(
    to: RouteLocationNormalized,
    _: RouteLocationNormalized,
    next: NavigationGuardNext
) {
    if (!to.meta.requiresAuth) return next()

    const auth = useAuthStore()
    if (auth.isAuthenticated) return next()

    // Thử refresh (cookie còn hiệu lực)
    const ok = await auth.refresh()
    ok ? next() : next('/login')
}
```

---

## 10. vite.config.ts

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: { '@': path.resolve(__dirname, './src') }
    },
    server: {
        port: 5173,
        proxy: {
            // Proxy trong dev → tránh CORS
            '/api': {
                target     : process.env.VITE_API_URL || 'http://localhost:8080',
                changeOrigin: true,
            }
        }
    },
    build: {
        rollupOptions: {
            output: {
                manualChunks: {
                    vue     : ['vue', 'vue-router', 'pinia'],
                    tanstack: ['@tanstack/vue-query', '@tanstack/vue-table'],
                    charts  : ['vue-chartjs', 'chart.js'],
                    vueuse  : ['@vueuse/core'],
                }
            }
        }
    }
})
```

---

## 11. Dev Scripts

### `scripts/dev.sh`
```bash
#!/usr/bin/env bash
set -e

if [ ! -f .env.development ]; then
    cp .env.development.example .env.development
    echo "⚠️  Điền VITE_API_URL vào .env.development"
    exit 1
fi

echo "📦 Installing dependencies..."
npm install

echo "🔧 Installing shadcn-vue components (first time)..."
if [ ! -d "src/shared/components/ui/button" ]; then
    npx shadcn-vue@latest add button input form label select textarea \
        table badge card dialog drawer toast dropdown-menu separator \
        skeleton alert-dialog tooltip
fi

echo "🚀 Starting dev server..."
npm run dev
```

### `.env.development.example`
```bash
VITE_API_URL=http://localhost:8080
VITE_APP_TITLE=Tutor Admin (Dev)
```

### `.env.production`
```bash
VITE_API_URL=https://api.tutor.your-domain.com
VITE_APP_TITLE=Tutor Admin
```

### `package.json` scripts
```json
{
  "scripts": {
    "dev"      : "vite",
    "build"    : "vue-tsc -b && vite build",
    "preview"  : "vite preview",
    "lint"     : "eslint src --ext .ts,.vue",
    "typecheck": "vue-tsc --noEmit",
    "format"   : "prettier --write src/"
  }
}
```

---

## 12. shadcn-vue Setup

```bash
# Khởi tạo shadcn-vue
npx shadcn-vue@latest init

# Cài components (tự động copy vào src/shared/components/ui/)
npx shadcn-vue@latest add button input form label select textarea
npx shadcn-vue@latest add table badge card dialog drawer toast
npx shadcn-vue@latest add dropdown-menu separator skeleton
npx shadcn-vue@latest add alert-dialog tooltip
```

Components được copy vào project — **không phải npm package**.
Sửa được thoải mái, không bị breaking changes từ upstream.

---

## 13. Deploy

```bash
# Build → dist/ (HTML + CSS + JS thuần, không cần Node.js runtime)
npm run build

# Option A: Nginx riêng (Docker container)
FROM nginx:alpine
COPY dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf
# nginx.conf: try_files $uri /index.html (SPA fallback)

# Option B: Vercel (push git = auto deploy)
# vercel.json:
# { "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }

# Option C: Netlify
# _redirects: /*  /index.html  200
```

**Deploy hoàn toàn tách khỏi backend Go** — chỉ là static files.

---

## 14. Thứ tự implement

```
Phase 1 — Foundation
[ ] npm create vue@latest + TypeScript + Vite 6
[ ] Tailwind v4 + shadcn-vue init + theme
[ ] Vue Router 4 setup + auth guard
[ ] Pinia setup + persist plugin
[ ] TanStack Query setup (VueQueryPlugin)
[ ] Axios client + interceptors
[ ] shared/utils/cn, format, query-keys
[ ] shared/components/layout (AppLayout, Sidebar, Header)
[ ] shared/components/data-table (DataTable.vue wrapper)
[ ] shared/components/feedback (Loading, Error, Empty)

Phase 2 — Auth
[ ] features/auth: LoginForm.vue, auth.store.ts, auth.api.ts
[ ] Router auth guard (refresh token on page reload)
[ ] 401 interceptor + retry logic

Phase 3 — Core Features
[ ] features/providers: API, composables, table, form, test button
[ ] features/prompts: API, composables, table, form, preview
[ ] features/devices: API, composables, table, create dialog (token 1 lần)
[ ] features/settings: API, composables, form

Phase 4 — Analyses + Dashboard
[ ] features/analyses: infinite scroll, filters, detail drawer
[ ] features/dashboard: stats cards + charts

Phase 5 — Polish
[ ] Error boundaries (onErrorCaptured)
[ ] Toast notifications (Sonner hoặc shadcn-vue toast)
[ ] Keyboard shortcuts (VueUse useMagicKeys)
[ ] Dark mode toggle (VueUse useColorMode)
[ ] Responsive sidebar (useBreakpoints từ VueUse)
```

---

## 15. Tận dụng VueUse (tránh viết lại)

```typescript
// Dùng VueUse thay vì tự implement:
import { useClipboard }    from '@vueuse/core'  // useCopyToClipboard
import { useDebounce }     from '@vueuse/core'  // search input debounce
import { useColorMode }    from '@vueuse/core'  // dark/light mode
import { useBreakpoints }  from '@vueuse/core'  // responsive sidebar
import { useMagicKeys }    from '@vueuse/core'  // keyboard shortcuts
import { useLocalStorage } from '@vueuse/core'  // persist theme preference
import { useTimeAgo }      from '@vueuse/core'  // "2 phút trước" format
import { useElementSize }  from '@vueuse/core'  // responsive table columns
```
