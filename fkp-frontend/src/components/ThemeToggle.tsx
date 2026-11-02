import type { ComponentPropsWithoutRef } from 'react'
import { ActionIcon, useMantineColorScheme, type ActionIconProps } from '@mantine/core'
import { Sun, Moon } from 'lucide-react'

type ThemeToggleProps = ActionIconProps &
  Omit<ComponentPropsWithoutRef<'button'>, keyof ActionIconProps> & {
    iconSize?: number
  }

export function ThemeToggle({
  iconSize = 18,
  onClick,
  className,
  ...props
}: ThemeToggleProps) {
  const { colorScheme, toggleColorScheme } = useMantineColorScheme()
  const isDark = colorScheme === 'dark'

  return (
    <ActionIcon
      variant="subtle"
      aria-label="Toggle color scheme"
      {...props}
      className={`transition-colors duration-150 ${className ?? ''}`}
      onClick={(e) => {
        toggleColorScheme()
        onClick?.(e)
      }}
    >
      {isDark ? <Sun size={iconSize} /> : <Moon size={iconSize} />}
    </ActionIcon>
  )
}