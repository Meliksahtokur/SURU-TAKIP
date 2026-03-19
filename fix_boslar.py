import re

with open('query.py', 'r', encoding='utf-8') as f:
    kod = f.read()

yeni_fonksiyon = """def get_bos_hayvanlar(con):
    query = '''
    SELECT 
        t.kupe_no,
        MAX(t.tohumlama_tar) as son_tohumlama_tarihi,
        COUNT(t.id) as tohumlama_sayisi
    FROM tohumlamalar t
    LEFT JOIN (
        SELECT kupe_no, MAX(tohumlama_tar) as son_gebe_tarihi
        FROM tohumlamalar
        WHERE gebe IN (1, '1', 'TRUE', 'true')
        GROUP BY kupe_no
    ) sg ON t.kupe_no = sg.kupe_no
    WHERE sg.son_gebe_tarihi IS NULL OR t.tohumlama_tar > sg.son_gebe_tarihi
    GROUP BY t.kupe_no
    ORDER BY son_tohumlama_tarihi DESC;
    '''
    return con.execute(query).fetchall()"""

kod = re.sub(r'def get_bos_hayvanlar\(con\):.*?return con\.execute\(query\)\.fetchall\(\)', yeni_fonksiyon, kod, flags=re.DOTALL)

with open('query.py', 'w', encoding='utf-8') as f:
    f.write(kod)

print("İşlem tamam. Fantezi bitti, sadece küpe no bazlı çalışıyor.")
