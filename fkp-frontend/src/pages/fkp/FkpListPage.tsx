import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, FileText, Download } from 'lucide-react'        // + Download
import { useFkpList, useExportFkpExcel } from '@/hooks/useFkp'  // + useExportFkpExcel
import { FkpCard } from '@/components/fkp/FkpCard'
import { FkpFilterBar } from '@/components/fkp/FkpFilterBar'
import type { AdvFilters } from '@/components/fkp/FkpFilterBar'
import { PageLoader } from '@/components/ui/Spinner'
import { useKodeRole } from '@/store/authStore'

// Role yang boleh membuat FKP baru
const CAN_CREATE = ['outlet', 'distributor', 'sc_spv', 'apsm', 'superadmin']

// BARU — role yang boleh export Excel (hanya untuk tampilkan/sembunyikan
// tombol; penegakan akses sesungguhnya tetap di BE lewat require_permission)
const CAN_EXPORT = ['admin_ho', 'rsm', 'direktur', 'apsm', 'superadmin']

const EMPTY_ADV_FILTERS: AdvFilters = {
  area_id: '',
  distributor_id: '',
  outlet_id: '',
  tanggal_dari: '',
  tanggal_sampai: '',
}

export function FkpListPage() {
  const navigate = useNavigate()
  const kodeRole = useKodeRole()

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [prioritasFilter, setPrioritasFilter] = useState('')
  const [advFilters, setAdvFilters] = useState<AdvFilters>(EMPTY_ADV_FILTERS)

  const handleAdvChange = (patch: Partial<AdvFilters>) => {
    setAdvFilters((prev) => {
      const next = { ...prev, ...patch }
      if ('area_id' in patch) {
        next.distributor_id = ''
        next.outlet_id = ''
      } else if ('distributor_id' in patch) {
        next.outlet_id = ''
      }
      return next
    })
  }

  const params = {
    status: statusFilter || undefined,
    prioritas: prioritasFilter || undefined,
    outlet_id: advFilters.outlet_id || undefined,
    distributor_id: advFilters.distributor_id || undefined,
    area_id: advFilters.area_id || undefined,
    tanggal_dari: advFilters.tanggal_dari || undefined,
    tanggal_sampai: advFilters.tanggal_sampai || undefined,
  }

  const { data: fkpList = [], isLoading, isError } = useFkpList(params)

  // BARU
  const exportMut = useExportFkpExcel()

  const filtered = useMemo(() => {
    if (!search.trim()) return fkpList
    const q = search.toLowerCase()
    return fkpList.filter(
      (f) =>
        f.nomor_fkp.toLowerCase().includes(q) ||
        f.jenis_keluhan?.toLowerCase().includes(q),
    )
  }, [fkpList, search])

  const hasAnyFilter =
    search || statusFilter || prioritasFilter || Object.values(advFilters).some(Boolean)

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Formulir Keluhan Produk</h1>
          <p className="text-gray-500 text-sm mt-0.5">
            Kelola dan pantau semua pengajuan keluhan produk
          </p>
        </div>

        {/* BARU — dibungkus flex gap-2 supaya 2 tombol berdampingan */}
        <div className="flex items-center gap-2">
          {CAN_EXPORT.includes(kodeRole) && (
            <button
              onClick={() => exportMut.mutate(params)}
              disabled={exportMut.isPending}
              className="btn-secondary p-2 px-4 !text-sm bg-green-500 hover:bg-green-600"
            >
              <Download className="w-4 h-4" />
              {exportMut.isPending ? 'Menyiapkan...' : 'Download Excel'}
            </button>
          )}

          {CAN_CREATE.includes(kodeRole) && (
            <button onClick={() => navigate('/fkp/baru')} className="btn-primary">
              <Plus className="w-4 h-4" />
              Buat FKP
            </button>
          )}
        </div>
      </div>

      {/* Filter bar — TIDAK berubah dari sebelumnya */}
      <FkpFilterBar
        search={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusChange={setStatusFilter}
        prioritasFilter={prioritasFilter}
        onPrioritasChange={setPrioritasFilter}
        advFilters={advFilters}
        onAdvChange={handleAdvChange}
        totalCount={filtered.length}
      />

      {/* Content — TIDAK berubah dari sebelumnya */}
      {isLoading ? (
        <PageLoader />
      ) : isError ? (
        <div className="card card-body text-center py-12">
          <p className="text-red-500 font-medium">Gagal memuat data FKP.</p>
          <p className="text-gray-400 text-sm mt-1">Periksa koneksi dan coba lagi.</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card card-body text-center py-16">
          <FileText className="w-12 h-12 text-gray-200 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">
            {hasAnyFilter ? 'Tidak ada FKP yang sesuai filter.' : 'Belum ada FKP.'}
          </p>
          {CAN_CREATE.includes(kodeRole) && !search && !statusFilter && (
            <button onClick={() => navigate('/fkp/baru')} className="btn-primary mt-4 mx-auto">
              <Plus className="w-4 h-4" />
              Buat FKP Pertama
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((fkp) => (
            <FkpCard key={fkp.id} fkp={fkp} />
          ))}
        </div>
      )}

      {filtered.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-xs text-gray-500 shrink-0">
            <span className="font-semibold text-gray-900">Total : {filtered.length}</span> FKP
          </p>
        </div>
      )}
    </div>
  )
}