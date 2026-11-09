export interface Provider {
  id: string
  name: string
  base_url: string
  api_key: string  // masked, e.g. "sk-...abc"
  model: string
  timeout_sec: number
  is_default: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TestResult {
  success: boolean
  latency_ms: number
  error?: string
}
