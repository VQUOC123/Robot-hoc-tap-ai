export interface Prompt {
  id: string
  name: string
  content: string
  description?: string
  is_active: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}
