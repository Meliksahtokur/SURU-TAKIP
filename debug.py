import sqlite3

con = sqlite3.connect("data/tohumlamalar.db")
cur = con.cursor()

gebe = cur.execute("SELECT COUNT(*) FROM tohumlamalar WHERE gebe IN (1, '1', 'TRUE', 'true')").fetchone()[0]
bos = cur.execute("SELECT COUNT(*) FROM tohumlamalar WHERE gebe IN (0, '0', 'FALSE', 'false') OR gebe IS NULL").fetchone()[0]

tekrar_giren = cur.execute("""
    WITH SonGebelikler AS (
        SELECT hayvan_id, MAX(tohumlama_tar) as son_gebe_tarihi
        FROM tohumlamalar
        WHERE gebe IN (1, '1', 'TRUE', 'true')
        GROUP BY hayvan_id
    )
    SELECT COUNT(t.id)
    FROM tohumlamalar t
    INNER JOIN SonGebelikler sg ON t.hayvan_id = sg.hayvan_id
    WHERE t.tohumlama_tar > sg.son_gebe_tarihi
""").fetchone()[0]

print(f"--- Veri Tabanı Durumu ---")
print(f"Toplam Gebe Kaydı: {gebe}")
print(f"Toplam Boş/Belirsiz Kaydı: {bos}")
print(f"Geçmişte Gebe Olup Sonra Tekrar Tohumlanan: {tekrar_giren}")
