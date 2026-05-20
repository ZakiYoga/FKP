import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNow } from 'date-fns'
import { id } from 'date-fns/locale'
import type { ApiError, FkpStatusKey, FkpPrioritas } from '@/types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  return format(new Date(dateStr), 'dd MMM yyyy', { locale: id })
}

export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  return format(new Date(dateStr), 'dd MMM yyyy, HH:mm', { locale: id })
}

export function formatRelative(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: id })
}

export function getErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as { response?: { data?: ApiError } }
    const detail = axiosError.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ')
  }
  if (error instanceof Error) return error.message
  return 'Terjadi kesalahan. Silakan coba lagi.'
}

// Status color sesuai FkpStatus BE baru
export function getStatusColor(status: FkpStatusKey): string {
  const map: Record<FkpStatusKey, string> = {
    draft:                    'bg-gray-100 text-gray-600',
    submitted:                'bg-blue-100 text-blue-700',
    apsm_reviewed:            'bg-violet-100 text-violet-700',
    rsm_approval_investigasi: 'bg-amber-100 text-amber-700',
    in_investigation:         'bg-orange-100 text-orange-700',
    investigated:             'bg-cyan-100 text-cyan-700',
    rsm_approval_resolusi:    'bg-purple-100 text-purple-700',
    direktur_approval:        'bg-fuchsia-100 text-fuchsia-700',
    accepted:                 'bg-emerald-100 text-emerald-700',
    in_process:               'bg-teal-100 text-teal-700',
    need_revision:            'bg-red-100 text-red-700',
    rejected:                 'bg-red-200 text-red-800',
    closed:                   'bg-slate-100 text-slate-600',
  }
  return map[status] ?? 'bg-gray-100 text-gray-600'
}

export function getPrioritasColor(prioritas: FkpPrioritas): string {
  const map: Record<FkpPrioritas, string> = {
    top_urgent: 'bg-red-100 text-red-700 border border-red-200',
    urgent:     'bg-orange-100 text-orange-700 border border-orange-200',
    reguler:    'bg-green-100 text-green-700 border border-green-200',
    low:        'bg-blue-100 text-blue-700 border border-blue-200',
  }
  return map[prioritas] ?? 'bg-gray-100 text-gray-600'
}

export function formatFileSize(bytes: number | null): string {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function formatRupiah(amount: number | null | undefined): string {
  if (amount == null) return '-'
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
  }).format(amount)
}