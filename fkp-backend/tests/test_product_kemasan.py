"""Test unit murni (tanpa DB/fixture) untuk aturan kemasan besar dan isi per kemasan
produk. Salin ke tests/."""
import pytest
from pydantic import ValidationError

from app.models.fkp import KEMASAN_DIHITUNG_JALUR, KEMASAN_PCS
from app.models.product import JenisKemasan, tentukan_qty_per_kemasan
from app.schemas.product import KemasanUpdate, ProductCreate, ProductUpdate


# ─── Konstanta & sinkron dengan models/fkp.py ────────────────────────────────

def test_kemasan_besar_sama_dengan_kemasan_dihitung_jalur():
    assert set(JenisKemasan.KEMASAN_BESAR) == set(KEMASAN_DIHITUNG_JALUR)


def test_partisi_kemasan_tanpa_irisan():
    besar, pcs = set(JenisKemasan.KEMASAN_BESAR), set(KEMASAN_PCS)
    assert besar | pcs == set(JenisKemasan.ALL)
    assert besar & pcs == set()


def test_isi_tetap_hanya_untuk_kemasan_besar():
    assert set(JenisKemasan.ISI_TETAP) <= set(JenisKemasan.KEMASAN_BESAR)
    assert JenisKemasan.ISI_TETAP == {"zak": 1}


def test_renceng_tetap_dihapus():
    assert "renceng" not in JenisKemasan.ALL
    assert "renceng" not in JenisKemasan.LABELS


# ─── tentukan_qty_per_kemasan ────────────────────────────────────────────────

@pytest.mark.parametrize("kemasan, qty, hasil", [
    (["zak"], None, 1),
    (["zak"], 5, 1),                 # kiriman klien diabaikan
    (["pcs"], None, 1),
    (["pcs"], 7, 1),                 # tanpa kemasan besar -> dipaksa 1
    (["ball"], 20, 20),
    (["ball", "pcs"], 20, 20),
    (["karton", "pcs"], 40, 40),
    (["pcs", "karton"], 40, 40),     # urutan input tidak berpengaruh
    (["ball", "ball"], 20, 20),      # duplikat bukan dua kemasan besar
])
def test_qty_sah(kemasan, qty, hasil):
    assert tentukan_qty_per_kemasan(kemasan, qty) == hasil


@pytest.mark.parametrize("kemasan, qty, label", [
    (["ball"], None, "ball"),
    (["ball", "pcs"], 1, "ball"),
    (["karton"], 0, "karton"),
    (["karton", "pcs"], None, "karton"),
])
def test_qty_wajib_untuk_ball_karton(kemasan, qty, label):
    with pytest.raises(ValueError) as e:
        tentukan_qty_per_kemasan(kemasan, qty)
    assert str(e.value) == f"Isi per {label} wajib diisi (minimal 2 pcs)."


@pytest.mark.parametrize("kemasan", [["ball", "karton"], ["zak", "ball"], ["zak", "karton", "pcs"]])
def test_maksimal_satu_kemasan_besar(kemasan):
    with pytest.raises(ValueError, match="hanya boleh punya satu kemasan besar"):
        tentukan_qty_per_kemasan(kemasan, 10)


def test_logika_digerakkan_konstanta_bukan_nama(monkeypatch):
    """Aturan 7: menambah kemasan baru (mis. renceng) cukup menambah konstanta."""
    monkeypatch.setattr(JenisKemasan, "ALL", JenisKemasan.ALL + ["renceng"])
    monkeypatch.setattr(JenisKemasan, "LABELS", {**JenisKemasan.LABELS, "renceng": "Renceng"})
    monkeypatch.setattr(JenisKemasan, "KEMASAN_BESAR", JenisKemasan.KEMASAN_BESAR + ["renceng"])

    assert tentukan_qty_per_kemasan(["renceng", "pcs"], 10) == 10
    with pytest.raises(ValueError, match="Isi per renceng wajib diisi"):
        tentukan_qty_per_kemasan(["renceng"], None)
    with pytest.raises(ValueError, match="satu kemasan besar"):
        tentukan_qty_per_kemasan(["renceng", "ball"], 10)


# ─── ProductCreate ───────────────────────────────────────────────────────────

def _create(**kw):
    dasar = dict(kode_produk="X-1", nama_produk="Produk X", berat_gr=1000)
    return ProductCreate(**{**dasar, **kw})


def test_create_ball_pcs_ternormalisasi():
    p = _create(kemasan=["pcs", "ball"], qty_per_kemasan=20)
    assert p.kemasan == ["ball", "pcs"]
    assert p.jenis_kemasan == "ball"
    assert p.qty_per_kemasan == 20


def test_create_zak_qty_dipaksa_satu():
    assert _create(kemasan=["zak"], berat_gr=10000, qty_per_kemasan=5).qty_per_kemasan == 1


def test_create_pcs_saja_qty_dipaksa_satu():
    assert _create(kemasan=["pcs"]).qty_per_kemasan == 1


def test_create_jalur_lama_jenis_kemasan_tetap_dipatuhi_aturan():
    assert _create(jenis_kemasan="karton", qty_per_kemasan=40).qty_per_kemasan == 40
    with pytest.raises(ValidationError):
        _create(jenis_kemasan="karton")


def test_create_berat_wajib():
    with pytest.raises(ValidationError):
        ProductCreate(kode_produk="X-1", nama_produk="Produk X", kemasan=["zak"])
    with pytest.raises(ValidationError):
        _create(kemasan=["zak"], berat_gr=0)


@pytest.mark.parametrize("kemasan, qty", [
    (["ball"], None),
    (["karton"], 1),
    (["ball", "karton"], 10),
    (["zak", "ball"], 10),
    (["renceng"], 10),
])
def test_create_ditolak(kemasan, qty):
    with pytest.raises(ValidationError):
        _create(kemasan=kemasan, qty_per_kemasan=qty)


# ─── ProductUpdate ───────────────────────────────────────────────────────────

def test_update_tidak_lagi_punya_qty_per_kemasan():
    assert "qty_per_kemasan" not in ProductUpdate.model_fields
    u = ProductUpdate(qty_per_kemasan=5, kemasan=["ball"], jenis_kemasan="ball")
    assert u.model_dump(exclude_unset=True) == {}   # semua diabaikan


# ─── KemasanUpdate ───────────────────────────────────────────────────────────

def test_kemasan_update_urut_dan_qty():
    k = KemasanUpdate(kemasan=["pcs", "ball", "pcs"], qty_per_kemasan=20)
    assert k.kemasan == ["ball", "pcs"]
    assert k.qty_per_kemasan == 20


def test_kemasan_update_zak_dan_pcs_saja_dipaksa_satu():
    assert KemasanUpdate(kemasan=["zak"], qty_per_kemasan=9).qty_per_kemasan == 1
    assert KemasanUpdate(kemasan=["pcs"]).qty_per_kemasan == 1


@pytest.mark.parametrize("kemasan, qty", [
    (["karton"], None),
    (["ball", "pcs"], 1),
    (["ball", "karton"], 10),
    ([], 10),
    (["renceng"], 10),
])
def test_kemasan_update_ditolak(kemasan, qty):
    with pytest.raises(ValidationError):
        KemasanUpdate(kemasan=kemasan, qty_per_kemasan=qty)