#!/usr/bin/env python3
"""
query.py  —  Tohumlama interaktif CLI sorgu aracı
--------------------------------------------------
Kullanım:
    python query.py              # interaktif menü
    python query.py --help       # tüm seçenekler

Gereksinim: pip install rich
"""

import sys
import re
import sqlite3
import argparse
from datetime import date, timedelta
from pathlib import Path

try:
    from rich.console import Console
    from rich.table   import Table
    from rich.prompt  import Prompt
    from rich.panel   import Panel
    from rich         import box
    from rich.text    import Text
except ImportError:
    sys.exit("❌  rich yüklü değil:  pip install rich")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH  = DATA_DIR / "tohumlamalar.db"

console = Console()


# ── DB ────────────────────────────────────────────────────────────────────────

def get_conn(db: Path = DB_PATH) -> sqlite3.Connection:
    if not db.exists():
        console.print(f"[red]❌  {db} bulunamadı.[/red]  Önce scrape.py çalıştır.")
        sys.exit(1)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con


# ── Sorgu motoru ──────────────────────────────────────────────────────────────

def run_query(
    con: sqlite3.Connection,
    hayvan_ids: list[int] | None = None,
    kupe_nos:   list[str] | None = None,
    gebe:       int | None = None,       # 1=gebe, 0=boş, None=hepsi
    tarih_bas:  str | None = None,
    tarih_bit:  str | None = None,
    scrape_gun: str | None = None,       # belirli scrape tarihi
) -> list[sqlite3.Row]:

    where, params = [], []

    if hayvan_ids:
        ph = ",".join("?" * len(hayvan_ids))
        where.append(f"hayvan_id IN ({ph})")
        params.extend(hayvan_ids)

    if kupe_nos:
        ph = ",".join("?" * len(kupe_nos))
        where.append(f"kupe_no IN ({ph})")
        params.extend(kupe_nos)

    if gebe == 1:
        where.append("gebe = 1")
        where.append("(julianday('now') - julianday(tohumlama_tar)) <= 285")
    elif gebe == 0:
        where.append("(gebe = 0 OR gebe IS NULL OR (julianday('now') - julianday(tohumlama_tar)) > 285)")

    if tarih_bas:
        where.append("tohumlama_tar >= ?")
        params.append(tarih_bas)

    if tarih_bit:
        where.append("tohumlama_tar <= ?")
        params.append(tarih_bit)

    if scrape_gun:
        where.append("scrape_tarihi = ?")
        params.append(scrape_gun)

    # Her hayvanın sadece son tohumlama kaydını al
    sql = """
        SELECT * FROM tohumlamalar t1
        WHERE tohumlama_tar = (
            SELECT MAX(tohumlama_tar) FROM tohumlamalar t2
            WHERE t2.kupe_no = t1.kupe_no AND t2.kupe_no != ''
        )
    """
    if where:
        sql += " AND " + " AND ".join(where)
    sql += " ORDER BY tohumlama_tar DESC"

    return con.execute(sql, params).fetchall()


# ── Görüntüleme ───────────────────────────────────────────────────────────────













def get_bos_hayvanlar(con):
    query = '''
    SELECT t.kupe_no, MAX(t.tohumlama_tar) as son_tohumlama_tarihi, COUNT(t.id) as tohumlama_sayisi
    FROM tohumlamalar t
    LEFT JOIN (
        SELECT kupe_no, MAX(tohumlama_tar) as son_gebe_tarihi
        FROM tohumlamalar WHERE gebe IN (1, '1', 'TRUE', 'true') GROUP BY kupe_no
    ) sg ON t.kupe_no = sg.kupe_no
    WHERE sg.son_gebe_tarihi IS NULL OR t.tohumlama_tar > sg.son_gebe_tarihi
    GROUP BY t.kupe_no ORDER BY son_tohumlama_tarihi DESC
    '''
    return con.execute(query).fetchall()

