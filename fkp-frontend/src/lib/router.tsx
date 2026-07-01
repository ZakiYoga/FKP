import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider } from '@/components/auth/AuthProvider'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { PublicOnlyRoute } from '@/components/auth/PublicOnlyRoute'
import { AppLayout } from '@/components/layout/AppLayout'
import { AuthLayout } from '@/components/layout/AuthLayout'
import { PublicLayout } from '@/components/layout/PublicLayout'
import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterOutletPage } from '@/pages/auth/RegisterOutletPage'
import { ChangePasswordPage } from '@/pages/auth/ChangePasswordPage'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { FkpListPage } from '@/pages/fkp/FkpListPage'
import { FkpCreatePage } from '@/pages/fkp/FkpCreatePage'
import { FkpDetailPage } from '@/pages/fkp/FkpDetailPage'
import { FkpEditPage } from '@/pages/fkp/FkpEditPage'
import { AreaPage } from '@/pages/areas/AreaPage'
import { DistributorPage } from '@/pages/distributors/DistributorPage'
import { OutletPage } from '@/pages/outlets/OutletPage'
import { OutletRegistrationsPage } from '@/pages/outlets/OutletRegistrationPage'
import { ProductPage } from '@/pages/products/ProductPage'
import { UserPage } from '@/pages/users/UserPage'
import { HierarchyPage } from '@/pages/hierarchy/HierarchyPage'
import { NotificationPage } from '@/pages/notifications/NotificationPage'
import { FkpTrackPage } from '@/pages/public/FkpTrackPage'
import { TestimoniPage } from '@/pages/testimoni/TestimoniPage'
import { PenerbitanFkpPage } from '@/pages/documents/PenerbitanFkpPage'
import { BaManualPage } from '@/pages/documents/BaManualPage'
import { NotFoundPage, ForbiddenPage } from '@/pages/ErrorPages'

// AuthProvider dibungkus di root layout agar punya akses ke router context
function RootLayout() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  )
}

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      // ── Root redirect ──────────────────────────────────────────────────────
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: '/', element: <Navigate to="/dashboard" replace /> },

      // ── Publik murni ───────────────────────────────────────────────────────
      {
        element: <PublicLayout />,
        children: [
          { path: '/403', element: <ForbiddenPage /> },
          { path: '/track', element: <FkpTrackPage /> },
          { path: '/track/:fkpId', element: <FkpTrackPage /> },
        ],
      },

      // ── Hanya untuk yang BELUM login ───────────────────────────────────────
      {
        element: <PublicOnlyRoute />,
        children: [
          {
            element: <AuthLayout />,
            children: [
              { path: '/login', element: <LoginPage /> },
              { path: '/register/outlet', element: <RegisterOutletPage /> },
            ],
          },
        ],
      },

      // ── Hanya untuk yang SUDAH login ───────────────────────────────────────
      {
        element: <ProtectedRoute />,
        children: [
          {
            element: <AppLayout />,
            children: [
              { path: '/dashboard', element: <DashboardPage /> },
              { path: '/change-password', element: <ChangePasswordPage /> },
              { path: '/outlet-registrations', element: <OutletRegistrationsPage /> },

              // FKP
              { path: '/fkp', element: <FkpListPage /> },
              { path: '/fkp/baru', element: <FkpCreatePage /> },
              { path: '/fkp/:id', element: <FkpDetailPage /> },
              { path: '/fkp/:id/edit', element: <FkpEditPage /> },

              // Master Data
              { path: '/areas', element: <AreaPage /> },
              { path: '/distributors', element: <DistributorPage /> },
              { path: '/outlets', element: <OutletPage /> },
              { path: '/products', element: <ProductPage /> },

              // Tim & Hierarki
              { path: '/hierarchy', element: <HierarchyPage /> },

              // Notifikasi
              { path: '/notifications', element: <NotificationPage /> },

              // Penerbitan FKP
              { path: '/penerbitan-fkp', element: <PenerbitanFkpPage /> },

              // Superadmin only
              {
                element: <ProtectedRoute allowedRoles={['superadmin']} />,
                children: [
                  { path: '/users', element: <UserPage /> },
                ],
              },

              // Role tertentu
              {
                element: <ProtectedRoute allowedRoles={['distributor', 'outlet', 'sc_spv']} />,
                children: [
                  { path: '/testimoni', element: <TestimoniPage /> },
                ],
              },

              {
                element: <ProtectedRoute allowedRoles={['admin_ho', 'superadmin', 'qc', 'rsm', 'direktur']} />,
                children: [
                  { path: '/penerbitan-fkp/manual', element: <BaManualPage /> },
                ],
              },
            ],
          },
        ],
      },

      // ── 404 ───────────────────────────────────────────────────────────────
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])