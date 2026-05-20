import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Eye, EyeOff, Loader2, CheckCircle2, ChevronLeft } from 'lucide-react'
import { motion } from 'framer-motion'
import { useRegisterOutlet } from '@/hooks/useOutletRegister'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { cn } from '@/lib/utils'
import axios from 'axios'

// ─── Types ────────────────────────────────────────────────────────────────────

interface DistributorOption {
  id: string
  nama_perusahaan: string
  kode_distributor: string
  alamat_lengkap: string | null
}

// ─── Password Strength ────────────────────────────────────────────────────────

function getPasswordStrength(password: string): { score: number; label: string; color: string } {
  let score = 0
  if (password.length >= 8) score += 25
  if (/[A-Z]/.test(password)) score += 25
  if (/[0-9]/.test(password)) score += 25
  if (/[^A-Za-z0-9]/.test(password)) score += 25

  if (score <= 25) return { score, label: 'Lemah', color: '#ef4444' }
  if (score <= 50) return { score, label: 'Cukup', color: '#f97316' }
  if (score <= 75) return { score, label: 'Kuat', color: '#eab308' }
  return { score, label: 'Sangat Kuat', color: '#22c55e' }
}

function PasswordStrengthBar({ password }: { password: string }) {
  if (!password) return null
  const { score, label, color } = getPasswordStrength(password)
  return (
    <div className="mt-2 space-y-1">
      <div className="h-1.5 w-full rounded-full bg-gray-100 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300 ease-out"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium" style={{ color }}>{label}</p>
        <p className="text-[10px] text-gray-400">
          {score < 100 ? 'Tambahkan huruf besar, angka, atau simbol' : '✓ Password kuat'}
        </p>
      </div>
    </div>
  )
}

// ─── Schema ───────────────────────────────────────────────────────────────────

const schema = z
  .object({
    nama_toko:       z.string().min(3, 'Nama toko minimal 3 karakter'),
    pemilik_toko:    z.string().min(3, 'Nama pemilik minimal 3 karakter'),
    tipe_toko:       z.enum(['retail', 'grosir', 'horeka'], { required_error: 'Pilih tipe toko' }),
    no_hp:           z.string().min(9, 'No. HP tidak valid').max(15),
    distributor_id:  z.string().uuid('Pilih distributor terlebih dahulu'),
    alamat_lengkap:  z.string().optional(),
    email:           z.string().email('Format email tidak valid'),
    password:        z.string().min(8, 'Password minimal 8 karakter'),
    retype_password: z.string(),
  })
  .refine((d) => d.password === d.retype_password, {
    message: 'Password tidak cocok',
    path: ['retype_password'],
  })

type FormValues = z.infer<typeof schema>

// ─── Steps ────────────────────────────────────────────────────────────────────

const STEPS = ['Data Toko', 'Distribusi', 'Akun'] as const

// ─── Hook ─────────────────────────────────────────────────────────────────────

function usePublicDistributors() {
  const [distributors, setDistributors] = useState<DistributorOption[]>([])
  const [isLoading, setIsLoading]       = useState(true)
  const [error, setError]               = useState<string | null>(null)

  useEffect(() => {
    axios
      .get<DistributorOption[]>('/api/distributors/public')
      .then((res) => setDistributors(res.data))
      .catch(() => setError('Gagal memuat daftar distributor. Coba muat ulang halaman.'))
      .finally(() => setIsLoading(false))
  }, [])

  return { distributors, isLoading, error }
}

// ─── Animation Variants ───────────────────────────────────────────────────────

const containerVariants = {
  animate: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
}

const itemVariants = {
  initial: { opacity: 0, y: 14 },
  animate: {
    opacity: 1,
    y: 0,
  },
}

