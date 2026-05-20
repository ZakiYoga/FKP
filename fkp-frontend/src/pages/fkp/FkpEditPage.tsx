import { useParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useEffect, useRef, useState } from 'react'
import {
  ArrowLeft,
  Loader2,
  Upload,
  X,
  Plus,
  Pencil,
  Trash2
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  useFkpDetail, useUpdateFkp, useDeleteAttachment,
  useAddFkpItem, useUpdateFkpItem, useDeleteFkpItem, useProducts, useOutlets,
} from '@/hooks/useFkp'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { PageLoader } from '@/components/ui/Spinner'
import { FkpItemFormModal, type FileWithMeta } from '@/components/fkp/FkpItemFormModal'
import { JENIS_KELUHAN_LABEL } from '@/types'
import type { FkpItem, FkpItemCreatePayload } from '@/types'
import api from '@/lib/axios'
import { AttachmentGrid } from '@/components/fkp/AttachmentLightbox'
import { TIPE_DOKUMEN_OPTIONS } from '@/components/fkp/FkpItemFormModal'
import { useQueryClient } from '@tanstack/react-query'
import { fkpKeys } from '@/hooks/useFkp'

// ── Schema header FKP (sesuai FkpUpdate di backend) ──────────────────────────
const headerSchema = z.object({
  outlet_id: z.string().optional(),
  // prioritas: z.enum(['top_urgent', 'urgent', 'reguler', 'low']),
  catatan_distributor: z.string().optional(),
})
type HeaderForm = z.infer<typeof headerSchema>

interface PendingFile {
  file: File
  preview: string
  tipe_dokumen: string
  keterangan: string
}

