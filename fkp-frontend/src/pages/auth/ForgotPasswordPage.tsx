import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { CheckCircle2, ChevronLeft, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useForgotPassword } from '@/hooks/useAuthRecovery'

// Samakan dengan AUTH_EMAIL_RESEND_COOLDOWN_SECONDS di backend (config.py).
// Backend diam-diam tidak mengirim ulang selama cooldown, jadi tombol
// tidak boleh aktif lebih cepat dari ini.
const RESEND_COOLDOWN_SECONDS = 60

const forgotPasswordSchema = z.object({
  email: z
    .string()
    .trim()
    .toLowerCase()
    .min(1, 'Email wajib diisi')
    .email('Format email tidak valid'),
})

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>

// ─── Component ────────────────────────────────────────────────────────────────

export function ForgotPasswordPage() {
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null)
  const [cooldown, setCooldown] = useState(0)
  const reduceMotion = useReducedMotion()
  const forgotPassword = useForgotPassword()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
  })

  // Hitung mundur untuk tombol "Kirim ulang"
  useEffect(() => {
    if (cooldown <= 0) return
    const id = window.setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => window.clearTimeout(id)
  }, [cooldown])

  // Animasi mengikuti pola Login; durasi/offset dinolkan jika prefers-reduced-motion aktif
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

  // Backend selalu membalas pesan yang sama (anti user-enumeration), jadi
  // "sukses" di sini berarti permintaan diterima, bukan email pasti terkirim.
  const sendRequest = async (email: string) => {
    try {
      await forgotPassword.mutateAsync(email)
      setSubmittedEmail(email)
      setCooldown(RESEND_COOLDOWN_SECONDS)
    } catch {
      // Notifikasi error sudah ditampilkan oleh hook useForgotPassword.
    }
  }

  const onSubmit = async (data: ForgotPasswordForm) => {
    await sendRequest(data.email)
  }

  const handleResend = async () => {
    if (!submittedEmail || cooldown > 0) return
    await sendRequest(submittedEmail)
  }

  const handleUseAnotherEmail = () => {
    setSubmittedEmail(null)
    setCooldown(0)
    reset()
  }

  return (
    <div className="w-full p-6 md:p-12 lg:max-w-xl xl:max-w-2xl">
      <AnimatePresence mode="wait">
        {submittedEmail ? (
          // ── Sukses ───────────────────────────────────────────────────────
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
              Periksa email Anda
            </h2>
            <p className="text-gray-500 text-sm leading-relaxed mb-1">
              Jika alamat berikut terdaftar dan emailnya sudah terverifikasi, tautan untuk
              mengatur ulang password akan dikirim ke:
            </p>
            <p className="text-sm font-semibold text-gray-900 break-all mb-6">{submittedEmail}</p>
            <p className="text-xs text-gray-400 mb-6 leading-relaxed">
              Tautan berlaku singkat dan hanya bisa dipakai sekali. Tidak menerima email? Periksa
              folder spam. Jika email akun Anda belum pernah diverifikasi, hubungi administrator.
            </p>

            <div className="space-y-3">
              <Link
                to="/login"
                className="btn-primary w-full btn-lg inline-flex items-center justify-center gap-2"
              >
                Kembali ke Login
              </Link>
              <button
                type="button"
                onClick={handleResend}
                disabled={cooldown > 0 || forgotPassword.isPending}
                aria-busy={forgotPassword.isPending}
                className="btn-secondary w-full btn-md"
              >
                {forgotPassword.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                    Mengirim ulang...
                  </>
                ) : cooldown > 0 ? (
                  `Kirim ulang (${cooldown} dtk)`
                ) : (
                  'Kirim ulang tautan'
                )}
              </button>
              <button
                type="button"
                onClick={handleUseAnotherEmail}
                className="text-xs text-brand-600 font-medium hover:underline"
              >
                Gunakan email lain
              </button>
            </div>
          </motion.div>
        ) : (
          // ── Form ─────────────────────────────────────────────────────────
          <motion.div
            key="form"
            variants={viewVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            className="space-y-6"
          >
            {/* Header */}
            <motion.div variants={itemVariants} className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Lupa password?</h2>
              <p className="text-gray-500 text-sm mt-1.5">
                Masukkan email yang terdaftar dan kami akan membantu Anda mengatur ulang password.
              </p>
            </motion.div>

            <motion.form
              variants={itemVariants}
              onSubmit={handleSubmit(onSubmit)}
              noValidate
              className="space-y-5"
            >
              {/* Email */}
              <div>
                <label htmlFor="email" className="label">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  autoFocus
                  placeholder="mail@saktipangan.co.id"
                  aria-invalid={errors.email ? 'true' : 'false'}
                  aria-describedby={errors.email ? 'email-error' : undefined}
                  className={cn('input-base', errors.email && 'input-error')}
                  {...register('email')}
                />
                {errors.email && (
                  <motion.p
                    id="email-error"
                    role="alert"
                    initial={{ opacity: 0, y: reduceMotion ? 0 : -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: reduceMotion ? 0 : 0.2 }}
                    className="mt-1.5 text-xs text-red-600"
                  >
                    {errors.email.message}
                  </motion.p>
                )}
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={isSubmitting}
                aria-busy={isSubmitting}
                className="btn-primary w-full btn-md lg:btn-lg"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                    Memproses...
                  </>
                ) : (
                  'Kirim Link Reset'
                )}
              </button>
            </motion.form>

            {/* Back to login */}
            <motion.div variants={itemVariants} className="mt-6 text-center">
              <Link
                to="/login"
                className="inline-flex items-center gap-1 text-xs text-brand-600 font-medium hover:underline"
              >
                <ChevronLeft className="w-3.5 h-3.5" aria-hidden="true" />
                Kembali ke Login
              </Link>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}