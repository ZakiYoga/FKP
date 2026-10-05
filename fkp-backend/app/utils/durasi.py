from datetime import datetime, timezone
from typing import Optional


def _as_utc(dt: datetime) -> datetime:
    # Kolom DB bisa mengembalikan naive datetime; mengurangkan naive dengan
    # aware akan raise TypeError, jadi keduanya dinormalisasi dulu.
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def hitung_durasi_detik(mulai: Optional[datetime], selesai: Optional[datetime]) -> Optional[int]:
    if not mulai or not selesai:
        return None
    return max(0, int((_as_utc(selesai) - _as_utc(mulai)).total_seconds()))


def format_durasi(total_detik: int) -> str:
    hari, sisa = divmod(total_detik, 86400)
    jam, sisa = divmod(sisa, 3600)
    menit = sisa // 60

    parts = []
    if hari:
        parts.append(f"{hari} hari")
    if jam:
        parts.append(f"{jam} jam")
    if not hari and menit:  # menit hanya relevan kalau durasi < 1 hari
        parts.append(f"{menit} menit")
    return " ".join(parts) or "Kurang dari 1 menit"