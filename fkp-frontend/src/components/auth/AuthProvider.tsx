import { useEffect, useState } from 'react'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'
import { Center, Loader } from '@mantine/core'

interface AuthProviderProps {
  children: React.ReactNode
}

/**
 * Diletakkan di root app. Tugasnya satu:
 * verifikasi token yang ada di localStorage ke backend saat pertama load.
 * Jika token invalid/expired → clearAuth otomatis via axios interceptor.
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const { isAuthenticated, token, clearAuth, updateUser } = useAuthStore()
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    // Tidak ada token sama sekali → langsung selesai
    if (!token) {
      setIsChecking(false)
      return
    }

    // Ada token → validasi ke backend
    authApi
      .me()
      .then((res) => updateUser(res.user))
      .catch(() => clearAuth()) // token invalid/expired
      .finally(() => setIsChecking(false))
  }, []) // hanya saat pertama mount

  // Tampilkan loading spinner selama validasi
  // Ini mencegah flash ke /login sebelum validasi selesai
  if (isChecking) {
    return (
      <Center h="100vh">
        <Loader size="md" />
      </Center>
    )
  }

  return <>{children}</>
}