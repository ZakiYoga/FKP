"""
Schemas untuk manajemen hierarki sales:
RSM → APSM → SC/SPV → Distributor → Outlet
"""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ─── SC/SPV ↔ DISTRIBUTOR ────────────────────────────────────────────────────

class ScSpvDistributorAssign(BaseModel):
    """Assign SC/SPV ke distributor."""
    sc_spv_user_id: uuid.UUID
    distributor_id: uuid.UUID

    class Config:
        json_schema_extra = {
            "example": {
                "sc_spv_user_id": "uuid-user-sc-spv",
                "distributor_id": "uuid-distributor"
            }
        }


class ScSpvDistributorResponse(BaseModel):
    id: uuid.UUID
    sc_spv_user_id: uuid.UUID
    distributor_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ─── APSM ↔ SC/SPV ───────────────────────────────────────────────────────────

class ApsmScSpvAssign(BaseModel):
    """Assign SC/SPV ke bawah APSM tertentu."""
    apsm_user_id: uuid.UUID
    sc_spv_user_id: uuid.UUID

    class Config:
        json_schema_extra = {
            "example": {
                "apsm_user_id": "uuid-user-apsm",
                "sc_spv_user_id": "uuid-user-sc-spv"
            }
        }


class ApsmScSpvResponse(BaseModel):
    id: uuid.UUID
    apsm_user_id: uuid.UUID
    sc_spv_user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ─── RSM ↔ APSM ──────────────────────────────────────────────────────────────

class RsmApsmAssign(BaseModel):
    """Assign APSM ke bawah RSM tertentu."""
    rsm_user_id: uuid.UUID
    apsm_user_id: uuid.UUID

    class Config:
        json_schema_extra = {
            "example": {
                "rsm_user_id": "uuid-user-rsm",
                "apsm_user_id": "uuid-user-apsm"
            }
        }


class RsmApsmResponse(BaseModel):
    id: uuid.UUID
    rsm_user_id: uuid.UUID
    apsm_user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ─── RESPONSE HIERARKI (untuk dashboard/view) ────────────────────────────────

class UserBasicInfo(BaseModel):
    id: uuid.UUID
    nama: str
    email: str
    no_telepon: Optional[str]

    class Config:
        from_attributes = True


class DistributorBasicInfo(BaseModel):
    id: uuid.UUID
    kode_distributor: str
    nama_perusahaan: str
    status: str

    class Config:
        from_attributes = True


class ScSpvWithDistributors(BaseModel):
    """SC/SPV beserta daftar distributor yang dia handle."""
    sc_spv: UserBasicInfo
    distributors: List[DistributorBasicInfo] = []


class ApsmWithTeam(BaseModel):
    """APSM beserta tim SC/SPV di bawahnya."""
    apsm: UserBasicInfo
    sc_spv_list: List[ScSpvWithDistributors] = []


class RsmWithTeam(BaseModel):
    """RSM beserta tim APSM di bawahnya."""
    rsm: UserBasicInfo
    apsm_list: List[ApsmWithTeam] = []
