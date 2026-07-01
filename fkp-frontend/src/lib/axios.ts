import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 detik
})

// ─── REQUEST INTERCEPTOR ──────────────────────────────────────────────────────
// Sisipkan token di setiap request jika ada
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('fkp_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ─── RESPONSE INTERCEPTOR ─────────────────────────────────────────────────────
// Handle error global
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginEndpoint = error.config?.url?.includes('/auth/login')

    if (error.response?.status === 401 && !isLoginEndpoint) {
      // Token expired atau invalid → bersihkan storage dan redirect ke login
      localStorage.removeItem('fkp_token')
      localStorage.removeItem('fkp_user')
      // Hanya redirect jika bukan di halaman login
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api
