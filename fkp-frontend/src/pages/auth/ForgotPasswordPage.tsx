import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { CheckCircle2, ChevronLeft, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useForgotPassword } from '@/hooks/useAuthRecovery'
import { useCooldown } from '@/hooks/useCooldown'
import { AUTH_EMAIL_RESEND_COOLDOWN_SECONDS } from '@/lib/constants'
import { resetPasswordCooldownKey, retryAfterSeconds } from '@/lib/cooldown'

const EMAIL_PATTERN = /^\S+@\S+\.\S+$/

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
  const reduceMotion = useReducedMotion()
  const forgotPassword = useForgotPassword()

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
  })

  // Cooldown per alamat email. Di layar sukses kuncinya email yang sudah dikirim;
  // di layar form kuncinya email yang sedang diketik. Dengan begitu "Gunakan email
  // lain" lalu mengirim ke alamat YANG SAMA tetap tertahan, sedangkan alamat lain
  // (mis. salah ketik yang dikoreksi) langsung boleh. Cooldown bertahan walau
  // halaman dimuat ulang (sessionStorage), jadi tidak ada "sukses" palsu saat
  // server diam-diam tidak mengirim ulang.
  const typedEmail = (watch('email') ?? '').trim().toLowerCase()
  const keyEmail = submittedEmail ?? (EMAIL_PATTERN.test(typedEmail) ? typedEmail : null)
  const cooldownKey = keyEmail ? resetPasswordCooldownKey(keyEmail) : null
  const cooldown = useCooldown(cooldownKey)

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
      cooldown.start(AUTH_EMAIL_RESEND_COOLDOWN_SECONDS, resetPasswordCooldownKey(email))
    } catch (err) {
      // Notifikasi error sudah ditampilkan oleh hook useForgotPassword.
      // Jika server menolak karena terlalu sering (429), ikuti waktu tunggunya.
      const retry = retryAfterSeconds(err)
      if (retry) cooldown.start(retry, resetPasswordCooldownKey(email))
    }
  }

  const onSubmit = async (data: ForgotPasswordForm) => {
    // Enter di kolom email juga lewat sini, jadi cooldown dicek di handler, bukan hanya di tombol.
    if (cooldown.isCoolingDown) return
    await sendRequest(data.email)
  }

  const handleResend = async () => {
    if (!submittedEmail || cooldown.isCoolingDown || forgotPassword.isPending) return
    await sendRequest(submittedEmail)
  }

  const handleUseAnotherEmail = () => {
    setSubmittedEmail(null)
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
            <h2 className="text-2xl font-bold tracking-tight mb-2">
              Periksa email Anda
            </h2>
            <p className="text-gray-500 text-sm leading-relaxed mb-1">
              Jika alamat berikut terdaftar dan emailnya sudah terverifikasi, tautan untuk
              mengatur ulang password akan dikirim ke:
            </p>
            <p className="text-sm font-semibold break-all mb-6">{submittedEmail}</p>
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
                disabled={cooldown.isCoolingDown || forgotPassword.isPending}
                aria-busy={forgotPassword.isPending}
                className="btn-secondary w-full btn-md"
              >
                {forgotPassword.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                    Mengirim ulang...
                  </>
                ) : cooldown.isCoolingDown ? (
                  `Kirim ulang (${cooldown.remaining} dtk)`
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
              <h2 className="text-2xl font-bold tracking-tight">Lupa password?</h2>
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
                disabled={isSubmitting || cooldown.isCoolingDown}
                aria-busy={isSubmitting}
                className="btn-primary w-full btn-md lg:btn-lg"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                    Memproses...
                  </>
                ) : cooldown.isCoolingDown ? (
                  `Coba lagi dalam ${cooldown.remaining} detik`
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
