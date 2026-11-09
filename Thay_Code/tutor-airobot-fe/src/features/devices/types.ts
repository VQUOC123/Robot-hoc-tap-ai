// Device matches backend DeviceOutput (GET /api/v1/devices)
export interface Device {
  id: string
  name: string
  last_used_at?: string  // ISO timestamp of last authenticated request
  last_ip?: string       // IP of last authenticated request
  is_active: boolean
  created_at: string
}

// CreateDeviceResult matches the flat backend response (POST /api/v1/devices)
// Backend embeds CreateDeviceOutput: { id, name, token, is_active, created_at, note }
export interface CreateDeviceResult {
  id: string
  name: string
  token: string          // raw bearer token — shown once only, store securely
  is_active: boolean
  created_at: string
  note: string
}
