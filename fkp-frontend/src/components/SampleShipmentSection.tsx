import { useState } from 'react'
import {
  Plus, Truck, PackageCheck, ClipboardCheck, FlaskConical, XCircle,
  Upload, Loader2, CheckCircle2, Ban,
} from 'lucide-react'
import {
  useSampleList, useCreateSample, useConfirmSampleDelivery, useReceiveSample,
  useForwardSampleToQc, useStartSampleReview, useExamineSample, useCancelSample,
  useUploadSampleDocument,
} from '@/hooks/useSample'
import { useKodeRole, useCurrentUser, useAuthStore } from '@/store/authStore'
import { Modal } from '@/components/ui/Modal'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { AuthenticatedImage } from '@/components/AuthenticatedImage'
import { openAuthenticatedFile } from '@/hooks/useAuthenticatedImage'
import { TIPE_DOKUMEN_SAMPLE_OPTIONS } from '@/constants/fkpAttachment'
import {
  SAMPLE_STATUS_LABEL, SAMPLE_STATUS_FLOW, SAMPLE_STATUS_TERMINAL,
} from '@/types'
import type {
  FkpItem, FkpStatusKey, FkpAttachment, SampleShipment,
} from '@/types'

interface Props {
  fkpId: string
  fkpItems: FkpItem[]
  fkpStatus: FkpStatusKey
  attachments: FkpAttachment[]
}

// FKP hanya boleh menerima sample baru sebelum investigasi selesai — persis
// ALLOWED_FKP_STATUS_FOR_SAMPLE di backend (§4.3 dokumen rencana modul).
const STATUS_BOLEH_DAFTAR_SAMPLE: FkpStatusKey[] = [
  'submitted', 'apsm_reviewed', 'rsm_approval_investigasi', 'in_investigation',
]

type SampleModalTipe = 'create' | 'receive' | 'examine' | 'cancel' | 'upload' | null

const emptyCreateForm = {
  fkp_item_id: '', ekspedisi: '', nomor_resi: '', tanggal_kirim: '', catatan_pengirim: '', qty_sample: '1',
}
const emptyReceiveForm = { nomor_tanda_terima: '', catatan_warehouse: '' }
const emptyUploadForm = { tipeDokumen: TIPE_DOKUMEN_SAMPLE_OPTIONS[0].value, keterangan: '' }

