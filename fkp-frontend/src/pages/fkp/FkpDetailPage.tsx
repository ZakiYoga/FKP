/* eslint-disable @typescript-eslint/no-explicit-any */
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, FileText, Clock, CheckCircle2, Loader2, Send,
  AlertTriangle, ShieldCheck, XCircle, Edit2, Plus, Package,
  QrCode, Download, Copy, Check, ExternalLink,
} from 'lucide-react'
import { useState, useRef, useCallback } from 'react'
import { QRCodeCanvas } from 'qrcode.react'
import { useFkpDetail, useSubmitFkp, useProducts, useAddFkpItem, useDeleteFkpItem } from '@/hooks/useFkp'
import { StatusBadge, PriorittasBadge } from '@/components/ui/Badge'
import { PageLoader } from '@/components/ui/Spinner'
import { Modal } from '@/components/ui/Modal'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { FkpItemFormModal, type FileWithMeta } from '@/components/fkp/FkpItemFormModal'
import { FkpItemReviewForm, type ApsmReviewState, type AdminHoReviewState, APSM_REVIEW_BLANK, ADMIN_HO_REVIEW_BLANK } from '@/components/fkp/FkpItemReviewForm'
import { formatDateTime, formatRupiah } from '@/lib/utils'
import { useKodeRole } from '@/store/authStore'
import { FKP_STATUS_LABEL, METODE_PENANGANAN_LABEL, TIPE_RESOLUSI_LABEL } from '@/types'
import type { FkpStatusKey, FkpItemCreatePayload, TipeResolusi, MetodePenangananFisik, RekomendasiPenanganan, RekomendasiKompensasi } from '@/types'
import { fkpApi } from '@/api/fkp'
import { useQueryClient } from '@tanstack/react-query'
import { fkpKeys } from '@/hooks/useFkp'
import toast from 'react-hot-toast'
import InfoRow from '@/components/fkp/InfoRow'
import CatatanItem from '@/components/fkp/FkpItemCatatan'
import FkpItemCard from '@/components/fkp/FkpItemCard'

// ── Tipe modal ────────────────────────────────────────────────────────────────

