import { useState } from 'react'
import { Link } from 'react-router-dom'
import { format, toZonedTime } from 'date-fns-tz'
import { useFkpList } from '@/hooks/useFkp'
import { PcsTahapSelect } from '@/components/fkp-pcs/PcsTahapSelect'
import { RejectPcsModal } from '@/components/fkp-pcs/RejectPcsModal'
import { StatusBadge } from '@/components/ui/Badge'
import { JENIS_KELUHAN_LABEL, type FkpListItem } from '@/types'

type Tab = 'aktif' | 'selesai' | 'ditolak'

const TABS: { key: Tab; label: string; cocok: (f: FkpListItem) => boolean }[] = [
  { key: 'aktif', label: 'Perlu ditangani', cocok: (f) => f.status === 'pcs_ditangani_apsm' },
  { key: 'selesai', label: 'Selesai', cocok: (f) => f.status === 'closed' },
  { key: 'ditolak', label: 'Ditolak', cocok: (f) => f.status === 'rejected' },
]

const fmtTanggal = (s: string | null) =>
  s ? format(toZonedTime(new Date(s), 'Asia/Jakarta'), 'dd/MM/yyyy') : '-'

function PcsRow({ fkp }: { fkp: FkpListItem }) {
  const [rejectOpen, setRejectOpen] = useState(false)
  const aktif = fkp.status === 'pcs_ditangani_apsm'
  const bisaTolak = aktif && fkp.pcs_tahap === null

  return (
    <tr className="border-t border-gray-100">
      <td className="px-3 py-2.5 text-sm">
        {/* sesuaikan path rute detail FKP */}
        <Link to={`/fkp/${fkp.id}`} className="font-medium text-brand-600 hover:underline">
          {fkp.nomor_fkp}
        </Link>
      </td>
      <td className="px-3 py-2.5 text-sm text-gray-600">{fmtTanggal(fkp.tanggal_pengajuan)}</td>
      <td className="px-3 py-2.5 text-sm text-gray-600">
        <div>{fkp.distributor_info?.nama_perusahaan ?? '-'}</div>
        {fkp.outlet_info && <div className="text-xs text-gray-400">{fkp.outlet_info.nama_toko}</div>}
      </td>
      <td className="px-3 py-2.5 text-sm text-gray-600">
        {fkp.jenis_keluhan ? (JENIS_KELUHAN_LABEL[fkp.jenis_keluhan] ?? fkp.jenis_keluhan) : '-'}
      </td>
      <td className="px-3 py-2.5">
        <StatusBadge status={fkp.status} jalur={fkp.jalur} pcsTahap={fkp.pcs_tahap} classname="inline-flex" />
      </td>
      <td className="px-3 py-2.5">
        <div className="flex items-center gap-2">
          <PcsTahapSelect fkp={fkp} canHandle />
          {bisaTolak && (
            <>
              <button
                type="button"
                onClick={() => setRejectOpen(true)}
                className="whitespace-nowrap rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100"
              >
                Tolak
              </button>
              <RejectPcsModal fkpId={fkp.id} isOpen={rejectOpen} onClose={() => setRejectOpen(false)} />
            </>
          )}
          <Link to={`/fkp/${fkp.id}`} className="whitespace-nowrap text-xs text-gray-500 hover:underline">
            Detail
          </Link>
        </div>
      </td>
    </tr>
  )
}

// Akses dibatasi di router (ProtectedRoute allowedRoles apsm/superadmin).
export function FkpPcsPage() {
  const { data: semua = [], isLoading, isError } = useFkpList({ jalur: 'pcs' })
  // Jaga-jaga bila backend belum menyaring param jalur: param tak dikenal diabaikan
  // diam-diam oleh FastAPI, sehingga FKP non-pcs ikut terkirim.
  const data = semua.filter((f) => f.jalur === 'pcs')
  const [tab, setTab] = useState<Tab>('aktif')

  const aktifTab = TABS.find((t) => t.key === tab)!
  const rows = data.filter(aktifTab.cocok)

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-gray-900">FKP Pcs</h1>
        <p className="text-sm text-gray-500">
          FKP kemasan pcs yang ditangani langsung oleh APSM. Periksa produk, qty, dan foto bukti di
          halaman detail sebelum menentukan tahap.
        </p>
      </div>

      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-sm -mb-px border-b-2 ${
              tab === t.key
                ? 'border-brand-500 font-medium text-brand-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label} ({data.filter(t.cocok).length})
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="py-8 text-center text-sm text-gray-400">Memuat...</p>
      ) : isError ? (
        <p className="py-8 text-center text-sm text-red-600">Gagal memuat daftar FKP pcs.</p>
      ) : rows.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">Tidak ada FKP pada tab ini.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-left">
            <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-3 py-2 font-medium">Nomor FKP</th>
                <th className="px-3 py-2 font-medium">Tgl pengajuan</th>
                <th className="px-3 py-2 font-medium">Distributor / Outlet</th>
                <th className="px-3 py-2 font-medium">Keluhan</th>
                <th className="px-3 py-2 font-medium">Tahap</th>
                <th className="px-3 py-2 font-medium">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((f) => (
                <PcsRow key={f.id} fkp={f} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}