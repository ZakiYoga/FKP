// src/theme.ts
import { createTheme, Button, Input, Select, rem } from '@mantine/core'
import type { MantineColorsTuple } from '@mantine/core'

/**
 * Sinkron dengan src/index.css:
 * - brand      -> @theme --color-brand-50..900 (Mantine indeks 0..9)
 * - radius     -> --control-radius (0.5rem = 8px = radius "md" Mantine)
 * - tinggi     -> btn-sm / btn-md / btn-lg dan --control-h (2.5rem = 40px)
 * - font       -> --font-sans / --font-mono
 */

// Indigo, sama persis dengan --color-brand-50 s/d --color-brand-900
const brand: MantineColorsTuple = [
  '#eef2ff', // 0 = brand-50
  '#e0e7ff', // 1 = brand-100
  '#c7d2fe', // 2 = brand-200
  '#a5b4fc', // 3 = brand-300
  '#818cf8', // 4 = brand-400
  '#6366f1', // 5 = brand-500
  '#4f46e5', // 6 = brand-600 (primary light)
  '#4338ca', // 7 = brand-700 (hover)
  '#3730a3', // 8 = brand-800
  '#312e81', // 9 = brand-900
]

// Ukuran kontrol, sama dengan btn-sm/md/lg di index.css
const CONTROL = {
  xs: { height: rem(28), px: rem(10), fz: rem(12) },
  sm: { height: rem(32), px: rem(12), fz: rem(12) },
  md: { height: rem(40), px: rem(16), fz: rem(14) },
  lg: { height: rem(48), px: rem(24), fz: rem(16) },
  xl: { height: rem(56), px: rem(28), fz: rem(18) },
} as const

type ControlSize = keyof typeof CONTROL

const getSize = (size: unknown): ControlSize =>
  typeof size === 'string' && size in CONTROL ? (size as ControlSize) : 'md'

export const theme = createTheme({
  // ===== Warna =====
  primaryColor: 'brand',
  colors: { brand },
  primaryShade: { light: 6, dark: 5 },
  black: '#141b2b', // gray-900
  white: '#ffffff',

  // ===== Radius (md = 8px = rounded-lg Tailwind) =====
  defaultRadius: 'md',
  radius: {
    xs: rem(2),
    sm: rem(4),
    md: rem(8),
    lg: rem(12),
    xl: rem(16),
  },

  // ===== Tipografi =====
  fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
  fontFamilyMonospace: "'JetBrains Mono', monospace",
  headings: {
    fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
    fontWeight: '600',
  },

  components: {
    // ===== Button: ukuran mengikuti btn-sm / btn-md / btn-lg =====
    Button: Button.extend({
      defaultProps: { size: 'md' },
      vars: (t, props) => {
        const s = CONTROL[getSize(props.size)]
        const root: Record<string, string> = {
          '--button-height': s.height,
          '--button-padding-x': s.px,
          '--button-fz': s.fz,
        }

        // Variant kustom: merah solid untuk aksi berbahaya
        if (props.variant === 'destructive') {
          root['--button-bg'] = t.colors.red[6]       // #e03131 (Mantine red-6)
          root['--button-hover'] = t.colors.red[7]
          root['--button-color'] = t.white
          root['--button-bd'] = 'calc(0.0625rem * var(--mantine-scale)) solid transparent'
        }

        return { root }
      },
      styles: {
        root: { fontWeight: 600 },
      },
    }),

    // ===== Input (juga dipakai TextInput, Select, NumberInput, dll.) =====
    Input: Input.extend({
      defaultProps: { size: 'md' },
      vars: (_theme, props) => {
        const s = CONTROL[getSize(props.size)]
        return {
          wrapper: {
            '--input-height': s.height,
            '--input-fz': s.fz,
            '--input-bd': 'var(--mantine-color-default-border)',
            '--input-bd-focus': 'var(--mantine-color-brand-6)',
          },
        }
      },
    }),

    // ===== Select: dropdown =====
    Select: Select.extend({
      defaultProps: {
        comboboxProps: { shadow: 'md', radius: 'md' },
      },
      styles: {
        dropdown: { borderColor: 'var(--mantine-color-default-border)' },
        option: { fontSize: rem(14) },
      },
    }),

    InputWrapper: Input.Wrapper.extend({
      defaultProps: {
        inputWrapperOrder: ['label', 'input', 'description', 'error'],
      },
      styles: {
        label: {
          fontSize: rem(14),
          fontWeight: 600,
          marginBottom: rem(6),
          color: 'light-dark(var(--mantine-color-gray-7), var(--mantine-color-gray-3))',
        },
        required: { color: 'var(--mantine-color-red-6)' },
        description: { fontSize: rem(12), marginBottom: rem(6) },
        error: { fontSize: rem(12), marginTop: rem(4) },
      },
    }),
  },
})