import { useState, type ElementType } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LogOut, ChevronDown, User, Route } from 'lucide-react'
import { Menu, Text, Box, Divider } from '@mantine/core'
import { useCurrentUser } from '@/store/authStore'
import { useLogout } from '@/hooks/useAuth'
import { UserAvatar } from './UserAvatar'

interface MenuItem {
  label: string
  href: string
  icon: ElementType
}

const PROFILE_HREF = '/profile'

const MENU_ITEMS: MenuItem[] = [
  { label: 'Profil', href: PROFILE_HREF, icon: User },
  { label: 'Lacak Proses FKP', href: '/track', icon: Route },
]

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
            flex items-center gap-2 p-2 rounded-md ml-2
            transition-colors duration-150 border-none cursor-pointer
            ${opened
              ? 'bg-gray-100 dark:bg-gray-800'
              : 'bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800'
            }
          `}
        >
          <UserAvatar user={user} size={32} />
          <ChevronDown size={16} />
        </button>
      </Menu.Target>

      <Menu.Dropdown
        style={{ border: '1px solid var(--mantine-color-gray-3)' }}
        py={4}
      >
        {/* Profile card */}
        <Link
          to={PROFILE_HREF}
          onClick={() => setOpened(false)}
          className="flex w-full items-center justify-start gap-2 rounded-md p-2 transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <UserAvatar user={user} size={30} />
          <Box className="flex min-w-0 flex-1 flex-col items-start justify-end">
            <Text size="sm" fw={600} truncate className="w-full">
              {user?.full_name}
            </Text>
            <Text size="xs" c="dimmed" truncate className="w-full">
              {user?.role?.nama_role}
            </Text>
          </Box>
        </Link>

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