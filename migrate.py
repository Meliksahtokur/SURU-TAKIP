import sqlite3
import requests

SUPABASE_URL = "https://zqnexqbdfvbhlxzelzju.supabase.co"
SUPABASE_KEY = "sb_publishable_-erowcVJ100DwEQrjyIyoA_AU76R12S"

print("Yerel veritabanı okunuyor...")
con = sqlite3.connect("data/tohumlamalar.db")
con.row_factory = sqlite3.Row
rows = con.execute("SELECT * FROM tohumlamalar").fetchall()

if not rows:
    print("Yerel veritabanında kayıt bulunamadı.")
    exit()

payload = []
for r in rows:
    row = dict(r)
    # Yerel ID'yi çıkarıyoruz ki Supabase kendi BIGSERIAL ID'sini atasın
    row.pop("id", None) 
    
    # Supabase boolean formatına çevir
    if row.get("gebe") == 1:
        row["gebe"] = True
    elif row.get("gebe") == 0:
        row["gebe"] = False
    else:
        row["gebe"] = None
        
    payload.append(row)

print(f"Toplam {len(payload)} kayıt Supabase'e gönderiliyor...")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}
endpoint = f"{SUPABASE_URL}/rest/v1/vethek_tohumlamalar"

resp = requests.post(endpoint, json=payload, headers=headers)

if resp.status_code in (200, 201):
    print("✅ Tüm veriler başarıyla Supabase'e aktarıldı!")
else:
    print(f"❌ Hata oluştu: {resp.status_code} - {resp.text}")
