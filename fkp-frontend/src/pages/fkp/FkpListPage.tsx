import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, FileText } from 'lucide-react'
import { useFkpList } from '@/hooks/useFkp'
import { FkpCard } from '@/components/fkp/FkpCard'
import { FkpFilterBar } from '@/components/fkp/FkpFilterBar'
import { PageLoader } from '@/components/ui/Spinner'
import { useKodeRole } from '@/store/authStore'

// Role yang boleh membuat FKP baru
const CAN_CREATE = ['outlet', 'distributor', 'sc_spv', 'apsm', 'superadmin']

export function FkpListPage() {
  const navigate = useNavigate()
  const kodeRole = useKodeRole()

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [prioritasFilter, setPrioritasFilter] = useState('')

  const { data: fkpList = [], isLoading, isError } = useFkpList({
    status: statusFilter || undefined,
    prioritas: prioritasFilter || undefined,
  })

  // Filter lokal berdasarkan search
  const filtered = useMemo(() => {
    if (!search.trim()) return fkpList
    const q = search.toLowerCase()
    return fkpList.filter(
      (f) =>
        f.nomor_fkp.toLowerCase().includes(q) ||
        f.jenis_keluhan?.toLowerCase().includes(q),
    )
  }, [fkpList, search])

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
        {CAN_CREATE.includes(kodeRole) && (
          <button
            onClick={() => navigate('/fkp/baru')}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" />
            Buat FKP
          </button>
        )}
      </div>

      {/* Filter bar */}
      <FkpFilterBar
        search={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusChange={setStatusFilter}
        prioritasFilter={prioritasFilter}
        onPrioritasChange={setPrioritasFilter}
        totalCount={filtered.length}
      />

      {/* Content */}
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
            {search || statusFilter || prioritasFilter
              ? 'Tidak ada FKP yang sesuai filter.'
              : 'Belum ada FKP.'}
          </p>
          {CAN_CREATE.includes(kodeRole) && !search && !statusFilter && (
            <button
              onClick={() => navigate('/fkp/baru')}
              className="btn-primary mt-4 mx-auto"
            >
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
    </div>
  )
}