def display_boslar(rows, baslik, dar=False):
    t = Table(title=f"{baslik}  —  {len(rows)} kayıt", box=box.SIMPLE_HEAVY)
    t.add_column("Küpe No", style="white", min_width=15)
    t.add_column("Son Tohumlama", style="green", justify="center")
    t.add_column("Geçen Gün", style="yellow", justify="center")
    t.add_column("Tohumlama Sayısı", style="red", justify="center")
    from datetime import datetime
    for r in rows:
        gecen = "—"
        if r["son_tohumlama_tarihi"]:
            try:
                tarih_str = str(r["son_tohumlama_tarihi"])[:10]
                d = datetime.strptime(tarih_str, "%Y-%m-%d")
                gecen = str((datetime.now() - d).days)
            except Exception: 
                gecen = "ERR"
        t.add_row(str(r["kupe_no"]), str(r["son_tohumlama_tarihi"])[:10] if r["son_tohumlama_tarihi"] else "—", gecen, str(r["tohumlama_sayisi"]))
    console.print(t)

def display(rows: list[sqlite3.Row], baslik: str = "Sonuçlar", dar: bool = False):
    if not rows:
        console.print("[yellow]⚠️  Kayıt bulunamadı.[/yellow]")
        return

    t = Table(
        title=f"{baslik}  —  {len(rows)} kayıt",
        box=box.SIMPLE_HEAVY,
        highlight=True,
        show_lines=True,
    )

    t.add_column("Küpe No",      style="white",   min_width=15)
    if not dar:
        t.add_column("Tohumlama", style="green",  min_width=12, no_wrap=True)
    t.add_column("Gebe Gün",     style="magenta", min_width=8,  no_wrap=True)
    t.add_column("Tahmini Doğum", style="cyan",   min_width=12, no_wrap=True)


    for r in rows:
        if r["gebe"] == 1:
            gebe_str = "[green]✓ Gebe[/green]"
        elif r["gebe"] == 0:
            gebe_str = "[red]✗ Boş[/red]"
        else:
            gebe_str = "[dim]?[/dim]"

        from datetime import date as _date, timedelta
        gun = "—"
        dogum = "—"
        if r["gebe"] == 1 and r["tohumlama_tar"]:
            try:
                toh = _date.fromisoformat(r["tohumlama_tar"])
                gecen = (_date.today() - toh).days
                if gecen > 285:
                    gun = "—"   # doğum yapmış, artık gebe değil
                    dogum = "—"
                else:
                    gun_str = str(gecen) + " gün"
                    gun = "⚠️ " + gun_str if gecen >= 260 else gun_str
                    dogum = str(toh + timedelta(days=285))
            except:
                pass

        if dar:
            t.add_row(r["kupe_no"] or "—", gun, dogum)
        else:
            t.add_row(r["kupe_no"] or "—", r["tohumlama_tar"] or "—", gun, dogum)

    console.print(t)


# ── Tarih yardımcıları ────────────────────────────────────────────────────────

