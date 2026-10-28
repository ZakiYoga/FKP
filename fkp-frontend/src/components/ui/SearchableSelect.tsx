import { useRef } from 'react'
import type { FocusEventHandler, KeyboardEvent, Ref } from 'react'
import { Loader, Select } from '@mantine/core'
import type { ComboboxProps } from '@mantine/core'
import { useReducedMotion } from '@mantine/hooks'
import { cn } from '@/lib/utils'

export interface SearchableSelectOption {
  value: string
  label: string
  disabled?: boolean
}

export interface SearchableSelectProps<TOption extends SearchableSelectOption = SearchableSelectOption> {
  /** Data dari parent. Komponen ini tidak melakukan API call. */
  options: TOption[]
  /** Nilai terpilih = `value` option (id), bukan label. */
  value: string | null
  /** Hanya terpanggil saat user memilih item atau menekan clear. Mengetik saja tidak memanggilnya. */
  onChange: (value: string | null) => void
  label?: string
  placeholder?: string
  nothingFoundMessage?: string
  loading?: boolean
  clearable?: boolean
  /** false: tampil sebagai select biasa (tanpa ketik/cari), cocok untuk daftar pendek. Default true. */
  searchable?: boolean
  searchValue?: string
  onSearchChange?: (value: string) => void
  disabled?: boolean
  /** Tampil seperti input aktif, tapi dropdown tidak bisa dibuka dan nilai tidak bisa diubah. */
  readOnly?: boolean // BARU
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  error?: string
  required?: boolean
  /** Batas jumlah item yang dirender di dropdown. */
  limit?: number
  id?: string
  name?: string
  /** Untuk pemakaian tanpa `label` (mis. label sudah dirender parent). */
  'aria-label'?: string
  className?: string
  /** Diteruskan ke Combobox Mantine (mis. zIndex bila dipakai di dalam modal custom). */
  comboboxProps?: ComboboxProps
  /** Untuk react-hook-form: field.onBlur / field.ref dari Controller. */
  onBlur?: FocusEventHandler<HTMLInputElement>
  ref?: Ref<HTMLInputElement>
}

// Mantine v9 bergaya via CSS bawaannya. Modifier `!` (important Tailwind v4) dipakai agar
// kelas Tailwind tetap menang walau CSS Mantine tidak dibungkus @layer.
const CLASS_NAMES = {
  label: 'mb-1 font-semibold text-gray-700 dark:text-gray-400',
  input:
    'border-gray-300 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-200 placeholder:text-gray-400 ' +
    'focus:border-brand-400! dark:border-[var(--mantine-color-gray-7)] focus:ring-2 focus:ring-brand-500/20',
  dropdown: 'border-gray-200 bg-white dark:bg-gray-900',
  option:
    'text-sm data-combobox-selected:bg-brand-50! data-combobox-selected:text-gray-900! ' +
    'data-checked:font-medium',
  empty: 'text-sm text-gray-500',
}

export function SearchableSelect<TOption extends SearchableSelectOption = SearchableSelectOption>({
  options,
  value,
  onChange,
  label,
  placeholder,
  nothingFoundMessage = 'Data tidak ditemukan',
  loading = false,
  clearable = true,
  searchable = true,
  searchValue,
  onSearchChange,
  disabled,
  readOnly,
  error,
  required,
  limit = 100,
  id,
  name,
  'aria-label': ariaLabel,
  className,
  comboboxProps,
  onBlur,
  ref,
}: SearchableSelectProps<TOption>) {
  const reduceMotion = useReducedMotion()
  // Ref (bukan state) agar tidak memicu render: hanya perlu tahu dropdown sedang terbuka atau tidak.
  const dropdownOpenRef = useRef(false)

  // Nilai yang sudah tidak ada di options (daftar berganti / belum dimuat) ditampilkan kosong,
  // tanpa memanggil onChange. Nilai di parent tidak diubah.
  const safeValue = value !== null && options.some((o) => o.value === value) ? value : null

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!dropdownOpenRef.current) return
    // Enter saat dropdown terbuka tidak boleh men-submit form (termasuk saat tidak ada yang cocok).
    // Pemilihan item tersorot tetap ditangani Mantine.
    if (e.key === 'Enter') e.preventDefault()
    // Escape menutup dropdown saja, tidak naik ke handler Escape milik card/modal di atasnya.
    if (e.key === 'Escape') e.stopPropagation()
  }

  return (
    <Select
      ref={ref}
      id={id}
      name={name}
      aria-label={ariaLabel}
      className={cn(className)}
      classNames={CLASS_NAMES}
      size="md"
      radius="md"
      data={options}
      value={safeValue}
      onChange={(next) => onChange(next)}
      onBlur={onBlur}
      onKeyDown={handleKeyDown}
      onDropdownOpen={() => {
        dropdownOpenRef.current = true
      }}
      onDropdownClose={() => {
        dropdownOpenRef.current = false
      }}
      label={label}
      placeholder={placeholder}
      // Validasi diserahkan ke form library; asterisk saja, tanpa atribut `required` native.
      withAsterisk={required}
      error={error}
      disabled={disabled}
      readOnly={readOnly} // BARU
      searchable={searchable}
      searchValue={searchValue}
      onSearchChange={onSearchChange}
      clearable={clearable}
      // Satu-satunya cara menghapus nilai adalah tombol clear, bukan klik ulang item terpilih.
      allowDeselect={false}
      // Item pertama yang cocok langsung tersorot, cukup ketik lalu Enter.
      selectFirstOptionOnChange
      // Saat loading, "Data tidak ditemukan" tidak ditampilkan.
      nothingFoundMessage={loading ? undefined : nothingFoundMessage}
      rightSection={loading ? <Loader size={14} /> : undefined}
      limit={limit}
      maxDropdownHeight={240}
      comboboxProps={{
        // Portal bawaan Mantine dibiarkan aktif agar dropdown tidak terpotong card/modal.
        shadow: 'sm',
        radius: 'md',
        transitionProps: { duration: reduceMotion ? 0 : 100 },
        ...comboboxProps,
      }}
    />
  )
}