import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import {
  Alert,
  Avatar,
  Button,
  Group,
  Modal,
  PasswordInput,
  Radio,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from '@mantine/core'
import { BadgeCheck } from 'lucide-react'
import { getAvatarUrl } from '@/lib/avatar'
import type { Gender, UpdateProfilePayload, UserMe } from '@/types'
import { ConfirmDialog } from '../ui/ConfirmDialog'

// Handler boleh sinkron (void) atau async (Promise). Jika Promise:
// mode edit baru selesai setelah berhasil, dan tetap terbuka jika gagal.
interface ProfileSectionProps {
  data: UserMe
  onSave: (values: UpdateProfilePayload) => void | Promise<unknown>
  onUploadAvatar: (file: File) => void | Promise<unknown>
  onDeleteAvatar: () => void | Promise<unknown>
  onResendVerification: () => void | Promise<unknown>
  onChangeEmail: (values: { email_baru: string; password: string }) => void | Promise<unknown>
}

interface FormValues {
  first_name: string
  last_name?: string
  phone: string // nomor lokal tanpa 0 / +62 di depan
  gender: Gender | null
}

type FormErrors = Partial<Record<'first_name' | 'last_name' | 'phone', string>>

interface EmailFormValues {
  email_baru: string
  password: string
}
type EmailFormErrors = Partial<Record<keyof EmailFormValues, string>>

const EMAIL_PATTERN = /^\S+@\S+\.\S+$/
const EMPTY_EMAIL_FORM: EmailFormValues = { email_baru: '', password: '' }

// "+62812..." / "0812..." / "812..." -> "812..."
const toLocalPhone = (v: string | null | undefined) =>
  (v ?? '').replace(/\D/g, '').replace(/^(62|0)/, '')

const toFormValues = (u: UserMe): FormValues => ({
  first_name: u.first_name,
  last_name: u.last_name ?? '',
  phone: toLocalPhone(u.no_telepon),
  gender: u.gender,
})

// Kirim hanya field yang berubah. Nomor disimpan dengan format lokal "08...".
function buildPayload(original: UserMe, v: FormValues): UpdateProfilePayload {
  const payload: UpdateProfilePayload = {}
  const first = v.first_name.trim()
  const last = v.last_name?.trim()
  if (first !== original.first_name) payload.first_name = first
  if (last !== (original.last_name ?? '')) payload.last_name = last
  if (v.gender && v.gender !== original.gender) payload.gender = v.gender
  if (v.phone !== toLocalPhone(original.no_telepon)) payload.no_telepon = `0${v.phone}`
  return payload
}

export function ProfileSection({
  data,
  onSave,
  onUploadAvatar,
  onDeleteAvatar,
  onResendVerification,
  onChangeEmail,
}: ProfileSectionProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [values, setValues] = useState<FormValues>(() => toFormValues(data))
  const [errors, setErrors] = useState<FormErrors>({})
  const [saving, setSaving] = useState(false)
  const [avatarBusy, setAvatarBusy] = useState(false)
  const [preview, setPreview] = useState<string | null>(null)
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Email
  const [resending, setResending] = useState(false)
  const [emailModalOpen, setEmailModalOpen] = useState(false)
  const [emailValues, setEmailValues] = useState<EmailFormValues>(EMPTY_EMAIL_FORM)
  const [emailErrors, setEmailErrors] = useState<EmailFormErrors>({})
  const [emailSaving, setEmailSaving] = useState(false)

  // Sinkron dari server saat tidak sedang mengedit (juga membuang perubahan saat Cancel).
  useEffect(() => {
    if (!isEditing) {
      setValues(toFormValues(data))
      setErrors({})
    }
  }, [data, isEditing])

  // Lepas object URL lama saat preview berganti atau komponen dilepas.
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  const fieldsDisabled = !isEditing || saving
  const emailVerified = Boolean(data.email_verified_at)
  const hasAvatar = !!(preview || data.avatar_path)
  const avatarSrc = preview ?? getAvatarUrl(data.avatar_path)
  const initials = [data.first_name?.[0], data.last_name?.[0]]
    .filter(Boolean)
    .join('')
    .toUpperCase()

  const setField = <K extends keyof FormValues>(key: K, value: FormValues[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }))
    setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = '' // izinkan memilih file yang sama lagi
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setAvatarBusy(true)
    try {
      await onUploadAvatar(file)
    } catch {
      // pesan error ditampilkan oleh hook
    } finally {
      setPreview(null)
      setAvatarBusy(false)
    }
  }

  // handleDeleteAvatar: tutup dialog setelah proses selesai
  const handleDeleteAvatar = async () => {
    setAvatarBusy(true)
    try {
      await onDeleteAvatar()
    } catch {
      // pesan error ditampilkan oleh hook
    } finally {
      setAvatarBusy(false)
      setConfirmDeleteOpen(false)
    }
  }

  const handleSave = async () => {
    const next: FormErrors = {}
    if (!values.first_name.trim()) next.first_name = 'Wajib diisi'
    if (!values.phone) next.phone = 'Wajib diisi'
    setErrors(next)
    if (Object.keys(next).length > 0) return

    const payload = buildPayload(data, values)
    if (Object.keys(payload).length === 0) {
      setIsEditing(false)
      return
    }

    setSaving(true)
    try {
      await onSave(payload)
      setIsEditing(false)
    } catch {
      // tetap di mode edit; pesan error ditampilkan oleh hook
    } finally {
      setSaving(false)
    }
  }

  // ─── Email ──────────────────────────────────────────────────────────────────

  const handleResendVerification = async () => {
    setResending(true)
    try {
      await onResendVerification()
    } catch {
      // pesan error ditampilkan oleh hook
    } finally {
      setResending(false)
    }
  }

  const resetEmailModal = () => {
    setEmailModalOpen(false)
    setEmailValues(EMPTY_EMAIL_FORM)
    setEmailErrors({})
  }

  const closeEmailModal = () => {
    if (!emailSaving) resetEmailModal()
  }

  const setEmailField = (key: keyof EmailFormValues, value: string) => {
    setEmailValues((prev) => ({ ...prev, [key]: value }))
    setEmailErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const handleChangeEmail = async (e: FormEvent) => {
    e.preventDefault()
    const email_baru = emailValues.email_baru.trim().toLowerCase()
    const next: EmailFormErrors = {}
    if (!email_baru) next.email_baru = 'Wajib diisi'
    else if (!EMAIL_PATTERN.test(email_baru)) next.email_baru = 'Format email tidak valid'
    else if (email_baru === data.email.toLowerCase()) next.email_baru = 'Sama dengan email saat ini'
    if (!emailValues.password) next.password = 'Wajib diisi'
    setEmailErrors(next)
    if (Object.keys(next).length > 0) return

    setEmailSaving(true)
    try {
      await onChangeEmail({ email_baru, password: emailValues.password })
      resetEmailModal()
    } catch {
      // modal tetap terbuka; pesan error ditampilkan oleh hook
    } finally {
      setEmailSaving(false)
    }
  }

  return (
    <>
      <Stack gap="lg">
        {/* Avatar */}
        <Group gap="lg">
          <Avatar size={92} color="brand" variant="filled">
            {initials}
          </Avatar>
          <Group gap="xs">
            <Button loading={avatarBusy} onClick={() => fileInputRef.current?.click()}>
              {hasAvatar ? 'Upload New' : 'Upload'}
            </Button>
            {hasAvatar && (
              <Button
                variant="default"
                disabled={avatarBusy}
                onClick={() => setConfirmDeleteOpen(true)}
              >
                Delete avatar
              </Button>
            )}
          </Group>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            hidden
            onChange={handleFileChange}
          />
        </Group>

        {/* Form */}
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <TextInput
            label="First name"
            withAsterisk
            maxLength={100}
            value={values.first_name}
            error={errors.first_name}
            readOnly={fieldsDisabled}
            onChange={(e) => setField('first_name', e.currentTarget.value)}
          />
          <TextInput
            label="Last name"
            maxLength={100}
            value={values.last_name}
            error={errors.last_name}
            readOnly={fieldsDisabled}
            onChange={(e) => setField('last_name', e.currentTarget.value)}
          />

          {/* Email: tidak diedit langsung, diganti lewat modal + verifikasi tautan */}
          <Stack gap={6}>
            <TextInput
              label="Email"
              value={data.email}
              disabled
              description={
                emailVerified
                  ? 'Terverifikasi'
                  : 'Belum terverifikasi. Verifikasi diperlukan untuk fitur lupa password.'
              }
              rightSection={
                emailVerified ? (
                  <BadgeCheck
                    size={18}
                    aria-label="Email terverifikasi"
                    style={{ color: 'var(--mantine-color-brand-6)' }}
                  />
                ) : undefined
              }
            />
            <Group gap="xs">
              {!emailVerified && !data.pending_email && (
                <Button
                  size="compact-xs"
                  variant="subtle"
                  loading={resending}
                  onClick={handleResendVerification}
                >
                  Kirim ulang verifikasi
                </Button>
              )}
              <Button size="compact-xs" variant="subtle" onClick={() => setEmailModalOpen(true)}>
                Ganti email
              </Button>
            </Group>
            {data.pending_email && (
              <Alert color="blue" variant="light" p="xs">
                <Text size="xs">
                  Menunggu konfirmasi email baru <b>{data.pending_email}</b>. Email akun belum
                  berubah sampai tautan di email tersebut diklik.
                </Text>
              </Alert>
            )}
          </Stack>

          <TextInput
            label="Mobile number"
            withAsterisk
            inputMode="numeric"
            maxLength={13}
            leftSection={
              <Text size="sm" c="dimmed">
                +62
              </Text>
            }
            leftSectionWidth={52}
            value={values.phone}
            error={errors.phone}
            readOnly={fieldsDisabled}
            onChange={(e) => setField('phone', toLocalPhone(e.currentTarget.value))}
          />
          <Radio.Group
            label="Gender"
            value={values.gender ?? ''}
            onChange={(v) => setField('gender', v as Gender)}
          >
            <Group mt="xs" gap="lg">
              <Radio value="male" label="Male" disabled={fieldsDisabled} />
              <Radio value="female" label="Female" disabled={fieldsDisabled} />
            </Group>
          </Radio.Group>
        </SimpleGrid>

        {/* Aksi */}
        <Group gap="xs">
          {isEditing ? (
            <>
              <Button loading={saving} onClick={handleSave}>
                Save Changes
              </Button>
              <Button variant="default" disabled={saving} onClick={() => setIsEditing(false)}>
                Cancel
              </Button>
            </>
          ) : (
            <Button onClick={() => setIsEditing(true)}>Edit Profile</Button>
          )}
        </Group>
      </Stack>

      <ConfirmDialog
        isOpen={confirmDeleteOpen}
        onClose={() => {
          if (!avatarBusy) setConfirmDeleteOpen(false)
        }}
        onConfirm={handleDeleteAvatar}
        isPending={avatarBusy}
        title="Hapus Avatar"
        message="Avatar Anda akan dihapus dan diganti dengan inisial. Lanjutkan?"
        confirmLabel="Ya, Hapus"
        variant="danger"
      />

      <Modal
        opened={emailModalOpen}
        onClose={closeEmailModal}
        title="Ganti email"
        closeOnClickOutside={!emailSaving}
        closeOnEscape={!emailSaving}
        centered
      >
        <form onSubmit={handleChangeEmail} noValidate>
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Kami akan mengirim tautan konfirmasi ke email baru. Email akun Anda baru berubah
              setelah tautan itu diklik; sampai saat itu Anda tetap login dengan email lama.
            </Text>
            <TextInput
              label="Email baru"
              type="email"
              autoComplete="email"
              data-autofocus
              value={emailValues.email_baru}
              error={emailErrors.email_baru}
              onChange={(e) => setEmailField('email_baru', e.currentTarget.value)}
            />
            <PasswordInput
              label="Password saat ini"
              autoComplete="current-password"
              value={emailValues.password}
              error={emailErrors.password}
              onChange={(e) => setEmailField('password', e.currentTarget.value)}
            />
            <Group justify="flex-end" gap="xs">
              <Button variant="default" disabled={emailSaving} onClick={closeEmailModal}>
                Batal
              </Button>
              <Button type="submit" loading={emailSaving}>
                Ganti Email
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </>
  )
}