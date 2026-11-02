import { useCallback, useEffect, useState } from 'react'

const PREFIX = 'cooldown:'

function readUntil(key: string): number {
    try {
        return Number(sessionStorage.getItem(PREFIX + key)) || 0
    } catch {
        return 0 // storage diblokir (mode privat ketat): cooldown hanya hidup di memori
    }
}

/**
 * Mulai cooldown untuk `key` tanpa hook (mis. di handler sukses halaman registrasi:
 * server sudah mengirim email verifikasi saat itu, jadi tombol "kirim ulang" di
 * halaman lain tidak boleh langsung aktif). Return: timestamp berakhirnya (ms).
 */
export function startCooldownFor(key: string, seconds: number): number {
    const end = Date.now() + seconds * 1000
    try {
        sessionStorage.setItem(PREFIX + key, String(end))
    } catch {
        // abaikan: storage diblokir
    }
    return end
}

/**
 * Hitung mundur untuk tombol "kirim ulang".
 *
 * - Waktu selesai disimpan sebagai timestamp di sessionStorage, jadi muat ulang
 *   halaman tidak mengosongkan cooldown.
 * - Per `key` (mis. email): salah ketik alamat bisa langsung diperbaiki tanpa
 *   menunggu cooldown alamat yang salah.
 * - Sisa waktu dihitung dari Date.now(), bukan dikurangi tiap detik, sehingga
 *   tetap akurat ketika tab di latar belakang dan timer-nya ditahan browser.
 *
 * Ini hanya UX. Batas sebenarnya harus ada di server.
 */
export function useCooldown(key: string | null) {
    const [until, setUntil] = useState(0)
    const [now, setNow] = useState(() => Date.now())

    // Sinkronkan ketika key berubah (user mengganti email)
    useEffect(() => {
        setUntil(key ? readUntil(key) : 0)
        setNow(Date.now())
    }, [key])

    const remaining = Math.max(0, Math.ceil((until - now) / 1000))
    const isCoolingDown = remaining > 0

    useEffect(() => {
        if (!isCoolingDown) return
        const id = window.setInterval(() => setNow(Date.now()), 1000)
        return () => window.clearInterval(id)
    }, [isCoolingDown])

    // forKey: dipakai bila key baru diketahui setelah request sukses
    // (mis. email yang dikirim, sedangkan hook belum dirender ulang dengan key itu).
    const start = useCallback(
        (seconds: number, forKey?: string) => {
            const k = forKey ?? key
            if (!k) return
            const end = startCooldownFor(k, seconds)
            setUntil(end)
            setNow(Date.now())
        },
        [key],
    )

    return { remaining, isCoolingDown, start }
}
