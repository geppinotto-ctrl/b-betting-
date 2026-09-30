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
    .ai-box { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; margin-top: 15px; margin-bottom: 15px; color: #c9d1d9; font-size: 14px; }
    .smart-tip-box { background-color: #111b27; border: 1px solid #1f6feb; padding: 20px; border-radius: 12px; margin-top: 20px; margin-bottom: 20px; color: #c9d1d9; }
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


if "pagina" not in st.session_state:
  st.session_state.pagina = "home"

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

  st.divider()
  if st.button("🏠 Torna alla Home", use_container_width=True):
    st.session_state.pagina = "home"
    st.rerun()

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
  return f"""
    🤖 **Report e Pronostico IA — {t1} vs {t2}**<br><br>
    * **Predizione Esito Finale (1X2):** L'intelligenza artificiale assegna il **{p1}%** di probabilità per la vittoria di {t1} (1), il **{px}%** per il pareggio (X) e il **{p2}%** per il successo esterno di {t2} (2).<br>
    * **Tendenza di Pronostico:** Il modello statistico indica un vantaggio potenziale per **{favorevole}** in base al confronto dei punti a partita (PPG) e alla solidità difensiva recente.<br>
    * **Consiglio Strategico:** Valutare coperture o mercati combinati (es. 1X o Goal) se la percentuale di pareggio supera il 25%.
    """


if st.session_state.pagina == "home":
  st.markdown(
      """
        <div style='background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; padding: 35px; border-radius: 16px; margin-top: 20px; text-align: center;'>
            <h1 style='color: #58a6ff; font-size: 38px; margin-bottom: 10px;'>⚽ b-betting Hub</h1>
            <p style='color: #8b949e; font-size: 16px; margin-bottom: 30px;'>Piattaforma avanzata di Live Data Architecture, Statistiche Sportive e Previsioni Algoritmiche.</p>
        </div>
    """,
      unsafe_allow_html=True,
  )

  col_h1, col_h2, col_h3 = st.columns([1, 2, 1])
  with col_h2:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    if st.button(
        "🚀 ACCEDI ALLA DASHBOARD", use_container_width=True, type="primary"
    ):
      st.session_state.pagina = "dashboard"
      st.rerun()

  st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

  col_feat1, col_feat2, col_feat3 = st.columns(3)
  with col_feat1:
    st.markdown(
        "<div style='background: #161b22; padding: 20px; border-radius: 12px;"
        " border: 1px solid #30363d; text-align: center;'><h3>📅</h3><h4>Palinsesto"
        " Live</h4><p style='color: #8b949e; font-size: 13px;'>Consulta"
        " calendari e partite aggiornate in tempo reale dai principali"
        " tornei.</p></div>",
        unsafe_allow_html=True,
    )
  with col_feat2:
    st.markdown(
        "<div style='background: #161b22; padding: 20px; border-radius: 12px;"
        " border: 1px solid #30363d; text-align: center;'><h3>📊</h3><h4>Classifiche"
        " Aggiornate</h4><p style='color: #8b949e; font-size: 13px;'>Analizza"
        " tabelle punti, gol fatti, subiti e differenza reti dei"
        " campionati.</p></div>",
        unsafe_allow_html=True,
    )
  with col_feat3:
    st.markdown(
        "<div style='background: #161b22; padding: 20px; border-radius: 12px;"
        " border: 1px solid #30363d; text-align: center;'><h3>🤖</h3><h4>Analisi"
        " IA & Pronostici</h4><p style='color: #8b949e; font-size: 13px;'>Algoritmi"
        " predittivi avanzati per stimare probabilità di match e quote"
        " di valore.</p></div>",
        unsafe_allow_html=True,
    )

else:
  col_title, col_home_btn = st.columns([0.80, 0.20])
  with col_title:
    st.title("⚽ b-betting")
    st.markdown("##### *Live Data Architecture & AI Sports Forecasting*")

  with col_home_btn:
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    if st.button("🏠 Home", use_container_width=True, help="Torna alla Home"):
      st.session_state.pagina = "home"
      st.rerun()

  st.divider()

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
          "Seleziona o digita una squadra per visualizzare le sue statistiche"
          " dedicate",
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

try:
    _matches = matches
except NameError:
    _matches = []

oggi = str(__import__('datetime').date.today())
match_prossima_giornata = []
for m in _matches:
    if isinstance(m, dict):
        if str(m.get('date', '')) >= oggi:
            if m.get('team1') and m.get('team2'):
                match_prossima_giornata.append(m)
                
                
                
                
                
        

      
if match_prossima_giornata:
    match_options = []
    match_dict = {}
    for m in match_prossima_giornata:
        data_m = m.get("date", "Data n.d.")
        t1_m = m.get("team1")
        t2_m = m.get("team2")
        label = f"{data_m} | {t1_m} vs {t2_m}"
        match_options.append(label)
        match_dict[label] = m

    st.markdown("🎯 *Seleziona una partita per il Confronto Diretto e Pronostico IA:*")
    
    partita_scelta_label = st.selectbox(
        "Seleziona la Partita della Giornata",
        match_options,
        key=f"match_scelto_stat_{len(match_options)}",
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

          st.markdown(
              "<br>**Barra Statistiche Squadra:**", unsafe_allow_html=True
          )
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

          st.markdown(
              "<br>**Barra Statistiche Squadra:**", unsafe_allow_html=True
          )
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
    
