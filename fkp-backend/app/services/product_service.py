import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.uploads import FOTO_PRODUK_DIR, FOTO_PRODUK_URL_PREFIX
from app.models.product import (
    JenisKemasan, ProductCatalog, ProductKemasan, tentukan_qty_per_kemasan,
)
from app.schemas.product import ProductCreate, ProductUpdate


def _urutan(k: str) -> int:
    return JenisKemasan.ALL.index(k) if k in JenisKemasan.ALL else len(JenisKemasan.ALL)


def _validasi_jenis_kemasan(nilai: str) -> None:
    if nilai not in JenisKemasan.ALL:
        raise HTTPException(
            status_code=400,
            detail=f"Jenis kemasan harus salah satu dari: {', '.join(JenisKemasan.ALL)}.",
        )


# ---------------------------------------------------------------------------
# Kemasan
# ---------------------------------------------------------------------------

async def get_kemasan(
    db: AsyncSession, product_ids: List[uuid.UUID]
) -> Dict[uuid.UUID, List[str]]:
    """
    Kemasan yang tersedia per produk, urut sesuai JenisKemasan.ALL.
    Sumber tunggal untuk dropdown FE dan validasi BE (set_jenis_kemasan di
    fkp_service). Produk yang belum punya baris ProductKemasan (masa transisi)
    memakai ProductCatalog.jenis_kemasan. Produk tanpa kemasan sama sekali tidak
    muncul di hasil.
    """
    if not product_ids:
        return {}

    r = await db.execute(
        select(ProductKemasan.product_id, ProductKemasan.jenis_kemasan)
        .where(ProductKemasan.product_id.in_(product_ids))
    )
    hasil: Dict[uuid.UUID, set] = {}
    for pid, k in r.all():
        hasil.setdefault(pid, set()).add(k)

    tanpa_data = [p for p in product_ids if p not in hasil]
    if tanpa_data:
        r2 = await db.execute(
            select(ProductCatalog.id, ProductCatalog.jenis_kemasan)
            .where(ProductCatalog.id.in_(tanpa_data))
        )
        for pid, k in r2.all():
            if k:
                hasil[pid] = {k}

    return {pid: sorted(v, key=_urutan) for pid, v in hasil.items()}


async def _terapkan_kemasan(
    product: ProductCatalog, kemasan: List[str], qty: Optional[int], db: AsyncSession
) -> List[str]:
    """
    Sinkronkan ProductKemasan dengan daftar `kemasan`, isi kolom lama
    ProductCatalog.jenis_kemasan dengan kemasan utama (yang pertama menurut
    JenisKemasan.ALL), dan tetapkan ProductCatalog.qty_per_kemasan lewat
    tentukan_qty_per_kemasan() (zak/pcs-saja = 1, ball/karton wajib >= 2, maksimal
    satu kemasan besar). Kemasan dan isi adalah satu kesatuan. TIDAK commit;
    pemanggil yang commit supaya bisa digabung dalam satu transaksi. Produk harus
    sudah punya id dan sudah di-flush bila baru.
    """
    baru = set(kemasan)
    if not baru:
        raise HTTPException(
            status_code=400,
            detail="Minimal satu kemasan harus dipilih untuk produk ini.",
        )
    for k in baru:
        _validasi_jenis_kemasan(k)
    urut = sorted(baru, key=_urutan)

    # Hitung isi SEBELUM menyentuh ProductKemasan, supaya input yang ditolak tidak
    # meninggalkan perubahan setengah jalan di session.
    try:
        qty_final = tentukan_qty_per_kemasan(urut, qty)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    r = await db.execute(
        select(ProductKemasan).where(ProductKemasan.product_id == product.id)
    )
    lama = {row.jenis_kemasan: row for row in r.scalars().all()}

    for k, row in lama.items():
        if k not in baru:
            await db.delete(row)
    for k in urut:
        if k not in lama:
            db.add(ProductKemasan(product_id=product.id, jenis_kemasan=k))

    product.jenis_kemasan = urut[0]
    product.qty_per_kemasan = qty_final
    db.add(product)
    return urut


