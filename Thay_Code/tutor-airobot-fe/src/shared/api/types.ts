export interface PaginatedResponse<T> {
  data: T[]
  meta: PaginationMeta
}

export interface PaginationMeta {
  total: number
  page: number
  limit: number
  total_pages: number
}

export interface CursorMeta {
  cursor: string | null  // next page cursor (backend field name)
  has_more: boolean
  total?: number
}

export interface CursorResponse<T> {
  data: T[]
  meta: CursorMeta
}

export interface ApiError {
  code: string
  message: string
  details?: Record<string, string>
}
