// src/layouts/Header.tsx

import { Group, Burger, Text } from '@mantine/core'
import { NotificationDropdown } from '@/components/NotificationDropdown'
import { UserProfileDropdown } from '@/components/UserProfileDropdown'
import { ThemeToggle } from '../ThemeToggle'

interface HeaderProps {
  mobileOpened: boolean
  onToggleMobile: () => void
  pageTitle?: string
}

export function Header({ mobileOpened, onToggleMobile, pageTitle }: HeaderProps) {
  return (
    <Group h="100%" px="md" justify="space-between" style={{ gap: 0 }}>
      {/* Kiri: Burger (mobile/tablet) + Page title */}
      <Group gap="sm flex">
        {/* Burger hanya muncul di bawah lg */}
        <Burger
          opened={mobileOpened}
          onClick={onToggleMobile}
          className="lg:hidden text-gray-700 dark:text-gray-300"
          size="sm"
          aria-label="Toggle navigation"
        />

        {pageTitle && (
          <Text className="pl-5 text-sm font-semibold text-gray-800 dark:text-gray-100">
            {pageTitle}
          </Text>
        )}
      </Group>

      {/* Kanan: Notification + User */}
      <div className="hidden sm:flex items-center justify-center gap-2">
        <ThemeToggle />
        <NotificationDropdown />
        <UserProfileDropdown />
      </div>
    </Group>
  )
}