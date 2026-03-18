import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

class CiftlikTakvimi:
    """Çiftlik için zaman bazlı event yönetimi"""
    
    def __init__(self, df_raw, df_active):
        self.df_raw = df_raw
        self.df_active = df_active
        self.today = pd.Timestamp.now().normalize()
        self.gestation = 285  # gün
        self.waiting = 60      # doğum sonrası bekleme
        
    def generate_events(self):
        """Tüm hayvanlar için eventleri oluştur"""
        events = []
        
        for _, animal in self.df_active.iterrows():
            animal_data = self.df_raw[self.df_raw['kupe_no'] == animal['kupe_no']]
            
            # 1. Kızgınlık tahmini (son tohumlamadan 21 gün sonra)
            if not animal['gebe_mi'] and animal['gun'] > 0:
                next_heat = animal['son_islem'] + timedelta(days=21)
                events.append({
                    'tarih': next_heat,
                    'hayvan': animal['kupe_no'],
                    'tip': 'heat',
                    'aciklama': f'Tahmini kızgınlık (son tohumlamadan 21 gün)',
                    'oncelik': 'Yüksek' if animal['gun'] > 40 else 'Normal',
                    'gun': (next_heat - self.today).days
                })
            
            # 2. Doğum tahmini
            if animal['gebe_mi'] and animal.get('tahmini_dogum') is not None:
                if pd.notna(animal['tahmini_dogum']):
                    events.append({
                        'tarih': animal['tahmini_dogum'],
                        'hayvan': animal['kupe_no'],
                        'tip': 'birth',
                        'aciklama': f'Tahmini doğum',
                        'oncelik': 'Kritik',
                        'gun': (animal['tahmini_dogum'] - self.today).days
                    })
            
            # 3. Tohumlama zamanı
            if animal.get('tohumlamaya_hazir'):
                events.append({
                    'tarih': self.today,
                    'hayvan': animal['kupe_no'],
                    'tip': 'insemination',
                    'aciklama': f'TOHUMLAMA ZAMANI! Doğum üzerinden {int(animal["dogum_sonrasi_gun"])} gün',
                    'oncelik': 'Acil',
                    'gun': 0
                })
            
            # 4. Gebelik kontrolü (45. gün)
            if animal['gebe_mi'] and animal['gun'] >= 45 and animal['gun'] <= 50:
                events.append({
                    'tarih': self.today,
                    'hayvan': animal['kupe_no'],
                    'tip': 'check',
                    'aciklama': 'Gebelik kontrolü zamanı (45-50 gün)',
                    'oncelik': 'Yüksek',
                    'gun': 0
                })
        
        if events:
            return pd.DataFrame(events)
        return pd.DataFrame()
    
    def get_weekly_agenda(self):
        """Haftalık ajanda oluştur"""
        events = self.generate_events()
        if events.empty:
            return pd.DataFrame()
        
        # Önümüzdeki 7 gün
        next_week = self.today + timedelta(days=7)
        weekly = events[
            (pd.to_datetime(events['tarih']) >= self.today) & 
            (pd.to_datetime(events['tarih']) <= next_week)
        ].sort_values('tarih')
        
        return weekly
    
    def render_calendar_view(self):
        """Takvim görünümü"""
        events = self.generate_events()
        if events.empty:
            st.info("Takvimde event bulunmuyor.")
            return
        
        # Bugün ve gelecek eventler
        future_events = events[pd.to_datetime(events['tarih']) >= self.today].sort_values('tarih')
        
        if future_events.empty:
            st.info("Gelecek event bulunmuyor.")
            return
        
        # Zaman çizelgesi
        fig = go.Figure()
        
        for tip, renk, sembol in [('heat', 'orange', 'circle'), 
                                  ('birth', 'green', 'star'),
                                  ('insemination', 'red', 'triangle-up'),
                                  ('check', 'blue', 'square')]:
            tip_events = future_events[future_events['tip'] == tip]
            if not tip_events.empty:
                fig.add_trace(go.Scatter(
                    x=tip_events['tarih'],
                    y=[tip] * len(tip_events),
                    mode='markers+text',
                    marker=dict(size=15, color=renk, symbol=sembol),
                    text=tip_events['hayvan'],
                    textposition="top center",
                    name=tip.capitalize(),
                    hovertemplate='<b>%{text}</b><br>Tarih: %{x}<br>Tip: %{y}<extra></extra>'
                ))
        
        fig.update_layout(
            title="Çiftlik Zaman Çizelgesi",
            xaxis_title="Tarih",
            yaxis_title="Event Tipi",
            height=400,
            showlegend=True,
            hovermode='closest'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tablo görünümü
        st.subheader("📅 Yaklaşan Eventler")
        future_events['tarih_str'] = pd.to_datetime(future_events['tarih']).dt.strftime('%Y-%m-%d')
        future_events['kalan_gun'] = future_events['gun']
        
        tip_isim = {
            'heat': '🌡️ Kızgınlık',
            'birth': '👶 Doğum',
            'insemination': '💉 Tohumlama',
            'check': '🔍 Gebelik Kontrol'
        }
        future_events['tip_str'] = future_events['tip'].map(tip_isim)
        
        st.dataframe(
            future_events[['tarih_str', 'hayvan', 'tip_str', 'aciklama', 'oncelik', 'kalan_gun']]
            .rename(columns={
                'tarih_str': 'Tarih',
                'hayvan': 'Küpe No',
                'tip_str': 'Event Tipi',
                'aciklama': 'Açıklama',
                'oncelik': 'Öncelik',
                'kalan_gun': 'Kalan Gün'
            }),
            use_container_width=True,
            hide_index=True
        )
