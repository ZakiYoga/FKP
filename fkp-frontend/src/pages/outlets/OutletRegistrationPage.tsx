import { useState } from 'react'
import { Search, CheckCircle, XCircle, Clock, RefreshCw, Eye, Building2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { formatDateTime } from '@/lib/utils'
import { OutletRegistrationDetail } from '@/types/outletRegister'
import { useApproveRegistration, usePendingRegistrations, useRejectRegistration } from '@/hooks/useOutletRegister'

// ─── Reject form schema ───────────────────────────────────────────────────────

const rejectSchema = z.object({
  alasan: z.string().min(5, 'Alasan minimal 5 karakter').max(500),
})
type RejectForm = z.infer<typeof rejectSchema>

// ─── Badge tipe toko ─────────────────────────────────────────────────────────

const TIPE_BADGE: Record<string, string> = {
  retail: 'bg-blue-50 text-blue-700',
  grosir: 'bg-violet-50 text-violet-700',
  horeka: 'bg-amber-50 text-amber-700',
}

// ─── Modal konfirmasi ─────────────────────────────────────────────────────────

function ApproveModal({
  item,
  onConfirm,
  onClose,
  isPending,
}: {
  item: OutletRegistrationDetail
  onConfirm: (catatan?: string) => void
  onClose: () => void
  isPending: boolean
}) {
  const [catatan, setCatatan] = useState('')
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-modal w-full max-w-md p-6 animate-slide-up">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
            <CheckCircle className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Setujui Pendaftaran</h3>
            <p className="text-sm text-gray-500">{item.nama_toko}</p>
          </div>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          Outlet akan diaktifkan dan pemilik ({item.email}) dapat login ke sistem.
        </p>
        <div className="mb-5">
          <label className="label">Catatan (opsional)</label>
          <textarea
            rows={3}
            className="input-base resize-none"
            placeholder="Catatan untuk distributor / outlet..."
            value={catatan}
            onChange={(e) => setCatatan(e.target.value)}
          />
        </div>
        <div className="flex gap-3">
          <button onClick={onClose} className="btn-secondary flex-1 btn-md" disabled={isPending}>
            Batal
          </button>
          <button
            onClick={() => onConfirm(catatan || undefined)}
            className="btn-primary flex-1 btn-md bg-emerald-600 hover:bg-emerald-700"
            disabled={isPending}
          >
            {isPending ? 'Menyetujui...' : 'Ya, Setujui'}
          </button>
        </div>
      </div>
    </div>
  )
}

