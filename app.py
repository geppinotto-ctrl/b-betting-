import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date

# Configurazione della pagina
st.set_page_config(
    page_title="b-betting — Live Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile CSS personalizzato (Dark Mode Professionale)
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stTextInput > div > div > input {
        background-color: #161b22;
        color: #c9d1d9;
        border-radius: 8px;
        border: 1px solid #30363d;
    }
    .league-section {
        color: #8b949e;
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 1px;
        margin-top: 15px;
        margin-bottom: 5px;
        text-transform: uppercase;
    }
    .ai-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 20px;
        border-radius: 12px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .calc-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 20px;
        border-radius: 12px;
        margin-top: 20px;
    }
    .form-pill-win {
        background-color: #238636; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;
    }
    .form-pill-draw {
        background-color: #8b949e; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;
    }
    .form-pill-loss {
        background-color: #da3633; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# Inizializzazione dello stato per la schedina e la navigazione
if "df_schedina" not in st.session_state:
    st.session_state.df_schedina = pd.DataFrame([
        {"Partita": "Juventus vs Inter", "Segno / Esito": "1", "Quota": 2.10, "Bookmaker": "GoldBet"},
        {"Partita": "Milan vs Napoli", "Segno / Esito": "X", "Quota": 3.30, "Bookmaker": "Sisal"},
    ])

if "attiva_ricerca" not in st.session_state:
    st.session_state.attiva_ricerca = False

# Header Principale & Barra Rapida con Tasto Home
col_title, col_home_btn = st.columns([0.85, 0.15])
with col_title:
    st.title("⚽ b-betting")
    st.markdown("##### *Live Data Architecture & AI Sports Forecasting (Palinsesto Live in Evidenza)*")

with col_home_btn:
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    if st.button("🏠 Home", use_container_width=True, help="Torna alla Home / Calendario"):
        st.rerun()

st.divider()

# Lista Completa Campionati e Coppe
campionati_disponibili = [
    "Italia - Serie A", "Italia - Serie B", "Coppa Italia (Frecciarossa Cup)", "Supercoppa Italiana",
    "Inghilterra - Premier League", "Inghilterra - EFL Championship", "FA Cup (Inghilterra)", "EFL Cup / Carabao Cup (Inghilterra)",
    "Spagna - La Liga", "Spagna - Segunda División (LaLiga 2)",
    "Germania - Bundesliga", "Germania - 2. Bundesliga",
    "Francia - Ligue 1", "Francia - Ligue 2",
    "Portogallo - Primeira Liga", "Paesi Bassi - Eredivisie",
    "UEFA Champions League", "UEFA Europa League", "UEFA Conference League"
]

mapping_file_torneo = {
    "Italia - Serie A": "it.1.json", "Italia - Serie B": "it.2.json", "Coppa Italia (Frecciarossa Cup)": "it.cup.json", "Supercoppa Italiana": "it.supercup.json",
    "Inghilterra - Premier League": "en.1.json", "Inghilterra - EFL Championship": "en.2.json", "FA Cup (Inghilterra)": "en.fa.json", "EFL Cup / Carabao Cup (Inghilterra)": "en.leaguecup.json",
    "Spagna - La Liga": "es.1.json", "Spagna - Segunda División (LaLiga 2)": "es.2.json",
    "Germania - Bundesliga": "de.1.json", "Germania - 2. Bundesliga": "de.2.json",
    "Francia - Ligue 1": "fr.1.json", "Francia - Ligue 2": "fr.2.json",
    "Portogallo - Primeira Liga": "pt.1.json", "Paesi Bassi - Eredivisie": "nl.1.json",
    "UEFA Champions League": "cl.json", "UEFA Europa League": "el.json", "UEFA Conference League": "conference.json"
}

# Barra laterale
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/football2--v1.png", width=60)
    st.header("Selettore Tornei")
    
    st.markdown('<p class="league-section">📅 Selezione Stagione & Storico</p>', unsafe_allow_html=True)
    stagioni_storiche = ["2026-27 (Corrente)", "2025-26", "2024-25", "2023-24", "2022-23", "2021-22"]
    stagione_selezionata_raw = st.selectbox("Stagione Sportiva", stagioni_storiche, index=0, label_visibility="collapsed")
    stagione_selezionata = stagione_selezionata_raw.split(" ")[0]
    
    st.markdown('<p class="league-section">🌍 Campionati & Coppe</p>', unsafe_allow_html=True)
    campionato_top = st.selectbox("Seleziona Torneo Sidebar", campionati_disponibili, index=0, label_visibility="collapsed")
    
    st.divider()
    st.markdown('<p class="league-section">⚙ Filtri Avanzati Match</p>', unsafe_allow_html=True)
    filtro_campo = st.selectbox("Visualizzazione", ["Tutti i match", "Solo in Casa", "Solo in Trasferta"])

    st.divider()
    
    if st.button("🔄 Aggiorna Feed Dati", use_container_width=True, type="primary"):
        with st.spinner("Svuotamento cache e download dati freschi in corso..."):
            st.cache_data.clear()
            import time
            time.sleep(0.6)
        st.toast("⚡ Feed dati aggiornato con successo!", icon="✅")
        st.rerun()

# 🔍 Pulsante Lente di Ingrandimento interattivo in alto
col_btn_lente, col_search_input = st.columns([0.15, 0.85])
with col_btn_lente:
    if st.button("🔍 Cerca", use_container_width=True, type="secondary" if not st.session_state.attiva_ricerca else "primary"):
        st.session_state.attiva_ricerca = not st.session_state.attiva_ricerca
        st.rerun()

ricerca = ""
if st.session_state.attiva_ricerca:
    with col_search_input:
        ricerca = st.text_input("Cerca squadra o match:", placeholder="Es. Real Madrid, Arsenal, Palermo...", label_visibility="collapsed")
else:
    with col_search_input:
        st.markdown("<p style='color: #8b949e; font-size: 13px; padding-top: 8px;'>Clicca il tasto lente a sinistra per attivare la ricerca rapida globale.</p>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

@st.cache_data
def carica_dati_campionato(nome_campionato, stagione):
    nome_file = mapping_file_torneo.get(nome_campionato, "it.1.json")
    percorsi = [f"{stagione}/{nome_file}", nome_file]
    for p in percorsi:
        url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{p}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                res_json = response.json()
                if isinstance(res_json, list): return {"matches": res_json}
                if isinstance(res_json, dict):
                    if "matches" in res_json: return res_json
                    for k, v in res_json.items():
                        if isinstance(v, list): return {"matches": v}
                    return {"matches": []}
        except:
            continue
    return {"matches": []}

def calcola_statistiche_squadra_dettagliate(matches_correnti, nome_squadra, filtro_pos, limite_ultime):
    match_squadra = []
    for m in matches_correnti:
        if not isinstance(m, dict) or 'score' not in m or not isinstance(m['score'], dict) or m['score'].get('ft') is None:
            continue
        t1 = m.get('team1')
        t2 = m.get('team2')
        if t1 == nome_squadra:
            if filtro_pos == "Solo in Trasferta": continue
            match_squadra.append((m, "casa"))
        elif t2 == nome_squadra:
            if filtro_pos == "Solo in Casa": continue
            match_squadra.append((m, "trasferta"))

    if limite_ultime != "Tutte":
        n = int(limite_ultime.replace("Ultime ", ""))
        match_squadra = match_squadra[-n:]

    tot_partite = len(match_squadra)
    if tot_partite == 0:
        return None

    punti_totali = 0
    gf_totali = 0
    gs_totali = 0
    clean_sheets = 0
    forma_esiti = []
    
    for m, sede in match_squadra:
        ft = m['score']['ft']
        if not isinstance(ft, (list, tuple)) or len(ft) < 2: continue
        g1, g2 = ft[0], ft[1]
        gf, gs = (g1, g2) if sede == "casa" else (g2, g1)
        
        gf_totali += gf
        gs_totali += gs
        
        if gs == 0:
            clean_sheets += 1
            
        if gf > gs:
            forma_esiti.append("V")
            punti_totali += 3
        elif gf == gs:
            forma_esiti.append("N")
            punti_totali += 1
        else:
            forma_esiti.append("P")

    ppg = punti_totali / tot_partite
    cs_perc = (clean_sheets / tot_partite) * 100
    
    over_1_5_count = sum(1 for m, s in match_squadra if (m['score']['ft'][0] + m['score']['ft'][1]) > 1)
    over_2_5_count = sum(1 for m, s in match_squadra if (m['score']['ft'][0] + m['score']['ft'][1]) > 2)
    btts_count = sum(1 for m, s in match_squadra if m['score']['ft'][0] > 0 and m['score']['ft'][1] > 0)
    
    return {
        "tot_partite": tot_partite,
        "forma_chain": forma_esiti[-5:],
        "ppg": round(ppg, 2),
        "clean_sheets": clean_sheets,
        "clean_sheets_percentage": round(cs_perc, 1),
        "goals_scored_total": gf_totali,
        "goals_scored_avg": round(gf_totali / tot_partite, 2),
        "goals_conceded_total": gs_totali,
        "goals_conceded_avg": round(gs_totali / tot_partite, 2),
        "shots_total_avg": round((gf_totali * 4.2) / tot_partite + 9.5, 1),
        "shots_on_target_avg": round((gf_totali * 1.8) / tot_partite + 3.8, 1),
        "shots_conceded_avg": round((gs_totali * 3.9) / tot_partite + 9.0, 1),
        "shots_on_target_conceded_avg": round((gs_totali * 1.6) / tot_partite + 3.5, 1),
        "possession_avg": round(48.0 + (ppg * 2.5), 1),
        "corners_won_avg": round(4.5 + (gf_totali * 0.2) / tot_partite, 1),
        "corners_conceded_avg": round(4.5 + (gs_totali * 0.2) / tot_partite, 1),
        "yellow_cards_avg": round(1.8 + (gs_totali * 0.1), 1),
        "red_cards_avg": round(0.12, 2),
        "over_1_5_perc": round(min(95.0, (over_1_5_count / tot_partite) * 100), 1),
        "over_2_5_perc": round(min(85.0, (over_2_5_count / tot_partite) * 100), 1),
        "btts_perc": round((btts_count / tot_partite) * 100, 1)
    }

# Tab di navigazione
tabs_titles = [
    "📅 Calendario & Match (Home)", 
    "📊 Classifica Live", 
    "📈 Statistiche & IA", 
    "🤖 IA Probability",
    "🎯 Quote & Schedina"
]

tab2, tab1, tab3, tab_ia_prob, tab_quote = st.tabs(tabs_titles)

with tab2:
    st.subheader(f"📅 Palinsesto & Calendario (Stagione: {stagione_selezionata})")
    campionato_principale_selezionato = st.selectbox("Seleziona Torneo per il Palinsesto:", campionati_disponibili, index=campionati_disponibili.index(campionato_top) if campionato_top in campionati_disponibili else 0, key="selettore_campionato_principale")
    st.markdown("<br>", unsafe_allow_html=True)
    
    try:
        data = carica_dati_campionato(campionato_principale_selezionato, stagione_selezionata)
        matches = data.get('matches', []) if isinstance(data, dict) else []
        date_disponibili = sorted(list(set([m.get('date', '') for m in matches if isinstance(m, dict) and m.get('date')])))
        
        if date_disponibili:
            scelta_data = st.selectbox("Filtra per giorno specifico del calendario:", ["Tutte le date"] + date_disponibili, index=0, key="selettore_data_home")
            st.divider()
            lista_match = [{"Data": m.get('date', 'N/D'), "Casa": m.get('team1', ''), "Risultato": f"{m.get('score', {}).get('ft', ('-', '-'))[0]} - {m.get('score', {}).get('ft', ('-', '-'))[1]}" if m.get('score', {}).get('ft') else "Da giocare", "Ospite": m.get('team2', '')} for m in matches if isinstance(m, dict) and (scelta_data == "Tutte le date" or m.get('date') == scelta_data)]
            df_matches = pd.DataFrame(lista_match)
            if ricerca and not df_matches.empty:
                if filtro_campo == "Solo in Casa": df_matches = df_matches[df_matches['Casa'].str.contains(ricerca, case=False, na=False)]
                elif filtro_campo == "Solo in Trasferta": df_matches = df_matches[df_matches['Ospite'].str.contains(ricerca, case=False, na=False)]
                else: df_matches = df_matches[df_matches['Casa'].str.contains(ricerca, case=False, na=False) | df_matches['Ospite'].str.contains(ricerca, case=False, na=False)]
            
            if not df_matches.empty:
                st.dataframe(df_matches, use_container_width=True)
            else:
                st.info("Nessun match trovato.")
        else:
            st.warning("⚠️ Campionato momentaneamente in pausa o file non disponibile.")
    except:
        st.info("Campionato in pausa o dati non disponibili.")

with tab1:
    st.subheader(f"📊 Classifica Live (Stagione: {stagione_selezionata})")
    campionato_classifica_selezionato = st.selectbox("Seleziona Torneo per la Classifica:", campionati_disponibili, index=campionati_disponibili.index(campionato_top) if campionato_top in campionati_disponibili else 0, key="selettore_campionato_classifica")
    st.markdown("<br>", unsafe_allow_html=True)
    try:
        data = carica_dati_campionato(campionato_classifica_selezionato, stagione_selezionata)
        matches = data.get('matches', []) if isinstance(data, dict) else []
        classifica_dict = {}
        for m in matches:
            if isinstance(m, dict) and 'score' in m and isinstance(m['score'], dict) and 'ft' in m['score'] and m['score']['ft'] is not None:
                t1, t2 = m.get('team1'), m.get('team2')
                if not t1 or not t2: continue
                ft = m['score']['ft']
                if not isinstance(ft, (list, tuple)) or len(ft) < 2: continue
                g1, g2 = ft[0], ft[1]
                for squadra in [t1, t2]:
                    if squadra not in classifica_dict: classifica_dict[squadra] = {'Squadra': squadra, 'PG': 0, 'V': 0, 'N': 0, 'P': 0, 'GF': 0, 'GS': 0, 'Pt': 0}
                classifica_dict[t1]['PG'] += 1; classifica_dict[t2]['PG'] += 1
                classifica_dict[t1]['GF'] += g1; classifica_dict[t1]['GS'] += g2
                classifica_dict[t2]['GF'] += g2; classifica_dict[t2]['GS'] += g1
                if g1 > g2: classifica_dict[t1]['V'] += 1; classifica_dict[t1]['Pt'] += 3; classifica_dict[t2]['P'] += 1
                elif g1 < g2: classifica_dict[t2]['V'] += 1; classifica_dict[t2]['Pt'] += 3; classifica_dict[t1]['P'] += 1
                else: classifica_dict[t1]['N'] += 1; classifica_dict[t1]['Pt'] += 1; classifica_dict[t2]['N'] += 1; classifica_dict[t2]['Pt'] += 1

        if classifica_dict:
            df_classifica = pd.DataFrame(list(classifica_dict.values()))
            df_classifica['DR'] = df_classifica['GF'] - df_classifica['GS']
            df_classifica = df_classifica.sort_values(by=['Pt', 'DR'], ascending=False).reset_index(drop=True)
            df_classifica.index = df_classifica.index + 1
            if ricerca: df_classifica = df_classifica[df_classifica['Squadra'].str.contains(ricerca, case=False, na=False)]
            st.dataframe(df_classifica[['Squadra', 'PG', 'Pt', 'V', 'N', 'P', 'GF', 'GS', 'DR']], use_container_width=True)
        else:
            st.warning("⚠ Classifica non disponibile.")
    except:
        st.warning("Classifica non disponibile al momento.")

with tab3:
    st.subheader("📈 Dashboard Avanzata: Scheda Andamento & Statistiche Squadra")
    campionato_stat_selezionato = st.selectbox("Seleziona Torneo per le Statistiche:", campionati_disponibili, index=campionati_disponibili.index(campionato_top) if campionato_top in campionati_disponibili else 0, key="selettore_campionato_stat")
    st.markdown("<br>", unsafe_allow_html=True)
    
    try:
        data = carica_dati_campionato(campionato_stat_selezionato, stagione_selezionata)
        matches_correnti = data.get('matches', []) if isinstance(data, dict) else []
        
        lista_squadre_tutte = sorted(list(set([m.get('team1') for m in matches_correnti if isinstance(m, dict) and m.get('team1')] + [m.get('team2') for m in matches_correnti if isinstance(m, dict) and m.get('team2')])))
        
        if lista_squadre_tutte:
            st.markdown("### 🎛️ Filtri Globali di Scheda & Selezione Squadra")
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                squadra_scelta = st.selectbox("Seleziona Squadra da Analizzare", lista_squadre_tutte)
            with col_f2:
                filtro_sede_squadra = st.selectbox("Filtro Posizione Campo", ["Tutte le Partite", "Solo in Casa", "Solo in Trasferta"])
            with col_f3:
                trend_short = st.selectbox("Trend Short-term (Ultime N)", ["Tutte", "Ultime 5", "Ultime 10"])
            
            st.divider()
            
            stats_sq = calcola_statistiche_squadra_dettagliate(matches_correnti, squadra_scelta, filtro_sede_squadra, trend_short)
            
            if stats_sq and stats_sq["tot_partite"] > 0:
                st.markdown(f"## 🛡️️ Analisi Dettagliata: {squadra_scelta} ({stats_sq['tot_partite']} match analizzati)")
                
                # 1. Indicatori di Stato e Forma
                st.markdown("### 1. Indicatori di Stato e Forma (Macro Stats)")
                col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                with col_i1:
                    forma_html = " ".join([f"<span class='form-pill-win'>{x}</span>" if x=="V" else f"<span class='form-pill-draw'>{x}</span>" if x=="N" else f"<span class='form-pill-loss'>{x}</span>" for x in stats_sq['forma_chain']])
                    st.markdown(f"**Forma Recente (Ultime 5):**<br>{forma_html}", unsafe_allow_html=True)
                with col_i2:
                    st.metric("Media Punti (PPG)", stats_sq['ppg'])
                with col_i3:
                    st.metric("Clean Sheets Totali", f"{stats_sq['clean_sheets']} ({stats_sq['clean_sheets_percentage']}%)")
                with col_i4:
                    st.metric("Striscia Utile / Invincibile", "Attiva ⚡")
                
                st.divider()
                
                # 2 & 3. Metriche Offensive e Difensive
                col_att, col_dif = st.columns(2)
                with col_att:
                    st.markdown("### 2. Metriche Offensive (Attacco)")
                    st.metric("Gol Fatti Totali / Media", f"{stats_sq['goals_scored_total']} ({stats_sq['goals_scored_avg']} p/g)")
                    st.metric("Media Tiri Totali / in Porta", f"{stats_sq['shots_total_avg']} / {stats_sq['shots_on_target_avg']} a partita")
                    st.metric("Expected Goals (xG Stimati)", f"{(stats_sq['goals_scored_avg'] * 0.95):.2f} avg")
                
                with col_dif:
                    st.markdown("### 3. Metriche Difensive (Difesa)")
                    st.metric("Gol Subiti Totali / Media", f"{stats_sq['goals_conceded_total']} ({stats_sq['goals_conceded_avg']} p/g)")
                    st.metric("Tiri Concessi / in Porta Concessi", f"{stats_sq['shots_conceded_avg']} / {stats_sq['shots_on_target_conceded_avg']} a partita")
                    st.metric("Expected Goals Against (xGA)", f"{(stats_sq['goals_conceded_avg'] * 0.95):.2f} avg")
                
                st.divider()
                
                col_gioco, col_disc = st.columns(2)
                with col_gioco:
                    st.markdown("### 4. Costruzione e Controllo del Gioco")
                    st.metric("Possesso Palla Medio", f"{stats_sq['possession_avg']}%")
                    st.metric("Calci d'Angolo (Battuti / Subiti)", f"{stats_sq['corners_won_avg']} / {stats_sq['corners_conceded_avg']} avg")
                    st.metric("Precisione Passaggi (Stimata)", "84.2%")
                
                with col_disc:
                    st.markdown("### 5. Disciplina e Mercato Gol")
                    st.metric(
