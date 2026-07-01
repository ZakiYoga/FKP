import { Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AppLayout } from '@/components/layout/AppLayout'
import { ChangePasswordPage } from '@/pages/auth/ChangePasswordPage'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { FkpListPage } from '@/pages/fkp/FkpListPage'
import { FkpCreatePage } from '@/pages/fkp/FkpCreatePage'
import { FkpDetailPage } from '@/pages/fkp/FkpDetailPage'
import { FkpEditPage } from '@/pages/fkp/FkpEditPage'
import { AreaPage } from '@/pages/areas/AreaPage'
import { DistributorPage } from '@/pages/distributors/DistributorPage'
import { OutletPage } from '@/pages/outlets/OutletPage'
import { ProductPage } from '@/pages/products/ProductPage'
import { UserPage } from '@/pages/users/UserPage'
import { HierarchyPage } from '@/pages/hierarchy/HierarchyPage'
import { NotificationPage } from '@/pages/notifications/NotificationPage'
import { NotFoundPage, ForbiddenPage } from '@/pages/ErrorPages'
import { RegisterOutletPage } from './pages/auth/RegisterOutletPage'
import { OutletRegistrationsPage } from './pages/outlets/OutletRegistrationPage'
import { LoginPage } from './pages/auth/LoginPage'
import { AuthLayout } from './components/layout/AuthLayout'
import { FkpTrackPage } from './pages/public/FkpTrackPage'
import { TestimoniPage } from './pages/testimoni/TestimoniPage'
import { PublicLayout } from './components/layout/PublicLayout'

export function AppRouter() {
  return (
    <Routes>
      {/* Publik */}'
      <Route element={<PublicLayout />}>
        <Route path="/403" element={<ForbiddenPage />} />
        <Route path="/track" element={<FkpTrackPage />} />
        <Route path="/track/:fkpId" element={<FkpTrackPage />} />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register/outlet" element={<RegisterOutletPage />} />
      </Route>

      {/* Protected */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          {/* Dashboard */}
          <Route path="/dashboard" element={<DashboardPage />} />

          {/* Auth */}
          <Route path="/change-password" element={<ChangePasswordPage />} />
          <Route path="/outlet-registrations" element={<OutletRegistrationsPage />} />

          {/* FKP */}
          <Route path="/fkp" element={<FkpListPage />} />
          <Route path="/fkp/baru" element={<FkpCreatePage />} />
          <Route path="/fkp/:id" element={<FkpDetailPage />} />
          <Route path="/fkp/:id/edit" element={<FkpEditPage />} />

          {/* Master Data */}
          <Route path="/areas" element={<AreaPage />} />
          <Route path="/distributors" element={<DistributorPage />} />
          <Route path="/outlets" element={<OutletPage />} />
          <Route path="/products" element={<ProductPage />} />

          {/* Tim & Hierarki */}
          <Route path="/hierarchy" element={<HierarchyPage />} />

          {/* User Management (SuperAdmin only) */}
          <Route element={<ProtectedRoute allowedRoles={['superadmin']} />}>
            <Route
              path="/users"
              element={<UserPage />}
            />
          </Route>

          {/* Notifikasi */}
          <Route path="/notifications" element={<NotificationPage />} />

          <Route element={<ProtectedRoute allowedRoles={['distributor', 'outlet', 'sc_spv']} />}>
            <Route path="/testimoni" element={<TestimoniPage />} />
          </Route>

        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}