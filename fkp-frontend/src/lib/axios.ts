import axios from 'axios'
import { useAuthStore } from '@/store/authStore'
import { queryClient } from '@/lib/queryClient'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// ─── REQUEST INTERCEPTOR ──────────────────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    // Baca token dari Zustand store, bukan langsung localStorage
    const token = useAuthStore.getState().token
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error),
)

// Endpoint auth publik: 401 dari sini tidak boleh memicu logout + redirect ke /login
const PUBLIC_AUTH_PATHS = [
  '/auth/login',
  '/auth/forgot-password',
  '/auth/reset-password',
  '/auth/email/verify',
  '/auth/email/resend-verification',
]

// ─── RESPONSE INTERCEPTOR ─────────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isPublicAuthEndpoint = PUBLIC_AUTH_PATHS.some((p) =>
      error.config?.url?.includes(p),
    )

    if (error.response?.status === 401 && !isPublicAuthEndpoint) {
      const detail = error.response?.data?.detail
      if (typeof detail === 'string' && detail.includes('password telah diubah')) {
        sessionStorage.setItem('auth_notice', detail)
      }
      useAuthStore.getState().clearAuth()
      queryClient.clear()

      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  },
)

export default api