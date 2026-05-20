import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: string
  label?: string
  required?: boolean
  placeholder?: string
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, error, label, required, placeholder, children, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className={cn('label', required && 'label-required')}>
            {label}
          </label>
        )}
        <select
          ref={ref}
          className={cn('input-base', error && 'input-error', className)}
          {...props}
        >
          {placeholder && (
            <option value="">{placeholder}</option>
          )}
          {children}
        </select>
        {error && <p className="mt-1.5 text-xs text-red-600">{error}</p>}
      </div>
    )
  },
)
Select.displayName = 'Select'
