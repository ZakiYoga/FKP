import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import { authApi } from '@/api/auth'
import { notifications } from '@mantine/notifications'
import { useAuthStore } from '@/store/authStore'
import { getErrorMessage } from '@/lib/utils'
import { clearAuthenticatedImageCache } from '@/hooks/useAuthenticatedImage' // ← BARU
import type { LoginRequest } from '@/types'

export function useLogin() {
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()

  return useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (res) => {
      setAuth(res.user, res.access_token)
      notifications.show({
        message: `Selamat datang, ${res.user.nama}!`,
        color: 'green',
      })

      // Redirect ke halaman yang ingin dituju sebelumnya, atau dashboard
      const from = (location.state as { from?: Location })?.from?.pathname ?? '/dashboard'
      navigate(from, { replace: true })
    },
    onError: (error) => {
      notifications.show({
        message: getErrorMessage(error),
        color: 'red',
      })
    },
  })
}

export function useLogout() {
  const { clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      // Selalu bersihkan state meskipun request gagal
      clearAuth()
      queryClient.clear()
      // [BARU] Bersihkan blob URL gambar attachment milik user ini —
      // supaya tidak nyangkut di memori & tidak ter-reuse kalau user lain
      // login di browser/device yang sama. Lihat useAuthenticatedImage.ts.
      clearAuthenticatedImageCache()
      navigate('/login', { replace: true })
      notifications.show({
        message: 'Berhasil logout.',
        color: 'green',
      })
    },
  })
}

export function useMe() {
  const { isAuthenticated, updateUser } = useAuthStore()

  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const res = await authApi.me()
      updateUser(res.user)
      return res.user
    },
    enabled: isAuthenticated,
    staleTime: 1 * 60 * 1000,
    retry: false,
    throwOnError: false,
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: () => {
      notifications.show({
        message: 'Password berhasil diubah.',
        color: 'green',
      })
    },
    onError: (error) => {
      notifications.show({
        message: getErrorMessage(error),
        color: 'red',
      })
    },
  })
}