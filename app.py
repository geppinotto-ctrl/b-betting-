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

# Stile CSS personalizzato (Dark Mode Professionale + Stile Barra Giorni)
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
    </style>
""", unsafe_allow_html=True)

# Header Principale
st.title("⚽ b-betting")
st.markdown("##### *Live Data Architecture & AI Sports Forecasting (Palinsesto Giornaliero Dinamico)*")
st.divider()

# Barra laterale stile App Professionale con filtri avanzati e Refresh Button
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
    
    st.markdown('<p class="league-section">⚙️ Filtri Avanzati Match</p>', unsafe_allow_html=True)
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
    st.success("🟢 Palinsesto Giornaliero & IA Attivi")

# Ricerca
col_search_icon, col_search_input = st.columns([0.05, 0.95])
with col_search_icon:
    st.markdown("### 🔍")
with col_search_input:
    ricerca = st.text_input("", placeholder="Cerca squadra (es. Juventus, Inter) o match...", label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

# Funzione per caricare i dati della stagione corrente (con cache)
@st.cache_data
def carica_dati_campionato():
    url = "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/it.1.json"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        return response.json()
    else:
        url_alt = "https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/it.1.json"
        return requests.get(url_alt, timeout=10).json()

# Funzione per caricare lo storico pluriennale (ultimi 20 anni per H2H)
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

# Funzione per calcolare le ultime 5 partite di una squadra
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

# Layout a schede
tab1, tab2, tab3 = st.tabs(["📊 Classifica Live", "📅 Calendario & Match", "📈 Statistiche, H2H & AI Pronostici"])

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

with tab2:
    st.subheader(f"📅 Palinsesto Calendario & Match — {campionato_top}")
    try:
        data = carica_dati_campionato()
        matches = data.get('matches', [])
        
        # Estrazione delle date uniche presenti nel calendario
        date_disponibili = sorted(list(set([m.get('date', '') for m in matches if m.get('date')])))
        
        if date_disponibili:
            st.markdown("##### 🗓 Seleziona Giornata / Data Partite")
            
            # Creazione della griglia scorrevole di pulsanti stile palinsesto professionale
            # Mostriamo le date in orizzontale usando colonne multiple
            num_cols = min(7, len(date_cols := date_disponibili))
            if num_cols > 0:
                cols_giorni = st.columns(num_cols)
                
                # Inizializzazione della data selezionata nello state di sessione se non presente
                if 'data_selezionata' not in st.session_state:
                    # Imposta per default la data odierna o la prima disponibile
                    oggi_str = datetime.now().strftime('%Y-%m-%d')
                    st.session_state.data_selezionata = oggi_str if oggi_str in date_disponibili else date_disponibili[0]
                
                # Renderizziamo una selezione compatta dei giorni (mostriamo una finestra scorrevole o le principali)
                # Per comodità e pulizia, mostriamo un selettore a tendina avanzato o i pulsanti rapidi dei giorni chiave
                scelta_data = st.selectbox("Filtra per giorno specifico del calendario:", ["Tutte le date"] + date_disponibili, index=0)
            else:
                scelta_data = "Tutte le date"
            
            st.divider()
            
            lista_match = []
            for m in matches:
                t1 = m.get('team1', '')
                t2 = m.get('team2', '')
                data_match = m.get('date', 'Data da definire')
                
                # Se l'utente ha selezionato un giorno specifico, filtriamo
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
                        classifica_dict[sq] = {
                            'Squadra': sq, 'PG': 0, 'V': 0, 'N': 0, 'P': 0, 
                            'GF': 0, 'GS': 0, 'Pt': 0, 
                            'Over_15': 0, 'Over_25': 0, 'Over_35': 0
                        }
                
                classifica_dict[t1]['PG'] += 1; classifica_dict[t2]['PG'] += 1
                classifica_dict[t1]['GF'] += g1; classifica_dict[t1]['GS'] += g2
                classifica_dict[t2]['GF'] += g2; classifica_dict[t2]['GS'] += g1
                
                tot_match_gol = g1 + g2
                if tot_match_gol > 1.5: classifica_dict[t1]['Over_15'] += 1; classifica_dict[t2]['Over_15'] += 1
                if tot_match_gol > 2.5: classifica_dict[t1]['Over_25'] += 1; classifica_dict[t2]['Over_25'] += 1
                if tot_match_gol > 3.5: classifica_dict[t1]['Over_35'] += 1; classifica_dict[t2]['Over_35'] += 1

                if g1 > g2:
                    classifica_dict[t1]['V'] += 1; classifica_dict[t1]['Pt'] += 3; classifica_dict[t2]['P'] += 1
                elif g1 < g2:
                    classifica_dict[t2]['V'] += 1; classifica_dict[t2]['Pt'] += 3; classifica_dict[t1]['P'] += 1
                else:
                    classifica_dict[t1]['N'] += 1; classifica_dict[t1]['Pt'] += 1; classifica_dict[t2]['N'] += 1; classifica_dict[t2]['Pt'] += 1

        if ento_giocate > 0:
            media_gol = tot_gol / ento_giocate
            st.markdown("### 🌐 Panoramica Generale Lega")
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Match Analizzati", ento_giocate)
            with col2: st.metric("Gol Totali Segnati", tot_gol)
            with col3: st.metric("Media Gol / Match", f"{media_gol:.2f}")
            
            st.divider()
            
            # SEZIONE: TEST A TESTA (H2H) & STATO DI FORMA ULTIME 5 + MOTORE IA
            st.markdown("### ⚔️️ Confronto Testa a Testa (H2H) & 🤖 Pronostici IA (Peso Max su Ultime 5)")
            st.caption("Il motore calcola il pronostico dando massima priorità allo stato di forma delle ultime 5 partite correnti, integrando il rendimento globale e lo storico 20 anni.")
            
            col_h2h_1, col_h2h_2 = st.columns(2)
            lista_sqs_sorted = sorted(list(lista_squadre_tutte))
            with col_h2h_1:
                squadra_a = st.selectbox("Squadra Casa / A", lista_sqs_sorted, index=0, key="h2h_sq_a_forma")
            with col_h2h_2:
                squadra_b = st.selectbox("Squadra Ospite / B", lista_sqs_sorted, index=min(1, len(lista_sqs_sorted)-1), key="h2h_sq_b_forma")
            
            if squadra_a == squadra_b:
                st.warning("Seleziona due squadre differenti per effettuare il confronto.")
            else:
                # Calcolo Stato di Forma Ultime 5
                forma_a, punti_5_a, gf_5_a, gs_5_a = calcola_ultime_5_partite(matches_correnti, squadra_a)
                forma_b, punti_5_b, gf_5_b, gs_5_b = calcola_ultime_5_partite(matches_correnti, squadra_b)
                
                st.markdown(f"#### 🔥 Stato di Forma Recente (Ultime 5 Partite)")
                fcol1, fcol2 = st.columns(2)
                with fcol1:
                    st.markdown(f"**{squadra_a}** (Punti negli ultimi 5 match: **{punti_5_a}**) | Gol: +{gf_5_a} / -{gs_5_a}")
                    html_pillole_a = ""
                    for res in forma_a:
                        if res == "V": html_pillole_a += '<span class="form-pill-win">V</span> '
                        elif res == "N": html_pillole_a += '<span class="form-pill-draw">N</span> '
                        else: html_pillole_a += '<span class="form-pill-loss">P</span> '
                    st.markdown(html_pillole_a if html_pillole_a else "<em>Nessun dato recente</em>", unsafe_allow_html=True)
                    
                with fcol2:
                    st.markdown(f"**{squadra_b}** (Punti negli ultimi 5 match: **{punti_5_b}**) | Gol: +{gf_5_b} / -{gs_5_b}")
                    html_pillole_b = ""
                    for res in forma_b:
                        if res == "V": html_pillole_b += '<span class="form-pill-win">V</span> '
                        elif res == "N": html_pillole_b += '<span class="form-pill-draw">N</span> '
                        else: html_pillole_b += '<span class="form-pill-loss">P</span> '
                    st.markdown(html_pillole_b if html_pillole_b else "<em>Nessun dato recente</em>", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                with st.spinner("Analisi storico 20 anni e calcolo predittivo IA..."):
                    tutti_i_match_20_anni = carica_storico_h2h_20_anni()
                
                match_h2h_storico = [
                    m for m in tutti_i_match_20_anni 
                    if ('score' in m and 'ft' in m['score'] and m['score']['ft'] is not None) and (
                        (m.get('team1') == squadra_a and m.get('team2') == squadra_b) or 
                        (m.get('team1') == squadra_b and m.get('team2') == squadra_a)
                    )
                ]
                
                vittorie_a_h2h = vittorie_b_h2h = pareggi_h2h = 0
                for mh in match_h2h_storico:
                    t1, t2 = mh.get('team1'), mh.get('team2')
                    g_t1, g_t2 = mh.get('score', {}).get('ft')
                    if t1 == squadra_a:
                        if g_t1 > g_t2: vittorie_a_h2h += 1
                        elif g_t1 < g_t2: vittorie_b_h2h += 1
                        else: pareggi_h2h += 1
                    else:
                        if g_t1 > g_t2: vittorie_b_h2h += 1
                        elif g_t1 < g_t2: vittorie_a_h2h += 1
                        else: pareggi_h2h += 1

                # --- 🤖 MOTORE IA PONDERATO ---
                peso_forma_a = punti_5_a * 4.0 + (gf_5_a - gs_5_a) * 2.0
                peso_forma_b = punti_5_b * 4.0 + (gf_5_b - gs_5_b) * 2.0
                
                dati_a = classifica_dict.get(squadra_a, {'Pt': 10, 'PG': 5})
                dati_b = classifica_dict.get(squadra_b, {'Pt': 10, 'PG': 5})
                
                stagione_a = (dati_a['Pt'] / max(1, dati_a['PG'])) * 3.0
                stagione_b = (dati_b['Pt'] / max(1, dati_b['PG'])) * 3.0
                
                storico_a = vittorie_a_h2h * 1.0
                storico_b = vittorie_b_h2h * 1.0
                
                score_tot_a = peso_forma_a + stagione_a + storico_a
                score_tot_b = peso_forma_b + stagione_b + storico_b
                score_pareggio = 6.0 + (pareggi_h2h * 0.5)
                
                somma_forze = max(1.0, score_tot_a + score_tot_b + score_pareggio)
                perc_1 = int((score_tot_a / somma_forze) * 100)
                perc_x = int((score_pareggio / somma_forze) * 100)
                perc_2 = 100 - (perc_1 + perc_x)
                
                perc_1 = max(10, min(85, perc_1))
                perc_2 = max(10, min(85, perc_2))
                perc_x = 100 - (perc_1 + perc_2)

                media_gol_5 = ((gf_5_a + gf_5_b + gs_5_a + gs_5_b) / 10.0) if len(forma_a) > 0 and len(forma_b) > 0 else 2.5
                prob_over25 = min(85, max(25, int(media_gol_5 * 40)))
                prob_gol = min(80, max(30, int(media_gol_5 * 35)))

                if perc_1 >= 50:
                    consiglio_principale = f"1 (Vittoria {squadra_a})"
                    affidabilita = f"Alta ({perc_1}%)"
                    combo_consigliata = "1X + Over 1.5"
                elif perc_2 >= 50:
                    consiglio_principale = f"2 (Vittoria {squadra_b})"
                    affidabilita = f"Alta ({perc_2}%)"
                    combo_consigliata = "X2 + Over 1.5"
                elif perc_1 > perc_2:
                    consiglio_principale = "1X (Doppia Chance Casa)"
                    affidabilita = f"Media-Alta ({perc_1 + perc_x}%)"
                    combo_consigliata = "1X + Under 3.5"
                else:
                    consiglio_principale = "X2 (Doppia Chance Ospite)"
                    affidabilita = f"Media-Alta ({perc_2 + perc_x}%)"
                    combo_consigliata = "X2 + Under 3.5"

                st.markdown(f"""
                <div class="ai-box">
                    <h4>🧠 Report IA (Algoritmo Stato di Forma Ponderato)</h4>
                    <p style='color: #8b949e; font-size: 13px;'>Il modello ha calcolato le probabilità dando massima priorità alle prestazioni delle <strong>ultime 5 partite</strong>:</p>
                    <hr style='border-color: #30363d;'>
                    <p><b>📊 Stime Probabilità Esito (1X2):</b></p>
                    <ul>
                        <li><b>{squadra_a} (1):</b> {perc_1}%</li>
                        <li><b>Pareggio (X):</b> {perc_x}%</li>
                        <li><b>{squadra_b} (2):</b> {perc_2}%</li>
                    </ul>
                    <p><b>⚽ Trend Reti Recenti:</b> Over 2.5 stimato al <b>{prob_over25}%</b> | Gol / Gol stimato al <b>{prob_gol}%</b></p>
                    <hr style='border-color: #30363d;'>
                    <h4 style='color: #58a6ff;'>💡 Suggerimento Consigliato dall'IA: <code>{consiglio_principale}</code></h4>
                    <p><b>Affidabilità Statistica:</b> {affidabilita} &nbsp;|&nbsp; <b>Combo Consigliata:</b> {combo_consigliata}</p>
                </div>
                """, unsafe_allow_html=True)

                if len(match_h2h_storico) > 0:
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander("📂 Visualizza Storico Precedenti (20 Anni) per Valutazione Potenziale"):
                        dettagli_h2h = []
                        for mh in match_h2h_storico:
                            t1 = mh.get('team1')
                            t2 = mh.get('team2')
                            sc = mh.get('score', {}).get('ft')
                            dettagli_h2h.append({
                                "Stagione": mh.get('stagione_riferimento', 'N/D'), 
                                "Data": mh.get('date', 'N/D'),
                                "Match": f"{t1} vs {t2}", 
                                "Risultato": f"{sc[0]} - {sc[1]}"
                            })
                        st.dataframe(pd.DataFrame(dettagli_h2h), use_container_width=True)

        else:
            st.info("Dati statistici in fase di popolamento per la nuova giornata.")
    except Exception as e:
        st.error(f"Errore calcolo Forma & IA: {e}")

st.markdown("<br><hr><p style='text-align: center; color: #8b949e; font-size: 12px;'>b-betting Architecture — Trasparenza e Dati Reali al 100%.</p>", unsafe_allow_html=True)
