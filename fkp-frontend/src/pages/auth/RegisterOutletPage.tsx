import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Eye, EyeOff, Loader2, CheckCircle2, ChevronLeft } from 'lucide-react'
import { motion } from 'framer-motion'
import { useRegisterOutlet } from '@/hooks/useOutletRegister'
import { Input } from '@/components/ui/Input'
import { SearchableSelect } from '@/components/ui/SearchableSelect'
import { cn, getErrorMessage, getFieldErrors } from '@/lib/utils'
import axios from 'axios'
import { DistributorOption } from '@/types'
import { RegisterOutletFormValues, registerOutletSchema } from '@/schemas/registerOutletSchema'
import { TIPE_TOKO_OPTIONS } from '@/types/outlet'
import { notifications } from '@mantine/notifications'

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
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700">
        <div
          className="h-full rounded-full transition-all duration-300 ease-out"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium" style={{ color }}>{label}</p>
        <p className="text-[10px] text-gray-400">
          {score < 100 ? 'Kombinasikan huruf besar, angka, atau simbol' : '✓ Password kuat'}
        </p>
      </div>
    </div>
  )
}

const TIPE_TOKO_SELECT_OPTIONS = TIPE_TOKO_OPTIONS.map((t) => ({ value: t.value, label: t.label }))

// ─── Steps ────────────────────────────────────────────────────────────────────

const STEPS = ['Data Toko', 'Distribusi', 'Akun'] as const

// ─── Hook ─────────────────────────────────────────────────────────────────────

