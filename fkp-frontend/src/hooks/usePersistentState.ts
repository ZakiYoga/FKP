import { useEffect, useState } from 'react'

/**
 * State React yang otomatis tersimpan di `localStorage`, sehingga nilainya
 * tetap ada setelah halaman di-refresh atau browser ditutup lalu dibuka lagi.
 *
 * Cara kerja:
 * - Saat komponen pertama kali dibuat, nilai dibaca dari `localStorage`
 *   (lazy initializer, jadi tidak ada kedipan nilai awal sebelum nilai tersimpan dimuat).
 * - Setiap kali nilai berubah, nilai terbaru ditulis kembali ke `localStorage`.
 * - Jika `localStorage` tidak tersedia (mode privat, diblokir, penuh) atau isinya
 *   rusak, hook tetap berjalan seperti `useState` biasa memakai `initialValue`.
 *
 * Catatan:
 * - Nilai disimpan sebagai JSON, jadi hanya tipe yang bisa di-serialisasi
 *   (boolean, angka, string, array, objek biasa) yang aman dipakai.
 * - Jangan simpan data sensitif (token, password) di sini.
 * - Nilai tidak disinkronkan antar-tab secara real-time; tab lain baru membaca
 *   nilai terbaru saat dimuat ulang.
 *
 * @typeParam T - Tipe nilai yang disimpan.
 * @param key - Kunci unik di `localStorage`, mis. `'sidebar-collapsed'`.
 * @param initialValue - Nilai awal bila belum ada data tersimpan atau data tidak terbaca.
 * @returns Tuple `[value, setValue]`, bentuknya sama dengan `useState`
 *          (`setValue` juga menerima fungsi updater, mis. `setValue(v => !v)`).
 *
 * @example
 * const [collapsed, setCollapsed] = usePersistentState('sidebar-collapsed', false)
 * <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
 */
export function usePersistentState<T>(key: string, initialValue: T) {
    const [value, setValue] = useState<T>(() => {
        try {
            const raw = localStorage.getItem(key)
            return raw !== null ? (JSON.parse(raw) as T) : initialValue
        } catch {
            // localStorage diblokir atau isinya bukan JSON valid
            return initialValue
        }
    })

    // Tulis ulang ke penyimpanan setiap kali nilai (atau kunci) berubah
    useEffect(() => {
        try {
            localStorage.setItem(key, JSON.stringify(value))
        } catch {
            // abaikan jika penyimpanan penuh atau diblokir; state tetap berjalan di memori
        }
    }, [key, value])

    return [value, setValue] as const
}