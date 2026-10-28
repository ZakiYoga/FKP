import { Outlet, useLocation } from 'react-router-dom'
import { Box, Flex, Text, Center } from '@mantine/core'
import { useDisclosure, useMediaQuery } from '@mantine/hooks'
import { motion, AnimatePresence } from 'framer-motion'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { APP_VERSION } from '@/lib/app-config'
import { usePersistentState } from '@/hooks/usePersistentState'

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/fkp': 'Formulir Keluhan Produk',
  '/outlets': 'Manajemen Outlet',
  '/outlet-registrations': 'Registrasi Outlet',
  '/distributors': 'Manajemen Distributor',
  '/areas': 'Manajemen Area',
  '/products': 'Katalog Produk',
  '/hierarchy': 'Hierarki Tim',
  '/users': 'Manajemen Pengguna',
  '/notifications': 'Notifikasi',
  '/change-password': 'Ubah Password',
}

const SIDEBAR_EXPANDED = 240
const SIDEBAR_COLLAPSED = 64
const MOBILE_BREAKPOINT = '(min-width: 1024px)'

// Warna sidebar — tetap dark regardless color scheme
const SIDEBAR_BG = '#0f172a'

export function AppLayout() {
  const [collapsed, setCollapsed] = usePersistentState('sidebar-collapsed', false)
  const [mobileOpened, { toggle: toggleMobile, close: closeMobile }] = useDisclosure(false)

  const isDesktop = useMediaQuery(MOBILE_BREAKPOINT)
  const location = useLocation()
  const currentTitle = PAGE_TITLES[location.pathname] ?? 'FKP SaktiFood'

  return (
    <Flex h="100vh" style={{ overflow: 'hidden' }}>

      {/* ── Desktop sidebar ── */}
      {isDesktop && (
        <Box
          h="100vh"
          style={{
            width: collapsed ? SIDEBAR_COLLAPSED : SIDEBAR_EXPANDED,
            flexShrink: 0,
            transition: 'width 220ms ease',
            overflow: 'visible',
            position: 'relative',
            zIndex: 999,
            background: "#fff",
          }}
        >
          <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
        </Box>
      )}

      {/* ── Mobile: backdrop + drawer ── */}
      {!isDesktop && (
        <AnimatePresence>
          {mobileOpened && (
            <>
              <motion.div
                key="backdrop"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                onClick={closeMobile}
                style={{
                  position: 'fixed',
                  inset: 0,
                  zIndex: 200,
                  background: 'rgba(0,0,0,0.5)',
                  backdropFilter: 'blur(2px)',
                }}
              />
              <motion.div
                key="drawer"
                initial={{ x: -SIDEBAR_EXPANDED }}
                animate={{ x: 0 }}
                exit={{ x: -SIDEBAR_EXPANDED }}
                transition={{ type: 'tween', duration: 0.22, ease: 'easeOut' }}
                style={{
                  position: 'fixed',
                  top: 0, left: 0,
                  zIndex: 201,
                  width: SIDEBAR_EXPANDED,
                  height: '100vh',
                  background: SIDEBAR_BG,
                  boxShadow: '8px 0 32px rgba(0,0,0,0.4)',
                }}
              >
                <Sidebar collapsed={false} onToggle={closeMobile} isMobile />
              </motion.div>
            </>
          )}
        </AnimatePresence>
      )}

      <Flex
        flex={1}
        direction="column"
        style={{ minWidth: 0, overflow: 'hidden' }}
      >
        {/* Header */}
        <Box className="h-16 shrink-0 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-[0_1px_3px_rgba(0,0,0,0.05)] z-100">
          <Header
            mobileOpened={mobileOpened}
            onToggleMobile={toggleMobile}
            pageTitle={currentTitle}
          />
        </Box>

        {/* Main content: hapus class bg yang rusak */}
        <Box flex={1} style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <Box
            flex={1}
            p={{ base: 'md', sm: 'lg', lg: 'xl' }}
            style={{ maxWidth: 1440, margin: '0 auto', width: '100%' }}
          >
            <Outlet />
          </Box>

          {/* Footer */}
          <Center
            py="xs"
            className="border-t border-gray-200 dark:border-gray-800"
            style={{ flexShrink: 0 }}
          >
            <Text size="xs" c="dimmed">
              FKP SaktiFood Version {APP_VERSION} — Sistem Formulir Keluhan Produk
            </Text>
          </Center>
        </Box>
      </Flex>
    </Flex >
  )
}