import { useEffect, useRef, useState, type FormEvent } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { cn, getErrorMessage } from '@/lib/utils'
import { useResendVerificationPublic, useVerifyEmail } from '@/hooks/useAuthRecovery'
import { useIsAuthenticated } from '@/store/authStore'

const EMAIL_PATTERN = /^\S+@\S+\.\S+$/

export function VerifyEmailPage() {
    const [searchParams] = useSearchParams()
    const [token] = useState(() => searchParams.get('token') ?? '')
    const navigate = useNavigate()
    const { pathname } = useLocation()
    const reduceMotion = useReducedMotion()
    // Cegah panggilan ganda (React StrictMode) yang akan menghabiskan token sekali pakai.
    const calledRef = useRef(false)
    const verify = useVerifyEmail()
    const resend = useResendVerificationPublic()

    const [resendEmail, setResendEmail] = useState('')
    const [resendError, setResendError] = useState<string | null>(null)

    const isAuthenticated = useIsAuthenticated()

    useEffect(() => {
        if (!token || calledRef.current) return
        calledRef.current = true
        navigate(pathname, { replace: true }) // hapus token dari URL
        verify.mutate(token)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token])

    const status = !token
        ? 'invalid'
        : verify.isSuccess
            ? 'success'
            : verify.isError
                ? 'error'
                : 'loading'

    const noToken = status === 'invalid'

    const handleResend = async (e: FormEvent) => {
        e.preventDefault()
        setResendError(null)
        const email = resendEmail.trim().toLowerCase()
        if (!EMAIL_PATTERN.test(email)) {
            setResendError('Format email tidak valid')
            return
        }
        try {
            await resend.mutateAsync(email)
        } catch {
            // Notifikasi error sudah ditampilkan oleh hook useResendVerificationPublic.
        }
    }

    const fade = {
        initial: { opacity: 0, y: reduceMotion ? 0 : 8 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: reduceMotion ? 0 : 0.3 },
    }

    return (
        <div className="w-full p-6 md:p-12 lg:max-w-xl xl:max-w-2xl">
            {status === 'loading' && (
                <motion.div {...fade} role="status" aria-live="polite" className="text-center">
                    <Loader2
                        className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4"
                        aria-hidden="true"
                    />
                    <p className="text-sm text-gray-500">Memverifikasi email Anda...</p>
                </motion.div>
            )}

            {status === 'success' && (
                <motion.div {...fade} role="status" aria-live="polite" className="text-center">
                    <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-5">
                        <CheckCircle2 className="w-8 h-8 text-emerald-600" aria-hidden="true" />
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 tracking-tight mb-2">
                        Email berhasil diverifikasi
                    </h2>
                    <p className="text-gray-500 text-sm leading-relaxed mb-8">
                        Terima kasih. Sekarang Anda dapat memakai fitur lupa password jika suatu saat
                        dibutuhkan.
                    </p>
                    <Link
                        to={isAuthenticated ? '/dashboard' : '/login'}
                        className="btn-primary w-full btn-lg inline-flex items-center justify-center gap-2"
                    >
                        {isAuthenticated ? 'Ke Dashboard' : 'Ke Halaman Login'}
                    </Link>
                </motion.div>
            )}

            {(status === 'error' || status === 'invalid') && (
                <motion.div {...fade} role={noToken ? 'status' : 'alert'}>
                    <div className="text-center">
                        {!noToken && (
                            <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-5">
                                <XCircle className="w-8 h-8 text-red-600" aria-hidden="true" />
                            </div>
                        )}
                        <h2 className="text-2xl font-bold text-gray-900 tracking-tight mb-2">
                            {noToken ? 'Kirim ulang verifikasi email' : 'Verifikasi gagal'}
                        </h2>
                        <p className="text-gray-500 text-sm leading-relaxed mb-8">
                            {noToken
                                ? 'Masukkan email akun Anda, kami akan mengirim tautan verifikasi baru.'
                                : getErrorMessage(verify.error)}
                        </p>
                    </div>

                    {/* Kirim ulang tanpa login (mis. outlet yang masih menunggu approval) */}
                    <form onSubmit={handleResend} noValidate className="space-y-3 mb-6">
                        <div>
                            <label htmlFor="resend-email" className="label">
                                Email akun
                            </label>
                            <input
                                id="resend-email"
                                type="email"
                                autoComplete="email"
                                placeholder="mail@saktipangan.co.id"
                                value={resendEmail}
                                onChange={(e) => setResendEmail(e.target.value)}
                                aria-invalid={resendError ? 'true' : 'false'}
                                className={cn('input-base', resendError && 'input-error')}
                            />
                            {resendError && <p className="mt-1.5 text-xs text-red-600">{resendError}</p>}
                        </div>
                        <button
                            type="submit"
                            disabled={resend.isPending}
                            aria-busy={resend.isPending}
                            className="btn-secondary w-full btn-md"
                        >
                            {resend.isPending ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                                    Mengirim...
                                </>
                            ) : (
                                'Kirim Ulang'
                            )}
                        </button>
                    </form>

                    <div className="text-center">
                        <Link to="/login" className="text-xs text-brand-600 font-medium hover:underline">
                            Kembali ke Login
                        </Link>
                    </div>
                </motion.div>
            )
            }
        </div >
    )
}