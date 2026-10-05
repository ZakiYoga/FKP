from pathlib import Path

from app.core.config import settings

# Satu-satunya definisi lokasi dan URL foto produk. Dipakai main.py (mount static)
# dan product_service (simpan/hapus). Berada di bawah UPLOAD_DIR supaya ikut
# volume/backup yang sama dengan lampiran FKP.
FOTO_PRODUK_DIR = Path(settings.UPLOAD_DIR) / "products"
FOTO_PRODUK_URL_PREFIX = "/uploads/products/"