import api from '@/lib/axios'

// File upload dari BE (avatar, foto outlet, dll.) disajikan lewat static mount /uploads.
// Origin diambil dari baseURL axios; jika baseURL relatif (mis. '/api'), pakai origin halaman.
// Sesuaikan jika format path yang disimpan service berbeda.
export function getUploadUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined
  if (/^(https?:|blob:|data:)/i.test(path)) return path
  const origin = new URL(api.defaults.baseURL ?? '', window.location.origin).origin
  const clean = path.replace(/^\/+/, '').replace(/^uploads\//, '')
  return `${origin}/uploads/${clean}`
}

// Nama lama dipertahankan agar import yang sudah ada tidak rusak.
export const getAvatarUrl = getUploadUrl