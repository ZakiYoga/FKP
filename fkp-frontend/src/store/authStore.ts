import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserMe } from '@/types'

interface AuthState {
  user: UserMe | null
  token: string | null
  isAuthenticated: boolean

  // Actions
  setAuth: (user: UserMe, token: string) => void
  clearAuth: () => void
  updateUser: (user: UserMe) => void
}

/**
 * Auth store dengan persist middleware.
 * Token dan user disimpan di localStorage otomatis.
 * Key: 'fkp_token' dan 'fkp_user' (sesuai dengan axios interceptor).
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      setAuth: (user, token) => {
        // Simpan token di localStorage agar axios interceptor bisa baca
        localStorage.setItem('fkp_token', token)
        set({ user, token, isAuthenticated: true })
      },

      clearAuth: () => {
        localStorage.removeItem('fkp_token')
        localStorage.removeItem('fkp_user')
        set({ user: null, token: null, isAuthenticated: false })
      },

      updateUser: (user) => set({ user }),
    }),
    {
      name: 'fkp_auth',        // key di localStorage
      partialize: (state) => ({
        // Hanya persist user dan token, bukan function
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)

// ─── SELECTOR HELPERS ─────────────────────────────────────────────────────────
export const useCurrentUser = () => useAuthStore((s) => s.user)
export const useKodeRole = () => useAuthStore((s) => s.user?.role?.kode_role ?? '')
export const useIsAuthenticated = () => useAuthStore((s) => s.isAuthenticated)
