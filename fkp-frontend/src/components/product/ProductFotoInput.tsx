import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { ImagePlus, Trash2, Undo2, X } from 'lucide-react'

export const FOTO_MAX_BYTES = 2 * 1024 * 1024
const FOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp']

interface Props {
  /** foto_url produk saat ini (mode edit). */
  currentUrl?: string | null
  /** File baru yang dipilih, belum diunggah. */
  file: File | null
  onFileChange: (file: File | null) => void
  /** Foto lama ditandai untuk dihapus saat disimpan. */
  removed: boolean
  onRemovedChange: (removed: boolean) => void
  disabled?: boolean
}

export function ProductFotoInput({
  currentUrl, file, onFileChange, removed, onRemovedChange, disabled,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setPreview(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    e.target.value = '' // supaya memilih file yang sama dua kali tetap memicu change
    if (!f) return
    if (!FOTO_TYPES.includes(f.type)) {
      setError('Foto harus berformat JPG, PNG, atau WebP.')
      return
    }
    if (f.size > FOTO_MAX_BYTES) {
      setError('Ukuran foto maksimal 2 MB.')
      return
    }
    setError(null)
    onRemovedChange(false)
    onFileChange(f)
  }

  const tampil = preview ?? (removed ? null : currentUrl ?? null)
  const adaFotoLama = !!currentUrl

  return (
    <div>
      <p className="mb-1 text-sm font-semibold text-gray-700">Foto Produk</p>
      <div className="flex items-center gap-4">
        <div className="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-gray-200 bg-gray-50">
          {tampil ? (
            <img src={tampil} alt="Foto produk" className="h-full w-full object-cover" />
          ) : (
            <ImagePlus className="h-8 w-8 text-gray-300" aria-hidden="true" />
          )}
        </div>

        <div className="flex flex-col items-start gap-2">
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={onPick}
            disabled={disabled}
          />
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => inputRef.current?.click()}
            disabled={disabled}
          >
            <ImagePlus className="w-3.5 h-3.5" />
            {tampil ? 'Ganti foto' : 'Pilih foto'}
          </button>

          {file ? (
            <button
              type="button"
              className="text-xs text-gray-500 hover:text-gray-700 inline-flex items-center gap-1"
              onClick={() => { onFileChange(null); setError(null) }}
              disabled={disabled}
            >
              <X className="w-3 h-3" /> Batalkan pilihan
            </button>
          ) : adaFotoLama && !removed ? (
            <button
              type="button"
              className="text-xs text-red-600 hover:text-red-700 inline-flex items-center gap-1"
              onClick={() => onRemovedChange(true)}
              disabled={disabled}
            >
              <Trash2 className="w-3 h-3" /> Hapus foto
            </button>
          ) : adaFotoLama && removed ? (
            <button
              type="button"
              className="text-xs text-gray-500 hover:text-gray-700 inline-flex items-center gap-1"
              onClick={() => onRemovedChange(false)}
              disabled={disabled}
            >
              <Undo2 className="w-3 h-3" /> Batalkan hapus
            </button>
          ) : null}

          <p className="text-xs text-gray-400">JPG, PNG, atau WebP. Maksimal 2 MB.</p>
        </div>
      </div>
      {error && <p className="mt-1.5 text-xs text-red-600">{error}</p>}
    </div>
  )
}