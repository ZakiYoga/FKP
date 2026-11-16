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
import { ROLE_PENANGAN_PCS } from '@/constants/fkpPcs'
import { NotFoundPage, ForbiddenPage } from '@/pages/ErrorPages'
import { FkpPcsPage } from '@/pages/apsm/FkpPcsPage'
import LabQcPage from '@/pages/lab-qc/LabQcPage'
import Profile from '@/pages/profile/Profile'
import { ForgotPasswordPage } from '@/pages/auth/ForgotPasswordPage'
import { ResetPasswordPage } from '@/pages/auth/ResetPasswordPage'
import { VerifyEmailPage } from '@/pages/auth/VerifyEmailPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { SuratJalanPage } from '@/pages/warehouse/SuratJalanPage'
import { SampleMasukPage } from '@/pages/SampleMasukPage'
import { LAB_QC_VIEW_ROLES } from '@/constants/labQc'
import LabQcWorkspacePage from '@/pages/lab-qc/LabQcWorkspacePage'
import type { RouteHandle } from '@/lib/route-handle'

// ── Breadcrumb helpers ──────────────────────────────────────────────────────
const crumb = (...crumbs: NonNullable<RouteHandle['crumbs']>[]) => crumbs
const FKP_ROOT = { title: 'Formulir Keluhan Produk', href: '/fkp' }
const QC_ROOT = { title: 'Investigasi QC', href: '/investigasi-qc' }

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

      // ── Publik ─────────────────────────────────────────────────────────────
      {
        element: <PublicLayout />,
        children: [
          { path: '/403', element: <ForbiddenPage /> },
          { path: '/track', element: <FkpTrackPage /> },
          { path: '/track/:fkpId', element: <FkpTrackPage /> },
        ],
      },
      {
        element: <AuthLayout />,
        children: [
          { path: '/reset-password', element: <ResetPasswordPage /> },
          { path: '/verify-email', element: <VerifyEmailPage /> },
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
              { path: '/forgot-password', element: <ForgotPasswordPage /> },
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
              // Dashboard (crumbs kosong → header hanya menampilkan ikon home)
              {
                path: '/dashboard',
                element: <DashboardPage />,
                handle: { crumbs: [] } satisfies RouteHandle,
              },

              // Profile
              {
                path: '/profile',
                element: <Profile />,
                handle: { crumbs: [{ title: 'Profil' }] } satisfies RouteHandle,
              },
              {
                path: '/change-password',
                element: <ChangePasswordPage />,
                handle: { crumbs: [{ title: 'Ubah Password' }] } satisfies RouteHandle,
              },

              // FKP
              {
                path: '/fkp',
                element: <FkpListPage />,
                handle: { crumbs: [{ title: FKP_ROOT.title }] } satisfies RouteHandle,
              },
              {
                path: '/fkp/baru',
                element: <FkpCreatePage />,
                handle: { crumbs: [FKP_ROOT, { title: 'Buat FKP' }] } satisfies RouteHandle,
              },
              {
                path: '/fkp/:id',
                element: <FkpDetailPage />,
                handle: { crumbs: [FKP_ROOT, { title: 'Detail FKP' }] } satisfies RouteHandle,
              },
              {
                path: '/fkp/:id/edit',
                element: <FkpEditPage />,
                handle: {
                  crumbs: (params) => [
                    FKP_ROOT,
                    { title: 'Detail FKP', href: `/fkp/${params.id}` },
                    { title: 'Edit' },
                  ],
                } satisfies RouteHandle,
              },

              // Master Data
              {
                path: '/areas',
                element: <AreaPage />,
                handle: { crumbs: [{ title: 'Manajemen Area' }] } satisfies RouteHandle,
              },
              {
                path: '/distributors',
                element: <DistributorPage />,
                handle: { crumbs: [{ title: 'Manajemen Distributor' }] } satisfies RouteHandle,
              },
              {
                path: '/outlets',
                element: <OutletPage />,
                handle: { crumbs: [{ title: 'Manajemen Outlet' }] } satisfies RouteHandle,
              },
              {
                path: '/outlet-registrations',
                element: <OutletRegistrationsPage />,
                handle: { crumbs: [{ title: 'Registrasi Outlet' }] } satisfies RouteHandle,
              },
              {
                path: '/products',
                element: <ProductPage />,
                handle: { crumbs: [{ title: 'Katalog Produk' }] } satisfies RouteHandle,
              },

              // Lab Investigasi QC
              {
                element: <ProtectedRoute allowedRoles={LAB_QC_VIEW_ROLES} />,
                children: [
                  {
                    path: '/investigasi-qc',
                    element: <LabQcPage />,
                    handle: { crumbs: [{ title: QC_ROOT.title }] } satisfies RouteHandle,
                  },
                  {
                    path: '/investigasi-qc/:fkpId',
                    element: <LabQcWorkspacePage />,
                    handle: { crumbs: [QC_ROOT, { title: 'Workspace' }] } satisfies RouteHandle,
                  },
                ],
              },

              // Tim & Hierarki
              {
                path: '/hierarchy',
                element: <HierarchyPage />,
                handle: { crumbs: [{ title: 'Hierarki Tim' }] } satisfies RouteHandle,
              },

              // Notifikasi
              {
                path: '/notifications',
                element: <NotificationPage />,
                handle: { crumbs: [{ title: 'Notifikasi' }] } satisfies RouteHandle,
              },

              // Penerbitan FKP
              {
                path: '/penerbitan-fkp',
                element: <PenerbitanFkpPage />,
                handle: { crumbs: [{ title: 'Penerbitan FKP' }] } satisfies RouteHandle,
              },

              // Superadmin only
              {
                element: <ProtectedRoute allowedRoles={['superadmin']} />,
                children: [
                  {
                    path: '/users',
                    element: <UserPage />,
                    handle: { crumbs: [{ title: 'Manajemen Pengguna' }] } satisfies RouteHandle,
                  },
                ],
              },

              // Role tertentu
              {
                element: <ProtectedRoute allowedRoles={['distributor', 'outlet', 'sc_spv']} />,
                children: [
                  {
                    path: '/testimoni',
                    element: <TestimoniPage />,
                    handle: { crumbs: [{ title: 'Testimoni' }] } satisfies RouteHandle,
                  },
                ],
              },

              {
                element: <ProtectedRoute allowedRoles={['admin_ho', 'superadmin', 'qc', 'rsm', 'direktur']} />,
                children: [
                  {
                    path: '/buat-berita-acara',
                    element: <BaManualPage />,
                    handle: { crumbs: [{ title: 'Buat Berita Acara' }] } satisfies RouteHandle,
                  },
                ],
              },

              // Sample Masuk (permission BE sample.view_all: warehouse, qc, admin_ho; superadmin bypass)
              {
                element: <ProtectedRoute allowedRoles={['warehouse', 'qc', 'admin_ho', 'superadmin']} />,
                children: [
                  {
                    path: '/sample-masuk',
                    element: <SampleMasukPage />,
                    handle: { crumbs: [{ title: 'Sample Masuk' }] } satisfies RouteHandle,
                  },
                ],
              },

              // Surat Jalan (warehouse; admin_ho/rsm/direktur hanya melihat + admin_ho konfirmasi diterima)
              {
                element: <ProtectedRoute allowedRoles={['warehouse', 'admin_ho', 'rsm', 'direktur', 'superadmin']} />,
                children: [
                  {
                    path: '/surat-jalan',
                    element: <SuratJalanPage />,
                    handle: { crumbs: [{ title: 'Surat Jalan' }] } satisfies RouteHandle,
                  },
                ],
              },

              // Penanganan FKP pcs oleh APSM (daftar role dari satu konstanta)
              {
                element: <ProtectedRoute allowedRoles={ROLE_PENANGAN_PCS} />,
                children: [
                  {
                    path: '/apsm/fkp-pcs',
                    element: <FkpPcsPage />,
                    handle: { crumbs: [{ title: 'Penanganan FKP Pcs' }] } satisfies RouteHandle,
                  },
                ],
              },
            ],
          },
        ],
      },

      // ── 404 ────────────────────────────────────────────────────────────────
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])