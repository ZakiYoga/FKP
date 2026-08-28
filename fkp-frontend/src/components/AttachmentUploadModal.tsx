import { useRef, useState } from 'react'
import { Upload, FileText, Image as ImageIcon, X } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { TIPE_DOKUMEN_OPTIONS } from '@/constants/fkpAttachment'
import toast from 'react-hot-toast'

interface Props {
    isOpen: boolean
    onClose: () => void
    onUpload: (file: File, tipeDokumen: string, keterangan: string) => Promise<void>
    isUploading?: boolean
    /**
     * Kalau diisi, dropdown tipe dokumen dikunci ke nilai ini (tidak bisa
     * diubah user) — dipakai untuk alur spesifik seperti upload BA
     * Pemusnahan & Tukar Barang yang sudah ditandatangani, supaya user
     * tidak salah pilih tipe dokumen lain.
     */
    lockedTipeDokumen?: string
    /** Judul modal — default "Upload Dokumen" */
    title?: string
    /** Teks bantuan di atas form, opsional */
    helperText?: string
}

const ACCEPTED_TYPES = 'image/jpeg,image/png,image/webp,application/pdf'
const MAX_SIZE_MB = 10

export function AttachmentUploadModal({
    isOpen, onClose, onUpload, isUploading = false,
    lockedTipeDokumen, title = 'Upload Dokumen', helperText,
}: Props) {
    const [file, setFile] = useState<File | null>(null)
    const [preview, setPreview] = useState<string | null>(null)
    const [tipeDokumen, setTipeDokumen] = useState(lockedTipeDokumen ?? '')
    const [keterangan, setKeterangan] = useState('')
    const fileRef = useRef<HTMLInputElement>(null)

    const isPdf = file?.type === 'application/pdf'

    const resetAndClose = () => {
        if (preview) URL.revokeObjectURL(preview)
        setFile(null)
        setPreview(null)
        setTipeDokumen(lockedTipeDokumen ?? '')
        setKeterangan('')
        onClose()
    }

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0]
        if (!f) return
        if (f.size > MAX_SIZE_MB * 1024 * 1024) {
            toast.error(`Ukuran file maksimal ${MAX_SIZE_MB}MB.`)
            return
        }
        if (preview) URL.revokeObjectURL(preview)
        setFile(f)
        setPreview(f.type === 'application/pdf' ? null : URL.createObjectURL(f))
    }

    const handleSubmit = async () => {
        if (!file) {
            toast.error('Pilih file terlebih dahulu.')
            return
        }
        if (!tipeDokumen) {
            toast.error('Pilih tipe dokumen terlebih dahulu.')
            return
        }
        await onUpload(file, tipeDokumen, keterangan)
        resetAndClose()
    }

    return (
        <Modal isOpen={isOpen} onClose={resetAndClose} title={title} size="md">
            <div className="space-y-4">
                {helperText && (
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
                        {helperText}
                    </div>
                )}

                <Select
                    label="Tipe Dokumen"
                    required
                    value={tipeDokumen}
                    onChange={(e) => setTipeDokumen(e.target.value)}
                    disabled={!!lockedTipeDokumen}
                >
                    <option value="">— Pilih tipe dokumen —</option>
                    {TIPE_DOKUMEN_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                </Select>

                {/* ── File picker / preview ─────────────────────────────── */}
                {!file ? (
                    <>
                        <input
                            ref={fileRef}
                            type="file"
                            accept={ACCEPTED_TYPES}
                            onChange={handleFileChange}
                            className="hidden"
                        />
                        <button
                            type="button"
                            onClick={() => fileRef.current?.click()}
                            className="w-full border-2 border-dashed border-gray-200 rounded-xl py-8
                                       flex flex-col items-center justify-center gap-2 text-gray-400 text-sm
                                       hover:border-brand-400 hover:text-brand-500 hover:bg-brand-50 transition-all"
                        >
                            <Upload className="w-5 h-5" />
                            Pilih foto/scan atau file PDF
                            <span className="text-[11px] text-gray-300">JPG, PNG, WebP, atau PDF — maks {MAX_SIZE_MB}MB</span>
                        </button>
                    </>
                ) : (
                    <div className="relative border border-gray-200 rounded-xl overflow-hidden">
                        <button
                            type="button"
                            onClick={() => {
                                if (preview) URL.revokeObjectURL(preview)
                                setFile(null)
                                setPreview(null)
                            }}
                            className="absolute top-2 right-2 bg-red-500 text-white rounded-lg p-1.5 z-10"
                        >
                            <X className="w-3.5 h-3.5" />
                        </button>
                        {isPdf ? (
                            <div className="flex items-center gap-3 p-4 bg-gray-50">
                                <FileText className="w-8 h-8 text-red-500 shrink-0" />
                                <div className="min-w-0">
                                    <p className="text-sm font-medium text-gray-800 truncate">{file.name}</p>
                                    <p className="text-xs text-gray-400">{(file.size / 1024 / 1024).toFixed(2)} MB · PDF</p>
                                </div>
                            </div>
                        ) : (
                            <div className="flex items-center gap-3 p-3 bg-gray-50">
                                {preview && (
                                    <img src={preview} alt="preview" className="w-16 h-16 object-cover rounded-lg border border-gray-200" />
                                )}
                                <div className="min-w-0">
                                    <p className="text-sm font-medium text-gray-800 truncate flex items-center gap-1.5">
                                        <ImageIcon className="w-3.5 h-3.5 text-gray-400" /> {file.name}
                                    </p>
                                    <p className="text-xs text-gray-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                <Textarea
                    label="Keterangan (opsional)"
                    rows={2}
                    value={keterangan}
                    onChange={(e) => setKeterangan(e.target.value)}
                    placeholder="Contoh: BA ditandatangani APSM & distributor tanggal 20 Agustus 2026"
                />

                <div className="flex gap-2 justify-end pt-2">
                    <button onClick={resetAndClose} className="btn-secondary" disabled={isUploading}>
                        Batal
                    </button>
                    <button onClick={handleSubmit} className="btn-primary" disabled={isUploading || !file}>
                        {isUploading
                            ? <span className="flex items-center gap-2">
                                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                Mengupload...
                            </span>
                            : <span className="flex items-center gap-2"><Upload className="w-4 h-4" /> Upload</span>
                        }
                    </button>
                </div>
            </div>
        </Modal>
    )
}