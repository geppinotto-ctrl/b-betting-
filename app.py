import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="b-betting — Live Dashboard", page_icon="⚽", layout="wide"
)

import streamlit.components.v1 as components

from analisi import pagina_dashboard
from config import STAGIONI, campionati_disponibili
from dati import carica_dati_campionato
from home import mostra_home
from quote import mostra_stato_quote
from stile import (
    applica_css_principale,
    applica_css_vetro,
    audio_sottofondo,
    prepara_sfondo,
)

audio_sottofondo()
applica_css_vetro()
mostra_stato_quote()
applica_css_principale()
prepara_sfondo()

if "pagina" not in st.session_state:
    st.session_state.pagina = "home"

with st.sidebar:
    st.header("Selettore Tornei")

    components.html(
        """
        <div style="background:#161b22;border:1px solid #30363d;padding:10px;border-radius:8px;text-align:center;color:#58a6ff;font-family:sans-serif;font-weight:bold;font-size:13px;">
            🕒 Orologio Live (Italia)<br>
            <span id="orologio" style="font-size:16px;"></span>
        </div>
        <script>
        function aggiorna() {
            const opt = {timeZone: 'Europe/Rome', weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false};
            document.getElementById('orologio').textContent = new Intl.DateTimeFormat('it-IT', opt).format(new Date());
        }
        aggiorna();
        setInterval(aggiorna, 1000);
        </script>
        """,
        height=80,
    )

    st.markdown("### 🔹 FILTRI TORNEO")
    st.selectbox("▪ STAGIONE", STAGIONI, key="stagione")
    st.selectbox("▪ COMPETIZIONE", campionati_disponibili, key="torneo")
    
    # Caricamento dati e rilevamento intelligente della giornata corrente (senza pytz)
    data_sidebar = carica_dati_campionato(st.session_state.get("torneo", campionati_disponibili[0]), st.session_state.get("stagione", STAGIONI[0]))
    matches_sidebar = data_sidebar.get("matches", [])
    
    giornate_disponibili = []
    oggi_str = datetime.now().strftime("%Y-%m-%d")
    giornata_default = None
    
    for m in matches_sidebar:
        if isinstance(m, dict):
            g = m.get("round")
            if g and g not in giornate_disponibili:
                giornate_disponibili.append(g)
            if not giornata_default and m.get("date", "") >= oggi_str:
                giornata_default = g

    lista_scelte = ["Tutte le giornate"] + giornate_disponibili
    
    indice_default = 0
    if giornata_default and giornata_default in giornate_disponibili:
        indice_default = lista_scelte.index(giornata_default)

    if giornate_disponibili:
        st.selectbox("▪ GIORNATA", lista_scelte, index=indice_default, key="giornata_selezionata")
    else:
        st.selectbox("▪ GIORNATA", ["Nessuna giornata disponibile"], key="giornata_selezionata")

    st.divider()
    if st.button("🏠 Torna alla Home", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()

    if st.button("🔄 Aggiorna Dati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if st.session_state.pagina == "home":
    mostra_home()
    st.stop()

pagina_dashboard()
