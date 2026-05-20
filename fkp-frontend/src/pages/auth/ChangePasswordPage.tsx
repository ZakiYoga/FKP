import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, Loader2, Lock } from 'lucide-react'
import { useState } from 'react'
import { useChangePassword } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

const schema = z
  .object({
    password_lama: z.string().min(1, 'Password lama wajib diisi'),
    password_baru: z.string().min(8, 'Password baru minimal 8 karakter'),
    password_baru_konfirmasi: z.string().min(1, 'Konfirmasi password wajib diisi'),
  })
  .refine((d) => d.password_baru === d.password_baru_konfirmasi, {
    message: 'Konfirmasi password tidak cocok',
    path: ['password_baru_konfirmasi'],
  })

type FormData = z.infer<typeof schema>

export function ChangePasswordPage() {
  const [show, setShow] = useState({ lama: false, baru: false, konfirmasi: false })
  const { mutate: changePassword, isPending } = useChangePassword()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = (data: FormData) => {
    changePassword(data, { onSuccess: () => reset() })
  }

  const toggle = (field: keyof typeof show) =>
    setShow((prev) => ({ ...prev, [field]: !prev[field] }))

  const PasswordField = ({
    id,
    label,
    field,
    showKey,
    error,
  }: {
    id: keyof FormData
    label: string
    field: keyof typeof show
    showKey: keyof typeof show
    error?: string
  }) => (
    <div>
      <label className="label">{label}</label>
      <div className="relative">
        <input
          type={show[showKey] ? 'text' : 'password'}
          className={cn('input-base pr-10', error && 'input-error')}
          {...register(id)}
        />
        <button
          type="button"
          onClick={() => toggle(field)}
          className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
          tabIndex={-1}
        >
          {show[showKey] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
      {error && <p className="mt-1.5 text-xs text-red-600">{error}</p>}
    </div>
  )

  return (
    <div className="max-w-lg mx-auto">
      <div className="card">
        <div className="card-header flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-brand-50 flex items-center justify-center">
            <Lock className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">Ubah Password</h2>
            <p className="text-sm text-gray-500">Pastikan password baru minimal 8 karakter</p>
          </div>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <PasswordField
              id="password_lama"
              label="Password Lama"
              field="lama"
              showKey="lama"
              error={errors.password_lama?.message}
            />
            <PasswordField
              id="password_baru"
              label="Password Baru"
              field="baru"
              showKey="baru"
              error={errors.password_baru?.message}
            />
            <PasswordField
              id="password_baru_konfirmasi"
              label="Konfirmasi Password Baru"
              field="konfirmasi"
              showKey="konfirmasi"
              error={errors.password_baru_konfirmasi?.message}
            />
            <div className="flex justify-end pt-2">
              <button type="submit" disabled={isPending} className="btn-primary">
                {isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Menyimpan...
                  </>
                ) : (
                  'Simpan Password Baru'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
