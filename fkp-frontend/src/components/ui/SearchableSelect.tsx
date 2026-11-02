import { useEffect, useMemo } from 'react'
import type { KeyboardEvent, Ref } from 'react'
import { CloseButton, Combobox, Input, InputBase, Loader, ScrollArea, useCombobox } from '@mantine/core'
import type { ComboboxProps } from '@mantine/core'
import { useReducedMotion, useUncontrolled } from '@mantine/hooks'
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
  /** Placeholder kolom cari di dalam dropdown. */
  searchPlaceholder?: string
  loading?: boolean
  clearable?: boolean
  /** false: tampil sebagai select biasa (tanpa kolom cari), cocok untuk daftar pendek. Default true. */
  searchable?: boolean
  searchValue?: string
  onSearchChange?: (value: string) => void
  disabled?: boolean
  /** Tampil seperti input aktif, tapi dropdown tidak bisa dibuka dan nilai tidak bisa diubah. */
  readOnly?: boolean
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
  /** Untuk react-hook-form: field.onBlur / field.ref dari Controller. Elemen target kini berupa <button>. */
  onBlur?: () => void
  ref?: Ref<HTMLButtonElement>
}

// Mantine v9 bergaya via CSS bawaannya. Modifier `!` (important Tailwind v4) dipakai agar
// kelas Tailwind tetap menang walau CSS Mantine tidak dibungkus @layer.
const CLASS_NAMES = {
  label: 'mb-1 font-semibold text-gray-700 dark:text-gray-400',
  // Target berupa <button multiline>, jadi nama terpilih yang panjang turun ke baris berikutnya.
  input:
    'border-gray-300 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-200 placeholder:text-gray-400 ' +
    'focus:border-brand-400! dark:border-[var(--mantine-color-gray-7)] focus:ring-2 focus:ring-brand-500/20 ' +
    'text-left whitespace-normal! break-words! leading-snug',
  searchInput:
    'border-gray-300 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-200 placeholder:text-gray-400 ' +
    'focus:border-brand-400! dark:border-[var(--mantine-color-gray-7)]',
  dropdown: 'border-gray-200 bg-white dark:bg-gray-900',
  option:
    'text-sm whitespace-normal! break-words! leading-snug ' +
    'data-combobox-selected:bg-brand-50! data-combobox-selected:text-gray-900! ' +
    'data-checked:font-medium data-checked:bg-brand-100! data-checked:text-gray-900! ' +
    'data-disabled:text-gray-400 data-disabled:cursor-not-allowed',
  empty: 'text-sm text-gray-500',
}

// Pencarian multi-kata: kata kunci dipecah jadi token, dan SEMUA token harus ada di label.
// Urutan bebas dan tidak peka huruf besar/kecil, jadi "sakti orange" cocok dengan
// "SAKTI TEPUNG ROTI ORANGE 10 KG".
function filterByTokens<T extends SearchableSelectOption>(options: T[], search: string): T[] {
  const tokens = search.toLowerCase().trim().split(/\s+/).filter(Boolean)
  if (tokens.length === 0) return options
  return options.filter((option) => {
    const label = option.label.toLowerCase()
    return tokens.every((token) => label.includes(token))
  })
}

