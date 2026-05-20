import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useIsAuthenticated, useKodeRole } from '@/store/authStore'

interface ProtectedRouteProps {
  allowedRoles?: string[]
}

/**
 * Komponen guard untuk route yang membutuhkan autentikasi.
 *
 * Cara pakai:
 *   <Route element={<ProtectedRoute />}>
 *     <Route path="/dashboard" element={<Dashboard />} />
 *   </Route>
 *
 *   // Dengan role restriction:
 *   <Route element={<ProtectedRoute allowedRoles={['qc', 'superadmin']} />}>
 *     <Route path="/investigasi" element={<Investigasi />} />
 *   </Route>
 */
export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const isAuthenticated = useIsAuthenticated()
  const kodeRole = useKodeRole()
  const location = useLocation()

  // Belum login → redirect ke halaman login
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Login tapi role tidak diizinkan → redirect ke 403
  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(kodeRole)) {
    return <Navigate to="/403" replace />
  }

  return <Outlet />
}
