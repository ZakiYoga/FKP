// Nomor HP disimpan di BE dalam format 62… (mis. 628123456789).
// Di form, nomor ditampilkan tanpa awalan setelah label "+62".

// "+62812…" / "62812…" / "0812…" / "812…" -> "812…"
export const toLocalPhone = (v: string | null | undefined): string =>
  (v ?? '').replace(/\D/g, '').replace(/^(62|0)/, '')

// "812…" -> "62812…" (string kosong tetap kosong)
export const toStoredPhone = (local: string): string => (local ? `62${local}` : '')