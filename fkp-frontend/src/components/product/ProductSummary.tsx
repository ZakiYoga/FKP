import type { ReactNode } from 'react'
import { Boxes, Package, Scale, Tag } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { ProductThumb } from '@/components/product/ProductPhoto'
import {
  KEMASAN_LABEL,
  beratKemasanGr,
  formatBerat,
  kemasanBesarDari,
  normalisasiKemasan,
  perluInputIsi,
  satuanBerat,
} from '@/lib/kemasan'
import { PRODUCT_CLASS_LABEL } from '@/types'
import type { Product } from '@/types'

function InfoLine({
  icon: Icon, title, children,
}: { icon: LucideIcon; title?: string; children: ReactNode }) {
  return (
    <span className="flex min-w-0 items-center gap-1.5" title={title}>
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <span className="truncate">{children}</span>
    </span>
  )
}

/**
 * Ringkasan produk untuk slot `meta` EntityCard: thumbnail di kiri; kemasan, Class,
 * berat per satuan, dan isi kemasan besar di kanan. Markup sengaja hanya <span>
 * (tanpa <div>) karena slot meta dirender di dalam <span>.
 */
export function ProductSummary({
  product,
  onOpenFoto,
}: {
  product: Product
  onOpenFoto: () => void
}) {
  const kemasan = normalisasiKemasan(product.kemasan_tersedia)
  const besar = kemasanBesarDari(kemasan)[0]
  const beratBesar = perluInputIsi(kemasan)
    ? beratKemasanGr(kemasan, product.berat_gr, product.qty_per_kemasan)
    : null
  // Baris isi hanya untuk ball/karton yang isinya sudah terisi. Zak/pcs-saja tidak punya.
  const teksIsi =
    besar && beratBesar !== null && !!product.qty_per_kemasan
      ? `1 ${KEMASAN_LABEL[besar].toLowerCase()} = ${product.qty_per_kemasan} pcs · ${formatBerat(beratBesar)}`
      : null

  return (
    <span className="flex items-center gap-3">
      <ProductThumb src={product.foto_url} alt={product.nama_produk} onOpen={onOpenFoto} />
      <span className="flex min-w-0 flex-col gap-1 text-gray-500 dark:text-gray-400">
        <InfoLine icon={Package}>
          {kemasan.length > 0
            ? kemasan.map((k) => KEMASAN_LABEL[k]).join(' · ')
            : 'Belum ada kemasan'}
        </InfoLine>
        <InfoLine icon={Tag}>Class: {PRODUCT_CLASS_LABEL[product.class]}</InfoLine>
        {!!product.berat_gr && (
          <InfoLine icon={Scale}>
            {formatBerat(product.berat_gr)} / {satuanBerat(kemasan)}
          </InfoLine>
        )}
        {teksIsi && (
          <InfoLine icon={Boxes} title={teksIsi}>
            {teksIsi}
          </InfoLine>
        )}
      </span>
    </span>
  )
}