import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

// Map path → page title untuk header
const PAGE_TITLES: Record<string, string> = {
  '/dashboard':      'Dashboard',
  '/fkp':            'Formulir Keluhan Produk',
  '/outlets':        'Manajemen Outlet',
  '/outlet-registrations': 'Registrasi Outlet',
  '/distributors':   'Manajemen Distributor',
  '/areas':          'Manajemen Area',
  '/products':       'Katalog Produk',
  '/hierarchy':      'Hierarki Tim Sales',
  '/users':          'Manajemen Pengguna',
  '/notifications':  'Notifikasi',
  '/change-password':'Ubah Password',
}

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  // Ambil title dari path saat ini
  const currentTitle = PAGE_TITLES[location.pathname] ?? 'FKP SaktiFood'

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* ── Sidebar desktop (selalu tampil di lg+) ─────────── */}
      <div className="hidden lg:flex lg:shrink-0">
        <Sidebar />
      </div>

      {/* ── Sidebar mobile (overlay) ────────────────────────── */}
      {sidebarOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden animate-fade-in"
            onClick={() => setSidebarOpen(false)}
          />
          {/* Sidebar panel */}
          <div className="fixed inset-y-0 left-0 z-50 lg:hidden animate-slide-up">
            <Sidebar />
          </div>
        </>
      )}

      {/* ── Main content ─────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0">
        <Header
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          pageTitle={currentTitle}
        />

        <main className="flex-1 p-4 md:p-6 lg:p-8 max-w-(--breakpoint-2xl) mx-auto w-full">
          <Outlet />
        </main>

        {/* Footer */}
        <footer className="px-6 py-3 border-t border-gray-100 text-center">
          <p className="text-xs text-gray-400">
            FKP SaktiFood v1.0.0 — Sistem Formulir Keluhan Produk
          </p>
        </footer>
      </div>
    </div>
  )
}
