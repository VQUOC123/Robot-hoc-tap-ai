export interface SystemSettings {
  max_image_size_kb: number
  ai_timeout_sec: number
  rate_limit_per_minute: number
  log_retention_days: number
  allow_concurrent_requests: boolean
}