async def set_kemasan(
    product_id: uuid.UUID, kemasan: List[str], qty: Optional[int], db: AsyncSession
) -> List[str]:
    """
    Menetapkan daftar kemasan sebuah produk beserta isi per kemasannya (dipakai
    layar admin produk). Daftar lama diganti seluruhnya; qty_per_kemasan ikut
    diganti bersamaan (aturan di tentukan_qty_per_kemasan()). Item FKP lama tidak
    terpengaruh karena jenis_kemasan di FkpItem adalah snapshot, tetapi draft FKP
    yang memakai kemasan yang dihapus akan ditolak saat disubmit (revalidasi di
    submit_fkp).
    """
    product = await get_product(product_id, db)
    urut = await _terapkan_kemasan(product, kemasan, qty, db)
    await db.commit()
    return urut


# ---------------------------------------------------------------------------
# Produk
# ---------------------------------------------------------------------------

async def list_products(
    db: AsyncSession,
    jenis_kemasan: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[ProductCatalog]:
    query = select(ProductCatalog)
    if jenis_kemasan:
        _validasi_jenis_kemasan(jenis_kemasan)
        # Mengikuti aturan get_kemasan: ProductKemasan jika ada, kolom lama sebagai fallback.
        punya_kemasan = select(ProductKemasan.product_id)
        query = query.where(
            or_(
                ProductCatalog.id.in_(
                    punya_kemasan.where(ProductKemasan.jenis_kemasan == jenis_kemasan)
                ),
                and_(
                    ProductCatalog.jenis_kemasan == jenis_kemasan,
                    ~ProductCatalog.id.in_(punya_kemasan),
                ),
            )
        )
    if is_active is not None:
        query = query.where(ProductCatalog.is_active == is_active)
    query = query.order_by(ProductCatalog.nama_produk)
    result = await db.execute(query)
    return result.scalars().all()


async def get_product(product_id: uuid.UUID, db: AsyncSession) -> ProductCatalog:
    result = await db.execute(
        select(ProductCatalog).where(ProductCatalog.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    return product


async def list_products_with_kemasan(
    db: AsyncSession,
    jenis_kemasan: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[dict]:
    """
    Untuk endpoint list produk. Satu query tambahan untuk semua produk (tanpa N+1).
    Mengembalikan dict agar field kemasan_tersedia divalidasi oleh ProductResponse.
    """
    produk_list = await list_products(db, jenis_kemasan, is_active)
    kemasan_map = await get_kemasan(db, [p.id for p in produk_list])
    return [
        {**p.model_dump(), "kemasan_tersedia": kemasan_map.get(p.id, [])}
        for p in produk_list
    ]


async def get_product_with_kemasan(product_id: uuid.UUID, db: AsyncSession) -> dict:
    """Untuk endpoint detail produk (dan respons create/update/set kemasan/foto)."""
    product = await get_product(product_id, db)
    kemasan_map = await get_kemasan(db, [product.id])
    return {**product.model_dump(), "kemasan_tersedia": kemasan_map.get(product.id, [])}


async def create_product(data: ProductCreate, db: AsyncSession) -> ProductCatalog:
    # Validasi kode_produk unik
    existing = await db.execute(
        select(ProductCatalog).where(ProductCatalog.kode_produk == data.kode_produk)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Kode produk '{data.kode_produk}' sudah digunakan.",
        )

    # `kemasan`, `jenis_kemasan`, dan `qty_per_kemasan` sudah dinormalisasi oleh
    # ProductCreate (jenis_kemasan = kemasan utama; qty mengikuti aturan kemasan
    # besar). `kemasan` bukan kolom ProductCatalog.
    product = ProductCatalog(**data.model_dump(exclude={"kemasan"}))
    db.add(product)
    try:
        await db.flush()  # product.id tersedia; unique constraint bisa gagal di sini
        await _terapkan_kemasan(product, data.kemasan or [], data.qty_per_kemasan, db)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Kode produk '{data.kode_produk}' sudah digunakan.",
        )
    await db.refresh(product)
    return product


async def update_product(
    product_id: uuid.UUID, data: ProductUpdate, db: AsyncSession
) -> ProductCatalog:
    """
    Update data dasar produk. Field jenis_kemasan, kemasan, dan qty_per_kemasan dari
    klien diabaikan oleh ProductUpdate; kemasan beserta isinya hanya berubah lewat
    set_kemasan. nama_produk, is_active, dan berat_gr tidak bisa dikosongkan (null
    diabaikan). Bila foto_url berubah atau dikosongkan, file foto lama dihapus jika
    tidak dipakai produk lain.
    """
    product = await get_product(product_id, db)
    foto_lama = product.foto_url
    NON_NULLABLE = {"nama_produk", "is_active", "berat_gr"}

    for key, value in data.model_dump(exclude_unset=True).items():
        if value is None and key in NON_NULLABLE:
            continue
        setattr(product, key, value)

    db.add(product)
    await db.commit()
    await db.refresh(product)

    if product.foto_url != foto_lama:
        await _hapus_file_foto_bila_yatim(foto_lama, db)
    return product


# ---------------------------------------------------------------------------
# Foto
# ---------------------------------------------------------------------------

FOTO_MAX_BYTES = 2 * 1024 * 1024  # 2 MB


def _deteksi_ekstensi_foto(isi: bytes) -> Optional[str]:
    """Tipe gambar ditentukan dari isi file, bukan dari content_type kiriman klien."""
    if isi.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if isi.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(isi) >= 12 and isi[:4] == b"RIFF" and isi[8:12] == b"WEBP":
        return ".webp"
    return None


async def _hapus_file_foto_bila_yatim(foto_url: Optional[str], db: AsyncSession) -> None:
    """
    Hapus file foto di FOTO_PRODUK_DIR bila tidak lagi dipakai produk mana pun.
    URL eksternal atau di luar folder produk tidak disentuh. Hanya nama file
    (tanpa path) yang dipakai, sehingga tidak bisa keluar dari folder foto.
    """
    if not foto_url or not foto_url.startswith(FOTO_PRODUK_URL_PREFIX):
        return
    nama = Path(foto_url).name
    if not nama or nama in {".", ".."}:
        return
    masih_dipakai = await db.execute(
        select(ProductCatalog.id).where(ProductCatalog.foto_url == foto_url).limit(1)
    )
    if masih_dipakai.first() is not None:
        return
    (FOTO_PRODUK_DIR / nama).unlink(missing_ok=True)


async def set_foto(
    product_id: uuid.UUID, file: UploadFile, db: AsyncSession
) -> None:
    """
    Simpan foto produk (JPG/PNG/WebP, maks 2 MB) dan perbarui foto_url. Tipe
    ditentukan dari isi file. File baru dibersihkan bila commit gagal; file lama
    dihapus setelah commit berhasil, hanya bila tidak dipakai produk lain.
    """
    product = await get_product(product_id, db)

    isi = await file.read(FOTO_MAX_BYTES + 1)
    if not isi:
        raise HTTPException(status_code=400, detail="File foto kosong.")
    if len(isi) > FOTO_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran foto maksimal {FOTO_MAX_BYTES // (1024 * 1024)} MB.",
        )
    ext = _deteksi_ekstensi_foto(isi)
    if ext is None:
        raise HTTPException(
            status_code=400,
            detail="Foto harus berformat JPG, PNG, atau WebP (isi file tidak dikenali).",
        )

    foto_lama = product.foto_url

    FOTO_PRODUK_DIR.mkdir(parents=True, exist_ok=True)
    nama = f"{uuid.uuid4().hex}{ext}"
    path_baru = FOTO_PRODUK_DIR / nama
    path_baru.write_bytes(isi)

    try:
        product.foto_url = f"{FOTO_PRODUK_URL_PREFIX}{nama}"
        db.add(product)
        await db.commit()
    except Exception:
        path_baru.unlink(missing_ok=True)
        raise

    await _hapus_file_foto_bila_yatim(foto_lama, db)