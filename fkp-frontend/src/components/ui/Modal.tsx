import { useEffect } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string | undefined
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const SIZE_MAP = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-2xl',
}

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  // Tutup modal dengan Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  // Lock scroll saat modal terbuka
  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-xs animate-fade-in"
        onClick={onClose}
      />
      {/* Panel */}
      <div
        className={cn(
          'relative w-full bg-white rounded-2xl shadow-modal animate-slide-up',
          SIZE_MAP[size],
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-gray-100">
          <h3 className="text-base font-semibold text-gray-900">{title}</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        {/* Content */}
        <div className="sm:px-6 px-4 py-5">{children}</div>
      </div>
    </div>
  )
}
