import { useEffect } from 'react'
import { Group, Burger } from '@mantine/core'
import { NotificationDropdown } from '@/components/NotificationDropdown'
import { UserProfileDropdown } from '@/components/UserProfileDropdown'
import { PageBreadcrumb, type BreadcrumbItem } from '@/components/ui/PageBreadcrumb'
import { useRouteCrumbs } from '@/hooks/useRouteCrumbs'
import { ThemeToggle } from '../ThemeToggle'

interface HeaderProps {
  mobileOpened: boolean
  onToggleMobile: () => void
}

const DASHBOARD_CRUMB: BreadcrumbItem[] = [{ title: 'Dashboard' }]

export function Header({ mobileOpened, onToggleMobile }: HeaderProps) {
  const routeCrumbs = useRouteCrumbs()

  // Dashboard = route dengan handle.crumbs kosong
  const isDashboard = routeCrumbs.length === 0
  const items = isDashboard ? DASHBOARD_CRUMB : routeCrumbs
  const currentTitle = items[items.length - 1].title

  // Judul tab browser mengikuti halaman aktif
  useEffect(() => {
    document.title = `${currentTitle} · FKP SaktiFood`
  }, [currentTitle])

  return (
    <Group h="100%" px="md" justify="space-between" wrap="nowrap" style={{ gap: 0 }}>
      {/* Kiri: Burger (mobile/tablet) + Breadcrumb */}
      <Group gap="sm" wrap="nowrap" className="min-w-0">
        <Burger
          opened={mobileOpened}
          onClick={onToggleMobile}
          className="lg:hidden text-gray-700 dark:text-gray-300"
          size="sm"
          aria-label="Toggle navigation"
        />

        {/* ≥ sm: dashboard hanya teks "Dashboard", halaman lain ikon home + trail */}
        <div className="hidden min-w-0 sm:block">
          <PageBreadcrumb items={items} showHome={!isDashboard} />
        </div>

        {/* < sm: hanya halaman aktif agar tidak sesak */}
        <div className="min-w-0 truncate text-sm font-semibold text-gray-800 dark:text-gray-100 sm:hidden">
          {currentTitle}
        </div>
      </Group>

      {/* Kanan: Theme + Notification + User */}
      <div className="hidden sm:flex items-center justify-center gap-2">
        <ThemeToggle
          size="lg"
          className="hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
        />
        <NotificationDropdown />
        <UserProfileDropdown />
      </div>
    </Group>
  )
}