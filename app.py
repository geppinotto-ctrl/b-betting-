import streamlit as st
import requests

# Mappatura dei tornei sui file openfootball
mapping_file_torneo = {
    "Spagna - La Liga": "es/1.json",
    "Italia - Serie A": "it/1.json",
    "Inghilterra - Premier League": "en/1.json",
    "Germania - Bundesliga": "de/1.json",
    "Francia - Ligue 1": "fr/1.json"
}

@st.cache_data
def carica_dati_campionato(nome_campionato, stagione):
    nome_file = mapping_file_torneo.get(nome_campionato, "it/1.json")
    percorsi = [
        f"{stagione}/{nome_file}",
        nome_file
    ]
    for p in percorsi:
        url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{p}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                res_json = response.json()
                if isinstance(res_json, list):
                    return {"matches": res_json}
                return res_json
        except:
            continue
    return {"matches": []}

# Interfaccia Streamlit di base
st.title("b-betting Architecture")
st.write("Seleziona il torneo desiderato e la partita specifica per estrarre in tempo reale le probabili scelte tecniche.")

# Esempio di utilizzo dei filtri nell'app
stagione = st.selectbox("Seleziona Stagione:", ["2023-24", "2024-25", "2025-26"])
torneo = st.selectbox("Seleziona Torneo per le Formazioni:", list(mapping_file_torneo.keys()))

dati = carica_dati_campionato(torneo, stagione)
matches = dati.get("matches", [])

st.write(f"Partite caricate con successo: {len(matches)}")
