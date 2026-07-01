import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useIsAuthenticated, useKodeRole } from '@/store/authStore'

interface ProtectedRouteProps {
  allowedRoles?: string[]
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const isAuthenticated = useIsAuthenticated()
  const kodeRole = useKodeRole()
  const location = useLocation()

  if (!isAuthenticated) {
    // Simpan halaman yang ingin dituju, agar setelah login bisa redirect balik
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(kodeRole)) {
    return <Navigate to="/403" replace />
  }

  return <Outlet />
}