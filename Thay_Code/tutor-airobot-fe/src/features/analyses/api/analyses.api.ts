import { api } from '@/shared/api/client'
import type { Analysis, AnalysisFilters, OverviewStats, LatencyStat, SubjectStat } from '../types'
import type { CursorResponse } from '@/shared/api/types'

const BASE = '/api/v1/analyses'

export const analysesApi = {
  list: (filters: AnalysisFilters = {}) =>
    api.get<CursorResponse<Analysis>>(BASE, { params: filters }),

  getById: (id: string) => api.get<Analysis>(`${BASE}/${id}`),

  getOverviewStats: () => api.get<OverviewStats>('/api/v1/stats/overview'),

  getLatencyStats: () => api.get<LatencyStat[]>('/api/v1/stats/latency'),

  getSubjectStats: () => api.get<SubjectStat[]>('/api/v1/stats/subjects'),
}
