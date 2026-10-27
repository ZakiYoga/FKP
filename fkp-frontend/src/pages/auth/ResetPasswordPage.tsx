import { isAxiosError } from 'axios'
import { useEffect, useRef, useState } from 'react'
import { useForm, type UseFormRegisterReturn } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { newPasswordSchema, PASSWORD_RULE_HINT } from '@/lib/password'
import { useResetPassword } from '@/hooks/useAuthRecovery'

// Aturan password (minimal 8 karakter, maksimal 72 byte) ada di satu tempat:
// src/lib/password.ts, supaya semua form konsisten dengan backend.
const resetPasswordSchema = z
  .object({
    password_baru: newPasswordSchema,
    password_baru_konfirmasi: z.string().min(1, 'Konfirmasi password wajib diisi'),
  })
  .refine((d) => d.password_baru === d.password_baru_konfirmasi, {
    message: 'Konfirmasi password tidak cocok',
    path: ['password_baru_konfirmasi'],
  })

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>

// ─── Field password (dipakai dua kali) ────────────────────────────────────────

function PasswordField({
  id,
  label,
  error,
  registration,
  autoFocus,
  reduceMotion,
}: {
  id: string
  label: string
  error?: string
  registration: UseFormRegisterReturn
  autoFocus?: boolean
  reduceMotion: boolean | null
}) {
  return (
    <div>
      <label htmlFor={id} className="label">
        {label}
      </label>
      <input
        id={id}
        type="password"
        autoComplete="new-password"
        autoFocus={autoFocus}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${id}-error` : undefined}
        className={cn('input-base', error && 'input-error')}
        {...registration}
      />
      {error && (
        <motion.p
          id={`${id}-error`}
          role="alert"
          initial={{ opacity: 0, y: reduceMotion ? 0 : -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.2 }}
          className="mt-1.5 text-xs text-red-600"
        >
          {error}
        </motion.p>
      )}
    </div>
  )
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  // Token dibaca sekali ke state, lalu dihapus dari URL (lihat effect di bawah).
  const [token] = useState(() => searchParams.get('token') ?? '')
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const reduceMotion = useReducedMotion()
  const resetPassword = useResetPassword()
  const [done, setDone] = useState(false)
  const strippedRef = useRef(false)

  const [tokenRejected, setTokenRejected] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
  })

  // Hapus token dari URL setelah dibaca supaya tidak tersimpan di riwayat / bocor lewat Referer.
  useEffect(() => {
    if (!token || strippedRef.current) return
    strippedRef.current = true
    navigate(pathname, { replace: true })
  }, [token, navigate, pathname])

  const offset = reduceMotion ? 0 : 16
  const duration = reduceMotion ? 0 : 0.4

  const viewVariants = {
    initial: {},
    animate: {
      transition: {
        staggerChildren: reduceMotion ? 0 : 0.08,
        delayChildren: reduceMotion ? 0 : 0.1,
      },
    },
    exit: { opacity: 0, transition: { duration: reduceMotion ? 0 : 0.15 } },
  }

  const itemVariants = {
    initial: { opacity: 0, y: offset },
    animate: { opacity: 1, y: 0, transition: { duration } },
  }

  const onSubmit = async (data: ResetPasswordForm) => {
    try {
      await resetPassword.mutateAsync({
        token,
        password_baru: data.password_baru,
        password_baru_konfirmasi: data.password_baru_konfirmasi,
      })
      setDone(true)
    } catch (e) {
      const detail = isAxiosError(e) ? e.response?.data?.detail : null
      if (isAxiosError(e) && e.response?.status === 400 && typeof detail === 'string' && detail.startsWith('Tautan tidak valid')) {
        setTokenRejected(true)
      }
    }
  }

  const view = (!token && !done) || tokenRejected ? 'invalid' : done ? 'success' : 'form'

  return (
    <div className="w-full p-6 md:p-12 lg:max-w-xl xl:max-w-2xl">
      <AnimatePresence mode="wait">
        {view === 'invalid' && (
          // ── Tautan tidak ada / tidak valid ──────────────────────────────
          <motion.div
            key="invalid"
            role="alert"
            initial={{ opacity: 0, y: reduceMotion ? 0 : 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.3 }}
            className="text-center"
          >
            <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-5">
              <XCircle className="w-8 h-8 text-red-600" aria-hidden="true" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 tracking-tight mb-2">
              Tautan tidak valid
            </h2>
            <p className="text-gray-500 text-sm leading-relaxed mb-8">
              Tautan reset password tidak lengkap atau sudah tidak berlaku. Silakan minta tautan
              baru.
            </p>
            <Link
              to="/forgot-password"
              className="btn-primary w-full btn-lg inline-flex items-center justify-center gap-2"
            >
              Minta Tautan Baru
            </Link>
          </motion.div>
        )}

        {view === 'success' && (
          // ── Sukses ──────────────────────────────────────────────────────
          <motion.div
            key="success"
            role="status"
            aria-live="polite"
            initial={{ opacity: 0, y: reduceMotion ? 0 : 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.3 }}
            className="text-center"
          >
            <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-5">
              <CheckCircle2 className="w-8 h-8 text-emerald-600" aria-hidden="true" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 tracking-tight mb-2">
              Password berhasil diubah
            </h2>
            <p className="text-gray-500 text-sm leading-relaxed mb-8">
              Silakan login dengan password baru Anda. Sesi login lama di perangkat lain otomatis
              dikeluarkan.
            </p>
            <Link
              to="/login"
              className="btn-primary w-full btn-lg inline-flex items-center justify-center gap-2"
            >
              Ke Halaman Login
            </Link>
          </motion.div>
        )}

        {view === 'form' && (
          // ── Form ────────────────────────────────────────────────────────
          <motion.div
            key="form"
            variants={viewVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            className="space-y-6"
          >
            <motion.div variants={itemVariants} className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 tracking-tight">
                Buat password baru
              </h2>
              <p className="text-gray-500 text-sm mt-1.5">
                {PASSWORD_RULE_HINT} Tautan ini hanya bisa dipakai sekali.
              </p>
            </motion.div>

            <motion.form
              variants={itemVariants}
              onSubmit={handleSubmit(onSubmit)}
              noValidate
              className="space-y-5"
            >
              <PasswordField
                id="password_baru"
                label="Password baru"
                autoFocus
                error={errors.password_baru?.message}
                registration={register('password_baru')}
                reduceMotion={reduceMotion}
              />
              <PasswordField
                id="password_baru_konfirmasi"
                label="Konfirmasi password baru"
                error={errors.password_baru_konfirmasi?.message}
                registration={register('password_baru_konfirmasi')}
                reduceMotion={reduceMotion}
              />

              <button
                type="submit"
                disabled={isSubmitting}
                aria-busy={isSubmitting}
                className="btn-primary w-full btn-md lg:btn-lg"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                    Menyimpan...
                  </>
                ) : (
                  'Simpan Password'
                )}
              </button>

              <p className="text-center text-xs text-gray-500">
                Tautan bermasalah?{' '}
                <Link
                  to="/forgot-password"
                  className="text-brand-600 font-medium hover:underline"
                >
                  Minta tautan baru
                </Link>
              </p>
            </motion.form>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}