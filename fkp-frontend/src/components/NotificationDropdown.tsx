import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, Check, CheckCheck, ExternalLink } from 'lucide-react'
import {
    Popover,
    ActionIcon,
    Indicator,
    Text,
    Group,
    Stack,
    Box,
    Badge,
    ScrollArea,
    Divider,
    Tabs,
    Center,
    UnstyledButton,
    Loader,
    Anchor,
} from '@mantine/core'
import {
    useNotifications,
    useUnreadCount,
    useMarkRead,
    useMarkAllRead,
} from '@/hooks/useNotifications'
import { formatRelative } from '@/lib/utils'

interface Notification {
    id: string
    fkp_id?: string | null
    nomor_fkp?: string | null
    fkp_status?: string | null
    judul: string
    pesan: string
    tipe: string
    is_read: boolean
    created_at: string
}

// Badge style per tipe
const TIPE_CONFIG: Record<string, { label: string; color: string }> = {
    need_action: { label: 'Perlu Aksi', color: 'yellow' },
    status_change: { label: 'Status', color: 'blue' },
    info: { label: 'Info', color: 'gray' },
}

function resolveTarget(notif: Notification): string | null {
    return notif.fkp_id ? `/fkp/${notif.fkp_id}` : null
}

// ─── Satu item notifikasi ─────────────────────────────────────────────────────
function NotificationItem({
    notification,
    onMarkRead,
    onClose,
}: {
    notification: Notification
    onMarkRead: (id: string) => void
    onClose: () => void
}) {
    const { id, judul, pesan, nomor_fkp, tipe, is_read, created_at } = notification
    const target = resolveTarget(notification)
    const tipeConf = TIPE_CONFIG[tipe] ?? TIPE_CONFIG.info
    const navigate = useNavigate()
    const [hovered, setHovered] = useState(false)

    function handleClick() {
        if (!is_read) onMarkRead(id)
        if (target) {
            onClose()
            navigate(target)
        }
    }

    return (
        <UnstyledButton
            onClick={handleClick}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            w="100%"
            style={{
                borderRadius: 'var(--mantine-radius-md)',
                background: !is_read
                    ? 'var(--mantine-color-blue-0)'
                    : hovered ? 'var(--mantine-color-gray-0)' : 'transparent',
                transition: 'background 120ms',
                cursor: target ? 'pointer' : 'default',
            }}
            p="xs"
        >
            <Group align="flex-start" gap="xs" wrap="nowrap">
                {/* Dot unread */}
                <Box
                    mt={6}
                    w={8}
                    h={8}
                    style={{
                        borderRadius: '50%',
                        background: !is_read ? 'var(--mantine-color-blue-5)' : 'transparent',
                        flexShrink: 0,
                    }}
                />

                {/* Konten */}
                <Box flex={1} style={{ minWidth: 0 }}>
                    <Group justify="space-between" align="flex-start" mb={2} gap="xs" wrap="nowrap">
                        <Text
                            size="xs"
                            fw={!is_read ? 600 : 400}
                            c={!is_read ? 'gray.9' : 'gray.6'}
                            truncate
                            style={{ flex: 1 }}
                        >
                            {judul}
                        </Text>
                        <Badge
                            size="xs"
                            color={tipeConf.color}
                            variant="light"
                            style={{ flexShrink: 0 }}
                        >
                            {tipeConf.label}
                        </Badge>
                    </Group>

                    <Text size="xs" c="dimmed" lineClamp={2} lh={1.4}>
                        {pesan}
                    </Text>

                    <Group justify="space-between" align="center" mt={4} gap="xs">
                        {nomor_fkp && (
                            <Badge size="xs" variant="light" color="blue" radius="sm">
                                {nomor_fkp}
                            </Badge>
                        )}
                        <Text size="10px" c="dimmed" ml="auto">
                            {formatRelative(created_at)}
                        </Text>
                    </Group>
                </Box>

                {/* Tombol mark read — muncul saat hover */}
                {!is_read && (
                    <ActionIcon
                        size="sm"
                        variant="subtle"
                        color="blue"
                        onClick={(e) => { e.stopPropagation(); onMarkRead(id) }}
                        title="Tandai sudah dibaca"
                        style={{ opacity: hovered ? 1 : 0, transition: 'opacity 150ms', flexShrink: 0 }}
                    >
                        <Check size={12} />
                    </ActionIcon>
                )}
            </Group>
        </UnstyledButton>
    )
}

