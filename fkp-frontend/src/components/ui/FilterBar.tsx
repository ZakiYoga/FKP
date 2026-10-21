import { useEffect, useId, useRef, useState } from 'react'
import { ChevronUp, Search, X } from 'lucide-react'
import { Button } from '@mantine/core'
import clsx from 'clsx'
import { FilterSelect, filterFieldClass } from '@/components/fkp/FilterSelect'
import type { FilterOption } from '@/components/fkp/FilterSelect'
import { SearchableSelect } from '@/components/ui/SearchableSelect'

export type { FilterOption }

// ─── Tipe konfigurasi field ──────────────────────────────────────────────────

interface BaseField {
  /** Kunci unik untuk React key. */
  key: string
  /** Sembunyikan field (mis. berdasarkan role). Field tersembunyi tidak dihitung dan tidak di-reset. */
  hidden?: boolean
}

export interface SelectFilterField extends BaseField {
  type: 'select'
  label: string
  /** '' berarti belum ada filter. */
  value: string
  onChange: (v: string) => void
  options: FilterOption[]
  /** Teks saat belum ada pilihan, mis. "Semua Status". */
  placeholder: string
  /** true: kolom ketik dengan pencarian (SearchableSelect). false/kosong: select biasa. */
  searchable?: boolean
  /** Hanya berlaku untuk searchable. */
  loading?: boolean
}

export interface DateRangeFilterField extends BaseField {
  type: 'date-range'
  from: string
  to: string
  onFromChange: (v: string) => void
  onToChange: (v: string) => void
  fromLabel?: string
  toLabel?: string
}

export interface ToggleFilterField extends BaseField {
  type: 'toggle'
  /** Teks di samping checkbox, mis. "Tampilkan nonaktif". */
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
}

export type FilterBarField = SelectFilterField | DateRangeFilterField | ToggleFilterField

export interface FilterBarProps {
  search: string
  onSearchChange: (v: string) => void
  searchPlaceholder?: string
  /** Isi card filter, dirender sesuai urutan array. */
  fields: FilterBarField[]
  /**
   * Dipanggil saat tombol Reset ditekan (setelah search dikosongkan).
   * Bila tidak diisi, setiap field yang tampil dikosongkan lewat onChange-nya sendiri.
   */
  onReset?: () => void
  /** Jeda (ms) sebelum ketikan di search diteruskan ke parent. */
  debounceMs?: number
}

// ─── Konstanta ───────────────────────────────────────────────────────────────

// Dropdown/popover yang di-portal (Mantine) tidak boleh dianggap "klik di luar"
const PORTAL_SELECTOR =
  '.mantine-Popover-dropdown, [data-combobox-dropdown], [data-portal="true"], [role="listbox"]'

// `inert` didukung runtime React 19, tapi belum ada di versi @types/react tertentu.
// Kalau @types/react sudah ^19, helper ini boleh dihapus dan dipakai `inert={...}` langsung.
const inertProps = (on: boolean): Record<string, unknown> => (on ? { inert: true } : {})

// Layout flex-wrap: tiap field punya lebar dasar (basis) lalu `grow` membagi sisa ruang,
// jadi berapa pun field yang tampil, setiap baris selalu terisi penuh tanpa ruang kosong.
const FIELD_BASIS = 'grow basis-48' // select: ±12rem
const DATE_GROUP_BASIS = 'grow basis-72' // pasangan tanggal: ±18rem, tetap berdampingan

const DEFAULT_DEBOUNCE_MS = 300

// ─── Field ───────────────────────────────────────────────────────────────────

interface FieldProps {
  label: string
  className?: string
  // 'div' untuk SearchableSelect: <label> pembungkus akan meneruskan klik ke input
  // dan bisa membuat dropdown terbuka lalu langsung menutup.
  as?: 'label' | 'div'
  children: React.ReactNode
}

function Field({ label, className, as: Tag = 'label', children }: FieldProps) {
  return (
    <Tag className={clsx('flex flex-col gap-1 min-w-0', className)}>
      <span className="text-xs font-medium text-gray-600">{label}</span>
      {children}
    </Tag>
  )
}

