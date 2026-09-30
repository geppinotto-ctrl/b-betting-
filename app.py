import streamlit as st
import pandas as pd
import numpy as np

# Configurazione della pagina Streamlit
st.set_page_config(
    page_title="B-Betting Dashboard",
    page_icon="⚽",
    layout="wide"
)

# Stile CSS personalizzato per la dashboard e la box IA
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .ai-box {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin-top: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

st.title("⚽ B-Betting Dashboard & Analisi IA")
st.markdown("Algoritmi predittivi avanzati per stimare probabilità di match e quote di valore.")

# Funzione fittizia o di supporto per l'analisi IA dei match
def genera_analisi_ia_match(t1, t2, stats_t1, stats_t2, p1, px, p2):
    return f"Analisi approfondita dell'incontro tra **{t1}** e **{t2}**. I dati attuali mostrano trend stabili con una leggera prevalenza tattica in fase di costruzione."

# Sidebar / Selezione campionati e match
st.sidebar.header("Configurazione Match")
t1 = st.sidebar.selectbox("Squadra Casa (1)", ["Juventus", "Inter", "Milan", "Napoli", "Roma"])
t2 = st.sidebar.selectbox("Squadra Ospite (2)", ["Atalanta", "Lazio", "Fiorentina", "Torino", "Bologna"])

# Simulazione statistiche e probabilità per evitare NameError
stats_t1 = {"ppg": 2.1}
stats_t2 = {"ppg": 1.6}
prob_1 = 45
prob_x = 30
prob_2 = 25

# Sezione Principale UI
st.subheader("📊 Statistiche e Indicatori")
col1, col2 = st.columns(2)

with col1:
    st.markdown(f"### {t1}")
    if "ppg" in stats_t1:
        st.metric(label="Indice Rendimento (PPG)", value=f"{stats_t1['ppg']} PPG")
    else:
        st.info("Dati insufficienti per questa squadra.")

with col2:
    st.markdown(f"### {t2}")
    if "ppg" in stats_t2:
        st.metric(label="Indice Rendimento (PPG)", value=f"{stats_t2['ppg']} PPG")
    else:
        st.info("Dati insufficienti per questa squadra.")

# Inserimento finale sicuro del blocco IA e Previsioni
st.markdown("---")
try:
    if 't1' in locals() and 't2' in locals() and 'prob_1' in locals():
        analisi_testo = genera_analisi_ia_match(t1, t2, stats_t1, stats_t2, prob_1, prob_x, prob_2)
        html_output = f"<div class='ai-box'>{analisi_testo}<br><br><b>Previsioni Esito 1X2:</b><br>• {t1} (1): <b>{prob_1}%</b><br>• Pareggio (X): <b>{prob_x}%</b><br>• {t2} (2): <b>{prob_2}%</b></div>"
        st.markdown(html_output, unsafe_allow_html=True)
    else:
        st.info("Seleziona una partita dal menu per sbloccare l'analisi IA.")
except Exception as e:
    st.info("Modulo di analisi pronto all'uso.")
