import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText, Download, Filter, Calendar,
  ChevronDown, X, ExternalLink, Loader2,
} from 'lucide-react'
import { useFkpPenerbitan } from '@/hooks/useFkp'
import { StatusBadge, PrioritasBadge } from '@/components/ui/Badge'
import { PageLoader } from '@/components/ui/Spinner'
import { formatDateTime } from '@/lib/utils'
import { FKP_STATUS_LABEL } from '@/types'
import type { FkpStatusKey } from '@/types'
import { fkpApi } from '@/api/fkp'
import toast from 'react-hot-toast'
import api from '@/lib/axios'

// Status yang valid untuk filter dropdown
const PENERBITAN_STATUSES: { value: string; label: string }[] = [
  { value: 'submitted',                label: 'Menunggu Review APSM' },
  { value: 'apsm_reviewed',            label: 'Direview APSM' },
  { value: 'rsm_approval_investigasi', label: 'Menunggu Persetujuan RSM' },
  { value: 'in_investigation',         label: 'Sedang Diinvestigasi' },
  { value: 'investigated',             label: 'Investigasi Selesai' },
  { value: 'rsm_approval_resolusi',    label: 'Menunggu RSM (Resolusi)' },
  { value: 'direktur_approval',        label: 'Menunggu Direktur' },
  { value: 'accepted',                 label: 'Disetujui' },
  { value: 'in_process',              label: 'Sedang Diproses' },
  { value: 'closed',                   label: 'Selesai' },
  { value: 'rejected',                 label: 'Ditolak' },
]

export function PenerbitanFkpPage() {
  const navigate = useNavigate()

  const [filterStatus, setFilterStatus]     = useState('')
  const [filterDari, setFilterDari]         = useState('')
  const [filterSampai, setFilterSampai]     = useState('')
  const [showFilter, setShowFilter]         = useState(false)
  const [downloadingId, setDownloadingId]   = useState<string | null>(null)

  const activeFilters = {
    status:        filterStatus || undefined,
    tanggal_dari:  filterDari   || undefined,
    tanggal_sampai: filterSampai || undefined,
  }

  const { data: fkpList = [], isLoading, isError } = useFkpPenerbitan(activeFilters)

  const hasFilter = !!(filterStatus || filterDari || filterSampai)

  const clearFilter = () => {
    setFilterStatus('')
    setFilterDari('')
    setFilterSampai('')
  }

  const handleDownload = async (fkpId: string, nomorFkp: string) => {
    setDownloadingId(fkpId)
    try {
      // Download via axios agar auth header ikut (jika API butuh auth)
      const res = await api.get(`/fkp/${fkpId}/formulir-pdf`, {
        responseType: 'blob',
      })
      const url  = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href     = url
      link.download = `Formulir-FKP-${nomorFkp.replace(/\//g, '-')}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      toast.success(`Formulir FKP ${nomorFkp} berhasil diunduh.`)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Gagal mengunduh formulir.')
    } finally {
      setDownloadingId(null)
    }
  }

  if (isLoading) return <PageLoader />

  return (
    <div className="max-w-5xl mx-auto space-y-5 animate-fade-in">

      {/* ── Header ── */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Penerbitan Formulir FKP</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Download Formulir Keluhan Pelanggan yang sudah disubmit
          </p>
        </div>
        <button
          onClick={() => setShowFilter(v => !v)}
          className={`btn-secondary btn-sm flex items-center gap-1.5 ${hasFilter ? 'border-brand-400 text-brand-700' : ''}`}
        >
          <Filter className="w-4 h-4" />
          Filter
          {hasFilter && (
            <span className="ml-1 px-1.5 py-0.5 rounded-full bg-brand-100 text-brand-700 text-xs font-semibold">
              aktif
            </span>
          )}
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showFilter ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* ── Filter Panel ── */}
      {showFilter && (
        <div className="card card-body">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="input w-full text-sm"
              >
                <option value="">Semua Status</option>
                {PENERBITAN_STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                <Calendar className="inline w-3.5 h-3.5 mr-1" />
                Tanggal Dari
              </label>
              <input
                type="date"
                value={filterDari}
                onChange={(e) => setFilterDari(e.target.value)}
                className="input w-full text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                <Calendar className="inline w-3.5 h-3.5 mr-1" />
                Tanggal Sampai
              </label>
              <input
                type="date"
                value={filterSampai}
                onChange={(e) => setFilterSampai(e.target.value)}
                className="input w-full text-sm"
              />
            </div>
          </div>
          {hasFilter && (
            <div className="mt-3 pt-3 border-t border-gray-100 flex justify-end">
              <button onClick={clearFilter} className="btn-ghost btn-sm flex items-center gap-1.5 text-gray-500">
                <X className="w-3.5 h-3.5" /> Reset Filter
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Tabel ── */}
      <div className="card overflow-hidden">
        {isError ? (
          <div className="card-body text-center py-12 text-red-500">
            Gagal memuat data. Coba refresh halaman.
          </div>
        ) : fkpList.length === 0 ? (
          <div className="card-body text-center py-12">
            <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-500">
              {hasFilter ? 'Tidak ada FKP yang cocok dengan filter.' : 'Belum ada FKP yang bisa diterbitkan.'}
            </p>
            {hasFilter && (
              <button onClick={clearFilter} className="btn-secondary btn-sm mt-3 mx-auto">
                Reset Filter
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">
                    Nomor FKP
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">
                    Distributor / Outlet
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">
                    Prioritas
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">
                    Status
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">
                    Tgl Pengajuan
                  </th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">
                    Aksi
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {fkpList.map((fkp) => (
                  <tr key={fkp.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-gray-700 font-semibold">
                        {fkp.nomor_fkp}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900 text-sm">
                        {fkp.distributor_info?.nama_perusahaan ?? '—'}
                      </p>
                      {fkp.outlet_info && (
                        <p className="text-xs text-gray-400 mt-0.5">
                          {fkp.outlet_info.nama_toko}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <PrioritasBadge prioritas={fkp.prioritas} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={fkp.status} />
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {fkp.tanggal_pengajuan ? formatDateTime(fkp.tanggal_pengajuan) : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        {/* Tombol lihat detail */}
                        <button
                          onClick={() => navigate(`/fkp/${fkp.id}`)}
                          className="btn-ghost btn-sm p-1.5"
                          title="Lihat detail FKP"
                        >
                          <ExternalLink className="w-4 h-4 text-gray-400" />
                        </button>
                        {/* Tombol download */}
                        <button
                          onClick={() => handleDownload(fkp.id, fkp.nomor_fkp)}
                          disabled={downloadingId === fkp.id}
                          className="btn-primary btn-sm flex items-center gap-1.5 px-3"
                          title="Download Formulir FKP (PDF)"
                        >
                          {downloadingId === fkp.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Download className="w-3.5 h-3.5" />
                          )}
                          <span className="hidden sm:inline">Download</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
              <p className="text-xs text-gray-400">
                Menampilkan {fkpList.length} dokumen
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}