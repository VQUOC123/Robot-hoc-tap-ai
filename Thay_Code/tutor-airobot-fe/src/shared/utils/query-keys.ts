export const queryKeys = {
  providers: {
    all: () => ['providers'] as const,
    list: (p?: object) => ['providers', 'list', p] as const,
    detail: (id: string) => ['providers', 'detail', id] as const,
  },
  prompts: {
    all: () => ['prompts'] as const,
    list: (p?: object) => ['prompts', 'list', p] as const,
    detail: (id: string) => ['prompts', 'detail', id] as const,
  },
  analyses: {
    all: () => ['analyses'] as const,
    infinite: (f?: object) => ['analyses', 'infinite', f] as const,
    detail: (id: string) => ['analyses', 'detail', id] as const,
  },
  devices: {
    all: () => ['devices'] as const,
    list: (p?: object) => ['devices', 'list', p] as const,
    detail: (id: string) => ['devices', 'detail', id] as const,
  },
  stats: {
    overview: () => ['stats', 'overview'] as const,
    latency: () => ['stats', 'latency'] as const,
    subjects: () => ['stats', 'subjects'] as const,
  },
  settings: {
    all: () => ['settings'] as const,
  },
} as const
