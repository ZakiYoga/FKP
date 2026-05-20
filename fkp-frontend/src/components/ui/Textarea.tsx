import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string
  label?: string
  required?: boolean
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, label, required, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className={cn('label', required && 'label-required')}>{label}</label>
        )}
        <textarea
          ref={ref}
          rows={4}
          className={cn('input-base resize-none', error && 'input-error', className)}
          {...props}
        />
        {error && <p className="mt-1.5 text-xs text-red-600">{error}</p>}
      </div>
    )
  },
)
Textarea.displayName = 'Textarea'
