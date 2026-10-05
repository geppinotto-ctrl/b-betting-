import streamlit as st

st.set_page_config(
    page_title="b-betting — Live Dashboard", page_icon="⚽", layout="wide"
)

import streamlit.components.v1 as components

from analisi import pagina_dashboard
from assenze import pannello_assenze
from calibra_modello import mostra_calibrazione
from confronta_motori import mostra_confronto_motori
from config import STAGIONI, campionati_disponibili
from home import mostra_home
import persistenza
from quote import mostra_stato_quote
from resilienza import sezione_sicura, svuota_cache, svuota_quote
from stile import (
    applica_css_principale,
    applica_css_vetro,
    audio_sottofondo,
    prepara_sfondo,
)

# Parti decorative (audio, CSS, sfondo): se un file manca o un'immagine è
# corrotta l'app parte comunque, senza disturbare l'utente con un errore.
import logging

for _passo in (audio_sottofondo, applica_css_vetro):
    try:
        _passo()
    except Exception:  # noqa: BLE001
        logging.getLogger("b-betting").exception("Passo decorativo %s fallito", _passo.__name__)

with sezione_sicura("Stato quote"):
    mostra_stato_quote()

for _passo in (applica_css_principale, prepara_sfondo):
    try:
        _passo()
    except Exception:  # noqa: BLE001
        logging.getLogger("b-betting").exception("Passo decorativo %s fallito", _passo.__name__)


def _cambia_motore():
    """Motore e rho cambiano i calcoli, non i download né le quote API."""
    svuota_cache("calcoli")

if "pagina" not in st.session_state:
    st.session_state.pagina = "home"

# Dati salvati (archivio schedine, schedina in corso, curve calibrate): si
# caricano una volta per sessione e si risalvano a ogni giro se cambiano.
# Il salvataggio a inizio giro cattura anche le modifiche fatte prima di un
# st.rerun(), che interrompe lo script prima della fine.
persistenza.carica_avvio()

# L'interruttore delle probabilità calibrate è un widget della barra laterale:
# si può modificare solo PRIMA che venga creato, quindi il tab Backtest lascia
# una richiesta e la applichiamo qui, all'inizio del giro successivo.
if st.session_state.pop("_attiva_calib", False):
    st.session_state["usa_calib"] = True

persistenza.salva_se_cambiato()

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

    # I due pulsanti di uso quotidiano stanno subito sotto i selettori, così
    # non finiscono in fondo a una barra laterale lunga.
    if st.button("🏠 Torna alla Home", use_container_width=True):
        st.session_state.pagina = "home"
        st.session_state.mostra_confronto = False
        st.session_state.mostra_calibrazione = False
        st.rerun()

    quote_anche = st.checkbox(
        "Aggiorna anche le quote",
        value=False,
        help="Ogni aggiornamento delle quote consuma richieste del tuo piano API. "
        "Lasciala spenta se vuoi solo ricaricare partite e statistiche.",
    )
    if st.button("🔄 Aggiorna Dati", use_container_width=True):
        with st.spinner("Aggiorno i dati…"):
            svuota_cache("download", "calcoli")
            if quote_anche:
                svuota_quote()
        st.rerun()

    st.divider()
    st.markdown("**⚙️ Motore e assenze**")

    # Cambiare motore deve invalidare backtest, radar e confronto mercato,
    # che sono in cache e altrimenti mostrerebbero i numeri del motore vecchio.
    st.selectbox(
        "Motore probabilistico",
        ["Poisson", "Dixon–Coles"],
        key="motore",
        on_change=_cambia_motore,
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
            on_change=_cambia_motore,
            help="Negativo = più 0-0 e 1-1. Valore stimabile con confronta_motori.py.",
        )

    if st.session_state.get("calib"):
        st.checkbox(
            "Usa probabilità calibrate",
            key="usa_calib",
            help="Applica le curve calibrate nel tab Backtest a consigli, radar "
            "e pronostici dei tornei calibrati: "
            + ", ".join(sorted(st.session_state["calib"]))
            + ". Il backtest resta sempre sui valori grezzi.",
        )

    pannello_assenze()

    if st.button("🧪 Confronta Poisson / Dixon–Coles", use_container_width=True):
        st.session_state.mostra_confronto = True
        st.session_state.mostra_calibrazione = False
        st.rerun()

    if st.button("🎛️ Calibra parametri del modello", use_container_width=True):
        st.session_state.mostra_calibrazione = True
        st.session_state.mostra_confronto = False
        st.rerun()

    st.divider()
    persistenza.mostra_stato_salvataggio()


if st.session_state.get("mostra_calibrazione"):
    with sezione_sicura("Calibrazione modello"):
        mostra_calibrazione()
    st.stop()

if st.session_state.get("mostra_confronto"):
    with sezione_sicura("Confronto motori"):
        mostra_confronto_motori()
    st.stop()

if st.session_state.pagina == "home":
    with sezione_sicura("Home"):
        mostra_home()
    st.stop()

with sezione_sicura("Dashboard"):
    pagina_dashboard()

persistenza.salva_se_cambiato()