export function SearchableSelect<TOption extends SearchableSelectOption = SearchableSelectOption>({
  options,
  value,
  onChange,
  label,
  placeholder,
  nothingFoundMessage = 'Data tidak ditemukan',
  searchPlaceholder = 'Ketik untuk mencari...',
  loading = false,
  clearable = true,
  searchable = true,
  searchValue,
  onSearchChange,
  disabled,
  readOnly,
  size = 'md',
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

  // Teks pencarian: bisa dikontrol parent (searchValue/onSearchChange) atau dikelola sendiri.
  const [search, setSearch] = useUncontrolled<string>({
    value: searchValue,
    defaultValue: '',
    onChange: onSearchChange,
  })

  const combobox = useCombobox({
    onDropdownClose: () => {
      combobox.resetSelectedOption()
      setSearch('')
      onBlur?.()
    },
    onDropdownOpen: () => {
      if (searchable) combobox.focusSearchInput()
    },
  })
  const { selectFirstOption, selectActiveOption } = combobox
  const opened = combobox.dropdownOpened

  // Nilai yang sudah tidak ada di options (daftar berganti / belum dimuat) ditampilkan kosong,
  // tanpa memanggil onChange. Nilai di parent tidak diubah.
  const selectedOption = value !== null ? options.find((o) => o.value === value) : undefined
  const safeValue = selectedOption ? selectedOption.value : null

  const filtered = useMemo(() => filterByTokens(options, search).slice(0, limit), [options, search, limit])

  // Item pertama yang cocok langsung tersorot, cukup ketik lalu Enter.
  // Saat dropdown baru dibuka tanpa kata kunci, item yang sedang terpilih yang tersorot.
  useEffect(() => {
    if (!opened) return
    if (!search && safeValue) selectActiveOption()
    else selectFirstOption()
  }, [opened, search, safeValue, selectFirstOption, selectActiveOption])

  const handleSearchKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // Enter di kolom cari tidak boleh men-submit form (termasuk saat tidak ada yang cocok).
    // Pemilihan item tersorot tetap ditangani Mantine.
    if (e.key === 'Enter') e.preventDefault()
    // Escape menutup dropdown saja, tidak naik ke handler Escape milik card/modal di atasnya.
    if (e.key === 'Escape') e.stopPropagation()
  }

  const handleTargetKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (opened && e.key === 'Escape') e.stopPropagation()
  }

  const showClear = clearable && safeValue !== null && !disabled && !readOnly && !loading

  const rightSection = loading ? (
    <Loader size={14} />
  ) : showClear ? (
    <CloseButton
      size="sm"
      aria-label="Hapus pilihan"
      // Cegah tombol clear merebut fokus dari target sebelum onClick berjalan.
      onMouseDown={(e) => e.preventDefault()}
      onClick={() => onChange(null)}
    />
  ) : (
    <Combobox.Chevron />
  )

  return (
    <Combobox
      store={combobox}
      shadow="sm"
      radius="md"
      transitionProps={{ duration: reduceMotion ? 0 : 100 }}
      onOptionSubmit={(next) => {
        onChange(next)
        combobox.closeDropdown()
        combobox.focusTarget()
      }}
      {...comboboxProps}
    >
      <Combobox.Target>
        <InputBase
          ref={ref}
          id={id}
          aria-label={ariaLabel}
          className={cn(className)}
          classNames={{ label: CLASS_NAMES.label, input: CLASS_NAMES.input }}
          component="button"
          type="button"
          // multiline: tinggi input menyesuaikan isi, teks panjang turun ke baris berikutnya.
          multiline
          pointer={!readOnly && !disabled}
          size={size}
          radius="md"
          label={label}
          // Validasi diserahkan ke form library; asterisk saja, tanpa atribut `required` native.
          withAsterisk={required}
          error={error}
          disabled={disabled}
          rightSection={rightSection}
          // Lebar area kanan dicadangkan, jadi teks tidak pernah tertutup ikon clear/panah.
          rightSectionWidth={40}
          rightSectionPointerEvents={showClear ? 'all' : 'none'}
          onClick={() => {
            if (!readOnly && !disabled) combobox.toggleDropdown()
          }}
          onKeyDown={handleTargetKeyDown}
          onBlur={() => {
            // Fokus pindah ke kolom cari di dropdown bukan blur sungguhan.
            if (!combobox.dropdownOpened) onBlur?.()
          }}
        >
          {selectedOption ? selectedOption.label : <Input.Placeholder>{placeholder}</Input.Placeholder>}
        </InputBase>
      </Combobox.Target>

      {name && <Combobox.HiddenInput name={name} value={safeValue ?? ''} />}

      <Combobox.Dropdown className={CLASS_NAMES.dropdown}>
        {searchable && (
          <Combobox.Search
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            onKeyDown={handleSearchKeyDown}
            placeholder={searchPlaceholder}
            size="sm"
            classNames={{ input: CLASS_NAMES.searchInput }}
          />
        )}
        <Combobox.Options>
          <ScrollArea.Autosize type="scroll" mah={240}>
            {filtered.map((option) => {
              const checked = option.value === safeValue
              return (
                <Combobox.Option
                  key={option.value}
                  value={option.value}
                  disabled={option.disabled}
                  active={checked}
                  data-checked={checked || undefined}
                  className={CLASS_NAMES.option}
                >
                  {option.label}
                </Combobox.Option>
              )
            })}
            {/* Saat loading, "Data tidak ditemukan" tidak ditampilkan. */}
            {filtered.length === 0 && !loading && (
              <Combobox.Empty className={CLASS_NAMES.empty}>{nothingFoundMessage}</Combobox.Empty>
            )}
          </ScrollArea.Autosize>
        </Combobox.Options>
      </Combobox.Dropdown>
    </Combobox>
  )
}