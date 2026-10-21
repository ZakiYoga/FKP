import { FilterBar } from '@/components/ui/FilterBar'
import type { FilterBarField, FilterOption } from '@/components/ui/FilterBar'
import { useAreas, useDistributors } from '@/hooks/useMasterData'
import { useKodeRole } from '@/store/authStore'
import { STATUS_OUTLET_OPTIONS } from '@/types/outlet'

interface OutletFilterBarProps {
  search: string
  onSearchChange: (v: string) => void
  statusFilter: string
  onStatusChange: (v: string) => void
  areaFilter: string
  // Parent bertugas mereset distributor saat area berubah
  onAreaChange: (v: string) => void
  distFilter: string
  onDistChange: (v: string) => void
}

const STATUS_FILTER_OPTIONS: FilterOption[] = STATUS_OUTLET_OPTIONS.map((s) => ({
  value: s.value,
  label: s.label,
}))

export function OutletFilterBar({
  search,
  onSearchChange,
  statusFilter,
  onStatusChange,
  areaFilter,
  onAreaChange,
  distFilter,
  onDistChange,
}: OutletFilterBarProps) {
  const { data: areas = [] } = useAreas()
  // Pilihan distributor mengikuti area yang dipilih
  const { data: distributors = [] } = useDistributors({ area_id: areaFilter || undefined })

  const areaOptions: FilterOption[] = areas.map((a) => ({ value: a.id, label: a.nama_area }))
  const distributorOptions: FilterOption[] = distributors.map((d) => ({
    value: d.id,
    label: `[${d.kode_distributor}] ${d.nama_perusahaan}`,
  }))

  // Role distributor hanya melihat distributornya sendiri, jadi filter area/distributor
  // tidak berguna. Hanya penyederhanaan UI; pembatasan data tetap di backend.
  const kodeRole = useKodeRole()
  const showAreaDistributor = kodeRole !== 'distributor'

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
      hidden: !showAreaDistributor,
      value: areaFilter,
      onChange: onAreaChange,
      options: areaOptions,
      placeholder: 'Semua Area',
    },
    {
      key: 'distributor',
      type: 'select',
      label: 'Distributor',
      hidden: !showAreaDistributor,
      value: distFilter,
      onChange: onDistChange,
      options: distributorOptions,
      placeholder: 'Semua Distributor',
    },
  ]

  return (
    <FilterBar
      search={search}
      onSearchChange={onSearchChange}
      searchPlaceholder="Cari nama toko, kode, pemilik..."
      fields={fields}
    />
  )
}