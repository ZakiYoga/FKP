import { z } from 'zod'

// ─── Sumber tunggal aturan password baru ──────────────────────────────────────
// Dipakai oleh: ResetPasswordPage, SecuritySection (ubah password),
// UserPage (tambah user), dan form lain yang menetapkan password baru.
// Backend harus menegakkan aturan yang sama (minimal 8 karakter, maksimal 72
// byte UTF-8 karena batas bcrypt).

export const PASSWORD_MIN_LENGTH = 8
export const PASSWORD_MAX_BYTES = 72

export const PASSWORD_RULE_HINT = `Gunakan minimal ${PASSWORD_MIN_LENGTH} karakter dan maksimal ${PASSWORD_MAX_BYTES} byte.`

const encoder = new TextEncoder()

/** Panjang dalam byte UTF-8 (emoji / karakter non-ASCII bisa 2-4 byte). */
export const passwordByteLength = (value: string): number =>
  encoder.encode(value).length

/**
 * Panjang dalam code point (satu emoji dihitung 1), sama dengan len() di Python.
 * `value.length` di JS menghitung unit UTF-16 sehingga satu emoji dihitung 2.
 */
const passwordCharLength = (value: string): number => Array.from(value).length

/** Mengembalikan pesan error, atau null jika password baru valid. */
export function validateNewPassword(value: string): string | null {
  if (!value) return 'Password wajib diisi'
  if (passwordCharLength(value) < PASSWORD_MIN_LENGTH) {
    return `Password minimal ${PASSWORD_MIN_LENGTH} karakter`
  }
  if (passwordByteLength(value) > PASSWORD_MAX_BYTES) {
    return `Password terlalu panjang (maksimal ${PASSWORD_MAX_BYTES} byte)`
  }
  return null
}

/** Skema zod untuk form berbasis react-hook-form. */
export const newPasswordSchema = z.string().superRefine((value, ctx) => {
  const message = validateNewPassword(value)
  if (message) ctx.addIssue({ code: 'custom', message })
})