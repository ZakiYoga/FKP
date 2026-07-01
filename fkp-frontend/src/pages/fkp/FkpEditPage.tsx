import { useParams, useNavigate, useBlocker } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, Loader2, Upload, X, Plus, Pencil, Trash2 } from 'lucide-react'
import { notifications } from '@mantine/notifications'
import {
  useFkpDetail, useUpdateFkp, useDeleteAttachment,
  useAddFkpItem, useUpdateFkpItem, useDeleteFkpItem, useProducts, useOutlets,
} from '@/hooks/useFkp'
import { useCanWriteFkp } from '@/hooks/useCanWriteFkp'
import { useKodeRole } from '@/store/authStore'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { PageLoader } from '@/components/ui/Spinner'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { FkpItemFormModal, type FileWithMeta } from '@/components/fkp/FkpItemFormModal'
import { JENIS_KELUHAN_LABEL } from '@/types'
import type { FkpItem, FkpItemCreatePayload } from '@/types'
import api from '@/lib/axios'
import { TIPE_DOKUMEN_OPTIONS } from '@/constants/fkpAttachment'
import { useQueryClient } from '@tanstack/react-query'
import { fkpKeys } from '@/hooks/useFkp'
import type { ItemFormData } from '@/schemas/itemFKPSchema'
import { useFkpEditState, type PendingAddedItem } from '@/hooks/useFkpEditState'

// ── Schema header ─────────────────────────────────────────────────────────────

function buildHeaderSchema(isOutlet: boolean) {
  return z.object({
    outlet_id: z.string().optional(),
    catatan_distributor: z.string().optional(),
  }).superRefine((d, ctx) => {
    if (isOutlet && !d.outlet_id) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Outlet wajib dipilih',
        path: ['outlet_id'],
      })
    }
  })
}
type HeaderForm = z.infer<ReturnType<typeof buildHeaderSchema>>

// ── Tipe untuk modal state ────────────────────────────────────────────────────

type ModalMode =
  | { type: 'add' }
  | { type: 'edit-existing'; item: FkpItem; pendingPhotosToDelete: string[] }
  | { type: 'edit-added'; item: PendingAddedItem }

const DEFAULT_TIPE_UMUM = 'dokumen_lainnya'

interface PendingFile {
  file: File
  preview: string
  tipe_dokumen: string
  keterangan: string
}

