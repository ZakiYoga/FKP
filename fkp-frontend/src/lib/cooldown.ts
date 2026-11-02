import { AUTH_EMAIL_RESEND_COOLDOWN_SECONDS } from '@/lib/constants'

// Kunci cooldown per JENIS email + alamatnya. Di server cooldown dihitung per user
// dan per jenis token (verifikasi vs reset password), jadi keduanya tidak boleh
// saling mengunci di UI. Pengiriman verifikasi dari halaman publik, menu Profil,
// maupun ganti email memakai kunci yang sama karena memakai token yang sama.
const normalize = (email: string) => email.trim().toLowerCase()
export const verifyEmailCooldownKey = (email: string) => `verify-email:${normalize(email)}`
export const resetPasswordCooldownKey = (email: string) => `reset-password:${normalize(email)}`

type HttpErrorLike = {
    response?: { status?: number; headers?: Record<string, unknown>; data?: { detail?: unknown } }
}

/**
 * Sisa waktu tunggu (detik) bila server menolak dengan HTTP 429, selain itu null.
 * Urutan sumber: header Retry-After, angka di pesan ("Mohon tunggu 42 detik ..."),
 * lalu nilai cooldown bawaan. Asumsi klien HTTP axios (error.response).
 */
export function retryAfterSeconds(error: unknown): number | null {
    const res = (error as HttpErrorLike | null)?.response
    if (res?.status !== 429) return null

    const header = Number(res.headers?.['retry-after'])
    if (Number.isFinite(header) && header > 0) return Math.min(Math.ceil(header), 3600)

    const detail = typeof res.data?.detail === 'string' ? res.data.detail : ''
    const match = /(\d+)\s*detik/i.exec(detail)
    if (match) return Math.min(Number(match[1]), 3600)

    return AUTH_EMAIL_RESEND_COOLDOWN_SECONDS
}
