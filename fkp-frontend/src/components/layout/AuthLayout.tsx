// src/layouts/AuthLayout.tsx

import { Outlet } from 'react-router-dom'
import { LeftPanel } from './LeftPanelAuth'

function RightPanel() {
  return (
    <div className={`flex-1 flex flex-col items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900 overflow-y-auto`}>
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