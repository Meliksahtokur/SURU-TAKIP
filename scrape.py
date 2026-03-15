#!/usr/bin/env python3
"""
scrape.py  —  Tohumlama sayfasını çek, kaydet
----------------------------------------------
Kullanım:
    python scrape.py http://vethek.org/t_2_7867_MTQzMjY.htm

Çıktı:
    data/2026-03-14_vethek.sql        (PostgreSQL export)
    data/tohumlamalar.db              (SQLite, sorgu için)
"""

import re
import sys
import sqlite3
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("❌  Eksik paket: pip install requests beautifulsoup4 lxml")

# ── Klasör yapısı ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH  = DATA_DIR / "tohumlamalar.db"


# ── Yardımcılar ───────────────────────────────────────────────────────────────

def next_path(base: Path) -> Path:
    """İsim çakışmasında  base, base_1, base_2 ... döndür."""
    if not base.exists():
        return base
    stem, suffix = base.stem, base.suffix
    i = 1
    while True:
        candidate = base.parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1

def slug_from_url(url: str) -> str:
    """URL'den kısa bir isim üret:  vethek_t_2_7867"""
    p = urlparse(url)
    name = Path(p.path).stem                    # t_2_7867_MTQzMjY
    # Base64 kısmı at, fazla uzun olmasın
    parts = name.split("_")
    slug  = "_".join(p for p in parts if not re.match(r"^[A-Za-z0-9+/=]{6,}$", p))
    return slug[:40] or "scrape"

def fetch_page(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; surü-takip/1.0)"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return r.text