def parse_tarih_input(raw: str) -> str | None:
    """DD.MM.YYYY, DD/MM/YYYY veya YYYY-MM-DD kabul et."""
    raw = raw.strip()
    if not raw:
        return None
    m = re.match(r"(\d{2})[./](\d{2})[./](\d{4})", raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return raw
    return None

def tarih_n_gun_once(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


# ── Scrape tarihleri ──────────────────────────────────────────────────────────

def list_scrape_dates(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        "SELECT DISTINCT scrape_tarihi FROM tohumlamalar ORDER BY scrape_tarihi DESC"
    ).fetchall()
    return [r[0] for r in rows if r[0]]


# ── İnteraktif menü ───────────────────────────────────────────────────────────

HEADER = """
[bold cyan]🐄  Tohumlama Sorgu Terminali[/bold cyan]
[dim]data/tohumlamalar.db  |  çıkış: q[/dim]
"""

DAR_EKRAN = False  # açılışta ayarlanır

def menu_tarih() -> tuple[str | None, str | None]:
    console.print("\n[bold]Tarih aralığı:[/bold]")
    console.print(
        "  [bold]1[/bold] Son 1 yıl    "
        "  [bold]2[/bold] Son 6 ay     "
        "  [bold]3[/bold] Son 3 ay     "
        "  [bold]4[/bold] Manuel giriş "
        "  [bold]5[/bold] Tümü"
    )
    s = Prompt.ask("Seçim", default="1").strip()

    today = date.today().isoformat()

    if s == "1": return tarih_n_gun_once(365), today
    if s == "2": return tarih_n_gun_once(180), today
    if s == "3": return tarih_n_gun_once(90),  today
    if s == "5": return None, None

    # Manuel
    bas_raw = Prompt.ask("Başlangıç (GG.AA.YYYY veya YYYY-AA-GG)", default="01.01.2025")
    bit_raw = Prompt.ask("Bitiş     (GG.AA.YYYY veya YYYY-AA-GG)", default=today)
    return parse_tarih_input(bas_raw), parse_tarih_input(bit_raw)

def menu_gebe() -> int | None:
    console.print("\n[bold]Durum filtresi:[/bold]")
    console.print("  [bold]1[/bold] Gebeler   [bold]2[/bold] Boşlar   [bold]3[/bold] Hepsi")
    s = Prompt.ask("Seçim", default="3").strip()
    if s == "1": return 1
    if s == "2": return 0
    return None

def menu_kupe() -> list[str] | None:
    raw = Prompt.ask(
        "\n[bold]Küpe no[/bold] "
        "[dim](boş=tümü, birden fazla: 115+121+175)[/dim]",
        default=""
    ).strip()
    if not raw:
        return None
    parts = [p.strip() for p in re.split(r"[+,; ]+", raw) if p.strip()]
    return parts or None

def menu_hayvan() -> list[int] | None:
    raw = Prompt.ask(
        "\n[bold]Hayvan ID[/bold] "
        "[dim](boş=tümü, birden fazla: 35654+34701)[/dim]",
        default=""
    ).strip()
    if not raw:
        return None
    parts = [p.strip() for p in re.split(r"[+,; ]+", raw) if p.strip()]
    ids = []
    for p in parts:
        if p.isdigit():
            ids.append(int(p))
    return ids or None

def interaktif():
    global DAR_EKRAN
    console.print(HEADER)
    ekran = Prompt.ask("Ekran tipi", choices=["telefon", "tablet"], default="tablet").strip()
    DAR_EKRAN = ekran == "telefon"
    con = get_conn()

    # İstatistik özeti
    total = con.execute("SELECT COUNT(*) FROM tohumlamalar").fetchone()[0]
    gebe  = con.execute("SELECT COUNT(*) FROM tohumlamalar WHERE gebe=1").fetchone()[0]
    bos   = con.execute("SELECT COUNT(*) FROM tohumlamalar WHERE gebe=0 OR gebe IS NULL").fetchone()[0]
    tarihler = list_scrape_dates(con)
    console.print(
        f"[dim]DB özeti: {total} tohumlama kaydı  |  "
        f"Gebe: {gebe}  Boş/Bilinmiyor: {bos}  |  "
        f"Scrape sayısı: {len(tarihler)}[/dim]\n"
    )

    while True:
        console.rule("[dim]Yeni sorgu[/dim]")

        # Tarih
        tarih_bas, tarih_bit = menu_tarih()

        # Durum
        gebe_filtre = menu_gebe()

        # Küpe
        kupe_nos = menu_kupe()

        # Hayvan ID (isteğe bağlı, genelde küpe yeterli)
        h_raw = Prompt.ask(
            "\n[bold]Hayvan ID[/bold] [dim](boş=atla)[/dim]", default=""
        ).strip()
        hayvan_ids = None
        if h_raw:
            hayvan_ids = [int(p) for p in re.split(r"[+,; ]+", h_raw) if p.strip().isdigit()]

        rows = run_query(
            con,
            hayvan_ids=hayvan_ids,
            kupe_nos=kupe_nos,
            gebe=gebe_filtre,
            tarih_bas=tarih_bas,
            tarih_bit=tarih_bit,
        )

        # Başlık özeti
        parts = []
        if tarih_bas: parts.append(f"{tarih_bas} → {tarih_bit or 'bugün'}")
        if gebe_filtre == 1: parts.append("Gebeler")
        elif gebe_filtre == 0: parts.append("Boşlar")
        if kupe_nos:   parts.append("Küpe: " + "+".join(kupe_nos))
        if hayvan_ids: parts.append("ID: " + "+".join(str(i) for i in hayvan_ids))
        baslik = "  |  ".join(parts) if parts else "Tüm kayıtlar"

        if "Boş" in baslik:
            bos_rows = get_bos_hayvanlar(con)
            display_boslar(bos_rows, "Laktasyona Tekrar Giren Boşlar", dar=DAR_EKRAN)
        else:
            if args.kupe:
                # Küpe aramasında tarih/gebe filtresiz tam döküm
                q = f"SELECT * FROM tohumlamalar WHERE kupe_no IN ({','.join(['?']*len(args.kupe))}) ORDER BY tohumlama_tar DESC"
                rows = con.execute(q, args.kupe).fetchall()
                baslik = f"Küpe Geçmişi: {', '.join(args.kupe)}"
                display(rows, baslik, dar=DAR_EKRAN)
            elif args.gebe == 0:
                r = get_bos_hayvanlar(con)
                display_boslar(r, "Laktasyona Tekrar Giren Boşlar", dar=DAR_EKRAN)
            else:
                display(rows, baslik, dar=DAR_EKRAN)

        devam = Prompt.ask(
            "\n[dim]Yeni sorgu[/dim] ([bold]Enter[/bold]) "
            "ya da [bold]q[/bold] çıkış",
            default=""
        ).strip().lower()
        if devam in ("q", "quit", "exit", "çıkış"):
            console.print("[dim]Güle güle.[/dim]")
            break

    con.close()


# ── CLI (argparse) modu ───────────────────────────────────────────────────────

def cli_mode():
    ap = argparse.ArgumentParser(
        description="Tohumlama kayıt sorgulayıcı",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python query.py                                   # interaktif menü
  python query.py --kupe 115 121 175
  python query.py --gebe 1 --tarih 01.01.2025 bugün
  python query.py --hayvan 35654 34701
  python query.py --gebe 0 --tarih 01.06.2025 31.12.2025
        """
    )
    ap.add_argument("--hayvan", nargs="+", type=int, help="Hayvan ID(leri)")
    ap.add_argument("--kupe",   nargs="+", type=str, help="Küpe no(ları)")
    ap.add_argument("--gebe",   type=int, choices=[0,1], help="1=gebe 0=boş")
    ap.add_argument("--tarih",  nargs=2, metavar=("BAS","BIT"),
                    help="Tarih aralığı: GG.AA.YYYY GG.AA.YYYY")

    args = ap.parse_args()

    # Hiç argüman yoksa interaktif
    if len(sys.argv) == 1:
        interaktif()
        return

    tarih_bas = tarih_bit = None
    if args.tarih:
        t1, t2 = args.tarih
        tarih_bas = tarih_n_gun_once(365) if t1 in ("son1yil","1y") else parse_tarih_input(t1)
        tarih_bit = date.today().isoformat() if t2 in ("bugün","bugun","today") else parse_tarih_input(t2)

    con = get_conn()
    rows = run_query(
        con,
        hayvan_ids=args.hayvan,
        kupe_nos=args.kupe,
        gebe=args.gebe,
        tarih_bas=tarih_bas,
        tarih_bit=tarih_bit,
    )
    if args.gebe == 0:
        bos_rows = get_bos_hayvanlar(con)
        display_boslar(bos_rows, "Laktasyona Tekrar Giren Boşlar", dar=DAR_EKRAN if 'DAR_EKRAN' in globals() else False)
    else:
        display(rows)
    con.close()


if __name__ == "__main__":
    cli_mode()

