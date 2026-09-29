import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="b-betting — Live Dashboard",
    page_icon="⚽",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stTextInput > div > div > input { background-color: #161b22; color: #c9d1d9; border-radius: 8px; border: 1px solid #30363d; }
    .league-section { color: #8b949e; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; }
    .ai-box, .calc-box { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; margin-top: 15px; margin-bottom: 15px; }
    .form-pill-win { background-color: #238636; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .form-pill-draw { background-color: #8b949e; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .form-pill-loss { background-color: #da3633; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    </style>
""", unsafe_allow_html=True)

# Gestione dello stato iniziale
if "df_schedina" not in st.session_state:
    st.session_state.df_schedina = pd.DataFrame([
        {"Partita": "Juventus vs Inter", "Segno / Esito": "1", "Quota": 2.10, "Bookmaker": "GoldBet"}
    ])

# Header Principale con Tasto Home in alto a destra
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
    "Italia - Serie A", "Italia - Serie B", "Inghilterra - Premier League", 
    "Spagna - La Liga", "Germania - Bundesliga", "Francia - Ligue 1", "UEFA Champions League"
]

mapping_file_torneo = {
    "Italia - Serie A": "it.1.json", "Italia - Serie B": "it.2.json",
    "Inghilterra - Premier League": "en.1.json", "Spagna - La Liga": "es.1.json",
    "Germania - Bundesliga": "de.1.json", "Francia - Ligue 1": "fr.1.json",
    "UEFA Champions League": "cl.json"
}

with st.sidebar:
    st.header("Selettore Tornei")
    stagione_selezionata = st.selectbox("Stagione", ["2026-27", "2025-26", "2024-25"])
    campionato_top = st.selectbox("Torneo", campionati_disponibili)
    if st.button("🔄 Aggiorna Dati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

@st.cache_data
def carica_dati_campionato(nome_campionato, stagione):
    nome_file = mapping_file_torneo.get(nome_campionato, "it.1.json")
    for p in [f"{stagione}/{nome_file}", nome_file]:
        url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{p}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                res = r.json()
                if isinstance(res, list): return {"matches": res}
                if isinstance(res, dict):
                    if "matches" in res: return res
                    for v in res.values():
                        if isinstance(v, list): return {"matches": v}
        except:
            pass
    return {"matches": []}

def calcola_statistiche(matches, squadra):
    match_squadra = []
    for m in matches:
        if not isinstance(m, dict) or 'score' not in m or not isinstance(m['score'], dict) or m['score'].get('ft') is None:
            continue
        if m.get('team1') == squadra or m.get('team2') == squadra:
            match_squadra.append(m)
    
    tot = len(match_squadra)
    if tot == 0: return None
    
    gf, gs, pt = 0, 0, 0
    forma = []
    for m in match_squadra:
        t1, t2 = m.get('team1'), m.get('team2')
        ft = m['score']['ft']
        g1, g2 = ft[0], ft[1]
        squadra_casa = (t1 == squadra)
        m_gf = g1 if squadra_casa else g2
        m_gs = g2 if squadra_casa else g1
        
        gf += m_gf
        gs += m_gs
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
        "forma": forma[-5:],
        "ppg": round(pt / tot, 2),
        "gf": gf, "gs": gs,
        "gf_avg": round(gf / tot, 2),
        "gs_avg": round(gs / tot, 2)
    }

tab1, tab2, tab3 = st.tabs(["📅 Palinsesto", "📊 Classifica", "📈 Statistiche"])

with tab1:
    st.subheader("Palinsesto Match")
    data = carica_dati_campionato(campionato_top, stagione_selezionata)
    matches = data.get('matches', [])
    if matches:
        lista = [{"Data": m.get('date', ''), "Casa": m.get('team1', ''), "Ospite": m.get('team2', '')} for m in matches if isinstance(m, dict)]
        st.dataframe(pd.DataFrame(lista), use_container_width=True)
    else:
        st.warning("Dati non disponibili per questo torneo.")

with tab2:
    st.subheader("Classifica Live")
    data = carica_dati_campionato(campionato_top, stagione_selezionata)
    matches = data.get('matches', [])
    classifica = {}
    for m in matches:
        if isinstance(m, dict) and 'score' in m and isinstance(m['score'], dict) and m['score'].get('ft'):
            t1, t2 = m.get('team1'), m.get('team2')
            if not t1 or not t2: continue
            ft = m['score']['ft']
            g1, g2 = ft[0], ft[1]
            for sq in [t1, t2]:
                if sq not in classifica: classifica[sq] = {'Squadra': sq, 'PG': 0, 'Pt': 0, 'GF': 0, 'GS': 0}
            classifica[t1]['PG'] += 1; classifica[t2]['PG'] += 1
            classifica[t1]['GF'] += g1; classifica[t1]['GS'] += g2
            classifica[t2]['GF'] += g2; classifica[t2]['GS'] += g1
            if g1 > g2: classifica[t1]['Pt'] += 3
            elif g1 < g2: classifica[t2]['Pt'] += 3
            else: classifica[t1]['Pt'] += 1; classifica[t2]['Pt'] += 1
    if classifica:
        df_c = pd.DataFrame(list(classifica.values()))
        df_c['DR'] = df_c['GF'] - df_c['GS']
        df_c = df_c.sort_values(by=['Pt', 'DR'], ascending=False).reset_index(drop=True)
        df_c.index += 1
        st.dataframe(df_c, use_container_width=True)
    else:
        st.warning("Classifica non disponibile.")

with tab3:
    st.subheader("Analisi Statistica Squadra")
    data = carica_dati_campionato(campionato_top, stagione_selezionata)
    matches = data.get('matches', [])
    squadre = sorted(list(set([m.get('team1') for m in matches if isinstance(m, dict) and m.get('team1')] + [m.get('team2') for m in matches if isinstance(m, dict) and m.get('team2')])))
    
    if squadre:
        sq_scelta = st.selectbox("Seleziona Squadra", squadre)
        stats = calcola_statistiche(matches, sq_scelta)
        if stats:
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Partite Analizzate", stats['tot'])
            with col2: st.metric("Media Punti (PPG)", stats['ppg'])
            with col3: st.metric("Gol Fatti / Media", f"{stats['gf']} ({stats['gf_avg']})")
            
            col4, col5 = st.columns(2)
            with col4: st.metric("Gol Subiti / Media", f"{stats['gs']} ({stats['gs_avg']})")
            with col5:
                forma_str = " ".join(stats['forma'])
                st.markdown(f"**Ultime 5:** {forma_str}")
        else:
            st.info("Nessun dato di match giocati per questa squadra.")
    else:
        st.warning("Nessuna squadra trovata.")
        