// ─── Daftar notifikasi ────────────────────────────────────────────────────────
function NotificationList({
    notifications,
    onMarkRead,
    onClose,
    emptyLabel,
}: {
    notifications: Notification[]
    onMarkRead: (id: string) => void
    onClose: () => void
    emptyLabel: string
}) {
    if (notifications.length === 0) {
        return (
            <Center py="xl" style={{ flexDirection: 'column', gap: 8 }}>
                <Bell size={32} color="var(--mantine-color-gray-4)" />
                <Text size="sm" c="dimmed">{emptyLabel}</Text>
            </Center>
        )
    }

    return (
        <ScrollArea
            h={300}              // ← gunakan h (fixed height), bukan mah
            scrollbarSize={6}
            type="auto"          // ← tambahin ini, biar scrollbar muncul saat hover
            offsetScrollbars     // ← biar scrollbar tidak overlap konten
        >
            <Stack gap={2} p={4}>
                {notifications.map((notif) => (
                    <NotificationItem
                        key={notif.id}
                        notification={notif}
                        onMarkRead={onMarkRead}
                        onClose={onClose}
                    />
                ))}
            </Stack>
        </ScrollArea >
    )
}

// ─── Komponen utama ───────────────────────────────────────────────────────────
export function NotificationDropdown() {
    const navigate = useNavigate()
    const [open, setOpen] = useState(false)

    const { data: unreadData } = useUnreadCount()
    const unreadCount = unreadData?.unread_count ?? 0

    const { data: allData, isLoading } = useNotifications({ limit: 30 })
    const allNotifications: Notification[] = allData?.notifications ?? []
    const unreadNotifications = allNotifications.filter((n) => !n.is_read)

    const { mutate: markRead } = useMarkRead()
    const { mutate: markAllRead, isPending: isMarkingAll } = useMarkAllRead()

    const handleClose = useCallback(() => setOpen(false), [])

    function handleLihatSemua() {
        setOpen(false)
        navigate('/notifications')
    }

    return (
        <Popover
            opened={open}
            onChange={setOpen}
            position="bottom-end"
            offset={8}
            shadow="lg"
            radius="md"
            width={360}
        >
            <Popover.Target>
                <Indicator
                    disabled={unreadCount === 0}
                    label={unreadCount > 99 ? '99+' : unreadCount}
                    size={16}
                    color="red"
                    processing={unreadCount > 0}
                >
                    <ActionIcon
                        variant="subtle"
                        color="gray"
                        size="lg"
                        radius="md"
                        aria-label="Buka notifikasi"
                        onClick={() => setOpen((v) => !v)}
                    >
                        <Bell size={18} />
                    </ActionIcon>
                </Indicator>
            </Popover.Target>

            <Popover.Dropdown
                p={0}
                style={{ border: '1px solid var(--mantine-color-gray-2)' }}
                mah={500}
            >
                {/* Header */}
                <Group justify="space-between" px="md" pt="sm" pb="xs">
                    <Text fw={600} size="sm">Notifikasi</Text>
                    <Group gap={4}>
                        {unreadCount > 0 && (
                            <UnstyledButton
                                onClick={() => markAllRead()}
                                disabled={isMarkingAll}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 4,
                                    fontSize: '0.75rem',
                                    color: 'var(--mantine-color-blue-6)',
                                    padding: '4px 8px',
                                    borderRadius: 'var(--mantine-radius-sm)',
                                    opacity: isMarkingAll ? 0.5 : 1,
                                }}
                            >
                                <CheckCheck size={13} />
                                Baca semua
                            </UnstyledButton>
                        )}
                        <ActionIcon
                            variant="subtle"
                            color="gray"
                            size="sm"
                            onClick={handleLihatSemua}
                            title="Lihat semua notifikasi"
                        >
                            <ExternalLink size={13} />
                        </ActionIcon>
                    </Group>
                </Group>

                <Divider />

                {/* Tabs */}
                <Tabs defaultValue="unread" px="xs" pt="xs">
                    <Tabs.List grow mb="xs">
                        <Tabs.Tab
                            value="unread"
                            rightSection={
                                unreadCount > 0 ? (
                                    <Badge size="xs" color="red" variant="filled" circle>
                                        {unreadCount > 99 ? '99+' : unreadCount}
                                    </Badge>
                                ) : undefined
                            }
                        >
                            Belum Dibaca
                        </Tabs.Tab>
                        <Tabs.Tab value="all">Semua</Tabs.Tab>
                    </Tabs.List>

                    {isLoading ? (
                        <Center py="xl">
                            <Loader size="sm" />
                        </Center>
                    ) : (
                        <>
                            <Tabs.Panel value="unread">
                                <NotificationList
                                    notifications={unreadNotifications}
                                    onMarkRead={markRead}
                                    onClose={handleClose}
                                    emptyLabel="Tidak ada notifikasi yang belum dibaca"
                                />
                            </Tabs.Panel>
                            <Tabs.Panel value="all">
                                <NotificationList
                                    notifications={allNotifications}
                                    onMarkRead={markRead}
                                    onClose={handleClose}
                                    emptyLabel="Belum ada notifikasi"
                                />
                            </Tabs.Panel>
                        </>
                    )}
                </Tabs>

                {/* Footer */}
                <Divider />
                <Center py="xs">
                    <Anchor
                        size="xs"
                        onClick={handleLihatSemua}
                        style={{ cursor: 'pointer' }}
                    >
                        Lihat semua notifikasi →
                    </Anchor>
                </Center>
            </Popover.Dropdown>
        </Popover>
    )
}
