import { useMantineColorScheme, ActionIcon } from '@mantine/core'
import { Sun, Moon } from 'lucide-react'

export function ThemeToggle() {
  const { colorScheme, toggleColorScheme } = useMantineColorScheme()
  const isDark = colorScheme === 'dark'

  return (
    <ActionIcon
      onClick={toggleColorScheme}
      variant="subtle"
      aria-label="Toggle color scheme"
      className="transition-colors duration-150 py-4"
    >
      {isDark ? <Sun size={18} /> : <Moon size={18} />}
    </ActionIcon>
  )
}