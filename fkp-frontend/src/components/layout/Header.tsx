import { useEffect } from 'react'
import { Group, Burger, Text } from '@mantine/core'
import { NotificationDropdown } from '@/components/NotificationDropdown'
import { UserProfileDropdown } from '@/components/UserProfileDropdown'
import { PageBreadcrumb } from '@/components/ui/PageBreadcrumb'
import { useRouteCrumbs } from '@/hooks/useRouteCrumbs'
import { ThemeToggle } from '../ThemeToggle'

interface HeaderProps {
  mobileOpened: boolean
  onToggleMobile: () => void
}

export function Header({ mobileOpened, onToggleMobile }: HeaderProps) {
  const routeCrumbs = useRouteCrumbs()

  const currentTitle =
    routeCrumbs.length > 0
      ? routeCrumbs[routeCrumbs.length - 1].title
      : 'Dashboard'

  useEffect(() => {
    document.title = `${currentTitle} · FKP SaktiFood`
  }, [currentTitle])

  return (
    <Group
      h="100%"
      px="md"
      justify="space-between"
      wrap="nowrap"
      style={{ gap: 0 }}
    >
      {/* Kiri: Burger + Breadcrumb */}
      <Group
        gap="sm"
        wrap="nowrap"
        style={{ flex: 1, minWidth: 0 }}
      >
        <Burger
          opened={mobileOpened}
          onClick={onToggleMobile}
          className="lg:hidden text-gray-700 dark:text-gray-300"
          size="sm"
          aria-label="Toggle navigation"
        />

        {routeCrumbs.length === 0 ? (
          <Text className="text-sm font-semibold text-gray-800 dark:text-gray-100">
            Dashboard
          </Text>
        ) : (
          <PageBreadcrumb items={routeCrumbs} />
        )}
      </Group>

      {/* Kanan: Theme + Notification + User */}
      <div className="hidden sm:flex shrink-0 items-center justify-center gap-2">
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
