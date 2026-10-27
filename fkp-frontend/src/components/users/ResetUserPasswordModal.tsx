import { useState, type FormEvent } from 'react'
import { Alert, Button, Group, Modal, PasswordInput, Stack, Text } from '@mantine/core'
import { useResetUserPassword } from '@/hooks/useUsers'
import { PASSWORD_RULE_HINT, validateNewPassword } from '@/lib/password'
import type { UserDetail } from '@/api/users'

interface Props {
    user: UserDetail | null
    onClose: () => void
}

export function ResetUserPasswordModal({ user, onClose }: Props) {
    const [password, setPassword] = useState('')
    const [confirm, setConfirm] = useState('')
    const [error, setError] = useState<string | null>(null)
    const resetMutation = useResetUserPassword()

    const close = () => {
        if (resetMutation.isPending) return
        setPassword('')
        setConfirm('')
        setError(null)
        onClose()
    }

    // Aturan password baru dari satu sumber: src/lib/password.ts
    // (sama dengan backend: validate_password_baru)
    const validate = (): string | null => {
        const passwordError = validateNewPassword(password)
        if (passwordError) return passwordError
        if (password !== confirm) return 'Konfirmasi password tidak cocok'
        return null
    }

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        if (!user) return
        const msg = validate()
        setError(msg)
        if (msg) return
        try {
            await resetMutation.mutateAsync({
                id: user.id,
                password_baru: password,
                password_baru_konfirmasi: confirm,
            })
            close()
        } catch {
            // pesan error ditampilkan oleh hook; modal tetap terbuka
        }
    }

    return (
        <Modal
            opened={!!user}
            onClose={close}
            title="Reset password user"
            centered
            closeOnClickOutside={!resetMutation.isPending}
            closeOnEscape={!resetMutation.isPending}
        >
            {user && (
                <form onSubmit={handleSubmit} noValidate>
                    <Stack gap="md">
                        <Text size="sm">
                            Tetapkan password baru untuk <b>{user.full_name}</b> ({user.email}). Semua sesi login
                            user ini akan dikeluarkan.
                        </Text>
                        {!user.email_verified_at && (
                            <Alert color="yellow" variant="light" p="xs">
                                <Text size="xs">
                                    Email user belum terverifikasi: user tidak akan menerima email pemberitahuan.
                                    Sampaikan password sementara lewat jalur lain.
                                </Text>
                            </Alert>
                        )}
                        <PasswordInput
                            label="Password baru"
                            description={PASSWORD_RULE_HINT}
                            autoComplete="new-password"
                            data-autofocus
                            value={password}
                            onChange={(e) => { setPassword(e.currentTarget.value); setError(null) }}
                        />
                        <PasswordInput
                            label="Konfirmasi password baru"
                            autoComplete="new-password"
                            value={confirm}
                            error={error ?? undefined}
                            onChange={(e) => { setConfirm(e.currentTarget.value); setError(null) }}
                        />
                        <Group justify="flex-end" gap="xs">
                            <Button variant="default" disabled={resetMutation.isPending} onClick={close}>
                                Batal
                            </Button>
                            <Button type="submit" color="red" loading={resetMutation.isPending}>
                                Reset Password
                            </Button>
                        </Group>
                    </Stack>
                </form>
            )}
        </Modal>
    )
}