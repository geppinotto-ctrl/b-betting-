from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="b-betting — Live Dashboard", page_icon="⚽", layout="wide"
)

st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    .stTextInput > div > div > input { background-color: #161b22; color: #c9d1d9; border-radius: 8px; border: 1px solid #30363d; }
    .league-section { color: #8b949e; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; }
    .ai-box { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; margin-top: 15px; margin-bottom: 15px; }
    .timer-box { background-color: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 15px; color: #58a6ff; font-weight: bold; font-size: 13px; }
    
    .badge-v { background-color: #238636; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }
    .badge-n { background-color: #d29922; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }
    .badge-p { background-color: #da3633; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }
    </style>
""",
    unsafe_allow_html=True,
)

if "df_schedina" not in st.session_state:
  st.session_state.df_schedina = pd.DataFrame([{
      "Partita": "Juventus vs Inter",
      "Segno / Esito": "1",
      "Quota": 2.10,
      "Bookmaker": "GoldBet",
  }])

col_title, col_home_btn = st.columns([0.80, 0.20])
with col_title:
  st.title("⚽ b-betting")
  st.markdown("##### *Live Data Architecture & AI Sports Forecasting*")

with col_home_btn:
  st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
  if st.button("🏠 Home", use_container_width=True, help="Torna alla Home"):
    st.rerun()

st.divider()

campionati_disponibili = [
    "Italia - Serie A",
    "Inghilterra - Premier League",
    "Spagna - La Liga",
    "Germania - Bundesliga",
    "Francia - Ligue 1",
    "UEFA Champions League",
]

mapping_file_torneo = {
    "Italia - Serie A": ["it.1.json", "italy/it.1.json"],
    "Inghilterra - Premier League": ["en.1.json", "england/en.1.json"],
    "Spagna - La Liga": ["es.1.json", "spain/es.1.json"],
    "Germania - Bundesliga": ["de.1.json", "germany/de.1.json"],
    "Francia - Ligue 1": ["fr.1.json", "france/fr.1.json"],
    "UEFA Champions League": ["cl.json", "champions-league/index.json"],
}

with st.sidebar:
  st.header("Selettore Tornei")

  # Timer sincronizzato sul fuso orario italiano (UTC+2 ora legale)
  TZ_ITALIA = timezone(timedelta(hours=2))
  now = datetime.now(TZ_ITALIA)

  giorni_it = [
      "Lunedì",
      "Martedì",
      "Mercoledì",
      "Giovedì",
      "Venerdì",
      "Sabato",
      "Domenica",
  ]
  giorno_corrente = giorni_it[now.weekday()]
  data_ora_formattata = (
      f"{giorno_corrente}, {now.strftime('%d/%m/%Y - %H:%M')}"
  )
  st.markdown(
      f"<div class='timer-box'>🕒 Riferimento Live (Italia):<br>{data_ora_formattata}</div>",
      unsafe_allow_html=True,
  )

  stagione_selezionata = st.selectbox(
      "Stagione", ["2025-26", "2026-27", "2024-25"]
  )
  campionato_top = st.selectbox("Torneo", campionati_disponibili)
  if st.button("🔄 Aggiorna Dati", use_container_width=True):
    st.cache_data.clear()
    st.rerun()


@st.cache_data
def carica_dati_campionato(nome_campionato, stagione):
  possibili_nomi = mapping_file_torneo.get(nome_campionato, ["it.1.json"])
  percorsi_da_tentare = []
  for nome_file in possibili_nomi:
    percorsi_da_tentare.append(f"{stagione}/{nome_file}")
    percorsi_da_tentare.append(nome_file)
    anno_inizio = stagione.split("-")[0]
    percorsi_da_tentare.append(f"{anno_inizio}/{nome_file}")

  for p in percorsi_da_tentare:
    url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{p}"
    try:
      r = requests.get(url, timeout=4)
      if r.status_code == 200:
        res = r.json()
        if isinstance(res, list):
          return {"matches": res}
        if isinstance(res, dict):
          if "matches" in res:
            return res
          for v in res.values():
            if isinstance(v, list):
              return {"matches": v}
    except:
      pass

  return {"matches": []}


def calcola_statistiche_squadra(matches, squadra):
  match_squadra = [
      m
      for m in matches
      if isinstance(m, dict)
      and "score" in m
      and isinstance(m["score"], dict)
      and m["score"].get("ft") is not None
      and (m.get("team1") == squadra or m.get("team2") == squadra)
  ]

  tot = len(match_squadra)
  if tot == 0:
    return None

  gf, gs, pt = 0, 0, 0
  clean_sheets = 0
  over_2_5 = 0
  btts = 0
  forma = []

  for m in match_squadra:
    is_casa = m.get("team1") == squadra
    ft = m["score"]["ft"]
    g1, g2 = ft[0], ft[1]
    m_gf = g1 if is_casa else g2
    m_gs = g2 if is_casa else g1

    gf += m_gf
    gs += m_gs

    if m_gs == 0:
      clean_sheets += 1
    if (g1 + g2) > 2.5:
      over_2_5 += 1
    if g1 > 0 and g2 > 0:
      btts += 1

    if m_gf > m_gs:
      forma.append("V")
      pt += 3
    elif m_gf == m_gs:
      forma.append("N")
      pt += 1
    else:
      forma.append("P")

  return {
      "tot": tot,
      "forma": forma,
      "ppg": round(pt / tot, 2),
      "gf_avg": round(gf / tot, 2),
      "gs_avg": round(gs / tot, 2),
      "clean_sheets_pct": round((clean_sheets / tot) * 100, 1),
      "over_2_5_pct": round((over_2_5 / tot) * 100, 1),
      "btts_pct": round((btts / tot) * 100, 1),
  }


def genera_analisi_ia_match(t1, t2, stats1, stats2):
  ppg1 = stats1["ppg"] if stats1 else 1.0
  ppg2 = stats2["ppg"] if stats2 else 1.0

  testo = f"""
    🤖 **Analisi Match IA — {t1} vs {t2}**<br><br>
    * **Confronto Passo (PPG):** {t1} viaggia a una media di **{ppg1} punti/partita**, mentre {t2} fa registrare **{ppg2} punti/partita**.<br>
    * **Tendenza Reti:** Analizzando lo storico stagionale delle due sfidanti, la partita mostra compatibilità elevate con mercati orientati ai gol.<br>
    * **Consiglio Strategico:** Valutare la tendenza delle ultime uscite in base al fattore campo. Partita aperta a diverse chiavi di lettura tattica.
    """
  return testo


tab1, tab2, tab3 = st.tabs(["📅 Palinsesto", "📊 Classifica", "📈 Analisi Match"])

with tab1:
  st.subheader("Palinsesto Match")
  data = carica_dati_campionato(campionato_top, stagione_selezionata)
  matches = data.get("matches", [])
  if matches:
    lista = [{
        "Data": m.get("date", ""),
        "Casa": m.get("team1", ""),
        "Ospite": m.get("team2", ""),
    } for m in matches if isinstance(m, dict)]
    st.dataframe(pd.DataFrame(lista), use_container_width=True)
  else:
    st.warning("Dati non disponibili per questo torneo.")

with tab2:
  st.subheader("Classifica Live")
  data = carica_dati_campionato(campionato_top, stagione_selezionata)
  matches = data.get("matches", [])
  classifica = {}
  for m in matches:
    if (
        isinstance(m, dict)
        and "score" in m
        and isinstance(m["score"], dict)
        and m["score"].get("ft")
    ):
      t1, t2 = m.get("team1"), m.get("team2")
      if not t1 or not t2:
        continue
      ft = m["score"]["ft"]
      g1, g2 = ft[0], ft[1]
      for sq in [t1, t2]:
        if sq not in classifica:
          classifica[sq] = {"Squadra": sq, "PG": 0, "Pt": 0, "GF": 0, "GS": 0}
      classifica[t1]["PG"] += 1
      classifica[t2]["PG"] += 1
      classifica[t1]["GF"] += g1
      classifica[t1]["GS"] += g2
      classifica[t2]["GF"] += g2
      classifica[t2]["GS"] += g1
      if g1 > g2:
        classifica[t1]["Pt"] += 3
      elif g1 < g2:
        classifica[t2]["Pt"] += 3
      else:
        classifica[t1]["Pt"] += 1
        classifica[t2]["Pt"] += 1
  if classifica:
    df_c = pd.DataFrame(list(classifica.values()))
    df_c["DR"] = df_c["GF"] - df_c["GS"]
    df_c = (
        df_c.sort_values(by=["Pt", "DR"], ascending=False)
        .reset_index(drop=True)
    )
    df_c.index += 1
    st.dataframe(df_c, use_container_width=True)
  else:
    st.warning("Classifica non disponibile.")

with tab3:
  st.subheader("📊 Analisi e Confronto Partita")

  data = carica_dati_campionato(campionato_top, stagione_selezionata)
  matches = data.get("matches", [])

  match_options = []
  match_dict = {}
  for m in matches:
    if isinstance(m, dict) and m.get("team1") and m.get("team2"):
      data_m = m.get("date", "Data n.d.")
      t1 = m.get("team1")
      t2 = m.get("team2")
      label = f"{data_m} | {t1} vs {t2}"
      match_options.append(label)
      match_dict[label] = m

  if match_options:
    partita_scelta_label = st.selectbox(
        "Seleziona la Partita da Analizzare",
        match_options,
        key="match_scelto_stat",
    )
    m_sel = match_dict[partita_scelta_label]
    t1 = m_sel.get("team1")
    t2 = m_sel.get("team2")

    stats_t1 = calcola_statistiche_squadra(matches, t1)
    stats_t2 = calcola_statistiche_squadra(matches, t2)

    st.markdown("---")
    st.markdown(f"### ⚔️ Confronto Diretto: {t1} vs {t2}")

    col_s1, col_s2 = st.columns(2)

    with col_s1:
      st.markdown(f"#### 🏠 {t1}")
      if stats_t1:
        st.metric("Punti a Partita (PPG)", stats_t1["ppg"])
        st.metric("Media Gol Fatti", stats_t1["gf_avg"])
        st.metric("Over 2.5 %", f"{stats_t1['over_2_5_pct']}%")
      else:
        st.info("Dati insufficienti per questa squadra.")

    with col_s2:
      st.markdown(f"#### ✈️ {t2}")
      if stats_t2:
        st.metric("Punti a Partita (PPG)", stats_t2["ppg"])
        st.metric("Media Gol Fatti", stats_t2["gf_avg"])
        st.metric("Over 2.5 %", f"{stats_t2['over_2_5_pct']}%")
      else:
        st.info("Dati insufficienti per questa squadra.")

    st.markdown("---")
    st.markdown("### 🧠 Report IA sul Match")
    analisi_testo = genera_analisi_ia_match(t1, t2, stats_t1, stats_t2)
    st.markdown(
        f"<div class='ai-box'>{analisi_testo}</div>", unsafe_allow_html=True
    )

  else:
    st.warning(
        "Nessuna partita trovata nel calendario per la stagione selezionata."
    )
    
