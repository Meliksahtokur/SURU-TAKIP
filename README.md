# 🐄 Sürü Takip — Tohumlama Scraper & Sorgu Aracı

## Kurulum

```bash
# 1. Klasör oluştur
mkdir sürü_takip && cd sürü_takip

# 2. Dosyaları buraya koy:
#    scrape.py  query.py  requirements.txt

# 3. Bağımlılıkları yükle
pip install -r requirements.txt
```

---

## Kullanım

### Veri çek

```bash
python scrape.py http://vethek.org/t_2_7867_MTQzMjY.htm
```

- `data/2026-03-14_t_2_7867.sql` dosyası oluşur  
- `data/tohumlamalar.db` güncellenir (birikimli)
- Aynı günde tekrar çekersen `data/2026-03-14_t_2_7867_1.sql` olur

---

### Sorgula — İnteraktif Menü

```bash
python query.py
```

Adım adım sorgu:
```
Tarih aralığı:
  1 Son 1 yıl    2 Son 6 ay    3 Son 3 ay    4 Manuel    5 Tümü
Seçim: 1

Durum filtresi:
  1 Gebeler   2 Boşlar   3 Hepsi
Seçim: 1

Küpe no (boş=tümü, birden fazla: 115+121+175): 115+175

Hayvan ID (boş=atla):
```

---

### Sorgula — Tek Satır CLI

```bash
# Son 1 yılın gebeleri
python query.py --gebe 1 --tarih 01.01.2025 bugun

# Belirli küpeler
python query.py --kupe 115 121 175

# Belirli hayvan ID'leri
python query.py --hayvan 35654 34701

# Kombine
python query.py --gebe 0 --tarih 01.06.2025 31.12.2025 --kupe 166 181
```

---

## Klasör yapısı

```
sürü_takip/
├── scrape.py
├── query.py
├── requirements.txt
└── data/
    ├── tohumlamalar.db          ← tüm scrape'lerin birikimlisi
    ├── 2026-03-14_t_2_7867.sql  ← PostgreSQL export (Supabase için)
    └── 2026-03-20_t_2_7867.sql  ← sonraki scrape
```

---

## Notlar

- `data/tohumlamalar.db` her `scrape.py` çalışmasında yeni kayıtlar eklenir, silinmez
- SQL dosyaları Supabase'e direkt import edilebilir
- Tablo yapısı sitede değişirse `scrape.py` içindeki `FALLBACK` indeksleri güncellenmeli