function RejectModal({
  item,
  onConfirm,
  onClose,
  isPending,
}: {
  item: OutletRegistrationDetail
  onConfirm: (alasan: string) => void
  onClose: () => void
  isPending: boolean
}) {
  const { register, handleSubmit, formState: { errors } } = useForm<RejectForm>({
    resolver: zodResolver(rejectSchema),
  })
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-modal w-full max-w-md p-6 animate-slide-up">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
            <XCircle className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Tolak Pendaftaran</h3>
            <p className="text-sm text-gray-500">{item.nama_toko}</p>
          </div>
        </div>
        <form onSubmit={handleSubmit((d) => onConfirm(d.alasan))} className="space-y-4">
          <div>
            <label className="label label-required">Alasan Penolakan</label>
            <textarea
              rows={4}
              className={`input-base resize-none ${errors.alasan ? 'input-error' : ''}`}
              placeholder="Jelaskan alasan penolakan pendaftaran ini..."
              {...register('alasan')}
            />
            {errors.alasan && (
              <p className="mt-1.5 text-xs text-red-600">{errors.alasan.message}</p>
            )}
          </div>
          <div className="flex gap-3">
            <button type="button" onClick={onClose} className="btn-secondary flex-1 btn-md" disabled={isPending}>
              Batal
            </button>
            <button type="submit" className="flex-1 btn-md bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium" disabled={isPending}>
              {isPending ? 'Menolak...' : 'Tolak Pendaftaran'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function DetailModal({
  item,
  onClose,
}: {
  item: OutletRegistrationDetail
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-modal w-full max-w-lg p-6 animate-slide-up">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-semibold text-gray-900">Detail Pendaftaran</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          {[
            ['Kode Outlet', item.kode_outlet],
            ['Nama Toko', item.nama_toko],
            ['Pemilik', item.pemilik_toko],
            ['Tipe Toko', item.tipe_toko],
            ['No. HP', item.no_hp ?? '-'],
            ['Email', item.email],
            ['Alamat', item.alamat_lengkap ?? '-'],
            ['Terdaftar', formatDateTime(item.created_at)],
          ].map(([label, val]) => (
            <div key={label}>
              <p className="text-xs text-gray-400 mb-0.5">{label}</p>
              <p className="font-medium text-gray-800 break-words">{val}</p>
            </div>
          ))}
        </div>
        <button onClick={onClose} className="btn-secondary w-full btn-md mt-6">Tutup</button>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function OutletRegistrationsPage() {
  const [search, setSearch] = useState('')
  const [approveTarget, setApproveTarget] = useState<OutletRegistrationDetail | null>(null)
  const [rejectTarget, setRejectTarget]   = useState<OutletRegistrationDetail | null>(null)
  const [detailTarget, setDetailTarget]   = useState<OutletRegistrationDetail | null>(null)

  const { data, isLoading, isError, refetch } = usePendingRegistrations()
  const { mutate: approve, isPending: isApproving } = useApproveRegistration()
  const { mutate: reject,  isPending: isRejecting  } = useRejectRegistration()

  const items = data?.items ?? []

  const filtered = items.filter((item) => {
    const q = search.toLowerCase()
    return (
      item.nama_toko.toLowerCase().includes(q) ||
      item.pemilik_toko.toLowerCase().includes(q) ||
      item.email.toLowerCase().includes(q) ||
      item.kode_outlet.toLowerCase().includes(q)
    )
  })

  const handleApprove = (catatan?: string) => {
    if (!approveTarget) return
    approve(
      { outletId: approveTarget.outlet_id, data: { catatan } },
      { onSuccess: () => setApproveTarget(null) },
    )
  }

  const handleReject = (alasan: string) => {
    if (!rejectTarget) return
    reject(
      { outletId: rejectTarget.outlet_id, data: { alasan } },
      { onSuccess: () => setRejectTarget(null) },
    )
  }

  return (
    <>
      {/* ── Modals ─────────────────────────────────────────────────────── */}
      {approveTarget && (
        <ApproveModal
          item={approveTarget}
          onConfirm={handleApprove}
          onClose={() => setApproveTarget(null)}
          isPending={isApproving}
        />
      )}
      {rejectTarget && (
        <RejectModal
          item={rejectTarget}
          onConfirm={handleReject}
          onClose={() => setRejectTarget(null)}
          isPending={isRejecting}
        />
      )}
      {detailTarget && (
        <DetailModal item={detailTarget} onClose={() => setDetailTarget(null)} />
      )}

      {/* ── Page ───────────────────────────────────────────────────────── */}
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Registrasi Outlet</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Outlet yang mendaftar dan menunggu verifikasi
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Counter badge */}
            {(data?.total ?? 0) > 0 && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-100 text-amber-700 text-sm font-medium">
                <Clock className="w-3.5 h-3.5" />
                {data?.total} menunggu
              </span>
            )}
            <button
              onClick={() => refetch()}
              className="btn-secondary btn-md flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Cari nama toko, pemilik, email..."
            className="input-base pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Table / States */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-16 gap-2 text-gray-400">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span className="text-sm">Memuat data...</span>
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-gray-400">
              <XCircle className="w-8 h-8 text-red-400" />
              <p className="text-sm">Gagal memuat data</p>
              <button onClick={() => refetch()} className="btn-secondary btn-sm">Coba Lagi</button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-gray-400">
              <Building2 className="w-8 h-8" />
              <p className="text-sm">
                {search ? 'Tidak ada hasil untuk pencarian ini' : 'Tidak ada pendaftaran outlet yang menunggu verifikasi'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/50">
                    <th className="text-left px-4 py-3 font-medium text-gray-500 whitespace-nowrap">Toko</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500 whitespace-nowrap">Kontak</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500 whitespace-nowrap">Tipe</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500 whitespace-nowrap">Kode</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500 whitespace-nowrap">Terdaftar</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-500 whitespace-nowrap">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filtered.map((item) => (
                    <tr key={item.outlet_id} className="hover:bg-gray-50/50 transition-colors group">
                      {/* Toko */}
                      <td className="px-4 py-3.5">
                        <p className="font-medium text-gray-900">{item.nama_toko}</p>
                        <p className="text-xs text-gray-400 mt-0.5">{item.pemilik_toko}</p>
                      </td>
                      {/* Kontak */}
                      <td className="px-4 py-3.5">
                        <p className="text-gray-700">{item.email}</p>
                        <p className="text-xs text-gray-400 mt-0.5">{item.no_hp ?? '-'}</p>
                      </td>
                      {/* Tipe */}
                      <td className="px-4 py-3.5">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${TIPE_BADGE[item.tipe_toko] ?? 'bg-gray-100 text-gray-600'}`}>
                          {item.tipe_toko}
                        </span>
                      </td>
                      {/* Kode */}
                      <td className="px-4 py-3.5">
                        <span className="font-mono text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                          {item.kode_outlet}
                        </span>
                      </td>
                      {/* Tanggal */}
                      <td className="px-4 py-3.5 text-gray-500 text-xs whitespace-nowrap">
                        {formatDateTime(item.created_at)}
                      </td>
                      {/* Aksi */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => setDetailTarget(item)}
                            title="Lihat detail"
                            className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setApproveTarget(item)}
                            title="Setujui"
                            className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-50 hover:text-emerald-600 transition-colors"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setRejectTarget(item)}
                            title="Tolak"
                            className="p-1.5 rounded-lg text-red-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer count */}
        {filtered.length > 0 && (
          <p className="text-xs text-gray-400">
            Menampilkan {filtered.length} dari {data?.total ?? 0} pendaftaran
          </p>
        )}
      </div>
    </>
  )
}