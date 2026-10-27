import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

UPLOAD_ROOT = Path("uploads")
AVATAR_DIR = UPLOAD_ROOT / "avatars"
MAX_BYTES = 2 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
AVATAR_SIZE = (256, 256)


async def save_avatar(file: UploadFile, user_id: uuid.UUID) -> str:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Format harus JPEG, PNG, atau WebP.")

    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Ukuran file maksimal 2 MB.")

    try:
        Image.open(BytesIO(data)).verify()
        img = Image.open(BytesIO(data))
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "File bukan gambar yang valid.")

    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageOps.fit(img, AVATAR_SIZE)

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{user_id}-{uuid.uuid4().hex[:8]}.webp"
    img.save(AVATAR_DIR / filename, "WEBP", quality=85)
    return f"avatars/{filename}"


def delete_avatar(avatar_path: Optional[str]) -> None:
    if not avatar_path:
        return
    target = (UPLOAD_ROOT / avatar_path).resolve()
    if AVATAR_DIR.resolve() in target.parents and target.is_file():
        target.unlink()