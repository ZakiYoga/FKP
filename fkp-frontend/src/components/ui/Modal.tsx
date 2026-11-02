import { useEffect } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string | undefined
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const SIZE_MAP = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-2xl',
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
}: ModalProps) {
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

    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'modal-title' : undefined}
        className={cn(
          'relative flex max-h-[85vh] w-full flex-col overflow-hidden',
          'rounded-2xl border border-gray-200/80 dark:border-gray-700/70',
          'bg-white dark:bg-gray-900',
          'shadow-xl shadow-black/10 dark:shadow-black/40',
          'animate-slide-up',
          SIZE_MAP[size],
        )}
      >
        {/* Header */}
        <div
          className={cn(
            'flex shrink-0 items-center px-4 py-4 sm:px-6',
            'border-gray-100 dark:border-gray-800',
            title
              ? 'justify-between border-b'
              : 'justify-end',
          )}
        >
          {title && (
            <h2
              id="modal-title"
              className="text-lg font-semibold tracking-tight text-gray-900 dark:text-gray-100"
            >
              {title}
            </h2>
          )}

          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup modal"
            className={cn(
              'rounded-lg p-2 transition-colors duration-200',
              'text-gray-400 hover:text-gray-700',
              'hover:bg-gray-100',
              'dark:text-gray-400 dark:hover:text-gray-100',
              'dark:hover:bg-gray-800',
              'focus-visible:outline-none focus-visible:ring-2',
              'focus-visible:ring-blue-500 focus-visible:ring-offset-2',
              'dark:focus-visible:ring-offset-gray-900',
            )}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div
          className={cn(
            'overflow-y-auto px-4 py-5 sm:px-6',
            'text-gray-700 dark:text-gray-300',
            '[&_h1]:text-gray-900 dark:[&_h1]:text-gray-100',
            '[&_h2]:text-gray-900 dark:[&_h2]:text-gray-100',
            '[&_h3]:text-gray-800 dark:[&_h3]:text-gray-200',
          )}
        >
          {children}
        </div>
      </div>
    </div>
  )
}