export function SampleShipmentSection({ fkpId, fkpItems, fkpStatus, attachments }: Props) {
  const kodeRole = useKodeRole()
  const user = useCurrentUser()
  const token = useAuthStore((s) => s.token)

  const { data: samples = [], isLoading } = useSampleList(fkpId)
  const { mutateAsync: createSample, isPending: creating } = useCreateSample(fkpId)
  const { mutateAsync: confirmDelivery } = useConfirmSampleDelivery(fkpId)
  const { mutateAsync: receiveSample, isPending: receiving } = useReceiveSample(fkpId)
  const { mutateAsync: forwardToQc } = useForwardSampleToQc(fkpId)
  const { mutateAsync: startReview } = useStartSampleReview(fkpId)
  const { mutateAsync: examineSample, isPending: examining } = useExamineSample(fkpId)
  const { mutateAsync: cancelSample, isPending: cancelling } = useCancelSample(fkpId)
  const { mutateAsync: uploadDocument, isPending: uploading } = useUploadSampleDocument(fkpId)

  const [modal, setModal] = useState<SampleModalTipe>(null)
  const [activeSampleId, setActiveSampleId] = useState<string | null>(null)
  const [createForm, setCreateForm] = useState(emptyCreateForm)
  const [receiveForm, setReceiveForm] = useState(emptyReceiveForm)
  const [examineForm, setExamineForm] = useState('')
  const [cancelForm, setCancelForm] = useState('')
  const [uploadForm, setUploadForm] = useState(emptyUploadForm)
  const [uploadFile, setUploadFile] = useState<File | null>(null)

  const closeModal = () => { setModal(null); setActiveSampleId(null) }

  // ── Role gates — persis mapping "roles" di seeds/seed_permissions.py ──────
  // (bukan §11.2 dokumen rencana v3.0 yang sedikit berbeda — misal apsm TIDAK
  // termasuk sample.create/deliver_confirm di seed aktual, meski dokumen
  // rencana mencantumkannya. Ikuti seed aktual supaya tombol tidak menampilkan
  // aksi yang pasti akan 403.)
  const canCreate = ['outlet', 'distributor', 'sc_spv', 'admin_ho', 'superadmin'].includes(kodeRole)
    && STATUS_BOLEH_DAFTAR_SAMPLE.includes(fkpStatus)
  const canReceive = ['warehouse', 'admin_ho', 'superadmin'].includes(kodeRole)
  const canForwardQc = ['warehouse', 'admin_ho', 'superadmin'].includes(kodeRole)
  const canExamine = ['qc', 'admin_ho', 'superadmin'].includes(kodeRole)
  const canUploadDoc = ['warehouse', 'qc', 'admin_ho', 'superadmin'].includes(kodeRole)

  const canConfirmDelivery = (s: SampleShipment) =>
    ['admin_ho', 'superadmin'].includes(kodeRole) ||
    (['outlet', 'distributor', 'sc_spv'].includes(kodeRole) && s.sender_id === user?.id)

  // [CATATAN] Backend saat ini HANYA mengizinkan admin_ho/warehouse/superadmin
  // untuk cancel (permission "sample.cancel" di seed belum mencakup
  // outlet/distributor/sc_spv/apsm walau ada logic ownership-check untuk
  // mereka di sample_service.cancel_sample() — cabang itu currently tidak
  // pernah tercapai karena permission gate duluan menolak). Tombol di sini
  // sengaja mengikuti kondisi permission AKTUAL, bukan logic ownership yang
  // belum bisa dicapai, supaya tidak menampilkan tombol yang pasti 403.
  const canCancel = (s: SampleShipment) => {
    if (SAMPLE_STATUS_TERMINAL.includes(s.status)) return false
    if (['admin_ho', 'superadmin'].includes(kodeRole)) return true
    if (kodeRole === 'warehouse') return s.status === 'received_by_warehouse'
    return false
  }

  const itemName = (fkpItemId: string) =>
    fkpItems.find((it) => it.id === fkpItemId)?.nama_produk_custom ?? 'Produk'

  const openReceiveModal = (sampleId: string) => {
    setActiveSampleId(sampleId)
    setReceiveForm(emptyReceiveForm)
    setModal('receive')
  }
  const openExamineModal = (sampleId: string) => {
    setActiveSampleId(sampleId)
    setExamineForm('')
    setModal('examine')
  }
  const openCancelModal = (sampleId: string) => {
    setActiveSampleId(sampleId)
    setCancelForm('')
    setModal('cancel')
  }
  const openUploadModal = (sampleId: string) => {
    setActiveSampleId(sampleId)
    setUploadForm(emptyUploadForm)
    setUploadFile(null)
    setModal('upload')
  }

  const handleCreate = async () => {
    if (!createForm.fkp_item_id) return
    await createSample({
      fkp_item_id: createForm.fkp_item_id,
      ekspedisi: createForm.ekspedisi || null,
      nomor_resi: createForm.nomor_resi || null,
      tanggal_kirim: createForm.tanggal_kirim || null,
      catatan_pengirim: createForm.catatan_pengirim || null,
      qty_sample: Number(createForm.qty_sample) || 1,
    })
    setCreateForm(emptyCreateForm)
    closeModal()
  }

  const handleReceive = async () => {
    if (!activeSampleId || !receiveForm.nomor_tanda_terima.trim()) return
    await receiveSample({
      sampleId: activeSampleId,
      data: {
        nomor_tanda_terima: receiveForm.nomor_tanda_terima,
        catatan_warehouse: receiveForm.catatan_warehouse || null,
      },
    })
    closeModal()
  }

  const handleExamine = async () => {
    if (!activeSampleId || !examineForm.trim()) return
    await examineSample({ sampleId: activeSampleId, data: { hasil_pemeriksaan: examineForm } })
    closeModal()
  }

  const handleCancel = async () => {
    if (!activeSampleId || !cancelForm.trim()) return
    await cancelSample({ sampleId: activeSampleId, data: { alasan_batal: cancelForm } })
    closeModal()
  }

  const handleUpload = async () => {
    if (!activeSampleId || !uploadFile) return
    await uploadDocument({
      sampleId: activeSampleId,
      file: uploadFile,
      tipeDokumen: uploadForm.tipeDokumen,
      keterangan: uploadForm.keterangan || null,
    })
    closeModal()
  }

  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <h2 className="font-semibold text-gray-900 flex items-center gap-2">
          <Truck className="w-4 h-4 text-brand-500" /> Sample Shipment ({samples.length})
        </h2>
        {canCreate && (
          <button className="btn-primary btn-sm" onClick={() => { setCreateForm(emptyCreateForm); setModal('create') }}>
            <Plus className="w-3.5 h-3.5" /> Daftarkan Sample
          </button>
        )}
      </div>
      <div className="card-body space-y-4">
        {isLoading && <p className="text-sm text-gray-500">Memuat...</p>}
        {!isLoading && samples.length === 0 && (
          <p className="text-sm text-gray-500">Belum ada sample yang didaftarkan.</p>
        )}
        {samples.map((s) => {
          const docs = attachments.filter((a) => a.sample_shipment_id === s.id)
          const stepIndex = SAMPLE_STATUS_FLOW.indexOf(s.status)
          return (
            <div key={s.id} className="p-3 rounded-xl border border-gray-200 space-y-2.5">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div>
                  <p className="text-sm font-semibold text-gray-800">{itemName(s.fkp_item_id)}</p>
                  <p className="text-xs text-gray-500">
                    Qty: {s.qty_sample}{s.nomor_resi ? ` · Resi: ${s.nomor_resi}` : ''}
                    {s.ekspedisi ? ` · ${s.ekspedisi}` : ''}
                  </p>
                </div>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs border ${
                  s.status === 'cancelled'
                    ? 'bg-red-50 text-red-700 border-red-200'
                    : s.status === 'examined'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-brand-50 text-brand-700 border-brand-200'
                }`}>
                  {SAMPLE_STATUS_LABEL[s.status]}
                </span>
              </div>

              {/* Mini progress — hanya untuk alur normal, cancelled ditampilkan terpisah */}
              {s.status !== 'cancelled' && (
                <div className="flex items-center gap-1">
                  {SAMPLE_STATUS_FLOW.map((step, i) => (
                    <div key={step} className={`h-1.5 flex-1 rounded-full ${i <= stepIndex ? 'bg-brand-500' : 'bg-gray-150'}`} />
                  ))}
                </div>
              )}

              {s.status === 'cancelled' && s.alasan_batal && (
                <p className="text-xs text-red-600">Alasan pembatalan: {s.alasan_batal}</p>
              )}
              {s.nomor_tanda_terima && (
                <p className="text-xs text-gray-500">No. Tanda Terima: {s.nomor_tanda_terima}</p>
              )}
              {/* hasil_pemeriksaan sudah disaring null oleh backend untuk role
                  outlet/distributor/sc_spv — kalau null di sini, memang belum
                  ada ATAU memang tidak berhak lihat, tidak perlu dibedakan di FE */}
              {s.hasil_pemeriksaan && (
                <div className="p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-700">
                  <strong>Hasil Pemeriksaan QC:</strong> {s.hasil_pemeriksaan}
                </div>
              )}

              {docs.length > 0 && (
                <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
                  {docs.map((d) => (
                    <button key={d.id} type="button" onClick={() => openAuthenticatedFile(d.url, token)} className="aspect-square block">
                      <AuthenticatedImage src={d.url} alt={d.nama_file}
                        className="w-full h-full object-cover rounded-lg border border-gray-200 hover:opacity-90 transition-opacity" />
                    </button>
                  ))}
                </div>
              )}

              <div className="flex flex-wrap gap-2 pt-1">
                {s.status === 'shipped' && canConfirmDelivery(s) && (
                  <button className="btn-secondary btn-sm" onClick={() => confirmDelivery(s.id)}>
                    <PackageCheck className="w-3.5 h-3.5" /> Konfirmasi Terkirim
                  </button>
                )}
                {s.status === 'delivered' && canReceive && (
                  <button className="btn-secondary btn-sm" onClick={() => openReceiveModal(s.id)}>
                    <PackageCheck className="w-3.5 h-3.5" /> Terima di Warehouse
                  </button>
                )}
                {s.status === 'received_by_warehouse' && canForwardQc && (
                  <button className="btn-secondary btn-sm" onClick={() => forwardToQc(s.id)}>
                    <ClipboardCheck className="w-3.5 h-3.5" /> Serahkan ke QC
                  </button>
                )}
                {s.status === 'forwarded_to_qc' && canExamine && (
                  <button className="btn-secondary btn-sm" onClick={() => startReview(s.id)}>
                    <FlaskConical className="w-3.5 h-3.5" /> Mulai Pemeriksaan
                  </button>
                )}
                {s.status === 'under_qc_review' && canExamine && (
                  <button className="btn-primary btn-sm" onClick={() => openExamineModal(s.id)}>
                    <CheckCircle2 className="w-3.5 h-3.5" /> Selesaikan Pemeriksaan
                  </button>
                )}
                {canUploadDoc && !SAMPLE_STATUS_TERMINAL.includes(s.status) && (
                  <button className="btn-secondary btn-sm" onClick={() => openUploadModal(s.id)}>
                    <Upload className="w-3.5 h-3.5" /> Upload Dokumen
                  </button>
                )}
                {/* {canCancel(s) && (
                  <button className="btn-danger btn-sm" onClick={() => openCancelModal(s.id)}>
                    <Ban className="w-3.5 h-3.5" /> Batalkan
                  </button>
                )} */}
              </div>
            </div>
          )
        })}
      </div>

      {/* ── Daftarkan Sample Baru ──────────────────────────────────────────── */}
      <Modal isOpen={modal === 'create'} onClose={closeModal} title="Daftarkan Pengiriman Sample" size="md">
        <div className="space-y-4">
          <Select label="Item Produk" required placeholder="— Pilih item —"
            value={createForm.fkp_item_id}
            onChange={(e) => setCreateForm((p) => ({ ...p, fkp_item_id: e.target.value }))}>
            {fkpItems.map((it) => (
              <option key={it.id} value={it.id}>{it.nama_produk_custom ?? 'Produk'} (Qty: {it.qty})</option>
            ))}
          </Select>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Ekspedisi (opsional)" value={createForm.ekspedisi}
              onChange={(e) => setCreateForm((p) => ({ ...p, ekspedisi: e.target.value }))} />
            <Input label="No. Resi (opsional)" value={createForm.nomor_resi}
              onChange={(e) => setCreateForm((p) => ({ ...p, nomor_resi: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Tanggal Kirim (opsional)" type="date" value={createForm.tanggal_kirim}
              onChange={(e) => setCreateForm((p) => ({ ...p, tanggal_kirim: e.target.value }))} />
            <Input label="Qty Sample" type="number" value={createForm.qty_sample}
              onChange={(e) => setCreateForm((p) => ({ ...p, qty_sample: e.target.value }))} />
          </div>
          <Textarea label="Catatan Pengirim (opsional)" rows={2} value={createForm.catatan_pengirim}
            onChange={(e) => setCreateForm((p) => ({ ...p, catatan_pengirim: e.target.value }))} />
          <div className="flex justify-end gap-2 pt-2">
            <button className="btn-secondary" onClick={closeModal}>Batal</button>
            <button className="btn-primary" onClick={handleCreate} disabled={creating || !createForm.fkp_item_id}>
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Daftarkan
            </button>
          </div>
        </div>
      </Modal>

      {/* ── Terima di Warehouse ──────────────────────────────────────────────── */}
      <Modal isOpen={modal === 'receive'} onClose={closeModal} title="Terima Sample di Warehouse" size="md">
        <div className="space-y-4">
          <Input label="Nomor Tanda Terima" required value={receiveForm.nomor_tanda_terima}
            onChange={(e) => setReceiveForm((p) => ({ ...p, nomor_tanda_terima: e.target.value }))} />
          <Textarea label="Catatan Warehouse (opsional)" rows={2} value={receiveForm.catatan_warehouse}
            onChange={(e) => setReceiveForm((p) => ({ ...p, catatan_warehouse: e.target.value }))} />
          <div className="flex justify-end gap-2 pt-2">
            <button className="btn-secondary" onClick={closeModal}>Batal</button>
            <button className="btn-primary" onClick={handleReceive} disabled={receiving || !receiveForm.nomor_tanda_terima.trim()}>
              {receiving ? <Loader2 className="w-4 h-4 animate-spin" /> : <PackageCheck className="w-4 h-4" />} Terima
            </button>
          </div>
        </div>
      </Modal>

      {/* ── Selesaikan Pemeriksaan QC ──────────────────────────────────────────── */}
      <Modal isOpen={modal === 'examine'} onClose={closeModal} title="Selesaikan Pemeriksaan QC" size="md">
        <div className="space-y-4">
          <Textarea label="Hasil Pemeriksaan" required rows={4} value={examineForm}
            onChange={(e) => setExamineForm(e.target.value)}
            placeholder="Wajib diisi — narasi hasil pemeriksaan QC" />
          <div className="flex justify-end gap-2 pt-2">
            <button className="btn-secondary" onClick={closeModal}>Batal</button>
            <button className="btn-primary" onClick={handleExamine} disabled={examining || !examineForm.trim()}>
              {examining ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Selesaikan
            </button>
          </div>
        </div>
      </Modal>

      {/* ── Batalkan Sample ──────────────────────────────────────────────────── */}
      <Modal isOpen={modal === 'cancel'} onClose={closeModal} title="Batalkan Pengiriman Sample" size="md">
        <div className="space-y-4">
          <Textarea label="Alasan Pembatalan" required rows={3} value={cancelForm}
            onChange={(e) => setCancelForm(e.target.value)}
            placeholder="Wajib diisi" />
          <div className="flex justify-end gap-2 pt-2">
            <button className="btn-secondary" onClick={closeModal}>Tutup</button>
            <button className="btn-danger" onClick={handleCancel} disabled={cancelling || !cancelForm.trim()}>
              {cancelling ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />} Batalkan
            </button>
          </div>
        </div>
      </Modal>

      {/* ── Upload Dokumen Sample ──────────────────────────────────────────────── */}
      <Modal isOpen={modal === 'upload'} onClose={closeModal} title="Upload Dokumen Sample" size="md">
        <div className="space-y-4">
          <Select label="Tipe Dokumen" required value={uploadForm.tipeDokumen}
            onChange={(e) => setUploadForm((p) => ({ ...p, tipeDokumen: e.target.value }))}>
            {TIPE_DOKUMEN_SAMPLE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </Select>
          <div>
            <label className="label">File</label>
            <input type="file" accept="image/*,.pdf"
              onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              className="input-base" />
          </div>
          <Input label="Keterangan (opsional)" value={uploadForm.keterangan}
            onChange={(e) => setUploadForm((p) => ({ ...p, keterangan: e.target.value }))} />
          <div className="flex justify-end gap-2 pt-2">
            <button className="btn-secondary" onClick={closeModal}>Batal</button>
            <button className="btn-primary" onClick={handleUpload} disabled={uploading || !uploadFile}>
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />} Upload
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}