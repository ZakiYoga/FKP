import api from '@/lib/axios'
import type { InvoiceCreatePayload, InvoiceResponse, FkpDetail, ProsesFinancePayload } from '@/types'

// Endpoint di-mount di router fkp.py (prefix "/api/fkp"), bukan router terpisah.
export const financeApi = {
  // ── Terbitkan Invoice ────────────────────────────────────────────────────
  // Aktor: finance, admin_ho, superadmin. Guard BE: status === accepted,
  // resolusi.tipe_resolusi === potong_tagihan, persentase_kompensasi_disetujui
  // sudah diisi (dari Fase 1 buat_resolusi).
  //
  // [PENTING] nilai_nota_penjualan WAJIB — backend menghitung nilai_cashback
  // dari sini dan langsung menuliskannya ke PDF invoice. Endpoint ini JUGA
  // yang men-trigger transisi accepted → in_process untuk potong_tagihan.
  // Kalau resolusi.metode_penanganan_fisik === 'dimusnahkan', backend juga
  // mewajibkan dokumen 'berita_acara_pemusnahan_tukar_barang' sudah diupload
  // lebih dulu (lewat fkpApi.uploadAttachment) — kalau belum, request ini 400.
  terbitkanInvoice: async (fkpId: string, data: InvoiceCreatePayload): Promise<InvoiceResponse> => {
    const res = await api.post<InvoiceResponse>(`/fkp/${fkpId}/finance/invoice`, data)
    return res.data
  },

  // ── Download PDF Invoice ────────────────────────────────────────────────
  // [PENTING] Butuh header Authorization — pakai bersama
  // openAuthenticatedFile()/downloadAuthenticatedFile() dari
  // hooks/useAuthenticatedImage.ts, sama seperti warehouseApi.pdfPath().
  invoicePdfPath: (fkpId: string, docId: string): string =>
    `/api/fkp/${fkpId}/finance/invoice/${docId}`,

  // ── Konfirmasi Pembayaran (langkah kedua, setelah invoice terbit) ───────
  // Aktor: finance, admin_ho, superadmin. Guard BE: status === in_process,
  // resolusi.tipe_resolusi === potong_tagihan, nilai_cashback sudah ada
  // (otomatis benar kalau alurnya lewat terbitkanInvoice() dulu).
  // TIDAK men-trigger transisi status apa pun — murni menandai
  // diproses_finance = true.
  prosesFinance: async (fkpId: string, data: ProsesFinancePayload): Promise<FkpDetail> => {
    const res = await api.post<FkpDetail>(`/fkp/${fkpId}/finance/proses`, null, {
      params: data.catatan ? { catatan: data.catatan } : undefined,
    })
    return res.data
  },
}