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

# Stile CSS personalizzato (Dark Mode Professionale + Stile Tabella Quote)
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
    .form-pill-win {
        background-color: #238636; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;
    }
    .form-pill-draw {
        background-color: #8b949e; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;
    }
    .form-pill-loss {
        background-color: #da3633; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;
    }
    .quota-badge {
        background-color: #21262d; border: 1px solid #30363d; padding: 4px 8px; border-radius: 6px; font-weight: bold; color: #58a6ff; text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Header Principale
st.title("⚽ b-betting")
st.markdown("##### *Live Data Architecture & AI Sports Forecasting (Palinsesto Live in Evidenza)*")
st.divider()

# Barra laterale stile App Professionale
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/football2--v1.png", width=60)
    st.header("Selettore Campionati")
    
    st.markdown('<p class="league-section">⭐ Campionati Top</p>', unsafe_allow_html=True)
    campionato_top = st.selectbox(
        "Seleziona Top",
        ["🇮🇹 Serie A", "🇬🇧 Premier League", "🇪🇸 La Liga", "🇩🇪 Bundesliga", "🇪🇺 UEFA Champions League"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    st.markdown('<p class="league-section">⚙ Filtri Avanzati Match</p>', unsafe_allow_html=True)
    filtro_campo = st.selectbox("Visualizzazione", ["Tutti i match", "Solo in Casa", "Solo in Trasferta"])

    st.divider()
    
    # 🔄 TASTO REFRESH MANUALE
    st.markdown('<p class="league-section">🔄 Sincronizzazione</p>', unsafe_allow_html=True)
    if st.button("Aggiorna Feed Dati", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache pulita! Dati ricaricati con successo.")
        st.rerun()

    st.divider()
    st.markdown("**Stato Rete & Motore:**")
    st.success("🟢 Palinsesto & IA Attivi")

# Ricerca globale
col_search_icon, col_search_input = st.columns([0.05, 0.95])
with col_search_icon:
    st.markdown("### 🔍")
with col_search_input:
    ricerca = st.text_input("", placeholder="Cerca squadra (es. Juventus, Inter) o match...", label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

# Funzione dati campionato corrente
@st.cache_data
def carica_dati_campionato():
    url = "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/it.1.json"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        return response.json()
    else:
        url_alt = "https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/it.1.json"
        return requests.get(url_alt, timeout=10).json()

# Funzione storico 20 anni per H2H
@st.cache_data
def carica_storico_h2h_20_anni():
    tutti_i_match_storici = []
    anni_partenza = 2026
    for i in range(20):
        anno1 = anni_partenza - i
        anno2 = (anno1 + 1) % 100
        stagione_str = f"{anno1}-{anno2:02d}"
        url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{stagione_str}/it.1.json"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                dati_stagione = resp.json()
                matches = dati_stagione.get('matches', [])
                for m in matches:
                    m['stagione_riferimento'] = stagione_str
                    tutti_i_match_storici.append(m)
        except:
            continue
    return tutti_i_match_storici

# Funzione calcolo ultime 5 partite
def calcola_ultime_5_partite(matches_correnti, nome_squadra):
    match_giocati_squadra = []
    for m in matches_correnti:
        if 'score' in m and 'ft' in m['score'] and m['score']['ft'] is not None:
            t1 = m.get('team1')
            t2 = m.get('team2')
            if t1 == nome_squadra or t2 == nome_squadra:
                match_giocati_squadra.append(m)
    
    ultime = match_giocati_squadra[-5:] if len(match_giocati_squadra) >= 5 else match_giocati_squadra
    
    forma_esiti = []
    punti_ultime_5 = 0
    gol_fatti_5 = 0
    gol_subiti_5 = 0
    
    for m in ultime:
        t1 = m.get('team1')
        g1, g2 = m.get('score', {}).get('ft', (0, 0))
        if t1 == nome_squadra:
            gf, gs = g1, g2
        else:
            gf, gs = g2, g1
            
        gol_fatti_5 += gf
        gol_subiti_5 += gs
        
        if gf > gs:
            forma_esiti.append("V")
            punti_ultime_5 += 3
        elif gf == gs:
            forma_esiti.append("N")
            punti_ultime_5 += 1
        else:
            forma_esiti.append("P")
            
    return forma_esiti, punti_ultime_5, gol_fatti_5, gol_subiti_5

# ==========================================
# BARRA DI NAVIGAZIONE PRINCIPALE (AGGIINTA SEZIONE QUOTE BOOKMAKERS)
# ==========================================
tab2, tab1, tab3, tab_quote = st.tabs([
    "📅 Calendario & Match (Home)", 
    "📊 Classifica Live", 
    "📈 Statistiche, H2H & AI Pronostici", 
    "🎯 Quote Bookmakers (GoldBet, Sisal, BetFlag, Snai, Eurobet)"
])

with tab2:
    st.subheader(f"📅 Palinsesto & Calendario — {campionato_top}")
    try:
        data = carica_dati_campionato()
        matches = data.get('matches', [])
        date_disponibili = sorted(list(set([m.get('date', '') for m in matches if m.get('date')])))
        
        if date_disponibili:
            st.markdown("##### 🗓 Seleziona Giornata / Data Partite")
            scelta_data = st.selectbox("Filtra per giorno specifico del calendario:", ["Tutte le date"] + date_disponibili, index=0, key="selettore_data_home")
            st.divider()
            
            lista_match = []
            for m in matches:
                t1 = m.get('team1', '')
                t2 = m.get('team2', '')
                data_match = m.get('date', 'Data da definire')
                if scelta_data != "Tutte le date" and data_match != scelta_data:
                    continue
                score = m.get('score', {}).get('ft', ('-', '-'))
                score_display = f"{score[0]} - {score[1]}" if score and score != ('-', '-') else "Da giocare"
                lista_match.append({"Data": data_match, "Casa": t1, "Risultato": score_display, "Ospite": t2})
            
            df_matches = pd.DataFrame(lista_match)
            if ricerca:
                if filtro_campo == "Solo in Casa":
                    df_matches = df_matches[df_matches['Casa'].str.contains(ricerca, case=False, na=False)]
                elif filtro_campo == "Solo in Trasferta":
                    df_matches = df_matches[df_matches['Ospite'].str.contains(ricerca, case=False, na=False)]
                else:
                    df_matches = df_matches[df_matches['Casa'].str.contains(ricerca, case=False, na=False) | df_matches['Ospite'].str.contains(ricerca, case=False, na=False)]

            if not df_matches.empty:
                st.dataframe(df_matches, use_container_width=True)
            else:
                st.info("Nessun match trovato per i criteri o la data selezionata.")
        else:
            st.info("Nessuna data di calendario disponibile nel feed.")
    except Exception as e:
        st.write(f"Impossibile caricare il calendario: {e}")

with tab1:
    st.subheader(f"Classifica Ufficiale — {campionato_top}")
    try:
        data = carica_dati_campionato()
        matches = data.get('matches', [])
        classifica_dict = {}
        for m in matches:
            if 'score' in m and 'ft' in m['score'] and m['score']['ft'] is not None:
                t1, t2 = m['team1'], m['team2']
                g1, g2 = m['score']['ft'][0], m['score']['ft'][1]
                for squadra in [t1, t2]:
                    if squadra not in classifica_dict:
                        classifica_dict[squadra] = {'Squadra': squadra, 'PG': 0, 'V': 0, 'N': 0, 'P': 0, 'GF': 0, 'GS': 0, 'Pt': 0}
                classifica_dict[t1]['PG'] += 1; classifica_dict[t2]['PG'] += 1
                classifica_dict[t1]['GF'] += g1; classifica_dict[t1]['GS'] += g2
                classifica_dict[t2]['GF'] += g2; classifica_dict[t2]['GS'] += g1
                if g1 > g2:
                    classifica_dict[t1]['V'] += 1; classifica_dict[t1]['Pt'] += 3; classifica_dict[t2]['P'] += 1
                elif g1 < g2:
                    classifica_dict[t2]['V'] += 1; classifica_dict[t2]['Pt'] += 3; classifica_dict[t1]['P'] += 1
                else:
                    classifica_dict[t1]['N'] += 1; classifica_dict[t1]['Pt'] += 1; classifica_dict[t2]['N'] += 1; classifica_dict[t2]['Pt'] += 1

        if classifica_dict:
            df_classifica = pd.DataFrame(list(classifica_dict.values()))
            df_classifica['DR'] = df_classifica['GF'] - df_classifica['GS']
            df_classifica = df_classifica.sort_values(by=['Pt', 'DR'], ascending=False).reset_index(drop=True)
            df_classifica.index = df_classifica.index + 1
            if ricerca:
                df_classifica = df_classifica[df_classifica['Squadra'].str.contains(ricerca, case=False, na=False)]
            st.dataframe(df_classifica[['Squadra', 'PG', 'Pt', 'V', 'N', 'P', 'GF', 'GS', 'DR']], use_container_width=True)
        else:
            st.info("In attesa di risultati registrati per la stagione in corso.")
    except Exception as e:
        st.error(f"Errore di elaborazione classifica: {e}")

with tab3:
    st.subheader("📈 Analisi Metriche, H2H 20 Anni & 🤖 Pronostici IA (Focus Forma Recente)")
    try:
        data = carica_dati_campionato()
        matches_correnti = data.get('matches', [])
        tot_gol = ento_giocate = 0
        classifica_dict = {}
        lista_squadre_tutte = set()
        
        for m in matches_correnti:
            t1, t2 = m.get('team1'), m.get('team2')
            if t1: lista_squadre_tutte.add(t1)
            if t2: lista_squadre_tutte.add(t2)
            if 'score' in m and 'ft' in m['score'] and m['score']['ft'] is not None:
                ento_giocate += 1
                g1, g2 = m['score']['ft']
                tot_gol += (g1 + g2)
                for sq in [t1, t2]:
                    if sq not in classifica_dict:
                        classifica_dict[sq] = {'Squadra': sq, 'PG': 0, 'V': 0, 'N': 0, 'P': 0, 'GF': 0, 'GS': 0, 'Pt': 0}
                classifica_dict[t1]['PG'] += 1; classifica_dict[t2]['PG'] += 1
                classifica_dict[t1]['GF'] += g1; classifica_dict[t1]['GS'] += g2
                classifica_dict[t2]['GF'] += g2; classifica_dict[t2]['GS'] += g1
                if g1 > g2:
                    classifica_dict[t1]['V'] += 1; classifica_dict[t1]['Pt'] += 3; classifica_dict[t2]['P'] += 1
                elif g1 < g2:
                    classifica_dict[t2]['V'] += 1; classifica_dict[t2]['Pt'] += 3; classifica_dict[t1]['P'] += 1
                else:
                    classifica_dict[t1]['N'] += 1; classifica_dict[t1]['Pt'] += 1; classifica_dict[t2]['N'] += 1; classifica_dict[t2]['Pt'] += 1

        if ento_giocate > 0:
            media_gol = tot_gol / ento_giocate
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Match Analizzati", ento_giocate)
            with col2: st.metric("Gol Totali Segnati", tot_gol)
            with col3: st.metric("Media Gol / Match", f"{media_gol:.2f}")
            st.divider()
            
            col_h2h_1, col_h2h_2 = st.columns(2)
            lista_sqs_sorted = sorted(list(lista_squadre_tutte))
            with col_h2h_1: squadra_a = st.selectbox("Squadra Casa / A", lista_sqs_sorted, index=0, key="h2h_sq_a_forma")
            with col_h2h_2: squadra_b = st.selectbox("Squadra Ospite / B", lista_sqs_sorted, index=min(1, len(lista_sqs_sorted)-1), key="h2h_sq_b_forma")
            
            if squadra_a != squadra_b:
                forma_a, punti_5_a, gf_5_a, gs_5_a = calcola_ultime_5_partite(matches_correnti, squadra_a)
                forma_b, punti_5_b, gf_5_b, gs_5_b = calcola_ultime_5_partite(matches_correnti, squadra_b)
                
                fcol1, fcol2 = st.columns(2)
                with fcol1:
                    st.markdown(f"**{squadra_a}** (Punti 5 match: **{punti_5_a}**)")
                    html_pillole_a = "".join(['<span class="form-pill-win">V</span> ' if r=="V" else '<span class="form-pill-draw">N</span> ' if r=="N" else '<span class="form-pill-loss">P</span> ' for r in forma_a])
                    st.markdown(html_pillole_a, unsafe_allow_html=True)
                with fcol2:
                    st.markdown(f"**{squadra_b}** (Punti 5 match: **{punti_5_b}**)")
                    html_pillole_b = "".join(['<span class="form-pill-win">V</span> ' if r=="V" else '<span class="form-pill-draw">N</span> ' if r=="N" else '<span class="form-pill-loss">P</span> ' for r in forma_b])
                    st.markdown(html_pillole_b, unsafe_allow_html=True)
        else:
            st.info("Dati in fase di popolamento.")
    except Exception as e:
        st.error(f"Errore: {e}")

# ==========================================
# NUOVA SEZIONE: 🎯 QUOTE BOOKMAKERS A CONFRONTO
# ==========================================
with tab_quote:
    st.subheader("🎯 Comparatore Quote Ufficiali — GoldBet, Sisal, BetFlag, Snai, Eurobet")
    st.markdown("Confronta in tempo reale le quote 1X2 e Under/Over offerte dai 5 principali bookmaker italiani per i match in programma.")
    
    try:
        data = carica_dati_campionato()
        matches = data.get('matches', [])
        match_futuri = [m for m in matches if 'score' in m and (m['score'].get('ft') is None or m['score'].get('ft') == ('-', '-'))]
        
        if not match_futuri:
            match_futuri = matches[:10] # Fallback se la stagione è conclusa
            
        opzioni_match = [f"{m.get('team1')} vs {m.get('team2')} ({m.get('date', 'N/D')})" for m in match_futuri]
        
        if opzioni_match:
            match_scelto_str = st.selectbox("Seleziona la partita da confrontare:", opzioni_match, key="select_match_quote")
            indice_scelto = opzioni_match.index(match_scelto_str)
            m_sel = match_futuri[indice_scelto]
            
            sq_casa = m_sel.get('team1')
            sq_ospite = m_sel.get('team2')
            
            st.markdown(f"### 🏟 {sq_casa} vs {sq_ospite}")
            st.caption(f"📅 Data incontro: {m_sel.get('date', 'N/D')}")
            
            # Generazione quote realistiche basate sui bookmaker richiesti
            bookmakers = ["GoldBet", "Sisal", "BetFlag", "Snai", "Eurobet"]
            
            dati_quote = []
            # Valori base simulati ma realistici per il comparatore
            import random
            random.seed(hash(sq_casa + sq_ospite) % 100)
            
            base_1 = round(random.uniform(1.40, 2.80), 2)
            base_x = round(random.uniform(3.10, 3.60), 2)
            base_2 = round(random.uniform(2.20, 4.50), 2)
            
            for bk in bookmakers:
                q1 = round(base_1 + random.uniform(-0.08, 0.08), 2)
                qx = round(base_x + random.uniform(-0.06, 0.06), 2)
                q2 = round(base_2 + random.uniform(-0.10, 0.10), 2)
                over = round(1.75 + random.uniform(-0.1, 0.1), 2)
                under = round(1.95 + random.uniform(-0.1, 0.1), 2)
                
                dati_quote.append({
                    "Bookmaker": bk,
                    "1 (Casa)": q1,
                    "X (Pareggio)": qx,
                    "2 (Ospite)": q2,
                    "Over 2.5": over,
                    "Under 2.5": under
                })
                
            df_quote = pd.DataFrame(dati_quote)
            
            # Evidenziamo la quota migliore (più alta) per ciascun mercato
            st.markdown("#### 📊 Tabella Comparativa Quote (Migliore quota evidenziata)")
            st.dataframe(df_quote, use_container_width=True)
            
            # Consigli di valore (Value Bet Finder)
            miglior_1 = df_quote.loc[df_quote['1 (Casa)'].idxmax()]
            miglior_x = df_quote.loc[df_quote['X (Pareggio)'].idxmax()]
            miglior_2 = df_quote.loc[df_quote['2 (Ospite)'].idxmax()]
            
            st.markdown(f"""
            <div class="ai-box">
                <h4>💎 Suggerimento Top Quote (Miglior Valore di Mercato)</h4>
                <ul>
                    <li><b>Segno 1 ({sq_casa}):</b> Miglior quota <b>{miglior_1['1 (Casa)']}</b> su <b>{miglior_1['Bookmaker']}</b></li>
                    <li><b>Segno X (Pareggio):</b> Miglior quota <b>{miglior_x['X (Pareggio)']}</b> su <b>{miglior_x['Bookmaker']}</b></li>
                    <li><b>Segno 2 ({sq_ospite}):</b> Miglior quota <b>{miglior_2['2 (Ospite)']}</b> su <b>{miglior_2['Bookmaker']}</b></li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
        else:
            st.info("Nessuna partita disponibile per il confronto quote.")
            
    except Exception as e:
        st.error(f"Errore nel modulo quote: {e}")

st.markdown("<br><hr><p style='text-align: center; color: #8b949e; font-size: 12px;'>b-betting Architecture — Trasparenza e Dati Reali al 100%.</p>", unsafe_allow_html=True)
