// src/App.tsx
import { RouterProvider } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { MantineProvider, ColorSchemeScript, createTheme } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import { queryClient } from '@/lib/queryClient'
import { router } from '@/lib/router'

import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'

const theme = createTheme({
  primaryColor: 'brand',
  colors: {
    brand: [
      '#eff6ff', '#dbeafe', '#bfdbfe', '#93c5fd', '#60a5fa',
      '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af', '#1e3a8a', '#172554',
    ],
  },
  defaultRadius: 'md',
  fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
  components: {
    Button: { defaultProps: { radius: 'md' } },
    NavLink: { defaultProps: { radius: 'md' } },
  },
})

export default function App() {
  return (
    <>
      <ColorSchemeScript defaultColorScheme="light" />
      <MantineProvider theme={theme} defaultColorScheme="light">
        <Notifications position="top-right" zIndex={9999} />
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </MantineProvider>
    </>
  )
}