# Import semua model di sini agar Alembic bisa mendeteksi semua tabel
# saat generate migrasi. Urutan import penting (model dengan FK belakangan).

from app.models.wilayah import Provinsi, KabupatenKota, Kecamatan, Kelurahan
from app.models.role import Role, RolePermission
from app.models.permission import Permission
from app.models.user import User
from app.models.area import Area, AreaProvince
from app.models.distributor import Distributor, DistributorUser
from app.models.outlet import Outlet
from app.models.sc_spv import ScSpvDistributor, ApsmScSpv, RsmApsm
from app.models.product import ProductCatalog
from app.models.fkp import (
    FkpComplaint, FkpItem, FkpStatusLog, 
    FkpResolution, FkpAttachment, FkpDocument,
)
from app.models.sample import SampleShipment, SampleStatusLog
from app.models.warehouse import WarehouseSuratJalan, WarehouseSuratJalanItem
from app.models.notification import Notification
from app.models.testimoni import FkpTestimoni

__all__ = [
    "Provinsi", "KabupatenKota", "Kecamatan", "Kelurahan",
    "Role", "RolePermission", "Permission",
    "User",
    "Area", "AreaProvince",
    "Distributor", "DistributorUser",
    "Outlet",
    "ScSpvDistributor", "ApsmScSpv", "RsmApsm",
    "ProductCatalog",
    "FkpComplaint", "FkpItem", "FkpStatusLog", 
    "FkpResolution", "FkpAttachment", "FkpDocument",
    "SampleShipment", "SampleStatusLog",
    "WarehouseSuratJalan", "WarehouseSuratJalanItem",
    "Notification", "FkpTestimoni"
]