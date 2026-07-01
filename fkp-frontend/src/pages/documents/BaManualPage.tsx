import { useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, FileText, Plus, Trash2,
  Loader2, Download, CheckCircle2, AlertTriangle,
} from 'lucide-react'
import { useGenerateBAManual } from '@/hooks/useBeritaAcara'
import { useFkpList } from '@/hooks/useFkp'
import { Input } from '@/components/ui/Input'
import type { BeritaAcaraItemManual, BeritaAcaraManualPayload } from '@/types'
import api from '@/lib/axios'
import toast from 'react-hot-toast'

// ── Konstanta ──────────────────────────────────────────────────────────────

const METODE_OPTIONS = [
  { value: 'dibakar',           label: 'Dibakar' },
  { value: 'dihancurkan',       label: 'Dihancurkan' },
  { value: 'dikembalikan_ho',   label: 'Dikembalikan ke HO' },
  { value: 'lainnya',           label: 'Lainnya (isi manual)' },
]

const TINDAK_OPTIONS = [
  { value: '',                  label: '— Pilih tindak lanjut —' },
  { value: 'penukaran_barang',  label: 'Penukaran Barang' },
  { value: 'potong_tagihan',    label: 'Potong Tagihan' },
  { value: 'tanpa_kompensasi',  label: 'Tanpa Kompensasi' },
]

const ITEM_BLANK: BeritaAcaraItemManual = {
  nama_barang: '',
  batch_no_ed: '',
  jumlah:      '',
  keterangan:  '',
}

// ── Form state type ────────────────────────────────────────────────────────

interface BaForm {
  fkp_id:               string
  nomor_dokumen:        string
  tanggal_pelaksanaan:  string
  lokasi_pelaksanaan:   string
  metode_pemusnahan:    string
  metode_custom:        string   // jika "lainnya"
  lokasi_pemusnahan:    string
  pihak_pelaksana:      string
  dokumentasi_lampiran: string
  tindak_lanjut:        string
  nama_pengaju:         string
  nama_saksi_internal:  string
  nama_saksi_eksternal: string
  nama_penyetuju:       string
}

const FORM_BLANK: BaForm = {
  fkp_id:               '',
  nomor_dokumen:        '',
  tanggal_pelaksanaan:  '',
  lokasi_pelaksanaan:   '',
  metode_pemusnahan:    'dibakar',
  metode_custom:        '',
  lokasi_pemusnahan:    '',
  pihak_pelaksana:      '',
  dokumentasi_lampiran: '',
  tindak_lanjut:        '',
  nama_pengaju:         '',
  nama_saksi_internal:  '',
  nama_saksi_eksternal: '',
  nama_penyetuju:       '',
}

// ── Helpers ────────────────────────────────────────────────────────────────

function buildPayload(form: BaForm, items: BeritaAcaraItemManual[]): BeritaAcaraManualPayload {
  const metode = form.metode_pemusnahan === 'lainnya'
    ? form.metode_custom || undefined
    : form.metode_pemusnahan || undefined

  return {
    fkp_id:               form.fkp_id      || null,
    nomor_dokumen:        form.nomor_dokumen || null,
    tanggal_pelaksanaan:  form.tanggal_pelaksanaan || null,
    lokasi_pelaksanaan:   form.lokasi_pelaksanaan  || null,
    metode_pemusnahan:    metode,
    lokasi_pemusnahan:    form.lokasi_pemusnahan   || null,
    pihak_pelaksana:      form.pihak_pelaksana      || null,
    dokumentasi_lampiran: form.dokumentasi_lampiran || null,
    tindak_lanjut:        form.tindak_lanjut        || null,
    nama_pengaju:         form.nama_pengaju         || null,
    nama_saksi_internal:  form.nama_saksi_internal  || null,
    nama_saksi_eksternal: form.nama_saksi_eksternal || null,
    nama_penyetuju:       form.nama_penyetuju       || null,
    items: items.filter(i => i.nama_barang.trim()),
  }
}

// ── Komponen utama ─────────────────────────────────────────────────────────

