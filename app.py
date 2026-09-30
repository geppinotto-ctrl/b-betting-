# --- PERSONALIZZAZIONE COLORI TAB (Verde, Giallo, Rosso) ---
st.markdown(
    """
    <style>
    /* Seleziona il primo tab (Palinsesto) e lo colora di verde */
    .stTabs [data-baseweb="tab-list"] button:nth-child(1) {
        background-color: rgba(35, 134, 54, 0.15);
        border: 1px solid #238636;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(1):hover {
        background-color: rgba(35, 134, 54, 0.3);
    }

    /* Seleziona il secondo tab (Classifica) e lo colora di giallo/ambra */
    .stTabs [data-baseweb="tab-list"] button:nth-child(2) {
        background-color: rgba(210, 153, 34, 0.15);
        border: 1px solid #d29922;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(2):hover {
        background-color: rgba(210, 153, 34, 0.3);
    }

    /* Seleziona il terzo tab (Analisi Match & Statistiche) e lo colora di rosso */
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

# Definizione dei tab con le icone dedicate
tab1, tab2, tab3 = st.tabs(
    ["📅 Palinsesto", "📊 Classifica", "📈 Analisi Match & Statistiche"]
)