const stepContentVariants = {
  initial: { opacity: 0, x: 20 },
  animate: { opacity: 1, x: 0 },
  exit:    { opacity: 0, x: -16 },
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function RegisterOutletPage() {
  const [step, setStep]         = useState(0)
  const [showPw, setShowPw]     = useState(false)
  const [showPw2, setShowPw2]   = useState(false)
  const [isSuccess, setIsSuccess] = useState<{ kode_outlet: string; message: string } | null>(null)

  const { mutate: register, isPending } = useRegisterOutlet()
  const { distributors, isLoading: loadingDist, error: distError } = usePublicDistributors()

  const {
    register: reg,
    handleSubmit,
    trigger,
    setValue,
    watch,
    clearErrors,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const selectedDistributorId = watch('distributor_id')
  const passwordValue         = watch('password') ?? ''
  const selectedDistributor   = distributors.find((d) => d.id === selectedDistributorId) ?? null

  const stepFields: (keyof FormValues)[][] = [
    ['nama_toko', 'pemilik_toko', 'tipe_toko', 'no_hp'],
    ['distributor_id'],
    ['email', 'password', 'retype_password'],
  ]

  const handleNext = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    const valid = await trigger(stepFields[step])
    if (valid) { clearErrors(); setStep((s) => s + 1) }
  }

  const onSubmit = (data: FormValues) => {
    register(
      { ...data, alamat_lengkap: data.alamat_lengkap || null },
      { onSuccess: (res) => setIsSuccess({ kode_outlet: res.kode_outlet, message: res.message }) },
    )
  }

  // ── Sukses ────────────────────────────────────────────────────────────────
  if (isSuccess) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="text-center"
      >
        <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-5">
          <CheckCircle2 className="w-8 h-8 text-emerald-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Pendaftaran Berhasil!</h2>
        <p className="text-gray-500 text-sm mb-6">{isSuccess.message}</p>
        <div className="bg-gray-50 border border-gray-100 rounded-xl px-5 py-4 mb-6">
          <p className="text-xs text-gray-400 mb-1">Kode Outlet Anda</p>
          <p className="text-xl font-bold text-brand-700 tracking-widest">{isSuccess.kode_outlet}</p>
        </div>
        <p className="text-xs text-gray-400 mb-8 leading-relaxed">
          Simpan kode outlet di atas. Anda akan mendapat notifikasi setelah akun diverifikasi oleh distributor.
        </p>
        <Link to="/login" className="btn-primary w-full btn-lg inline-flex items-center justify-center gap-2">
          Kembali ke Login
        </Link>
      </motion.div>
    )
  }

  // ── Form ─────────────────────────────────────────────────────────────────
  return (
    <motion.div variants={containerVariants} initial="initial" animate="animate" className="max-w-lg w-full space-y-6">
      {/* Header */}
      <motion.div variants={itemVariants} className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Daftar Outlet</h2>
        <p className="text-gray-500 text-sm mt-1.5">
          Lengkapi data berikut untuk mendaftarkan outlet Anda.
        </p>
      </motion.div>

      {/* Stepper */}
      <motion.div variants={itemVariants} className="flex items-center gap-2 mb-8">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center gap-2 flex-1">
            <div className="flex flex-col items-center gap-1 flex-1">
              <div
                className={cn(
                  'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300',
                  i < step   ? 'bg-emerald-500 text-white' :
                  i === step ? 'bg-brand-600 text-white ring-4 ring-brand-100' :
                               'bg-gray-100 text-gray-400',
                )}
              >
                {i < step ? '✓' : i + 1}
              </div>
              <span className={cn('text-[10px] font-medium whitespace-nowrap transition-colors',
                i === step ? 'text-brand-600' : i < step ? 'text-emerald-500' : 'text-gray-400'
              )}>
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={cn('h-0.5 flex-1 mb-4 rounded-full transition-all duration-500',
                i < step ? 'bg-emerald-400' : 'bg-gray-200'
              )} />
            )}
          </div>
        ))}
      </motion.div>

      {/* Form */}
      <motion.form
        variants={itemVariants}
        id="outlet-form"
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
      >
        {/* ── Step 0 ─────────────────────────────────────────────────────── */}
        {step === 0 && (
          <motion.div key="step0" variants={stepContentVariants} initial="initial" animate="animate" exit="exit" className="space-y-4">
            <Input label="Nama Toko" required placeholder="Toko Sumber Jaya" error={errors.nama_toko?.message} {...reg('nama_toko')} />
            <Input label="Nama Pemilik" required placeholder="Budi Santoso" error={errors.pemilik_toko?.message} {...reg('pemilik_toko')} />
            <Select label="Tipe Toko" required placeholder="-- Pilih tipe toko --" error={errors.tipe_toko?.message} {...reg('tipe_toko')}>
              <option value="retail">Retail</option>
              <option value="grosir">Grosir</option>
              <option value="horeka">HoReCa</option>
            </Select>
            <Input label="No. HP / WhatsApp" required type="tel" placeholder="081234567890" error={errors.no_hp?.message} {...reg('no_hp')} />
          </motion.div>
        )}

        {/* ── Step 1 ─────────────────────────────────────────────────────── */}
        {step === 1 && (
          <motion.div key="step1" variants={stepContentVariants} initial="initial" animate="animate" exit="exit" className="space-y-4">
            <div>
              <label className="label">Distributor <span className="text-red-500">*</span></label>
              {loadingDist && (
                <div className="input-base flex items-center gap-2 text-gray-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Memuat daftar distributor...</span>
                </div>
              )}
              {distError && !loadingDist && (
                <div className="input-base text-sm text-red-500 bg-red-50 border-red-200">{distError}</div>
              )}
              {!loadingDist && !distError && (
                <select
                  className={cn('input-base', errors.distributor_id && 'input-error', !selectedDistributorId && 'text-gray-400')}
                  {...reg('distributor_id')}
                  onChange={(e) => {
                    const picked = distributors.find((d) => d.id === e.target.value)
                    setValue('distributor_id', e.target.value, { shouldValidate: true })
                    setValue('alamat_lengkap', picked?.alamat_lengkap ?? '')
                  }}
                >
                  <option value="">-- Pilih distributor --</option>
                  {distributors.map((d) => (
                    <option key={d.id} value={d.id} className="text-gray-900">
                      {d.nama_perusahaan}{d.kode_distributor ? ` (${d.kode_distributor})` : ''}
                    </option>
                  ))}
                </select>
              )}
              {errors.distributor_id && (
                <p className="mt-1.5 text-xs text-red-600">{errors.distributor_id.message}</p>
              )}
              <p className="mt-1 text-xs text-gray-400">Pilih distributor yang akan mengelola outlet Anda.</p>
            </div>

            <div>
              <label className="label">Alamat Distributor</label>
              <textarea
                rows={3}
                disabled
                readOnly
                value={selectedDistributor?.alamat_lengkap ?? ''}
                placeholder={selectedDistributorId ? 'Alamat tidak tersedia' : 'Otomatis terisi setelah memilih distributor'}
                className="input-base resize-none bg-gray-50 text-gray-500 cursor-not-allowed"
              />
              <p className="mt-1 text-xs text-gray-400">Alamat diambil otomatis dari data distributor.</p>
            </div>
          </motion.div>
        )}

        {/* ── Step 2 ─────────────────────────────────────────────────────── */}
        {step === 2 && (
          <motion.div key="step2" variants={stepContentVariants} initial="initial" animate="animate" exit="exit" className="space-y-4">
            <Input label="Email" required type="email" placeholder="toko@email.com" error={errors.email?.message} {...reg('email')} />

            <div>
              <label className="label label-required">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  placeholder="Minimal 8 karakter"
                  className={cn('input-base pr-10', errors.password && 'input-error')}
                  {...reg('password')}
                />
                <button type="button" onClick={() => setShowPw(!showPw)} className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600" tabIndex={-1}>
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="mt-1.5 text-xs text-red-600">{errors.password.message}</p>}
              <PasswordStrengthBar password={passwordValue} />
            </div>

            <div>
              <label className="label label-required">Ulangi Password</label>
              <div className="relative">
                <input
                  type={showPw2 ? 'text' : 'password'}
                  placeholder="Ketik ulang password"
                  className={cn('input-base pr-10', errors.retype_password && 'input-error')}
                  {...reg('retype_password')}
                />
                <button type="button" onClick={() => setShowPw2(!showPw2)} className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600" tabIndex={-1}>
                  {showPw2 ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.retype_password && <p className="mt-1.5 text-xs text-red-600">{errors.retype_password.message}</p>}
            </div>
          </motion.div>
        )}
      </motion.form>

      {/* Navigation */}
      <motion.div variants={itemVariants} className="flex gap-3 pt-5">
        {step > 0 && (
          <button
            type="button"
            onClick={() => setStep((s) => s - 1)}
            className="btn-secondary flex-1 btn-md flex items-center justify-center gap-1.5"
          >
            <ChevronLeft className="w-4 h-4" /> Kembali
          </button>
        )}
        {step < STEPS.length - 1 ? (
          <button type="button" onClick={handleNext} className="btn-primary flex-1 btn-md">
            Lanjut
          </button>
        ) : (
          <button type="submit" form="outlet-form" disabled={isPending} className="btn-primary flex-1 btn-lg">
            {isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Mendaftar...</> : 'Daftar Sekarang'}
          </button>
        )}
      </motion.div>

      <motion.p variants={itemVariants} className="mt-5 text-center text-xs text-gray-400">
        Sudah punya akun?{' '}
        <Link to="/login" className="text-brand-600 font-medium hover:underline">Masuk di sini</Link>
      </motion.p>
    </motion.div>
  )
}