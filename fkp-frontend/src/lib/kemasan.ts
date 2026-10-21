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

// ─── KEMASAN BESAR & ISI PER KEMASAN (katalog produk) ─────────────────────────
// Cermin aturan backend (JenisKemasan.KEMASAN_BESAR / ISI_TETAP dan
// tentukan_qty_per_kemasan() di models/product.py). Digerakkan KONSTANTA, bukan
// if/else per nama kemasan: menambah kemasan baru (mis. renceng kelak) cukup
// menambah ke KEMASAN_OPTIONS, KEMASAN_LABEL, KEMASAN_COLOR, dan KEMASAN_BESAR.
//
// Aturan:
//  - Satu SKU maksimal SATU kemasan besar; pcs boleh menyertai.
//  - Isi per kemasan: kemasan besar berisi tetap (zak = 1) tidak perlu diisi;
//    kemasan besar lain (ball/karton) WAJIB, bilangan bulat >= 2;
//    tanpa kemasan besar (pcs saja) = 1.
//  - berat_gr = berat per SATUAN TERKECIL (per zak untuk zak, per pcs untuk
//    ball/karton/pcs). Berat kemasan = isi x berat_gr (dihitung, tidak disimpan).
export const KEMASAN_BESAR: readonly KemasanValue[] = ['zak', 'ball', 'karton']
export const ISI_TETAP: Partial<Record<KemasanValue, number>> = { zak: 1 }
export const ISI_MINIMAL = 2

const adalahKemasanBesar = (k: string): boolean =>
  (KEMASAN_BESAR as readonly string[]).includes(k)

// Kemasan besar dalam daftar, unik dan terurut sesuai KEMASAN_OPTIONS.
export function kemasanBesarDari(list: readonly string[] | null | undefined): KemasanValue[] {
  return normalisasiKemasan(list).filter(adalahKemasanBesar)
}

// True bila admin harus mengisi isi per kemasan (ada kemasan besar yang isinya tidak tetap).
export function perluInputIsi(list: readonly string[] | null | undefined): boolean {
  const besar = kemasanBesarDari(list)
  return besar.length === 1 && ISI_TETAP[besar[0]] === undefined
}

export type HasilIsi = { ok: true; qty: number } | { ok: false; error: string }

// Padanan tentukan_qty_per_kemasan() di backend (pesan error disamakan).
export function tentukanQtyPerKemasan(
  list: readonly string[] | null | undefined,
  qty: number | null | undefined,
): HasilIsi {
  const besar = kemasanBesarDari(list)
  if (besar.length > 1) {
    return { ok: false, error: 'Satu SKU hanya boleh punya satu kemasan besar (zak/ball/karton).' }
  }
  if (besar.length === 0) return { ok: true, qty: 1 }
  const tetap = ISI_TETAP[besar[0]]
  if (tetap !== undefined) return { ok: true, qty: tetap }
  if (qty == null || !Number.isInteger(qty) || qty < ISI_MINIMAL) {
    return {
      ok: false,
      error: `Isi per ${KEMASAN_LABEL[besar[0]].toLowerCase()} wajib diisi (minimal ${ISI_MINIMAL} pcs).`,
    }
  }
  return { ok: true, qty }
}

// Menjaga maksimal satu kemasan besar saat user mengklik picker: kemasan besar
// yang BARU dipilih menggantikan kemasan besar sebelumnya. Kemasan non-besar
// (pcs) tidak tersentuh.
export function terapkanSatuKemasanBesar(
  sebelum: readonly string[],
  sesudah: readonly string[],
): KemasanValue[] {
  const besarBaru = kemasanBesarDari(sesudah)
  if (besarBaru.length <= 1) return normalisasiKemasan(sesudah)
  const dulu = new Set(sebelum)
  const dipilihSekarang = besarBaru.find((k) => !dulu.has(k)) ?? besarBaru[besarBaru.length - 1]
  return normalisasiKemasan(
    sesudah.filter((k) => !adalahKemasanBesar(k) || k === dipilihSekarang),
  )
}

// Satuan acuan berat_gr: zak untuk SKU zak, selain itu pcs.
export function satuanBerat(list: readonly string[] | null | undefined): string {
  return kemasanBesarDari(list).some((k) => ISI_TETAP[k] !== undefined) ? 'zak' : 'pcs'
}

// 10000 -> "10 kg", 500 -> "500 gr"
export function formatBerat(gr: number): string {
  if (gr >= 1000) return `${Number((gr / 1000).toFixed(3))} kg`
  return `${gr} gr`
}

// Berat satu kemasan besar (isi x berat per satuan); null bila tidak ada kemasan
// besar atau datanya belum lengkap.
export function beratKemasanGr(
  list: readonly string[] | null | undefined,
  beratGr: number | null | undefined,
  qty: number | null | undefined,
): number | null {
  if (!beratGr || beratGr <= 0) return null
  const hasil = tentukanQtyPerKemasan(list, qty)
  if (!hasil.ok || kemasanBesarDari(list).length === 0) return null
  return hasil.qty * beratGr
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