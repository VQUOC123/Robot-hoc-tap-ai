import { format, formatDistanceToNow } from 'date-fns'
import { vi } from 'date-fns/locale'

export function formatDate(date: string | Date, fmt = 'dd/MM/yyyy HH:mm'): string {
  return format(new Date(date), fmt, { locale: vi })
}

export function formatDateShort(date: string | Date): string {
  return format(new Date(date), 'dd/MM/yyyy', { locale: vi })
}

export function formatRelativeTime(date: string | Date): string {
  return formatDistanceToNow(new Date(date), { addSuffix: true, locale: vi })
}

export function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60_000).toFixed(1)}m`
}

export function formatSubject(subject: string): string {
  const map: Record<string, string> = {
    math: 'Toán',
    vietnamese: 'Văn',
    english: 'Anh',
    physics: 'Lý',
    chemistry: 'Hóa',
    biology: 'Sinh',
    history: 'Sử',
    geography: 'Địa',
    other: 'Khác',
  }
  return map[subject] ?? subject
}

export function truncate(str: string, maxLength = 50): string {
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength) + '…'
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
