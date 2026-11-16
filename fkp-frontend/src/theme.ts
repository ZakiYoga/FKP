// src/theme.ts
import { createTheme, Button, Input, Select, rem, Modal, Card } from '@mantine/core'
import type { MantineColorsTuple } from '@mantine/core'

/**
 * SUMBER TUNGGAL warna brand/secondary. Ganti warna cukup di tuple di bawah.
 * src/index.css membaca lewat var(--mantine-color-brand-*) (@theme inline).
 * - radius -> --control-radius (0.5rem = 8px = radius "md" Mantine)
 * - tinggi -> btn-sm / btn-md / btn-lg dan --control-h (2.5rem = 40px)
 * - font   -> --font-sans / --font-mono
 */

// Brand — indeks 0..9 = brand-50..900 (500 = #1C4D8D di indeks 5)
const brand: MantineColorsTuple = [
  '#F1F6FB', // 0 = 50
  '#E1ECF7', // 1 = 100
  '#C3D9EE', // 2 = 200
  '#94BADF', // 3 = 300
  '#4988C4', // 4 = 400
  '#1C4D8D', // 5 = 500
  '#174079', // 6 = 600
  '#133463', // 7 = 700
  '#0F2854', // 8 = 800
  '#0B1E40', // 9 = 900
]

// Secondary — 500 = #BDE8F5 di indeks 5
const secondary: MantineColorsTuple = [
  '#F9FDFE', // 0 = 50
  '#F2FBFD', // 1 = 100
  '#E9F7FC', // 2 = 200
  '#DDF3FA', // 3 = 300
  '#D0EEF8', // 4 = 400
  '#BDE8F5', // 5 = 500
  '#8FD0E6', // 6 = 600
  '#5FB5D3', // 7 = 700
  '#3A93B5', // 8 = 800
  '#276F8B', // 9 = 900
]

const FOCUS_COLOR = 'var(--mantine-color-brand-4)'

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
  colors: { brand, secondary },
  primaryShade: { light: 5, dark: 4 },
  black: '#0B1E40',
  white: '#ffffff',
  focusRing: 'auto',

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
            '--input-bd-focus': FOCUS_COLOR,
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

    // ===== Card =====
    Card: Card.extend({
      defaultProps: {
        padding: 'lg',
        radius: 'md',
        withBorder: true,
        shadow: 'xs',
      },
      styles: {
        root: {
          backgroundColor: 'light-dark(var(--mantine-color-white), var(--mantine-color-dark-6))',
          borderColor: 'var(--mantine-color-default-border)',
          transition: 'box-shadow 150ms ease, transform 150ms ease',
        },
        section: {
          borderColor: 'var(--mantine-color-default-border)',
        },
      },
    }),

    // ===== Modal (opsional, supaya seragam dengan Card) =====
    Modal: Modal.extend({
      defaultProps: {
        centered: false,
        radius: 'md',
        overlayProps: { backgroundOpacity: 0.55, blur: 3 },
      },
      styles: {
        title: { fontWeight: 700, fontSize: rem(18) },
        header: { borderBottom: '1px solid var(--mantine-color-default-border)' },
      },
    }),
  },
})