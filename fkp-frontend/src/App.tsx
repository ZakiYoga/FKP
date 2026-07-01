import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { MantineProvider, ColorSchemeScript, createTheme } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import { AppRouter } from './AppRouter'

import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'

const theme = createTheme({
  primaryColor: 'brand',
  colors: {
    brand: [
      '#eff6ff', // 50
      '#dbeafe', // 100
      '#bfdbfe', // 200
      '#93c5fd', // 300
      '#60a5fa', // 400
      '#3b82f6', // 500
      '#2563eb', // 600  ← primary
      '#1d4ed8', // 700
      '#1e40af', // 800
      '#1e3a8a', // 900
      '#172554', // 950
    ],
  },
  defaultRadius: 'md',
  fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
  components: {
    Button: { defaultProps: { radius: 'md' } },
    NavLink: { defaultProps: { radius: 'md' } },
  },
})

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  return (
    <>
      {/* Mencegah flash warna saat halaman pertama load */}
      <ColorSchemeScript defaultColorScheme="light" />

      <MantineProvider theme={theme} defaultColorScheme="light">
        <Notifications position="top-right" zIndex={9999} />

        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AppRouter />
          </BrowserRouter>
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </MantineProvider>
    </>
  )
}