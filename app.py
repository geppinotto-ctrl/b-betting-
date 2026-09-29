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
    
    # TASTO AGGIORNA FEED DATI REALE E FORZATO
    if st.button("🔄 Aggiorna Feed Dati", use_container_width=True, type="primary"):
        with st.spinner("Svuotamento cache e download dati freschi in corso..."):
            st.cache_data.clear()  # Pulisce la memoria cache di Streamlit
            import time
            time.sleep(0.6)        # Piccolo delay visivo per dare percezione dell'azione
        st.toast("⚡ Feed dati aggiornato con successo!", icon="✅")
        st.rerun()                 # Ricarica immediatamente l'intera app per applicare i dati freschi
