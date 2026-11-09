export interface Analysis {
  id: string
  device_id: string
  device_name: string           // joined from devices table
  student_id?: string
  activity?: string
  focus_score?: number
  hw_visible?: boolean
  doing_hw?: boolean            // null when analysis is incomplete
  subject?: string              // math, vietnamese, english, ...
  grade?: string                // "10", "11", "12"
  hw_type?: string              // exercises, theory, reading
  progress?: number             // 0–100
  hints?: string                // AI suggestion (was "help" in older design)
  confidence?: number           // 0.0–1.0
  provider_id?: string
  provider_name?: string        // joined from providers table
  latency_ms?: number           // s1 + s2 latency combined
  image_width?: number
  image_height?: number
  image_size_kb?: number
  created_at: string
}

export interface AnalysisFilters {
  from?: string               // ISO date "YYYY-MM-DD"
  to?: string
  subject?: string
  device_id?: string
  doing_hw?: boolean
  cursor?: string
  limit?: number
}

export interface OverviewStats {
  total_analyses: number
  today_total: number
  today_homework: number
  homework_rate: number         // 0.0–1.0
  avg_latency_ms: number
  active_providers: number
  active_devices: number
  top_subject?: string
}

export interface LatencyStat {
  hour: string                  // RFC3339 UTC timestamp
  avg_ms: number
  count: number
}

export interface SubjectStat {
  subject: string               // "math", "vietnamese", etc.
  count: number
}
