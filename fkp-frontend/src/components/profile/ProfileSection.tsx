import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import {
  Alert,
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
import type { Gender, UpdateProfilePayload, UserMe } from '@/types'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { UserAvatar } from '../UserAvatar'

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

// File avatar yang sudah dipilih tetapi belum diupload (menunggu konfirmasi di modal pratinjau).
interface PendingAvatar {
  file: File
  url: string // object URL untuk pratinjau
}

const EMAIL_PATTERN = /^\S+@\S+\.\S+$/
const EMPTY_EMAIL_FORM: EmailFormValues = { email_baru: '', password: '' }

const AVATAR_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const AVATAR_MAX_MB = 2
const AVATAR_MAX_BYTES = AVATAR_MAX_MB * 1024 * 1024

const formatSize = (bytes: number) =>
  bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1024 / 1024).toFixed(2)} MB`

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

  // Avatar
  const [avatarBusy, setAvatarBusy] = useState(false)
  const [pendingAvatar, setPendingAvatar] = useState<PendingAvatar | null>(null)
  const [avatarError, setAvatarError] = useState<string | null>(null)
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pendingRef = useRef<PendingAvatar | null>(null)

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

  // Simpan pratinjau terbaru di ref, lalu lepas object URL-nya saat komponen dilepas.
  useEffect(() => {
    pendingRef.current = pendingAvatar
  }, [pendingAvatar])

  useEffect(() => {
    return () => {
      if (pendingRef.current) URL.revokeObjectURL(pendingRef.current.url)
    }
  }, [])

  const fieldsDisabled = !isEditing || saving
  const emailVerified = Boolean(data.email_verified_at)
  const hasAvatar = Boolean(data.avatar_path)

  const setField = <K extends keyof FormValues>(key: K, value: FormValues[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }))
    setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  // ─── Avatar ─────────────────────────────────────────────────────────────────

  // Ganti pratinjau (atau kosongkan) sambil melepas object URL sebelumnya.
  const replacePending = (next: PendingAvatar | null) => {
    setPendingAvatar((prev) => {
      if (prev) URL.revokeObjectURL(prev.url)
      return next
    })
  }

  // Memilih file TIDAK langsung mengupload: validasi dulu, lalu buka modal pratinjau.
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = '' // izinkan memilih file yang sama lagi
    if (!file) return

    if (!AVATAR_TYPES.includes(file.type)) {
      setAvatarError('Format harus JPG, PNG, atau WebP.')
      return
    }
    if (file.size > AVATAR_MAX_BYTES) {
      setAvatarError(`Ukuran file maksimal ${AVATAR_MAX_MB} MB (file ini ${formatSize(file.size)}).`)
      return
    }

    setAvatarError(null)
    replacePending({ file, url: URL.createObjectURL(file) })
  }

  const closePreview = () => {
    if (avatarBusy) return
    replacePending(null)
  }

  const handleConfirmUpload = async () => {
    if (!pendingAvatar) return
    setAvatarBusy(true)
    try {
      await onUploadAvatar(pendingAvatar.file)
      replacePending(null) // sukses: tutup modal
    } catch {
      // gagal: modal tetap terbuka agar bisa dicoba lagi; pesan error ditampilkan oleh hook
    } finally {
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

  // ─── Profil ─────────────────────────────────────────────────────────────────

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
        <Stack gap={6}>
          <Group gap="lg">
            <UserAvatar user={data} size={92} />
            <Group gap="xs">
              <Button disabled={avatarBusy} onClick={() => fileInputRef.current?.click()}>
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
              accept={AVATAR_TYPES.join(',')}
              hidden
              onChange={handleFileChange}
            />
          </Group>
          {avatarError ? (
            <Text size="xs" c="red">
              {avatarError}
            </Text>
          ) : (
            <Text size="xs" c="dimmed">
              JPG, PNG, atau WebP. Maksimal {AVATAR_MAX_MB} MB.
            </Text>
          )}
        </Stack>

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

      {/* Pratinjau avatar: upload baru terjadi setelah user menekan "Upload" */}
      <Modal
        opened={pendingAvatar !== null}
        onClose={closePreview}
        title="Pratinjau avatar"
        closeOnClickOutside={!avatarBusy}
        closeOnEscape={!avatarBusy}
        withCloseButton={!avatarBusy}
        centered
        size="sm"
      >
        {pendingAvatar && (
          <Stack gap="md" align="center">
            <img
              src={pendingAvatar.url}
              alt="Pratinjau avatar baru"
              className="size-44 rounded-full border border-gray-200 object-cover dark:border-gray-700"
            />
            <div className="text-center">
              <Text size="sm" fw={500} className="max-w-[16rem] truncate">
                {pendingAvatar.file.name}
              </Text>
              <Text size="xs" c="dimmed">
                {formatSize(pendingAvatar.file.size)}
              </Text>
            </div>
            <Text size="xs" c="dimmed" ta="center">
              Gunakan foto persegi (1:1) untuk hasil terbaik.
            </Text>
            <Group justify="space-between" w="100%" gap="xs">
              <Button
                variant="subtle"
                disabled={avatarBusy}
                onClick={() => fileInputRef.current?.click()}
              >
                Pilih ulang
              </Button>
              <Group gap="xs">
                <Button variant="default" disabled={avatarBusy} onClick={closePreview}>
                  Batal
                </Button>
                <Button loading={avatarBusy} onClick={handleConfirmUpload}>
                  Upload
                </Button>
              </Group>
            </Group>
          </Stack>
        )}
      </Modal>

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