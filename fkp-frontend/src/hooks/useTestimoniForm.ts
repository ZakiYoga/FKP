import { useState, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  useTestimoniMilikSaya,
  useCreateTestimoni,
  useUpdateTestimoni,
  useDeleteTestimoni,
} from '@/hooks/useTestimoni'
import {
  testimoniSchema,
  TESTIMONI_DEFAULT_VALUES,
  toTestimoniFormValues,
  type TestimoniFormValues,
} from '@/schemas/testimoniSchema'
import type { TestimoniCreatePayload } from '@/types/testimoni'

export function useTestimoniForm(fkpId: string) {
  const [isEditing, setIsEditing]          = useState(false)
  const [showDeleteConfirm, setShowDelete] = useState(false)

  const { data: existing, isLoading } = useTestimoniMilikSaya(fkpId)

  const { mutateAsync: create, isPending: isCreating } = useCreateTestimoni(fkpId)
  const { mutateAsync: update, isPending: isUpdating } = useUpdateTestimoni(
    fkpId,
    existing?.id ?? '',
  )
  const { mutate: hapus, isPending: isDeleting } = useDeleteTestimoni(fkpId)

  const form = useForm<TestimoniFormValues>({
    resolver: zodResolver(testimoniSchema),
    defaultValues: TESTIMONI_DEFAULT_VALUES,
  })

  /**
   * Fix bug timing: reset form SEBELUM set isEditing=true
   * existing dijamin ada karena tombol Edit hanya muncul saat existing tidak null
   */
  const startEdit = useCallback(() => {
    if (!existing) return
    form.reset(toTestimoniFormValues(existing))
    setIsEditing(true)
  }, [existing, form])

  const cancelEdit = useCallback(() => {
    setIsEditing(false)
    form.reset(TESTIMONI_DEFAULT_VALUES)
  }, [form])

  const onSubmit = async (values: TestimoniFormValues) => {
    const payload: TestimoniCreatePayload = {
      rating_keseluruhan: values.rating_keseluruhan ?? null,
      rating_kecepatan:   values.rating_kecepatan ?? null,
      rating_komunikasi:  values.rating_komunikasi ?? null,
      rating_solusi:      values.rating_solusi ?? null,
      rating_aplikasi:    values.rating_aplikasi ?? null,
      komentar:           values.komentar         ?? null,
      kritik_saran_tim:   values.kritik_saran_tim ?? null,
      kritik_saran_app:   values.kritik_saran_app ?? null,
      is_public:          values.is_public,
    }
    if (existing) {
      await update(payload)
    } else {
      await create(payload)
    }
    setIsEditing(false)
  }

  const handleHapus = useCallback(() => {
    if (!existing) return
    hapus(existing.id)
    setShowDelete(false)
  }, [existing, hapus])

  return {
    form,
    existing,
    isLoading,
    isEditing,
    isPending: isCreating || isUpdating,
    isDeleting,
    showDeleteConfirm,
    setShowDelete,
    startEdit,
    cancelEdit,
    onSubmit,
    handleHapus,
  }
}