def parse_tarih(raw: str) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    m = re.search(r"(\d{2})[./](\d{2})[./](\d{4})", raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None

def clean(text: str) -> str:
    return " ".join(text.split()) if text else ""


# ── Tablo parser ──────────────────────────────────────────────────────────────

def parse_table(html: str, scrape_url: str) -> list[dict]:
    soup   = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        sys.exit("❌  Sayfada <table> yok. JS render mi? scrape.py çalışmıyor.")

    target = max(tables, key=lambda t: len(t.find_all("tr")))
    rows   = target.find_all("tr")

    # Başlık satırından kolon isimlerini çıkar
    header_cells = rows[0].find_all(["th", "td"]) if rows else []
    headers = [clean(c.get_text(" ", strip=True)).lower() for c in header_cells]

    def col_idx(*keywords) -> int:
        """Başlıktan kolon indexi bul, bulamazsan -1."""
        for kw in keywords:
            for i, h in enumerate(headers):
                if kw in h:
                    return i
        return -1

    # 0:id | 1:sperma | 2:belge_no | 3:kupe_no | 4:irk | 5:not_ | 6:tarih | 7:gebe_onay
    IDX = {"hayvan_id":0,"sperma":1,"belge_no":2,"kupe_no":3,
           "irk":4,"not_":5,"tarih":6,"gebe":7}

    today = date.today().isoformat()
    records = []

    for tr in rows[1:]:
        cells = [clean(td.get_text(" ", strip=True)) for td in tr.find_all(["td","th"])]
        if not cells:
            continue

        def col(key):
            i = IDX.get(key, -1)
            return cells[i] if 0 <= i < len(cells) else ""

        raw_id = col("hayvan_id")
        if not re.match(r"^\d{4,6}$", raw_id):
            continue

        # Tarih: önce belirlenen sütun, yoksa tüm satırda ara
        tarih = parse_tarih(col("tarih"))
        if not tarih:
            for c in cells:
                tarih = parse_tarih(c)
                if tarih:
                    break

        # Gebe tespiti: sütun 7 doluysa gebe, boşsa değil
        gebe = 1 if col("gebe").strip() else 0

        records.append({
            "hayvan_id"    : int(raw_id),
            "sperma"       : col("sperma"),
            "belge_no"     : col("belge_no"),
            "kupe_no"      : col("kupe_no"),
            "irk"          : col("irk"),
            "not_"         : col("not_"),
            "tohumlama_tar": tarih,
            "gebe"         : gebe,
            "scrape_tarihi": today,
            "kaynak_url"   : scrape_url,
        })

    return records


# ── SQLite yaz ────────────────────────────────────────────────────────────────

DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS tohumlamalar (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    hayvan_id      INTEGER NOT NULL,
    sperma         TEXT,
    belge_no       TEXT,
    kupe_no        TEXT,
    irk            TEXT,
    not_           TEXT,
    tohumlama_tar  TEXT,
    gebe           INTEGER,
    scrape_tarihi  TEXT NOT NULL,
    kaynak_url     TEXT
);
CREATE INDEX IF NOT EXISTS idx_hayvan   ON tohumlamalar(hayvan_id);
CREATE INDEX IF NOT EXISTS idx_kupe     ON tohumlamalar(kupe_no);
CREATE INDEX IF NOT EXISTS idx_tarih    ON tohumlamalar(tohumlama_tar);
CREATE INDEX IF NOT EXISTS idx_scrape   ON tohumlamalar(scrape_tarihi);
"""

def write_sqlite(records: list[dict]) -> int:
    con = sqlite3.connect(DB_PATH)
    for stmt in DDL_SQLITE.strip().split(";"):
        if stmt.strip():
            con.execute(stmt)
    con.executemany("""
        INSERT INTO tohumlamalar
            (hayvan_id,sperma,belge_no,kupe_no,irk,not_,
             tohumlama_tar,gebe,scrape_tarihi,kaynak_url)
        VALUES
            (:hayvan_id,:sperma,:belge_no,:kupe_no,:irk,:not_,
             :tohumlama_tar,:gebe,:scrape_tarihi,:kaynak_url)
    """, records)
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM tohumlamalar").fetchone()[0]
    con.close()
    return total


# ── SQL export yaz ────────────────────────────────────────────────────────────

DDL_PG = """-- ================================================================
--  Tohumlama kayıtları  |  {ts}
--  Kaynak: {url}
-- ================================================================

CREATE TABLE IF NOT EXISTS tohumlamalar (
    id             BIGSERIAL PRIMARY KEY,
    hayvan_id      INTEGER       NOT NULL,
    sperma         TEXT,
    belge_no       TEXT,
    kupe_no        TEXT,
    irk            TEXT,
    not_           TEXT,
    tohumlama_tar  DATE,
    gebe           BOOLEAN,
    scrape_tarihi  DATE          NOT NULL,
    kaynak_url     TEXT
);

"""

def _esc(val) -> str:
    if val is None:          return "NULL"
    if isinstance(val, int): return str(val)
    return "'" + str(val).replace("'","''") + "'"

def write_sql(records: list[dict], path: Path, url: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", encoding="utf-8") as f:
        f.write(DDL_PG.format(ts=ts, url=url))
        f.write(f"-- {len(records)} kayıt\n\n")
        for r in records:
            # gebe integer → boolean string
            row = dict(r)
            if row["gebe"] is None:
                row["gebe"] = "NULL"
            elif row["gebe"]:
                row["gebe"] = "TRUE"
            else:
                row["gebe"] = "FALSE"
            cols = ",".join(k for k in r.keys() if k != "id")
            vals = ",".join(
                row[k] if k == "gebe" else _esc(r[k])
                for k in r.keys() if k != "id"
            )
            f.write(f"INSERT INTO tohumlamalar ({cols}) VALUES ({vals});\n")


# ── Ana akış ──────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    url = sys.argv[1].strip()
    if not url.startswith("http"):
        sys.exit("❌  Geçerli bir URL gir. Örnek: python scrape.py http://...")

    print(f"🌐  Çekiliyor: {url}")
    html    = fetch_page(url)
    records = parse_table(html, url)

    if not records:
        sys.exit("⚠️  Hiç kayıt parse edilemedi. Tablo yapısını kontrol et.")

    print(f"📋  {len(records)} kayıt parse edildi.")

    # SQLite'a ekle
    toplam = write_sqlite(records)
    print(f"💾  SQLite güncellendi  →  {DB_PATH}  (toplam {toplam} kayıt)")

    # SQL dosya adı: 2026-03-14_t_2_7867.sql
    today = date.today().isoformat()
    slug  = slug_from_url(url)
    base  = DATA_DIR / f"{today}_{slug}.sql"
    path  = next_path(base)

    write_sql(records, path, url)
    print(f"📄  SQL export       →  {path}")

if __name__ == "__main__":
    main()

