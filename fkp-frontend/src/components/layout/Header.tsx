import { Bell, Menu, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useCurrentUser } from '@/store/authStore'
import { useUnreadCount } from '@/hooks/useNotifications'
import { HeaderProps } from '@/types'

export function Header({ sidebarOpen, onToggleSidebar, pageTitle }: HeaderProps) {
  const user = useCurrentUser()
  const navigate = useNavigate()

  // Gunakan hook khusus unread count — endpoint ringan, tidak perlu fetch semua notifikasi
  const { data } = useUnreadCount()
  const unreadCount = data?.unread_count ?? 0

  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-sm border-b border-gray-100 shadow-sm">
      <div className="flex items-center justify-between h-16 px-4 md:px-6">
        <div className="flex items-center gap-4">
          <button onClick={onToggleSidebar}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors lg:hidden">
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          {pageTitle && <h1 className="text-lg font-semibold text-gray-900 hidden md:block">{pageTitle}</h1>}
        </div>

        <div className="flex items-center gap-2">
          {/* Bell dengan badge */}
          <button
            onClick={() => navigate('/notifications')}
            className="relative p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 min-w-[16px] h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </button>

          {/* Avatar */}
          <div className="flex items-center gap-2.5 pl-2">
            <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center shrink-0">
              <span className="text-white text-xs font-bold">{user?.nama?.charAt(0).toUpperCase()}</span>
            </div>
            <div className="hidden md:block text-right">
              <p className="text-sm font-medium text-gray-900 leading-tight">{user?.nama}</p>
              <p className="text-xs text-gray-400">{user?.role?.nama_role}</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}