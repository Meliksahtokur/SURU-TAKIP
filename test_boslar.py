import sqlite3
from datetime import datetime
from rich.console import Console
from rich.table import Table

def test_bos_hayvanlar_sorgusu(db_path="data/tohumlamalar.db"):
    # SQLite bağlantısı
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Özel SQL Sorgumuz:
    # 1. Her hayvanın en son gebe kaldığı tarihi bul (CTE: SonGebelikler)
    # 2. Ana tablo ile birleştirip, sadece son gebelikten SONRAKİ boş tohumlamaları say
    query = """
    WITH SonGebelikler AS (
        SELECT hayvan_id, MAX(tohumlama_tar) as son_gebe_tarihi
        FROM tohumlamalar
        WHERE gebe = 1 OR gebe = 'TRUE'
        GROUP BY hayvan_id
    ),
    GuncelDurum AS (
        SELECT 
            t.hayvan_id,
            t.kupe_no,
            MAX(t.tohumlama_tar) as son_tohumlama_tarihi,
            COUNT(t.id) as tohumlama_sayisi
        FROM tohumlamalar t
        LEFT JOIN SonGebelikler sg ON t.hayvan_id = sg.hayvan_id
        WHERE (sg.son_gebe_tarihi IS NULL OR t.tohumlama_tar > sg.son_gebe_tarihi)
          AND (t.gebe = 0 OR t.gebe IS NULL OR t.gebe = 'FALSE')
        GROUP BY t.hayvan_id, t.kupe_no
    )
    SELECT kupe_no, son_tohumlama_tarihi, tohumlama_sayisi 
    FROM GuncelDurum 
    ORDER BY son_tohumlama_tarihi DESC;
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"SQL Hatası: {e}")
        return
    finally:
        conn.close()

    # Rich Tablosu Tasarımı
    console = Console()
    table = Table(title=f"Boşlar — {len(rows)} kayıt", show_header=True, header_style="bold magenta")
    table.add_column("Küpe No", style="cyan", width=15)
    table.add_column("Son Tohumlama", style="green", justify="center")
    table.add_column("Geçen Gün", style="yellow", justify="center")
    table.add_column("Tohumlama Sayısı", style="red", justify="center")

    bugun = datetime.now()

    for row in rows:
        kupe_no = str(row[0])
        son_tohumlama_str = row[1]
        tohumlama_sayisi = str(row[2])
        
        # Geçen günü hesapla
        gecen_gun = "—"
        if son_tohumlama_str:
            try:
                # Veritabanındaki tarih formatına göre (Örn: 2026-03-14)
                son_tohumlama_date = datetime.strptime(son_tohumlama_str, "%Y-%m-%d")
                fark = (bugun - son_tohumlama_date).days
                gecen_gun = str(fark)
            except ValueError:
                pass # Tarih formatı farklıysa tire kalır

        table.add_row(kupe_no, son_tohumlama_str, gecen_gun, tohumlama_sayisi)

    console.print(table)

if __name__ == "__main__":
    test_bos_hayvanlar_sorgusu()
