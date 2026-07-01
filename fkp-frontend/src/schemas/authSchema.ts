import { z } from 'zod'

export const changePasswordSchema = z
  .object({
    password_lama: z.string().min(1, 'Password lama wajib diisi'),
    password_baru: z.string().min(8, 'Password baru minimal 8 karakter'),
    password_baru_konfirmasi: z.string().min(1, 'Konfirmasi password wajib diisi'),
  })
  .refine((d) => d.password_baru === d.password_baru_konfirmasi, {
    message: 'Konfirmasi password tidak cocok',
    path: ['password_baru_konfirmasi'],
  })

export type ChangePasswordFormData = z.infer<typeof changePasswordSchema>