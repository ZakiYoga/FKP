import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LayoutDashboard, Settings, LogOut, ChevronDown } from 'lucide-react'
import {
  Menu,
  Avatar,
  Group,
  Text,
  Box,
  Divider,
} from '@mantine/core'
import { useCurrentUser } from '@/store/authStore'
import { useLogout } from '@/hooks/useAuth'

interface MenuItem {
  label: string
  href: string
  icon: React.ElementType
}

const MENU_ITEMS: MenuItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Ubah Password', href: '/change-password', icon: Settings },
]

function getInitials(nama?: string) {
  return nama
    ?.split(' ')
    .slice(0, 2)
    .map((w) => w.charAt(0).toUpperCase())
    .join('') ?? '?'
}

export function UserProfileDropdown() {
  const [opened, setOpened] = useState(false)
  const navigate = useNavigate()
  const user = useCurrentUser()
  const { mutate: logout, isPending } = useLogout()

  return (
    <Menu
      opened={opened}
      onChange={setOpened}
      position="bottom-end"
      offset={8}
      shadow="lg"
      radius="md"
      width={240}
      styles={{
        item: { margin: '2px 0' },
        dropdown: { padding: '4px 8px' },
      }}
    >
      <Menu.Target>
        <button
          aria-label="Menu profil pengguna"
          className={`
            flex items-center gap-2 p-2 rounded-md
            transition-colors duration-150 border-none cursor-pointer
            ${opened
              ? 'bg-gray-100 dark:bg-gray-800'
              : 'bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800'
            }
          `}
        >
          <Avatar size={32} radius="xl" color="brand" variant="filled">
            {getInitials(user?.nama)}
          </Avatar>
          {/* <Box visibleFrom="md">
            <Text size="sm" fw={500} c="gray.9" lh={1.3}>
              {user?.nama}
            </Text>
            <Text size="xs" c="dimmed" lh={1.2}>
              {user?.role?.nama_role}
            </Text>
          </Box> */}
          <ChevronDown size={16} />
        </button>
      </Menu.Target>

      <Menu.Dropdown
        style={{ border: '1px solid var(--mantine-color-gray-3)' }}
        py={4}
      >
        {/* Profile card */}
        <Box px="sm" py="xs">
          <Group gap="sm">
            <Avatar size={42} radius="xl" color="brand" variant="filled">
              {getInitials(user?.nama)}
            </Avatar>
            <Box style={{ minWidth: 0, flex: 1 }}>
              <Text size="sm" fw={600} truncate>
                {user?.nama}
              </Text>
              <Text size="xs" c="dimmed" truncate>
                {user?.role?.nama_role}
              </Text>
            </Box>
          </Group>
        </Box>

        <Divider my={4} />

        {MENU_ITEMS.map(({ label, href, icon: Icon }) => (
          <Menu.Item
            key={href}
            leftSection={<Icon size={15} />}
            onClick={() => { setOpened(false); navigate(href) }}
          >
            {label}
          </Menu.Item>
        ))}

        <Divider my={4} />

        <Menu.Item
          color="red"
          leftSection={<LogOut size={15} />}
          onClick={() => { setOpened(false); logout() }}
          disabled={isPending}
        >
          {isPending ? 'Keluar...' : 'Keluar'}
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  )
}