import re

with open('query.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Rastgele basılan rakamları/karakterleri temizlemek zor olduğu için 
# get_bos_hayvanlar fonksiyonunu ve hatalı blokları komple uçurup temiz bir başlangıç yapalım
content = re.sub(r'def get_bos_hayvanlar.*?return con\.execute\(query\)\.fetchall\(\)', '', content, flags=re.DOTALL)

# Varsa mükerrer display_boslar fonksiyonlarını temizle
content = re.sub(r'def display_boslar.*?console\.print\(t\)', '', content, flags=re.DOTALL)

with open('query.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Dosya temizlendi. Şimdi sağlam yamayı uygulayabiliriz.")
