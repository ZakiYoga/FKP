import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import type { BreadcrumbItem } from '@/components/ui/PageBreadcrumb'

interface PageHeaderProps {
  title: string
  description?: ReactNode
  /** Tombol aksi di sisi kanan. Maksimal 2 tombol (1 atau 2). */
  actions?: ReactNode
  /** Icon button back, dirender di kiri judul. */
  backButton?: ReactNode
  /** @deprecated Breadcrumb kini dirender di Header dari route `handle.crumbs`. Prop ini diabaikan. */
  breadcrumbs?: BreadcrumbItem[]
  className?: string
}

export default function PageHeader({
  title, description, actions, backButton, className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center',
        className,
      )}
    >
      <div className="flex min-w-0 items-start gap-2">
        {backButton && (
          <div className="-ml-2 flex h-8 shrink-0 items-center">{backButton}</div>
        )}
        <div className="min-w-0">
          <h1 className="text-2xl font-bold">{title}</h1>
          {description && (
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">{description}</p>
          )}
        </div>
      </div>

      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}