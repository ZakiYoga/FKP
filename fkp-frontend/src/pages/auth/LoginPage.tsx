import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useLogin } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'
import { Link } from 'react-router-dom'
import { notifications } from '@mantine/notifications'

const loginSchema = z.object({
  email: z.string().email('Format email tidak valid'),
  password: z.string().min(6, 'Password minimal 6 karakter'),
})

type LoginForm = z.infer<typeof loginSchema>

// ─── Animation Variants ───────────────────────────────────────────────────────

const containerVariants = {
  animate: {
    transition: { staggerChildren: 0.08, delayChildren: 0.1 },
  },
}

const itemVariants = {
  initial: { opacity: 0, y: 16 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4 },
  },
}

// ─── Component ────────────────────────────────────────────────────────────────

export function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const { mutate: login, isPending } = useLogin()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = (data: LoginForm) => {
    login(data)
  }

  useEffect(() => {
    const notice = sessionStorage.getItem('auth_notice')
    if (notice) {
      sessionStorage.removeItem('auth_notice')
      notifications.show({ message: notice, color: 'yellow' })
    }
  }, [])

  return (
    <motion.div
      variants={containerVariants}
      initial="initial"
      animate="animate"
      className="w-full space-y-6 p-6 md:p-12 lg:max-w-xl xl:max-w-2xl"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="mb-8">
        <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
          Selamat datang
        </h2>
        <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">
          Masuk menggunakan akun Anda untuk melanjutkan.
        </p>
      </motion.div>

      <motion.form
        variants={itemVariants}
        onSubmit={handleSubmit(onSubmit)}
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
            placeholder="email@example.com"
            className={cn('input-base', errors.email && 'input-error')}
            {...register('email')}
          />
          {errors.email && (
            <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{errors.email.message}</p>
          )}
        </div>

        {/* Password */}
        <div>
          <div className="flex items-center justify-between">
            <label htmlFor="password" className="label">
              Password
            </label>
            <Link
              to="/forgot-password"
              className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
            >
              Lupa password?
            </Link>
          </div>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              placeholder="Masukkan password"
              className={cn('input-base pr-10', errors.password && 'input-error')}
              {...register('password')}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 transition-colors hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
              tabIndex={-1}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.password && (
            <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{errors.password.message}</p>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={isPending}
          className="btn-primary w-full btn-md lg:btn-lg"
        >
          {isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Memproses...
            </>
          ) : (
            'Masuk'
          )}
        </button>
      </motion.form>

      {/* Divider */}
      <motion.div variants={itemVariants} className="mt-6 text-center text-xs text-gray-400">
        Belum punya akun?&nbsp;
        <Link
          to="/register/outlet"
          className="font-medium text-brand-600 hover:underline dark:text-brand-400"
        >
          Daftar sekarang
        </Link>
      </motion.div>
    </motion.div>
  )
}