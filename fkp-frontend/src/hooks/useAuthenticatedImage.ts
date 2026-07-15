import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/authStore"; // ganti sesuai lokasi store token kamu

interface UseAuthenticatedImageResult {
  src: string | null;
  isLoading: boolean;
  error: string | null;
}

// [FIX] URL yang dikirim backend sekarang berupa path relatif, mis.
// "/api/fkp/{fkp_id}/attachments/{attachment_id}/file". Kalau frontend &
// backend beda origin (tidak lewat proxy), fetch(url) tanpa base akan
// nyasar ke origin frontend sendiri. Sesuaikan VITE_API_URL di .env.
const API_BASE = import.meta.env.VITE_API_URL ?? "";

// Cache in-memory sederhana supaya gambar yang sama tidak di-fetch berulang
// tiap kali komponen remount (misal buka-tutup lightbox).
const blobUrlCache = new Map<string, string>();

export function useAuthenticatedImage(url: string | null | undefined): UseAuthenticatedImageResult {
  const [src, setSrc] = useState<string | null>(url ? blobUrlCache.get(url) ?? null : null);
  const [isLoading, setIsLoading] = useState(!!url && !blobUrlCache.has(url));
  const [error, setError] = useState<string | null>(null);
  const token = useAuthStore((s) => s.token); // ganti sesuai nama field token di store kamu

  useEffect(() => {
    if (!url) {
      setSrc(null);
      setIsLoading(false);
      return;
    }

    // Sudah ada di cache -> langsung pakai, skip fetch.
    if (blobUrlCache.has(url)) {
      setSrc(blobUrlCache.get(url)!);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    const controller = new AbortController();

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        // [FIX] prepend API_BASE karena `url` dari backend adalah path relatif.
        const res = await fetch(`${API_BASE}${url}`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });

        if (res.status === 401) {
          // Token expired/invalid — sesuaikan dengan flow refresh/redirect
          // login yang sudah kamu punya di tempat lain.
          throw new Error("Sesi berakhir, silakan login ulang.");
        }
        if (res.status === 403) {
          throw new Error("Tidak punya akses ke dokumen ini.");
        }
        if (!res.ok) {
          throw new Error(`Gagal memuat gambar (${res.status})`);
        }

        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        blobUrlCache.set(url!, objectUrl);
        if (!cancelled) {
          setSrc(objectUrl);
        }
      } catch (err) {
        if (!cancelled && (err as Error).name !== "AbortError") {
          setError((err as Error).message);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
      controller.abort();
      // NOTE: object URL sengaja TIDAK di-revoke di sini karena disimpan
      // di cache global untuk dipakai ulang. Cleanup total dilakukan lewat
      // clearAuthenticatedImageCache() saat logout.
    };
  }, [url, token]);

  return { src, isLoading, error };
}

// Panggil ini saat logout supaya blob URL lama tidak nyangkut di memori
// dan tidak dipakai user berikutnya yang login di sesi/browser yang sama.
export function clearAuthenticatedImageCache() {
  blobUrlCache.forEach((objectUrl) => URL.revokeObjectURL(objectUrl));
  blobUrlCache.clear();
}

// [BARU] Untuk kasus <a href={att.url} target="_blank"> — navigasi browser
// biasa TIDAK bisa kirim header Authorization, jadi klik langsung ke URL
// endpoint akan selalu gagal (401). Ganti pemakaian <a href> dengan
// onClick={() => openAuthenticatedFile(att.url, token)} sebagai gantinya.
export async function openAuthenticatedFile(url: string, token: string | null) {
  try {
    let objectUrl = blobUrlCache.get(url);
    if (!objectUrl) {
      const res = await fetch(`${API_BASE}${url}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Gagal memuat file (${res.status})`);
      const blob = await res.blob();
      objectUrl = URL.createObjectURL(blob);
      blobUrlCache.set(url, objectUrl);
    }
    window.open(objectUrl, "_blank", "noopener,noreferrer");
  } catch (err) {
    console.error("Gagal membuka file:", err);
    alert("Gagal membuka file. Coba lagi.");
  }
}

// [BARU] Untuk kasus <a href={att.url} download> — atribut `download` di
// browser JUGA memicu navigasi/fetch native tanpa header Authorization,
// jadi sama rusaknya dengan target="_blank". Fetch dulu jadi blob, baru
// trigger download dari blob URL lewat anchor sementara.
export async function downloadAuthenticatedFile(url: string, token: string | null, filename: string) {
  try {
    let objectUrl = blobUrlCache.get(url);
    if (!objectUrl) {
      const res = await fetch(`${API_BASE}${url}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Gagal mengunduh file (${res.status})`);
      const blob = await res.blob();
      objectUrl = URL.createObjectURL(blob);
      blobUrlCache.set(url, objectUrl);
    }
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (err) {
    console.error("Gagal mengunduh file:", err);
    alert("Gagal mengunduh file. Coba lagi.");
  }
}