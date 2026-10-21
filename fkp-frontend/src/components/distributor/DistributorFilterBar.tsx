import { FilterBar } from '@/components/ui/FilterBar'
import type { FilterBarField, FilterOption } from '@/components/ui/FilterBar'
import { useAreas } from '@/hooks/useMasterData'
import { useKodeRole } from '@/store/authStore'

interface DistributorFilterBarProps {
  search: string
  onSearchChange: (v: string) => void
  statusFilter: string
  onStatusChange: (v: string) => void
  areaFilter: string
  onAreaChange: (v: string) => void
}

const STATUS_FILTER_OPTIONS: FilterOption[] = [
  { value: 'aktif', label: 'Aktif' },
  { value: 'nonaktif', label: 'Nonaktif' },
]

export function DistributorFilterBar({
  search,
  onSearchChange,
  statusFilter,
  onStatusChange,
  areaFilter,
  onAreaChange,
}: DistributorFilterBarProps) {
  const { data: areas = [] } = useAreas()
  const areaOptions: FilterOption[] = areas.map((a) => ({ value: a.id, label: a.nama_area }))

  // Role distributor hanya melihat distributornya sendiri, jadi filter area tidak berguna.
  // Hanya penyederhanaan UI; pembatasan data tetap di backend.
  const kodeRole = useKodeRole()
  const showArea = kodeRole !== 'distributor'

  const fields: FilterBarField[] = [
    {
      key: 'status',
      type: 'select',
      label: 'Status',
      value: statusFilter,
      onChange: onStatusChange,
      options: STATUS_FILTER_OPTIONS,
      placeholder: 'Semua Status',
    },
    {
      key: 'area',
      type: 'select',
      label: 'Area',
      hidden: !showArea,
      value: areaFilter,
      onChange: onAreaChange,
      options: areaOptions,
      placeholder: 'Semua Area',
    },
  ]

  return (
    <FilterBar
      search={search}
      onSearchChange={onSearchChange}
      searchPlaceholder="Cari nama, kode, pemilik..."
      fields={fields}
    />
  )
}