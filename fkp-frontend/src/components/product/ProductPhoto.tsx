import { useState } from 'react'
import { cn } from '@/lib/utils'
import { Modal } from '@/components/ui/Modal'
import type { Product } from '@/types'

export const PRODUCT_PLACEHOLDER_SRC = `${import.meta.env.BASE_URL}products/placeholder-product.webp`

const THUMB_BOX =
  'block h-16 w-16 shrink-0 overflow-hidden rounded-lg border border-gray-200 bg-gray-50 ' +
  'dark:border-gray-700 dark:bg-gray-800'

interface ProductThumbProps {
  src?: string | null
  alt: string
  onOpen: () => void
}

/**
 * Thumbnail kecil di kartu. Ada foto: bisa diklik (membuka modal). Tidak ada foto,
 * atau file gagal dimuat (404 / sudah terhapus): placeholder, tidak bisa diklik.
 */
export function ProductThumb({ src, alt, onOpen }: ProductThumbProps) {
  // Menyimpan src yang gagal (bukan boolean) supaya otomatis normal lagi saat foto diganti.
  const [brokenSrc, setBrokenSrc] = useState<string | null>(null)

  if (!src || brokenSrc === src) {
    return (
      <span className={THUMB_BOX}>
        <img
          src={PRODUCT_PLACEHOLDER_SRC}
          alt="placeholder produk"
          aria-hidden="true"
          className="h-full w-full p-1.5 object-cover"
        />
      </span>
    )
  }

  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={`Perbesar foto ${alt}`}
      title="Klik untuk memperbesar"
      className={cn(
        THUMB_BOX,
        'cursor-zoom-in focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500',
      )}
    >
      <img
        src={src}
        alt={alt}
        loading="lazy"
        onError={() => setBrokenSrc(src)}
        className="h-full w-full object-cover"
      />
    </button>
  )
}

/** Modal foto besar. Dibuka bila `product` terisi; hanya dipanggil untuk produk yang punya foto. */
export function ProductPhotoModal({
  product,
  onClose,
}: {
  product: Product | null
  onClose: () => void
}) {
  return (
    <Modal
      isOpen={!!product}
      onClose={onClose}
      title={product?.nama_produk ?? 'Foto produk'}
      size="md"
    >
      {product?.foto_url && (
        <div className="space-y-2">
          <img
            src={product.foto_url}
            alt={`Foto ${product.nama_produk}`}
            className="mx-auto max-h-[70vh] w-auto max-w-full rounded-lg object-contain"
          />
          <p className="text-center text-xs font-mono text-gray-400">{product.kode_produk}</p>
        </div>
      )}
    </Modal>
  )
}