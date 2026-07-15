/* eslint-disable @typescript-eslint/no-explicit-any */
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, FileText, Clock, CheckCircle2, Loader2, Send,
  AlertTriangle, ShieldCheck, XCircle, Edit2, Plus, Package,
  QrCode, Download, Copy, Check, ExternalLink,
  Paperclip, Truck, Banknote, FileDown,
} from 'lucide-react'
import { useState, useRef, useCallback } from 'react'
import { QRCodeCanvas } from 'qrcode.react'
import { useFkpDetail, useSubmitFkp, useProducts, useAddFkpItem, useDeleteFkpItem } from '@/hooks/useFkp'
import { useSuratJalanList } from '@/hooks/useWarehouse'
import { useSampleList } from '@/hooks/useSample'
import { StatusBadge, PrioritasBadge } from '@/components/ui/Badge'
import { PageLoader } from '@/components/ui/Spinner'
import { Modal } from '@/components/ui/Modal'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { FkpItemFormModal, type FileWithMeta } from '@/components/fkp/FkpItemFormModal'
import { FkpItemReviewForm, type ApsmReviewState, type AdminHoReviewState, APSM_REVIEW_BLANK, ADMIN_HO_REVIEW_BLANK } from '@/components/fkp/FkpItemReviewForm'
import { formatDateTime, formatRupiah } from '@/lib/utils'
import { useAuthStore, useKodeRole } from '@/store/authStore'
import { FKP_STATUS_LABEL, METODE_PENANGANAN_LABEL, TIPE_RESOLUSI_LABEL, SURAT_JALAN_STATUS_LABEL, SAMPLE_STATUS_LABEL, SAMPLE_STATUS_TERMINAL } from '@/types'
import type {
  FkpStatusKey, FkpItemCreatePayload, TipeResolusi, MetodePenangananFisik,
  RekomendasiPenanganan, RekomendasiKompensasi,
} from '@/types'
import { fkpApi } from '@/api/fkp'
import { warehouseApi } from '@/api/warehouse'
import { financeApi } from '@/api/finance'
import { useQueryClient } from '@tanstack/react-query'
import { fkpKeys } from '@/hooks/useFkp'
import { warehouseKeys } from '@/hooks/useWarehouse'
import toast from 'react-hot-toast'
import InfoRow from '@/components/fkp/InfoRow'
import CatatanItem from '@/components/fkp/FkpItemCatatan'
import FkpItemCard from '@/components/fkp/FkpItemCard'
import { SampleShipmentSection } from '@/components/SampleShipmentSection'
import { useCanWriteFkp } from '@/hooks/useCanWriteFkp'
import { AuthenticatedImage } from '@/components/AuthenticatedImage'
import { openAuthenticatedFile } from '@/hooks/useAuthenticatedImage'

// ── Tipe modal ────────────────────────────────────────────────────────────────

type ModalTipe =
  | 'apsm_review' | 'admin_ho_review'
  | 'rsm_investigasi_ok' | 'rsm_investigasi_tolak'
  | 'qc_investigasi'
  | 'buat_resolusi'
  | 'request_resolusi_approval'
  | 'rsm_resolusi_ok' | 'rsm_resolusi_tolak'
  | 'direktur_ok' | 'direktur_tolak'
  | 'set_qty_disetujui'  // ← BARU: admin_ho only, isi fkp_items.qty_disetujui
  | 'lengkapi_qty_sj'    // [DIUBAH] sekarang HANYA buat Surat Jalan, tidak lagi menulis qty_disetujui
  | 'lengkapi_rekening'
  | 'terbitkan_invoice'
  | 'proses_finance'
  | 'confirm_resolusi'
  | 'sj_ship'
  | 'revision' | 'reject' | 'close'
  | 'qr_code'

type QcItemResult = {
  status_item: string
  catatan_qc: string
  alasan_penolakan: string
}


// ─── QR Code Modal Content ────────────────────────────────────────────────────

function QrCodeModalContent({
  fkpId,
  nomorFkp,
}: {
  fkpId: string
  nomorFkp: string
}) {
  const canvasRef = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)

  const trackingUrl = `${window.location.origin}/track/${fkpId}`

  const handleDownload = useCallback(() => {
    const canvas = canvasRef.current?.querySelector('canvas')
    if (!canvas) return

    // Buat canvas baru dengan padding + label nomor FKP di bawah
    const padding = 24
    const labelH = 44
    const off = document.createElement('canvas')
    off.width = canvas.width + padding * 2
    off.height = canvas.height + padding * 2 + labelH
    const ctx = off.getContext('2d')!

    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, off.width, off.height)
    ctx.drawImage(canvas, padding, padding)

    // Nomor FKP
    ctx.fillStyle = '#374151'
    ctx.font = 'bold 13px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(nomorFkp, off.width / 2, canvas.height + padding + 22)

    // URL kecil di bawah nomor
    ctx.fillStyle = '#9ca3af'
    ctx.font = '10px monospace'
    ctx.fillText(trackingUrl, off.width / 2, canvas.height + padding + 38)

    const link = document.createElement('a')
    link.download = `QR-FKP-${nomorFkp.replace(/\//g, '-')}.png`
    link.href = off.toDataURL('image/png')
    link.click()
    toast.success('QR Code berhasil didownload.')
  }, [nomorFkp, trackingUrl])

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(trackingUrl)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = trackingUrl
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    setCopied(true)
    toast.success('URL tracking disalin ke clipboard.')
    setTimeout(() => setCopied(false), 2500)
  }, [trackingUrl])

  return (
    <div className="flex flex-col items-center gap-5">
      {/* Info */}
      <p className="text-sm text-gray-500 text-center max-w-xs">
        Scan QR Code ini untuk memantau progres keluhan tanpa perlu login ke aplikasi.
      </p>

      {/* QR Canvas — bisa diklik untuk buka tracking di tab baru */}
      <a
        href={trackingUrl}
        target="_blank"
        rel="noreferrer"
        title="Buka halaman tracking publik"
        className="group relative block"
      >
        <div
          ref={canvasRef}
          className="p-4 bg-white border-2 border-gray-200 rounded-2xl shadow-sm
                     group-hover:border-brand-400 group-hover:shadow-md transition-all"
        >
          <QRCodeCanvas
            value={trackingUrl}
            size={220}
            level="M"
            includeMargin={false}
          />
        </div>
        {/* Hover overlay */}
        <div className="absolute inset-0 flex items-center justify-center
                        opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl
                        bg-brand-500/10">
          <span className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 text-white
                           text-xs font-medium rounded-full shadow">
            <ExternalLink className="w-3.5 h-3.5" />
            Buka Tracking
          </span>
        </div>
      </a>

      {/* Label nomor FKP */}
      <p className="text-xs font-mono text-gray-400">{nomorFkp}</p>

      {/* URL preview */}
      <div className="w-full px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-[11px] font-mono text-gray-500 break-all text-center">{trackingUrl}</p>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 w-full">
        <button
          onClick={handleDownload}
          className="flex-1 flex items-center justify-center gap-2
                     py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-gray-700
                     hover:bg-gray-50 hover:border-gray-300 transition-all font-medium"
        >
          <Download className="w-4 h-4 text-gray-500" />
          Download PNG
        </button>
        <button
          onClick={handleCopy}
          className={`
            flex-1 flex items-center justify-center gap-2
            py-2.5 rounded-xl border text-sm font-medium transition-all
            ${copied
              ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
              : 'border-brand-300 bg-brand-50 text-brand-700 hover:bg-brand-100'
            }
          `}
        >
          {copied
            ? <><Check className="w-4 h-4" /> Tersalin!</>
            : <><Copy className="w-4 h-4" /> Salin URL</>
          }
        </button>
      </div>

      <p className="text-[11px] text-gray-400 text-center">
        Klik gambar QR untuk membuka halaman tracking publik di tab baru
      </p>
    </div>
  )
}


// ─── QR Trigger Button — tampil di sidebar ────────────────────────────────────

function QrTriggerCard({
  fkpId,
  nomorFkp,
  onClick,
}: {
  fkpId: string
  nomorFkp: string
  onClick: () => void
}) {
  const canvasRef = useRef<HTMLDivElement>(null)
  const trackingUrl = `${window.location.origin}/track/${fkpId}`

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="font-semibold text-gray-900 flex items-center gap-2">
          <QrCode className="w-4 h-4 text-brand-500" />
          QR Tracking
        </h2>
      </div>
      <div className="card-body flex flex-col items-center gap-3">
        {/* QR preview kecil — klik buka modal */}
        <button
          onClick={onClick}
          className="group relative p-2.5 bg-white border border-gray-200 rounded-xl
                     hover:border-brand-400 hover:shadow-md transition-all"
          title="Klik untuk memperbesar"
        >
          {/* Canvas tersembunyi untuk referensi download di modal */}
          <div ref={canvasRef}>
            <QRCodeCanvas
              value={trackingUrl}
              size={120}
              level="M"
              includeMargin={false}
            />
          </div>
          {/* Hover overlay */}
          <div className="absolute inset-0 flex items-center justify-center rounded-xl
                          bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-white text-xs font-semibold">Lihat QR</span>
          </div>
        </button>

        <p className="text-xs font-mono text-gray-400 text-center">{nomorFkp}</p>

        {/* Tombol Download & Buka — langsung dari card kecil */}
        <div className="flex gap-2 w-full">
          <button
            onClick={onClick}
            className="flex-1 btn-secondary btn-sm flex items-center justify-center gap-1.5 text-xs"
          >
            <Download className="w-3.5 h-3.5" />
            Download
          </button>
          <a
            href={trackingUrl}
            target="_blank"
            rel="noreferrer"
            className="flex-1 btn-secondary btn-sm flex items-center justify-center gap-1.5 text-xs"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Tracking
          </a>
        </div>
      </div>
    </div>
  )
}


// ─── Main Page ────────────────────────────────────────────────────────────────

