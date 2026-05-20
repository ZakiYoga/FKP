import { AlertTriangle, Loader2 } from 'lucide-react'
import { Modal } from './Modal'

interface ConfirmDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  isPending?: boolean
  title?: string
  message: string
  confirmLabel?: string
  variant?: 'danger' | 'warning'
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  isPending,
  title = 'Konfirmasi',
  message,
  confirmLabel = 'Ya, Lanjutkan',
  variant = 'danger',
}: ConfirmDialogProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <div className="space-y-4">
        <div className="flex gap-3">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0
            ${variant === 'danger' ? 'bg-red-100' : 'bg-amber-100'}`}>
            <AlertTriangle className={`w-5 h-5
              ${variant === 'danger' ? 'text-red-600' : 'text-amber-600'}`} />
          </div>
          <p className="text-sm text-gray-700 leading-relaxed pt-2">{message}</p>
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button onClick={onClose} disabled={isPending} className="btn-secondary">
            Batal
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className={variant === 'danger' ? 'btn-danger' : 'btn btn-lg bg-amber-500 text-white hover:bg-amber-600'}
          >
            {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  )
}
