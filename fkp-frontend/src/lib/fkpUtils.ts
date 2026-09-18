export const UUID_REGEX =
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export function isUuid(value: string): boolean {
    return UUID_REGEX.test(value.trim())
}

export function extractUuid(raw: string): string {
    const trimmed = raw.trim()
    const match = trimmed.match(
        /[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/i,
    )
    return match ? match[0] : trimmed
}

export function formatDate(iso: string | null): string {
    if (!iso) return '-'
    return new Intl.DateTimeFormat('id-ID', {
        day: '2-digit', month: 'long', year: 'numeric',
    }).format(new Date(iso))
}

// ─── Gate Persetujuan Direktur ──────────────────────────────────────────────
// Cermin dari app/models/fkp.py::butuh_approval_direktur() di backend.
// Dipakai FE HANYA untuk preview/label sebelum submit — keputusan final
// (dan validasi sesungguhnya) tetap di backend. Kalau angka batas berubah
// di backend, update juga di sini supaya preview tidak menyesatkan.
export const BATAS_QTY_DIREKTUR = 10 // zak — strictly LEBIH DARI angka ini butuh TTD Direktur

export const TIPE_RESOLUSI_KENA_GATE_DIREKTUR = ['tukar_barang', 'potong_tagihan'] as const

export function butuhApprovalDirektur(
    tipeResolusi: string | null | undefined,
    totalQty: number,
): boolean {
    if (!tipeResolusi) return false
    if (!TIPE_RESOLUSI_KENA_GATE_DIREKTUR.includes(tipeResolusi as never)) return false
    return totalQty > BATAS_QTY_DIREKTUR
}