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
    .smart-tip-box { background-color: #111b27; border: 1px solid #1f6feb; padding: 20px; border-radius: 12px; margin-top: 20px; margin-bottom: 20px; }
    .timer-box { background-color: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 15px; color: #58a6ff; font-weight: bold; font-size: 13px; }
    
    .badge-v { background-color: #238636; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }
    .badge-n { background-color: #d29922; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }
    .badge-p { background-color: #da3633; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }
    
    .stTabs [data-baseweb="tab-list"] button:nth-child(1) {
        background-color: rgba(35, 134, 54, 0.15);
        border: 1px solid #238636;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(1):hover {
        background-color: rgba(35, 134, 54, 0.3);
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(2) {
        background-color: rgba(210, 153, 34, 0.15);
        border: 1px solid #d29922;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(2):hover {
        background-color: rgba(210, 153, 34, 0.3);
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(3) {
        background-color: rgba(218, 54, 51, 0.15);
        border: 1px solid #da3633;
        border-radius: 8px 8px 0 0;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(3):hover {
        background-color: rgba(218, 54, 51, 0.3);
    }
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

TZ_ITALIA = timezone(timedelta(hours=2))
now = datetime.now(TZ_ITALIA)

with st.sidebar:
  st.header("Selettore Tornei")

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
      "Stagione", ["2026-27", "2025-26", "2024-25"]
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


def calcola_pronostico_ia(stats1, stats2):
  if not stats1 or not stats2:
    return 33.3, 33.4, 33.3

  forza_1 = stats1["ppg"] * 1.5 + (stats1["gf_avg"] - stats1["gs_avg"]) * 0.5
  forza_2 = stats2["ppg"] * 1.5 + (stats2["gf_avg"] - stats2["gs_avg"]) * 0.5
  forza_1 += 0.2

  diff = forza_1 - forza_2

  base_1 = 40 + (diff * 18)
  base_2 = 40 - (diff * 18)
  base_x = 26 - abs(diff * 5)

  p1 = max(10.0, min(80.0, base_1))
  p2 = max(10.0, min(80.0, base_2))
  px = max(10.0, min(50.0, base_x))

  tot_p = p1 + px + p2
  return (
      round((p1 / tot_p) * 100, 1),
      round((px / tot_p) * 100, 1),
      round((p2 / tot_p) * 100, 1),
  )


def genera_analisi_ia_match(t1, t2, stats1, stats2, p1, px, p2):
  favorevole = t1 if p1 > p2 else (t2 if p2 > p1 else "Equilibrio")
  testo = f"""
    🤖 **Report e Pronostico IA — {t1} vs {t2}**<br><br>
    * **Predizione Esito Finale (1X2):** L'intelligenza artificiale assegna il **{p1}%** di probabilità per la vittoria di {t1} (1), il **{px}%** per il pareggio (X) e il **{p2}%** per il successo esterno di {t2} (2).<br>
    * **Tendenza di Pronostico:** Il modello statistico indica un vantaggio potenziale per **{favorevole}** in base al confronto dei punti a partita (PPG) e alla solidità difensiva recente.<br>
    * **Consiglio Strategico:** Valutare coperture o mercati combinati (es. 1X o Goal) se la percentuale di pareggio supera il 25%.
    """
  return testo


st.markdown(
    """
    <div style='background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; padding: 25px; border-radius: 16px; margin-bottom: 20px;'>
        <h2 style='color: #58a6ff; margin-bottom: 5px;'>⚽ b-betting Hub</h2>
        <p style='color: #8b949e; font-size: 14px; margin-top: 0;'>Piattaforma avanzata di Live Data Architecture, Statistiche Sportive e Previsioni Algoritmiche.</p>
        <div style='display: flex; gap: 10px; flex-wrap: wrap; margin-top: 15px;'>
            <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>⚡ Engine: <b>Attivo</b></span>
            <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>📊 Modello IA: <b>v4.2 Pro</b></span>
            <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>🕒 Sync: <b>Real-time</b></span>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs(
    ["📅 Palinsesto", "📊 Classifica", "📈 Analisi Match & Statistiche"]
)

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
  st.subheader("📊 Analisi Match & Statistiche")

  data = carica_dati_campionato(campionato_top, stagione_selezionata)
  matches = data.get("matches", [])

  tutte_squadre = sorted(
      list(
          set(
              [m.get("team1") for m in matches if m.get("team1")]
              + [m.get("team2") for m in matches if m.get("team2")]
          )
      )
  )

  if tutte_squadre:
    st.markdown("🔍 **Cerca Statistiche per Singola Squadra:**")
    squadra_singola = st.selectbox(
        "Seleziona o digita una squadra per visualizzare le sue statistiche dedicate",
        ["-- Seleziona una squadra --"] + tutte_squadre,
        key="ricerca_singola_squadra",
    )

    if squadra_singola != "-- Seleziona una squadra --":
      st.markdown(f"### 📋 Report Singola Squadra: **{squadra_singola}**")
      stats_singola = calcola_statistiche_squadra(matches, squadra_singola)
      if stats_singola:
        col_ss1, col_ss2, col_ss3, col_ss4 = st.columns(4)
        with col_ss1:
          st.metric("Punti a Partita (PPG)", stats_singola["ppg"])
          st.metric("Partite Giocate", stats_singola["tot"])
        with col_ss2:
          st.metric("Media Gol Fatti", stats_singola["gf_avg"])
          st.metric("Over 2.5 %", f"{stats_singola['over_2_5_pct']}%")
        with col_ss3:
          st.metric("Media Gol Subiti", stats_singola["gs_avg"])
          st.metric("Clean Sheet %", f"{stats_singola['clean_sheets_pct']}%")
        with col_ss4:
          st.metric("Gol a Partita (BTTS %)", f"{stats_singola['btts_pct']}%")

        st.markdown("**Stato di Forma (Ultime 5):**")
        forma_html = ""
        for ris in stats_singola["forma"][-5:]:
          if ris == "V":
            forma_html += "<span class='badge-v'>V</span>"
          elif ris == "N":
            forma_html += "<span class='badge-n'>N</span>"
          else:
            forma_html += "<span class='badge-p'>P</span>"
        st.markdown(
            forma_html if forma_html else "N.D.", unsafe_allow_html=True
        )
      else:
        st.info(
            "Nessun dato di match disputati disponibile per questa squadra"
            " nella stagione selezionata."
        )
      st.markdown("---")

  oggi_str = now.strftime("%Y-%m-%d")

  matches_da_giocare = []
  for m in matches:
    if isinstance(m, dict) and m.get("team1") and m.get("team2"):
      anno_stagione = stagione_selezionata.split("-")[0]
      data_m = m.get("date", "")

      ha_score = (
          m.get("score")
          and isinstance(m["score"], dict)
          and m["score"].get("ft") is not None
      )
      if not ha_score and (
          data_m.startswith(anno_stagione)
          or (
              data_m >= "2026-01-01"
              if stagione_selezionata == "2026-27"
              else True
          )
      ):
        matches_da_giocare.append(m)

  if not matches_da_giocare:
    matches_da_giocare = [
        m
        for m in matches
        if isinstance(m, dict)
        and m.get("team1")
        and not (m.get("score") and m["score"].get("ft"))
    ]

  if not matches_da_giocare:
    matches_da_giocare = [
        m for m in matches if isinstance(m, dict) and m.get("team1")
    ]

  match_prossima_giornata = (
      matches_da_giocare[:10] if matches_da_giocare else []
  )

  if match_prossima_giornata:
    match_options = []
    match_dict = {}
    for m in match_prossima_giornata:
      data_m = m.get("date", "Data n.d.")
      t1 = m.get("team1")
      t2 = m.get("team2")
      label = f"{data_m} | {t1} vs {t2}"
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

    stats_t1 = calcola_statistiche_squadra(matches, t1)
    stats_t2 = calcola_statistiche_squadra(matches, t2)
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
        forma_html = ""
        for ris in stats_t1["forma"][-5:]:
          if ris == "V":
            forma_html += "<span class='badge-v'>V</span>"
          elif ris == "N":
            forma_html += "<span class='badge-n'>N</span>"
          else:
            forma_html += "<span class='badge-p'>P</span>"
        st.markdown(
            forma_html if forma_html else "N.D.", unsafe_allow_html=True
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
        forma_html = ""
        for ris in stats_t2["forma"][-5:]:
          if ris == "V":
            forma_html += "<span class='badge-v'>V</span>"
          elif ris == "N":
            forma_html += "<span class='badge-n'>N</span>"
          else:
            forma_html += "<span class='badge-p'>P</span>"
        st.markdown(
            forma_html if forma_html else "N.D.", unsafe_allow_html=True
        )

        st.markdown("<br>**Barra Statistiche Squadra:**", unsafe_allow_html=True)
        st.progress(
            min(max(int(stats_t2["ppg"] / 3.0 * 100), 0), 100),
            text=f"Indice Rendimento: {stats_t2['ppg']} PPG",
        )
      else:
        st.info("Dati insufficienti per questa squadra.")

    st.markdown("---")
    st.markdown("### 🔮 Pronostico IA Esito Finale (1 X 2)")
    col_p1, col_px, col_p2 = st.columns(3)
    with col_p1:
      st.metric(label="Vittoria Casa (1)", value=f"{prob_1}%")
    with col_px:
      st.metric(label="Pareggio (X)", value=f"{prob_x}%")
    with col_p2:
      st.metric(label="Vittoria Ospite (2)", value=f"{prob_2}%")

    st.markdown("---")
    st.markdown("### 🧠 Report IA sullo Stato di Forma e Match")
    analisi_testo = genera_analisi_ia_match(
        t1, t2, stats_t1, stats_t2, prob_1, prob_x, prob_2
    )
    st.markdown(
        f"<div class='ai-box'>{analisi_testo}</div>", unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("### 🌟 Consiglio Smart IA della Giornata")

    media_gol_totale = 2.5
    if stats_t1 and stats_t2:
      media_gol_totale = (
          stats_t1["gf_avg"]
          + stats_t1["gs_avg"]
          + stats_t2["gf_avg"]
          + stats_t2["gs_avg"]
      ) / 2

    btts_consigliato = (
        stats_t1
        and stats_t2
        and ((stats_t1["btts_pct"] + stats_t2["btts_pct"]) / 2 > 55)
    )
    over_consigliato = media_gol_totale > 2.75

    if btts_consigliato:
      giocata_top = "GOAL (Entrambe le squadre a segno)"
      motivazione_giocata = f"Le medie realizzative di {t1} e {t2} unite alle percentuali di BTTS elevate (>55%) rendono altamente probabile reti da ambo i lati."
    elif over_consigliato:
      giocata_top = "OVER 2.5"
      motivazione_giocata = f"Il volume offensivo complessivo ({round(media_gol_totale, 2)} gol attesi combinati) suggerisce un match aperto e ricco di marcature."
    else:
      if prob_1 > 60:
        giocata_top = f"1 (Vittoria {t1})"
        motivazione_giocata = f"Netta superiorità statistica e fattore campo per {t1}."
      elif prob_2 > 60:
        giocata_top = f"2 (Vittoria {t2})"
        motivazione_giocata = f"Il rendimento esterno e i punti a partita (PPG) premiano {t2}."
      else:
        giocata_top = "1X o Over 1.5 (Combo di Sicurez
