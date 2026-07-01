import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserMe } from '@/types'

interface AuthState {
  user: UserMe | null
  token: string | null
  isAuthenticated: boolean
  setAuth: (user: UserMe, token: string) => void
  clearAuth: () => void
  updateUser: (user: UserMe) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      setAuth: (user, token) => {
        set({ user, token, isAuthenticated: true })
      },

      clearAuth: () => {
        set({ user: null, token: null, isAuthenticated: false })
        // Hapus key persist Zustand, bukan key yang tidak ada
        localStorage.removeItem('fkp_auth')
      },

      updateUser: (user) => set({ user }),
    }),
    {
      name: 'fkp_auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)

export const useCurrentUser = () => useAuthStore((s) => s.user)
export const useKodeRole = () => useAuthStore((s) => s.user?.role?.kode_role ?? '')
export const useIsAuthenticated = () => useAuthStore((s) => s.isAuthenticated)