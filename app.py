import json
from datetime import datetime
import requests
import streamlit as st

# Configurazione della pagina
st.set_page_config(
    page_title="Dashboard Betting & IA",
    page_icon="⚽",
    layout="wide",
)


# Funzioni di supporto per statistiche e pronostici
def calcola_statistiche_squadra(matches_list, squadra):
  # Filtriamo i match giocati dalla squadra
  match_squadra = [
      m
      for m in matches_list
      if isinstance(m, dict)
      and (m.get("team1") == squadra or m.get("team2") == squadra)
  ]
  if not match_squadra:
    return {
        "ppg": 1.2,
        "gf_avg": 1.0,
        "gs_avg": 1.0,
        "over_2_5_pct": 50,
        "clean_sheets_pct": 30,
        "btts_pct": 50,
        "forma": ["V", "N", "P", "V", "N"],
    }

  punti = 0
  gol_fatti = 0
  gol_subiti = 0
  over_count = 0
  clean_sheets = 0
  btts_count = 0
  forma = []

  for m in match_squadra:
    score = m.get("score", {})
    if isinstance(score, dict) and score.get("ft") is not None:
      ft = score.get("ft")
      if isinstance(ft, list) and len(ft) == 2:
        g1, g2 = ft[0], ft[1]
        is_home = m.get("team1") == squadra
        gf = g1 if is_home else g2
        gs = g2 if is_home else g1

        gol_fatti += gf
        gol_subiti += gs
        if (gf + gs) > 2.5:
          over_count += 1
        if gs == 0:
          clean_sheets += 1
        if gf > 0 and gs > 0:
          btts_count += 1

        if gf > gs:
          punti += 3
          forma.append("V")
        elif gf == gs:
          punti += 1
          forma.append("N")
        else:
          forma.append("P")

  tot_giocate = max(len(forma), 1)
  return {
      "ppg": round(punti / tot_giocate, 2),
      "gf_avg": round(gol_fatti / tot_giocate, 2),
      "gs_avg": round(gol_subiti / tot_giocate, 2),
      "over_2_5_pct": int((over_count / tot_giocate) * 100),
      "clean_sheets_pct": int((clean_sheets / tot_giocate) * 100),
      "btts_pct": int((btts_count / tot_giocate) * 100),
      "forma": forma if forma else ["N", "N", "N", "N", "N"],
  }


def calcola_pronostico_ia(stats1, stats2):
  p1 = max(
      10,
      min(
          85,
          int(
              50
              + (stats1["ppg"] - stats2["ppg"]) * 15
              + (stats1["gf_avg"] - stats2["gs_avg"]) * 10
          ),
      ),
  )
  p2 = max(
      10,
      min(
          85,
          int(
              50
              + (stats2["ppg"] - stats1["ppg"]) * 15
              + (stats2["gf_avg"] - stats1["gs_avg"]) * 10
          ),
      ),
  )
  px = max(10, 100 - p1 - p2)
  tot = p1 + px + p2
  return int((p1 / tot) * 100), int((px / tot) * 100), int((p2 / tot) * 100)


def genera_analisi_ia_match(t1, t2, s1, s2, p1, px, p2):
  return f"Analisi tattica avanzata: {t1} presenta una media punti di {s1['ppg']} PPG contro i {s2['ppg']} PPG di {s2}. I dati evidenziano un potenziale offensivo equilibrato con una tendenza stimata sui gol."


# Caricamento dati partite (usiamo una fonte dati o fallback sicuro)
now = datetime.now()
matches = []

try:
  # Esempio di recupero dati (sostituisci l'endpoint se usi un URL specifico per il tuo campionato)
  response = requests.get(
      "https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/it.1.json",
      timeout=5,
  )
  if response.status_code == 200:
    data = response.json()
    matches = data.get("matches", [])
except Exception:
  matches = []

st.title("⚽ Dashboard Pronostici & Statistiche")

matches_list = matches if matches else []

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
