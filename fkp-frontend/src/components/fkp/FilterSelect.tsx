import { SearchableSelect } from '../ui/SearchableSelect'

export interface FilterOption {
  value: string
  label: string
}

// Masih dipakai input tanggal agar tinggi dan gayanya sama dengan select (h-9 = size="sm" Mantine).
// Select sendiri sudah di-style lewat CLASS_NAMES di SearchableSelect.
export const filterFieldClass =
  'w-full text-sm border border-gray-200 bg-red-500 rounded-lg px-3 pr-2 h-10 bg-white text-gray-700' +
  'focus:outline-hidden focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400 cursor-pointer'

interface FilterSelectProps {
  value: string
  onChange: (v: string) => void
  placeholder: string
  options: FilterOption[]
  className?: string
}

export function FilterSelect({ value, onChange, placeholder, options, className }: FilterSelectProps) {
  return (
    <SearchableSelect
      className={className}
      options={options}
      // Filter memakai '' untuk "semua", SearchableSelect memakai null
      value={value || null}
      onChange={(v) => onChange(v ?? '')}
      placeholder={placeholder}
      // Kolom ketik hanya muncul bila opsinya banyak
      searchable={options.length > 8}
      clearable
    />
  )
}