function usePublicDistributors() {
  const [distributors, setDistributors] = useState<DistributorOption[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
  exit: { opacity: 0, x: -16 },
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function RegisterOutletPage() {
  const [step, setStep] = useState(0)
  const [showPw, setShowPw] = useState(false)
  const [showPw2, setShowPw2] = useState(false)
  const [isSuccess, setIsSuccess] = useState<{ kode_outlet: string; message: string; email: string } | null>(null)

  const { mutate: register, isPending } = useRegisterOutlet()
  const { distributors, isLoading: loadingDist, error: distError } = usePublicDistributors()
  const [previewAlamatDistributor, setPreviewAlamatDistributor] = useState('')

  const {
    register: reg,
    handleSubmit,
    control,
    trigger,
    setValue,
    watch,
    clearErrors,
    setError,
    setFocus,
    formState: { errors },
  } = useForm<RegisterOutletFormValues>({ resolver: zodResolver(registerOutletSchema) })

  const selectedDistributorId = watch('distributor_id')
  const passwordValue = watch('password') ?? ''
  const selectedDistributor = distributors.find((d) => d.id === selectedDistributorId) ?? null
  // Label memuat nama dan kode, jadi pencarian cocok untuk keduanya
  const distributorOptions = distributors.map((d) => ({
    value: d.id,
    label: `${d.nama_perusahaan}${d.kode_distributor ? ` (${d.kode_distributor})` : ''}`,
  }))

  const stepFields: (keyof RegisterOutletFormValues)[][] = [
    ['nama_toko', 'first_name', 'last_name', 'tipe_toko', 'no_hp', 'alamat_lengkap'],
    ['distributor_id'],
    ['email', 'password', 'retype_password'],
  ]

  const handleNext = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    const valid = await trigger(stepFields[step])
    if (valid) { clearErrors(); setStep((s) => s + 1) }
  }

  const onSubmit = (data: RegisterOutletFormValues) => {
    const email = data.email.trim().toLowerCase()
    register(
      {
        ...data,
        last_name: data.last_name?.trim() || undefined,
        alamat_lengkap: data.alamat_lengkap || '',
      },
      {
        onSuccess: (res) =>
          setIsSuccess({ kode_outlet: res.kode_outlet, message: res.message, email }),

        onError: (e) => {
          const fieldErrors = getFieldErrors(e)
          if (!fieldErrors) return // error umum sudah di-toast oleh hook

          // 1) Tandai tiap field yang dikenali, catat step paling awal
          let firstStep = Infinity
          let firstField: keyof RegisterOutletFormValues | null = null

          for (const [field, message] of Object.entries(fieldErrors)) {
            const key = field as keyof RegisterOutletFormValues
            const stepIdx = stepFields.findIndex((f) => f.includes(key))
            if (stepIdx === -1) continue
            setError(key, { type: 'server', message })
            if (stepIdx < firstStep) { firstStep = stepIdx; firstField = key }
          }

          // 2) Tidak ada field yang cocok → jangan diam, toast pesan server
          if (!firstField) {
            notifications.show({ message: getErrorMessage(e), color: 'red' })
            return
          }

          // 3) Pindah ke step bermasalah + toast ringkas + fokus ke field
          setStep(firstStep)
          notifications.show({
            title: 'Data belum valid',
            message: `Periksa kembali isian pada langkah "${STEPS[firstStep]}".`,
            color: 'red',
          })
          setTimeout(() => setFocus(firstField!), 150) // tunggu step selesai render
        },
      },
    )
  }

  function normalizePhoneLocal(raw: string): string {
    let digits = raw.replace(/\D/g, '')        // buang spasi, +, -, dll
    if (digits.startsWith('62')) digits = digits.slice(2)
    digits = digits.replace(/^0+/, '')         // buang 0 di depan
    return digits.slice(0, 13)                 // 62 + 13 digit = maks 15
  }

  // ── Sukses ────────────────────────────────────────────────────────────────
  if (isSuccess) {
    return (
      <motion.div
        variants={containerVariants}
        initial="initial"
        animate="animate"
        className="w-full text-center space-y-6 p-4 md:p-6 lg:max-w-xl xl:max-w-2xl"
      >
        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-500/15">
          <CheckCircle2 className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
        </div>
        <h2 className="mb-2 text-2xl font-bold text-gray-900 dark:text-gray-100">Pendaftaran Berhasil!</h2>
        <p className="mb-6 text-justify align-middle text-sm text-gray-500 dark:text-gray-400">Lorem, ipsum dolor sit amet consectetur adipisicing elit. Eos minima a, numquam neque temporibus obcaecati eveniet sunt, beatae voluptatem at officiis atque dolorem? Eum possimus perspiciatis, quos fuga explicabo sunt.</p>
        <div className="mb-6 rounded-xl border border-gray-100 bg-gray-50 px-5 py-4 text-center dark:border-gray-700 dark:bg-gray-800/60">
          <p className="mb-1 text-xs text-gray-400">Kode Outlet Anda</p>
          <p className="text-xl font-bold tracking-widest text-brand-700 dark:text-brand-300">OTL-129-1231-23</p>
        </div>
        <div className="mb-6 rounded-xl border border-gray-100 bg-gray-50 px-5 py-4 text-left dark:border-gray-700 dark:bg-gray-800/60">
          <p className="mb-1 text-xs font-semibold text-gray-700 dark:text-gray-200">Verifikasi email Anda</p>
          <p className="text-xs leading-relaxed text-gray-500 dark:text-gray-400">
            Kami mengirim email verifikasi ke{' '}
            <span className="break-all font-medium text-gray-700 dark:text-gray-200">Lorem ipsum dolor,</span>. Klik tautan
            di email tersebut agar fitur lupa password dapat dipakai. Tidak menerima email? Periksa folder
            spam atau{' '}
            <Link to="/verify-email" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
              kirim ulang tautan verifikasi
            </Link>
            .
          </p>
        </div>
        <p className="mb-8 text-xs leading-relaxed text-gray-400">
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
    <motion.div
      variants={containerVariants}
      initial="initial"
      animate="animate"
      className="w-full space-y-6 p-4 md:p-6 lg:max-w-xl xl:max-w-2xl"
    >
      {/* Header */}
      <motion.div
        variants={itemVariants}
        className="mb-6"
      >
        <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Daftar Outlet</h2>
        <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">
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
                  i < step ? 'bg-emerald-500 text-white' :
                    i === step ? 'bg-brand-600 text-white ring-4 ring-brand-100 dark:ring-brand-500/30' :
                      'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500',
                )}
              >
                {i < step ? '✓' : i + 1}
              </div>
              <span className={cn('text-[10px] font-medium whitespace-nowrap transition-colors',
                i === step ? 'text-brand-600 dark:text-brand-400' : i < step ? 'text-emerald-500' : 'text-gray-400'
              )}>
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={cn('h-0.5 flex-1 mb-4 rounded-full transition-all duration-500',
                i < step ? 'bg-emerald-400' : 'bg-gray-200 dark:bg-gray-700'
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
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input label="Nama Depan" required placeholder="Budi" error={errors.first_name?.message} {...reg('first_name')} />
              <Input label="Nama Belakang" placeholder="Santoso" error={errors.last_name?.message} {...reg('last_name')} />
            </div>
            <p className="-mt-2 text-xs text-gray-400">Nama belakang boleh dikosongkan.</p>
            <div>
              <label htmlFor="tipe_toko" className="label label-required">Tipe Toko</label>
              <Controller
                name="tipe_toko"
                control={control}
                render={({ field }) => (
                  <SearchableSelect
                    id="tipe_toko"
                    placeholder="Cari atau pilih tipe toko"
                    options={TIPE_TOKO_SELECT_OPTIONS}
                    value={field.value ?? null}
                    // Dikosongkan jadi undefined (bukan '') agar pesan "Pilih tipe toko" yang tampil
                    onChange={(v) => field.onChange(v ?? undefined)}
                    onBlur={field.onBlur}
                    ref={field.ref}
                    error={errors.tipe_toko?.message}
                  />
                )}
              />
            </div>

            <Controller
              name="no_hp"
              control={control}
              render={({ field }) => (
                <div>
                  <label className="label label-required">No. HP / WhatsApp</label>
                  <div className="relative">
                    <span className="pointer-events-none absolute inset-y-0 left-0 flex select-none items-center border-r border-gray-200 pl-3 pr-2 text-sm font-medium text-gray-500 dark:border-gray-600 dark:text-gray-400">
                      +62
                    </span>
                    <input
                      ref={field.ref}
                      type="tel"
                      inputMode="numeric"
                      autoComplete="tel-national"
                      placeholder="858xxxx8238"
                      className={cn('input-base pl-14', errors.no_hp && 'input-error')}
                      value={field.value?.slice(2) ?? ''}
                      onChange={(e) => {
                        const local = normalizePhoneLocal(e.target.value)
                        field.onChange(local ? `62${local}` : '')
                      }}
                      onBlur={field.onBlur}
                    />
                  </div>
                  {errors.no_hp && <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{errors.no_hp.message}</p>}
                  <p className="mt-1 text-xs text-gray-400">Nomor HP/WhatsApp aktif, tanpa angka 0 di depan. Contoh: 81234567890</p>
                </div>
              )}
            />

            {/* Alamat OUTLET — form field, dikirim ke backend sebagai alamat_lengkap */}
            <div>
              <label className="label">Alamat Toko</label>
              <textarea
                rows={3}
                placeholder="Jl. Mawar No. 10, Kelurahan ..., Kecamatan ..., Kota ..."
                className={cn('input-base resize-none', errors.alamat_lengkap && 'input-error')}
                {...reg('alamat_lengkap')}
              />
              {errors.alamat_lengkap && (
                <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{errors.alamat_lengkap.message}</p>
              )}
              <p className="mt-1 text-xs text-gray-400">Opsional. Alamat lengkap lokasi toko Anda.</p>
            </div>
          </motion.div>
        )}

        {/* ── Step 1 ─────────────────────────────────────────────────────── */}
        {step === 1 && (
          <motion.div key="step1" variants={stepContentVariants} initial="initial" animate="animate" exit="exit" className="space-y-4">
            <div>
              <label htmlFor="distributor_id" className="label label-required">Distributor</label>
              {distError && !loadingDist ? (
                <div className="input-base border-red-200 bg-red-50 text-sm text-red-500 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">{distError}</div>
              ) : (
                <Controller
                  name="distributor_id"
                  control={control}
                  render={({ field }) => (
                    <SearchableSelect
                      id="distributor_id"
                      placeholder="Cari atau pilih distributor"
                      options={distributorOptions}
                      value={field.value || null}
                      onChange={(v) => {
                        const picked = distributors.find((d) => d.id === v)
                        setValue('distributor_id', v ?? '', { shouldValidate: true })
                        setPreviewAlamatDistributor(picked?.alamat_lengkap ?? '')  // ← local state, BUKAN setValue form
                      }}
                      onBlur={field.onBlur}
                      ref={field.ref}
                      loading={loadingDist}
                      error={errors.distributor_id?.message}
                    />
                  )}
                />
              )}
              <p className="mt-1 text-xs text-gray-400">Pilih distributor yang akan mengelola outlet Anda.</p>
            </div>

            {/* Alamat DISTRIBUTOR — readonly preview, BUKAN form field, tidak ikut payload submit */}
            <div>
              <label className="label">Alamat Distributor</label>
              <textarea
                rows={3}
                disabled
                readOnly
                value={previewAlamatDistributor}
                placeholder={selectedDistributorId ? 'Alamat tidak tersedia' : 'Otomatis terisi setelah memilih distributor'}
                className="input-base cursor-not-allowed resize-none bg-gray-50 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
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
                <button type="button" onClick={() => setShowPw(!showPw)} className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300" tabIndex={-1}>
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{errors.password.message}</p>}
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
                <button type="button" onClick={() => setShowPw2(!showPw2)} className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300" tabIndex={-1}>
                  {showPw2 ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.retype_password && <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{errors.retype_password.message}</p>}
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
            className="btn-secondary flex-1 btn-md lg:btn-lg flex items-center justify-center gap-1.5"
          >
            <ChevronLeft className="w-4 h-4" /> Kembali
          </button>
        )}
        {step < STEPS.length - 1 ? (
          <button type="button" onClick={handleNext} className="btn-primary flex-1 btn-md lg:btn-lg">
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
        <Link to="/login" className="font-medium text-brand-600 hover:underline dark:text-brand-400">Masuk di sini</Link>
      </motion.p>
    </motion.div>
  )
}