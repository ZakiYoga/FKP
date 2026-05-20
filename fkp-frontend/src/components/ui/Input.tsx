import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string | undefined
  label?: string | undefined
  required?: boolean | undefined
  icon?: React.ReactNode  // tambah ini
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, label, required, icon, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className={cn('label', required && 'label-required')}>{label}</label>
        )}
        <div className={cn('relative', icon && 'flex items-center')}>
          {icon && (
            <span className="absolute left-3 text-gray-400 pointer-events-none">
              {icon}
            </span>
          )}
          <input
            ref={ref}
            className={cn(
              'input-base',
              icon && 'pl-9',        // beri padding kiri jika ada icon
              error && 'input-error',
              className
            )}
            {...props}
          />
        </div>
        {error && <p className="mt-1.5 text-xs text-red-600">{error}</p>}
      </div>
    )
  },
)
Input.displayName = 'Input'