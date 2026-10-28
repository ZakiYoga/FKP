// src/layouts/AuthLayout.tsx

import { Outlet } from 'react-router-dom'
import { LeftPanel } from './LeftPanelAuth'
import { ThemeToggle } from '@/components/ThemeToggle' // sesuaikan path dengan lokasi ThemeToggle Anda

function RightPanel() {
  return (
    <div className="relative flex min-h-screen flex-1 flex-col items-center justify-center overflow-y-auto bg-gray-100 dark:bg-gray-900">
      {/* Toggle tema: fixed agar tetap di pojok kanan atas walau konten di-scroll */}
      <div className="fixed right-4 top-4 z-10">
        <ThemeToggle />
      </div>
      <Outlet />
    </div>
  )
}

export function AuthLayout() {
  return (
    <div className="flex min-h-screen bg-gray-950">
      <LeftPanel />
      <RightPanel />
    </div>
  )
}