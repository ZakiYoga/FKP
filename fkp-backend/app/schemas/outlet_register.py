import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator, model_validator


class OutletRegisterRequest(BaseModel):
    # === Akun ===
    email: EmailStr
    password: str
    retype_password: str

    # === Data Outlet ===
    nama_toko: str
    pemilik_toko: str
    tipe_toko: str          # "retail" | "grosir" | "horeka"
    no_hp: str

    # === Relasi ===
    distributor_id: uuid.UUID

    # === Lokasi (opsional, bisa dilengkapi nanti) ===
    alamat_lengkap: Optional[str] = None
    kelurahan_id: Optional[int] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password minimal 8 karakter")
        return v

    @field_validator("tipe_toko")
    @classmethod
    def tipe_toko_valid(cls, v: str) -> str:
        allowed = {
            "retail_tradisional",
            "retail_modern",
            "grosir",
            "horeca",
            "umkm",
            "tobaku",
            "bakery",
            "catering",
            "reseller",
            "online_shop",
            "lainnya",
        }
        if v.lower() not in allowed:
            raise ValueError(f"tipe_toko harus salah satu dari: {allowed}")
        return v.lower()

    @model_validator(mode="after")
    def passwords_match(self) -> "OutletRegisterRequest":
        if self.password != self.retype_password:
            raise ValueError("Password dan retype_password tidak cocok")
        return self


class OutletRegisterResponse(BaseModel):
    message: str
    outlet_id: uuid.UUID
    user_id: uuid.UUID
    kode_outlet: str
    
# ─── RESPONSE: Detail Registrasi (untuk List Pending) ────────────────────────
 
class OutletRegistrationDetail(BaseModel):
    """Data ringkas satu pendaftaran outlet yang sedang pending."""
    outlet_id: uuid.UUID
    user_id: uuid.UUID
    kode_outlet: str
    nama_toko: str
    pemilik_toko: str
    tipe_toko: str
    no_hp: Optional[str]
    email: str
    alamat_lengkap: Optional[str]
    distributor_id: uuid.UUID
    status: str                     # selalu "pending" di endpoint ini
    created_at: datetime
 
    model_config = {"from_attributes": True}
 
 
class OutletRegistrationListResponse(BaseModel):
    total: int
    items: List[OutletRegistrationDetail]
 
 
# ─── REQUEST: Approve Registrasi ─────────────────────────────────────────────
 
class OutletApproveRequest(BaseModel):
    """Body opsional saat menyetujui registrasi outlet."""
    catatan: Optional[str] = None   # catatan dari admin/distributor (boleh kosong)
 
 
class OutletApproveResponse(BaseModel):
    """
    [REVISI] `user_is_active` bersifat informatif, BUKAN efek samping dari
    approve ini.

    Keputusan final: User.is_active SELALU True untuk akun yang valid secara
    administratif, dan TIDAK dipakai sebagai proxy status approval outlet.
    approve_registration() tidak lagi mengubah is_active sama sekali — yang
    berubah hanya Outlet.status. Gate login untuk role outlet sepenuhnya
    ditentukan oleh status outlet (lihat auth_service.login()): login
    diizinkan jika MINIMAL SATU outlet milik user berstatus 'aktif', karena
    1 user boleh memiliki lebih dari satu outlet (distributor harus sama).

    Field ini tetap disertakan agar caller bisa melihat status administratif
    user tanpa query tambahan — nilainya akan tetap True kecuali user
    tersebut secara independen pernah dinonaktifkan admin.
    """
    message: str
    outlet_id: uuid.UUID
    user_id: uuid.UUID
    kode_outlet: str
    status: str                     # "aktif"
    user_is_active: bool = True     # status administratif user, bukan hasil approve ini
 
 
# ─── REQUEST: Reject Registrasi ──────────────────────────────────────────────
 
class OutletRejectRequest(BaseModel):
    """Body wajib saat menolak registrasi — alasan harus diisi."""
    alasan: str
 
    @field_validator("alasan")
    @classmethod
    def alasan_tidak_kosong(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Alasan penolakan tidak boleh kosong")
        return v.strip()
 
 
class OutletRejectResponse(BaseModel):
    message: str
    outlet_id: uuid.UUID
    status: str                     # "ditolak"