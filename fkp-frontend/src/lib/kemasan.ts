// ─── SUMBER KONSTANTA KEMASAN (katalog produk) ────────────────────────────────
// Satu-satunya daftar nilai kemasan yang valid di frontend. Urutan = urutan
// tampil (cermin JenisKemasan.ALL di backend). Pakai ini untuk schema zod,
// filter, badge, dan picker; jangan membuat daftar ganda.
export const KEMASAN_OPTIONS = ['zak', 'ball', 'karton', 'pcs'] as const
export type KemasanValue = (typeof KEMASAN_OPTIONS)[number]

export const KEMASAN_LABEL: Record<KemasanValue, string> = {
  zak: 'Zak',
  ball: 'Ball',
  karton: 'Karton',
  pcs: 'Pcs',
}

// Kelas badge. Dipakai juga picker sebagai gaya "terpilih" (border + latar + teks).
export const KEMASAN_COLOR: Record<KemasanValue, string> = {
  zak: 'bg-orange-50 text-orange-700 border-orange-200',
  ball: 'bg-green-50 text-green-700 border-green-200',
  karton: 'bg-blue-50 text-blue-700 border-blue-200',
  pcs: 'bg-yellow-50 text-yellow-700 border-yellow-200',
}

// Menyaring nilai tak dikenal, membuang duplikat, dan mengurutkan sesuai
// KEMASAN_OPTIONS (bukan urutan klik / urutan input).
export function normalisasiKemasan(list: readonly string[] | null | undefined): KemasanValue[] {
  const ada = new Set(list ?? [])
  return KEMASAN_OPTIONS.filter((k) => ada.has(k))
}

// Bandingkan dua daftar kemasan sebagai himpunan (urutan diabaikan).
export function kemasanSama(a: readonly string[], b: readonly string[]): boolean {
  const sa = new Set(a)
  const sb = new Set(b)
  return sa.size === sb.size && [...sa].every((k) => sb.has(k))
}

// ─── ATURAN FKP (kelompok kemasan, default, dst.) ─────────────────────────────

// Kelompok kemasan: 'pcs' vs 'non_pcs' (zak/ball/karton). Satu FKP tidak boleh campur.
// Daftar 'pcs' adalah salinan dari backend — ubah di sini saja, jangan sebar string 'pcs'.
export const KEMASAN_PCS = ['pcs'] as const
export type KelompokKemasan = 'pcs' | 'non_pcs'

export const kelompokKemasan = (k: string): KelompokKemasan =>
  (KEMASAN_PCS as readonly string[]).includes(k) ? 'pcs' : 'non_pcs'

// null = kosong atau campuran
export function kelompokFkp(
  items: { jenis_kemasan?: string | null }[],
): KelompokKemasan | null {
  const set = new Set(
    items.filter((i) => i.jenis_kemasan).map((i) => kelompokKemasan(i.jenis_kemasan!)),
  )
  return set.size === 1 ? [...set][0] : null
}

export interface CampurKemasan {
  itemPcs: string[]
  itemNon: string[]
  pesan: string
}

// namaProduk: map product_id -> nama produk
export function cekCampurKemasan(
  items: { product_id: string; jenis_kemasan?: string | null }[],
  namaProduk: Record<string, string>,
): CampurKemasan | null {
  const pcs = items.filter((i) => i.jenis_kemasan && kelompokKemasan(i.jenis_kemasan) === 'pcs')
  const non = items.filter((i) => i.jenis_kemasan && kelompokKemasan(i.jenis_kemasan) === 'non_pcs')
  if (!pcs.length || !non.length) return null

  const nama = (id: string) => namaProduk[id] ?? id
  return {
    itemPcs: [...new Set(pcs.map((i) => nama(i.product_id)))],
    itemNon: [...new Set(non.map((i) => `${nama(i.product_id)} (${i.jenis_kemasan})`))],
    pesan:
      'Satu FKP tidak boleh memuat kemasan pcs bersamaan dengan zak/ball/karton, karena penanganannya berbeda. ' +
      'Pisahkan menjadi dua FKP: satu untuk item pcs dan satu untuk item zak/ball/karton.',
  }
}

// Kemasan yang boleh dipilih untuk sebuah produk, bersumber dari backend
// (kemasan_tersedia). Fallback ke kemasan utama (jenis_kemasan) bila field itu
// kosong/tidak ada (data lama). null = produk belum dipilih atau tidak ada data
// sama sekali; pemanggil memutuskan apa yang ditampilkan.
export function kemasanTersediaProduk(
  produk?: { jenis_kemasan?: string | null; kemasan_tersedia?: string[] | null } | null,
): string[] | null {
  if (!produk) return null
  if (produk.kemasan_tersedia?.length) return produk.kemasan_tersedia
  return produk.jenis_kemasan ? [produk.jenis_kemasan] : null
}

// Urutan preferensi kemasan default saat produk punya lebih dari satu kemasan:
// zak/karton/ball didahulukan, pcs paling akhir (mis. Sakti 200gr -> karton,
// Sakti 500gr/1kg -> ball). User tetap bisa mengganti manual.
export const URUTAN_KEMASAN_DEFAULT = ['zak', 'karton', 'ball', 'pcs'] as const

// Memilih kemasan default untuk produk yang baru dipilih.
// - Hanya satu kemasan yang cocok -> pakai itu.
// - Beberapa -> ambil yang paling didahulukan menurut URUTAN_KEMASAN_DEFAULT.
// - Bila FKP sudah punya kelompok (pcs / non_pcs), hanya kemasan sekelompok yang
//   dipertimbangkan, karena kelompok lain tidak boleh dicampur.
// Mengembalikan null bila tidak ada kandidat.
export function pilihKemasanDefault(
  list: string[] | null,
  kelompokAda: KelompokKemasan | null,
): string | null {
  if (!list || list.length === 0) return null
  const cocok = kelompokAda ? list.filter((k) => kelompokKemasan(k) === kelompokAda) : list
  if (cocok.length === 0) return null
  if (cocok.length === 1) return cocok[0]
  const rank = (k: string) => {
    const i = (URUTAN_KEMASAN_DEFAULT as readonly string[]).indexOf(k)
    return i === -1 ? 99 : i
  }
  return [...cocok].sort((a, b) => rank(a) - rank(b))[0]
}