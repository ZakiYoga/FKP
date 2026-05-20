import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


# ─── AREA ─────────────────────────────────────────────────────────────────────

class AreaCreate(BaseModel):
    kode_area: str
    nama_area: str
    pic_user_id: Optional[uuid.UUID] = None
    provinsi_ids: List[int] = []   # list id provinsi yang dicakup area ini

    class Config:
        json_schema_extra = {
            "example": {
                "kode_area": "AREA-07",
                "nama_area": "Area Baru",
                "pic_user_id": None,
                "provinsi_ids": [1, 2, 3]
            }
        }


class AreaUpdate(BaseModel):
    nama_area: Optional[str] = None
    pic_user_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    provinsi_ids: Optional[List[int]] = None


class ProvinsiResponse(BaseModel):
    id: int
    nama_provinsi: str

    class Config:
        from_attributes = True


class AreaResponse(BaseModel):
    id: uuid.UUID
    kode_area: str
    nama_area: str
    pic_user_id: Optional[uuid.UUID]
    status: str
    created_at: datetime
    updated_at: datetime
    provinsi: List[ProvinsiResponse] = []

    class Config:
        from_attributes = True