export function FkpEditPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
  const [isUploadingAll, setIsUploadingAll] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  // Modal state untuk tambah / edit item
  const [modalOpen, setModalOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<FkpItem | null>(null)
  const [resetKey, setResetKey] = useState(0)
  const [isSavingItem, setIsSavingItem] = useState(false)

  const { data: fkp, isLoading } = useFkpDetail(id)
  const { mutate: updateHeader, isPending: isUpdating } = useUpdateFkp(id ?? '')
  const { mutate: deleteAtt } = useDeleteAttachment(id ?? '')
  const { mutateAsync: addItem } = useAddFkpItem(id ?? '')
  const { mutateAsync: updateItem } = useUpdateFkpItem(id ?? '')
  const { mutate: deleteItem } = useDeleteFkpItem(id ?? '')
  const { data: products = [] } = useProducts()
  const { data: outlets = [] } = useOutlets(fkp?.distributor_id)

  const queryClient = useQueryClient()

  const { register, handleSubmit, reset, formState: { errors } } = useForm<HeaderForm>({
    resolver: zodResolver(headerSchema),
  })

  // ── Redirect jika status tidak bisa diedit ──────────────────────────────
  useEffect(() => {
    if (!fkp) return
    if (!['draft', 'need_revision'].includes(fkp.status)) {
      toast.error('FKP ini tidak bisa diedit.')
      navigate(`/fkp/${fkp.id}`)
      return
    }
    // Reset form dengan data header existing
    reset({
      outlet_id: fkp.outlet_id ?? '',
      // prioritas: fkp.prioritas,
      catatan_distributor: fkp.catatan_distributor ?? '',
    })
  }, [fkp, reset, navigate])

  // ── Submit header ────────────────────────────────────────────────────────
  const onSubmitHeader = (data: HeaderForm) => {
    updateHeader(
      {
        outlet_id: data.outlet_id || null,
        // prioritas: data.prioritas,
        catatan_distributor: data.catatan_distributor || null,
      },
      { onSuccess: () => navigate(`/fkp/${id}`) },
    )
  }

  // ── Upload foto ──────────────────────────────────────────────────────────
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const added = Array.from(e.target.files ?? [])
    if (pendingFiles.length + added.length > 10) {
      toast.error('Maksimal 10 foto per upload batch.')
      return
    }
    const newEntries: PendingFile[] = added.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      tipe_dokumen: 'foto_keluhan',
      keterangan: '',
    }))
    setPendingFiles((prev) => [...prev, ...newEntries])
    if (fileRef.current) fileRef.current.value = ''
  }

  const updatePendingMeta = (
    idx: number,
    field: 'tipe_dokumen' | 'keterangan',
    value: string,
  ) => {
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
      // Cleanup preview URLs
      pendingFiles.forEach((f) => URL.revokeObjectURL(f.preview))
      setPendingFiles([])
      toast.success(`${pendingFiles.length} foto berhasil diupload.`)
      // Refresh data
      queryClient.invalidateQueries({ queryKey: fkpKeys.detail(id) })
    } catch {
      toast.error('Gagal mengupload sebagian foto.')
    } finally {
      setIsUploadingAll(false)
    }
  }

  // ── Buka modal tambah item ───────────────────────────────────────────────
  const openAddModal = () => {
    setEditingItem(null)
    setResetKey((k) => k + 1)
    setModalOpen(true)
  }

  // ── Buka modal edit item ─────────────────────────────────────────────────
  const openEditModal = (item: FkpItem) => {
    setEditingItem(item)
    setResetKey((k) => k + 1)
    setModalOpen(true)
  }

  // ── Save dari modal (tambah atau edit) ───────────────────────────────────
  const handleItemSave = async (payload: FkpItemCreatePayload, files: FileWithMeta[]) => {
    if (!id) return
    setIsSavingItem(true)
    try {
      let savedItemId: string

      if (editingItem) {
        // Edit item existing
        await updateItem({ itemId: editingItem.id, data: payload })
        savedItemId = editingItem.id
        toast.success('Item berhasil diupdate.')
      } else {
        // Tambah item baru
        const newItem = await addItem(payload)
        savedItemId = newItem.id
        toast.success('Item berhasil ditambahkan.')
      }

      // Upload foto baru (jika ada)
      for (const f of files) {
        const form = new FormData()
        form.append('file', f.file)
        form.append('tipe_dokumen', f.tipe_dokumen)
        if (f.keterangan) form.append('keterangan', f.keterangan)
        await api.post(`/fkp/${id}/attachments`, form, {
          headers: { 'Content-Type': 'multipart/form-data' },
          params: { fkp_item_id: savedItemId },
        })
      }

      setModalOpen(false)
    } catch {
      // error sudah di-handle oleh mutation onError
    } finally {
      setIsSavingItem(false)
    }
  }

  if (isLoading) return <PageLoader />
  if (!fkp) return null

  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      {/* Page header */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate(`/fkp/${id}`)} className="btn-ghost btn-sm p-2">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Edit FKP</h1>
          <p className="text-sm text-gray-400 font-mono">{fkp.nomor_fkp}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmitHeader)} className="space-y-6">

        {/* ── Section 1: Header FKP ─────────────────────────────────── */}
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-brand-600 text-white text-xs
                               flex items-center justify-center font-bold">1</span>
              Identitas FKP
            </h2>
          </div>
          <div className="card-body space-y-4">
            {/* Distributor — read only, tidak bisa diubah */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Distributor</label>
              <p className="text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                {fkp.distributor_info?.nama_perusahaan ?? fkp.distributor_id}
              </p>
              <p className="text-xs text-gray-400 mt-1">Distributor tidak bisa diubah setelah FKP dibuat.</p>
            </div>

            {/* Outlet — bisa diubah */}
            {outlets.length > 0 && (
              <Select
                label="Outlet (opsional)"
                placeholder="— Pilih outlet —"
                {...register('outlet_id')}
              >
                {outlets.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.nama_toko}
                  </option>
                ))}
              </Select>
            )}

            {/* <Select label="Prioritas" required error={errors.prioritas?.message} {...register('prioritas')}>
              <option value="top_urgent">🔴 Top Urgent</option>
              <option value="urgent">🟠 Urgent</option>
              <option value="reguler">🟢 Reguler</option>
              <option value="low">🔵 Low</option>
            </Select> */}

            <Textarea
              label="Catatan Tambahan"
              placeholder="Catatan kondisi penyimpanan atau info relevan lainnya..."
              rows={3}
              {...register('catatan_distributor')}
            />
          </div>
        </div>

        {/* ── Section 2: Item Produk ───────────────────────────────── */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-brand-600 text-white text-xs
                                 flex items-center justify-center font-bold">2</span>
                Item Produk
              </h2>
              <span className="text-xs text-gray-400">{fkp.items.length} item</span>
            </div>
          </div>
          <div className="card-body space-y-3">
            {fkp.items.map((item, idx) => {
              const prod = products.find((p) => p.id === item.product_id)
              const namaLabel = prod
                ? `[${prod.kode_produk}] ${prod.nama_produk}`
                : item.nama_produk_custom ?? 'Produk manual'
              const keluhan = JENIS_KELUHAN_LABEL[item.jenis_keluhan] ?? item.jenis_keluhan
              const qtyLabel = item.qty > 0
                ? `${item.qty} ${item.jenis_kemasan ?? 'unit'}`
                : ''

              return (
                <div key={item.id}
                  className="flex items-start gap-3 p-3 rounded-xl border border-gray-100 bg-gray-50">
                  <div className="w-8 h-8 rounded-full bg-brand-100 text-brand-700 text-sm font-bold
                                  flex items-center justify-center shrink-0">
                    {idx + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-800 truncate">{namaLabel}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {keluhan}
                      {qtyLabel && <> · <span className="font-medium">{qtyLabel}</span></>}
                    </p>
                    {item.batch_number && (
                      <p className="text-xs text-gray-400 mt-0.5">Batch: {item.batch_number}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      type="button"
                      onClick={() => openEditModal(item)}
                      className="p-1.5 text-gray-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteItem(item.id)}
                      disabled={fkp.items.length <= 1}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg
                                 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                      title={fkp.items.length <= 1 ? 'Minimal 1 item harus ada' : 'Hapus item'}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )
            })}

            <button
              type="button"
              onClick={openAddModal}
              className="w-full border-2 border-dashed border-gray-200 rounded-xl py-4
                         flex items-center justify-center gap-2 text-gray-400 text-sm
                         hover:border-brand-400 hover:text-brand-500 hover:bg-brand-50 transition-all"
            >
              <Plus className="w-4 h-4" /> Tambah Item Produk
            </button>
          </div>
        </div>

        {/* ── Section 3: Foto Bukti ────────────────────────────────── */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-brand-600 text-white text-xs
                       flex items-center justify-center font-bold">3</span>
              Foto Bukti
            </h2>
            <span className="text-xs text-gray-400">{fkp.attachments.length} foto tersimpan</span>
          </div>
          <div className="card-body space-y-4">

            {/* ── Foto yang sudah tersimpan — pakai AttachmentGrid + hapus ── */}
            {fkp.attachments.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-500">Foto tersimpan</p>
                {/* Grid dengan lightbox bawaan AttachmentGrid */}
                <AttachmentGrid attachments={fkp.attachments} cols={4} />
                {/* Tombol hapus per foto — di bawah grid karena AttachmentGrid tidak expose hapus */}
                <div className="grid grid-cols-4 gap-2 mt-1">
                  {fkp.attachments.map((att) => (
                    <button
                      key={att.id}
                      type="button"
                      onClick={() => deleteAtt(att.id)}
                      className="flex items-center justify-center gap-1 py-1 text-[10px]
                         text-red-400 hover:text-red-600 hover:bg-red-50
                         rounded-lg border border-transparent hover:border-red-200
                         transition-colors"
                    >
                      <X className="w-3 h-3" /> Hapus
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-gray-400 text-center py-3">
                Belum ada foto tersimpan.
              </p>
            )}

            {/* Divider jika ada pending */}
            {pendingFiles.length > 0 && (
              <div className="border-t border-gray-100 pt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-gray-500">
                    Foto baru — belum diupload
                  </p>
                  <span className="text-xs text-gray-400">{pendingFiles.length} file</span>
                </div>

                {/* Grid pending files dengan meta editor */}
                <div className="grid grid-cols-2 gap-2">
                  {pendingFiles.map((f, idx) => (
                    <div key={idx}
                      className="border border-dashed border-brand-200 rounded-xl
                         overflow-hidden bg-brand-50/30 flex flex-col">
                      {/* Preview */}
                      <div className="relative group aspect-square">
                        <img
                          src={f.preview}
                          alt={`Foto baru ${idx + 1}`}
                          className="w-full h-full object-cover"
                        />
                        <button
                          type="button"
                          onClick={() => removePending(idx)}
                          className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white
                             rounded-full flex items-center justify-center
                             opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <X className="w-2.5 h-2.5" />
                        </button>
                        {/* Badge "baru" */}
                        <span className="absolute bottom-1 left-1 px-1.5 py-0.5 rounded text-[9px]
                                 font-semibold bg-brand-500 text-white">
                          BARU
                        </span>
                      </div>

                      {/* Meta editor */}
                      <div className="p-1.5 space-y-1">
                        <select
                          value={f.tipe_dokumen}
                          onChange={(e) => updatePendingMeta(idx, 'tipe_dokumen', e.target.value)}
                          className="w-full text-[10px] border border-gray-200 rounded-md
                             px-1.5 py-1 bg-white text-gray-700
                             focus:outline-none focus:border-brand-400"
                        >
                          {TIPE_DOKUMEN_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>
                        <input
                          type="text"
                          value={f.keterangan}
                          onChange={(e) => updatePendingMeta(idx, 'keterangan', e.target.value)}
                          placeholder="Keterangan (opsional)"
                          className="w-full text-[10px] border border-gray-200 rounded-md
                             px-1.5 py-1 bg-white text-gray-700 placeholder-gray-300
                             focus:outline-none focus:border-brand-400"
                        />
                      </div>
                    </div>
                  ))}
                </div>

                {/* Tombol upload semua pending */}
                <button
                  type="button"
                  onClick={uploadPendingFiles}
                  disabled={isUploadingAll}
                  className="w-full btn-primary py-2 text-sm"
                >
                  {isUploadingAll
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Mengupload {pendingFiles.length} foto...</>
                    : <><Upload className="w-4 h-4" /> Upload {pendingFiles.length} Foto Sekarang</>}
                </button>
              </div>
            )}

            {/* Tombol pilih foto baru */}
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,video/mp4"
              multiple
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="w-full border-2 border-dashed border-gray-200 rounded-xl py-5
                 flex items-center justify-center gap-2 text-gray-400 text-sm
                 hover:border-brand-400 hover:text-brand-500 hover:bg-brand-50
                 transition-all"
            >
              <Plus className="w-4 h-4" /> Pilih Foto Baru
            </button>

          </div>
        </div>

        {/* ── Actions ──────────────────────────────────────────────── */}
        <div className="flex justify-between pb-8">
          <button
            type="button"
            onClick={() => navigate(`/fkp/${id}`)}
            className="btn-secondary"
          >
            Batal
          </button>
          <button type="submit" disabled={isUpdating} className="btn-primary">
            {isUpdating
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Menyimpan...</>
              : 'Simpan Perubahan'}
          </button>
        </div>
      </form>

      {/* ── Modal Item ──────────────────────────────────────────────── */}
      <FkpItemFormModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        products={products}
        resetKey={resetKey}
        onSave={handleItemSave}
        isSaving={isSavingItem}
        // Jika edit, pass data existing ke modal untuk pre-fill
        initialData={editingItem ?? undefined}
      />
    </div>
  )
}