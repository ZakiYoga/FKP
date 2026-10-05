import { AlertTriangle, CheckCircle2, Info, Loader2 } from 'lucide-react'
import { Modal } from './Modal'

type Variant = 'danger' | 'warning' | 'success' | 'info'

interface ConfirmDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  isPending?: boolean
  title?: string
  message: string
  confirmLabel?: string
  variant?: Variant
}

const VARIANTS: Record<Variant, {
  icon: typeof AlertTriangle
  iconBg: string
  iconColor: string
  button: string
}> = {
  danger: {
    icon: AlertTriangle,
    iconBg: 'bg-red-100',
    iconColor: 'text-red-600',
    button: 'btn-danger',
  },
  warning: {
    icon: AlertTriangle,
    iconBg: 'bg-amber-100',
    iconColor: 'text-amber-600',
    button: 'btn btn-md bg-amber-500 text-white hover:bg-amber-600',
  },
  success: {
    icon: CheckCircle2,
    iconBg: 'bg-emerald-100',
    iconColor: 'text-emerald-600',
    button: 'btn-primary',
  },
  info: {
    icon: Info,
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-600',
    button: 'btn-primary',
  },
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  isPending,
  title,
  message,
  confirmLabel = 'Ya, Lanjutkan',
  variant = 'danger',
}: ConfirmDialogProps) {
  const v = VARIANTS[variant]
  const Icon = v.icon

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="sm">
      <div className="space-y-4">
        <div className="flex flex-col items-center justify-center gap-3">
          <div className={`w-16 h-16 rounded-full flex items-center justify-center shrink-0 ${v.iconBg}`}>
            <Icon className={`w-8 h-8 ${v.iconColor}`} />
          </div>
          <p className="text-sm text-center text-gray-700 leading-relaxed pt-2">{message}</p>
        </div>
        <div className="flex gap-2 items-center justify-center pt-2">
          <button type="button" onClick={onClose} disabled={isPending} className="btn-secondary">
            Batal
          </button>
          <button type="button" onClick={onConfirm} disabled={isPending} className={v.button}>
            {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  )
}