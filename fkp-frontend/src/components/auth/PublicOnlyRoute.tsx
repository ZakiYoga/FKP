import { Navigate, Outlet } from 'react-router-dom'
import { useIsAuthenticated } from '@/store/authStore'

/**
 * Route yang hanya boleh diakses oleh user yang BELUM login.
 * Jika sudah login → redirect ke dashboard.
 * Pakai untuk: /login, /register/outlet
 */
export function PublicOnlyRoute() {
  const isAuthenticated = useIsAuthenticated()

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}