import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'
import { getErrorMessage } from '@/lib/utils'
import type { LoginRequest } from '@/types'

export function useLogin() {
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (res) => {
      setAuth(res.user, res.access_token)
      toast.success(`Selamat datang, ${res.user.nama}!`)
      navigate('/dashboard', { replace: true })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error))
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
      navigate('/login', { replace: true })
      toast.success('Berhasil logout.')
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
    staleTime: 5 * 60 * 1000,  // 5 menit
    retry: false,
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: () => {
      toast.success('Password berhasil diubah.')
    },
    onError: (error) => {
      toast.error(getErrorMessage(error))
    },
  })
}
