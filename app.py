import streamlit as st
import pandas as pd
import requests
from streamlit_option_menu import option_menu
from datetime import datetime, timedelta

# --- KONFİGÜRASYON ---
SUPABASE_URL = "https://zqnexqbdfvbhlxzelzju.supabase.co"
SUPABASE_KEY = "sb_publishable_-erowcVJ100DwEQrjyIyoA_AU76R12S"
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

st.set_page_config(page_title="Çiftlik Yönetim Sistemi", page_icon="🐄", layout="wide")

@st.cache_data(ttl=60)
def fetch_from_supabase():
    """Supabase view'dan sürü analizini çeker"""
    try:
        endpoint = f"{SUPABASE_URL}/rest/v1/hayvan_durum_analizi?select=*"
        resp = requests.get(endpoint, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        df = pd.DataFrame(resp.json())
        if not df.empty:
            df["kupe_no"] = df["kupe_no"].astype(str).str.strip().str.upper()
            df["son_islem_tarihi"] = pd.to_datetime(df["son_islem_tarihi"])
        return df
    except Exception as e:
        st.sidebar.error(f"Bağlantı Hatası: {e}")
    return pd.DataFrame()

def analyze_herd_status(df):
    """View'dan gelen veriyi dashboard için ayırır"""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df_inactive = df[df["pasif_mi"] == True].copy()
    df_active = df[df["pasif_mi"] == False].copy()
    action_mask = (
        df_active["hic_gebe_kalmadi"] |
        (df_active["son_gebe_sonrasi_tohumlama"] & ~df_active["gebe_mi"]) |
        df_active["tohumlama_zamani"]
    )
    df_action = df_active[action_mask].copy()
    return df_active, df_inactive, df_action
    
    return df_active, df_inactive, df_action

df_raw = fetch_from_supabase()

# --- ÜST NAVİGASYON ---
selected = option_menu(
    menu_title=None, 
    options=["Dashboard", "Hayvanlar", "Stok", "Ayarlar"], 
    icons=["house", "cow", "box-seam", "gear"], 
    orientation="horizontal",
    styles={"nav-link-selected": {"background-color": "#2E7D32"}}
)

# --- YAN PANEL (SIDEBAR) ---
st.sidebar.header("🔍 Filtreler")
search_query = st.sidebar.text_input("Küpe No Ara (Son haneler)", placeholder="Örn: 0148").strip().upper()

selected_kno = None
pasif_goruntule = st.sidebar.checkbox("Pasif hayvanları göster", value=False)

if not df_raw.empty and search_query:
    matches = df_raw[df_raw["kupe_no"].str.endswith(search_query)]["kupe_no"].unique()
    if len(matches) > 0:
        selected_kno = st.sidebar.selectbox("Eşleşen Hayvanı Seç:", matches)
    else:
        st.sidebar.warning("Eşleşme yok.")

st.sidebar.divider()
st.sidebar.header("📥 Veri Senkronizasyonu")
if st.sidebar.button("🔄 SQLite → Supabase Sync"):
    with st.sidebar.status("Senkronize ediliyor..."):
        try:
            import subprocess
            result = subprocess.run(["python", "migrate.py"], capture_output=True, text=True)
            if result.returncode == 0:
                st.sidebar.success("✅ Senkronizasyon tamam!")
                st.cache_data.clear()
            else:
                st.sidebar.error(f"❌ Hata: {result.stderr}")
        except Exception as e:
            st.sidebar.error(f"❌ Hata: {e}")

vethek_url = st.sidebar.text_input("Vethek URL (scrape için)")
if st.sidebar.button("🌐 Veri Kazı ve Sync"):
    with st.sidebar.status("Kazınıyor ve senkronize ediliyor..."):
        try:
            import subprocess
            # Önce scrape
            subprocess.run(["python", "scrape.py", vethek_url], check=True)
            # Sonra migrate
            result = subprocess.run(["python", "migrate.py"], capture_output=True, text=True)
            if result.returncode == 0:
                st.sidebar.success("✅ Kazıma ve senkronizasyon tamam!")
                st.cache_data.clear()
            else:
                st.sidebar.error(f"❌ Migrate hatası: {result.stderr}")
        except subprocess.CalledProcessError as e:
            st.sidebar.error(f"❌ Scrape hatası: {e}")
        except Exception as e:
            st.sidebar.error(f"❌ Beklenmeyen hata: {e}")

# --- ANA EKRAN MANTIĞI ---
if df_raw.empty:
    st.warning("Veri bekleniyor...")
else:
    today = pd.Timestamp.now().normalize()
    
    # Sürü analizini yap
    df_active, df_inactive, df_action = analyze_herd_status(df_raw)
    
    # Her hayvanın son durumu (tüm aktifler için)
    df_latest = df_active.copy()
    df_latest["Gun"] = df_latest["gecen_gun"]

    if selected == "Dashboard":
        st.title("🚜 Sürü Özeti")
        
        # Aktif gebeler (son gebelik 300 günden az)
        active_gebe_mask = (df_latest["gebe_mi"] == True) & (df_latest["Gun"] <= 300)
        
        # Metrikler
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🏠 Aktif Toplam", f"{len(df_active)} Baş")
        m2.metric("✅ Aktif Gebe", f"{len(df_latest[active_gebe_mask])} Baş")
        m3.metric("⚠️ Aksiyon Bekleyen", f"{len(df_action)} Baş")
        m4.metric("📉 Pasif (2025 öncesi)", f"{len(df_inactive)} Baş")
        
        st.divider()
        
        tab1, tab2, tab3, tab4 = st.tabs(["⚠️ Aksiyon Bekleyenler", "✅ Aktif Gebeler", "📉 Pasif Hayvanlar", "📅 Takvim"])
        
        with tab1:
            st.subheader(f"Aksiyon Bekleyen Hayvanlar ({len(df_action)} baş)")
            
            if not df_action.empty:
                # Detaylı bilgileri ekle
                df_action_display = df_action.copy()
                df_action_display['son_islem_tarih'] = pd.to_datetime(df_action_display['son_islem']).dt.strftime('%Y-%m-%d')
                
                # Durum açıklaması
                def get_action_reason(row):
                    if row['hic_gebe_kalmadi']:
                        return '🐮 Hiç gebe kalmamış - İlk tohumlama'
                    elif row['tohumlamaya_hazir']:
                        return f"🤱 Doğum üzerinden {int(row['dogum_sonrasi_gun'])} gün - Tohumlama zamanı"
                    elif row['son_gebe_sonrasi_tohumlama'] and not row['gebe_mi']:
                        return '🔄 Gebelik sonrası tohumlandı - Kontrol gerekli'
                    else:
                        return '❓ Diğer'
                
                df_action_display['neden'] = df_action_display.apply(get_action_reason, axis=1)
                
                # Tahmini doğum tarihi olanları formatla
                if 'tahmini_dogum' in df_action_display.columns:
                    df_action_display['tahmini_dogum'] = pd.to_datetime(df_action_display['tahmini_dogum']).dt.strftime('%Y-%m-%d')
                
                # Tabloyu göster
                display_columns = ['kupe_no', 'son_islem_tarih', 'gun', 'neden', 'T.No', 'sperma']
                if 'tahmini_dogum' in df_action_display.columns:
                    display_columns.insert(3, 'tahmini_dogum')
                
                st.dataframe(
                    df_action_display[display_columns]
                    .rename(columns={
                        'kupe_no': 'Küpe No', 
                        'son_islem_tarih': 'Son İşlem', 
                        'gun': 'Gün', 
                        'neden': 'Aksiyon Nedeni',
                        'tahmini_dogum': 'Tahmini Doğum',
                        'T.No': 'T.No', 
                        'sperma': 'Sperma'
                    })
                    .sort_values('Gün', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
                
                # İstatistik kartları
                st.divider()
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    hic_gebe = len(df_action[df_action['hic_gebe_kalmadi']])
                    st.info(f"🐮 **Hiç gebe kalmamış:** {hic_gebe} baş")
                    
                with col2:
                    tohumlama_hazir = len(df_action[df_action['tohumlamaya_hazir']])
                    if tohumlama_hazir > 0:
                        st.success(f"🤱 **Doğum sonrası tohumlama hazır:** {tohumlama_hazir} baş")
                    else:
                        st.info(f"🤱 **Doğum sonrası tohumlama hazır:** 0 baş")
                    
                with col3:
                    kontrol = len(df_action[~df_action['hic_gebe_kalmadi'] & ~df_action['tohumlamaya_hazir']])
                    st.warning(f"🔄 **Kontrol gerekli:** {kontrol} baş")
            else:
                st.success("✅ Aksiyon bekleyen hayvan bulunmuyor!")
            
        with tab2:
            st.subheader(f"Aktif Gebe Hayvanlar ({len(df_latest[active_gebe_mask])} baş)")
            if not df_latest[active_gebe_mask].empty:
                df_preg = df_latest[active_gebe_mask].sort_values("Gun", ascending=False).copy()
                df_preg["Tarih"] = df_preg["son_islem_tarihi"].dt.strftime('%Y-%m-%d')
                df_preg["Kalan"] = 285 - df_preg["Gun"]
                st.dataframe(
                    df_preg[["kupe_no", "Tarih", "T.No", "Gun", "Kalan", "sperma"]]
                    .rename(columns={"kupe_no": "Küpe No", "Tarih": "Tohumlama", "Gun": "Gebe Gün", "Kalan": "Kalan Gün", "sperma": "Sperma"}),
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("Aktif gebe hayvan bulunmuyor.")
        
        with tab3:
            if pasif_goruntule and not df_inactive.empty:
                st.subheader(f"Pasif Hayvanlar (2025 öncesi kayıt) - {len(df_inactive)} baş")
                df_inactive_display = df_inactive.copy()
                df_inactive_display['son_islem_tarihi'] = pd.to_datetime(df_inactive_display['son_islem_tarihi']).dt.strftime('%Y-%m-%d')
                st.dataframe(
                    df_inactive_display[['kupe_no', 'son_islem_tarihi', 'gecen_gun']]
                    .rename(columns={'kupe_no': 'Küpe No', 'son_islem_tarihi': 'Son İşlem', 'gecen_gun': 'Gün'}),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Pasif hayvan bulunmuyor veya gösterilmiyor. Görmek için sol menüdeki kutucuğu işaretleyin.")

    elif selected == "Hayvanlar":
        if selected_kno:
            # --- HAYVAN KARTI (CONTAINER) ---
            st.title(f"🐄 Hayvan Kartı: {selected_kno}")
            df_single = df_raw[df_raw["kupe_no"] == selected_kno].copy()
            df_single["Tarih"] = df_single["son_islem_tarihi"].dt.strftime('%Y-%m-%d')
            
            # Hayvanın detaylı analizini bul
            animal_detail = df_active[df_active['kupe_no'] == selected_kno].iloc[0] if not df_active.empty and selected_kno in df_active['kupe_no'].values else None
            
            with st.container(border=True):
                # Üst satır - temel bilgiler
                col1, col2, col3, col4 = st.columns(4)
                is_gebe = df_single.iloc[0]["gebe"]
                
                col1.metric("Güncel Durum", "✅ GEBE" if is_gebe else "❌ BOŞ")
                col2.metric("Durum", "🟢 Aktif" if animal_detail is not None else "🔴 Pasif")
                col3.metric("Dönem Tohumlama", int(df_single.iloc[0]["T.No"]))
                col4.metric("Son İşlemden Beri", f"{int(df_single.iloc[0]['gecen_gun'])} Gün")
                
                st.divider()
                
                # İkinci satır - detaylı analiz
                if animal_detail is not None:
                    col1, col2, col3 = st.columns(3)
                    
                    # Gebelik geçmişi
                    ever_pregnant = animal_detail['gebe_kaldi']
                    if ever_pregnant:
                        col1.success(f"📊 **Gebelik Sayısı:** {df_single[df_single['gebe'] == True].shape[0]}")
                    else:
                        col1.warning("⚠️ **Hiç gebe kalmamış**")
                    
                    # Son gebelik bilgisi
                    if animal_detail['son_gebe_tarihi'] is not None and pd.notna(animal_detail['son_gebe_tarihi']):
                        son_gebe = pd.to_datetime(animal_detail['son_gebe_tarihi'])
                        col2.info(f"🤰 **Son Gebelik:** {son_gebe.strftime('%Y-%m-%d')}")
                        
                        # Tahmini doğum
                        if animal_detail['tahmini_dogum'] is not None and pd.notna(animal_detail['tahmini_dogum']):
                            tahmini_dogum = pd.to_datetime(animal_detail['tahmini_dogum'])
                            col3.info(f"👶 **Tahmini Doğum:** {tahmini_dogum.strftime('%Y-%m-%d')}")
                            
                            # Doğuma kalan gün
                            kalan_gun = (tahmini_dogum - today).days
                            if kalan_gun > 0:
                                st.metric("📅 Doğuma Kalan Gün", f"{kalan_gun} gün")
                            elif animal_detail['dogum_sonrasi_gun'] and animal_detail['dogum_sonrasi_gun'] > 0:
                                st.metric("👶 Doğum Üzerinden", f"{int(animal_detail['dogum_sonrasi_gun'])} gün")
                    else:
                        col2.info("🤰 **Son Gebelik:** Yok")
                    
                    # Tohumlama durumu
                    if animal_detail['tohumlamaya_hazir']:
                        st.success(f"✅ **Tohumlama Zamanı!** - Doğum üzerinden {int(animal_detail['dogum_sonrasi_gun'])} gün geçmiş.")
            
            st.subheader("📜 İşlem Geçmişi")
            st.dataframe(df_single[["Tarih", "gebe", "T.No", "sperma", "not_"]], use_container_width=True, hide_index=True)
        else:
            st.info("🔍 Lütfen sol panelden bir küpe numarası arayın veya seçin.")
            
            # Tüm hayvanları listele (aktif/pasif filtresiyle)
            st.subheader("📋 Tüm Hayvanlar")
            
            if pasif_goruntule:
                display_df = pd.concat([
                    df_active.assign(Durum='Aktif'),
                    df_inactive.assign(Durum='Pasif')
                ]) if not df_inactive.empty else df_active.assign(Durum='Aktif')
            else:
                display_df = df_active.assign(Durum='Aktif')
            
            if not display_df.empty:
                display_df['son_islem'] = pd.to_datetime(display_df['son_islem']).dt.strftime('%Y-%m-%d')
                st.dataframe(
                    display_df[['kupe_no', 'son_islem', 'gun', 'Durum', 'gebe_mi']]
                    .rename(columns={'kupe_no': 'Küpe No', 'son_islem': 'Son İşlem', 'gun': 'Gün', 'gebe_mi': 'Gebe'})
                    .sort_values('Küpe No'),
                    use_container_width=True,
                    hide_index=True
                )

    elif selected == "Stok":
        st.title("📦 Stok ve Envanter")
        
        tab1, tab2 = st.tabs(["📊 Stok Durumu", "📈 Kullanım Raporu"])
        
        
        with stok_tab2:
            st.subheader("📈 Kullanım Raporu")
            
            # Aylık tohumlama sayıları
            if not df_raw.empty:
                df_raw['ay'] = df_raw['son_islem_tarihi'].dt.to_period('M')
                aylik_tohumlama = df_raw.groupby('ay').size().reset_index(name='sayi')
                aylik_tohumlama['ay'] = aylik_tohumlama['ay'].astype(str)
                
                st.subheader("Aylık Tohumlama Sayıları")
                st.dataframe(aylik_tohumlama, use_container_width=True, hide_index=True)
        with tab1:
            st.info("Stok modülü geliştirme aşamasında...")
            
            # Basit sperma stok takibi
            if not df_raw.empty:
                sperma_kullanim = df_raw['sperma'].value_counts().reset_index()
                sperma_kullanim.columns = ['Sperma', 'Kullanım Sayısı']
                st.subheader("Sperma Kullanım İstatistikleri")
                st.dataframe(sperma_kullanim, use_container_width=True, hide_index=True)
        
        with tab2:
            st.info("Rapor modülü geliştirme aşamasında...")
            
            # Aylık tohumlama sayıları
            df_raw['ay'] = df_raw['son_islem_tarihi'].dt.to_period('M')
            aylik_tohumlama = df_raw.groupby('ay').size().reset_index(name='sayi')
            aylik_tohumlama['ay'] = aylik_tohumlama['ay'].astype(str)
            
            st.subheader("Aylık Tohumlama Sayıları")
            st.dataframe(aylik_tohumlama, use_container_width=True, hide_index=True)

    elif selected == "Ayarlar":
        st.title("⚙️ Sistem Ayarları")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Veri Yönetimi")
            if st.button("🔄 Verileri Zorla Yenile", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            
            if st.button("📊 İstatistikleri Hesapla", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        
        with col2:
            st.subheader("Sistem Bilgileri")
            if not df_raw.empty:
                st.metric("Toplam Kayıt", len(df_raw))
                st.metric("Aktif Hayvan", len(df_active))
                st.metric("Pasif Hayvan", len(df_inactive))
                st.metric("Aksiyon Bekleyen", len(df_action))
                
                en_eski = df_raw['son_islem_tarihi'].min()
                en_yeni = df_raw['son_islem_tarihi'].max()
                st.write(f"📅 En eski kayıt: {en_eski.strftime('%Y-%m-%d')}")
                st.write(f"📅 En yeni kayıt: {en_yeni.strftime('%Y-%m-%d')}")

# Takvim modülü lazy load (EN ÜSTE ALINDI)
try:
    from calendar_events import CiftlikTakvimi
    takvim_available = True
except ImportError:
    takvim_available = False
    st.warning("Takvim modülü yüklenemedi, plotly kurulu mu?")