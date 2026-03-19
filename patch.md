Mimar, patch.py aracının işleyiş mantığını, az önce yaşadığımız "tam eşleşme" tecrübesini de (best practice olarak) dahil ederek detaylıca dokümante ettim.
Doğrudan terminaline yapıştırarak Patch.md dosyasını oluşturabileceğin komut bloğu aşağıdadır:
cat << 'EOF' > Patch.md
# patch.py Kullanım Kılavuzu

`patch.py`, proje dosyalarındaki belirli metin bloklarını bulup değiştirmek (Search & Replace) için kullanılan, standart girdi (stdin) üzerinden çalışan bir betiktir. Değişiklikleri terminal üzerinden, herhangi bir metin editörü açmadan, dosyaya yerinde (in-place) uygular.

## 📌 Temel Sözdizimi (Syntax)

Araç, bir `SEARCH:` (Aranacak) ve bir `REPLACE:` (Değiştirilecek) bloğu bekler. En pratik kullanım yöntemi `cat << 'EOF'` (Here-Document) yapısı ile metni `patch.py`'ye borulamaktır (piping).

```bash
cat << 'EOF' | python patch.py hedef_dosya.py -
SEARCH:
aranacak_eski_kod_satiri_1
aranacak_eski_kod_satiri_2
REPLACE:
yeni_kod_satiri_1
yeni_kod_satiri_2
EOF

 * hedef_dosya.py: Değişikliğin yapılacağı dosya.
 * - : Girdinin standart girdiden (stdin) okunacağını belirtir.
⚠️ Kritik Kurallar ve Çalışma Mantığı
 * Tam Eşleşme (Exact Match) Zorunluluğu: patch.py regex veya esnek arama kullanmaz. SEARCH bloğuna yazılan metin; boşluklar, sekmeler (indentation), satır sonları ve karakterler bakımından hedef dosyadaki metinle birebir aynı olmalıdır.
 * Girintiler (Indentation): Özellikle Python kodlarını yamalarken, aranan bloğun başındaki boşluk sayısı dosyadakiyle tam uyuşmazsa yama başarısız olur (Patch uygulanamadı hatası verir).
 * Çoklu Yama: Aynı komut dizisi içinde arka arkaya birden fazla cat << 'EOF' bloğu kullanılarak aynı dosya üzerinde birden fazla değişiklik art arda yapılabilir.
🛠 En İyi Uygulamalar (Best Practices)
Yamayı hazırlamadan önce, değiştirilecek bloğun orijinal halini tam olarak görmek için grep komutundan faydalanın. Hedef satırın etrafındaki birkaç satırı görmek, tam eşleşmeyi garanti eder.
Örnek Grep Kullanımı:
# display( kelimesini arar, 2 satır üstünü (-B 2) ve 2 satır altını (-A 2) gösterir.
grep -B 2 -A 2 "display(" query.py

Grep'ten çıkan orijinal satırları kopyalayıp SEARCH bloğuna yapıştırmak, yamanın ilk seferde %100 başarılı olmasını sağlar.
🚀 Örnek Kullanım
query.py dosyasındaki bir tablo genişliğini ve rengini değiştirmek:
cat << 'EOF' | python patch.py query.py -
SEARCH:
    t.add_column("Küpe No", style="white", min_width=20)
    t.add_column("Tohumlama", style="green", min_width=12)
REPLACE:
    t.add_column("Küpe No", style="white", min_width=15)
    t.add_column("Tohumlama", style="bold green", min_width=14)
EOF

EOF

Bu komutu çalıştırdığında dizininde temiz, markdown formatında bir `Patch.md` belgesi hazır olacak. Başka bir dokümantasyon veya kodlama adımına geçelim mi?