export function FkpEditPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const kodeRole = useKodeRole()
  const isOutlet = kodeRole === 'outlet'
  const queryClient = useQueryClient()
  const isNavigatingAfterSaveRef = useRef(false)

  // ── Foto umum (immediate upload tetap dipertahankan) ──────────────────────
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
  const [isUploadingAll, setIsUploadingAll] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  // ── Modal ─────────────────────────────────────────────────────────────────
  const [modalMode, setModalMode] = useState<ModalMode | null>(null)
  const [resetKey, setResetKey] = useState(0)
  const [isSavingItem, setIsSavingItem] = useState(false)

  // ── Confirm dialogs ───────────────────────────────────────────────────────
  const [confirmDiscard, setConfirmDiscard] = useState(false)
  const [confirmDeleteItem, setConfirmDeleteItem] = useState<{
    type: 'existing'; itemId: string; label: string
  } | {
    type: 'added'; tempId: string; label: string
  } | null>(null)

  // ── Data fetch ────────────────────────────────────────────────────────────
  const { data: fkp, isLoading } = useFkpDetail(id)
  const canWrite = useCanWriteFkp(fkp)
  const { mutate: updateHeader, isPending: isUpdating } = useUpdateFkp(id ?? '')
  const { mutateAsync: deleteAttachment } = useDeleteAttachment(id ?? '')
  const { mutateAsync: addItemApi } = useAddFkpItem(id ?? '')
  const { mutateAsync: updateItemApi } = useUpdateFkpItem(id ?? '')
  const { mutateAsync: deleteItemApi } = useDeleteFkpItem(id ?? '')
  const { data: products = [] } = useProducts()
  const { data: outlets = [] } = useOutlets(fkp?.distributor_id)

  // ── Local edit state ──────────────────────────────────────────────────────
  const {
    state: editState,
    reset: resetEditState,
    visibleItems,
    totalItems,
    isDirty,
    markDeleted,
    markUpdated,
    addItem,
    removeAdded,
    updateAdded,
  } = useFkpEditState(fkp?.items ?? [])

  // ── Header form ───────────────────────────────────────────────────────────
  const { register, handleSubmit, reset: resetForm, formState: { errors, isDirty: isHeaderDirty } } =
    useForm<HeaderForm>({ resolver: zodResolver(buildHeaderSchema(isOutlet)) })

  const hasUnsavedChanges = isDirty || isHeaderDirty

  // ── Blocker navigasi ──────────────────────────────────────────────────────
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasUnsavedChanges &&
      !isNavigatingAfterSaveRef.current &&   // ← tambahkan ini
      currentLocation.pathname !== nextLocation.pathname,
  )

  useEffect(() => {
    if (blocker.state === 'blocked') setConfirmDiscard(true)
  }, [blocker.state])

  // ── Init ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!fkp) return
    if (!['draft', 'need_revision'].includes(fkp.status)) {
      notifications.show({ message: 'FKP ini tidak bisa diedit.', color: 'red' })
      navigate(`/fkp/${fkp.id}`)
      return
    }
    if (!canWrite) {
      notifications.show({ message: 'Anda hanya dapat mengubah FKP yang Anda buat sendiri.', color: 'red' })
      navigate(`/fkp/${fkp.id}`)
      return
    }
    resetForm({
      outlet_id: fkp.outlet_id ?? '',
      catatan_distributor: fkp.catatan_distributor ?? '',
    })
    resetEditState()
  }, [fkp, canWrite, resetForm, resetEditState, navigate])

  // ── Submit — eksekusi semua perubahan ─────────────────────────────────────
  const [isSubmitting, setIsSubmitting] = useState(false)

  const onSubmit = async (headerData: HeaderForm) => {
    if (totalItems === 0) {
      notifications.show({ message: 'Minimal 1 item produk harus ada.', color: 'red' })
      return
    }

    setIsSubmitting(true)
    try {
      // Step 1: Hapus item yang ditandai deleted
      for (const itemId of editState.deletedIds) {
        await deleteItemApi(itemId)
      }

      // Step 2: Update item existing + kelola fotonya
      for (const [itemId, changes] of Object.entries(editState.updated)) {
        await updateItemApi({ itemId, data: changes.payload })

        // Hapus foto lama yang ditandai dihapus
        for (const attachmentId of changes.photosToDelete) {
          await deleteAttachment(attachmentId)
        }

        // Upload foto baru
        for (const f of changes.photosToAdd) {
          const form = new FormData()
          form.append('file', f.file)
          form.append('tipe_dokumen', f.tipe_dokumen)
          if (f.keterangan) form.append('keterangan', f.keterangan)
          await api.post(`/fkp/${id}/attachments`, form, {
            headers: { 'Content-Type': 'multipart/form-data' },
            params: { fkp_item_id: itemId },
          })
        }
      }

      // Step 3: Tambah item baru + upload fotonya
      for (const addedItem of editState.added) {
        const newItem = await addItemApi(addedItem.payload)
        for (const f of addedItem.photos) {
          const form = new FormData()
          form.append('file', f.file)
          form.append('tipe_dokumen', f.tipe_dokumen)
          if (f.keterangan) form.append('keterangan', f.keterangan)
          await api.post(`/fkp/${id}/attachments`, form, {
            headers: { 'Content-Type': 'multipart/form-data' },
            params: { fkp_item_id: newItem.id },
          })
        }
      }

      // Step 4: Update header
      await new Promise<void>((resolve, reject) => {
        updateHeader(
          {
            outlet_id: headerData.outlet_id || null,
            catatan_distributor: headerData.catatan_distributor || null,
          },
          {
            onSuccess: () => resolve(),
            onError: (e) => reject(e),
          },
        )
      })

      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(id!) })
      notifications.show({ message: 'FKP berhasil disimpan.', color: 'green' })
      isNavigatingAfterSaveRef.current = true 
      navigate(`/fkp/${id}`)
    } catch {
      notifications.show({ message: 'Gagal menyimpan sebagian perubahan. Coba lagi.', color: 'red' })
    } finally {
      setIsSubmitting(false)
    }
  }

  // ── Batal / discard ───────────────────────────────────────────────────────
  const handleBatal = () => {
    navigate(`/fkp/${id}`)
  }

  const handleConfirmDiscard = () => {
    setConfirmDiscard(false)
    if (blocker.state === 'blocked') blocker.proceed()
  }

  const handleCancelDiscard = () => {
    setConfirmDiscard(false)
    if (blocker.state === 'blocked') blocker.reset()
  }

  // ── Modal helpers ─────────────────────────────────────────────────────────
  const openAddModal = () => {
    setModalMode({ type: 'add' })
    setResetKey((k) => k + 1)
  }

  const openEditExistingModal = (item: FkpItem) => {
    const pendingPhotosToDelete = editState.updated[item.id]?.photosToDelete ?? []
    setModalMode({ type: 'edit-existing', item, pendingPhotosToDelete })
    setResetKey((k) => k + 1)
  }

  const openEditAddedModal = (item: PendingAddedItem) => {
    setModalMode({ type: 'edit-added', item })
    setResetKey((k) => k + 1)
  }

  // ── Save dari modal ───────────────────────────────────────────────────────
  const handleItemSave = async (
    payload: FkpItemCreatePayload,
    files: FileWithMeta[],
    _formData: ItemFormData,
    photosToDelete: string[] = [],
  ) => {
    if (!modalMode) return
    setIsSavingItem(true)
    try {
      if (modalMode.type === 'add') {
        addItem(payload, files)
      } else if (modalMode.type === 'edit-existing') {
        markUpdated(modalMode.item.id, payload, files, photosToDelete)
      } else if (modalMode.type === 'edit-added') {
        updateAdded(modalMode.item.tempId, payload, files)
      }
      setModalMode(null)
    } finally {
      setIsSavingItem(false)
    }
  }

  // ── Hapus item ────────────────────────────────────────────────────────────
  const handleDeleteExistingItem = (item: FkpItem, label: string) => {
    setConfirmDeleteItem({ type: 'existing', itemId: item.id, label })
  }

  const handleDeleteAddedItem = (item: PendingAddedItem, label: string) => {
    setConfirmDeleteItem({ type: 'added', tempId: item.tempId, label })
  }

  const handleConfirmDeleteItem = () => {
    if (!confirmDeleteItem) return
    if (confirmDeleteItem.type === 'existing') {
      markDeleted(confirmDeleteItem.itemId)
    } else {
      removeAdded(confirmDeleteItem.tempId)
    }
    setConfirmDeleteItem(null)
  }

  // ── itemToFormData helper ─────────────────────────────────────────────────
  const itemToFormData = (item: FkpItem): ItemFormData => {
    const isCustomKeluhan = !Object.keys(JENIS_KELUHAN_LABEL).includes(item.jenis_keluhan)
    return {
      product_id: item.product_id ?? '',
      nama_produk_custom: item.nama_produk_custom ?? '',
      jenis_kemasan: (item.jenis_kemasan as ItemFormData['jenis_kemasan']) ?? undefined,
      qty: item.qty,
      batch_number: item.batch_number ?? '',
      expired_date: item.expired_date ?? '',
      ada_sample_keluhan: item.ada_sample_keluhan as ItemFormData['ada_sample_keluhan'],
      ada_foto_sample: item.ada_foto_sample,
      tanggal_pembelian: item.tanggal_pembelian ?? '',
      tanggal_dikonsumsi: item.tanggal_dikonsumsi ?? '',
      jenis_keluhan: isCustomKeluhan ? 'lainnya' : item.jenis_keluhan,
      jenis_keluhan_custom: isCustomKeluhan ? item.jenis_keluhan : '',
      deskripsi_keluhan: item.deskripsi_keluhan ?? '',
    }
  }

  // ── Foto umum ─────────────────────────────────────────────────────────────
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const added = Array.from(e.target.files ?? [])
    if (pendingFiles.length + added.length > 10) {
      notifications.show({ message: 'Maksimal 10 foto per upload batch.', color: 'red' })
      return
    }
    const newEntries: PendingFile[] = added.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      tipe_dokumen: DEFAULT_TIPE_UMUM,
      keterangan: '',
    }))
    setPendingFiles((prev) => [...prev, ...newEntries])
    if (fileRef.current) fileRef.current.value = ''
  }

  const updatePendingMeta = (idx: number, field: 'tipe_dokumen' | 'keterangan', value: string) => {
    setPendingFiles((prev) =>
      prev.map((f, i) => (i === idx ? { ...f, [field]: value } : f)),
    )
  }

  const removePending = (idx: number) => {
    setPendingFiles((prev) => {
      URL.revokeObjectURL(prev[idx].preview)
      return prev.filter((_, i) => i !== idx)
    })
  }

  const uploadPendingFiles = async () => {
    if (!id || pendingFiles.length === 0) return
    setIsUploadingAll(true)
    try {
      for (const f of pendingFiles) {
        const form = new FormData()
        form.append('file', f.file)
        form.append('tipe_dokumen', f.tipe_dokumen)
        if (f.keterangan) form.append('keterangan', f.keterangan)
        await api.post(`/fkp/${id}/attachments`, form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }
      pendingFiles.forEach((f) => URL.revokeObjectURL(f.preview))
      setPendingFiles([])
      notifications.show({ message: `${pendingFiles.length} foto berhasil diupload.`, color: 'green' })
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(id) })
    } catch {
      notifications.show({ message: 'Gagal mengupload sebagian foto.', color: 'red' })
    } finally {
      setIsUploadingAll(false)
    }
  }

  if (isLoading) return <PageLoader />
  if (!fkp) return null

  const fotoUmum = fkp.attachments.filter((a) => !a.fkp_item_id)
  const isBusy = isSubmitting || isUpdating

  // ── Modal props helper ────────────────────────────────────────────────────
  const getModalProps = () => {
    if (!modalMode) return { initialData: null, initialFiles: [], existingAttachments: [], variant: 'add' as const }

    if (modalMode.type === 'add') {
      return { initialData: null, initialFiles: [], existingAttachments: [], variant: 'add' as const }
    }

    if (modalMode.type === 'edit-existing') {
      const { item, pendingPhotosToDelete } = modalMode
      const pending = editState.updated[item.id]
      // Foto tersimpan: exclude yang sudah ditandai hapus di sesi ini
      const existingAttachments = fkp.attachments
        .filter((a) => a.fkp_item_id === item.id)
        .filter((a) => !pendingPhotosToDelete.includes(a.id))
      return {
        initialData: itemToFormData(item),
        initialFiles: pending?.photosToAdd ?? [],
        existingAttachments,
        variant: 'edit-saved' as const,
      }
    }

    // edit-added
    return {
      initialData: null,
      initialFiles: modalMode.item.photos,
      existingAttachments: [],
      variant: 'add' as const,
    }
  }

  const modalProps = getModalProps()

  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={handleBatal} className="btn-ghost btn-sm p-2">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Edit FKP</h1>
          <p className="text-sm text-gray-400 font-mono">{fkp.nomor_fkp}</p>
        </div>
        {hasUnsavedChanges && (
          <span className="ml-auto text-xs text-amber-600 bg-amber-50 border border-amber-200
                           px-2.5 py-1 rounded-full font-medium">
            Ada perubahan belum disimpan
          </span>
        )}
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">

        {/* ── Section 1: Header ───────────────────────────────────── */}
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-brand-600 text-white text-xs
                               flex items-center justify-center font-bold">1</span>
              Identitas FKP
            </h2>
          </div>
          <div className="card-body space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Distributor</label>
              <p className="text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                {fkp.distributor_info?.nama_perusahaan ?? fkp.distributor_id}
              </p>
              <p className="text-xs text-gray-400 mt-1">Distributor tidak bisa diubah setelah FKP dibuat.</p>
            </div>

            {isOutlet ? (
              outlets.length > 0 && (
                <div>
                  <Select label="Outlet" required placeholder="— Pilih outlet Anda —"
                    error={errors.outlet_id?.message} {...register('outlet_id')}>
                    {outlets.map((o) => (
                      <option key={o.id} value={o.id}>[{o.kode_outlet}] {o.nama_toko}</option>
                    ))}
                  </Select>
                  <p className="text-xs text-gray-400 mt-1">
                    {outlets.length === 1
                      ? 'Keluhan tercatat atas nama outlet Anda.'
                      : 'Anda terdaftar sebagai PIC di lebih dari satu outlet — pilih salah satu.'}
                  </p>
                </div>
              )
            ) : (
              outlets.length > 0 && (
                <Select label="Outlet (opsional)" placeholder="— Pilih outlet —" {...register('outlet_id')}>
                  {outlets.map((o) => (
                    <option key={o.id} value={o.id}>[{o.kode_outlet}] {o.nama_toko}</option>
                  ))}
                </Select>
              )
            )}

            <Textarea
              label="Catatan Tambahan"
              placeholder="Catatan kondisi penyimpanan atau info relevan lainnya..."
              rows={3}
              {...register('catatan_distributor')}
            />
          </div>
        </div>

        {/* ── Section 2: Item Produk ──────────────────────────────── */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-brand-600 text-white text-xs
                                 flex items-center justify-center font-bold">2</span>
                Item Produk
              </h2>
              <span className="text-xs text-gray-400">{totalItems} item</span>
            </div>
          </div>
          <div className="card-body space-y-3">

            {/* Item existing (tidak dihapus) */}
            {visibleItems.existing.map((item, idx) => {
              const prod = products.find((p) => p.id === item.product_id)
              const namaLabel = prod
                ? `[${prod.kode_produk}] ${prod.nama_produk}`
                : item.nama_produk_custom ?? 'Produk manual'
              const keluhan = JENIS_KELUHAN_LABEL[item.jenis_keluhan] ?? item.jenis_keluhan
              const qtyLabel = item.qty > 0 ? `${item.qty} ${item.jenis_kemasan ?? 'unit'}` : ''
              const isModified = !!editState.updated[item.id]

              return (
                <div key={item.id}
                  className="flex items-start gap-3 p-3 rounded-xl border border-gray-100 bg-gray-50">
                  <div className="w-8 h-8 rounded-full bg-brand-100 text-brand-700 text-sm font-bold
                                  flex items-center justify-center shrink-0">
                    {idx + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-gray-800 truncate">{namaLabel}</p>
                      {isModified && (
                        <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5
                                         rounded-full font-medium shrink-0">
                          diubah
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {keluhan}
                      {qtyLabel && <> · <span className="font-medium">{qtyLabel}</span></>}
                    </p>
                    {item.batch_number && (
                      <p className="text-xs text-gray-400 mt-0.5">Batch: {item.batch_number}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button type="button" onClick={() => openEditExistingModal(item)}
                      className="p-1.5 text-gray-400 hover:text-brand-600 hover:bg-brand-50
                                 rounded-lg transition-colors">
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button type="button"
                      onClick={() => handleDeleteExistingItem(item, namaLabel)}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50
                                 rounded-lg transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )
            })}

            {/* Item baru yang belum disimpan */}
            {visibleItems.added.map((item, idx) => {
              const prod = products.find((p) => p.id === item.payload.product_id)
              const namaLabel = prod
                ? `[${prod.kode_produk}] ${prod.nama_produk}`
                : item.payload.nama_produk_custom ?? 'Produk manual'
              const keluhan = JENIS_KELUHAN_LABEL[item.payload.jenis_keluhan] ?? item.payload.jenis_keluhan
              const qtyLabel = item.payload.qty > 0
                ? `${item.payload.qty} ${item.payload.jenis_kemasan ?? 'unit'}`
                : ''

              return (
                <div key={item.tempId}
                  className="flex items-start gap-3 p-3 rounded-xl border border-brand-200
                             bg-brand-50/40">
                  <div className="w-8 h-8 rounded-full bg-brand-500 text-white text-sm font-bold
                                  flex items-center justify-center shrink-0">
                    {visibleItems.existing.length + idx + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-gray-800 truncate">{namaLabel}</p>
                      <span className="text-[10px] bg-brand-100 text-brand-700 px-1.5 py-0.5
                                       rounded-full font-medium shrink-0">
                        baru
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {keluhan}
                      {qtyLabel && <> · <span className="font-medium">{qtyLabel}</span></>}
                    </p>
                    {item.payload.batch_number && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        Batch: {item.payload.batch_number}
                      </p>
                    )}
                    {item.photos.length > 0 && (
                      <p className="text-xs text-brand-600 mt-1">
                        📎 {item.photos.length} foto terlampir
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button type="button" onClick={() => openEditAddedModal(item)}
                      className="p-1.5 text-gray-400 hover:text-brand-600 hover:bg-brand-50
                                 rounded-lg transition-colors">
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button type="button"
                      onClick={() => handleDeleteAddedItem(item, namaLabel)}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50
                                 rounded-lg transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )
            })}

            {/* Hint jika semua item dihapus */}
            {totalItems === 0 && (
              <div className="text-center py-4 px-3 bg-red-50 border border-red-100 rounded-xl">
                <p className="text-sm text-red-600 font-medium">Minimal 1 item produk harus ada</p>
                <p className="text-xs text-red-400 mt-1">
                  Tambahkan item baru atau batalkan penghapusan.
                </p>
              </div>
            )}

            <button type="button" onClick={openAddModal}
              className="w-full border-2 border-dashed border-gray-200 rounded-xl py-4
                         flex items-center justify-center gap-2 text-gray-400 text-sm
                         hover:border-brand-400 hover:text-brand-500 hover:bg-brand-50 transition-all">
              <Plus className="w-4 h-4" /> Tambah Item Produk
            </button>
          </div>
        </div>

        {/* ── Section 3: Foto Lampiran Umum ──────────────────────── */}
        {/* Tidak berubah dari versi sebelumnya — foto umum tetap immediate */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-brand-600 text-white text-xs
                       flex items-center justify-center font-bold">3</span>
              Dokumen / Foto Lampiran
            </h2>
            <span className="text-xs text-gray-400">{fotoUmum.length} foto tersimpan</span>
          </div>
          <div className="card-body space-y-4">
            <p className="text-xs text-gray-400">
              Foto di sini bersifat umum dan tidak terkait item produk tertentu.
              Foto per item dikelola lewat tombol{' '}
              <Pencil className="w-3 h-3 inline -mt-0.5" /> pada masing-masing item di atas.
            </p>

            {fotoUmum.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-500">Foto tersimpan</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {fotoUmum.map((att) => (
                    <div key={att.id}
                      className="relative group rounded-xl overflow-hidden border border-gray-200 bg-white">
                      <a href={att.url} target="_blank" rel="noreferrer" className="block aspect-square">
                        <img src={att.url} alt={att.nama_file}
                          className="w-full h-full object-cover hover:opacity-90 transition-opacity" />
                      </a>
                      <button type="button" onClick={() => deleteAttachment(att.id)}
                        className="absolute top-1 right-1 w-6 h-6 bg-red-500 text-white rounded-full
                                   flex items-center justify-center opacity-0 group-hover:opacity-100
                                   transition-opacity">
                        <X className="w-3.5 h-3.5" />
                      </button>
                      {att.tipe_dokumen && (
                        <span className="absolute bottom-0 inset-x-0 bg-black/50 text-white
                                          text-[9px] text-center py-0.5 truncate px-1">
                          {TIPE_DOKUMEN_OPTIONS.find((o) => o.value === att.tipe_dokumen)?.label
                            ?? att.tipe_dokumen}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-gray-400 text-center py-3">Belum ada foto lampiran umum.</p>
            )}

            {pendingFiles.length > 0 && (
              <div className="border-t border-gray-100 pt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-gray-500">Foto baru — belum diupload</p>
                  <span className="text-xs text-gray-400">{pendingFiles.length} file</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {pendingFiles.map((f, idx) => (
                    <div key={idx}
                      className="border border-dashed border-brand-200 rounded-xl overflow-hidden
                                 bg-brand-50/30 flex flex-col">
                      <div className="relative group aspect-square">
                        <img src={f.preview} alt={`Foto baru ${idx + 1}`}
                          className="w-full h-full object-cover" />
                        <button type="button" onClick={() => removePending(idx)}
                          className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white
                                     rounded-full flex items-center justify-center
                                     opacity-0 group-hover:opacity-100 transition-opacity">
                          <X className="w-2.5 h-2.5" />
                        </button>
                        <span className="absolute bottom-1 left-1 px-1.5 py-0.5 rounded text-[9px]
                                         font-semibold bg-brand-500 text-white">BARU</span>
                      </div>
                      <div className="p-1.5 space-y-1">
                        <select value={f.tipe_dokumen}
                          onChange={(e) => updatePendingMeta(idx, 'tipe_dokumen', e.target.value)}
                          className="w-full text-[10px] border border-gray-200 rounded-md
                                     px-1.5 py-1 bg-white text-gray-700 focus:outline-hidden
                                     focus:border-brand-400">
                          {TIPE_DOKUMEN_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>
                        <input type="text" value={f.keterangan}
                          onChange={(e) => updatePendingMeta(idx, 'keterangan', e.target.value)}
                          placeholder="Keterangan (opsional)"
                          className="w-full text-[10px] border border-gray-200 rounded-md
                                     px-1.5 py-1 bg-white text-gray-700 placeholder-gray-300
                                     focus:outline-hidden focus:border-brand-400" />
                      </div>
                    </div>
                  ))}
                </div>
                <button type="button" onClick={uploadPendingFiles} disabled={isUploadingAll}
                  className="w-full btn-primary py-2 text-sm">
                  {isUploadingAll
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Mengupload {pendingFiles.length} foto...</>
                    : <><Upload className="w-4 h-4" /> Upload {pendingFiles.length} Foto Sekarang</>}
                </button>
              </div>
            )}

            <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp,video/mp4"
              multiple onChange={handleFileSelect} className="hidden" />
            <button type="button" onClick={() => fileRef.current?.click()}
              className="w-full border-2 border-dashed border-gray-200 rounded-xl py-5
                         flex items-center justify-center gap-2 text-gray-400 text-sm
                         hover:border-brand-400 hover:text-brand-500 hover:bg-brand-50 transition-all">
              <Plus className="w-4 h-4" /> Pilih Foto Lampiran Umum
            </button>
          </div>
        </div>

        {/* ── Actions ──────────────────────────────────────────────── */}
        <div className="flex justify-between pb-8">
          <button type="button" onClick={handleBatal} className="btn-secondary" disabled={isBusy}>
            Batal
          </button>
          <button type="submit" disabled={isBusy || totalItems === 0} className="btn-primary">
            {isBusy
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Menyimpan...</>
              : 'Simpan Perubahan'}
          </button>
        </div>
      </form>

      {/* ── Modal Item ────────────────────────────────────────────── */}
      <FkpItemFormModal
        isOpen={!!modalMode}
        onClose={() => setModalMode(null)}
        products={products}
        resetKey={resetKey}
        onSave={handleItemSave}
        isSaving={isSavingItem}
        {...modalProps}
      />

      {/* ── Confirm: buang perubahan ──────────────────────────────── */}
      <ConfirmDialog
        isOpen={confirmDiscard}
        onClose={handleCancelDiscard}
        onConfirm={handleConfirmDiscard}
        variant="warning"
        title="Buang Perubahan?"
        message="Ada perubahan yang belum disimpan. Jika kamu meninggalkan halaman ini, semua perubahan akan hilang."
        confirmLabel="Ya, Tinggalkan"
      />

      {/* ── Confirm: hapus item ───────────────────────────────────── */}
      <ConfirmDialog
        isOpen={!!confirmDeleteItem}
        onClose={() => setConfirmDeleteItem(null)}
        onConfirm={handleConfirmDeleteItem}
        variant="danger"
        title="Hapus Item?"
        message={`Item "${confirmDeleteItem?.label ?? ''}" akan dihapus dari FKP ini. Perubahan baru berlaku setelah kamu klik Simpan Perubahan.`}
        confirmLabel="Hapus Item"
      />
    </div>
  )
}