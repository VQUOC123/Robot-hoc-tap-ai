# Tutor Admin Frontend — CLAUDE.md

## Project Context
Admin dashboard for **Tutor AI Robot** system:
- **Client** (`/home/pi/ai-tutor`): Raspberry Pi camera — tracks students, detects homework activity
- **Backend** (`tutor-airobot-be`): Go service — receives image from client, calls AI to analyze student activity
- **This repo** (`tutor-airobot-fe`): Vue 3 admin UI — manage AI providers, prompts, devices, view analyses

## Git Rules (CRITICAL)
- **NEVER** commit, push, revert, or any git operation — user handles all git actions

---

## Tech Stack (use exact versions)

| Package | Version | Purpose |
|---|---|---|
| Vue | 3.5 | UI framework (Composition API) |
| TypeScript | 5.5+ | Type safety |
| Vite | 6 | Build tool |
| shadcn-vue | latest | UI components (copied into project) |
| Vue Router | 4 | Routing + auth guards |
| Pinia | 2 | UI state only (auth token, sidebar) |
| @tanstack/vue-query | v5 | Server state: cache, loading, refetch |
| @tanstack/vue-table | v8 | Headless data tables |
| VeeValidate | v4 | Form validation |
| Zod | v3 | Schema validation (paired with VeeValidate) |
| Axios | v1 | HTTP client with interceptors |
| VueUse | v11 | Utility composables — use before writing custom |
| vue-chartjs | v5 | Charts (Chart.js wrapper) |
| Tailwind CSS | v4 | Styling |
| date-fns | v3 | Date formatting (tree-shakeable) |

**Package safety**: Only use well-known, widely-maintained packages. Avoid obscure packages with low download counts.

---

## Architecture: Feature-Based

```
src/
├── app/              # main.ts, plugins (query/router/pinia)
├── router/           # index.ts + guards/auth.guard.ts
├── features/         # Business features — each self-contained
│   ├── auth/         # api/, composables/, components/, store/, types.ts
│   ├── dashboard/
│   ├── providers/    # + schemas/
│   ├── prompts/      # + schemas/
│   ├── analyses/
│   ├── devices/
│   └── settings/
├── shared/           # Code used by ≥2 features ONLY
│   ├── api/          # Axios client, interceptors, base types
│   ├── components/
│   │   ├── ui/       # shadcn-vue (DO NOT edit manually)
│   │   ├── layout/   # AppLayout, Sidebar, Header, PageContainer
│   │   ├── data-table/ # DataTable, Pagination, Toolbar, ColumnHeader
│   │   └── feedback/ # LoadingSpinner, ErrorState, EmptyState
│   ├── composables/  # Generic: useDebounce, useCopyToClipboard, useConfirm
│   └── utils/        # Pure functions: cn.ts, format.ts, query-keys.ts
└── views/            # Route-level thin wrappers only
```

---

## Core Principles

### SOLID
- **SRP**: One component/composable = one responsibility
- **OCP**: Extend via props/slots, not by modifying shared components
- **DIP**: Features depend on `shared/api/client`, never on each other

### DRY
- Use `shared/utils/query-keys.ts` (centralized key factory) — never inline query keys
- Use `shared/components/data-table/DataTable.vue` — never write raw TanStack Table per feature
- Use `shared/utils/format.ts` — never inline date/duration formatting
- Prefer VueUse composables over custom implementations

### KISS
- Composable calls API directly — no extra service/repository layer
- Pinia only for global UI state (auth token, sidebar open). All server state via TanStack Query
- No premature abstraction — shared/ only for code actually reused

### YAGNI
- Don't add config flags for hypothetical scenarios
- Don't create helpers for one-time use
- Don't add error handling for impossible cases

---

## Patterns

### Feature API module (object pattern)
```typescript
// features/providers/api/providers.api.ts
export const providersApi = {
  list:   ()              => apiClient.get<Provider[]>('/api/v1/providers'),
  getById:(id: string)    => apiClient.get<Provider>(`/api/v1/providers/${id}`),
  create: (data: Dto)     => apiClient.post<Provider>('/api/v1/providers', data),
  update: (id, data)      => apiClient.put<Provider>(`/api/v1/providers/${id}`, data),
  delete: (id: string)    => apiClient.delete(`/api/v1/providers/${id}`),
}
```

