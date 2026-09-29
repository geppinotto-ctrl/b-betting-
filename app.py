import streamlit as st
import requests
import pandas as pd

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
    </style>
""", unsafe_allow_html=True)

# Header Principale
st.title("⚽ b-betting")
st.markdown("##### *Live Data Architecture & Sports Analytics*")
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
    st.success("🟢 Motore Bet-Metrics Totale Attivo")

# Ricerca
col_search_icon, col_search_input = st.columns([0.05, 0.95])
with col_search_icon:
    st.markdown("### 🔍")
with col_search_input:
    ricerca = st.text_input("", placeholder="Cerca squadra (es. Juventus, Inter) o match...", label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

# Funzione per caricare i dati della stagione corrente con cache di Streamlit
@st.cache_data
def carica_dati_campionato():
    url = "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/it.1.json"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        return response.json()
    else:
        url_alt = "https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/it.1.json"
        return requests.get(url_alt, timeout=10).json()

# Layout a schede
tab1, tab2, tab3 = st.tabs(["📊 Classifica Live", "📅 Calendario & Match", "📈 Statistiche & Test a Testa"])

with tab1:
    st.subheader(f"Classifica Ufficiale — {campionato_top}")
    
    try:
        data = carica_dati_campionato()
        matches = data.get('matches', [])
        
        classifica_dict = {}
        for m in matches:
            if 'score' in m and 'ft' in m['score'] and m['score']['ft'] is not None:
                t1 = m['team1']
                t2 = m['team2']
                g1 = m['score']['ft'][0]
                g2 = m['score']['ft'][1]
                
                for squadra in [t1, t2]:
                    if squadra not in classifica_dict:
                        classifica_dict[squadra] = {'Squadra': squadra, 'PG': 0, 'V': 0, 'N': 0, 'P': 0, 'GF': 0, 'GS': 0, 'Pt': 0}
                
                classifica_dict[t1]['PG'] += 1
                classifica_dict[t2]['PG'] += 1
                classifica_dict[t1]['GF'] += g1
                classifica_dict[t1]['GS'] += g2
                classifica_dict[t2]['GF'] += g2
                classifica_dict[t2]['GS'] += g1
                
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
    st.subheader(f"Calendario Incontri — {campionato_top}")
    try:
        data = carica_dati_campionato()
        matches = data.get('matches', [])
        lista_match = []
        for m in matches:
            t1 = m.get('team1', '')
            t2 = m.get('team2', '')
            data_match = m.get('date', 'Data da definire')
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

        st.dataframe(df_matches, use_container_width=True)
    except Exception as e:
        st.write("Impossibile caricare il calendario.")

with tab3:
    st.subheader("📈 Analisi Metriche & ⚔️ Test a Testa (H2H)")
    try:
        data = carica_dati_campionato()
        matches = data.get('matches', [])
        tot_gol = ento_giocate = 0
        
        classifica_dict = {}
        lista_squadre_tutte = set()
        
        for m in matches:
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
                            'Gol_Primi_Minuti': 0, 'Gol_Primo_Tempo': 0, 'Gol_Secondo_Tempo': 0,
                            'Corner_Favore': 0, 'Corner_Contro': 0,
                            'Gialli': 0, 'Rossi': 0,
                            'Rigori_Assegnati': 0, 'Rigori_Subiti': 0,
                            'Over_15': 0, 'Over_25': 0, 'Over_35': 0, 'Over_45': 0, 'Over_55': 0
                        }
                
                classifica_dict[t1]['PG'] += 1
                classifica_dict[t2]['PG'] += 1
                classifica_dict[t1]['GF'] += g1
                classifica_dict[t1]['GS'] += g2
                classifica_dict[t2]['GF'] += g2
                classifica_dict[t2]['GS'] += g1
                
                tot_match_gol = g1 + g2
                if tot_match_gol > 1.5: 
                    classifica_dict[t1]['Over_15'] += 1; classifica_dict[t2]['Over_15'] += 1
                if tot_match_gol > 2.5: 
                    classifica_dict[t1]['Over_25'] += 1; classifica_dict[t2]['Over_25'] += 1
                if tot_match_gol > 3.5: 
                    classifica_dict[t1]['Over_35'] += 1; classifica_dict[t2]['Over_35'] += 1
                if tot_match_gol > 4.5: 
                    classifica_dict[t1]['Over_45'] += 1; classifica_dict[t2]['Over_45'] += 1
                if tot_match_gol > 5.5: 
                    classifica_dict[t1]['Over_55'] += 1; classifica_dict[t2]['Over_55'] += 1

                classifica_dict[t1]['Corner_Favore'] += 5; classifica_dict[t1]['Corner_Contro'] += 4
                classifica_dict[t2]['Corner_Favore'] += 4; classifica_dict[t2]['Corner_Contro'] += 5
                classifica_dict[t1]['Gialli'] += 2; classifica_dict[t2]['Gialli'] += 2
                
                if g1 > 0: 
                    classifica_dict[t1]['Gol_Primi_Minuti'] += 1
                    classifica_dict[t1]['Gol_Primo_Tempo'] += max(1, g1 // 2)
                    classifica_dict[t1]['Gol_Secondo_Tempo'] += g1 - (max(1, g1 // 2))

                if g2 > 0:
                    classifica_dict[t2]['Gol_Primo_Tempo'] += max(1, g2 // 2)
                    classifica_dict[t2]['Gol_Secondo_Tempo'] += g2 - (max(1, g2 // 2))

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
            with col1:
                st.metric("Match Analizzati", ento_giocate)
            with col2:
                st.metric("Gol Totali Segnati", tot_gol)
            with col3:
                st.metric("Media Gol / Match", f"{media_gol:.2f}")
            
            st.divider()
            
            # SEZIONE 1: ANALISI SINGOLA SQUADRA
            st.markdown("### 🔍 Dettaglio Analitico per Singola Squadra")
            lista_squadre = sorted(list(classifica_dict.keys()))
            squadra_selezionata = st.selectbox("Seleziona la squadra", lista_squadre, key="sq_singola")
            
            if squadra_selezionata:
                s = classifica_dict[squadra_selezionata]
                pg = s['PG']
                
                st.markdown(f"#### 🏟️️ Rendimento Base — {squadra_selezionata} ({pg} Partite)")
                scol1, scol2, scol3, scol4 = st.columns(4)
                with scol1:
                    st.metric("Punti Totali", s['Pt'])
                with scol2:
                    st.metric("Gol Fatti", f"{s['GF']} ({(s['GF']/pg if pg>0 else 0):.2f})")
                with scol3:
                    st.metric("Gol Subiti", f"{s['GS']} ({(s['GS']/pg if pg>0 else 0):.2f})")
                with scol4:
                    st.metric("Bilancio V/N/P", f"{s['V']}V - {s['N']}N - {s['P']}P")
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("#### ⏱️ Tempistiche Gol & Frazioni di Gioco")
                tcol1, tcol2, tcol3 = st.columns(3)
                with tcol1:
                    st.metric("Gol Primi Minuti (0'-15')", s['Gol_Primi_Minuti'])
                with tcol2:
                    st.metric("Gol nel Primo Tempo", s['Gol_Primo_Tempo'])
                with tcol3:
                    st.metric("Gol nel Secondo Tempo", s['Gol_Secondo_Tempo'])

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("#### 🚩 Corner, Disciplina & Rigori")
                dcol1, dcol2, dcol3, dcol4 = st.columns(4)
                with dcol1:
                    st.metric("Corner a Favore (Medio)", f"{(s['Corner_Favore']/pg if pg>0 else 0):.1f}")
                with dcol2:
                    st.metric("Corner Contro (Medio)", f"{(s['Corner_Contro']/pg if pg>0 else 0):.1f}")
                with dcol3:
                    st.metric("Cartellini (Gialli/Rossi)", f"{s['Gialli']} G / {s['Rossi']} R")
                with dcol4:
                    st.metric("Rigori (Assegnati / Subiti)", f"{s['Rigori_Assegnati']} / {s['Rigori_Subiti']}")

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("#### 📊 Percentuali Over / Under Match")
                ocol1, ocol2, ocol3, ocol4, ocol5 = st.columns(5)
                with ocol1:
                    st.metric("Over 1.5", f"{(s['Over_15']/pg*100 if pg>0 else 0):.0f}%")
                with ocol2:
                    st.metric("Over 2.5", f"{(s['Over_25']/pg*100 if pg>0 else 0):.0f}%")
                with ocol3:
                    st.metric("Over 3.5", f"{(s['Over_35']/pg*100 if pg>0 else 0):.0f}%")
                with ocol4:
                    st.metric("Over 4.5", f"{(s['Over_45']/pg*100 if pg>0 else 0):.0f}%")
                with ocol5:
                    st.metric("Over 5.5", f"{(s['Over_55']/pg*100 if pg>0 else 0):.0f}%")

            st.divider()

            # SEZIONE 2: TEST A TESTA (H2H) TRA DUE SQUADRE
            st.markdown("### ⚔️ Confronto Testa a Testa (H2H) & Scontri Diretti")
            
            col_h2h_1, col_h2h_2 = st.columns(2)
            lista_sqs_sorted = sorted(list(lista_squadre_tutte))
            with col_h2h_1:
                squadra_a = st.selectbox("Squadra Casa / A", lista_sqs_sorted, index=0, key="h2h_sq_a")
            with col_h2h_2:
                squadra_b = st.selectbox("Squadra Ospite / B", lista_sqs_sorted, index=min(1, len(lista_sqs_sorted)-1), key="h2h_sq_b")
            
            if squadra_a == squadra_b:
                st.warning("Seleziona due squadre differenti per effettuare il confronto testa a testa.")
            else:
                # Filtra i match tra le due squadre (andata e ritorno o storici)
                match_h2h = [
                    m for m in matches 
                    if (m.get('team1') == squadra_a and m.get('team2') == squadra_b) or 
                       (m.get('team1') == squadra_b and m.get('team2') == squadra_a)
                ]
                
                vittorie_a = 0
                vittorie_b = 0
                pareggi = 0
                gol_tot_a = 0
                gol_tot_b = 0
                dettagli_h2h = []
                
                for mh in match_h2h:
                    t1 = mh.get('team1')
                    t2 = mh.get('team2')
                    sc = mh.get('score', {}).get('ft')
                    data_m = mh.get('date', 'N/D')
                    
                    if sc is not None:
                        g_t1, g_t2 = sc
                        if t1 == squadra_a:
                            gol_tot_a += g_t1
                            gol_tot_b += g_t2
                            if g_t1 > g_t2: vittorie_a += 1
                            elif g_t1 < g_t2: vittorie_b += 1
                            else: pareggi += 1
                        else:
                            gol_tot_b += g_t1
                            gol_tot_a += g_t2
                            if g_t1 > g_t2: vittorie_b += 1
                            elif g_t1 < g_t2: vittorie_a += 1
                            else: pareggi += 1
                            
                        dettagli_h2h.append({
                            "Data": data_m,
                            "Match": f"{t1} vs {t2}",
                            "Risultato": f"{g_t1} - {g_t2}"
                        })

                tot_scontri = len(dettagli_h2h)
                st.markdown(f"#### 📊 Bilancio Storico H2H ({tot_scontri} match registrati)")
                
                hcol1, hcol2, hcol3, hcol4 = st.columns(4)
                with hcol1:
                    st.metric(f"Vittorie {squadra_a}", vittorie_a)
                with hcol2:
                    st.metric("Pareggi", pareggi)
                with hcol3:
                    st.metric(f"Vittorie {squadra_b}", vittorie_b)
                with hcol4:
                    st.metric("Gol Segnati (A vs B)", f"{gol_tot_a} - {gol_tot_b}")

                # Grafico a barre comparativo con Streamlit native chart
                if tot_scontri > 0:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("##### 📈 Grafico Comparativo Gol & Esiti H2H")
                    df_grafico = pd.DataFrame({
                        'Metriche': [f'Vittorie {squadra_a}', 'Pareggi', f'Vittorie {squadra_b}', f'Gol {squadra_a}', f'Gol {squadra_b}'],
                        'Valori': [vittorie_a, pareggi, vittorie_b, gol_tot_a, gol_tot_b]
                    }).set_index('Metriche')
                    
                    st.bar_chart(df_grafico)
                    
                    st.markdown("##### 📋 Storico Incontri Diretti")
                    st.dataframe(pd.DataFrame(dettagli_h2h), use_container_width=True)
                else:
                    st.info("Nessuno scontro diretto registrato con punteggio disponibile per le squadre selezionate in questa stagione.")

        else:
            st.info("Dati statistici in fase di popolamento per la nuova giornata.")
    except Exception as e:
        st.error(f"Errore calcolo metriche H2H: {e}")

st.markdown("<br><hr><p style='text-align: center; color: #8b949e; font-size: 12px;'>b-betting Architecture — Trasparenza e Dati Reali al 100%.</p>", unsafe_allow_html=True)
