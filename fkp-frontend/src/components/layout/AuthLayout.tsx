import { Outlet } from 'react-router-dom'
import { LeftPanel } from './LeftPanelAuth'

function RightPanel() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center min-h-screen bg-gray-100 rounded-s-2xl z-10 -ml-4 overflow-y-auto">
          <Outlet />
    </div>
  )
}
    
// ─── Auth Layout ──────────────────────────────────────────────────────────────

export function AuthLayout() {

  return (
    <div className="flex min-h-screen">
      <LeftPanel />
      <RightPanel />
    </div>
  )
}