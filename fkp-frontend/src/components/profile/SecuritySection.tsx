import { useState } from 'react'
import type { FormEvent } from 'react'
import { Button, PasswordInput, Stack, Text, Title } from '@mantine/core'
import { PASSWORD_RULE_HINT, validateNewPassword } from '@/lib/password'

// Handler boleh sinkron (void) atau async (Promise). Jika Promise,
// field hanya dikosongkan setelah berhasil (tetap terisi jika gagal).
interface SecuritySectionProps {
  onSubmit: (values: { oldPassword: string; newPassword: string }) => void | Promise<unknown>
}

interface Values {
  oldPassword: string
  newPassword: string
  confirmPassword: string
}

type Errors = Partial<Record<keyof Values, string>>

const EMPTY: Values = { oldPassword: '', newPassword: '', confirmPassword: '' }

export function SecuritySection({ onSubmit }: SecuritySectionProps) {
  const [values, setValues] = useState<Values>(EMPTY)
  const [errors, setErrors] = useState<Errors>({})
  const [submitting, setSubmitting] = useState(false)

  const setField = (key: keyof Values, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }))
    setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const validate = (): Errors => {
    const next: Errors = {}
    // Password lama sengaja tanpa batas panjang: password yang dibuat sebelum
    // aturan ini ada tetap harus bisa dimasukkan.
    if (!values.oldPassword) next.oldPassword = 'Wajib diisi'

    // Aturan password baru berasal dari satu sumber: src/lib/password.ts
    const newPasswordError = validateNewPassword(values.newPassword)
    if (newPasswordError) next.newPassword = newPasswordError

    if (!values.confirmPassword) next.confirmPassword = 'Wajib diisi'
    else if (values.confirmPassword !== values.newPassword) {
      next.confirmPassword = 'Password tidak sama'
    }
    return next
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const next = validate()
    setErrors(next)
    if (Object.keys(next).length > 0) return

    setSubmitting(true)
    try {
      await onSubmit({ oldPassword: values.oldPassword, newPassword: values.newPassword })
      setValues(EMPTY)
      setErrors({})
    } catch {
      // field tetap terisi; pesan error ditampilkan oleh hook
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Stack gap="md" maw={420}>
        <div>
          <Title order={4}>Ubah Password</Title>
          <Text size="sm" c="dimmed">
            {PASSWORD_RULE_HINT}
          </Text>
        </div>

        <PasswordInput
          label="Password lama"
          autoComplete="current-password"
          value={values.oldPassword}
          error={errors.oldPassword}
          disabled={submitting}
          onChange={(e) => setField('oldPassword', e.currentTarget.value)}
        />
        <PasswordInput
          label="Password baru"
          autoComplete="new-password"
          value={values.newPassword}
          error={errors.newPassword}
          disabled={submitting}
          onChange={(e) => setField('newPassword', e.currentTarget.value)}
        />
        <PasswordInput
          label="Ulangi password baru"
          autoComplete="new-password"
          value={values.confirmPassword}
          error={errors.confirmPassword}
          disabled={submitting}
          onChange={(e) => setField('confirmPassword', e.currentTarget.value)}
        />

        <div>
          <Button type="submit" loading={submitting}>
            Ubah Password
          </Button>
        </div>
      </Stack>
    </form>
  )
}