### Composable (TanStack Query)
```typescript
// features/providers/composables/useProviders.ts
export function useProviderList() {
  return useQuery({ queryKey: queryKeys.providers.list(), queryFn: providersApi.list, staleTime: 30_000 })
}
export function useDeleteProvider() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: providersApi.delete, onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.providers.all() }) })
}
```

### Zod schema + VeeValidate
```typescript
// features/providers/schemas/provider.schema.ts
export const providerSchema = z.object({ name: z.string().min(1).max(100), ... })
export const providerVeeSchema = toTypedSchema(providerSchema)
export type ProviderFormValues = z.infer<typeof providerSchema>
```

### Auth store (Pinia — token in memory only, NO localStorage)
```typescript
export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const isAuthenticated = computed(() => !!accessToken.value)
  // refresh() via httpOnly cookie
})
```

### Query Key Factory (centralized)
```typescript
// shared/utils/query-keys.ts
export const queryKeys = {
  providers: { all: () => ['providers'] as const, list: (p?) => ['providers','list',p] as const, detail: (id) => [...] },
  ...
}
```

---

## Shared Component Rules

### DataTable.vue
- **Always** use for tabular data — never write raw TanStack Table in a feature
- Accepts: `columns`, `data`, `isLoading`, `hasMore`, `onLoadMore`, toolbar slot

### shadcn-vue (`shared/components/ui/`)
- Components are copied into project — modifiable if needed
- Install via `npx shadcn-vue@latest add <component>`
- Available: Button, Input, Dialog, Table, Badge, Card, Form, Select, Toast, Drawer, Tooltip, Separator, Skeleton, AlertDialog, DropdownMenu

### VueUse — use before writing custom composables
```typescript
useClipboard()      // copy to clipboard
useDebounce()       // debounced ref
useColorMode()      // dark/light mode
useBreakpoints()    // responsive layout
useMagicKeys()      // keyboard shortcuts
useLocalStorage()   // persist preferences
useTimeAgo()        // relative time format
```

---

## Code Style

- **TypeScript strict mode** — no `any`, prefer explicit types for API responses
- **`<script setup lang="ts">`** — always, for all components
- **Props**: use `defineProps<Props>()` with interface, not runtime declaration
- **Emit**: use `defineEmits<{ ... }>()` typed form
- **Constants**: `UPPER_SNAKE_CASE` in `shared/utils/` or feature-level `constants.ts`
- **No magic strings**: route paths, query key strings, API endpoints — always from constants/factories
- **Formatting**: 2-space indent, single quotes, no semicolons (Prettier default)

---

## API Response Convention (matches BE)
```typescript
// Success: { data: T }  — interceptor auto-unwraps to T
// Error:   { error: { code: string, message: string } }
// Paginated: { data: T[], meta: { total, page, limit } }
// Cursor:    { data: T[], meta: { next_cursor, has_more } }
```

---

## Environment
```bash
# .env.development
VITE_API_URL=http://localhost:8080
VITE_APP_TITLE=Tutor Admin (Dev)

# .env.production
VITE_API_URL=https://api.your-domain.com
VITE_APP_TITLE=Tutor Admin
```

---

## Implementation Order
1. **Phase 1 — Foundation**: Vite + TS + Tailwind + shadcn-vue, Router, Pinia, TanStack Query, Axios client, shared layout + DataTable + feedback components
2. **Phase 2 — Auth**: LoginForm, auth store, auth guard, 401 refresh flow
3. **Phase 3 — Core Features**: providers → prompts → devices → settings
4. **Phase 4 — Analyses + Dashboard**: infinite scroll table, filters, detail drawer, stats cards + charts
5. **Phase 5 — Polish**: error boundaries, toast, dark mode, responsive sidebar

---

## Backend API Base URL
Backend (`tutor-airobot-be`) runs at `http://localhost:8080` (dev). Routes under `/api/v1/`.
Clean Architecture: `interfaces/http` → `application` → `domain` → `infrastructure`.
