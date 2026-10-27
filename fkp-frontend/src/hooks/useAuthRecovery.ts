import { useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import { authApi } from '@/api/auth'
import { PROFILE_ME_KEY } from '@/hooks/useProfile'
import { getErrorMessage } from '@/lib/utils'

const ME_QUERY_KEY = ['auth', 'me'] as const

// Invalidate hanya me-refetch query yang sedang aktif, jadi aman dipanggil
// dari halaman publik saat user belum login.
const refreshUser = (qc: QueryClient) => {
  qc.invalidateQueries({ queryKey: ME_QUERY_KEY })
  qc.invalidateQueries({ queryKey: PROFILE_ME_KEY })
}

const notifyError = (error: unknown) =>
  notifications.show({ message: getErrorMessage(error), color: 'red' })

const notifyOk = (res: { message: string }) =>
  notifications.show({ message: res.message, color: 'green' })

/** Respons backend selalu sama (anti user-enumeration), jadi tanpa notifikasi sukses. */
export function useForgotPassword() {
  return useMutation({
    mutationFn: (email: string) => authApi.forgotPassword(email),
    onError: notifyError,
  })
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (data: {
      token: string
      password_baru: string
      password_baru_konfirmasi: string
    }) => authApi.resetPassword(data),
    onError: notifyError,
  })
}

/** Publik. Error tidak dinotifikasi karena halaman verifikasi menampilkannya sendiri. */
export function useVerifyEmail() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (token: string) => authApi.verifyEmail(token),
    onSuccess: () => refreshUser(qc),
  })
}

export function useResendVerificationPublic() {
  return useMutation({
    mutationFn: (email: string) => authApi.resendVerificationPublic(email),
    onSuccess: notifyOk,
    onError: notifyError,
  })
}

export function useSendVerification() {
  return useMutation({
    mutationFn: () => authApi.sendVerification(),
    onSuccess: notifyOk,
    onError: notifyError,
  })
}

export function useChangeEmail() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { email_baru: string; password: string }) => authApi.changeEmail(data),
    onSuccess: (res) => {
      notifyOk(res)
      refreshUser(qc)
    },
    onError: notifyError,
  })
}