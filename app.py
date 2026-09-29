@st.cache_data
def carica_dati_campionato(nome_campionato, stagione):
    nome_file = mapping_file_torneo.get(nome_campionato, "it.1.json")
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
                # Se il JSON è una lista diretta, lo normalizziamo in un dizionario
                if isinstance(res_json, list):
                    return {"matches": res_json}
                return res_json
        except:
            continue
    return {"matches": []}
