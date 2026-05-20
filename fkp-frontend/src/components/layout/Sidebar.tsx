import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, FileText, Package, MapPin, Building2,
  Store, Users, ShieldCheck, LogOut, ChevronRight,
  GitBranch, Settings, Bell,
  ClipboardList,
} from 'lucide-react'
import { useKodeRole, useCurrentUser } from '@/store/authStore'
import { useLogout } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

interface NavItem {
  label: string
  href: string
  icon: React.ElementType
  roles?: string[]
  badge?: number
}

const NAV_ITEMS: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    label: 'FKP',
    href: '/fkp',
    icon: FileText,
  },
  {
    label: 'Outlet',
    href: '/outlets',
    icon: Store,
    roles: ['superadmin', 'admin_ho', 'apsm', 'sc_spv', 'distributor'],
  },
  {
    label: 'Distributor',
    href: '/distributors',
    icon: Building2,
    roles: ['superadmin', 'admin_ho', 'apsm', 'sc_spv', 'rsm', 'direktur', 'qc'],
  },
  {
    label: 'Area',
    href: '/areas',
    icon: MapPin,
    roles: ['superadmin', 'admin_ho', 'rsm', 'direktur'],
  },
  {
    label: 'Produk',
    href: '/products',
    icon: Package,
    roles: ['superadmin', 'admin_ho', 'qc'],
  },
  {
    label: 'Hierarki Tim',
    href: '/hierarchy',
    icon: GitBranch,
    roles: ['superadmin', 'admin_ho', 'rsm', 'direktur'],
  },
  {
    label: 'Pengguna',
    href: '/users',
    icon: Users,
    roles: ['superadmin'],
  },
  {
    label: 'Registrasi Outlet',
    href: '/outlet-registrations',
    icon: ClipboardList,
    roles: ['superadmin', 'admin_ho', 'apsm', 'sc_spv', 'distributor']
  },
  {
    label: 'Notifikasi',
    href: '/notifications',
    icon: Bell,
  },
  {
    label: 'Ubah Password',
    href: '/change-password',
    icon: Settings,
  },
]

export function Sidebar() {
  const kodeRole = useKodeRole()
  const user = useCurrentUser()
  const { mutate: logout, isPending } = useLogout()

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || item.roles.includes(kodeRole)
  )

  return (
    <aside className="flex flex-col w-64 min-h-screen bg-brand-950 border-r border-brand-900">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-brand-900">
        <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center shrink-0">
          <ShieldCheck className="w-5 h-5 text-white" />
        </div>
        <div className="min-w-0">
          <p className="text-white font-bold text-sm leading-tight">FKP SaktiFood</p>
          <p className="text-brand-400 text-xs truncate">Sistem Keluhan Produk</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto scrollbar-thin">
        {visibleItems.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 group',
                isActive
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-brand-300 hover:bg-brand-900 hover:text-white'
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={cn(
                    'w-4.5 h-4.5 shrink-0 transition-colors',
                    isActive ? 'text-white' : 'text-brand-400 group-hover:text-white'
                  )}
                />
                <span className="flex-1 truncate">{item.label}</span>
                {!isActive && (
                  <ChevronRight className="w-3.5 h-3.5 text-brand-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User info + logout */}
      <div className="px-3 py-4 border-t border-brand-900 space-y-2">
        <div className="px-3 py-2.5 rounded-lg bg-brand-900/50">
          <p className="text-white text-sm font-medium truncate">{user?.nama}</p>
          <p className="text-brand-400 text-xs truncate">{user?.role?.nama_role}</p>
        </div>
        <button
          onClick={() => logout()}
          disabled={isPending}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-brand-300 hover:bg-red-900/30 hover:text-red-400 transition-all duration-150 disabled:opacity-50"
        >
          <LogOut className="w-4 h-4 shrink-0" />
          {isPending ? 'Keluar...' : 'Keluar'}
        </button>
      </div>
    </aside>
  )
}
