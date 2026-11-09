export interface AdminUser {
  id: string
  email: string
  name: string
  role: string
  created_at: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  expires_in: number
  user: AdminUser
}
