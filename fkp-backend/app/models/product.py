import uuid
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

from app.models.fkp import FkpItem


class ProductCatalog(SQLModel, table=True):
    __tablename__ = "product_catalog"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    kode_produk: str = Field(max_length=30, unique=True, index=True)
    nama_produk: str = Field(max_length=200)
    jenis_kemasan: str = Field(max_length=20)   # "zak" | "karton" | "renceng" | "ball" | "pcs"
    berat_gr: Optional[int] = Field(default=None)   # berat dalam gram
    foto_url: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    
    fkp_items: List["FkpItem"] = Relationship(back_populates="product")