function countActive(fields: FilterBarField[]): number {
  return fields.reduce((total, f) => {
    if (f.type === 'select') return total + Number(Boolean(f.value))
    if (f.type === 'toggle') return total + Number(f.checked)
    return total + Number(Boolean(f.from)) + Number(Boolean(f.to))
  }, 0)
}

// ─── Komponen ────────────────────────────────────────────────────────────────

export function FilterBar({
  search,
  onSearchChange,
  searchPlaceholder = 'Cari...',
  fields,
  onReset,
  debounceMs = DEFAULT_DEBOUNCE_MS,
}: FilterBarProps) {
  const visibleFields = fields.filter((f) => !f.hidden)

  // Search di-debounce: input lokal langsung responsif, parent (dan query-nya) baru
  // diberi nilai setelah user berhenti mengetik.
  const [searchInput, setSearchInput] = useState(search)
  const lastEmittedSearch = useRef(search) // nilai terakhir yang sudah dikirim ke parent

  useEffect(() => {
    if (searchInput === lastEmittedSearch.current) return
    const timer = setTimeout(() => {
      lastEmittedSearch.current = searchInput
      onSearchChange(searchInput)
    }, debounceMs)
    return () => clearTimeout(timer)
  }, [searchInput, onSearchChange, debounceMs])

  // Perubahan dari luar (mis. parent mengosongkan search) disinkronkan ke input lokal.
  // Perubahan hasil debounce sendiri diabaikan agar tidak menimpa teks yang sedang diketik.
  useEffect(() => {
    if (search !== lastEmittedSearch.current) {
      lastEmittedSearch.current = search
      setSearchInput(search)
    }
  }, [search])

  const [open, setOpen] = useState(false)
  const panelId = useId()
  const buttonRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  // Jumlah filter aktif di dalam card (search tidak dihitung)
  const activeCount = countActive(visibleFields)
  // Pakai searchInput agar tombol Reset langsung muncul saat mengetik, tanpa menunggu debounce
  const hasFilter = activeCount > 0 || Boolean(searchInput)

  const clearAll = () => {
    // Kosongkan input lokal segera dan batalkan debounce yang sedang menunggu
    lastEmittedSearch.current = ''
    setSearchInput('')
    onSearchChange('')

    if (onReset) {
      onReset()
      return
    }
    for (const f of visibleFields) {
      if (f.type === 'select') {
        f.onChange('')
      } else if (f.type === 'toggle') {
        f.onChange(false)
      } else {
        f.onFromChange('')
        f.onToChange('')
      }
    }
  }

  // Tutup saat klik di luar atau Escape. Nilai filter tidak disentuh.
  useEffect(() => {
    if (!open) return

    const onPointerDown = (e: PointerEvent) => {
      const target = e.target as Node | null
      if (!(target instanceof Element)) return
      if (!target.isConnected) return // elemen sudah dilepas dari DOM (mis. opsi dropdown)
      if (panelRef.current?.contains(target)) return
      if (buttonRef.current?.contains(target)) return // toggle ditangani onClick
      if (target.closest(PORTAL_SELECTOR)) return
      setOpen(false)
    }

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || e.defaultPrevented) return
      // Dropdown yang sedang terbuka menutup lebih dulu
      if (panelRef.current?.querySelector('[aria-expanded="true"]')) return
      if (document.querySelector(PORTAL_SELECTOR)) return
      if (panelRef.current?.contains(document.activeElement)) buttonRef.current?.focus()
      setOpen(false)
    }

    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div>
      {/* Baris utama: search + Filter + Reset */}
      <div className="flex items-center">
        <div className="relative flex-1 min-w-0">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder={searchPlaceholder}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="input-base pl-9 py-0 h-9 w-full"
          />
        </div>

        {visibleFields.length > 0 && (
          <Button
            ref={buttonRef}
            type="button"
            variant="subtle"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls={panelId}
            className={clsx(
              'ml-2 shrink-0 inline-flex items-center px-3 text-sm rounded-lg border',
              'transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-brand-500/30',
              open
                ? 'border-brand-400 text-brand-500'
                : 'border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300',
            )}
          >
            Filter
            {activeCount > 0 && (
              <span className="min-w-5 text-white ml-1 h-5 px-1.5 inline-flex items-center justify-center rounded-full bg-brand-500 text-xs font-medium leading-none">
                {activeCount}
              </span>
            )}
            <ChevronUp
              className={clsx(
                'w-4 h-4 transition-transform duration-200 ease-in-out motion-reduce:transition-none',
                open && 'rotate-180',
              )}
            />
          </Button>
        )}

        {/* Reset: lebar dianimasikan agar search menyesuaikan dengan mulus */}
        <div
          {...inertProps(!hasFilter)}
          aria-hidden={!hasFilter}
          className={clsx(
            'grid transition-[grid-template-columns,opacity] duration-200 ease-in-out motion-reduce:transition-none',
            hasFilter ? 'grid-cols-[1fr] opacity-100' : 'grid-cols-[0fr] opacity-0',
          )}
        >
          <div className="overflow-hidden min-w-0">
            <Button
              type="button"
              variant="outline"
              onClick={clearAll}
              className="ml-2 inline-flex border items-center gap-1 text-red-500 border-red-500 h-9 px-3 text-sm whitespace-nowrap rounded-lg
                        hover:text-red-700 hover:bg-red-100 hover:border-red-600 transition-colors
                         focus-visible:outline-hidden"
            >
              <X className="w-3.5 h-3.5" />
              Reset
            </Button>
          </div>
        </div>
      </div>

      {/* Card filter — tinggi dianimasikan via grid-template-rows */}
      {visibleFields.length > 0 && (
        <div
          id={panelId}
          ref={panelRef}
          {...inertProps(!open)}
          aria-hidden={!open}
          className={clsx(
            'grid transition-[grid-template-rows,opacity,transform,visibility] duration-200',
            'motion-reduce:transition-none motion-reduce:translate-y-0',
            open
              ? 'grid-rows-[1fr] opacity-100 translate-y-0 visible ease-out'
              : 'grid-rows-[0fr] opacity-0 -translate-y-1 invisible ease-in',
          )}
        >
          <div className="overflow-hidden min-h-0">
            <div className="mt-3 rounded-lg border border-gray-200 bg-white p-4">
              <div className="flex flex-wrap gap-3">
                {visibleFields.map((field) => {
                  if (field.type === 'select') {
                    return (
                      <Field
                        key={field.key}
                        label={field.label}
                        as={field.searchable ? 'div' : 'label'}
                        className={FIELD_BASIS}
                      >
                        {field.searchable ? (
                          <SearchableSelect
                            aria-label={field.label}
                            value={field.value || null}
                            onChange={(v) => field.onChange(v ?? '')}
                            placeholder={field.placeholder}
                            options={field.options}
                            loading={field.loading}
                          />
                        ) : (
                          <FilterSelect
                            value={field.value}
                            onChange={field.onChange}
                            placeholder={field.placeholder}
                            options={field.options}
                          />
                        )}
                      </Field>
                    )
                  }

                  if (field.type === 'toggle') {
                    return (
                      <label
                        key={field.key}
                        className={clsx(
                          'flex items-center gap-2 self-end h-9 min-w-0 text-sm text-gray-700 cursor-pointer select-none',
                          FIELD_BASIS,
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={field.checked}
                          onChange={(e) => field.onChange(e.target.checked)}
                          className="rounded-sm border-gray-300 text-brand-600"
                        />
                        {field.label}
                      </label>
                    )
                  }

                  // date-range: dua tanggal dibungkus satu grup agar selalu berdampingan
                  return (
                    <div key={field.key} className={clsx('flex gap-3 min-w-0', DATE_GROUP_BASIS)}>
                      <Field label={field.fromLabel ?? 'Tanggal Mulai'} className="flex-1">
                        <input
                          type="date"
                          value={field.from}
                          max={field.to || undefined}
                          onChange={(e) => field.onFromChange(e.target.value)}
                          className={clsx(filterFieldClass, 'py-0', !field.from && 'text-gray-500')}
                        />
                      </Field>
                      <Field label={field.toLabel ?? 'Tanggal Selesai'} className="flex-1">
                        <input
                          type="date"
                          value={field.to}
                          min={field.from || undefined}
                          onChange={(e) => field.onToChange(e.target.value)}
                          className={clsx(filterFieldClass, 'py-0', !field.to && 'text-gray-500')}
                        />
                      </Field>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}