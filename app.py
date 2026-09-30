import json
from datetime import datetime
import streamlit as st

# Configurazione della pagina
st.set_page_config(
    page_title="Dashboard Betting & IA",
    page_icon="⚽",
    layout="wide",
)

# Funzioni di supporto (se presenti nel tuo script, le manteniamo integrate)
# Assicurati che le funzioni calcola_statistiche_squadra, calcola_pronostico_ia e genera_analisi_ia_match siano definite nel tuo script o importate correttamente.


def calcola_statistiche_squadra(matches_list, squadra):
  # Funzione di esempio o esistente nel tuo codice
  # Restituisce le statistiche della squadra
  ppg = 1.5
  gf_avg = 1.2
  gs_avg = 1.0
  over_2_5_pct = 50
  clean_sheets_pct = 30
  btts_pct = 50
  forma = ["V", "N", "V", "P", "V"]
  return {
      "ppg": ppg,
      "gf_avg": gf_avg,
      "gs_avg": gs_avg,
      "over_2_5_pct": over_2_5_pct,
      "clean_sheets_pct": clean_sheets_pct,
      "btts_pct": btts_pct,
      "forma": forma,
  }


def calcola_pronostico_ia(stats1, stats2):
  return 45, 30, 25


def genera_analisi_ia_match(t1, t2, s1, s2, p1, px, p2):
  return f"Analisi dettagliata per la sfida tra {t1} e {t2} basata sullo stato di forma e sulle medie stagionali."


# Caricamento dati (modifica a seconda di come carichi i tuoi matches)
now = datetime.now()
matches = []  # Sostituisci o collega alla tua variabile di caricamento JSON/dati

# Se hai una sorgente dati JSON esistente nel progetto, mantienila e usa direttamente la variabile matches.

st.title("⚽ Dashboard Pronostici & Statistiche")

matches_list = matches if "matches" in locals() and matches else []

match_prossima_giornata = [
    m
    for m in matches_list
    if isinstance(m, dict) and m.get("team1") and m.get("team2")
]

if match_prossima_giornata:
  match_options = []
  match_dict = {}
  for m in match_prossima_giornata:
    t1 = m.get("team1")
    t2 = m.get("team2")
    label = f"{t1} vs {t2}"
    match_options.append(label)
    match_dict[label] = m

  st.markdown("🎯 *Seleziona una partita per il Confronto Diretto e Pronostico IA:*")

  partita_scelta_label = st.selectbox(
      "Seleziona la Partita della Giornata",
      match_options,
      key="match_scelto_stat",
  )
  m_sel = match_dict[partita_scelta_label]
  t1 = m_sel.get("team1")
  t2 = m_sel.get("team2")

  stats_t1 = calcola_statistiche_squadra(matches_list, t1)
  stats_t2 = calcola_statistiche_squadra(matches_list, t2)
  prob_1, prob_x, prob_2 = calcola_pronostico_ia(stats_t1, stats_t2)

  st.markdown("---")
  st.markdown(f"### ⚔️ Confronto Diretto: {t1} vs {t2}")

  col_s1, col_s2 = st.columns(2)

  with col_s1:
    st.markdown(f"#### 🏠 {t1}")
    if stats_t1:
      st.metric("Punti a Partita (PPG)", stats_t1["ppg"])
      st.metric("Media Gol Fatti", stats_t1["gf_avg"])
      st.metric("Media Gol Subiti", stats_t1["gs_avg"])
      st.metric("Over 2.5 %", f"{stats_t1['over_2_5_pct']}%")
      st.metric("Clean Sheet %", f"{stats_t1['clean_sheets_pct']}%")
      st.metric("Gol a Partita (BTTS %)", f"{stats_t1['btts_pct']}%")

      st.markdown("**Stato di Forma (Ultime 5):**")
      forma_html_1 = ""
      for ris in stats_t1["forma"][-5:]:
        if ris == "V":
          forma_html_1 += "<span class='badge-v'>V</span>"
        elif ris == "N":
          forma_html_1 += "<span class='badge-n'>N</span>"
        else:
          forma_html_1 += "<span class='badge-p'>P</span>"
      st.markdown(
          forma_html_1 if forma_html_1 else "N.D.", unsafe_allow_html=True
      )

      st.markdown("<br>**Barra Statistiche Squadra:**", unsafe_allow_html=True)
      st.progress(
          min(max(int(stats_t1["ppg"] / 3.0 * 100), 0), 100),
          text=f"Indice Rendimento: {stats_t1['ppg']} PPG",
      )
    else:
      st.info("Dati insufficienti per questa squadra.")

  with col_s2:
    st.markdown(f"#### ✈️ {t2}")
    if stats_t2:
      st.metric("Punti a Partita (PPG)", stats_t2["ppg"])
      st.metric("Media Gol Fatti", stats_t2["gf_avg"])
      st.metric("Media Gol Subiti", stats_t2["gs_avg"])
      st.metric("Over 2.5 %", f"{stats_t2['over_2_5_pct']}%")
      st.metric("Clean Sheet %", f"{stats_t2['clean_sheets_pct']}%")
      st.metric("Gol a Partita (BTTS %)", f"{stats_t2['btts_pct']}%")

      st.markdown("**Stato di Forma (Ultime 5):**")
      forma_html_2 = ""
      for ris in stats_t2["forma"][-5:]:
        if ris == "V":
          forma_html_2 += "<span class='badge-v'>V</span>"
        elif ris == "N":
          forma_html_2 += "<span class='badge-n'>N</span>"
        else:
          forma_html_2 += "<span class='badge-p'>P</span>"
      st.markdown(
          forma_html_2 if forma_html_2 else "N.D.", unsafe_allow_html=True
      )

      st.markdown("<br>**Barra Statistiche Squadra:**", unsafe_allow_html=True)
      st.progress(
          min(max(int(stats_t2["ppg"] / 3.0 * 100), 0), 100),
          text=f"Indice Rendimento: {stats_t2['ppg']} PPG",
      )
    else:
      st.info("Dati insufficienti per questa squadra.")

  st.markdown("---")
  try:
    if "t1" in locals() and "t2" in locals() and "prob_1" in locals():
      analisi_testo = genera_analisi_ia_match(
          t1, t2, stats_t1, stats_t2, prob_1, prob_x, prob_2
      )
      html_output = f"<div class='ai-box'>{analisi_testo}<br><b>Previsioni Esito 1X2:</b><br>• {t1} (1): <b>{prob_1}%</b><br>• Pareggio (X): <b>{prob_x}%</b><br>• {t2} (2): <b>{prob_2}%</b></div>"
      st.markdown(html_output, unsafe_allow_html=True)
    else:
      st.info("Seleziona una partita dal menu per sbloccare l'analisi IA.")
  except Exception as e:
    st.info("Modulo di analisi pronto all'uso.")
else:
  st.info("Nessuna partita disponibile al momento.")