type ModalTipe =
  | 'apsm_review' | 'admin_ho_review'
  | 'rsm_investigasi_ok' | 'rsm_investigasi_tolak'
  | 'qc_investigasi'
  | 'buat_resolusi'
  | 'request_resolusi_approval'
  | 'rsm_resolusi_ok' | 'rsm_resolusi_tolak'
  | 'direktur_ok' | 'direktur_tolak'
  | 'proses_pengiriman'
  | 'revision' | 'reject' | 'close'
  | 'add_item'
  | 'qr_code'          // ← TAMBAH

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
    const labelH  = 44
    const off     = document.createElement('canvas')
    off.width  = canvas.width  + padding * 2
    off.height = canvas.height + padding * 2 + labelH
    const ctx  = off.getContext('2d')!

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

    const link     = document.createElement('a')
    link.download  = `QR-FKP-${nomorFkp.replace(/\//g, '-')}.png`
    link.href      = off.toDataURL('image/png')
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
  const qc = useQueryClient()

  const { data: fkp, isLoading, isError } = useFkpDetail(id)
  const { data: products = [] } = useProducts()

  const [modal, setModal] = useState<ModalTipe | null>(null)
  const [catatan, setCatatan] = useState('')
  const [isConfirming, setIsConfirming] = useState(false)
  const [isSavingItem, setIsSavingItem] = useState(false)
  const [itemResetKey, setItemResetKey] = useState(0)

  const [apsmReviews, setApsmReviews]       = useState<Record<string, ApsmReviewState>>({})
  const [adminHoReviews, setAdminHoReviews] = useState<Record<string, AdminHoReviewState>>({})
  const [qcResults, setQcResults]           = useState<Record<string, QcItemResult>>({})
  const [sumber, setSumber]                 = useState<'internal' | 'pelanggan'>('internal')

  const [tipeResolusi, setTipeResolusi] = useState('tukar_barang')
  const [resolusiForm, setResolusiForm] = useState({
    nilai_cashback: '', nama_bank: '', nomor_rekening: '',
    atas_nama: '', nomor_nota_retur: '', keterangan: '',
    tanggal_pemusnahan: '', lokasi_pemusnahan: '',
    metode_penanganan_fisik: 'dimusnahkan' as MetodePenangananFisik,
    detail_penanganan: '',
    persentase_kompensasi_disetujui: '',
  })

  const [detailForm, setDetailForm] = useState({
    nomor_do: '', ekspedisi: '', resi_pengiriman: '',
    nomor_surat_jalan: '', nilai_nota_penjualan: '',
    nama_bank: '', nomor_rekening: '', atas_nama: '',
    nomor_nota_retur: '', keterangan: '',
  })

  const [itemQtyDisetujui, setItemQtyDisetujui] = useState<Record<string, string>>({})

  const { mutate: submit, isPending: isSubmitting } = useSubmitFkp(id ?? '')
  const { mutateAsync: addItem }  = useAddFkpItem(id ?? '')
  const { mutate: deleteItem }    = useDeleteFkpItem(id ?? '')

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
    setModal('buat_resolusi')
  }

  const openDetailModal = () => {
    const r = fkp?.resolution
    setDetailForm({
      nomor_do: r?.nomor_do ?? '',
      ekspedisi: r?.ekspedisi ?? '',
      resi_pengiriman: r?.resi_pengiriman ?? '',
      nomor_surat_jalan: fkp?.nomor_surat_jalan ?? '',
      nilai_nota_penjualan: r?.nilai_nota_penjualan ? String(r.nilai_nota_penjualan) : '',
      nama_bank: r?.nama_bank ?? '',
      nomor_rekening: r?.nomor_rekening ?? '',
      atas_nama: r?.atas_nama ?? '',
      nomor_nota_retur: r?.nomor_nota_retur ?? '',
      keterangan: '',
    })
    const initialQty: Record<string, string> = {}
    fkp?.items
      .filter((item) => item.status_item === 'diterima')
      .forEach((item) => {
        initialQty[item.id] = item.qty_disetujui ? String(item.qty_disetujui) : ''
      })
    setItemQtyDisetujui(initialQty)
    setModal('proses_pengiriman')
  }

  const handleAddItem = async (payload: FkpItemCreatePayload, files: FileWithMeta[]) => {
    setIsSavingItem(true)
    try {
      const newItem = await addItem(payload)
      if (files.length > 0) {
        const { default: api } = await import('@/lib/axios')
        for (const f of files) {
          const form = new FormData()
          form.append('file', f.file)
          form.append('tipe_dokumen', f.tipe_dokumen)
          if (f.keterangan) form.append('keterangan', f.keterangan)
          await api.post(`/fkp/${id}/attachments`, form, {
            headers: { 'Content-Type': 'multipart/form-data' },
            params: { fkp_item_id: newItem.id },
          })
        }
        qc.invalidateQueries({ queryKey: fkpKeys.detail(id!) })
      }
      setModal(null)
    } finally {
      setIsSavingItem(false)
    }
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

      case 'buat_resolusi':
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

      case 'proses_pengiriman':
        return runAction(() => fkpApi.updateDetailResolusi(id, {
          nomor_do: detailForm.nomor_do || null,
          ekspedisi: detailForm.ekspedisi || null,
          resi_pengiriman: detailForm.resi_pengiriman || null,
          nomor_surat_jalan: detailForm.nomor_surat_jalan || null,
          item_qty_disetujui: fkp?.resolution?.tipe_resolusi === 'tukar_barang'
            ? fkp.items.filter((item) => item.status_item === 'diterima')
                .map((item) => ({
                  item_id: item.id,
                  qty_disetujui: Number(itemQtyDisetujui[item.id] ?? item.qty),
                }))
            : null,
          nilai_nota_penjualan: detailForm.nilai_nota_penjualan ? Number(detailForm.nilai_nota_penjualan) : null,
          nama_bank: detailForm.nama_bank || null,
          nomor_rekening: detailForm.nomor_rekening || null,
          atas_nama: detailForm.atas_nama || null,
          nomor_nota_retur: detailForm.nomor_nota_retur || null,
          keterangan: detailForm.keterangan || null,
        }))

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

  const canEdit            = fkp.status === 'draft' || fkp.status === 'need_revision'
  const hasResolusi        = !!fkp.resolution
  const canCreateResolusi  = kodeRole === 'admin_ho' && fkp.status === 'investigated' && !fkp.resolution
  const canEditResolusi    = kodeRole === 'admin_ho' && ['investigated', 'rsm_approval_resolusi'].includes(fkp.status) && !!fkp.resolution
  const resolusiTerkunci   = !!fkp.resolution && ['direktur_approval', 'accepted', 'in_process', 'closed', 'rejected'].includes(fkp.status)

  const hasAnyAction =
    canEdit ||
    (fkp.status === 'submitted' && kodeRole === 'apsm') ||
    (fkp.status === 'apsm_reviewed' && kodeRole === 'admin_ho') ||
    (fkp.status === 'rsm_approval_investigasi' && kodeRole === 'rsm') ||
    (fkp.status === 'in_investigation' && kodeRole === 'qc') ||
    (fkp.status === 'investigated' && kodeRole === 'admin_ho') ||
    (fkp.status === 'rsm_approval_resolusi' && kodeRole === 'rsm') ||
    (fkp.status === 'direktur_approval' && kodeRole === 'direktur') ||
    (fkp.status === 'accepted' && kodeRole === 'admin_ho') ||
    (fkp.status === 'in_process' && kodeRole === 'admin_ho')

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
          <PriorittasBadge prioritas={fkp.prioritas} />
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
                {fkp.nomor_surat_jalan && <InfoRow label="No. Surat Jalan" value={fkp.nomor_surat_jalan} mono />}
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
                {canEdit && (
                  <button onClick={() => { setItemResetKey(k => k + 1); setModal('add_item') }}
                    className="btn-secondary btn-sm flex items-center gap-1.5">
                    <Plus className="w-3.5 h-3.5" /> Tambah Item
                  </button>
                )}
              </div>
            </div>
            <div className="card-body space-y-4">
              {fkp.items.length === 0
                ? <p className="text-sm text-gray-400 text-center py-4">Belum ada item.</p>
                : fkp.items.map((item, idx) => (
                  <FkpItemCard
                    key={item.id} item={item} idx={idx} products={products}
                    canDelete={canEdit && fkp.items.length > 1}
                    onDelete={() => deleteItem(item.id)}
                    attachments={fkp.attachments.filter((a) => a.fkp_item_id === item.id)}
                  />
                ))}
            </div>
          </div>

          {/* Catatan proses */}
          {(fkp.catatan_sc_spv || fkp.catatan_apsm || fkp.catatan_admin ||
            fkp.catatan_qc || fkp.catatan_rsm_investigasi ||
            fkp.catatan_rsm_resolusi || fkp.catatan_direktur) && (
            <div className="card">
              <div className="card-header"><h2 className="font-semibold text-gray-900">Catatan Proses</h2></div>
              <div className="card-body space-y-3">
                <CatatanItem label="SC / SPV"         value={fkp.catatan_sc_spv} />
                <CatatanItem label="APSM"             value={fkp.catatan_apsm} />
                <CatatanItem label="Admin HO"         value={fkp.catatan_admin} />
                <CatatanItem label="QC"               value={fkp.catatan_qc} />
                <CatatanItem label="RSM (Investigasi)"value={fkp.catatan_rsm_investigasi} />
                <CatatanItem label="RSM (Resolusi)"   value={fkp.catatan_rsm_resolusi} />
                <CatatanItem label="Direktur"         value={fkp.catatan_direktur} />
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
              </div>
            </div>
          )}

          {/* Foto umum */}
          {fkp.attachments.filter((a) => !a.fkp_item_id).length > 0 && (
            <div className="card">
              <div className="card-header">
                <h2 className="font-semibold text-gray-900">
                  Foto Umum ({fkp.attachments.filter((a) => !a.fkp_item_id).length})
                </h2>
              </div>
              <div className="card-body">
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                  {fkp.attachments.filter((a) => !a.fkp_item_id).map((att) => (
                    <a key={att.id} href={att.url} target="_blank" rel="noreferrer" className="aspect-square block">
                      <img src={att.url} alt={att.nama_file}
                        className="w-full h-full object-cover rounded-lg border border-gray-200 hover:opacity-90 transition-opacity" />
                    </a>
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

                {fkp.status === 'accepted' && kodeRole === 'admin_ho' && (
                  <>
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
                      ✅ FKP disetujui Direktur. Lengkapi detail eksekusi untuk memulai proses.
                    </div>
                    <button className="btn-primary w-full" onClick={openDetailModal}>
                      <Package className="w-4 h-4" />
                      {TIPE_RESOLUSI_LABEL[fkp.resolution?.tipe_resolusi as TipeResolusi] ?? 'Mulai Proses'}
                    </button>
                  </>
                )}

                {fkp.status === 'in_process' && kodeRole === 'admin_ho' && (
                  <button className="btn-secondary w-full" onClick={() => setModal('close')}>
                    <CheckCircle2 className="w-4 h-4" /> Tutup FKP (Selesai)
                  </button>
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

      {/* Tambah Item */}
      <FkpItemFormModal
        isOpen={modal === 'add_item'}
        onClose={closeModal}
        products={products}
        resetKey={itemResetKey}
        onSave={handleAddItem}
        isSaving={isSavingItem}
      />

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
          <Select label="Sumber Ketidaksesuaian" required value={sumber}
            onChange={(e) => setSumber(e.target.value as 'internal' | 'pelanggan')}>
            <option value="internal">✅ Internal — cacat dari produksi (keluhan valid)</option>
            <option value="pelanggan">❌ Pelanggan — bukan cacat produksi</option>
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
                    <option value="pending">⏳ Pending</option>
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
            isLoading={isConfirming} confirmLabel="Simpan Hasil Investigasi" />
        </div>
      </Modal>

      {/* Buat / Edit Resolusi */}
      <Modal isOpen={modal === 'buat_resolusi'} onClose={closeModal}
        title={hasResolusi ? 'Edit Resolusi' : 'Buat Resolusi'} size="md">
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
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
          <Input label="Detail Penanganan (opsional)" placeholder="Contoh: dibakar di lokasi distributor..."
            value={resolusiForm.detail_penanganan}
            onChange={(e) => setResolusiForm(p => ({ ...p, detail_penanganan: e.target.value }))} />
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
              📋 Nomor DO, ekspedisi, resi pengiriman, dan qty disetujui per item diisi setelah Direktur menyetujui.
            </div>
          )}
          <Textarea label="Keterangan Tambahan" value={resolusiForm.keterangan}
            onChange={(e) => setResolusiForm(p => ({ ...p, keterangan: e.target.value }))} rows={3} />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm} isLoading={isConfirming}
            confirmLabel={hasResolusi ? 'Update Resolusi' : 'Simpan Resolusi'} />
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
      <Modal isOpen={modal === 'proses_pengiriman'} onClose={closeModal} title="Isi Detail Eksekusi & Mulai Proses" size="md">
        <div className="space-y-4">
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-700">
            ✅ Direktur telah menyetujui. Lengkapi detail di bawah untuk memulai proses.
          </div>
          <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-600 space-y-1">
            <p><strong>Tipe kompensasi:</strong> {TIPE_RESOLUSI_LABEL[fkp.resolution?.tipe_resolusi as TipeResolusi]}</p>
            <p><strong>Penanganan fisik:</strong> {METODE_PENANGANAN_LABEL[fkp.resolution?.metode_penanganan_fisik as MetodePenangananFisik]}</p>
          </div>
          {fkp.resolution?.tipe_resolusi === 'tukar_barang' && (
            <>
              <Input label="Nomor DO" required value={detailForm.nomor_do}
                onChange={(e) => setDetailForm(p => ({ ...p, nomor_do: e.target.value }))} />
              <div className="grid grid-cols-2 gap-3">
                <Input label="Ekspedisi" value={detailForm.ekspedisi}
                  onChange={(e) => setDetailForm(p => ({ ...p, ekspedisi: e.target.value }))} />
                <Input label="No. Resi" value={detailForm.resi_pengiriman}
                  onChange={(e) => setDetailForm(p => ({ ...p, resi_pengiriman: e.target.value }))} />
              </div>
              <Input label="Nomor Surat Jalan" value={detailForm.nomor_surat_jalan}
                onChange={(e) => setDetailForm(p => ({ ...p, nomor_surat_jalan: e.target.value }))} />
              {fkp.items.filter((item) => item.status_item === 'diterima').length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-700">Qty Disetujui per Item</p>
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
                </div>
              )}
            </>
          )}
          {fkp.resolution?.tipe_resolusi === 'potong_tagihan' && (
            <>
              {fkp.resolution.persentase_kompensasi_disetujui != null && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
                  📊 Persentase kompensasi disetujui: <strong>{fkp.resolution.persentase_kompensasi_disetujui}%</strong>
                </div>
              )}
              <Input label="Nilai Nota Penjualan (Rp)" type="number" required
                value={detailForm.nilai_nota_penjualan}
                onChange={(e) => setDetailForm(p => ({ ...p, nilai_nota_penjualan: e.target.value }))} />
              {detailForm.nilai_nota_penjualan && fkp.resolution.persentase_kompensasi_disetujui != null && (
                <div className="p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-700">
                  💡 Estimasi cashback: <strong>
                    {formatRupiah((Number(detailForm.nilai_nota_penjualan) * fkp.resolution.persentase_kompensasi_disetujui) / 100)}
                  </strong> ({fkp.resolution.persentase_kompensasi_disetujui}% × nilai nota)
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <Input label="Nama Bank" required value={detailForm.nama_bank}
                  onChange={(e) => setDetailForm(p => ({ ...p, nama_bank: e.target.value }))} />
                <Input label="No. Rekening" required value={detailForm.nomor_rekening}
                  onChange={(e) => setDetailForm(p => ({ ...p, nomor_rekening: e.target.value }))} />
              </div>
              <Input label="Atas Nama" required value={detailForm.atas_nama}
                onChange={(e) => setDetailForm(p => ({ ...p, atas_nama: e.target.value }))} />
              <Input label="Nomor Nota Retur" value={detailForm.nomor_nota_retur}
                onChange={(e) => setDetailForm(p => ({ ...p, nomor_nota_retur: e.target.value }))} />
            </>
          )}
          {fkp.resolution?.tipe_resolusi === 'tidak_ada_kompensasi' && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
              🚫 Tidak ada detail finansial. Klik Mulai Proses untuk melanjutkan.
            </div>
          )}
          <Textarea label="Catatan (opsional)" value={detailForm.keterangan}
            onChange={(e) => setDetailForm(p => ({ ...p, keterangan: e.target.value }))} rows={2} />
          <ModalFooter onCancel={closeModal} onConfirm={handleConfirm}
            isLoading={isConfirming} confirmLabel="Mulai Proses" />
        </div>
      </Modal>

      {/* Modal catatan opsional */}
      {(['rsm_investigasi_ok', 'rsm_resolusi_ok', 'direktur_ok', 'close'] as ModalTipe[]).includes(modal!) && (
        <Modal isOpen={!!modal} onClose={closeModal} title={MODAL_TITLES[modal!]!} size="sm">
          <div className="space-y-4">
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
  rsm_investigasi_ok:    'Setujui Investigasi',
  rsm_investigasi_tolak: 'Tolak FKP',
  rsm_resolusi_ok:       'Setujui Resolusi → Ke Direktur',
  rsm_resolusi_tolak:    'Tolak FKP',
  direktur_ok:           'Setujui FKP',
  direktur_tolak:        'Tolak FKP',
  revision:              'Minta Revisi / Kembalikan',
  reject:                'Tolak FKP',
  close:                 'Tutup FKP',
}

// ─── ModalFooter ──────────────────────────────────────────────────────────────
function ModalFooter({
  onCancel, onConfirm, isLoading,
  confirmLabel = 'Konfirmasi',
  confirmClassName = 'btn-primary',
}: {
  onCancel: () => void
  onConfirm: () => void
  isLoading: boolean
  confirmLabel?: string
  confirmClassName?: string
}) {
  return (
    <div className="flex gap-2 justify-end pt-2">
      <button onClick={onCancel} className="btn-secondary" disabled={isLoading}>Batal</button>
      <button onClick={onConfirm} className={confirmClassName} disabled={isLoading}>
        {isLoading
          ? <><Loader2 className="w-4 h-4 animate-spin" /> Memproses...</>
          : confirmLabel
        }
      </button>
    </div>
  )
}