export function BaManualPage() {
  const navigate      = useNavigate()
  const [params]      = useSearchParams()

  const [form, setForm]   = useState<BaForm>({
    ...FORM_BLANK,
    fkp_id: params.get('fkp_id') ?? '',
  })
  const [items, setItems] = useState<BeritaAcaraItemManual[]>([{ ...ITEM_BLANK }])
  const [isDownloading, setIsDownloading] = useState(false)
  const [generated, setGenerated]         = useState<{
    nomor: string; docId: string | null; urlDownload: string | null
  } | null>(null)

  const { data: fkpList = [] } = useFkpList()
  const { mutateAsync: generate, isPending } = useGenerateBAManual()

  const set = useCallback(
    (k: keyof BaForm) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm(p => ({ ...p, [k]: e.target.value })),
    [],
  )

  // ── Item handlers ────────────────────────────────────────────────────────

  const addItem = () => setItems(p => [...p, { ...ITEM_BLANK }])

  const removeItem = (idx: number) =>
    setItems(p => p.filter((_, i) => i !== idx))

  const setItem = (idx: number, k: keyof BeritaAcaraItemManual, v: string) =>
    setItems(p => p.map((item, i) => i === idx ? { ...item, [k]: v } : item))

  // ── Submit: generate + simpan ────────────────────────────────────────────

  const handleGenerate = async () => {
    const filledItems = items.filter(i => i.nama_barang.trim())
    if (filledItems.length === 0) {
      toast.error('Minimal satu baris barang harus diisi.')
      return
    }
    try {
      const res = await generate(buildPayload(form, items))
      setGenerated({
        nomor:       res.nomor_dokumen,
        docId:       res.doc_id ?? null,
        urlDownload: res.url_download ?? null,
      })
      toast.success('Berita Acara berhasil digenerate.')
    } catch {
      // error sudah di-handle di hook
    }
  }

  // ── Preview: download PDF langsung tanpa simpan ke DB ───────────────────

  const handlePreview = async () => {
    const filledItems = items.filter(i => i.nama_barang.trim())
    if (filledItems.length === 0) {
      toast.error('Minimal satu baris barang harus diisi.')
      return
    }
    setIsDownloading(true)
    try {
      const payload = buildPayload(form, items)
      // POST ke endpoint generate manual, terima blob PDF
      const res = await api.post('/fkp/berita-acara/manual', payload, {
        responseType: 'blob',
      })
      const safe  = (payload.nomor_dokumen ?? 'BA-MANUAL').replace(/\//g, '-')
      const url   = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const link  = document.createElement('a')
      link.href     = url
      link.download = `${safe}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      toast.success('PDF berhasil diunduh.')
    } catch (e: any) {
      const d = e?.response?.data?.detail
      toast.error(typeof d === 'string' ? d : 'Gagal mengunduh PDF.')
    } finally {
      setIsDownloading(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">

      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/penerbitan-ba-fkp')} className="btn-ghost btn-sm p-2">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Generate Berita Acara Manual</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Isi form sesuai data pelaksanaan pemusnahan
          </p>
        </div>
      </div>

      {/* Banner sukses */}
      {generated && (
        <div className="flex items-start gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
          <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-emerald-800">
              Berita Acara berhasil digenerate
            </p>
            <p className="text-sm text-emerald-700 mt-0.5">
              Nomor: <span className="font-mono">{generated.nomor}</span>
            </p>
          </div>
          {generated.urlDownload && (
            <button
              onClick={handlePreview}
              disabled={isDownloading}
              className="btn-secondary btn-sm flex items-center gap-1.5 shrink-0"
            >
              {isDownloading
                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                : <Download className="w-3.5 h-3.5" />
              }
              Download PDF
            </button>
          )}
        </div>
      )}

      {/* ── Seksi 1: Identitas Dokumen ── */}
      <div className="card">
        <div className="card-header">
          <h2 className="font-semibold text-gray-900 flex items-center gap-2">
            <FileText className="w-4 h-4 text-brand-500" />
            Identitas Dokumen
          </h2>
        </div>
        <div className="card-body space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Nomor Dokumen"
              placeholder="SPP/QC/FORM 26 (default)"
              value={form.nomor_dokumen}
              onChange={set('nomor_dokumen')}
            />
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Tautkan ke FKP (opsional)
              </label>
              <select
                value={form.fkp_id}
                onChange={set('fkp_id')}
                className="input w-full text-sm"
              >
                <option value="">— Tidak dikaitkan ke FKP —</option>
                {fkpList.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.nomor_fkp} — {f.distributor_info?.nama_perusahaan ?? ''}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-400 mt-1">
                Jika diisi, PDF akan tersimpan di dokumen FKP tersebut.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Seksi 2: Pelaksanaan ── */}
      <div className="card">
        <div className="card-header">
          <h2 className="font-semibold text-gray-900">Informasi Pelaksanaan</h2>
        </div>
        <div className="card-body space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Tanggal Pelaksanaan"
              type="date"
              value={form.tanggal_pelaksanaan}
              onChange={set('tanggal_pelaksanaan')}
            />
            <Input
              label="Lokasi Pelaksanaan"
              placeholder="Nama gudang, kota..."
              value={form.lokasi_pelaksanaan}
              onChange={set('lokasi_pelaksanaan')}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Metode Pemusnahan
              </label>
              <select
                value={form.metode_pemusnahan}
                onChange={set('metode_pemusnahan')}
                className="input w-full text-sm"
              >
                {METODE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            {form.metode_pemusnahan === 'lainnya' && (
              <Input
                label="Metode (isi manual)"
                placeholder="Jelaskan metode pemusnahan..."
                value={form.metode_custom}
                onChange={set('metode_custom')}
              />
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Lokasi Pemusnahan"
              placeholder="Area spesifik pelaksanaan..."
              value={form.lokasi_pemusnahan}
              onChange={set('lokasi_pemusnahan')}
            />
            <Input
              label="Pihak Pelaksana"
              placeholder="Nama pelaksana..."
              value={form.pihak_pelaksana}
              onChange={set('pihak_pelaksana')}
            />
          </div>
          <Input
            label="Dokumentasi / Lampiran"
            placeholder="Mis: Foto pemusnahan terlampir (3 foto)"
            value={form.dokumentasi_lampiran}
            onChange={set('dokumentasi_lampiran')}
          />
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Tindak Lanjut
            </label>
            <select
              value={form.tindak_lanjut}
              onChange={set('tindak_lanjut')}
              className="input w-full text-sm"
            >
              {TINDAK_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── Seksi 3: Daftar Barang ── */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">
              Daftar Barang yang Dimusnahkan
            </h2>
            <button
              onClick={addItem}
              className="btn-secondary btn-sm flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" /> Tambah Baris
            </button>
          </div>
        </div>
        <div className="card-body space-y-3">
          {items.map((item, idx) => (
            <div
              key={idx}
              className="p-3 rounded-xl bg-gray-50 border border-gray-100 space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500">
                  Barang #{idx + 1}
                </span>
                {items.length > 1 && (
                  <button
                    onClick={() => removeItem(idx)}
                    className="btn-ghost btn-sm p-1 text-red-400 hover:text-red-600"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label="Nama Barang"
                  required
                  placeholder="Nama produk..."
                  value={item.nama_barang}
                  onChange={(e) => setItem(idx, 'nama_barang', e.target.value)}
                />
                <Input
                  label="Batch No / ED"
                  placeholder="BT-2025-001 / Jan 2026"
                  value={item.batch_no_ed ?? ''}
                  onChange={(e) => setItem(idx, 'batch_no_ed', e.target.value)}
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label="Jumlah"
                  placeholder="24 pcs / 3 karton..."
                  value={item.jumlah ?? ''}
                  onChange={(e) => setItem(idx, 'jumlah', e.target.value)}
                />
                <Input
                  label="Keterangan"
                  placeholder="Kondisi / catatan..."
                  value={item.keterangan ?? ''}
                  onChange={(e) => setItem(idx, 'keterangan', e.target.value)}
                />
              </div>
            </div>
          ))}

          {items.filter(i => !i.nama_barang.trim()).length > 0 && (
            <div className="flex items-center gap-2 text-xs text-amber-600">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              Baris tanpa nama barang akan diabaikan saat generate.
            </div>
          )}
        </div>
      </div>

      {/* ── Seksi 4: Tanda Tangan ── */}
      <div className="card">
        <div className="card-header">
          <h2 className="font-semibold text-gray-900">Tanda Tangan / Persetujuan</h2>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Diajukan Oleh (Pelanggan)"
              placeholder="Nama pengaju..."
              value={form.nama_pengaju}
              onChange={set('nama_pengaju')}
            />
            <Input
              label="Saksi Internal"
              placeholder="Nama saksi dari perusahaan..."
              value={form.nama_saksi_internal}
              onChange={set('nama_saksi_internal')}
            />
            <Input
              label="Saksi Eksternal"
              placeholder="Nama / instansi saksi luar..."
              value={form.nama_saksi_eksternal}
              onChange={set('nama_saksi_eksternal')}
            />
            <Input
              label="Disetujui Oleh (Marketing)"
              placeholder="Nama penyetuju..."
              value={form.nama_penyetuju}
              onChange={set('nama_penyetuju')}
            />
          </div>
        </div>
      </div>

      {/* ── Action Bar ── */}
      <div className="flex items-center gap-3 justify-end pb-8">
        <button
          onClick={handlePreview}
          disabled={isDownloading || isPending}
          className="btn-secondary flex items-center gap-2"
        >
          {isDownloading
            ? <Loader2 className="w-4 h-4 animate-spin" />
            : <Download className="w-4 h-4" />
          }
          Download PDF
        </button>
        <button
          onClick={handleGenerate}
          disabled={isPending || isDownloading}
          className="btn-primary flex items-center gap-2"
        >
          {isPending
            ? <Loader2 className="w-4 h-4 animate-spin" />
            : <FileText className="w-4 h-4" />
          }
          Generate & Simpan
        </button>
      </div>
    </div>
  )
}