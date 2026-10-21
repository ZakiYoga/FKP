import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Kartu generik untuk halaman daftar (Distributor, Outlet, dst.).
 *
 * Props:
 * - code     : kode kecil monospace di kiri atas
 * - badge    : elemen di kanan atas (badge status)
 * - title    : judul utama (satu baris, dipotong jika panjang)
 * - subtitle : teks di bawah judul (mis. nama pemilik)
 * - meta     : baris info dengan ikon opsional. Item false/null dilewati.
 *              clamp: true -> maks 2 baris; default 1 baris dipotong "…"
 * - actions  : slot tombol aksi. Jika kosong, area aksi tidak dirender.
 */
export interface EntityCardMeta {
  icon?: LucideIcon
  text: ReactNode
  clamp?: boolean
  tone?: 'default' | 'warning'
}

export interface EntityCardProps {
  code: string
  badge?: ReactNode
  title: ReactNode
  subtitle?: ReactNode
  meta?: Array<EntityCardMeta | false | null | undefined | ''>
  actions?: ReactNode
  className?: string
}

export function EntityCard({
  code, badge, title, subtitle, meta = [], actions, className,
}: EntityCardProps) {
  const items = meta.filter((m): m is EntityCardMeta => Boolean(m))

  return (
    <div className={cn('card p-5', className)}>
      <div className="w-full flex justify-between">
        <p className="text-xs font-mono text-gray-400">{code}</p>
        {badge}
      </div>

      <h3 className="font-semibold mt-0.5 truncate first-letter:uppercase">{title}</h3>
      {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}

      {items.length > 0 && (
        <div className="mt-3 space-y-1">
          {items.map((m, i) => {
            const Icon = m.icon
            return (
              <div
                key={i}
                className={cn(
                  'flex items-start gap-1.5 text-xs',
                  m.tone === 'warning' ? 'text-amber-700 dark:text-amber-400' : 'text-gray-400',
                )}
              >
                {Icon && <Icon className="w-3.5 h-3.5 shrink-0 mt-0.5" />}
                <span className={cn('min-w-0', m.clamp ? 'line-clamp-2' : 'truncate')}>
                  {m.text}
                </span>
              </div>
            )
          })}
        </div>
      )}

      {actions && (
        <div className="mt-4 pt-3 border-t border-gray-300/60 dark:border-gray-700 space-y-2">
          {actions}
        </div>
      )}
    </div>
  )
}

// ── Tombol ikon (aktifkan / nonaktifkan) ──
const TONE = {
  danger: 'text-red-600 border-red-300 dark:border-red-500 hover:text-red-400 hover:bg-red-100 dark:hover:bg-red-800',
  success: 'text-green-600 hover:bg-green-100 dark:hover:bg-green-800',
} as const

export function EntityCardIconButton({
  icon: Icon, tone, label, onClick,
}: {
  icon: LucideIcon
  tone: keyof typeof TONE
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className={cn(
        'border border-gray-300 dark:border-gray-700 btn-sm rounded-lg',
        TONE[tone],
      )}
    >
      <Icon className="w-3.5 h-3.5" />
    </button>
  )
}