export function FkpDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const kodeRole = useKodeRole()
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()

  const { data: fkp, isLoading, isError } = useFkpDetail(id)
  const { data: products = [] } = useProducts()
  const canWrite = useCanWriteFkp(fkp)

  const [modal, setModal] = useState<ModalTipe | null>(null)
  const [catatan, setCatatan] = useState('')
  const [isConfirming, setIsConfirming] = useState(false)

  const [apsmReviews, setApsmReviews] = useState<Record<string, ApsmReviewState>>({})
  const [adminHoReviews, setAdminHoReviews] = useState<Record<string, AdminHoReviewState>>({})
  const [qcResults, setQcResults] = useState<Record<string, QcItemResult>>({})
  const [sumber, setSumber] = useState<'internal' | 'pelanggan'>('internal')

  const [tipeResolusi, setTipeResolusi] = useState('tukar_barang')
  const [resolusiForm, setResolusiForm] = useState({
    nilai_cashback: '', nama_bank: '', nomor_rekening: '',
    atas_nama: '', nomor_nota_retur: '', keterangan: '',
    tanggal_pemusnahan: '', lokasi_pemusnahan: '',
    metode_penanganan_fisik: 'dimusnahkan' as MetodePenangananFisik,
    detail_penanganan: '',
    persentase_kompensasi_disetujui: '',
  })

  // Fase 2 potong_tagihan — hanya detail rekening (nilai_nota_penjualan
  // pindah ke invoiceForm, lihat catatan di types/index.ts ResolusiPayload)
  const [rekeningForm, setRekeningForm] = useState({
    nama_bank: '', nomor_rekening: '', atas_nama: '', nomor_nota_retur: '',
  })

  // Fase 2 tukar_barang — qty disetujui per item, dikirim sekali lewat
  // buat_resolusi() sebelum membuat Surat Jalan yang pertama
  const [itemQtyDisetujui, setItemQtyDisetujui] = useState<Record<string, string>>({})

  // Form pembuatan Surat Jalan (Warehouse SJ) — item dikirim dikonstruksi
  // langsung dari fkp.items (status_item === 'diterima') + itemQtyDisetujui
  // saat submit (lihat case 'lengkapi_qty_sj' di handleConfirm), jadi tidak
  // perlu state array items terpisah di sini.
  const [sjForm, setSjForm] = useState({
    nomor_surat_jalan: '', tanggal_surat_jalan: '', nama_penerima: '',
    alamat_penerima: '', telepon_penerima: '', ekspedisi: '',
    nomor_resi: '', tanggal_kirim: '', catatan: '',
  })

  // Form terbitkan invoice (potong_tagihan)
  const [invoiceForm, setInvoiceForm] = useState({
    nomor_invoice: '', nilai_nota_penjualan: '', catatan: '',
  })

  // Form ship Surat Jalan yang sudah ada (issued → shipped)
  const [selectedSjId, setSelectedSjId] = useState<string | null>(null)
  const [shipForm, setShipForm] = useState({ ekspedisi: '', nomor_resi: '', tanggal_kirim: '' })

  const { mutate: submit, isPending: isSubmitting } = useSubmitFkp(id ?? '')
  const { data: suratJalanList = [] } = useSuratJalanList(id)
  // Dipakai HANYA untuk gate peringatan (item 5, QC investigasi) — daftar
  // sample lengkap dengan aksi ada di SampleShipmentSection tersendiri.
  const { data: sampleListForGate = [] } = useSampleList(id)

  const closeModal = () => { setModal(null); setCatatan('') }

  const runAction = async (fn: () => Promise<unknown>) => {
    setIsConfirming(true)
    try {
      await fn()
      qc.invalidateQueries({ queryKey: fkpKeys.detail(id!) })
      qc.invalidateQueries({ queryKey: fkpKeys.all })
      closeModal()
      toast.success('Aksi berhasil.')
    } catch (e: any) {
      const d = e?.response?.data?.detail
      toast.error(typeof d === 'string' ? d : 'Terjadi kesalahan.')
    } finally {
      setIsConfirming(false)
    }
  }

  const openResolusiModal = () => {
    if (fkp?.resolution) {
      const r = fkp.resolution
      setTipeResolusi(r.tipe_resolusi)
      setResolusiForm({
        nilai_cashback: String(r.nilai_cashback ?? ''),
        nama_bank: r.nama_bank ?? '',
        nomor_rekening: r.nomor_rekening ?? '',
        atas_nama: r.atas_nama ?? '',
        nomor_nota_retur: r.nomor_nota_retur ?? '',
        keterangan: r.keterangan ?? '',
        tanggal_pemusnahan: r.tanggal_pemusnahan ?? '',
        lokasi_pemusnahan: r.lokasi_pemusnahan ?? '',
        metode_penanganan_fisik: r.metode_penanganan_fisik ?? 'dimusnahkan',
        detail_penanganan: r.detail_penanganan ?? '',
        persentase_kompensasi_disetujui: r.persentase_kompensasi_disetujui
          ? String(r.persentase_kompensasi_disetujui) : '',
      })
    } else {
      setTipeResolusi('tukar_barang')
      setResolusiForm({
        nilai_cashback: '', nama_bank: '', nomor_rekening: '',
        atas_nama: '', nomor_nota_retur: '', keterangan: '',
        tanggal_pemusnahan: '', lokasi_pemusnahan: '',
        metode_penanganan_fisik: 'dimusnahkan',
        detail_penanganan: '', persentase_kompensasi_disetujui: '',
      })
    }
    // [BARU — gabung dengan Set Qty] Kalau dibuka di status 'accepted' untuk
    // tukar_barang, sekalian prefill qty_disetujui — modal ini jadi dipakai
    // ulang untuk 2 fase sekaligus (satu kesatuan alur, sesuai permintaan).
    if (fkp?.status === 'accepted') {
      const itemsDiterima = fkp?.items.filter((item) => item.status_item === 'diterima') ?? []
      const initialQty: Record<string, string> = {}
      itemsDiterima.forEach((item) => {
        initialQty[item.id] = item.qty_disetujui ? String(item.qty_disetujui) : String(item.qty)
      })
      setItemQtyDisetujui(initialQty)
    }
    setModal('buat_resolusi')
  }

  // ── tukar_barang: buka modal qty disetujui + form Surat Jalan ──────────
  const openSjModal = () => {
    const itemsDiterima = fkp?.items.filter((item) => item.status_item === 'diterima') ?? []
    const initialQty: Record<string, string> = {}
    itemsDiterima.forEach((item) => {
      initialQty[item.id] = item.qty_disetujui ? String(item.qty_disetujui) : String(item.qty)
    })
    setItemQtyDisetujui(initialQty)
    setSjForm({
      nomor_surat_jalan: '', tanggal_surat_jalan: '', nama_penerima: '',
      alamat_penerima: '', telepon_penerima: '', ekspedisi: '',
      nomor_resi: '', tanggal_kirim: '', catatan: '',
    })
    setModal('lengkapi_qty_sj')
  }

  // ── potong_tagihan: lengkapi detail rekening (Fase 2 buat_resolusi) ─────
  const openRekeningModal = () => {
    const r = fkp?.resolution
    setRekeningForm({
      nama_bank: r?.nama_bank ?? '',
      nomor_rekening: r?.nomor_rekening ?? '',
      atas_nama: r?.atas_nama ?? '',
      nomor_nota_retur: r?.nomor_nota_retur ?? '',
    })
    setModal('lengkapi_rekening')
  }

  // ── potong_tagihan: terbitkan invoice (trigger in_process) ──────────────
  const openInvoiceModal = () => {
    setInvoiceForm({ nomor_invoice: '', nilai_nota_penjualan: '', catatan: '' })
    setModal('terbitkan_invoice')
  }

  // ── tidak_ada_kompensasi: konfirmasi resolusi (trigger in_process) ──────
  const openConfirmResolusiModal = () => {
    setCatatan('')
    setModal('confirm_resolusi')
  }

  // ── Surat Jalan existing: kirim (issued → shipped) ──────────────────────
  const openShipSjModal = (sjId: string) => {
    setSelectedSjId(sjId)
    setShipForm({ ekspedisi: '', nomor_resi: '', tanggal_kirim: '' })
    setModal('sj_ship')
  }

  const handleConfirm = () => {
    if (!id) return
    switch (modal) {

      case 'apsm_review':
        return runAction(() => fkpApi.apsmReview(id, {
          catatan_apsm: catatan || null,
          item_reviews: fkp?.items.map((item) => {
            const r: ApsmReviewState = apsmReviews[item.id] ?? APSM_REVIEW_BLANK
            return {
              item_id: item.id,
              rekomendasi_penanganan_apsm: r.rekomendasi_penanganan_apsm ? r.rekomendasi_penanganan_apsm as RekomendasiPenanganan : null,
              rekomendasi_kompensasi_apsm: r.rekomendasi_kompensasi_apsm ? r.rekomendasi_kompensasi_apsm as RekomendasiKompensasi : null,
              catatan_apsm: r.catatan_apsm || null,
              persentase_disetujui_apsm: r.persentase_disetujui_apsm ? Number(r.persentase_disetujui_apsm) : null,
            }
          }) ?? null,
        }))

      case 'admin_ho_review':
        return runAction(() => fkpApi.adminHoReview(id, {
          catatan_admin: catatan || null,
          item_reviews: fkp?.items.map((item) => {
            const r: AdminHoReviewState = adminHoReviews[item.id] ?? ADMIN_HO_REVIEW_BLANK
            return {
              item_id: item.id,
              rekomendasi_penanganan_admin_ho: r.rekomendasi_penanganan_admin_ho ? r.rekomendasi_penanganan_admin_ho as RekomendasiPenanganan : null,
              rekomendasi_kompensasi_admin_ho: r.rekomendasi_kompensasi_admin_ho ? r.rekomendasi_kompensasi_admin_ho as RekomendasiKompensasi : null,
              catatan_admin_ho: r.catatan_admin_ho || null,
              persentase_disetujui_admin_ho: r.persentase_disetujui_admin_ho ? Number(r.persentase_disetujui_admin_ho) : null,
            }
          }) ?? null,
        }))

      case 'rsm_investigasi_ok':
        return runAction(() => fkpApi.rsmApproveInvestigasi(id, { disetujui: true, catatan: catatan || null }))
      case 'rsm_investigasi_tolak':
        if (!catatan.trim()) { toast.error('Alasan wajib diisi.'); return }
        return runAction(() => fkpApi.rsmApproveInvestigasi(id, { disetujui: false, catatan }))

      case 'qc_investigasi':
        return runAction(() => fkpApi.qcInvestigasi(id, {
          sumber_ketidaksesuaian: sumber,
          catatan_qc: catatan || null,
          item_results: fkp?.items.map((item) => {
            const r = qcResults[item.id] ?? { status_item: 'diterima', catatan_qc: '', alasan_penolakan: '' }
            return {
              item_id: item.id,
              status_item: r.status_item || 'diterima',
              catatan_qc: r.catatan_qc || null,
              alasan_penolakan: r.alasan_penolakan || null,
            }
          }),
        }))

      case 'buat_resolusi': {
        // [BARU] Status 'accepted' + tukar_barang → modal ini dipakai untuk isi
        // qty_disetujui (Fase 2), BUKAN tipe_resolusi/metode (itu sudah terkunci
        // sejak Fase 1). Endpoint sama (POST /resolusi → buat_resolusi()), hanya
        // payload & validasi klien yang beda.
        if (fkp?.status === 'accepted' && tipeResolusiAktif === 'tukar_barang') {
          const itemsDiterima = fkp?.items.filter((item) => item.status_item === 'diterima') ?? []
          if (itemsDiterima.length === 0) { toast.error('Tidak ada item berstatus diterima.'); return }
          return runAction(() => fkpApi.updateDetailResolusi(id, {
            item_qty_disetujui: itemsDiterima.map((item) => ({
              item_id: item.id,
              qty_disetujui: Number(itemQtyDisetujui[item.id] ?? item.qty),
            })),
          }))
        }
        return runAction(() => fkpApi.createResolusi(id, {
          tipe_resolusi: tipeResolusi,
          metode_penanganan_fisik: resolusiForm.metode_penanganan_fisik,
          detail_penanganan: resolusiForm.detail_penanganan || null,
          lokasi_pemusnahan: resolusiForm.lokasi_pemusnahan || null,
          tanggal_pemusnahan: resolusiForm.tanggal_pemusnahan || null,
          keterangan: resolusiForm.keterangan || null,
          persentase_kompensasi_disetujui:
            tipeResolusi === 'potong_tagihan' && resolusiForm.persentase_kompensasi_disetujui
              ? Number(resolusiForm.persentase_kompensasi_disetujui)
              : null,
        }))
      }

      case 'request_resolusi_approval':
        return runAction(() => fkpApi.requestResolusiApproval(id, catatan || null))
      case 'rsm_resolusi_ok':
        return runAction(() => fkpApi.rsmApproveResolusi(id, { disetujui: true, catatan: catatan || null }))
      case 'rsm_resolusi_tolak':
        if (!catatan.trim()) { toast.error('Alasan wajib diisi.'); return }
        return runAction(() => fkpApi.rsmApproveResolusi(id, { disetujui: false, catatan }))
      case 'direktur_ok':
        return runAction(() => fkpApi.direkturApprove(id, { disetujui: true, catatan: catatan || null }))
      case 'direktur_tolak':
        if (!catatan.trim()) { toast.error('Alasan wajib diisi.'); return }
        return runAction(() => fkpApi.direkturApprove(id, { disetujui: false, catatan }))

      // tukar_barang — simpan qty disetujui, lalu buat Surat Jalan pertama.
      // Ini yang men-trigger accepted → in_process di backend (bukan
      // buat_resolusi), lihat catatan di api/warehouse.ts.
      case 'lengkapi_qty_sj': {
        const itemsDiterima = fkp?.items.filter((item) => item.status_item === 'diterima') ?? []
        if (!sjForm.nomor_surat_jalan.trim()) { toast.error('Nomor surat jalan wajib diisi.'); return }
        if (!sjForm.tanggal_surat_jalan) { toast.error('Tanggal surat jalan wajib diisi.'); return }
        if (!sjForm.nama_penerima.trim()) { toast.error('Nama penerima wajib diisi.'); return }
        if (!sjForm.alamat_penerima.trim()) { toast.error('Alamat penerima wajib diisi.'); return }
        if (itemsDiterima.length === 0) { toast.error('Tidak ada item berstatus diterima untuk dikirim.'); return }
        return runAction(async () => {
          // [FIX — Opsi A] Step "simpan qty_disetujui ke FkpItem" DIHAPUS dari
          // sini. Endpoint itu (buat_resolusi/updateDetailResolusi) butuh
          // permission fkp.resolution.manage yang sengaja admin_ho-only, jadi
          // warehouse SELALU 403 kalau lewat sini. Qty untuk Surat Jalan ini
          // sekarang dikirim LANGSUNG sebagai item Surat Jalan
          // (warehouse_surat_jalan_items) tanpa menulis balik ke
          // fkp_items.qty_disetujui. Kalau Admin HO perlu mencatat qty_disetujui
          // resmi di level FKP, pakai tombol terpisah "Set Qty Disetujui"
          // (lihat openSetQtyModal(), admin_ho only).
          await warehouseApi.create(id, {
            nomor_surat_jalan: sjForm.nomor_surat_jalan,
            tanggal_surat_jalan: sjForm.tanggal_surat_jalan,
            nama_penerima: sjForm.nama_penerima,
            alamat_penerima: sjForm.alamat_penerima,
            telepon_penerima: sjForm.telepon_penerima || null,
            ekspedisi: sjForm.ekspedisi || null,
            nomor_resi: sjForm.nomor_resi || null,
            tanggal_kirim: sjForm.tanggal_kirim || null,
            catatan: sjForm.catatan || null,
            items: itemsDiterima.map((item) => ({
              fkp_item_id: item.id,
              nama_produk: item.nama_produk_custom ?? 'Produk',
              qty: Number(itemQtyDisetujui[item.id] ?? item.qty_disetujui ?? item.qty),
              satuan: item.jenis_kemasan ?? 'pcs',
            })),
          })
          qc.invalidateQueries({ queryKey: warehouseKeys.list(id) })
        })
      }

      // potong_tagihan — Fase 2: detail rekening (tidak trigger status apa pun)
      case 'lengkapi_rekening':
        if (!rekeningForm.nama_bank.trim() || !rekeningForm.nomor_rekening.trim() || !rekeningForm.atas_nama.trim()) {
          toast.error('Nama bank, nomor rekening, dan atas nama wajib diisi.'); return
        }
        return runAction(() => fkpApi.updateDetailResolusi(id, {
          nama_bank: rekeningForm.nama_bank,
          nomor_rekening: rekeningForm.nomor_rekening,
          atas_nama: rekeningForm.atas_nama,
          nomor_nota_retur: rekeningForm.nomor_nota_retur || null,
        }))

      // potong_tagihan — terbitkan invoice. INI yang trigger accepted → in_process.
      case 'terbitkan_invoice':
        if (!invoiceForm.nomor_invoice.trim()) { toast.error('Nomor invoice wajib diisi.'); return }
        if (!invoiceForm.nilai_nota_penjualan || Number(invoiceForm.nilai_nota_penjualan) <= 0) {
          toast.error('Nilai nota penjualan wajib diisi dan lebih dari 0.'); return
        }
        return runAction(() => financeApi.terbitkanInvoice(id, {
          nomor_invoice: invoiceForm.nomor_invoice,
          nilai_nota_penjualan: Number(invoiceForm.nilai_nota_penjualan),
          catatan: invoiceForm.catatan || null,
        }))

      // potong_tagihan — langkah kedua, konfirmasi pembayaran sudah ditransfer
      case 'proses_finance':
        return runAction(() => financeApi.prosesFinance(id, { catatan: catatan || null }))

      // tidak_ada_kompensasi (± dimusnahkan) — INI yang trigger accepted → in_process
      case 'confirm_resolusi':
        if (fkp?.resolution?.tipe_resolusi === 'tidak_ada_kompensasi' && !catatan.trim()) {
          toast.error('Catatan/alasan wajib diisi untuk resolusi tanpa kompensasi.'); return
        }
        return runAction(() => fkpApi.confirmResolusi(id, catatan || null))

      // Surat Jalan yang sudah issued → shipped
      case 'sj_ship':
        if (!selectedSjId) return
        return runAction(async () => {
          await warehouseApi.ship(id, selectedSjId, {
            ekspedisi: shipForm.ekspedisi || null,
            nomor_resi: shipForm.nomor_resi || null,
            tanggal_kirim: shipForm.tanggal_kirim || null,
          })
          qc.invalidateQueries({ queryKey: warehouseKeys.list(id) })
        })

      case 'revision':
        if (!catatan.trim()) { toast.error('Alasan revisi wajib diisi.'); return }
        return runAction(() => fkpApi.requestRevision(id, { catatan }))
      case 'reject':
        if (!catatan.trim()) { toast.error('Alasan penolakan wajib diisi.'); return }
        return runAction(() => fkpApi.reject(id, { catatan }))
      case 'close':
        return runAction(() => fkpApi.close(id, catatan || null))
    }
  }

  // ── Guard ─────────────────────────────────────────────────────────────────
  if (isLoading) return <PageLoader />
  if (isError || !fkp) return (
    <div className="card card-body text-center py-12">
      <p className="text-red-500 font-medium">FKP tidak ditemukan.</p>
      <button onClick={() => navigate('/fkp')} className="btn-secondary mt-4 mx-auto">
        <ArrowLeft className="w-4 h-4" /> Kembali
      </button>
    </div>
  )

  const canEdit = canWrite && (fkp.status === 'draft' || fkp.status === 'need_revision')
  const hasResolusi = !!fkp.resolution
  const canCreateResolusi = kodeRole === 'admin_ho' && fkp.status === 'investigated' && !fkp.resolution
  const canEditResolusi = kodeRole === 'admin_ho' && ['investigated', 'rsm_approval_resolusi'].includes(fkp.status) && !!fkp.resolution
  const resolusiTerkunci = !!fkp.resolution && ['direktur_approval', 'accepted', 'in_process', 'closed', 'rejected'].includes(fkp.status)

  // ── Helper untuk alur accepted → in_process per tipe resolusi ───────────
  // [FIX] role yang berhak menjalankan tahap ini BUKAN cuma admin_ho lagi —
  // lihat RBAC §11.2 dokumen rencana modul: warehouse berhak buat Surat
  // Jalan, finance berhak terbitkan invoice.
  const tipeResolusiAktif = fkp.resolution?.tipe_resolusi
  const rekeningTerisi = !!(fkp.resolution?.nama_bank && fkp.resolution?.nomor_rekening && fkp.resolution?.atas_nama)
  const invoiceDoc = fkp.documents?.find((d) => d.tipe_dokumen === 'invoice_potong_tagihan') ?? null
  const bisaKelolaSj = ['admin_ho', 'warehouse', 'superadmin'].includes(kodeRole)
  const bisaKelolaInvoice = ['admin_ho', 'finance', 'superadmin'].includes(kodeRole)
  const bisaConfirmResolusi = ['admin_ho', 'superadmin'].includes(kodeRole)

  // ── Item 5: gate peringatan investigasi QC ──────────────────────────────
  // Persis kondisi yang dicek backend di qc_investigasi() (§7.1 dokumen
  // rencana modul): semua sample AKTIF (non-terminal) harus sudah
  // examined/cancelled. Dihitung di sini juga supaya tombol submit bisa
  // diberi peringatan/nonaktif SEBELUM submit gagal dengan 400, bukan sesudah.
  const samplesBelumSelesai = sampleListForGate.filter((s) => !SAMPLE_STATUS_TERMINAL.includes(s.status))

  // ── Item 4: soft warning saat Tutup FKP ─────────────────────────────────
  // [CATATAN] close_fkp() di backend TIDAK mengecek precondition ini sama
  // sekali — closing murni manual & tanpa syarat begitu status in_process
  // (Open Question #2 di dokumen rencana: "manual", bukan otomatis). Ini
  // murni pencegahan human-error di FE, backend tetap mengizinkan close
  // meski warning ini muncul.
  const closeWarnings: string[] = []
  if (tipeResolusiAktif === 'tukar_barang') {
    const belumDelivered = suratJalanList.filter((sj) => sj.status !== 'delivered')
    if (belumDelivered.length > 0) {
      closeWarnings.push(`Ada ${belumDelivered.length} Surat Jalan yang belum berstatus "Diterima".`)
    }
  }
  if (tipeResolusiAktif === 'potong_tagihan' && !fkp.resolution?.diproses_finance) {
    closeWarnings.push('Pembayaran cashback belum dikonfirmasi sudah ditransfer.')
  }

  const hasAnyAction =
    canEdit ||
    (fkp.status === 'submitted' && kodeRole === 'apsm') ||
    (fkp.status === 'apsm_reviewed' && kodeRole === 'admin_ho') ||
    (fkp.status === 'rsm_approval_investigasi' && kodeRole === 'rsm') ||
    (fkp.status === 'in_investigation' && kodeRole === 'qc') ||
    (fkp.status === 'investigated' && kodeRole === 'admin_ho') ||
    (fkp.status === 'rsm_approval_resolusi' && kodeRole === 'rsm') ||
    (fkp.status === 'direktur_approval' && kodeRole === 'direktur') ||
    (fkp.status === 'accepted' && (bisaKelolaSj || bisaKelolaInvoice)) ||
    (fkp.status === 'in_process' && (kodeRole === 'admin_ho' || kodeRole === 'superadmin' || bisaKelolaSj || bisaKelolaInvoice))

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/fkp')} className="btn-ghost btn-sm p-2">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <p className="text-xs font-mono text-gray-400">{fkp.nomor_fkp}</p>
            <h1 className="text-xl font-bold text-gray-900 mt-0.5">Detail FKP</h1>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <PrioritasBadge prioritas={fkp.prioritas} />
          <StatusBadge status={fkp.status} />
        </div>
      </div>

      {/* ── Banner need_revision ─────────────────────────────────────────── */}
      {fkp.status === 'need_revision' && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-800">FKP Perlu Diperbaiki</p>
            <p className="text-sm text-red-700 mt-0.5">Periksa catatan, perbaiki data/item, lalu submit kembali.</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ── Kiri ──────────────────────────────────────────────────────── */}
        <div className="lg:col-span-2 space-y-5 order-2 lg:order-1">

          {/* Info FKP */}
          <div className="card">
            <div className="card-header">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-brand-500" /> Info FKP
              </h2>
            </div>
            <div className="card-body">
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                <InfoRow label="Nomor FKP" value={fkp.nomor_fkp} mono />
                <InfoRow label="Prioritas" value={fkp.prioritas.replace('_', ' ')} className="capitalize" />
                {fkp.tanggal_pengajuan && <InfoRow label="Tgl Pengajuan" value={formatDateTime(fkp.tanggal_pengajuan)} />}
                {fkp.tanggal_selesai && <InfoRow label="Tgl Selesai" value={formatDateTime(fkp.tanggal_selesai)} />}
                {/* [FIX] fkp.nomor_surat_jalan (fkp_complaints.nomor_surat_jalan)
                    DIHAPUS dari sini — field deprecated per §9 dokumen rencana
                    modul, sekarang selalu kosong untuk FKP baru. Nomor surat
                    jalan yang benar ada di kartu "Surat Jalan (Barang
                    Pengganti)" di bawah, sumbernya WarehouseSuratJalan. */}
              </dl>
              {fkp.catatan_distributor && (
                <div className="mt-4 pt-4 border-t border-gray-50">
                  <p className="text-xs font-medium text-gray-500 mb-1">Catatan Outlet/Distributor/SC/SPV</p>
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{fkp.catatan_distributor}</p>
                </div>
              )}
            </div>
          </div>

          {/* Items */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Package className="w-4 h-4 text-brand-500" /> Item Produk ({fkp.items.length})
                </h2>
              </div>
            </div>
            <div className="card-body space-y-4">
              {fkp.items.length === 0
                ? <p className="text-sm text-gray-400 text-center py-4">Belum ada item.</p>
                : fkp.items.map((item, idx) => (
                  <FkpItemCard
                    key={item.id} item={item} idx={idx} products={products}
                    attachments={fkp.attachments.filter((a) => a.fkp_item_id === item.id)}
                  />
                ))}
            </div>
          </div>

          {/* Sample Shipment — pengiriman sample fisik ke QC pusat. Selalu
              ditampilkan kecuali FKP masih draft (belum boleh didaftarkan
              sample apapun, lihat guard backend §4.3). */}
          {fkp.status !== 'draft' && (
            <SampleShipmentSection
              fkpId={fkp.id}
              fkpItems={fkp.items}
              fkpStatus={fkp.status}
              attachments={fkp.attachments}
            />
          )}

          {/* Catatan proses */}
          {(fkp.catatan_sc_spv || fkp.catatan_apsm || fkp.catatan_admin ||
            fkp.catatan_qc || fkp.catatan_rsm_investigasi ||
            fkp.catatan_rsm_resolusi || fkp.catatan_direktur) && (
              <div className="card">
                <div className="card-header"><h2 className="font-semibold text-gray-900">Catatan Proses</h2></div>
                <div className="card-body space-y-3">
                  <CatatanItem label="SC / SPV" value={fkp.catatan_sc_spv} />
                  <CatatanItem label="APSM" value={fkp.catatan_apsm} />
                  <CatatanItem label="Admin HO" value={fkp.catatan_admin} />
                  <CatatanItem label="QC" value={fkp.catatan_qc} />
                  <CatatanItem label="RSM (Investigasi)" value={fkp.catatan_rsm_investigasi} />
                  <CatatanItem label="RSM (Resolusi)" value={fkp.catatan_rsm_resolusi} />
                  <CatatanItem label="Direktur" value={fkp.catatan_direktur} />
                </div>
              </div>
            )}

          {/* Resolusi */}
          {fkp.resolution && (
            <div className="card border-l-4 border-l-emerald-400">
              <div className="card-header">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Resolusi yang Diusulkan
                    {resolusiTerkunci && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                             text-xs bg-gray-100 text-gray-500 border border-gray-200">
                        🔒 Terkunci
                      </span>
                    )}
                  </h2>
                  {canEditResolusi && (
                    <button onClick={openResolusiModal} className="btn-secondary btn-sm flex items-center gap-1.5">
                      <Edit2 className="w-3.5 h-3.5" /> Edit Resolusi
                    </button>
                  )}
                </div>
              </div>
              <div className="card-body">
                <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                  <InfoRow label="Tipe Kompensasi" value={TIPE_RESOLUSI_LABEL[fkp.resolution.tipe_resolusi] ?? fkp.resolution.tipe_resolusi} />
                  {fkp.resolution.metode_penanganan_fisik && (
                    <InfoRow label="Penanganan Fisik" value={METODE_PENANGANAN_LABEL[fkp.resolution.metode_penanganan_fisik] ?? fkp.resolution.metode_penanganan_fisik} />
                  )}
                  {fkp.resolution.detail_penanganan && <InfoRow label="Detail Penanganan" value={fkp.resolution.detail_penanganan} />}
                  {fkp.resolution.persentase_kompensasi_disetujui != null && (
                    <InfoRow label="Persentase Kompensasi" value={`${fkp.resolution.persentase_kompensasi_disetujui}%`} />
                  )}
                  {fkp.resolution.nilai_nota_penjualan != null && (
                    <InfoRow label="Nilai Nota Penjualan" value={formatRupiah(fkp.resolution.nilai_nota_penjualan)} />
                  )}
                  {fkp.resolution.nilai_cashback && <InfoRow label="Nilai Cashback" value={formatRupiah(fkp.resolution.nilai_cashback)} />}
                  {fkp.resolution.nama_bank && <InfoRow label="Bank" value={fkp.resolution.nama_bank} />}
                  {fkp.resolution.nomor_rekening && <InfoRow label="No. Rekening" value={fkp.resolution.nomor_rekening} mono />}
                  {fkp.resolution.atas_nama && <InfoRow label="Atas Nama" value={fkp.resolution.atas_nama} />}
                  {fkp.resolution.nomor_do && <InfoRow label="Nomor DO" value={fkp.resolution.nomor_do} mono />}
                  {fkp.resolution.ekspedisi && <InfoRow label="Ekspedisi" value={fkp.resolution.ekspedisi} />}
                  {fkp.resolution.resi_pengiriman && <InfoRow label="No. Resi" value={fkp.resolution.resi_pengiriman} mono />}
                  {fkp.resolution.lokasi_pemusnahan && <InfoRow label="Lokasi Pemusnahan" value={fkp.resolution.lokasi_pemusnahan} />}
                  {fkp.resolution.keterangan && (
                    <div className="col-span-2">
                      <p className="text-xs font-medium text-gray-500 mb-1">Keterangan</p>
                      <p className="text-sm text-gray-800">{fkp.resolution.keterangan}</p>
                    </div>
                  )}
                </dl>

                {/* ── potong_tagihan: info invoice yang sudah diterbitkan ── */}
                {tipeResolusiAktif === 'potong_tagihan' && invoiceDoc && (
                  <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-xs text-emerald-800">
                        <p className="font-semibold">📄 Invoice {invoiceDoc.nomor_dokumen}</p>
                        <p className="text-emerald-600">
                          {fkp.resolution.tanggal_proses_finance
                            ? '✅ Pembayaran sudah dikonfirmasi ditransfer'
                            : 'Menunggu konfirmasi pembayaran'}
                        </p>
                      </div>
                      <button
                        type="button"
                        className="btn-secondary btn-sm flex items-center gap-1.5 whitespace-nowrap"
                        onClick={() => openAuthenticatedFile(financeApi.invoicePdfPath(fkp.id, invoiceDoc.id), token)}
                      >
                        <Download className="w-3.5 h-3.5" /> Unduh PDF
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── tukar_barang: daftar Surat Jalan (barang pengganti) ─────────── */}
          {tipeResolusiAktif === 'tukar_barang' && ['accepted', 'in_process', 'closed'].includes(fkp.status) && (
            <div className="card">
              <div className="card-header">
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Truck className="w-4 h-4 text-brand-500" /> Surat Jalan (Barang Pengganti) ({suratJalanList.length})
                </h2>
              </div>
              <div className="card-body space-y-3">
                {suratJalanList.length === 0 && (
                  <p className="text-sm text-gray-500">Belum ada Surat Jalan dibuat.</p>
                )}
                {suratJalanList.map((sj) => (
                  <div key={sj.id} className="p-3 rounded-xl border border-gray-200 space-y-2">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div>
                        <p className="text-sm font-semibold text-gray-800">{sj.nomor_surat_jalan}</p>
                        <p className="text-xs text-gray-500">
                          {sj.nama_penerima} · {formatDateTime(sj.tanggal_surat_jalan)}
                        </p>
                      </div>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-brand-50 text-brand-700 border border-brand-200">
                        {SURAT_JALAN_STATUS_LABEL[sj.status]}
                      </span>
                    </div>
                    <ul className="text-xs text-gray-600 list-disc list-inside">
                      {sj.items.map((it) => (
                        <li key={it.id}>{it.nama_produk} — {it.qty} {it.satuan}</li>
                      ))}
                    </ul>
                    {bisaKelolaSj && (
                      <div className="flex flex-wrap gap-2 pt-1">
                        {sj.status === 'draft' && (
                          <button
                            className="btn-primary btn-sm"
                            onClick={() => runAction(async () => {
                              await warehouseApi.issue(fkp.id, sj.id)
                              qc.invalidateQueries({ queryKey: warehouseKeys.list(fkp.id) })
                            })}
                          >
                            Terbitkan (Generate PDF)
                          </button>
                        )}
                        {sj.status === 'issued' && (
                          <button className="btn-primary btn-sm" onClick={() => openShipSjModal(sj.id)}>
                            Tandai Dikirim
                          </button>
                        )}
                        {sj.status === 'shipped' && (
                          <button
                            className="btn-primary btn-sm"
                            onClick={() => runAction(async () => {
                              await warehouseApi.confirmDelivery(fkp.id, sj.id)
                              qc.invalidateQueries({ queryKey: warehouseKeys.list(fkp.id) })
                            })}
                          >
                            Konfirmasi Diterima
                          </button>
                        )}
                        {sj.url_pdf && (
                          <button
                            className="btn-secondary btn-sm flex items-center gap-1.5"
                            onClick={() => openAuthenticatedFile(warehouseApi.pdfPath(fkp.id, sj.id), token)}
                          >
                            <Download className="w-3.5 h-3.5" /> PDF
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                ))}
                {fkp.status === 'in_process' && bisaKelolaSj && (
                  <button className="btn-secondary w-full" onClick={openSjModal}>
                    <Plus className="w-4 h-4" /> Tambah Surat Jalan (Kirim Bertahap)
                  </button>
                )}
              </div>
            </div>
          )}
          {/* Foto umum — [FIX] exclude dokumen sample (sample_shipment_id
              terisi), sudah ditampilkan di kartu "Sample Shipment" masing2 */}
          {fkp.attachments.filter((a) => !a.fkp_item_id && !a.sample_shipment_id).length > 0 && (
            <div className="card">
              <div className="card-header">
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Paperclip className="w-4 h-4 text-brand-500" />
                  Dokumen / Foto Lampiran ({fkp.attachments.filter((a) => !a.fkp_item_id && !a.sample_shipment_id).length})
                </h2>
              </div>
              <div className="card-body">
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                  {fkp.attachments.filter((a) => !a.fkp_item_id && !a.sample_shipment_id).map((att) => (
                    <button
                      key={att.id}
                      type="button"
                      onClick={() => openAuthenticatedFile(att.url, token)}
                      className="aspect-square block"
                    >
                      <AuthenticatedImage
                        src={att.url}
                        alt={att.nama_file}
                        className="w-full h-full object-cover rounded-lg border border-gray-200 hover:opacity-90 transition-opacity"
                      />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Kanan: Aksi + QR + Riwayat ───────────────────────────────── */}
        <div className="space-y-5 order-1 lg:order-2">

          {/* Card Aksi */}
          {hasAnyAction && (
            <div className="card">
              <div className="card-header"><h2 className="font-semibold text-gray-900">Aksi</h2></div>
              <div className="card-body space-y-2">

                {fkp.status === 'submitted' && kodeRole === 'apsm' && (
                  <>
                    <button className="btn-primary w-full" onClick={() => setModal('apsm_review')}>
                      <ShieldCheck className="w-4 h-4" /> Review & Teruskan ke Admin HO
                    </button>
                    <button className="btn-secondary w-full" onClick={() => setModal('revision')}>
                      <AlertTriangle className="w-4 h-4" /> Minta Revisi
                    </button>
                  </>
                )}

                {fkp.status === 'apsm_reviewed' && kodeRole === 'admin_ho' && (
                  <>
                    <button className="btn-primary w-full" onClick={() => setModal('admin_ho_review')}>
                      <ShieldCheck className="w-4 h-4" /> Review & Teruskan ke RSM (Investigasi)
                    </button>
                    <button className="btn-secondary w-full" onClick={() => setModal('revision')}>
                      <AlertTriangle className="w-4 h-4" /> Minta Revisi ke APSM
                    </button>
                    <button className="btn-danger w-full" onClick={() => setModal('reject')}>
                      <XCircle className="w-4 h-4" /> Tolak FKP
                    </button>
                  </>
                )}

                {fkp.status === 'rsm_approval_investigasi' && kodeRole === 'rsm' && (
                  <>
                    <button className="btn-primary w-full flex flex-col" onClick={() => setModal('rsm_investigasi_ok')}>
                      <span className="flex items-center gap-1 justify-center">
                        <ShieldCheck className="w-4 h-4" /> Setujui Pengajuan
                      </span>
                      <span className="text-xs text-gray-200">(Mulai Investigasi QC)</span>
                    </button>
                    <button className="btn-secondary w-full" onClick={() => setModal('revision')}>
                      <AlertTriangle className="w-4 h-4" /> Kembalikan ke APSM
                    </button>
                    <button className="btn-danger w-full" onClick={() => setModal('rsm_investigasi_tolak')}>
                      <XCircle className="w-4 h-4" /> Tolak FKP
                    </button>
                  </>
                )}

                {fkp.status === 'in_investigation' && kodeRole === 'qc' && (
                  <button className="btn-primary w-full" onClick={() => setModal('qc_investigasi')}>
                    <CheckCircle2 className="w-4 h-4" /> Selesaikan Investigasi
                  </button>
                )}

                {fkp.status === 'investigated' && kodeRole === 'admin_ho' && (
                  <>
                    {canCreateResolusi && (
                      <>
                        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
                          ⚠️ Buat resolusi terlebih dahulu sebelum mengajukan ke RSM.
                        </div>
                        <button className="btn-primary w-full" onClick={openResolusiModal}>
                          <FileText className="w-4 h-4" /> Buat Resolusi
                        </button>
                      </>
                    )}
                    {hasResolusi && (
                      <>
                        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-700">
                          ✅ Resolusi sudah dibuat. Ajukan ke RSM untuk persetujuan.
                        </div>
                        {canEditResolusi && (
                          <button className="btn-secondary w-full" onClick={openResolusiModal}>
                            <Edit2 className="w-4 h-4" /> Edit Resolusi
                          </button>
                        )}
                        <button className="btn-primary w-full" onClick={() => setModal('request_resolusi_approval')}>
                          <ShieldCheck className="w-4 h-4" /> Ajukan Resolusi ke RSM
                        </button>
                        <button className="btn-danger w-full" onClick={() => setModal('reject')}>
                          <XCircle className="w-4 h-4" /> Tolak FKP
                        </button>
                      </>
                    )}
                  </>
                )}

                {fkp.status === 'rsm_approval_resolusi' && kodeRole === 'rsm' && (
                  <>
                    <button className="btn-primary w-full" onClick={() => setModal('rsm_resolusi_ok')}>
                      <ShieldCheck className="w-4 h-4" /> Setujui Resolusi → Ke Direktur
                    </button>
                    <button className="btn-secondary w-full" onClick={() => setModal('revision')}>
                      <AlertTriangle className="w-4 h-4" /> Kembalikan — Minta Perbaikan Resolusi
                    </button>
                    <button className="btn-danger w-full" onClick={() => setModal('rsm_resolusi_tolak')}>
                      <XCircle className="w-4 h-4" /> Tolak FKP
                    </button>
                  </>
                )}

                {fkp.status === 'direktur_approval' && kodeRole === 'direktur' && (
                  <>
                    <button className="btn-primary w-full" onClick={() => setModal('direktur_ok')}>
                      <CheckCircle2 className="w-4 h-4" /> Setujui FKP
                    </button>
                    <button className="btn-danger w-full" onClick={() => setModal('direktur_tolak')}>
                      <XCircle className="w-4 h-4" /> Tolak FKP
                    </button>
                  </>
                )}

                {fkp.status === 'accepted' && (
                  <>
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
                      ✅ FKP disetujui Direktur — resolusi: {TIPE_RESOLUSI_LABEL[tipeResolusiAktif as TipeResolusi] ?? '-'}
                    </div>

                    {/* ── tukar_barang: buat Surat Jalan (trigger in_process otomatis) ── */}
                    {tipeResolusiAktif === 'tukar_barang' && ['admin_ho', 'superadmin'].includes(kodeRole) && (
                      <button className="btn-secondary w-full" onClick={openResolusiModal}>
                        <Package className="w-4 h-4" /> Lengkapi Qty Disetujui
                      </button>
                    )}
                    {tipeResolusiAktif === 'tukar_barang' && bisaKelolaSj && (
                      <button className="btn-primary w-full" onClick={openSjModal}>
                        <Truck className="w-4 h-4" /> Buat Surat Jalan
                      </button>
                    )}
                    {tipeResolusiAktif === 'tukar_barang' && !bisaKelolaSj && (
                      <div className="text-xs text-slate-500">Menunggu Warehouse/Admin HO membuat Surat Jalan.</div>
                    )}

                    {/* ── potong_tagihan: lengkapi rekening → terbitkan invoice ── */}
                    {tipeResolusiAktif === 'potong_tagihan' && (
                      <>
                        {['admin_ho', 'superadmin'].includes(kodeRole) && (
                          <button className="btn-secondary w-full" onClick={openRekeningModal}>
                            <Banknote className="w-4 h-4" /> {rekeningTerisi ? 'Edit' : 'Lengkapi'} Detail Rekening
                          </button>
                        )}
                        {!rekeningTerisi && (
                          <div className="text-xs text-amber-600">
                            Detail rekening harus dilengkapi sebelum invoice bisa diterbitkan.
                          </div>
                        )}
                        {rekeningTerisi && bisaKelolaInvoice && (
                          <button className="btn-primary w-full" onClick={openInvoiceModal}>
                            <FileDown className="w-4 h-4" /> Terbitkan Invoice
                          </button>
                        )}
                      </>
                    )}

                    {/* ── tidak_ada_kompensasi (± dimusnahkan): konfirmasi resolusi ── */}
                    {tipeResolusiAktif === 'tidak_ada_kompensasi' && (
                      <>
                        {fkp.resolution?.metode_penanganan_fisik === 'dimusnahkan' &&
                          !fkp.attachments.some((a) => a.tipe_dokumen === 'berita_acara_pemusnahan_tukar_barang') && (
                            <div className="text-xs text-amber-600">
                              Upload dokumen "Berita Acara Pemusnahan & Tukar Barang" terlebih dahulu (lewat form tambah item/lampiran) sebelum konfirmasi resolusi.
                            </div>
                          )}
                        {bisaConfirmResolusi && (
                          <button className="btn-primary w-full" onClick={openConfirmResolusiModal}>
                            <CheckCircle2 className="w-4 h-4" /> Konfirmasi Resolusi
                          </button>
                        )}
                      </>
                    )}
                  </>
                )}

                {fkp.status === 'in_process' && (
                  <>
                    {/* ── tukar_barang: kelola Surat Jalan yang sudah ada — lihat kartu "Surat Jalan" di kolom utama ── */}
                    {tipeResolusiAktif === 'tukar_barang' && (
                      <div className="text-xs text-slate-500">Kelola status Surat Jalan di kartu "Surat Jalan (Barang Pengganti)" di bawah.</div>
                    )}

                    {/* ── potong_tagihan: konfirmasi pembayaran sudah ditransfer ── */}
                    {tipeResolusiAktif === 'potong_tagihan' && !fkp.resolution?.diproses_finance && bisaKelolaInvoice && (
                      <button className="btn-primary w-full" onClick={() => { setCatatan(''); setModal('proses_finance') }}>
                        <Banknote className="w-4 h-4" /> Konfirmasi Pembayaran Ditransfer
                      </button>
                    )}
                    {tipeResolusiAktif === 'potong_tagihan' && fkp.resolution?.diproses_finance && (
                      <div className="text-xs text-green-700">✅ Pembayaran sudah dikonfirmasi ditransfer.</div>
                    )}

                    {(kodeRole === 'admin_ho' || kodeRole === 'superadmin') && (
                      <button className="btn-secondary w-full" onClick={() => setModal('close')}>
                        <CheckCircle2 className="w-4 h-4" /> Tutup FKP (Selesai)
                      </button>
                    )}
                  </>
                )}

                {canEdit && (
                  <>
                    <button onClick={() => submit()} disabled={isSubmitting} className="btn-primary w-full">
                      {isSubmitting
                        ? <><Loader2 className="w-4 h-4 animate-spin" /> Memproses...</>
                        : <><Send className="w-4 h-4" /> Submit FKP</>
                      }
                    </button>
                    <button onClick={() => navigate(`/fkp/${fkp.id}/edit`)} className="btn-secondary w-full">
                      <Edit2 className="w-4 h-4" /> Edit FKP
                    </button>
                  </>
                )}

                {['rejected', 'closed'].includes(fkp.status) && (
                  <p className="text-sm text-gray-400 text-center py-2">
                    FKP sudah {fkp.status === 'closed' ? 'ditutup' : 'ditolak'}.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ── QR Code Card ─────────────────────────────────────────────── */}
          <QrTriggerCard
            fkpId={fkp.id}
            nomorFkp={fkp.nomor_fkp}
            onClick={() => setModal('qr_code')}
          />

          {/* Riwayat Status */}
          <div className="card">
            <div className="card-header">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <Clock className="w-4 h-4 text-brand-500" /> Riwayat Status
              </h2>
            </div>
            <div className="card-body">
              {fkp.status_logs.length === 0
                ? <p className="text-sm text-gray-400 text-center py-4">Belum ada riwayat.</p>
                : <ol className="relative border-l border-gray-100 space-y-4 ml-2">
                  {[...fkp.status_logs].reverse().map((log) => (
                    <li key={log.id} className="pl-4">
                      <div className="absolute -left-1.5 w-3 h-3 rounded-full border-2 border-white bg-brand-400" />
                      <p className="text-xs text-gray-400">{formatDateTime(log.changed_at)}</p>
                      <p className="text-sm font-medium text-gray-800 mt-0.5">
                        {log.status_lama && (
                          <span className="text-gray-400">
                            {FKP_STATUS_LABEL[log.status_lama as FkpStatusKey] ?? log.status_lama} →{' '}
                          </span>
                        )}
                        <span className="text-brand-600">
                          {FKP_STATUS_LABEL[log.status_baru as FkpStatusKey] ?? log.status_baru}
                        </span>
                      </p>
                      {log.catatan && (
                        <p className="text-xs text-gray-500 mt-1 bg-gray-50 rounded-sm px-2 py-1">{log.catatan}</p>
                      )}
                    </li>
                  ))}
                </ol>
              }
            </div>
          </div>
        </div>
      </div>

      {/* ══════════════ MODALS ══════════════════════════════════════════════ */}

      {/* QR Code Modal — ukuran besar, konten download & copy */}
      <Modal
        isOpen={modal === 'qr_code'}
        onClose={closeModal}
        title="QR Code Tracking FKP"
        size="sm"
      >
        <QrCodeModalContent fkpId={fkp.id} nomorFkp={fkp.nomor_fkp} />
      </Modal>

      {/* APSM review */}
      <Modal isOpen={modal === 'apsm_review'} onClose={closeModal} title="Review APSM" size="lg">
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          <p className="text-sm text-gray-600">Isi rekomendasi per item (opsional), lalu teruskan ke Admin HO.</p>
          {fkp?.items.map((item) => (
            <FkpItemReviewForm
              key={item.id} prefix="apsm" item={item} products={products}
              value={apsmReviews[item.id] ?? APSM_REVIEW_BLANK}
              onChange={(v) => setApsmReviews((p) => ({ ...p, [item.id]: v }))}
            />
          ))}
          <Textarea label="Catatan Tambahan APSM (opsional)" value={catatan}
            onChange={(e) => setCatatan(e.target.value)} rows={3} />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
            isLoading={isConfirming} confirmLabel="Teruskan ke Admin HO" />
        </div>
      </Modal>

      {/* Admin HO review */}
      <Modal isOpen={modal === 'admin_ho_review'} onClose={closeModal} title="Review Admin HO" size="lg">
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          <p className="text-sm text-gray-600">Isi rekomendasi Admin HO per item, lalu teruskan ke RSM (Investigasi).</p>
          {fkp?.items.map((item) => (
            <FkpItemReviewForm
              key={item.id} prefix="admin_ho" item={item} products={products}
              value={adminHoReviews[item.id] ?? ADMIN_HO_REVIEW_BLANK}
              onChange={(v) => setAdminHoReviews((p) => ({ ...p, [item.id]: v }))}
            />
          ))}
          <Textarea label="Catatan Tambahan Admin HO (opsional)" value={catatan}
            onChange={(e) => setCatatan(e.target.value)} rows={3} />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
            isLoading={isConfirming} confirmLabel="Teruskan ke RSM (Investigasi)" />
        </div>
      </Modal>

      {/* QC investigasi */}
      <Modal isOpen={modal === 'qc_investigasi'} onClose={closeModal} title="Selesaikan Investigasi QC" size="md">
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          {samplesBelumSelesai.length > 0 && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700 space-y-1">
              <p className="font-semibold">⚠️ Masih ada {samplesBelumSelesai.length} sample yang belum selesai diperiksa:</p>
              <ul className="list-disc list-inside">
                {samplesBelumSelesai.map((s) => (
                  <li key={s.id}>
                    {fkp?.items.find((it) => it.id === s.fkp_item_id)?.nama_produk_custom ?? 'Produk'} — {SAMPLE_STATUS_LABEL[s.status]}
                  </li>
                ))}
              </ul>
              <p>Selesaikan pemeriksaan (status: examined) atau batalkan sample tersebut di kartu "Sample Shipment" sebelum investigasi bisa ditutup.</p>
            </div>
          )}
          <Select label="Sumber Ketidaksesuaian" required value={sumber}
            onChange={(e) => setSumber(e.target.value as 'internal' | 'pelanggan')}>
            <option value="internal">Internal — cacat dari produksi (keluhan valid)</option>
            <option value="pelanggan">External/Pelanggan — bukan cacat produksi</option>
          </Select>
          <div className="space-y-3">
            <p className="text-sm font-medium text-gray-700">Hasil per Item</p>
            {fkp?.items.map((item) => {
              const r = qcResults[item.id] ?? { status_item: 'diterima', catatan_qc: '', alasan_penolakan: '' }
              return (
                <div key={item.id} className="p-3 rounded-xl bg-gray-50 border border-gray-100 space-y-2">
                  <p className="text-sm font-semibold text-gray-800">{item.nama_produk_custom ?? 'Produk'}</p>
                  <Select label="Status Item" value={r.status_item}
                    onChange={(e) => setQcResults((p) => ({ ...p, [item.id]: { ...r, status_item: e.target.value } }))}>
                    <option value="diterima">✅ Diterima</option>
                    <option value="ditolak">❌ Ditolak</option>
                  </Select>
                  {r.status_item === 'ditolak' && (
                    <Input label="Alasan Penolakan (wajib)" value={r.alasan_penolakan}
                      onChange={(e) => setQcResults((p) => ({ ...p, [item.id]: { ...r, alasan_penolakan: e.target.value } }))} />
                  )}
                </div>
              )
            })}
          </div>
          <Textarea label="Catatan QC (opsional)" value={catatan}
            onChange={(e) => setCatatan(e.target.value)} rows={3} />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
            isLoading={isConfirming} disabled={samplesBelumSelesai.length > 0}
            confirmLabel="Simpan Hasil Investigasi" />
        </div>
      </Modal>

      {/* Buat / Edit Resolusi */}
      <Modal isOpen={modal === 'buat_resolusi'} onClose={closeModal}
        title={
          fkp.status === 'accepted' ? 'Lengkapi Qty Disetujui'
            : hasResolusi ? 'Edit Resolusi' : 'Buat Resolusi'
        } size="md">
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          {fkp.status === 'accepted' && tipeResolusiAktif === 'tukar_barang' ? (
            // ── Fase 2: qty_disetujui saja — tipe_resolusi/metode sudah terkunci ──
            <>
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
                📦 FKP sudah disetujui Direktur. Isi qty yang disetujui untuk
                diganti per item sebelum Surat Jalan dibuat.
              </div>
              {fkp.items.filter((item) => item.status_item === 'diterima').map((item) => (
                <div key={item.id} className="p-3 rounded-xl bg-gray-50 border border-gray-100">
                  <p className="text-xs font-semibold text-gray-700 mb-1.5">
                    {item.nama_produk_custom ?? 'Produk'}{' '}
                    <span className="text-gray-400 font-normal">(Qty keluhan: {item.qty})</span>
                  </p>
                  <Input label="Qty Disetujui" type="number" required placeholder={String(item.qty)}
                    value={itemQtyDisetujui[item.id] ?? ''}
                    onChange={(e) => setItemQtyDisetujui((p) => ({ ...p, [item.id]: e.target.value }))} />
                </div>
              ))}
            </>
          ) : (
            // ── Fase 1: tipe_resolusi + metode_penanganan_fisik (perilaku lama, tidak berubah) ──
            <>
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
                💡 Isi <strong>metode penanganan fisik</strong> dan <strong>tipe resolusi</strong>. Keduanya bisa berbeda.
              </div>
              <Select label="Metode Penanganan Fisik Barang" required
                value={resolusiForm.metode_penanganan_fisik}
                onChange={(e) => setResolusiForm(p => ({ ...p, metode_penanganan_fisik: e.target.value as MetodePenangananFisik }))}>
                <option value="dimusnahkan">Dimusnahkan</option>
                <option value="dijual_pakan_ternak">Dijual sebagai pakan ternak</option>
                <option value="dikirim_ke_ho">Dikirim kembali ke Head Office</option>
                <option value="disimpan_distributor">Disimpan sementara oleh distributor</option>
                <option value="di_repack_oleh_pihak_internal">Di Repack oleh pihak internal</option>
              </Select>
              {resolusiForm.metode_penanganan_fisik === 'dimusnahkan' && (
                <>
                  <Input label="Lokasi Pemusnahan" required placeholder="Gudang distributor / TPA / Insinerator..."
                    value={resolusiForm.lokasi_pemusnahan}
                    onChange={(e) => setResolusiForm(p => ({ ...p, lokasi_pemusnahan: e.target.value }))} />
                  <Input label="Tanggal Pemusnahan" type="date"
                    value={resolusiForm.tanggal_pemusnahan}
                    onChange={(e) => setResolusiForm(p => ({ ...p, tanggal_pemusnahan: e.target.value }))} />
                </>
              )}
              <Textarea
                label="Detail Penanganan"
                placeholder="Contoh: dibakar di lokasi distributor..."
                value={resolusiForm.detail_penanganan}
                onChange={(e) => setResolusiForm(p => ({ ...p, detail_penanganan: e.target.value }))}
              />
              <Select label="Tipe Kompensasi / Resolusi" required value={tipeResolusi}
                onChange={(e) => setTipeResolusi(e.target.value)}>
                <option value="tukar_barang">Tukar Barang — kirim barang pengganti</option>
                <option value="potong_tagihan">Potong Tagihan / Cashback</option>
                <option value="tidak_ada_kompensasi">Tanpa Kompensasi</option>
              </Select>
              {tipeResolusi === 'potong_tagihan' && (
                <>
                  <Input label="Persentase Kompensasi Disetujui (%)" required type="number"
                    placeholder="Contoh: 80 (artinya 80% dari nilai nota)"
                    value={resolusiForm.persentase_kompensasi_disetujui}
                    onChange={(e) => setResolusiForm(p => ({ ...p, persentase_kompensasi_disetujui: e.target.value }))} />
                  <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-500">
                    📋 Detail rekening dan nilai nota penjualan diisi setelah Direktur menyetujui.
                  </div>
                </>
              )}
              {tipeResolusi === 'tukar_barang' && (
                <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-500">
                  📋 Qty disetujui per item diisi lewat modal ini juga setelah Direktur menyetujui.
                </div>
              )}
              <Textarea label="Keterangan Tambahan" value={resolusiForm.keterangan}
                onChange={(e) => setResolusiForm(p => ({ ...p, keterangan: e.target.value }))} rows={3} />
            </>
          )}
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm} isLoading={isConfirming}
            confirmLabel={
              fkp.status === 'accepted' ? 'Simpan Qty Disetujui'
                : hasResolusi ? 'Update Resolusi' : 'Simpan Resolusi'
            } />
        </div>
      </Modal>

      {/* Request resolusi approval */}
      <Modal isOpen={modal === 'request_resolusi_approval'} onClose={closeModal} title="Ajukan Resolusi ke RSM" size="sm">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Resolusi <strong>{fkp.resolution?.tipe_resolusi.replace(/_/g, ' ')}</strong> akan diajukan ke RSM.
          </p>
          <Textarea label="Catatan (opsional)" value={catatan}
            onChange={(e) => setCatatan(e.target.value)} rows={3} />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
            isLoading={isConfirming} confirmLabel="Ajukan ke RSM" />
        </div>
      </Modal>

      {/* Proses pengiriman */}
      {/* ── tukar_barang: qty disetujui + buat Surat Jalan pertama ──────────── */}
      <Modal isOpen={modal === 'lengkapi_qty_sj'} onClose={closeModal} title="Buat Surat Jalan (Barang Pengganti)" size="lg">
        <div className="space-y-4">
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
            📦 Mengirim Surat Jalan ini akan otomatis memindahkan FKP ke status "Diproses" — tidak perlu langkah konfirmasi terpisah.
          </div>
          {fkp.items.filter((item) => item.status_item === 'diterima').length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">Qty Disetujui / Dikirim per Item</p>
              {fkp.items.filter((item) => item.status_item === 'diterima').map((item) => (
                <div key={item.id} className="p-3 rounded-xl bg-gray-50 border border-gray-100">
                  <p className="text-xs font-semibold text-gray-700 mb-1.5">
                    {item.nama_produk_custom ?? 'Produk'}{' '}
                    <span className="text-gray-400 font-normal">(Qty keluhan: {item.qty})</span>
                  </p>
                  <Input
                    label="Qty Dikirim"
                    type="number"
                    required
                    placeholder={String(item.qty)}
                    value={itemQtyDisetujui[item.id] ?? ''}
                    onChange={(e) => setItemQtyDisetujui((p) => ({ ...p, [item.id]: e.target.value }))}
                    // [BARU] Warehouse tidak boleh ubah qty yang sudah disetujui
                    // Admin HO — field ini di-lock, hanya admin_ho/superadmin yang
                    disabled={kodeRole === 'warehouse'}
                  />
                  {kodeRole === 'warehouse' && (
                    <p className="text-[11px] text-gray-400 mt-1">
                      Qty ditentukan oleh Admin HO, tidak bisa diubah dari sini.
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <Input label="Nomor Surat Jalan" required value={sjForm.nomor_surat_jalan}
              onChange={(e) => setSjForm((p) => ({ ...p, nomor_surat_jalan: e.target.value }))} />
            <Input label="Tanggal Surat Jalan" type="date" required value={sjForm.tanggal_surat_jalan}
              onChange={(e) => setSjForm((p) => ({ ...p, tanggal_surat_jalan: e.target.value }))} />
          </div>
          <Input label="Nama Penerima" required value={sjForm.nama_penerima}
            onChange={(e) => setSjForm((p) => ({ ...p, nama_penerima: e.target.value }))} />
          <Textarea label="Alamat Penerima" required rows={2} value={sjForm.alamat_penerima}
            onChange={(e) => setSjForm((p) => ({ ...p, alamat_penerima: e.target.value }))} />
          <Input label="Telepon Penerima" required value={sjForm.telepon_penerima}
            onChange={(e) => setSjForm((p) => ({ ...p, telepon_penerima: e.target.value }))} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Ekspedisi" required value={sjForm.ekspedisi}
              onChange={(e) => setSjForm((p) => ({ ...p, ekspedisi: e.target.value }))} />
            <Input label="No. Resi" value={sjForm.nomor_resi}
              onChange={(e) => setSjForm((p) => ({ ...p, nomor_resi: e.target.value }))} />
          </div>
          <Textarea label="Catatan (opsional)" rows={2} value={sjForm.catatan}
            onChange={(e) => setSjForm((p) => ({ ...p, catatan: e.target.value }))} />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
            isLoading={isConfirming} confirmLabel="Buat Surat Jalan" />
        </div>
      </Modal>

      {/* ── potong_tagihan: detail rekening (Fase 2, tidak trigger status) ──── */}
      <Modal isOpen={modal === 'lengkapi_rekening'} onClose={closeModal} title="Lengkapi Detail Rekening" size="md">
        <div className="space-y-4">
          {fkp.resolution?.persentase_kompensasi_disetujui != null && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
              📊 Persentase kompensasi disetujui: <strong>{fkp.resolution.persentase_kompensasi_disetujui}%</strong>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <Input label="Nama Bank" required value={rekeningForm.nama_bank}
              onChange={(e) => setRekeningForm((p) => ({ ...p, nama_bank: e.target.value }))} />
            <Input label="No. Rekening" required value={rekeningForm.nomor_rekening}
              onChange={(e) => setRekeningForm((p) => ({ ...p, nomor_rekening: e.target.value }))} />
          </div>
          <Input label="Atas Nama" required value={rekeningForm.atas_nama}
            onChange={(e) => setRekeningForm((p) => ({ ...p, atas_nama: e.target.value }))} />
          <Input label="Nomor Nota Retur (opsional)" value={rekeningForm.nomor_nota_retur}
            onChange={(e) => setRekeningForm((p) => ({ ...p, nomor_nota_retur: e.target.value }))} />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
            isLoading={isConfirming} confirmLabel="Simpan Rekening" />
        </div>
      </Modal>

      {/* ── potong_tagihan: terbitkan invoice (trigger accepted → in_process) ── */}
      <Modal isOpen={modal === 'terbitkan_invoice'} onClose={closeModal} title="Terbitkan Invoice Potong Tagihan" size="md">
        <div className="space-y-4">
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
            📄 Menerbitkan invoice akan otomatis memindahkan FKP ke status "Diproses" dan menghasilkan PDF invoice.
          </div>
          <Input label="Nomor Invoice" required value={invoiceForm.nomor_invoice}
            onChange={(e) => setInvoiceForm((p) => ({ ...p, nomor_invoice: e.target.value }))} />
          <Input label="Nilai Nota Penjualan (Rp)" type="number" required
            value={invoiceForm.nilai_nota_penjualan}
            onChange={(e) => setInvoiceForm((p) => ({ ...p, nilai_nota_penjualan: e.target.value }))} />
          {invoiceForm.nilai_nota_penjualan && fkp.resolution?.persentase_kompensasi_disetujui != null && (
            <div className="p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-700">
              💡 Nilai cashback: <strong>
                {formatRupiah((Number(invoiceForm.nilai_nota_penjualan) * fkp.resolution.persentase_kompensasi_disetujui) / 100)}
              </strong> ({fkp.resolution.persentase_kompensasi_disetujui}% × nilai nota)
            </div>
          )}
          <Textarea label="Catatan (opsional)" rows={2} value={invoiceForm.catatan}
            onChange={(e) => setInvoiceForm((p) => ({ ...p, catatan: e.target.value }))} />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
            isLoading={isConfirming} confirmLabel="Terbitkan Invoice" />
        </div>
      </Modal>

      {/* ── potong_tagihan: konfirmasi pembayaran sudah ditransfer ──────────── */}
      <Modal isOpen={modal === 'proses_finance'} onClose={closeModal} title="Konfirmasi Pembayaran" size="md">
        <div className="space-y-4">
          <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-600">
            Nilai cashback: <strong>{fkp.resolution?.nilai_cashback != null ? formatRupiah(fkp.resolution.nilai_cashback) : '-'}</strong>
          </div>
          <Textarea label="Catatan (opsional)" rows={2} value={catatan}
            onChange={(e) => setCatatan(e.target.value)} />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
            isLoading={isConfirming} confirmLabel="Konfirmasi Sudah Ditransfer" />
        </div>
      </Modal>

      {/* ── tidak_ada_kompensasi (± dimusnahkan): trigger accepted → in_process ── */}
      <Modal isOpen={modal === 'confirm_resolusi'} onClose={closeModal} title="Konfirmasi Resolusi" size="md">
        <div className="space-y-4">
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
            🚫 Resolusi tanpa kompensasi finansial. Mengonfirmasi akan memindahkan FKP ke status "Diproses".
          </div>
          <Textarea label="Catatan / Alasan" required rows={3} value={catatan}
            onChange={(e) => setCatatan(e.target.value)}
            placeholder="Wajib diisi — alasan tidak ada kompensasi" />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
            isLoading={isConfirming} confirmLabel="Konfirmasi Resolusi" />
        </div>
      </Modal>

      {/* ── Surat Jalan existing: issued → shipped ──────────────────────────── */}
      <Modal isOpen={modal === 'sj_ship'} onClose={closeModal} title="Tandai Surat Jalan Dikirim" size="md">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Ekspedisi (opsional)" value={shipForm.ekspedisi}
              onChange={(e) => setShipForm((p) => ({ ...p, ekspedisi: e.target.value }))} />
            <Input label="No. Resi (opsional)" value={shipForm.nomor_resi}
              onChange={(e) => setShipForm((p) => ({ ...p, nomor_resi: e.target.value }))} />
          </div>
          <Input label="Tanggal Kirim (opsional)" type="date" value={shipForm.tanggal_kirim}
            onChange={(e) => setShipForm((p) => ({ ...p, tanggal_kirim: e.target.value }))} />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
            isLoading={isConfirming} confirmLabel="Tandai Dikirim" />
        </div>
      </Modal>

      {/* Modal catatan opsional */}
      {(['rsm_investigasi_ok', 'rsm_resolusi_ok', 'direktur_ok', 'close'] as ModalTipe[]).includes(modal!) && (
        <Modal isOpen={!!modal} onClose={closeModal} title={MODAL_TITLES[modal!]!} size="sm">
          <div className="space-y-4">
            {modal === 'close' && closeWarnings.length > 0 && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700 space-y-1">
                <p className="font-semibold">⚠️ Perhatian sebelum menutup FKP:</p>
                <ul className="list-disc list-inside">
                  {closeWarnings.map((w) => <li key={w}>{w}</li>)}
                </ul>
                <p>FKP tetap bisa ditutup — ini hanya pengingat, bukan larangan.</p>
              </div>
            )}
            <Textarea label="Catatan (opsional)" value={catatan}
              onChange={(e) => setCatatan(e.target.value)} rows={4} />
            <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
              isLoading={isConfirming} confirmLabel="Konfirmasi" />
          </div>
        </Modal>
      )}

      {/* Modal catatan wajib */}
      {(['revision', 'reject', 'rsm_investigasi_tolak', 'rsm_resolusi_tolak', 'direktur_tolak'] as ModalTipe[]).includes(modal!) && (
        <Modal isOpen={!!modal} onClose={closeModal} title={MODAL_TITLES[modal!]!} size="sm">
          <div className="space-y-4">
            <Textarea label="Alasan (wajib)" required placeholder="Jelaskan alasan..."
              value={catatan} onChange={(e) => setCatatan(e.target.value)} rows={4} />
            <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
              isLoading={isConfirming} confirmLabel="Konfirmasi" confirmClassName="btn-danger" />
          </div>
        </Modal>
      )}
    </div>
  )
}

// ─── Modal Titles ─────────────────────────────────────────────────────────────
const MODAL_TITLES: Partial<Record<ModalTipe, string>> = {
  rsm_investigasi_ok: 'Setujui Investigasi',
  rsm_investigasi_tolak: 'Tolak FKP',
  rsm_resolusi_ok: 'Setujui Resolusi → Ke Direktur',
  rsm_resolusi_tolak: 'Tolak FKP',
  direktur_ok: 'Setujui FKP',
  direktur_tolak: 'Tolak FKP',
  revision: 'Minta Revisi / Kembalikan',
  reject: 'Tolak FKP',
  close: 'Tutup FKP',
}

// ─── ModalFooter ──────────────────────────────────────────────────────────────
function ModalFooter({
  onCancel, onConfirm, isLoading, disabled = false,
  confirmLabel = 'Konfirmasi',
  confirmClassName = 'btn-primary',
}: {
  onCancel: () => void
  onConfirm: () => void
  isLoading: boolean
  disabled?: boolean
  confirmLabel?: string
  confirmClassName?: string
}) {
  return (
    <div className="flex gap-2 justify-end pt-2">
      <button onClick={onCancel} className="btn-secondary" disabled={isLoading}>Batal</button>
      <button onClick={onConfirm} className={confirmClassName} disabled={isLoading || disabled}>
        {isLoading
          ? <><Loader2 className="w-4 h-4 animate-spin" /> Memproses...</>
          : confirmLabel
        }
      </button>
    </div>
  )
}