import { useNavigate, useLocation } from 'react-router-dom'
import { LogOut, PanelLeftOpen, PanelRightOpen } from 'lucide-react'
import { Tooltip } from '@mantine/core'
import { useKodeRole, useCurrentUser } from '@/store/authStore'
import { useLogout } from '@/hooks/useAuth'
import { UserMe } from '@/types'
import { NavItem } from '@/types/navItems'
import { NAV_ITEMS } from '@/data/NavItems'
import { UserAvatar } from '../UserAvatar'

const SKELETON_USER: UserMe = {
  id: '',
  first_name: 'Loading...', last_name: null, full_name: 'Loading...',
  gender: null, avatar_path: null,
  email: '', no_telepon: null,
  is_active: true, last_login: null, created_at: '',
  role: { id: '', kode_role: '', nama_role: 'Loading...' },
  email_verified_at: null,
}

// Sesuaikan dengan route halaman profil di aplikasi Anda
const PROFILE_HREF = '/profile'

// ─── Single nav item ──────────────────────────────────────────────────────────
function NavItem_({
  item, isActive, collapsed, onClick,
}: {
  item: NavItem
  isActive: boolean
  collapsed: boolean
  onClick: () => void
}) {
  const Icon = item.icon

  return (
    <Tooltip
      label={item.label}
      position="right"
      withArrow
      offset={14}
      disabled={!collapsed}
      transitionProps={{ duration: 80 }}
    >
      <button
        type="button"
        onClick={onClick}
        aria-label={item.label}
        className={[
          'flex h-10 w-full items-center overflow-hidden whitespace-nowrap rounded-lg text-[0.8125rem] transition-colors duration-100',
          collapsed ? 'justify-center gap-0 p-0' : 'justify-start gap-2.5 px-2.5',
          isActive
            ? 'bg-linear-to-tl from-[#22396F] to-blue-500/60 font-semibold text-white'
            : 'bg-transparent font-normal text-slate-400 hover:bg-white/6 hover:text-white',
        ].join(' ')}
      >
        <Icon size={collapsed ? 17 : 15} className="shrink-0" />
        {!collapsed && <span className="truncate">{item.label}</span>}
      </button>
    </Tooltip>
  )
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────
interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
  isMobile?: boolean
}

export function Sidebar({ collapsed, onToggle, isMobile = false }: SidebarProps) {
  const kodeRole = useKodeRole()
  const user = useCurrentUser()
  const { mutate: logout, isPending } = useLogout()
  const navigate = useNavigate()
  const location = useLocation()

  const resolvedUser = user ?? SKELETON_USER
  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || item.roles.includes(kodeRole)
  )

  const toggleLabel = isMobile ? 'Tutup' : collapsed ? 'Perluas' : 'Ciutkan'

  const isProfileActive = location.pathname.startsWith(PROFILE_HREF)
  const goProfile = () => {
    navigate(PROFILE_HREF)
    if (isMobile) onToggle()
  }

  return (
    <div className="flex h-full flex-col bg-[#010736] dark:bg-slate-900">
      {/* ── Header ── */}
      <div
        className={[
          'relative flex h-16 shrink-0 items-center gap-2.5 border-b border-white/[0.07]',
          collapsed ? 'justify-center px-3' : 'justify-start px-4',
        ].join(' ')}
      >
        {!collapsed && (
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold leading-[1.3] text-white">FKP SaktiFood</p>
            <p className="text-xs leading-[1.2] text-blue-400">Sistem Keluhan Produk</p>
          </div>
        )}

        {/* Satu tombol toggle — ikon berbeda tergantung mode */}
        <Tooltip
          label={toggleLabel}
          position="right"
          withArrow
          offset={20}
          disabled={isMobile}
          transitionProps={{ duration: 80 }}
        >
          <button
            type="button"
            onClick={onToggle}
            aria-label={toggleLabel}
            className="flex size-6.5 shrink-0 items-center justify-center rounded-md bg-transparent text-white transition-colors hover:bg-white/10"
          >
            {!isMobile && collapsed ? (
              <PanelLeftOpen size={18} />
            ) : (
              <PanelRightOpen size={18} />
            )}
          </button>
        </Tooltip>
      </div>

      {/* ── Nav list ── */}
      <nav className="min-h-0 flex-1 overflow-y-auto py-2 [scrollbar-width:thin] [scrollbar-color:rgba(255,255,255,0.2)_transparent]">
        <div className={['flex flex-col gap-0.5', collapsed ? 'px-2' : 'px-2.5'].join(' ')}>
          {visibleItems.map((item) => {
            const isActive =
              location.pathname === item.href ||
              location.pathname.startsWith(item.href + '/')
            return (
              <NavItem_
                key={item.href}
                item={item}
                isActive={isActive}
                collapsed={collapsed}
                onClick={() => {
                  navigate(item.href)
                  if (isMobile) onToggle()
                }}
              />
            )
          })}
        </div>
      </nav>

      {/* ── User + Logout ── */}
      <div
        className={[
          'shrink-0 border-t border-white/[0.07] py-3',
          collapsed ? 'px-2' : 'px-3',
        ].join(' ')}
      >
        {collapsed ? (
          // Collapsed: hanya avatar, bisa diklik ke halaman profil
          <Tooltip
            label={`Profil — ${resolvedUser.full_name}`}
            position="right"
            withArrow
            transitionProps={{ duration: 80 }}
          >
            <button
              type="button"
              onClick={goProfile}
              aria-label="Buka halaman profil"
              className={[
                'mx-auto mb-1.5 flex size-9 items-center justify-center rounded-full transition-colors',
                isProfileActive ? 'bg-white/10' : 'bg-transparent hover:bg-white/10',
              ].join(' ')}
            >
              <UserAvatar user={resolvedUser} size={28} />
            </button>
          </Tooltip>
        ) : (
          // Expanded: seluruh kartu user bisa diklik
          <button
            type="button"
            onClick={goProfile}
            aria-label="Buka halaman profil"
            className={[
              'mb-1.5 flex w-full items-center gap-2.5 rounded-lg border px-2.5 py-2 text-left transition-colors',
              isProfileActive
                ? 'border-white/20 bg-white/10'
                : 'border-white/[0.07] bg-white/4 hover:bg-white/10',
            ].join(' ')}
          >
            <UserAvatar user={resolvedUser} size={28} className="shrink-0" />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-xs font-semibold leading-[1.4] text-white">
                {resolvedUser.full_name}
              </span>
              <span className="block truncate text-xs leading-[1.3] text-blue-400">
                {resolvedUser.role?.nama_role}
              </span>
            </span>
          </button>
        )}

        {collapsed ? (
          <Tooltip
            label="Keluar"
            position="right"
            withArrow
            transitionProps={{ duration: 80 }}
          >
            <button
              type="button"
              onClick={() => logout()}
              disabled={isPending}
              aria-label="Keluar"
              className="mx-auto flex h-9 w-10 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-red-500/12 hover:text-red-300 disabled:opacity-60"
            >
              <LogOut size={16} />
            </button>
          </Tooltip>
        ) : (
          <button
            type="button"
            onClick={() => logout()}
            disabled={isPending}
            className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-[0.8125rem] font-medium text-slate-400 transition-colors hover:bg-red-500/12 hover:text-red-300 disabled:opacity-60"
          >
            <LogOut size={15} />
            <span>{isPending ? 'Keluar...' : 'Keluar'}</span>
          </button>
        )}
      </div>
    </div>
  )
}