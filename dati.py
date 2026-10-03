from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import difflib
import io
import pandas as pd
import re
import requests
import streamlit as st
from config import TZ_ITALIA, mapping_file_torneo


ESPN_CL_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard"
)


def _converti_evento_cl(evento):
    comp = (evento.get("competitions") or [{}])[0]
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
    if not home or not away:
        return None
    nome1 = (home.get("team") or {}).get("displayName")
    nome2 = (away.get("team") or {}).get("displayName")
    if not nome1 or not nome2:
        return None

    iso = str(evento.get("date", ""))
    data, ora = iso[:10], ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ_ITALIA)
        data, ora = dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    except Exception:
        pass

    stato = ((evento.get("status") or comp.get("status") or {}).get("type")) or {}
    finita = stato.get("completed") is True or stato.get("state") == "post"

    ft = ht = None
    if finita:
        try:
            ft = [int(float(home.get("score"))), int(float(away.get("score")))]
        except Exception:
            ft = None
        try:
            lh = home.get("linescores") or []
            la = away.get("linescores") or []
            if len(lh) >= 2 and len(la) >= 2:
                ht = [int(float(lh[0].get("value"))), int(float(la[0].get("value")))]
        except Exception:
            ht = None

    return {
        "id": evento.get("id"),
        "date": data,
        "time": ora,
        "team1": nome1,
        "team2": nome2,
        "score": {"ft": ft, "ht": ht},
    }


@st.cache_data(ttl=1800, show_spinner=False)
def carica_dati_campionato(nome_campionato, stagione):
    if nome_campionato == "UEFA Champions League":
        return carica_dati_champions(stagione)

    possibili_nomi = mapping_file_torneo.get(
        nome_campionato,
        ["it.1.json"]
    )

    anno_inizio = stagione.split("-")[0]

    percorsi_da_tentare = []

    for nome_file in possibili_nomi:
        percorsi_da_tentare.append(f"{stagione}/{nome_file}")
        percorsi_da_tentare.append(nome_file)
        percorsi_da_tentare.append(f"{anno_inizio}/{nome_file}")

    for p in percorsi_da_tentare:
        url = (
            "https://raw.githubusercontent.com/"
            f"openfootball/football.json/master/{p}"
        )

        try:
            r = requests.get(url, timeout=4)

            if r.status_code == 200:
                res = r.json()

                if isinstance(res, list):
                    return {"matches": res}

                if isinstance(res, dict):
                    if "matches" in res:
                        return res

                    for v in res.values():
                        if isinstance(v, list):
                            return {"matches": v}

        except Exception:
            pass

    return {"matches": []}


def _scarica_anno_cl(anno):
    """ESPN accetta dates=ANNO (gli intervalli danno HTTP 400)."""
    for params in ({"dates": str(anno), "limit": 1000}, {"dates": str(anno)}):
        try:
            r = requests.get(ESPN_CL_URL, params=params, timeout=15)
            if r.status_code == 200:
                return r.json().get("events", [])
        except Exception:
            pass
    return None


@st.cache_data(ttl=900, show_spinner=False)
def carica_dati_champions(stagione):
    anno = int(stagione.split("-")[0])
    inizio, fine = f"{anno}-09-01", f"{anno + 1}-06-30"  # esclude i preliminari
    visti, matches = set(), []
    with ThreadPoolExecutor(max_workers=2) as ex:
        for eventi in ex.map(_scarica_anno_cl, [anno, anno + 1]):
            for ev in eventi or []:
                m = _converti_evento_cl(ev)
                if not m or m["id"] in visti:
                    continue
                if not (inizio <= m["date"] <= fine):
                    continue
                visti.add(m["id"])
                matches.append(m)
    matches.sort(key=lambda m: (m["date"], m["time"]))
    return {"matches": matches}


CODICI_FD = {
    "Italia - Serie A": "I1",
    "Inghilterra - Premier League": "E0",
    "Spagna - La Liga": "SP1",
    "Germania - Bundesliga": "D1",
    "Francia - Ligue 1": "F1",
}


@st.cache_data(ttl=3600)
def carica_stats_extra(campionato, stagione):
    codice = CODICI_FD.get(campionato)
    if not codice:
        return None
    anno_a = stagione.split("-")[0][2:]
    anno_b = stagione.split("-")[1]
    url = f"https://www.football-data.co.uk/mmz4281/{anno_a}{anno_b}/{codice}.csv"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return None
        df = pd.read_csv(
            io.BytesIO(r.content), encoding="latin-1", on_bad_lines="skip"
        )
        df = df.dropna(subset=["HomeTeam", "AwayTeam"])
        return df if not df.empty else None
    except Exception:
        return None


def normalizza_nome(nome):
    n = re.sub(r"[^a-z ]", " ", str(nome).lower())
    togli = {"fc", "ac", "as", "ss", "ssc", "us", "acf", "afc", "cfc", "bc",
             "calcio", "hellas", "club", "de", "di"}
    return " ".join(p for p in n.split() if p not in togli)


def trova_nome_fd(nome, nomi_fd):
    n = normalizza_nome(nome)
    if not n:
        return None
    mappa = {normalizza_nome(x): x for x in nomi_fd}
    if n in mappa:
        return mappa[n]
    for k, v in mappa.items():
        if k and (n.startswith(k) or k.startswith(n)):
            return v
    simili = difflib.get_close_matches(n, list(mappa.keys()), n=1, cutoff=0.8)
    return mappa[simili[0]] if simili else None


def calcola_stats_extra(df, nome):
    nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
    nome_fd = trova_nome_fd(nome, nomi)
    if not nome_fd:
        return None
    casa = df[df["HomeTeam"] == nome_fd]
    fuori = df[df["AwayTeam"] == nome_fd]
    tot = len(casa) + len(fuori)
    if tot == 0:
        return None

    def media(col_casa, col_fuori):
        if col_casa not in df.columns or col_fuori not in df.columns:
            return None
        v = (
            pd.to_numeric(casa[col_casa], errors="coerce").dropna().tolist()
            + pd.to_numeric(fuori[col_fuori], errors="coerce").dropna().tolist()
        )
        return round(sum(v) / len(v), 2) if v else None

    return {
        "nome_fd": nome_fd,
        "tot": tot,
        "angoli_f": media("HC", "AC"),
        "angoli_s": media("AC", "HC"),
        "tiri_f": media("HS", "AS"),
        "tiri_s": media("AS", "HS"),
        "porta_f": media("HST", "AST"),
        "porta_s": media("AST", "HST"),
        "falli": media("HF", "AF"),
        "gialli": media("HY", "AY"),
        "rossi": media("HR", "AR"),
    }
