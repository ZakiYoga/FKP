import { Loader2 } from 'lucide-react'
import { useTestimoniForm } from '@/hooks/useTestimoniForm'
import { TestimoniReadOnly } from './TestimoniReadOnly'
import { TestimoniFormFields } from './TestimoniFormFields'

interface Props {
  fkpId: string
  nomorFkp: string
}

function LoadingCard() {
  return (
    <div className="card">
      <div className="card-body flex items-center justify-center py-10 gap-3 text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm">Memuat testimoni...</span>
      </div>
    </div>
  )
}

export function TestimoniForm({ fkpId, nomorFkp }: Props) {
  const {
    form,
    existing,
    isLoading,
    isEditing,
    isPending,
    isDeleting,
    showDeleteConfirm,
    setShowDelete,
    startEdit,
    cancelEdit,
    onSubmit,
    handleHapus,
  } = useTestimoniForm(fkpId)

  if (isLoading) return <LoadingCard />

  if (existing && !isEditing) {
    return (
      <TestimoniReadOnly
        existing={existing}
        nomorFkp={nomorFkp}
        onEdit={startEdit}
        onDelete={() => setShowDelete(true)}
        showDeleteConfirm={showDeleteConfirm}
        onCancelDelete={() => setShowDelete(false)}
        onConfirmDelete={handleHapus}
        isDeleting={isDeleting}
      />
    )
  }

  return (
    <TestimoniFormFields
      form={form}
      nomorFkp={nomorFkp}
      isEditing={isEditing}
      isPending={isPending}
      onCancel={cancelEdit}
      onSubmit={onSubmit}
    />
  )
}