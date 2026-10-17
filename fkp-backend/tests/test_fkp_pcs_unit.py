"""Test unit murni (tanpa DB/fixture) untuk jalur pcs. Salin ke tests/."""
import pytest
from fastapi import HTTPException

from app.models.fkp import (
    JenisKemasan as JK_FKP, KEMASAN_DIHITUNG_JALUR, KEMASAN_PCS,
    FkpStatus, JalurFkp, TahapPcs,
)
from app.models.product import JenisKemasan as JK_PRODUCT
from app.services.fkp_service import (
    _tolak_jika_campur, KELOMPOK_PCS, KELOMPOK_NON_PCS, VALID_TRANSITIONS,
)


def test_partisi_kemasan_tanpa_irisan():
    assert set(KEMASAN_DIHITUNG_JALUR) | set(KEMASAN_PCS) == set(JK_FKP.ALL)
    assert set(KEMASAN_DIHITUNG_JALUR) & set(KEMASAN_PCS) == set()


def test_renceng_dihapus():
    assert "renceng" not in JK_FKP.ALL
    assert "renceng" not in JK_PRODUCT.ALL


def test_dua_definisi_jenis_kemasan_sinkron():
    assert set(JK_FKP.ALL) == set(JK_PRODUCT.ALL)


def test_tolak_jika_campur():
    assert _tolak_jika_campur([]) is None
    assert _tolak_jika_campur([("A", "pcs"), ("B", "pcs")]) == KELOMPOK_PCS
    assert _tolak_jika_campur([("A", "zak"), ("B", "ball"), ("C", "karton")]) == KELOMPOK_NON_PCS
    for non_pcs in ("zak", "ball", "karton"):
        with pytest.raises(HTTPException) as e:
            _tolak_jika_campur([("Pakan A", "pcs"), ("Pakan B", non_pcs)])
        assert e.value.status_code == 400
        assert "Pakan A" in e.value.detail and f"Pakan B ({non_pcs})" in e.value.detail
        assert "Pisahkan" in e.value.detail


def test_state_machine_pcs():
    assert FkpStatus.PCS_DITANGANI_APSM in VALID_TRANSITIONS[FkpStatus.SUBMITTED]
    assert set(VALID_TRANSITIONS[FkpStatus.PCS_DITANGANI_APSM]) == {FkpStatus.CLOSED, FkpStatus.REJECTED}
    assert FkpStatus.PCS_DITANGANI_APSM in FkpStatus.ALL
    # tidak ada jalan dari status pcs ke alur approval
    assert FkpStatus.RSM_APPROVAL_FINAL not in VALID_TRANSITIONS[FkpStatus.PCS_DITANGANI_APSM]


def test_urutan_tahap_dan_jalur():
    assert TahapPcs.URUTAN == ("dalam_pengajuan", "dalam_proses", "selesai")
    assert set(JalurFkp.ALL) == {"pcs", "approval_rsm", "approval_direktur"}