import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Toaster } from 'react-hot-toast'
import { AppRouter } from './AppRouter'

/**
 * QueryClient config:
 * - staleTime 2 menit: data tidak refetch terlalu sering
 * - retry 1x: jika request gagal, coba lagi 1x (bukan 3x default)
 * - refetchOnWindowFocus false: jangan refetch saat tab aktif kembali
 */
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
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRouter />

        {/* Toast notifications global */}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#1e293b',
              color: '#f1f5f9',
              fontSize: '14px',
              borderRadius: '10px',
              padding: '12px 16px',
            },
            success: {
              iconTheme: { primary: '#22c55e', secondary: '#fff' },
            },
            error: {
              iconTheme: { primary: '#ef4444', secondary: '#fff' },
              duration: 5000,
            },
          }}
        />
      </BrowserRouter>

      {/* TanStack Query devtools (hanya muncul di development) */}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
