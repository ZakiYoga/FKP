// src/layouts/AuthLayout.tsx

import { Outlet } from 'react-router-dom'
import { LeftPanel } from './LeftPanelAuth'
import { ThemeToggle } from '@/components/ThemeToggle' // sesuaikan path dengan lokasi ThemeToggle Anda

function RightPanel() {
  return (
    <div className="relative flex min-h-screen flex-1 flex-col items-center justify-center overflow-y-auto bg-gray-100 dark:bg-gray-900">
      {/* Toggle tema: fixed agar tetap di pojok kanan atas walau konten di-scroll */}
      <div className="flex w-full mb-auto justify-end space-y-6 py-4 md:py-6 lg:max-w-xl xl:max-w-2xl">
        <ThemeToggle className='border-gray-800 text-gray-800 dark:border-gray-300 dark:text-gray-300 p-2 hover:bg-brand-50 dark:hover:bg-gray-800' size={36}/>
      </div>
      <div className="flex w-full justify-center items-center h-full">
        <Outlet />
      </div>
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