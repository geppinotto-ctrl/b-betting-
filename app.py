import streamlit as st

st.set_page_config(
    page_title="b-betting — Live Dashboard", page_icon="⚽", layout="wide"
)

import streamlit.components.v1 as components

from analisi import pagina_dashboard
from assenze import pannello_assenze
from config import STAGIONI, campionati_disponibili
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

    st.selectbox("Stagione", STAGIONI, key="stagione")
    st.selectbox("Torneo", campionati_disponibili, key="torneo")

    # Cambiare motore deve invalidare backtest, radar e confronto mercato,
    # che sono in cache e altrimenti mostrerebbero i numeri del motore vecchio.
    st.selectbox(
        "Motore probabilistico",
        ["Poisson", "Dixon–Coles"],
        key="motore",
        on_change=st.cache_data.clear,
        help="Dixon–Coles corregge i punteggi bassi (0-0, 1-1, 1-0, 0-1). "
        "Confrontalo con Poisson nel tab Backtest prima di fidarti.",
    )
    if st.session_state.get("motore") == "Dixon–Coles":
        st.number_input(
            "ρ (correlazione punteggi bassi)",
            min_value=-0.30,
            max_value=0.10,
            value=-0.10,
            step=0.01,
            key="rho_dc",
            on_change=st.cache_data.clear,
            help="Negativo = più 0-0 e 1-1. Valore stimabile con confronta_motori.py.",
        )

    pannello_assenze()

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
