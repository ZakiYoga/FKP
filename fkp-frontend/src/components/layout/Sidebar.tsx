import { useNavigate, useLocation } from 'react-router-dom'
import { ShieldCheck, LogOut, ChevronLeft, ChevronRight, X, PanelLeftClose } from 'lucide-react'
import {
  Stack,
  Text,
  Box,
  Avatar,
  UnstyledButton,
  ScrollArea,
  ThemeIcon,
  Tooltip,
  ActionIcon,
} from '@mantine/core'
import { useKodeRole, useCurrentUser } from '@/store/authStore'
import { useLogout } from '@/hooks/useAuth'
import { UserMe } from '@/types'
import { NavItem } from '@/types/navItems'
import { NAV_ITEMS } from '@/data/NavItems'

function getInitials(nama?: string) {
  return nama?.split(' ').slice(0, 2).map((w) => w.charAt(0).toUpperCase()).join('') ?? '?'
}

// ─── Tokens ───────────────────────────────────────────────────────────────────
const BG = '#0f172a'
const BORDER = 'rgba(255,255,255,0.07)'
const NAV_COLOR = '#94a3b8'
const ACTIVE_BG = 'rgba(59,130,246,0.9)'

const SKELETON_USER: UserMe = {
  id: '', nama: 'Loading...', email: '', no_telepon: null,
  is_active: true, last_login: null, created_at: '',
  role: { id: '', kode_role: '', nama_role: 'Loading...' },
}

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

  const btn = (
    <UnstyledButton
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: collapsed ? 0 : 10,
        justifyContent: collapsed ? 'center' : 'flex-start',
        width: '100%',
        height: 40,
        padding: collapsed ? 0 : '0 10px',
        borderRadius: 8,
        background: isActive ? ACTIVE_BG : 'transparent',
        color: isActive ? '#fff' : NAV_COLOR,
        fontSize: '0.8125rem',
        fontWeight: isActive ? 600 : 400,
        transition: 'background 120ms, color 120ms',
        overflow: 'hidden',
        whiteSpace: 'nowrap',
      }}
      onMouseEnter={(e) => {
        if (!isActive) {
          e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
          e.currentTarget.style.color = '#fff'
        }
      }}
      onMouseLeave={(e) => {
        if (!isActive) {
          e.currentTarget.style.background = 'transparent'
          e.currentTarget.style.color = NAV_COLOR
        }
      }}
    >
      <Icon size={collapsed ? 17 : 15} style={{ flexShrink: 0 }} />
      {!collapsed && (
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {item.label}
        </span>
      )}
    </UnstyledButton>
  )

  if (collapsed) {
    return (
      <Tooltip label={item.label} position="right" withArrow transitionProps={{ duration: 80 }}>
        {btn}
      </Tooltip>
    )
  }
  return btn
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

  // Toggle button:
  // - mobile  → X (tutup drawer)
  // - desktop collapsed  → ChevronRight (expand)
  // - desktop expanded   → ChevronLeft  (collapse)
  const ToggleIcon = isMobile ? X : collapsed ? ChevronRight : ChevronLeft
  const toggleLabel = isMobile ? 'Tutup' : collapsed ? 'Perluas' : 'Ciutkan'

  return (
    <Stack h="100%" gap={0} style={{ background: BG }}>

      {/* ── Header ── */}
      <Box
        style={{
          display: 'flex',
          alignItems: 'center',
          height: 64,
          padding: collapsed ? '0 12px' : '0 16px',
          borderBottom: `1px solid ${BORDER}`,
          flexShrink: 0,
          gap: 10,
          justifyContent: collapsed ? 'center' : 'flex-start',
          position: 'relative',
        }}
      >

        <ThemeIcon size={34} radius="md" color="blue" variant="filled" style={{ flexShrink: 0 }}>
          <ShieldCheck size={17} />
        </ThemeIcon>

        {!collapsed && (
          <Box style={{ minWidth: 0, flex: 1, display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <Box style={{ minWidth: 0, flex: 1 }}>
              <Text fw={700} size="sm" c="white" lh={1.3} truncate>FKP SaktiFood</Text>
              <Text size="xs" lh={1.2} style={{ color: '#60a5fa' }}>Sistem Keluhan Produk</Text>
            </Box>
          </Box>
        )}

        {/* Satu tombol toggle — posisi berbeda tergantung mode */}
        <Tooltip label={toggleLabel} position="right" withArrow transitionProps={{ duration: 80 }}>
          <ActionIcon
            onClick={onToggle}
            size={26}
            radius="md"
            variant="subtle"
            aria-label={toggleLabel}
            style={
              // Desktop collapsed/expanded: mengapung di sisi kanan border
              !isMobile && !collapsed
                ? {
                  position: 'absolute',
                  right: -12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: BG,
                  color: NAV_COLOR,
                  zIndex: 10,
                }
                : !isMobile && collapsed
                  ? {
                    position: 'absolute',
                    right: -12,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: BG,
                      color: NAV_COLOR,
                    zIndex: 10,
                  }
                  : {
                    // Mobile: tombol X di kanan header
                    flexShrink: 0,
                    color: NAV_COLOR,
                    background: 'rgba(255,255,255,0.06)',
                  }
            }
          >
            <ToggleIcon size={18} />
          </ActionIcon>
        </Tooltip>
      </Box>

      {/* ── Nav list ── */}
      <ScrollArea flex={1} py="xs" scrollbarSize={4} style={{ minHeight: 0 }}>
        <Stack gap={2} px={collapsed ? 8 : 'xs'}>
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
        </Stack>
      </ScrollArea>

      {/* ── User + Logout ── */}
      <Box
        px={collapsed ? 8 : 'sm'}
        py="sm"
        style={{ borderTop: `1px solid ${BORDER}`, flexShrink: 0 }}
      >
        {!collapsed && (
          <Box
            px="xs"
            py={8}
            mb={6}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              background: 'rgba(255,255,255,0.04)',
              borderRadius: 8,
              border: `1px solid ${BORDER}`,
            }}
          >
            <Avatar size={28} radius="xl" color="blue" variant="filled">
              {getInitials(resolvedUser.nama)}
            </Avatar>
            <Box style={{ minWidth: 0, flex: 1 }}>
              <Text size="xs" fw={600} c="white" truncate lh={1.4}>{resolvedUser.nama}</Text>
              <Text size="xs" truncate lh={1.3} style={{ color: '#60a5fa' }}>
                {resolvedUser.role?.nama_role}
              </Text>
            </Box>
          </Box>
        )}

        {collapsed ? (
          <Tooltip label="Keluar" position="right" withArrow transitionProps={{ duration: 80 }}>
            <UnstyledButton
              onClick={() => logout()}
              disabled={isPending}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 40,
                height: 36,
                borderRadius: 8,
                color: NAV_COLOR,
                margin: '0 auto',
                transition: 'background 120ms, color 120ms',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(239,68,68,0.12)'
                e.currentTarget.style.color = '#fca5a5'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.color = NAV_COLOR
              }}
            >
              <LogOut size={16} />
            </UnstyledButton>
          </Tooltip>
        ) : (
          <UnstyledButton
            onClick={() => logout()}
            disabled={isPending}
            w="100%"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 10px',
              borderRadius: 8,
              color: NAV_COLOR,
              fontSize: '0.8125rem',
              fontWeight: 500,
              transition: 'background 120ms, color 120ms',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(239,68,68,0.12)'
              e.currentTarget.style.color = '#fca5a5'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = NAV_COLOR
            }}
          >
            <LogOut size={15} />
            <span>{isPending ? 'Keluar...' : 'Keluar'}</span>
          </UnstyledButton>
        )}
      </Box>
    </Stack>
  )
}