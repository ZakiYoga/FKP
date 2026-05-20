"""
Fetch data wilayah dari wilayah.web.id → simpan ke PostgreSQL
=============================================================
Fitur:
  - Progress tracking detail (provinsi > kab > kecamatan > kelurahan)
  - Resume otomatis jika terhenti di tengah jalan
  - Log file lengkap
  - Statistik real-time & estimasi waktu selesai (ETA)
  - Dry-run mode
  - Filter per provinsi

Jalankan:
    pip install requests psycopg2-binary tqdm colorama
    python fetch_wilayah_to_db.py
    python fetch_wilayah_to_db.py --provinsi 33          # Jawa Tengah saja
    python fetch_wilayah_to_db.py --dry-run              # tanpa insert DB
    python fetch_wilayah_to_db.py --resume               # lanjut dari checkpoint
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
from tqdm import tqdm

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        GREEN = YELLOW = RED = CYAN = MAGENTA = BLUE = WHITE = ""
    class Style:
        BRIGHT = RESET_ALL = ""

# ============================================================
# KONFIGURASI
# ============================================================
PG_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "user":     "fkp_sakti",
    "password": "Sakt1!",
    "dbname":   "fkp_db",
}

BASE_URL        = "https://wilayah.web.id/api"
DELAY           = 0.3
MAX_RETRY       = 3
CHECKPOINT_FILE = "wilayah_checkpoint.json"
LOG_FILE        = f"wilayah_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
# ============================================================


# ── Logging setup ─────────────────────────────────────────────
def setup_logging() -> logging.Logger:
    logger = logging.getLogger("wilayah")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger

log = setup_logging()


# ── Helper print berwarna ──────────────────────────────────────
def ok(msg):    print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {msg}");   log.info(msg)
def warn(msg):  print(f"  {Fore.YELLOW}⚠{Style.RESET_ALL} {msg}"); log.warning(msg)
def err(msg):   print(f"  {Fore.RED}✗{Style.RESET_ALL} {msg}");     log.error(msg)
def info(msg):  print(f"  {Fore.CYAN}→{Style.RESET_ALL} {msg}");    log.info(msg)
def head(msg):  print(f"\n{Fore.MAGENTA}{Style.BRIGHT}{msg}{Style.RESET_ALL}"); log.info(msg)


# ── Checkpoint (resume) ────────────────────────────────────────
def load_checkpoint() -> dict:
    if Path(CHECKPOINT_FILE).exists():
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {"done_prov": [], "done_kab": [], "done_kec": []}

def save_checkpoint(cp: dict):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(cp, f, indent=2)

def clear_checkpoint():
    if Path(CHECKPOINT_FILE).exists():
        os.remove(CHECKPOINT_FILE)


# ── Statistik & ETA ───────────────────────────────────────────
class Stats:
    def __init__(self):
        self.start_time   = time.time()
        self.provinsi     = 0
        self.kabupaten    = 0
        self.kecamatan    = 0
        self.kelurahan    = 0
        self.api_calls    = 0
        self.api_errors   = 0
        self._kec_times   = []   # untuk estimasi ETA

    def elapsed(self) -> str:
        s = int(time.time() - self.start_time)
        return str(timedelta(seconds=s))

    def eta(self, done_kec: int, total_kec: int) -> str:
        if done_kec == 0:
            return "menghitung..."
        avg = (time.time() - self.start_time) / done_kec
        sisa = (total_kec - done_kec) * avg
        return str(timedelta(seconds=int(sisa)))

    def summary(self):
        print()
        print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{Style.BRIGHT}  RINGKASAN AKHIR{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
        rows = [
            ("Provinsi",       self.provinsi,  Fore.GREEN),
            ("Kabupaten/Kota", self.kabupaten, Fore.GREEN),
            ("Kecamatan",      self.kecamatan, Fore.GREEN),
            ("Kelurahan/Desa", self.kelurahan, Fore.GREEN),
            ("Total API call", self.api_calls, Fore.CYAN),
            ("API error",      self.api_errors,Fore.RED if self.api_errors else Fore.GREEN),
        ]
        for label, val, color in rows:
            print(f"  {label:<20}: {color}{val:>8,}{Style.RESET_ALL}")
        print(f"  {'Durasi':<20}: {Fore.CYAN}{self.elapsed()}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
        log.info(f"SELESAI | provinsi={self.provinsi} kab={self.kabupaten} "
                 f"kec={self.kecamatan} kel={self.kelurahan} "
                 f"api_calls={self.api_calls} api_errors={self.api_errors} "
                 f"durasi={self.elapsed()}")


# ── HTTP fetch dengan retry ────────────────────────────────────
def fetch_json(url: str, stats: Stats) -> dict:
    stats.api_calls += 1
    for attempt in range(1, MAX_RETRY + 1):
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            stats.api_errors += 1
            if attempt == MAX_RETRY:
                log.error(f"GAGAL fetch {url}: {e}")
                raise RuntimeError(f"Gagal fetch setelah {MAX_RETRY}x: {url}\n  {e}")
            wait = attempt * 2
            warn(f"Retry {attempt}/{MAX_RETRY} ({wait}s) — {url}")
            time.sleep(wait)


# ── Cek koneksi DB ─────────────────────────────────────────────
def check_db(dry_run: bool):
    if dry_run:
        return
    head("[0] Memeriksa koneksi database")
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cur  = conn.cursor()
        ok(f"Terhubung ke '{PG_CONFIG['dbname']}' @ {PG_CONFIG['host']}:{PG_CONFIG['port']}")
    except psycopg2.OperationalError as e:
        err(f"Koneksi gagal: {e}")
        sys.exit(1)

    required = ["provinsi", "kabupaten_kota", "kecamatan", "kelurahan"]
    missing  = []
    for tbl in required:
        cur.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name=%s)", (tbl,))
        if not cur.fetchone()[0]:
            missing.append(tbl)
    if missing:
        err(f"Tabel tidak ditemukan: {', '.join(missing)}")
        info("Jalankan: alembic upgrade head")
        sys.exit(1)
    ok(f"Semua tabel ditemukan: {', '.join(required)}")

    print(f"\n  {Fore.CYAN}Data saat ini:{Style.RESET_ALL}")
    for tbl in required:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        n = cur.fetchone()[0]
        print(f"    {tbl:<20}: {n:,} baris")

    cur.close()
    conn.close()


# ── Cek koneksi API ────────────────────────────────────────────
def check_api(stats: Stats) -> list:
    head("[0b] Memeriksa koneksi API")
    try:
        data = fetch_json(f"{BASE_URL}/provinces", stats)
        provinces = data["data"]
        ok(f"API OK — {len(provinces)} provinsi tersedia")
        return provinces
    except Exception as e:
        err(f"API tidak dapat diakses: {e}")
        sys.exit(1)


# ── Baris status satu baris (overwrite) ───────────────────────
def status_line(prov_name: str, kab_name: str, kec_name: str, kel_name: str = ""):
    prov = f"{Fore.GREEN}{prov_name:<25}{Style.RESET_ALL}"
    kab  = f"{Fore.YELLOW}{kab_name:<30}{Style.RESET_ALL}"
    kec  = f"{Fore.CYAN}{kec_name:<30}{Style.RESET_ALL}"
    kel  = f"{Fore.WHITE}{kel_name}{Style.RESET_ALL}" if kel_name else ""
    line = f"  {prov} › {kab} › {kec}" + (f" › {kel}" if kel else "")
    # Potong agar tidak wrap di terminal sempit
    max_w = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 120
    print(f"\r{line[:max_w]}", end="", flush=True)


# ── MAIN ───────────────────────────────────────────────────────
def main(only_provinsi: list, dry_run: bool, resume: bool):
    stats = Stats()

    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"  Fetch wilayah.web.id → PostgreSQL")
    if dry_run: print(f"  {Fore.YELLOW}MODE DRY-RUN (tidak ada insert ke DB)")
    if resume:  print(f"  {Fore.CYAN}MODE RESUME (lanjut dari checkpoint)")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
    log.info(f"START | dry_run={dry_run} resume={resume} filter={only_provinsi}")

    check_db(dry_run)
    provinces = check_api(stats)

    if only_provinsi:
        provinces = [p for p in provinces if p["code"] in only_provinsi]
        info(f"Filter aktif: {only_provinsi} → {len(provinces)} provinsi")

    # Checkpoint
    cp = load_checkpoint() if resume else {"done_prov": [], "done_kab": [], "done_kec": []}
    if resume and cp["done_prov"]:
        info(f"Checkpoint: {len(cp['done_prov'])} provinsi sudah selesai sebelumnya")

    # Koneksi DB
    pg_conn = pg_cur = None
    if not dry_run:
        head("[1] Membuka koneksi PostgreSQL")
        pg_conn = psycopg2.connect(**PG_CONFIG)
        pg_conn.autocommit = False
        pg_cur  = pg_conn.cursor()
        ok("Koneksi berhasil")

        if not resume and not only_provinsi:
            head("[2] Membersihkan tabel")
            pg_cur.execute("""
                TRUNCATE TABLE kelurahan, kecamatan, kabupaten_kota, provinsi
                RESTART IDENTITY CASCADE
            """)
            pg_conn.commit()
            ok("Semua tabel dikosongkan")

    # ── Estimasi total kecamatan (opsional, skip jika lambat) ─
    # Gunakan angka tetap berdasarkan data BPS Indonesia
    EST_TOTAL_KEC = 7_277   # estimasi kecamatan seluruh Indonesia

    head(f"[3] Memulai proses ({len(provinces)} provinsi)")
    print(f"\n  {'PROVINSI':<25}   {'KABUPATEN/KOTA':<30}   {'KECAMATAN':<30}")
    print(f"  {'-'*25}   {'-'*30}   {'-'*30}\n")

    pbar_prov = tqdm(
        provinces,
        desc=f"{'Provinsi':>10}",
        unit="prov",
        position=0,
        colour="magenta",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
    )

    for prov in pbar_prov:
        prov_code = prov["code"]
        prov_name = prov["name"]
        reg_url   = prov.get("regencies_url", f"{BASE_URL}/regencies/{prov_code}")

        pbar_prov.set_description(f"Provinsi: {prov_name[:20]}")
        log.info(f"PROVINSI [{prov_code}] {prov_name}")

        # Skip jika sudah selesai (resume mode)
        if prov_code in cp["done_prov"]:
            tqdm.write(f"  {Fore.YELLOW}⏭  Skip (sudah selesai): [{prov_code}] {prov_name}{Style.RESET_ALL}")
            stats.provinsi += 1
            continue

        tqdm.write(f"\n{Fore.MAGENTA}{'─'*60}{Style.RESET_ALL}")
        tqdm.write(f"{Fore.GREEN}{Style.BRIGHT}  ▶ PROVINSI [{prov_code}] {prov_name}{Style.RESET_ALL}")

        # Insert provinsi
        if not dry_run:
            pg_cur.execute(
                "INSERT INTO provinsi (kode, nama_provinsi) VALUES (%s, %s) "
                "ON CONFLICT (kode) DO UPDATE SET nama_provinsi=EXCLUDED.nama_provinsi RETURNING id",
                (prov_code, prov_name)
            )
            prov_id = pg_cur.fetchone()[0]
        else:
            prov_id = 0
        stats.provinsi += 1

        # Fetch kabupaten
        time.sleep(DELAY)
        reg_data  = fetch_json(reg_url, stats)
        regencies = reg_data["data"]

        pbar_kab = tqdm(
            regencies,
            desc=f"{'Kab/Kota':>10}",
            unit="kab",
            position=1,
            leave=False,
            colour="yellow",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
        )

        for reg in pbar_kab:
            reg_code = reg["code"]
            reg_name = reg["name"]
            dist_url = reg.get("districts_url", f"{BASE_URL}/districts/{reg_code}")

            pbar_kab.set_description(f"  Kab: {reg_name[:22]}")
            log.info(f"  KAB [{reg_code}] {reg_name}")

            if reg_code in cp["done_kab"]:
                tqdm.write(f"    {Fore.YELLOW}⏭ Skip kab: {reg_name}{Style.RESET_ALL}")
                stats.kabupaten += 1
                continue

            tqdm.write(f"  {Fore.YELLOW}  ● [{reg_code}] {reg_name}{Style.RESET_ALL}")

            if not dry_run:
                pg_cur.execute(
                    """INSERT INTO kabupaten_kota (kode, provinsi_id, nama)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (kode) DO UPDATE SET nama=EXCLUDED.nama RETURNING id""",
                    (reg_code, prov_id, reg_name)
                )
                kab_id = pg_cur.fetchone()[0]
            else:
                kab_id = 0
            stats.kabupaten += 1

            # Fetch kecamatan
            time.sleep(DELAY)
            dist_data = fetch_json(dist_url, stats)
            districts = dist_data["data"]

            pbar_kec = tqdm(
                districts,
                desc=f"{'Kecamatan':>10}",
                unit="kec",
                position=2,
                leave=False,
                colour="cyan",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
            )

            for dist in pbar_kec:
                dist_code = dist["code"]
                dist_name = dist["name"]
                vil_url   = dist.get("villages_url", f"{BASE_URL}/villages/{dist_code}")

                pbar_kec.set_description(f"    Kec: {dist_name[:18]}")
                log.info(f"    KEC [{dist_code}] {dist_name}")

                if dist_code in cp["done_kec"]:
                    stats.kecamatan += 1
                    continue

                tqdm.write(f"    {Fore.CYAN}    ◆ [{dist_code}] {dist_name}{Style.RESET_ALL}")

                if not dry_run:
                    pg_cur.execute(
                        """INSERT INTO kecamatan (kode, kabupaten_kota_id, nama)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (kode) DO UPDATE SET nama=EXCLUDED.nama RETURNING id""",
                        (dist_code, kab_id, dist_name)
                    )
                    kec_id = pg_cur.fetchone()[0]
                else:
                    kec_id = 0
                stats.kecamatan += 1

                # Fetch kelurahan
                time.sleep(DELAY)
                vil_data = fetch_json(vil_url, stats)
                villages = vil_data["data"]

                if villages:
                    tqdm.write(
                        f"      {Fore.WHITE}  ↳ {len(villages)} kelurahan/desa{Style.RESET_ALL}"
                        + (f" | contoh: {villages[0]['name']}, ..." if villages else "")
                    )
                    log.info(f"      {len(villages)} kelurahan di {dist_name}")

                    if not dry_run:
                        psycopg2.extras.execute_batch(
                            pg_cur,
                            """INSERT INTO kelurahan (kode, kecamatan_id, nama, kode_pos)
                               VALUES (%s, %s, %s, %s)
                               ON CONFLICT (kode) DO UPDATE
                               SET nama=EXCLUDED.nama, kode_pos=EXCLUDED.kode_pos""",
                            [(v["code"], kec_id, v["name"], v.get("postal_code"))
                             for v in villages]
                        )
                stats.kelurahan += len(villages)

                # Tandai kecamatan selesai
                cp["done_kec"].append(dist_code)
                save_checkpoint(cp)

            # Commit per kabupaten & tandai selesai
            if not dry_run:
                pg_conn.commit()
            cp["done_kab"].append(reg_code)
            save_checkpoint(cp)

            tqdm.write(
                f"    {Fore.GREEN}✓ {reg_name} selesai "
                f"({len(districts)} kec, {stats.kelurahan:,} kel total)"
                f"{Style.RESET_ALL}"
            )

        # Tandai provinsi selesai
        cp["done_prov"].append(prov_code)
        save_checkpoint(cp)
        tqdm.write(
            f"\n{Fore.GREEN}{Style.BRIGHT}  ✔ [{prov_code}] {prov_name} SELESAI "
            f"| {len(regencies)} kab | kec total: {stats.kecamatan:,} "
            f"| kel total: {stats.kelurahan:,} "
            f"| elapsed: {stats.elapsed()}"
            f"{Style.RESET_ALL}\n"
        )
        log.info(f"PROVINSI SELESAI [{prov_code}] {prov_name}")

    pbar_prov.close()

    # Commit akhir & tutup koneksi
    if not dry_run and pg_conn:
        pg_conn.commit()
        pg_cur.close()
        pg_conn.close()

    # Bersihkan checkpoint jika selesai penuh
    if not only_provinsi:
        clear_checkpoint()
        info("Checkpoint dihapus (proses selesai penuh)")

    stats.summary()
    if dry_run:
        print(f"  {Fore.YELLOW}(Dry-run — tidak ada data yang disimpan ke DB){Style.RESET_ALL}\n")
    print(f"  Log tersimpan di: {Fore.CYAN}{LOG_FILE}{Style.RESET_ALL}\n")


# ── Entry point ────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch wilayah.web.id → PostgreSQL (dengan progress tracking)"
    )
    parser.add_argument(
        "--provinsi", type=str, default=None,
        help="Kode provinsi dipisah koma. Contoh: --provinsi 11,33"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Jalankan tanpa insert ke database"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Lanjutkan dari checkpoint terakhir jika proses terhenti"
    )
    args = parser.parse_args()

    filter_prov = [p.strip() for p in args.provinsi.split(",")] if args.provinsi else None
    main(only_provinsi=filter_prov, dry_run=args.dry_run, resume=args.resume)