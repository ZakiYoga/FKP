import { Outlet, useLocation } from 'react-router-dom'
import { Box, Flex, Text, Center } from '@mantine/core'
import { useDisclosure, useMediaQuery } from '@mantine/hooks'
import { motion, AnimatePresence } from 'framer-motion'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

const PAGE_TITLES: Record<string, string> = {
  '/dashboard':            'Dashboard',
  '/fkp':                  'Formulir Keluhan Produk',
  '/outlets':              'Manajemen Outlet',
  '/outlet-registrations': 'Registrasi Outlet',
  '/distributors':         'Manajemen Distributor',
  '/areas':                'Manajemen Area',
  '/products':             'Katalog Produk',
  '/hierarchy':            'Hierarki Tim Sales',
  '/users':                'Manajemen Pengguna',
  '/notifications':        'Notifikasi',
  '/change-password':      'Ubah Password',
}

const SIDEBAR_EXPANDED  = 240
const SIDEBAR_COLLAPSED = 64
const MOBILE_BREAKPOINT = '(min-width: 1024px)'

// Warna sidebar — tetap dark regardless color scheme
const SIDEBAR_BG = '#0f172a'

export function AppLayout() {
  const [collapsed,    { toggle: toggleCollapse }]                  = useDisclosure(false)
  const [mobileOpened, { toggle: toggleMobile, close: closeMobile }] = useDisclosure(false)

  const isDesktop  = useMediaQuery(MOBILE_BREAKPOINT)
  const location   = useLocation()
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
            background: SIDEBAR_BG,
          }}
        >
          <Sidebar collapsed={collapsed} onToggle={toggleCollapse} />
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

      {/* ── Kolom kanan ── */}
      <Flex
        flex={1}
        direction="column"
        style={{ minWidth: 0, overflow: 'hidden' }}
        bg="var(--mantine-color-gray-0)"
      >
        {/* Header */}
        <Box
          h={64}
          bg="var(--mantine-color-body)"
          style={{
            flexShrink: 0,
            borderBottom: '1px solid var(--mantine-color-gray-2)',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            zIndex: 100,
          }}
        >
          <Header
            mobileOpened={mobileOpened}
            onToggleMobile={toggleMobile}
            pageTitle={currentTitle}
          />
        </Box>

        {/* Main content */}
        <Box flex={1} style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column' }} className="bg-gray-50 dark:bg-gray-950">
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
            bg="var(--mantine-color-body)"
            style={{
              borderTop: '1px solid var(--mantine-color-gray-2)',
              flexShrink: 0,
            }}
          >
            <Text size="xs" c="dimmed">
              FKP SaktiFood v1.0.0 — Sistem Formulir Keluhan Produk
            </Text>
          </Center>
        </Box>
      </Flex>
    </Flex>
  )
}