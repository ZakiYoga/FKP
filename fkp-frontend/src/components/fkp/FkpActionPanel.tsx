import { useState } from 'react'
import {
  Send, CheckCircle2, XCircle, RotateCcw, Search,
  Loader2, ClipboardCheck, ThumbsUp, ThumbsDown, Lock,
} from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { useKodeRole } from '@/store/authStore'
import { fkpApi } from '@/api/fkp'
import { useQueryClient } from '@tanstack/react-query'
import { fkpKeys } from '@/hooks/useFkp'
import toast from 'react-hot-toast'
import { getErrorMessage } from '@/lib/utils'
import type { FkpDetail, FkpStatusKey, MetodePenangananFisik } from '@/types'

interface FkpActionPanelProps {
  fkp: FkpDetail
}

type ModalType =
  | 'submit' | 'apsm_review' | 'admin_approve' | 'revision'
  | 'investigate' | 'finish_investigation' | 'rsm_approve'
  | 'direktur_approve' | 'accept' | 'reject' | 'close'
  | 'resolusi' | 'surat_jalan' | null

export function FkpActionPanel({ fkp }: FkpActionPanelProps) {
  const kodeRole = useKodeRole()
  const queryClient = useQueryClient()
  const [modal, setModal] = useState<ModalType>(null)
  const [isPending, setIsPending] = useState(false)

  // Form state
  const [catatan, setCatatan] = useState('')
  const [sumber, setSumber] = useState<'internal' | 'pelanggan'>('internal')
  const [resolusiTipe, setResolusiTipe] = useState('potong_tagihan')
  const [resolusiData, setResolusiData] = useState<Record<string, string>>({})
  const [metodePenanganan, setMetodePenanganan] = useState<MetodePenangananFisik>('dimusnahkan')
  const [detailPenanganan, setDetailPenanganan] = useState('')
  // ← TAMBAH: state persentase_kompensasi_disetujui untuk potong_tagihan
  const [persentaseKompensasi, setPersentaseKompensasi] = useState('')


  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: fkpKeys.detail(fkp.id) })
    queryClient.invalidateQueries({ queryKey: fkpKeys.all })
  }

  const run = async (fn: () => Promise<unknown>, successMsg: string) => {
    setIsPending(true)
    try {
      await fn()
      toast.success(successMsg)
      refresh()
      setModal(null)
      setCatatan('')
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setIsPending(false)
    }
  }

  const handleConfirm = async () => {
    switch (modal) {
      case 'submit':
        return run(() => fkpApi.submit(fkp.id), 'FKP berhasil disubmit!')

      case 'apsm_review':
        return run(
          () => fkpApi.apsmReview(fkp.id, { catatan_apsm: catatan || null }),
          'FKP diteruskan ke Admin HO.',
        )

      case 'admin_approve':
        return run(
          () => fkpApi.adminHoReview(fkp.id, { catatan_admin: catatan || null }),
          'FKP disetujui, diteruskan ke QC.',
        )

      case 'revision':
        if (!catatan.trim()) { toast.error('Catatan revisi wajib diisi.'); return }
        return run(
          () => fkpApi.requestRevision(fkp.id, { catatan }),
          'FKP dikembalikan untuk revisi.',
        )

      case 'investigate':
        return run(
          () => fkpApi.qcInvestigasi(fkp.id, {
            sumber_ketidaksesuaian: sumber,
            catatan: catatan || null,
          }),
          'Investigasi dimulai.',
        )

      case 'finish_investigation':
        return run(
          () => fkpApi.qcInvestigasi(fkp.id, {
            sumber_ketidaksesuaian: sumber,
            catatan: catatan || null,
          }),
          'Hasil investigasi disimpan.',
        )

      case 'rsm_approve':
        return run(
          () => fkpApi.rsmApproveInvestigasi(fkp.id, {
            disetujui: true,
            catatan: catatan || null,
          }),
          'FKP disetujui RSM, diteruskan ke Direktur.',
        )

      case 'direktur_approve':
        return run(
          () => fkpApi.direkturApprove(fkp.id, {
            disetujui: true,
            catatan: catatan || null,
          }),
          'FKP disetujui Direktur.',
        )

      case 'accept':
        return run(
          () => fkpApi.direkturApprove(fkp.id, {
            disetujui: true,
            catatan: catatan || null,
          }),
          'FKP diterima!',
        )

      case 'reject':
        if (!catatan.trim()) { toast.error('Alasan penolakan wajib diisi.'); return }
        return run(
          () => fkpApi.reject(fkp.id, { catatan }),
          'FKP ditolak.',
        )

      case 'close':
        return run(
          () => fkpApi.close(fkp.id, catatan || null),
          'FKP berhasil ditutup.',
        )

      case 'surat_jalan':
        if (!resolusiData.nomor_surat_jalan?.trim()) { toast.error('Nomor surat jalan wajib diisi.'); return }
        return run(
          () => fkpApi.inputSuratJalan(fkp.id, resolusiData.nomor_surat_jalan),
          'Nomor surat jalan disimpan.',
        )

      case 'resolusi':
        return run(
          () => fkpApi.createResolusi(fkp.id, buildResolusiPayload()),
          'Resolusi berhasil dibuat.',
        )
    }
  }

  // ← UBAH: pindahkan field fase 2 (nilai_cashback, bank, dll) keluar dari sini,
  //         tambah persentase_kompensasi_disetujui untuk potong_tagihan (fase 1)
  const buildResolusiPayload = () => {
    const base = {
      tipe_resolusi: resolusiTipe,
      metode_penanganan_fisik: metodePenanganan,
      detail_penanganan: detailPenanganan || null,
      keterangan: catatan || null,
    }
    if (resolusiTipe === 'potong_tagihan') {
      return {
        ...base,
        // ← TAMBAH: persentase wajib untuk potong_tagihan di fase 1
        persentase_kompensasi_disetujui: persentaseKompensasi
          ? Number(persentaseKompensasi)
          : null,
        // ← HAPUS: nilai_cashback, nama_bank, nomor_rekening, atas_nama, nomor_nota_retur
        //           (field ini adalah fase 2, diisi di "Mulai Proses")
      }
    }
    if (resolusiTipe === 'tukar_barang') {
      return {
        ...base,
        // ← HAPUS: nomor_do, ekspedisi, resi_pengiriman
        //           (field ini adalah fase 2, diisi di "Mulai Proses")
      }
    }
    // tidak_ada_kompensasi
    return {
      ...base,
      lokasi_pemusnahan: resolusiData.lokasi_pemusnahan || null,
      tanggal_pemusnahan: resolusiData.tanggal_pemusnahan || null,
    }
  }


  const setR = (k: string, v: string) => setResolusiData((p) => ({ ...p, [k]: v }))

  // ── TOMBOL PER STATUS + ROLE ──────────────────────────────────────────────
  const buttons: { label: string; icon: React.ElementType; action: ModalType; variant: string; condition: boolean }[] = [
    {
      label: 'Submit FKP',
      icon: Send,
      action: 'submit',
      variant: 'btn-primary',
      condition:
        ['draft', 'need_revision'].includes(fkp.status) &&
        ['distributor', 'outlet', 'sc_spv', 'apsm', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'Review & Teruskan ke Admin HO',
      icon: ClipboardCheck,
      action: 'apsm_review',
      variant: 'btn-primary',
      condition: fkp.status === 'submitted' && ['apsm', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'Minta Revisi',
      icon: RotateCcw,
      action: 'revision',
      variant: 'btn-secondary',
      condition:
        (['submitted', 'apsm_reviewed', 'in_investigation'] as FkpStatusKey[]).includes(fkp.status) &&
        ['apsm', 'qc', 'admin_ho', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'ACC → Teruskan ke QC',
      icon: CheckCircle2,
      action: 'admin_approve',
      variant: 'btn-primary',
      condition: fkp.status === 'apsm_reviewed' && ['admin_ho', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'Mulai Investigasi',
      icon: Search,
      action: 'investigate',
      variant: 'btn-primary',
      condition: fkp.status === 'rsm_approval_investigasi' && ['qc', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'Isi Hasil Investigasi',
      icon: ClipboardCheck,
      action: 'finish_investigation',
      variant: 'btn-primary',
      condition: fkp.status === 'in_investigation' && ['qc', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'Approve → Teruskan ke Direktur',
      icon: ThumbsUp,
      action: 'rsm_approve',
      variant: 'btn-primary',
      condition: fkp.status === 'investigated' && ['rsm', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'Approve FKP',
      icon: ThumbsUp,
      action: 'direktur_approve',
      variant: 'btn-primary',
      condition: fkp.status === 'rsm_approval_resolusi' && ['direktur', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'Terima Keluhan',
      icon: CheckCircle2,
      action: 'accept',
      variant: 'btn-primary',
      condition: fkp.status === 'direktur_approval' && ['admin_ho', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'Tolak FKP',
      icon: XCircle,
      action: 'reject',
      variant: 'btn-danger',
      condition:
        (['apsm_reviewed', 'in_investigation', 'investigated', 'rsm_approval_resolusi', 'direktur_approval'] as FkpStatusKey[]).includes(fkp.status) &&
        ['apsm', 'qc', 'rsm', 'direktur', 'admin_ho', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'Buat Resolusi',
      icon: ClipboardCheck,
      action: 'resolusi',
      variant: 'btn-primary',
      condition: fkp.status === 'accepted' && ['qc', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'Input Surat Jalan',
      icon: ClipboardCheck,
      action: 'surat_jalan',
      variant: 'btn-secondary',
      condition:
        fkp.resolution?.tipe_resolusi === 'tukar_barang' &&
        fkp.status === 'in_process' &&
        ['admin_ho', 'superadmin'].includes(kodeRole),
    },
    {
      label: 'Tutup FKP',
      icon: Lock,
      action: 'close',
      variant: 'btn-secondary',
      condition: fkp.status === 'in_process' && ['admin_ho', 'superadmin'].includes(kodeRole),
    },
  ]

  const visibleButtons = buttons.filter((b) => b.condition)

  if (visibleButtons.length === 0) {
    return (
      <div className="text-center py-4 text-sm text-gray-400">
        Tidak ada aksi tersedia untuk status ini.
      </div>
    )
  }

  return (
    <>
      <div className="space-y-2">
        {visibleButtons.map((btn) => (
          <button
            key={btn.action}
            onClick={() => { setModal(btn.action); setCatatan('') }}
            className={`${btn.variant} w-full`}
          >
            <btn.icon className="w-4 h-4" />
            {btn.label}
          </button>
        ))}
      </div>

      {/* ── MODAL ─────────────────────────────────────────── */}
      <Modal
        isOpen={!!modal}
        onClose={() => { setModal(null); setCatatan('') }}
        title={getModalTitle(modal)}
        size={modal === 'resolusi' ? 'xl' : modal === 'finish_investigation' ? 'md' : 'sm'}
      >
        <div className="space-y-4">
          {/* Hasil investigasi */}
          {modal === 'finish_investigation' && (
            <Select
              label="Sumber Ketidaksesuaian"
              required
              value={sumber}
              onChange={(e) => setSumber(e.target.value as 'internal' | 'pelanggan')}
            >
              <option value="internal">✅ Internal — produk dari kami (keluhan diterima)</option>
              <option value="pelanggan">❌ Pelanggan — keluhan ditolak</option>
            </Select>
          )}

          {/* Resolusi form */}
          {modal === 'resolusi' && (
            <div className="space-y-4">

              {/* Metode Penanganan Fisik */}
              <Select
                label="Metode Penanganan Fisik Barang"
                required
                value={metodePenanganan}
                onChange={(e) => { setMetodePenanganan(e.target.value as MetodePenangananFisik); setResolusiData({}) }}
              >
                <option value="dimusnahkan">Dimusnahkan</option>
                <option value="dijual_pakan_ternak">Dijual sebagai pakan ternak</option>
                <option value="dikirim_ke_ho">Dikirim ke Head Office</option>
                <option value="disimpan_distributor">Disimpan di distributor</option>
                <option value="di_repack_oleh_pihak_internal">Di Repack oleh pihak internal</option>
              </Select>

              {metodePenanganan === 'dimusnahkan' && (
                <>
                  <Input label="Lokasi Pemusnahan" required
                    placeholder="Gudang distributor / TPA..."
                    value={resolusiData.lokasi_pemusnahan ?? ''}
                    onChange={(e) => setR('lokasi_pemusnahan', e.target.value)} />
                  <Input label="Tanggal Pemusnahan" type="date"
                    value={resolusiData.tanggal_pemusnahan ?? ''}
                    onChange={(e) => setR('tanggal_pemusnahan', e.target.value)} />
                </>
              )}

              <Input label="Detail Penanganan (opsional)"
                placeholder="Dibakar, dikubur, dijual ke peternak Pak Budi..."
                value={detailPenanganan}
                onChange={(e) => setDetailPenanganan(e.target.value)} />

              {/* Tipe Kompensasi Finansial */}
              <Select
                label="Tipe Kompensasi"
                required
                value={resolusiTipe}
                onChange={(e) => { setResolusiTipe(e.target.value); setResolusiData({}); setPersentaseKompensasi('') }}
              >
                <option value="tukar_barang">Tukar Barang</option>
                <option value="potong_tagihan">Potong Tagihan (Cashback)</option>
                <option value="tidak_ada_kompensasi">Tanpa Kompensasi</option>
              </Select>

              {/* ← UBAH: untuk potong_tagihan hanya tampilkan persentase (fase 1).
                         Hapus input nilai_cashback, nama_bank, nomor_rekening, atas_nama. */}
              {resolusiTipe === 'potong_tagihan' && (
                <>
                  <Input
                    label="Persentase Kompensasi Disetujui (%)"
                    required
                    type="number"
                    placeholder="Contoh: 80 (artinya 80% dari nilai nota)"
                    value={persentaseKompensasi}
                    onChange={(e) => setPersentaseKompensasi(e.target.value)}
                  />
                  <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-500">
                    📋 Detail rekening dan nilai nota penjualan diisi setelah Direktur menyetujui,
                    di tahap "Mulai Proses".
                  </div>
                </>
              )}

              {/* ← UBAH: untuk tukar_barang hapus input nomor_do, ekspedisi, resi_pengiriman */}
              {resolusiTipe === 'tukar_barang' && (
                <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-500">
                  📋 Nomor DO, ekspedisi, resi pengiriman, dan qty disetujui per item diisi setelah
                  Direktur menyetujui, di tahap "Mulai Proses".
                </div>
              )}
            </div>
          )}

          {/* Surat jalan */}
          {modal === 'surat_jalan' && (
            <Input
              label="Nomor Surat Jalan"
              required
              placeholder="SJ-2025-0042"
              value={resolusiData.nomor_surat_jalan ?? ''}
              onChange={(e) => setR('nomor_surat_jalan', e.target.value)}
            />
          )}

          {/* Catatan (hampir semua modal) */}
          {modal !== 'surat_jalan' && (
            <Textarea
              label={modal === 'revision' || modal === 'reject' ? 'Alasan / Catatan *' : 'Catatan (opsional)'}
              placeholder={
                modal === 'revision' ? 'Jelaskan apa yang perlu diperbaiki...'
                  : modal === 'reject' ? 'Jelaskan alasan penolakan...'
                    : 'Tambahkan catatan untuk aksi ini...'
              }
              value={catatan}
              onChange={(e) => setCatatan(e.target.value)}
              rows={3}
            />
          )}

          <div className="flex gap-2 justify-end pt-1">
            <button
              onClick={() => { setModal(null); setCatatan('') }}
              disabled={isPending}
              className="btn-secondary"
            >
              Batal
            </button>
            <button
              onClick={handleConfirm}
              disabled={isPending}
              className={modal === 'reject' ? 'btn-danger' : 'btn-primary'}
            >
              {isPending
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Memproses...</>
                : 'Konfirmasi'}
            </button>
          </div>
        </div>
      </Modal>
    </>
  )
}

function getModalTitle(modal: ModalType): string {
  const map: Record<NonNullable<ModalType>, string> = {
    submit: 'Submit FKP',
    apsm_review: 'Review APSM — Teruskan ke Admin HO',
    admin_approve: 'Persetujuan Admin HO',
    revision: 'Minta Revisi',
    investigate: 'Mulai Investigasi',
    finish_investigation: 'Isi Hasil Investigasi',
    rsm_approve: 'Persetujuan RSM',
    direktur_approve: 'Persetujuan Direktur',
    accept: 'Terima Keluhan',
    reject: 'Tolak FKP',
    close: 'Tutup FKP',
    resolusi: 'Buat Resolusi',
    surat_jalan: 'Input Nomor Surat Jalan',
  }
  return modal ? map[modal] : ''
}