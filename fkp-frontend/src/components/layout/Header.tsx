// src/layouts/Header.tsx

import { Group, Burger, Text, Box, Divider } from '@mantine/core'
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
      <Group gap="sm">
        {/* Burger hanya muncul di bawah lg */}
        <Burger
          opened={mobileOpened}
          onClick={onToggleMobile}
          hiddenFrom="md"
          size="sm"
          color="var(--mantine-color-gray-7)"
          aria-label="Toggle navigation"
        />

        {pageTitle && (
          <Text
            fw={600}
            size="sm"
            c="gray.8"
            style={{ letterSpacing: '-0.01em' }}
            pl={20}
          >
            {pageTitle}
          </Text>
        )}
      </Group>

      {/* Kanan: Notification + User */}
      <div className="flex items-center justify-center gap-2">
        <ThemeToggle />
        <NotificationDropdown />
        <UserProfileDropdown />
      </div>
    </Group>
  )
}