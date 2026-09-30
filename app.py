# --- SEZIONE HOME / BIGLIETTO DA VISITA ---
st.markdown(
    """
    <div style='background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; padding: 30px; border-radius: 16px; margin-bottom: 25px;'>
        <h1 style='color: #58a6ff; margin-bottom: 5px;'>⚽ b-betting Hub</h1>
        <p style='color: #8b949e; font-size: 16px; margin-top: 0;'>Piattaforma avanzata di Live Data Architecture, Statistiche Sportive e Previsioni Algoritmiche.</p>
        <hr style='border-color: #30363d; margin: 20px 0;'>
        <div style='display: flex; gap: 15px; flex-wrap: wrap;'>
            <span style='background: #21262d; border: 1px solid #30363d; padding: 6px 14px; border-radius: 20px; font-size: 13px; color: #c9d1d9;'>⚡ Engine: <b>Attivo</b></span>
            <span style='background: #21262d; border: 1px solid #30363d; padding: 6px 14px; border-radius: 20px; font-size: 13px; color: #c9d1d9;'>📊 Modello IA: <b>v4.2 Pro</b></span>
            <span style='background: #21262d; border: 1px solid #30363d; padding: 6px 14px; border-radius: 20px; font-size: 13px; color: #c9d1d9;'>🕒 Sync: <b>Real-time</b></span>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

# Metriche Rapide in Primo Piano
col_h1, col_h2, col_h3, col_h4 = st.columns(4)
with col_h1:
  st.metric(
      label="Tornei Principali", value="6 Nazionali", delta="Aggiornati"
  )
with col_h2:
  st.metric(label="Algoritmo", value="PPG & BTTS", delta="Alta Precisione")
with col_h3:
  st.metric(label="Stato Sistema", value="Ottimizzato", delta="100%")
with col_h4:
  st.metric(label="Stagione Corrente", value=stagione_selezionata)

st.markdown("<br>", unsafe_allow_html=True)

# Sezione Vetrina / Quick Access
st.markdown("### 🚀 Accesso Rapido alle Funzioni Chiave")
col_qa1, col_qa2, col_qa3 = st.columns(3)

with col_qa1:
  st.markdown(
      """
        <div class='ai-box' style='text-align: center;'>
            <h3>📅 Palinsesto</h3>
            <p style='color: #8b949e; font-size: 13px;'>Esplora tutte le partite in programma e i calendari completi dei tornei europei.</p>
        </div>
        """,
      unsafe_allow_html=True,
  )

with col_qa2:
  st.markdown(
      """
        <div class='ai-box' style='text-align: center;'>
            <h3>📊 Classifiche</h3>
            <p style='color: #8b949e; font-size: 13px;'>Monitora in tempo reale la graduatoria, i gol fatti/subiti e la differenza reti.</p>
        </div>
        """,
      unsafe_allow_html=True,
  )

with col_qa3:
  st.markdown(
      """
        <div class='ai-box' style='text-align: center;'>
            <h3>📈 Analisi & IA</h3>
            <p style='color: #8b949e; font-size: 13px;'>Confronti diretti testa a testa, stato di forma e pronostici generati dall'intelligenza artificiale.</p>
        </div>
        """,
      unsafe_allow_html=True,
  )

st.divider()
