from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components
import pandas as pd
import requests
import streamlit as st

try:
    from zoneinfo import ZoneInfo

    TZ_ITALIA = ZoneInfo("Europe/Rome")
except Exception:
    TZ_ITALIA = timezone(timedelta(hours=2))

st.set_page_config(
    page_title="b-betting — Live Dashboard", page_icon="⚽", layout="wide"
)
# 🔐 Chiave API quote prepartita
ODDS_API_KEY = st.secrets.get("ODDS_API_KEY", "")

# --- Atmosfera Sonora ---
import base64
import os

@st.cache_data
def carica_audio_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            audio_bytes = f.read()
        return base64.b64encode(audio_bytes).decode()
    return None

st.sidebar.markdown("### 🎵 Atmosfera Sonora")
silenziatore = st.sidebar.checkbox("Silenzia sottofondo", value=False)

audio_path = "calculated_grace (1).mp3"

if not silenziatore:
    audio_base64 = carica_audio_base64(audio_path)
    if audio_base64:
        audio_html = f"""
            <audio autoplay loop volume="0.02">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                Il tuo browser non supporta l'elemento audio.
            </audio>
        """
        # st.markdown(audio_html, unsafe_allow_html=True)
        components.html(audio_html + "<script>var a=document.querySelector('audio');a.volume=0.05;a.play().catch(function(){try{window.parent.document.addEventListener('click',function(){a.play();},{once:true});}catch(e){}});</script>", height=0)
else:
        st.sidebar.caption("⚠️ File audio non trovato.")
        
st.markdown("""
    <style>
    /* Pannello con vetro leggerissimo per far risaltare il portiere */
    div[data-testid="stVerticalBlock"] div[style*="border"] {
        background: rgba(10, 10, 15, 0.15) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    </style>
""", unsafe_allow_html=True)




@st.cache_data(ttl=300, show_spinner=False)
def testa_odds_api():
    if not ODDS_API_KEY:
        return {
            "ok": False,
            "errore": "Chiave ODDS_API_KEY non trovata nei Secrets."
        }

    url = "https://odss-api.com/api/v1/bookmakers"

    try:
        r = requests.get(
            url,
            headers={"x-api-key": ODDS_API_KEY},
            timeout=8
        )

        if r.status_code != 200:
            return {
                "ok": False,
                "errore": f"HTTP {r.status_code}"
            }

        data = r.json()

        if isinstance(data, dict):
            return {
                "ok": True,
                "dati": data
            }

        return {
            "ok": False,
            "errore": "Risposta API non riconosciuta."
        }

    except Exception as e:
        return {
            "ok": False,
            "errore": str(e)
        }


# 🧪 Test temporaneo collegamento quote
test_odds = testa_odds_api()

if test_odds["ok"]:
    st.success("🟢 Collegamento quote prepartita: OK")
else:
    st.error(f"🔴 Collegamento quote prepartita: {test_odds['errore']}")



        

st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    .stTextInput > div > div > input { background-color: #161b22; color: #c9d1d9; border-radius: 8px; border: 1px solid #30363d; }
    .league-section { color: #8b949e; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; }
    .ai-box { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; margin-top: 15px; margin-bottom: 15px; color: #c9d1d9; font-size: 14px; }
    .smart-tip-box { background-color: #111b27; border: 1px solid #1f6feb; padding: 20px; border-radius: 12px; margin-top: 20px; margin-bottom: 20px; color: #c9d1d9; }
    .timer-box { background-color: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 15px; color: #58a6ff; font-weight: bold; font-size: 13px; }

    .badge-v { background-color: #238636; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }
    .badge-n { background-color: #d29922; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }
    .badge-p { background-color: #da3633; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }
     .stTabs [data-baseweb="tab-list"] button {
    color: white !important;
}
    .stTabs [data-baseweb="tab-list"] button:nth-child(1) {
        background-color: rgba(35, 134, 54, 0.15);
        border: 1px solid #238636;
        color: white !important;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(1):hover {
        background-color: rgba(35, 134, 54, 0.3);
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(2) {
        background-color: rgba(210, 153, 34, 0.15);
        border: 1px solid #d29922;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(2):hover {
        background-color: rgba(210, 153, 34, 0.3);
    }
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

import base64
import io
from pathlib import Path

# Nomi dei file immagine caricati nel repository (cambiali se sono diversi)
FILE_TEXTURE = "17909154919832446827610680716341.jpg"
FILE_PORTIERE = "1000023096.jpg"
# Quanto si vede il portiere: 0.05 = quasi invisibile, 0.20 = ben visibile
OPACITA_PORTIERE = 0.30


@st.cache_data(show_spinner=False)
def immagine_base64(nome_file, larghezza_max=900, qualita=70):
    percorso = Path(__file__).parent / nome_file
    if not percorso.exists():
        return None
    try:
        from PIL import Image

        img = Image.open(percorso).convert("RGB")
        if img.width > larghezza_max:
            altezza = int(img.height * larghezza_max / img.width)
            img = img.resize((larghezza_max, altezza))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=qualita, optimize=True)
        dati = buf.getvalue()
    except Exception:
        dati = percorso.read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(dati).decode()


def applica_sfondo(opacita=0.20):
    texture = immagine_base64(FILE_TEXTURE)
    portiere = immagine_base64(FILE_PORTIERE)
    css = "<style>"
    css += ".stApp { background-color: #05070a;"
    if texture:
        css += (
            f" background-image: url('{texture}');"
            " background-size: cover; background-position: center;"
            " background-repeat: no-repeat;"
        )
    css += " }"
    css += (
        ".main, section.main, [data-testid='stMain'], "
        "[data-testid='stAppViewContainer'], [data-testid='stHeader'] "
        "{ background: transparent !important; }"
    )
    if portiere:
        css += (
            ".stApp::before { content: ''; position: fixed; top: 0; left: 0;"
            " right: 0; bottom: 0; z-index: 0; pointer-events: none;"
            f" opacity: {opacita};"
            f" background-image: url('{portiere}');"
            " background-size: 100% auto; background-position: center;"
            " background-repeat: no-repeat;"
            " -webkit-mask-image: linear-gradient(to bottom, transparent,"
            " black 25%, black 75%, transparent);"
            " mask-image: linear-gradient(to bottom, transparent,"
            " black 25%, black 75%, transparent); }"
            " @media (min-aspect-ratio: 1/1) { .stApp::before {"
            " background-size: cover; background-position: 62% center;"
            " -webkit-mask-image: none; mask-image: none; } }"
        )
        css += "[data-testid='stAppViewContainer'] { position: relative; z-index: 1; }"
    css += "[data-testid='stSidebar'] { background: rgba(8, 10, 14, 0.88) !important; }"
    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)


applica_sfondo(OPACITA_PORTIERE)
def trova_immagini():
    cartella = Path(__file__).parent
    texture = FILE_TEXTURE if (cartella / FILE_TEXTURE).is_file() else None
    portiere = FILE_PORTIERE if (cartella / FILE_PORTIERE).is_file() else None
    for p in sorted(cartella.iterdir()):
        if texture and portiere:
            break
        if not p.is_file() or p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        if p.name in (texture, portiere):
            continue
        try:
            from PIL import Image

            with Image.open(p) as im:
                larga = im.width > im.height
        except Exception:
            continue
        if larga and not portiere:
            portiere = p.name
        elif not larga and not texture:
            texture = p.name
    return texture, portiere


_trama, _portiere = trova_immagini()
if _trama:
    FILE_TEXTURE = _trama
if _portiere:
    FILE_PORTIERE = _portiere
applica_sfondo(OPACITA_PORTIERE)

MOSTRA_DIAGNOSI = False
if MOSTRA_DIAGNOSI:
    st.caption(
        "🖼️ Sfondo - trama: "
        + (_trama or "NON trovata")
        + " | portiere: "
        + (_portiere or "NON trovato")
    )
if "pagina" not in st.session_state:
    st.session_state.pagina = "home"

campionati_disponibili = [
    "Italia - Serie A",
    "Inghilterra - Premier League",
    "Spagna - La Liga",
    "Germania - Bundesliga",
    "Francia - Ligue 1",
    "UEFA Champions League",
]

mapping_file_torneo = {
    "Italia - Serie A": ["it.1.json", "italy/it.1.json"],
    "Inghilterra - Premier League": ["en.1.json", "england/en.1.json"],
    "Spagna - La Liga": ["es.1.json", "spain/es.1.json"],
    "Germania - Bundesliga": ["de.1.json", "germany/de.1.json"],
    "Francia - Ligue 1": ["fr.1.json", "france/fr.1.json"],
    "UEFA Champions League": ["uefa.cl.json"],
}

now = datetime.now(TZ_ITALIA)

with st.sidebar:
    st.header("Selettore Tornei")

    giorni_it = [
        "Lunedì",
        "Martedì",
        "Mercoledì",
        "Giovedì",
        "Venerdì",
        "Sabato",
        "Domenica",
    ]
    components.html(
        """
        <div style="background:#161b22;border:1px solid #30363d;padding:10px;border-radius:8px;text-align:center;color:#58a6ff;font-family:sans-serif;font-weight:bold;font-size:13px;">
            🕒 Orologio Live (Italia)<br>
            <span id="orologio" style="font-size:16px;"></span>
        </div>
        <script>
        function aggiorna() {
            const opt = {timeZone: 'Europe/Rome', weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false};
            document.getElementById('orologio').textContent = new Intl.DateTimeFormat('it-IT', opt).format(new Date());
        }
        aggiorna();
        setInterval(aggiorna, 1000);
        </script>
        """,
        height=80,
    )

    stagione_selezionata = st.selectbox(
        "Stagione", ["2026-27", "2025-26", "2024-25"]
    )
    campionato_top = st.selectbox("Torneo", campionati_disponibili)

    st.divider()
    if st.button("🏠 Torna alla Home", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()

    if st.button("🔄 Aggiorna Dati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
@st.cache_data
def carica_dati_champions(stagione):
    anno = stagione.split("-")[0]

    url = (
        "https://site.api.espn.com/apis/site/v2/"
        "sports/soccer/uefa.champions/scoreboard"
    )

    try:
        r = requests.get(
            url,
            params={"dates": anno},
            timeout=8
        )

        if r.status_code != 200:
            return {"matches": []}

        data = r.json()
        matches = []

        for evento in data.get("events", []):
            competizione = evento.get("competitions", [{}])[0]

            competitors = competizione.get("competitors", [])

            if len(competitors) != 2:
                continue

            home = next(
                (c for c in competitors if c.get("homeAway") == "home"),
                None
            )
            away = next(
                (c for c in competitors if c.get("homeAway") == "away"),
                None
            )

            if not home or not away:
                continue

            home_name = home.get("team", {}).get("displayName")
            away_name = away.get("team", {}).get("displayName")

            if not home_name or not away_name:
                continue

            score_home = home.get("score")
            score_away = away.get("score")

            ft = None

            if score_home is not None and score_away is not None:
                try:
                    ft = [int(score_home), int(score_away)]
                except Exception:
                    ft = None

            matches.append({
                "date": evento.get("date", ""),
                "team1": home_name,
                "team2": away_name,
                "score": {
                    "ft": ft
                }
            })

        return {"matches": matches}

    except Exception:
        return {"matches": []}
@st.cache_data
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


from concurrent.futures import ThreadPoolExecutor

ESPN_CL_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard"
)


def _intervalli_stagione(anno):
    """12 intervalli mensili da luglio a giugno, formato YYYYMMDD-YYYYMMDD."""
    out = []
    for k in range(12):
        m = 7 + k
        y = anno + (m - 1) // 12
        m = (m - 1) % 12 + 1
        inizio = datetime(y, m, 1)
        fine = datetime(y + (1 if m == 12 else 0), m % 12 + 1, 1) - timedelta(days=1)
        out.append(f"{inizio:%Y%m%d}-{fine:%Y%m%d}")
    return out


def _scarica_intervallo_cl(intervallo):
    try:
        r = requests.get(
            ESPN_CL_URL,
            params={"dates": intervallo, "limit": 300},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        return r.json().get("events", [])
    except Exception:
        return None


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


@st.cache_data(ttl=900, show_spinner=False)
def carica_dati_champions(stagione):
    anno = int(stagione.split("-")[0])
    visti, matches = set(), []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for eventi in ex.map(_scarica_intervallo_cl, _intervalli_stagione(anno)):
            for ev in eventi or []:
                m = _converti_evento_cl(ev)
                if not m or m["id"] in visti:
                    continue
                visti.add(m["id"])
                matches.append(m)
    matches.sort(key=lambda m: (m["date"], m["time"]))
    return {"matches": matches}


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
from concurrent.futures import ThreadPoolExecutor


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
# --- DIAGNOSTICA TEMPORANEA CHAMPIONS (si può togliere dopo) ---
if False and st.session_state.get("pagina") == "dashboard" and campionato_top == "UEFA Champions League":
    with st.expander("🔧 Diagnostica Champions"):
        for _d in ("20260901-20260930", "2026"):
            try:
                _r = requests.get(
                    ESPN_CL_URL, params={"dates": _d, "limit": 300}, timeout=10
                )
                _n = len(_r.json().get("events", [])) if _r.status_code == 200 else "-"
                st.write(f"dates={_d} → HTTP {_r.status_code}, eventi: {_n}")
                if _r.status_code != 200:
                    st.code(_r.text[:300])
            except Exception as _e:
                st.write(f"dates={_d} → errore: {_e}")
        _dati = carica_dati_campionato(campionato_top, stagione_selezionata)
        st.write("Partite caricate dall'app:", len(_dati.get("matches", [])))
def calcola_statistiche_squadra(matches, squadra):
    match_squadra = [
        m
        for m in matches
        if isinstance(m, dict)
        and isinstance(m.get("score"), dict)
        and m["score"].get("ft") is not None
        and (m.get("team1") == squadra or m.get("team2") == squadra)
    ]

    tot = len(match_squadra)
    if tot == 0:
        return None

    gf, gs, pt = 0, 0, 0
    clean_sheets = 0
    over_2_5 = 0
    btts = 0
    forma = []

    for m in match_squadra:
        is_casa = m.get("team1") == squadra
        ft = m["score"]["ft"]
        g1, g2 = ft[0], ft[1]
        m_gf = g1 if is_casa else g2
        m_gs = g2 if is_casa else g1

        gf += m_gf
        gs += m_gs

        if m_gs == 0:
            clean_sheets += 1
        if (g1 + g2) > 2.5:
            over_2_5 += 1
        if g1 > 0 and g2 > 0:
            btts += 1

        if m_gf > m_gs:
            forma.append("V")
            pt += 3
        elif m_gf == m_gs:
            forma.append("N")
            pt += 1
        else:
            forma.append("P")

    return {
        "tot": tot,
        "forma": forma,
        "ppg": round(pt / tot, 2),
        "gf_avg": round(gf / tot, 2),
        "gs_avg": round(gs / tot, 2),
        "clean_sheets_pct": round((clean_sheets / tot) * 100, 1),
        "over_2_5_pct": round((over_2_5 / tot) * 100, 1),
        "btts_pct": round((btts / tot) * 100, 1),
    }


def calcola_pronostico_ia(stats1, stats2):
    if not stats1 or not stats2:
        return 33.3, 33.4, 33.3

    forza_1 = stats1["ppg"] * 1.5 + (stats1["gf_avg"] - stats1["gs_avg"]) * 0.5
    forza_2 = stats2["ppg"] * 1.5 + (stats2["gf_avg"] - stats2["gs_avg"]) * 0.5
    forza_1 += 0.2  # vantaggio campo

    diff = forza_1 - forza_2

    base_1 = 40 + (diff * 18)
    base_2 = 40 - (diff * 18)
    base_x = 26 - abs(diff * 5)

    p1 = max(10.0, min(80.0, base_1))
    p2 = max(10.0, min(80.0, base_2))
    px = max(10.0, min(50.0, base_x))

    tot_p = p1 + px + p2
    return (
        round((p1 / tot_p) * 100, 1),
        round((px / tot_p) * 100, 1),
        round((p2 / tot_p) * 100, 1),
    )


def genera_analisi_ia_match(t1, t2, p1, px, p2):
    favorevole = t1 if p1 > p2 else (t2 if p2 > p1 else "Equilibrio")
    righe = [
        f"🤖 <b>Report e Pronostico IA — {t1} vs {t2}</b><br><br>",
        f"• <b>Predizione Esito Finale (1X2):</b> {p1}% per la vittoria di {t1} (1), "
        f"{px}% per il pareggio (X), {p2}% per il successo di {t2} (2).<br>",
        f"• <b>Tendenza:</b> vantaggio potenziale per <b>{favorevole}</b> "
        "in base ai punti a partita (PPG) e alla solidità difensiva.<br>",
        "• <b>Consiglio:</b> valutare coperture o mercati combinati "
        "(es. 1X o Goal) se il pareggio supera il 25%.",
    ]
    return "".join(righe)


def mostra_metriche_squadra(titolo, stats):
    st.markdown(titolo, unsafe_allow_html=True)
    if stats:
        st.metric("Punti a Partita (PPG)", stats["ppg"])
        st.metric("Media Gol Fatti", stats["gf_avg"])
        st.metric("Media Gol Subiti", stats["gs_avg"])
        st.metric("Over 2.5 %", f"{stats['over_2_5_pct']}%")
        st.metric("Clean Sheet %", f"{stats['clean_sheets_pct']}%")
        st.metric("BTTS %", f"{stats['btts_pct']}%")
    else:
        st.info("Dati insufficienti per questa squadra.")
def trova_scontri_diretti(campionato, t1, t2, max_scontri=5):
    stagioni = ["2026-27", "2025-26", "2024-25"]
    trovati = []
    for stag in stagioni:
        dati = carica_dati_campionato(campionato, stag)
        for m in dati.get("matches", []):
            if not isinstance(m, dict):
                continue
            s = m.get("score")
            if not isinstance(s, dict) or not s.get("ft"):
                continue
            a, b = m.get("team1"), m.get("team2")
            if {a, b} == {t1, t2}:
                trovati.append(
                    (str(m.get("date", "")), a, b, s["ft"][0], s["ft"][1])
                )
    trovati.sort(reverse=True)
    return trovati[:max_scontri]


def mostra_scontri_diretti(campionato, t1, t2):
    st.markdown("#### 🤝 Ultimi scontri diretti")
    scontri = trova_scontri_diretti(campionato, t1, t2)
    if not scontri:
        st.info("Nessuno scontro diretto trovato nelle ultime stagioni.")
        return

    v1, v2, pa = 0, 0, 0
    righe = []
    for data, casa, osp, g1, g2 in scontri:
        if g1 == g2:
            pa += 1
        elif (g1 > g2 and casa == t1) or (g2 > g1 and osp == t1):
            v1 += 1
        else:
            v2 += 1
        righe.append({"Data": data, "Partita": f"{casa} {g1}-{g2} {osp}"})

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Vittorie {t1}", v1)
    c2.metric("Pareggi", pa)
    c3.metric(f"Vittorie {t2}", v2)
    st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)
def mostra_grafico_forma(dati, n=10):
    st.markdown(f"#### 📈 Andamento punti (ultime {n} partite)")
    valori = {"V": 3, "N": 1, "P": 0}
    serie = {}
    for nome, stats in dati.items():
        if stats and stats["forma"]:
            totale = 0
            cumulati = []
            for r in stats["forma"][-n:]:
                totale += valori[r]
                cumulati.append(totale)
            serie[nome] = cumulati

    if not serie:
        st.info("Dati insufficienti per il grafico.")
        return

    df = pd.DataFrame({k: pd.Series(v) for k, v in serie.items()})
    df.index = range(1, len(df) + 1)
    df.index.name = "Partita"
    st.line_chart(df)
def _hash_nome(nome):
    import zlib

    return zlib.crc32(str(nome).encode("utf-8"))


def iniziali_squadra(nome):
    ignora = {"FC", "AC", "AS", "SS", "US", "CF", "SC", "RC", "SV", "AFC",
              "CD", "UD", "SD", "VFB", "VFL", "DE", "DI"}
    parole = [
        p for p in str(nome).replace(".", " ").split()
        if p.upper() not in ignora and not any(c.isdigit() for c in p)
    ]
    if not parole:
        return str(nome)[:3].upper()
    if len(parole) == 1:
        return parole[0][:3].upper()
    return (parole[0][0] + parole[1][0]).upper()


def badge_squadra(nome):
    tinta = _hash_nome(nome) % 360
    return (
        f"<span style='background:hsl({tinta}, 65%, 42%);color:white;"
        "padding:3px 7px;border-radius:12px;font-size:11px;font-weight:bold;"
        "display:inline-block;min-width:34px;text-align:center;margin-right:6px;'>"
        f"{iniziali_squadra(nome)}</span>"
    )


def simbolo_squadra(nome):
    cerchi = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫"]
    return cerchi[_hash_nome(nome) % len(cerchi)]
def calcola_stats_tempi(matches, squadra):
    gf1 = gs1 = gf2 = gs2 = 0
    segna_1t = 0
    tot = 0
    for m in matches:
        if not isinstance(m, dict):
            continue
        s = m.get("score")
        if not isinstance(s, dict):
            continue
        ft, ht = s.get("ft"), s.get("ht")
        if not ft or not ht:
            continue
        if squadra not in (m.get("team1"), m.get("team2")):
            continue
        casa = m.get("team1") == squadra
        f_fatti, f_subiti = (ft[0], ft[1]) if casa else (ft[1], ft[0])
        h_fatti, h_subiti = (ht[0], ht[1]) if casa else (ht[1], ht[0])
        gf1 += h_fatti
        gs1 += h_subiti
        gf2 += f_fatti - h_fatti
        gs2 += f_subiti - h_subiti
        if h_fatti > 0:
            segna_1t += 1
        tot += 1

    if tot == 0:
        return None
    return {
        "tot": tot,
        "gf1": round(gf1 / tot, 2),
        "gs1": round(gs1 / tot, 2),
        "gf2": round(gf2 / tot, 2),
        "gs2": round(gs2 / tot, 2),
        "segna_1t_pct": round(segna_1t / tot * 100, 1),
    }


def mostra_stats_tempi(titolo, stats):
    st.markdown(titolo)
    if not stats:
        st.info("Dati del primo tempo non disponibili.")
        return
    df = pd.DataFrame(
        {
            "Tempo": ["1° tempo", "2° tempo"],
            "Fatti (media)": [stats["gf1"], stats["gf2"]],
            "Subiti (media)": [stats["gs1"], stats["gs2"]],
        }
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.metric("Segna nel 1° tempo", f"{stats['segna_1t_pct']}%")
    st.caption(f"Calcolato su {stats['tot']} partite con dato del primo tempo.")
    
import difflib
import io
import re

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


def mostra_stats_extra(titolo, nome):
    st.markdown(titolo)
    df = carica_stats_extra(campionato_top, stagione_selezionata)
    if df is None:
        st.info(
            "Statistiche aggiuntive disponibili solo per la Serie A "
            "e se la stagione ha i dati."
        )
        return
    stats = calcola_stats_extra(df, nome)
    if not stats:
        st.warning(f"Squadra '{nome}' non riconosciuta nei dati aggiuntivi.")
        return

    def v(x):
        return "-" if x is None else str(x)

    tabella = pd.DataFrame(
        [
            {"Statistica": "Calci d'angolo", "Fatti": v(stats["angoli_f"]), "Subiti": v(stats["angoli_s"])},
            {"Statistica": "Tiri", "Fatti": v(stats["tiri_f"]), "Subiti": v(stats["tiri_s"])},
            {"Statistica": "Tiri in porta", "Fatti": v(stats["porta_f"]), "Subiti": v(stats["porta_s"])},
            {"Statistica": "Falli commessi", "Fatti": v(stats["falli"]), "Subiti": "-"},
            {"Statistica": "Cartellini gialli", "Fatti": v(stats["gialli"]), "Subiti": "-"},
            {"Statistica": "Cartellini rossi", "Fatti": v(stats["rossi"]), "Subiti": "-"},
        ]
    )
    st.dataframe(tabella, use_container_width=True, hide_index=True)
    st.caption(
        f"Media su {stats['tot']} partite. Fonte: football-data.co.uk "
        f"(nome nei dati: {stats['nome_fd']})."
        )
import math


def _poisson(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def calcola_forze(matches, d=0.95, prior=4):
    gio = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        s = m.get("score")
        ft = s.get("ft") if isinstance(s, dict) else None
        if ft and m.get("team1") and m.get("team2"):
            gio.append((m["team1"], m["team2"], ft[0], ft[1]))
    if len(gio) < 10:
        return None
    n = len(gio)
    mc = sum(g[2] for g in gio) / n
    mf = sum(g[3] for g in gio) / n
    media_sq = (mc + mf) / 2
    storico = {}
    for t1, t2, a, b in gio:
        storico.setdefault(t1, []).append((a, b))
        storico.setdefault(t2, []).append((b, a))
    forze = {}
    for t, lista in storico.items():
        k = len(lista)
        pesi = [d ** (k - 1 - i) for i in range(k)]
        sp = sum(pesi)
        gf = sum(p * x[0] for p, x in zip(pesi, lista))
        gs = sum(p * x[1] for p, x in zip(pesi, lista))
        forze[t] = {
            "att": (gf + prior * media_sq) / (sp + prior) / media_sq,
            "dif": (gs + prior * media_sq) / (sp + prior) / media_sq,
        }
    return {"mc": mc, "mf": mf, "forze": forze}


def forze_tiri(df):
    if df is None or "HST" not in df.columns or "AST" not in df.columns:
        return None
    d = df.dropna(subset=["HomeTeam", "AwayTeam"]).copy()
    d["HST"] = pd.to_numeric(d["HST"], errors="coerce")
    d["AST"] = pd.to_numeric(d["AST"], errors="coerce")
    d = d.dropna(subset=["HST", "AST"])
    if len(d) < 10:
        return None
    media = (d["HST"].mean() + d["AST"].mean()) / 2
    out = {}
    for s in set(d["HomeTeam"]) | set(d["AwayTeam"]):
        c = d[d["HomeTeam"] == s]
        f = d[d["AwayTeam"] == s]
        fatti = list(c["HST"]) + list(f["AST"])
        subiti = list(c["AST"]) + list(f["HST"])
        k = len(fatti)
        out[s] = {
            "att": (sum(fatti) + 4 * media) / (k + 4) / media,
            "dif": (sum(subiti) + 4 * media) / (k + 4) / media,
        }
    return out


def gol_attesi(modello, t1, t2, tiri=None, nome_fd1=None, nome_fd2=None, peso_tiri=0.3):
    f = modello["forze"]
    l1 = modello["mc"] * f[t1]["att"] * f[t2]["dif"]
    l2 = modello["mf"] * f[t2]["att"] * f[t1]["dif"]
    usato = False
    if tiri and nome_fd1 in tiri and nome_fd2 in tiri:
        s1 = modello["mc"] * tiri[nome_fd1]["att"] * tiri[nome_fd2]["dif"]
        s2 = modello["mf"] * tiri[nome_fd2]["att"] * tiri[nome_fd1]["dif"]
        l1 = (1 - peso_tiri) * l1 + peso_tiri * s1
        l2 = (1 - peso_tiri) * l2 + peso_tiri * s2
        usato = True
    return l1, l2, usato


def esiti_poisson(l1, l2, max_gol=8):
    p1 = [_poisson(i, l1) for i in range(max_gol + 1)]
    p2 = [_poisson(i, l2) for i in range(max_gol + 1)]
    tot = sum(p1) * sum(p2)
    vit1 = pareggio = vit2 = over25 = btts = 0.0
    risultati = []
    for i in range(max_gol + 1):
        for j in range(max_gol + 1):
            p = p1[i] * p2[j] / tot
            risultati.append((f"{i}-{j}", p))
            if i > j:
                vit1 += p
            elif i == j:
                pareggio += p
            else:
                vit2 += p
            if i + j > 2:
                over25 += p
            if i > 0 and j > 0:
                btts += p
    risultati.sort(key=lambda x: x[1], reverse=True)
    return {
        "1": vit1 * 100,
        "X": pareggio * 100,
        "2": vit2 * 100,
        "over25": over25 * 100,
        "under25": (1 - over25) * 100,
        "goal": btts * 100,
        "nogoal": (1 - btts) * 100,
        "top": risultati[:5],
    }
def sintesi_dna_pronostico(t1, t2, dettagli):
    if not dettagli:
        return ""

    l1 = dettagli.get("l1", 0)
    l2 = dettagli.get("l2", 0)
    e = dettagli.get("e", {})

    p1 = e.get("1", 0)
    px = e.get("X", 0)
    p2 = e.get("2", 0)

    att1 = dettagli.get("att1", 1)
    dif1 = dettagli.get("dif1", 1)
    att2 = dettagli.get("att2", 1)
    dif2 = dettagli.get("dif2", 1)

    if p1 > p2:
        esito = f"{t1} emerge come esito principale"
    elif p2 > p1:
        esito = f"{t2} emerge come esito principale"
    else:
        esito = "il modello vede un equilibrio tra le due squadre"

    if l1 > l2:
        gol = f"{t1} ha una proiezione offensiva superiore ({l1:.2f} vs {l2:.2f} gol attesi)"
    elif l2 > l1:
        gol = f"{t2} ha una proiezione offensiva superiore ({l2:.2f} vs {l1:.2f} gol attesi)"
    else:
        gol = "le due squadre hanno la stessa proiezione di gol"

    if att1 > att2:
        attacco = f"{t1} presenta l'indice offensivo più alto"
    elif att2 > att1:
        attacco = f"{t2} presenta l'indice offensivo più alto"
    else:
        attacco = "gli indici offensivi sono equivalenti"

    return f"{esito}. {gol}; {attacco}. Probabilità 1X2: {p1:.1f}% / {px:.1f}% / {p2:.1f}%."
def mostra_dna_pronostico(t1, t2, dettagli):
    if not dettagli:
        st.info("🧬 DNA del pronostico non disponibile.")
        return

    l1 = dettagli.get("l1")
    l2 = dettagli.get("l2")
    e = dettagli.get("e", {})
    usato_tiri = dettagli.get("tiri", False)

    mc = dettagli.get("mc")
    mf = dettagli.get("mf")
    att1 = dettagli.get("att1")
    dif1 = dettagli.get("dif1")
    att2 = dettagli.get("att2")
    dif2 = dettagli.get("dif2")

    def lettura_attacco(v):
        if v is None:
            return ""
        if v > 1:
            return "sopra il riferimento"
        if v < 1:
            return "sotto il riferimento"
        return "in linea con il riferimento"

    def lettura_gol_concessi(v):
        if v is None:
            return ""
        if v > 1:
            return "concede più gol del riferimento"
        if v < 1:
            return "concede meno gol del riferimento"
        return "in linea con il riferimento"

    st.markdown("### 🧬 DNA DEL PRONOSTICO")

    st.markdown("#### ⚽ Gol attesi")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(t1, f"{l1:.2f}")

    with col2:
        st.metric(t2, f"{l2:.2f}")

    st.markdown("#### 🧬 Forze del modello")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{t1}**")
        st.write(f"⚔️ Attacco: **{att1:.3f}×**")
        st.caption(f"↳ {lettura_attacco(att1)}")

        st.write(f"🛡️ Gol concessi: **{dif1:.3f}×**")
        st.caption(f"↳ {lettura_gol_concessi(dif1)}")

    with col2:
        st.markdown(f"**{t2}**")
        st.write(f"⚔️ Attacco: **{att2:.3f}×**")
        st.caption(f"↳ {lettura_attacco(att2)}")

        st.write(f"🛡️ Gol concessi: **{dif2:.3f}×**")
        st.caption(f"↳ {lettura_gol_concessi(dif2)}")

    st.markdown("#### 🏟️ Media gol del campionato")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Casa", f"{mc:.2f}")

    with col2:
        st.metric("Trasferta", f"{mf:.2f}")

    st.markdown("#### 📊 Esiti elaborati")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("1 — Casa", f"{e.get('1', 0):.1f}%")

    with col2:
        st.metric("X — Pareggio", f"{e.get('X', 0):.1f}%")

    with col3:
        st.metric("2 — Trasferta", f"{e.get('2', 0):.1f}%")

    if usato_tiri:
        st.success("🎯 Modulo tiri integrato — peso 30%")
    else:
        st.info("🎯 Modulo tiri non disponibile — modello basato sui gol")

    st.markdown("#### 🧠 Lettura del modello")

    st.markdown(
        f"""
        <div style="
            padding: 14px 18px;
            border-left: 3px solid rgba(255,255,255,0.35);
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            margin-top: 8px;
            margin-bottom: 12px;
        ">
            {sintesi_dna_pronostico(t1, t2, dettagli)}
        </div>
        """,
        unsafe_allow_html=True
    )

    top = e.get("top", [])

    if top:
        st.markdown("#### 🎯 Risultati esatti più probabili")

        dati_top = []

        for risultato, probabilita in top:
            dati_top.append({
                "Risultato": risultato,
                "Probabilità": f"{probabilita * 100:.2f}%"
            })

        st.dataframe(
            pd.DataFrame(dati_top),
            hide_index=True,
            use_container_width=True
                                     )
def mostra_pronostico_v2(matches, t1, t2):
    st.markdown("### 🧠 Pronostico v2 (modello di Poisson)")
    modello = calcola_forze(matches)
    if not modello or t1 not in modello["forze"] or t2 not in modello["forze"]:
        st.info("Servono più partite giocate per stimare il modello.")
        return

    df = carica_stats_extra(campionato_top, stagione_selezionata)
    tiri = forze_tiri(df)
    nome1 = nome2 = None
    if tiri is not None and df is not None:
        nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
        nome1 = trova_nome_fd(t1, nomi)
        nome2 = trova_nome_fd(t2, nomi)

    l1, l2, usato_tiri = gol_attesi(modello, t1, t2, tiri, nome1, nome2)
    e = esiti_poisson(l1, l2)

    def riga(nome, p):
        quota = f"{100 / p:.2f}" if p > 0.1 else "-"
        return {"Mercato": nome, "Probabilità": f"{p:.1f}%", "Quota equa": quota}

    tabella = pd.DataFrame(
        [
            riga(f"1 - {t1}", e["1"]),
            riga("X - Pareggio", e["X"]),
            riga(f"2 - {t2}", e["2"]),
            riga("Over 2.5", e["over25"]),
            riga("Under 2.5", e["under25"]),
            riga("Goal (segnano entrambe)", e["goal"]),
            riga("NoGoal", e["nogoal"]),
        ]
    )
    st.dataframe(tabella, use_container_width=True, hide_index=True)

    st.markdown("**Risultati esatti più probabili**")
    top = pd.DataFrame(
        [{"Risultato": r, "Probabilità": f"{p * 100:.1f}%"} for r, p in e["top"]]
    )
    st.dataframe(top, use_container_width=True, hide_index=True)

    base = "con tiri in porta (peso 30%)" if usato_tiri else "solo sui gol"
    st.caption(
        f"Gol attesi: {t1} {l1:.2f} - {t2} {l2:.2f}. Calcolo {base}, "
        "con più peso alle partite recenti. La quota equa è 100 diviso la "
        "probabilità, cioè senza il margine del bookmaker. È una stima, "
        "non una garanzia."
    )
def mostra_riepilogo(matches, tab):
    with tab:
        st.subheader("🎯 Riepilogo Pronostici")
        modello = calcola_forze(matches)
        if not modello:
            st.info("Servono più partite giocate per stimare il modello.")
            return

        oggi = now.strftime("%Y-%m-%d")
        c1, c2 = st.columns(2)
        with c1:
            giorni = st.selectbox(
                "Partite in arrivo",
                ["Prossimi 7 giorni", "Prossimi 14 giorni", "Prossimi 30 giorni", "Tutte"],
                index=1,
                key=f"riep_giorni_{campionato_top}_{stagione_selezionata}",
            )
        with c2:
            ordine = st.selectbox(
                "Ordina per",
                ["Probabilità più alta", "Data", "Over 2.5", "Goal"],
                key=f"riep_ordine_{campionato_top}_{stagione_selezionata}",
            )

        limite = None
        if giorni != "Tutte":
            n = int(giorni.split()[1])
            limite = (now + timedelta(days=n)).strftime("%Y-%m-%d")

        prossime = [
            m
            for m in matches
            if isinstance(m, dict)
            and m.get("team1")
            and m.get("team2")
            and not (isinstance(m.get("score"), dict) and m["score"].get("ft"))
            and str(m.get("date", "")) >= oggi
            and (limite is None or str(m.get("date", "")) <= limite)
        ]
        if not prossime:
            st.info("Nessuna partita in arrivo nel periodo scelto.")
            return

        df = carica_stats_extra(campionato_top, stagione_selezionata)
        tiri = forze_tiri(df)
        nomi = set()
        if tiri is not None and df is not None:
            nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
        cache_nomi = {}

        def nome_fd(t):
            if t not in cache_nomi:
                cache_nomi[t] = trova_nome_fd(t, nomi) if nomi else None
            return cache_nomi[t]

        righe = []
        for m in prossime:
            t1, t2 = m["team1"], m["team2"]
            if t1 not in modello["forze"] or t2 not in modello["forze"]:
                continue
            l1, l2, _ = gol_attesi(modello, t1, t2, tiri, nome_fd(t1), nome_fd(t2))
            e = esiti_poisson(l1, l2)
            esiti = {"1": e["1"], "X": e["X"], "2": e["2"]}
            migliore = max(esiti, key=esiti.get)
            p = esiti[migliore]
            righe.append(
                {
                    "Data": str(m.get("date", "")),
                    "Partita": f"{t1} - {t2}",
                    "Esito": migliore,
                    "Prob. esito": round(p, 1),
                    "Quota equa": round(100 / p, 2),
                    "1": round(e["1"], 1),
                    "X": round(e["X"], 1),
                    "2": round(e["2"], 1),
                    "Over 2.5": round(e["over25"], 1),
                    "Goal": round(e["goal"], 1),
                }
            )

        if not righe:
            st.info("Squadre non presenti nel modello.")
            return

        chiavi = {
            "Probabilità più alta": ("Prob. esito", True),
            "Data": ("Data", False),
            "Over 2.5": ("Over 2.5", True),
            "Goal": ("Goal", True),
        }
        colonna, decrescente = chiavi[ordine]
        righe.sort(key=lambda r: r[colonna], reverse=decrescente)

        st.dataframe(
            pd.DataFrame(righe),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Prob. esito": st.column_config.ProgressColumn(
                    "Prob. %", format="%.1f", min_value=0, max_value=100
                ),
            },
        )
        st.caption(
            f"{len(righe)} partite. Tocca l'intestazione di una colonna per "
            "riordinare. Probabilità in %, stime del modello di Poisson: "
            "non sono garanzie."
        )
def probabilita_v2(matches, t1, t2, stats1, stats2):
    modello = calcola_forze(matches)
    if modello and t1 in modello["forze"] and t2 in modello["forze"]:
        df = carica_stats_extra(campionato_top, stagione_selezionata)
        tiri = forze_tiri(df)
        nome1 = nome2 = None
        if tiri is not None and df is not None:
            nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
            nome1 = trova_nome_fd(t1, nomi)
            nome2 = trova_nome_fd(t2, nomi)
        l1, l2, usato_tiri = gol_attesi(modello, t1, t2, tiri, nome1, nome2)
        e = esiti_poisson(l1, l2)
        dettagli = {
    "l1": l1,
    "l2": l2,
    "e": e,
    "tiri": usato_tiri,
    "mc": modello["mc"],
    "mf": modello["mf"],
    "att1": modello["forze"][t1]["att"],
    "dif1": modello["forze"][t1]["dif"],
    "att2": modello["forze"][t2]["att"],
    "dif2": modello["forze"][t2]["dif"],
        }
        return round(e["1"], 1), round(e["X"], 1), round(e["2"], 1), dettagli
    p1, px, p2 = calcola_pronostico_ia(stats1, stats2)
    return p1, px, p2, None


def genera_analisi_v2(t1, t2, p1, px, p2, dettagli):
    if not dettagli:
        return genera_analisi_ia_match(t1, t2, p1, px, p2)
    e = dettagli["e"]
    esiti = {
        f"vittoria di {t1} (1)": p1,
        "pareggio (X)": px,
        f"vittoria di {t2} (2)": p2,
    }
    migliore = max(esiti, key=esiti.get)
    pm = esiti[migliore]
    if pm < 40:
        tono = "partita molto equilibrata, nessun esito nettamente favorito"
    elif pm < 55:
        tono = "leggero vantaggio per questo esito"
    else:
        tono = "vantaggio netto per questo esito"
    risultato, rp = e["top"][0]
    base = "gol e tiri in porta" if dettagli["tiri"] else "gol"
    totale = dettagli["l1"] + dettagli["l2"]
    righe = [
        f"🤖 <b>Report IA v2 — {t1} vs {t2}</b><br><br>",
        f"• <b>Esito più probabile:</b> {migliore} al <b>{pm}%</b> ({tono}).<br>",
        f"• <b>Gol attesi:</b> {t1} {dettagli['l1']:.2f} - {t2} {dettagli['l2']:.2f} (totale {totale:.2f}).<br>",
        f"• <b>Mercati gol:</b> Over 2.5 al {e['over25']:.1f}%, Goal al {e['goal']:.1f}%.<br>",
        f"• <b>Risultato esatto più probabile:</b> {risultato} ({rp * 100:.1f}%).<br>",
        f"• <b>Base di calcolo:</b> {base}, con più peso alle partite recenti.",
    ]
    return "".join(righe)
def _giocate_ordinate(matches):
    gio = []
    for i, m in enumerate(matches):
        if not isinstance(m, dict):
            continue
        s = m.get("score")
        ft = s.get("ft") if isinstance(s, dict) else None
        if ft and m.get("team1") and m.get("team2"):
            gio.append((str(m.get("date", "")), i, m))
    gio.sort(key=lambda x: (x[0], x[1]))
    return [g[2] for g in gio]


@st.cache_data(ttl=3600, show_spinner=False)
def esegui_backtest(_matches, campionato, stagione, d, rodaggio):
    giocate = _giocate_ordinate(_matches)
    risultati = []
    c1 = cx = c2 = c_over = c_goal = 0
    for m in giocate[:rodaggio]:
        a, b = m["score"]["ft"][0], m["score"]["ft"][1]
        c1 += a > b
        cx += a == b
        c2 += a < b
        c_over += (a + b) > 2
        c_goal += (a > 0 and b > 0)
    for i in range(rodaggio, len(giocate)):
        m = giocate[i]
        a, b = m["score"]["ft"][0], m["score"]["ft"][1]
        modello = calcola_forze(giocate[:i], d=d)
        t1, t2 = m["team1"], m["team2"]
        if modello and t1 in modello["forze"] and t2 in modello["forze"]:
            l1, l2, _ = gol_attesi(modello, t1, t2)
            e = esiti_poisson(l1, l2)
            n = i
            risultati.append(
                {
                    "p": (e["1"] / 100, e["X"] / 100, e["2"] / 100),
                    "reale": 0 if a > b else (1 if a == b else 2),
                    "base": (c1 / n, cx / n, c2 / n),
                    "p_over": e["over25"] / 100,
                    "over": 1 if (a + b) > 2 else 0,
                    "base_over": c_over / n,
                    "p_goal": e["goal"] / 100,
                    "goal": 1 if (a > 0 and b > 0) else 0,
                    "base_goal": c_goal / n,
                }
            )
        c1 += a > b
        cx += a == b
        c2 += a < b
        c_over += (a + b) > 2
        c_goal += (a > 0 and b > 0)
    return risultati


def riassumi_backtest(ris):
    n = len(ris)
    if n < 10:
        return None
    acc = acc_base = brier = brier_base = 0.0
    acc_over = br_over = br_over_base = 0.0
    acc_goal = br_goal = br_goal_base = 0.0
    fasce = {"sotto 40%": [], "40-50%": [], "50-60%": [], "60% o più": []}
    for r in ris:
        p, base, reale = r["p"], r["base"], r["reale"]
        pred = max(range(3), key=lambda k: p[k])
        hit = 1 if pred == reale else 0
        acc += hit
        acc_base += 1 if max(range(3), key=lambda k: base[k]) == reale else 0
        brier += sum((p[k] - (1 if k == reale else 0)) ** 2 for k in range(3))
        brier_base += sum(
            (base[k] - (1 if k == reale else 0)) ** 2 for k in range(3)
        )
        acc_over += 1 if (r["p_over"] > 0.5) == (r["over"] == 1) else 0
        br_over += (r["p_over"] - r["over"]) ** 2
        br_over_base += (r["base_over"] - r["over"]) ** 2
        acc_goal += 1 if (r["p_goal"] > 0.5) == (r["goal"] == 1) else 0
        br_goal += (r["p_goal"] - r["goal"]) ** 2
        br_goal_base += (r["base_goal"] - r["goal"]) ** 2
        top = max(p)
        if top < 0.40:
            chiave = "sotto 40%"
        elif top < 0.50:
            chiave = "40-50%"
        elif top < 0.60:
            chiave = "50-60%"
        else:
            chiave = "60% o più"
        fasce[chiave].append((top, hit))
    righe_fasce = []
    for nome, lista in fasce.items():
        if lista:
            righe_fasce.append(
                {
                    "Fascia di probabilità": nome,
                    "Partite": len(lista),
                    "Prob. media": f"{sum(x[0] for x in lista) / len(lista) * 100:.1f}%",
                    "Azzeccate": f"{sum(x[1] for x in lista) / len(lista) * 100:.1f}%",
                }
            )
    return {
        "n": n,
        "acc": acc / n * 100,
        "acc_base": acc_base / n * 100,
        "brier": brier / n,
        "brier_base": brier_base / n,
        "acc_over": acc_over / n * 100,
        "br_over": br_over / n,
        "br_over_base": br_over_base / n,
        "acc_goal": acc_goal / n * 100,
        "br_goal": br_goal / n,
        "br_goal_base": br_goal_base / n,
        "fasce": righe_fasce,
    }


def mostra_backtest(matches, tab):
    with tab:
        st.subheader("🧪 Backtest del modello")
        st.caption(
            "Il modello rifà le previsioni sulle partite già giocate, usando "
            "solo i dati precedenti a ciascuna partita, e le confronta con "
            "il risultato vero. Usa solo i gol: i tiri in porta sono medie "
            "di stagione e falserebbero la prova."
        )
        giocate = _giocate_ordinate(matches)
        if len(giocate) < 40:
            st.info(
                "Servono almeno 40 partite giocate. Prova con la stagione 2025-26."
            )
            return

        c1, c2 = st.columns(2)
        with c1:
            rodaggio = st.selectbox(
                "Partite di rodaggio",
                [30, 50, 100],
                index=1,
                key=f"bt_rodaggio_{campionato_top}_{stagione_selezionata}",
            )
        with c2:
            d_scelto = st.selectbox(
                "Peso forma recente",
                [1.00, 0.98, 0.95, 0.90],
                index=2,
                format_func=lambda x: "1.00 (nessun peso)" if x == 1.0 else f"{x:.2f}",
                key=f"bt_peso_{campionato_top}_{stagione_selezionata}",
            )
        if len(giocate) < rodaggio + 20:
            st.info("Poche partite dopo il rodaggio: scegli meno rodaggio o un'altra stagione.")
            return

        confronto = []
        dettaglio = None
        with st.spinner("Calcolo in corso..."):
            for d in [1.00, 0.98, 0.95, 0.90]:
                ris = esegui_backtest(
                    matches, campionato_top, stagione_selezionata, d, rodaggio
                )
                s = riassumi_backtest(ris)
                if not s:
                    continue
                confronto.append(
                    {
                        "Peso forma": "1.00 (nessun peso)" if d == 1.0 else f"{d:.2f}",
                        "Partite testate": s["n"],
                        "Esiti azzeccati": f"{s['acc']:.1f}%",
                        "Errore Brier": round(s["brier"], 3),
                    }
                )
                if d == d_scelto:
                    dettaglio = s
        if not dettaglio:
            st.info("Dati insufficienti per questo torneo.")
            return

        confronto.append(
            {
                "Peso forma": "Riferimento (frequenze di lega)",
                "Partite testate": dettaglio["n"],
                "Esiti azzeccati": f"{dettaglio['acc_base']:.1f}%",
                "Errore Brier": round(dettaglio["brier_base"], 3),
            }
        )
        st.markdown("**Confronto tra impostazioni**")
        st.dataframe(pd.DataFrame(confronto), use_container_width=True, hide_index=True)

        s = dettaglio
        st.markdown(f"**Dettaglio con peso {d_scelto:.2f}** ({s['n']} partite testate)")
        m1, m2 = st.columns(2)
        m1.metric(
            "Esiti 1X2 azzeccati",
            f"{s['acc']:.1f}%",
            delta=f"{s['acc'] - s['acc_base']:+.1f} punti vs riferimento",
        )
        m2.metric(
            "Errore Brier 1X2",
            f"{s['brier']:.3f}",
            delta=f"{s['brier'] - s['brier_base']:+.3f} vs riferimento",
            delta_color="inverse",
        )
        m3, m4 = st.columns(2)
        m3.metric(
            "Over 2.5 azzeccato",
            f"{s['acc_over']:.1f}%",
            delta=f"Brier {s['br_over'] - s['br_over_base']:+.3f}",
            delta_color="inverse",
        )
        m4.metric(
            "Goal azzeccato",
            f"{s['acc_goal']:.1f}%",
            delta=f"Brier {s['br_goal'] - s['br_goal_base']:+.3f}",
            delta_color="inverse",
        )

        st.markdown("**Calibrazione: se dice 60%, succede 6 volte su 10?**")
        st.dataframe(pd.DataFrame(s["fasce"]), use_container_width=True, hide_index=True)
        st.caption(
            "Brier: più basso è meglio, tirare a caso (un terzo per esito) dà "
            "0.667. Il riferimento usa solo le frequenze storiche della lega. "
            "Se il modello non batte il riferimento, non aggiunge informazione. "
            "Con poche centinaia di partite, differenze di uno o due punti "
            "possono essere solo fortuna."
            )

def migliore_giocata(e, t1, t2, doppia_chance=False):
    opzioni = [
        (f"1 - {t1}", e["1"]),
        (f"2 - {t2}", e["2"]),
        ("Over 2.5", e["over25"]),
        ("Under 2.5", e["under25"]),
        ("Goal", e["goal"]),
        ("NoGoal", e["nogoal"]),
    ]
    if doppia_chance:
        opzioni.append(("1X", e["1"] + e["X"]))
        opzioni.append(("X2", e["X"] + e["2"]))
    return max(opzioni, key=lambda x: x[1])


def stelle_difficolta(p):
    if p >= 60:
        return "⭐ Medio"
    if p >= 50:
        return "⭐⭐ Difficile"
    return "⭐⭐⭐ Molto difficile"


def stelle_multipla(p):
    if p >= 40:
        return "⭐ Medio"
    if p >= 20:
        return "⭐⭐ Difficile"
    return "⭐⭐⭐ Molto difficile"


@st.cache_data(ttl=1800, show_spinner=False)
def raccogli_consigli(stagione, giorni, doppia_chance):
    oggi = now.strftime("%Y-%m-%d")
    limite = (now + timedelta(days=giorni)).strftime("%Y-%m-%d")
    consigli = []
    for camp in campionati_disponibili:
        dati = carica_dati_campionato(camp, stagione)
        matches = dati.get("matches", [])
        st.caption(f"🏟️ Partite caricate: {len(matches)}")
        modello = calcola_forze(matches)
        if not modello:
            continue
        df = carica_stats_extra(camp, stagione)
        tiri = forze_tiri(df)
        nomi = set()
        if tiri is not None and df is not None:
            nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
        cache_nomi = {}

        def nome_fd(t):
            if t not in cache_nomi:
                cache_nomi[t] = trova_nome_fd(t, nomi) if nomi else None
            return cache_nomi[t]

        for m in matches:
            if not isinstance(m, dict):
                continue
            t1, t2 = m.get("team1"), m.get("team2")
            if not t1 or not t2:
                continue
            sc = m.get("score")
            if isinstance(sc, dict) and sc.get("ft"):
                continue
            data = str(m.get("date", ""))
            if data < oggi or data > limite:
                continue
            if t1 not in modello["forze"] or t2 not in modello["forze"]:
                continue
            l1, l2, _ = gol_attesi(modello, t1, t2, tiri, nome_fd(t1), nome_fd(t2))
            e = esiti_poisson(l1, l2)
            giocata, p = migliore_giocata(e, t1, t2, doppia_chance)
            consigli.append(
                {
                    "campionato": camp,
                    "data": data,
                    "partita": f"{t1} - {t2}",
                    "giocata": giocata,
                    "p": p,
                }
            )
    consigli.sort(key=lambda c: c["p"], reverse=True)
    return consigli


def mostra_ai_advice(tab):
    with tab:
        st.subheader("💡 AI Advice")
        st.caption(
            "Le partite con le previsioni più solide secondo il modello. "
            "Non confronta le quote dei bookmaker, quindi non può dire se "
            "una giocata ha valore: misura solo quanto il modello è sicuro. "
            "Nessuna giocata è garantita. Gioca responsabilmente, solo se "
            "maggiorenne e solo somme che puoi permetterti di perdere."
        )
        c1, c2 = st.columns(2)
        with c1:
            finestra = st.selectbox(
                "Partite in arrivo",
                ["Prossimi 3 giorni", "Prossimi 7 giorni", "Prossimi 14 giorni"],
                index=1,
                key="advice_finestra",
            )
        with c2:
            doppia = st.checkbox(
                "Includi doppia chance (1X, X2)", value=False, key="advice_doppia"
            )

        giorni = int(finestra.split()[1])
        with st.spinner("Analisi di tutti i campionati..."):
            consigli = raccogli_consigli(stagione_selezionata, giorni, doppia)
        if not consigli:
            st.info(
                "Nessuna partita trovata nel periodo. Prova una finestra più "
                "ampia o un'altra stagione."
            )
            return

        top = consigli[:10]
        st.markdown("**Top 10 giocate**")
        righe = [
            {
                "Difficoltà": stelle_difficolta(c["p"]),
                "Partita": c["partita"],
                "Giocata": c["giocata"],
                "Prob. %": round(c["p"], 1),
                "Quota equa": round(100 / c["p"], 2),
                "Data": c["data"],
                "Campionato": c["campionato"],
            }
            for c in top
        ]
        st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)

        st.markdown("**Multiple**")
        schemi = [("Doppia", 2), ("Tripla", 3), ("Quintupla", 5)]
        for nome, k in schemi:
            gambe = top[:k]
            if len(gambe) < k:
                continue
            prob = 1.0
            for g in gambe:
                prob *= g["p"] / 100
            testo = f"**{nome}** - {stelle_multipla(prob * 100)}  \n"
            testo += (
                f"Probabilità combinata **{prob * 100:.1f}%**, "
                f"quota equa **{1 / prob:.2f}**  \n"
            )
            for g in gambe:
                testo += f"• {g['partita']}: {g['giocata']} ({g['p']:.1f}%)  \n"
            st.markdown(testo)

        st.caption(
            "La probabilità di una multipla è il prodotto di quelle delle "
            "singole giocate, quindi scende in fretta. La quota equa non "
            "include il margine del bookmaker: le quote reali sono più basse. "
            "Le stelle indicano la difficoltà: più sono, meno è probabile."
        )
        coperti = sorted({c["campionato"] for c in consigli})
        st.caption("Campionati con dati: " + ", ".join(coperti) + ".")
import itertools
import json
import uuid

STATI_SCHEDINA = ["In attesa", "Vinta", "Persa"]


def quota_totale(quote):
    totale = 1.0
    for q in quote:
        totale *= q
    return totale


def calcola_multipla(quote, puntata, bonus_pct=0.0, quota_min=1.25,
                     eventi_min=5, base_netta=True):
    qt = quota_totale(quote)
    lorda = puntata * qt
    validi = sum(1 for q in quote if q >= quota_min)
    attivo = bonus_pct > 0 and validi >= eventi_min
    bonus = 0.0
    if attivo:
        base = (lorda - puntata) if base_netta else lorda
        bonus = base * bonus_pct / 100
    return {
        "quota_tot": qt,
        "lorda": lorda,
        "bonus": bonus,
        "totale": lorda + bonus,
        "validi": validi,
        "attivo": attivo,
    }


def calcola_sistema(quote, k, puntata_comb, vinte=None):
    n = len(quote)
    maschere = []
    prodotti = []
    for combo in itertools.combinations(range(n), k):
        m = 0
        p = 1.0
        for i in combo:
            m |= 1 << i
            p *= quote[i]
        maschere.append(m)
        prodotti.append(p)
    pieno = (1 << n) - 1

    def ritorno(vincenti):
        return puntata_comb * sum(
            p for m, p in zip(maschere, prodotti) if (m & vincenti) == m
        )

    puntata_tot = puntata_comb * len(maschere)
    if vinte is None:
        vinte = list(range(n))
    maschera_sim = 0
    for i in vinte:
        maschera_sim |= 1 << i

    tabella = []
    for errori in range(0, n - k + 1):
        valori = []
        for persi in itertools.combinations(range(n), errori):
            m_persi = 0
            for i in persi:
                m_persi |= 1 << i
            valori.append(ritorno(pieno & ~m_persi))
        tabella.append(
            {
                "Partite sbagliate": errori,
                "Ritorno minimo": round(min(valori), 2),
                "Ritorno massimo": round(max(valori), 2),
                "Netto minimo": round(min(valori) - puntata_tot, 2),
                "Netto massimo": round(max(valori) - puntata_tot, 2),
            }
        )
    return {
        "combinazioni": len(maschere),
        "puntata_tot": puntata_tot,
        "massimo": ritorno(pieno),
        "simulato": ritorno(maschera_sim),
        "tabella": tabella,
    }


def statistiche_archivio(arch):
    chiuse = [a for a in arch if a.get("stato") in ("Vinta", "Persa")]
    puntato = sum(float(a.get("puntata", 0)) for a in chiuse)
    incassato = sum(
        float(a.get("incasso", 0)) for a in chiuse if a.get("stato") == "Vinta"
    )
    vinte = sum(1 for a in chiuse if a.get("stato") == "Vinta")
    return {
        "chiuse": len(chiuse),
        "vinte": vinte,
        "in_attesa": sum(1 for a in arch if a.get("stato") == "In attesa"),
        "puntato": puntato,
        "incassato": incassato,
        "netto": incassato - puntato,
        "pct": (vinte / len(chiuse) * 100) if chiuse else 0.0,
    }


def importa_archivio(testo, esistente):
    try:
        dati = json.loads(testo)
    except Exception:
        return esistente, "Testo non valido: incolla il backup completo."
    if not isinstance(dati, list):
        return esistente, "Il backup non ha il formato giusto."
    ids = {a.get("id") for a in esistente}
    nuovi = [
        a for a in dati
        if isinstance(a, dict) and a.get("id") and a["id"] not in ids and "puntata" in a
    ]
    return esistente + nuovi, f"Importate {len(nuovi)} schedine."
def mostra_quote_prepartita(tab, matches):
    with tab:
        
        st.subheader("💰 Quote Prepartita")
        st.caption("Confronto quote 1X2 tra i bookmaker disponibili.")

        if not matches:
            st.info("Nessuna partita disponibile.")
            return
            
        st.write("DATI PARTITA:", matches[0])
        oggi = datetime.now().date()
        fine_settimana = oggi + timedelta(days=(6 - oggi.weekday()))

        partite_future = [
            m for m in matches
            if m.get("date")
            and oggi <= datetime.strptime(m["date"], "%Y-%m-%d").date() <= fine_settimana
        ]

        if not partite_future:
            st.info("Nessuna partita futura disponibile questa settimana.")
            return

        etichette_partite = [
            f'{m["team1"]} vs {m["team2"]} — {m["date"]} {m["time"]}'
            for m in partite_future
        ]

        partita = st.selectbox(
            "⚽ Seleziona la partita",
            etichette_partite
        )

        st.write("PARTITA SELEZIONATA:", partita)

        if not ODDS_API_KEY:
            st.error("🔴 Chiave API quote non disponibile.")
            return

        try:
            r = requests.get(
                "https://odss-api.com/api/v1/odds",
                params={
                    "sport": "calcio",
                    "market": "1x2",
                    "state": "prematch",
                    "limit": 500
                },
                headers={"x-api-key": ODDS_API_KEY},
                timeout=10
            )

            if r.status_code != 200:
                st.error(f"🔴 Errore API quote: HTTP {r.status_code}")
                return

            data = r.json()
            odds_list = data.get("odds", [])
            st.write(odds_list[0]["bookmakers"][0])

            squadra_casa, squadra_trasferta = partita.split(" vs ", 1)

            evento_trovato = None

            for evento in odds_list:
                nome_evento = str(evento.get("event", "")).lower()

                if (
    squadra_casa.lower().replace("calcio", "").strip() == str(evento.get("home_team", "")).lower().strip()
    and
    squadra_trasferta.lower().replace("1907", "").strip() == str(evento.get("away_team", "")).lower().strip()
):
                    evento_trovato = evento
                    break

            if evento_trovato is None:
                st.warning("⚠️ Quote non trovate per questa partita.")
                return
            st.write("EVENTO TROVATO:", evento_trovato.get("home_team"), "vs", evento_trovato.get("away_team"))
            bookmakers = evento_trovato.get("bookmakers", [])

            if not bookmakers:
                st.warning("⚠️ Nessun bookmaker disponibile per questa partita.")
                return

            righe = []

            for book in bookmakers[:5]:
                outcomes = book.get("outcomes", {})

                righe.append({
                    "Bookmaker": book.get("key", "N/D"),
                    "1": outcomes.get("HOME", "—"),
                    "X": outcomes.get("DRAW", "—"),
                    "2": outcomes.get("AWAY", "—")
                })

            st.markdown("### 📊 Confronto quote 1X2")

            st.dataframe(
                righe,
                use_container_width=True,
                hide_index=True
            )

        except Exception as e:
            st.error(f"🔴 Errore nel caricamento delle quote: {e}")
ALIAS_SQUADRE = {
    "internazionale milano": "inter",
    "internazionale": "inter",
    "inter milan": "inter",
    "manchester utd": "manchester united",
    "man united": "manchester united",
    "man city": "manchester city",
    "tottenham hotspur": "tottenham",
    "spurs": "tottenham",
    "wolves": "wolverhampton wanderers",
    "newcastle": "newcastle united",
    "west ham": "west ham united",
    "brighton hove albion": "brighton",
    "atletico madrid": "atletico",
    "paris saint germain": "psg",
    "paris sg": "psg",
}


def _canon_squadra(nome):
    n = normalizza_nome(nome)
    return ALIAS_SQUADRE.get(n, n)


def _simili(a, b):
    ca, cb = _canon_squadra(a), _canon_squadra(b)
    if not ca or not cb:
        return 0.0
    if ca == cb:
        return 1.0
    return difflib.SequenceMatcher(None, ca, cb).ratio()


def trova_evento_quote(odds_list, casa, ospite, soglia=0.8):
    migliore, punteggio = None, 0.0
    for ev in odds_list:
        if not isinstance(ev, dict):
            continue
        sc = min(
            _simili(casa, ev.get("home_team", "")),
            _simili(ospite, ev.get("away_team", "")),
        )
        if sc > punteggio:
            migliore, punteggio = ev, sc
    if punteggio >= soglia:
        return migliore, punteggio
    return None, punteggio


@st.cache_data(ttl=300, show_spinner=False)
def carica_quote_api(chiave):
    try:
        r = requests.get(
            "https://odss-api.com/api/v1/odds",
            params={"sport": "calcio", "market": "1x2", "state": "prematch", "limit": 500},
            headers={"x-api-key": chiave},
            timeout=10,
        )
    except Exception as e:
        return {"ok": False, "errore": str(e), "odds": [], "chiavi": []}
    if r.status_code != 200:
        return {"ok": False, "errore": f"HTTP {r.status_code} - {r.text[:150]}", "odds": [], "chiavi": []}
    try:
        data = r.json()
    except Exception:
        return {"ok": False, "errore": "Risposta non in formato JSON.", "odds": [], "chiavi": []}
    if isinstance(data, dict):
        odds = data.get("odds", [])
        chiavi = list(data.keys())
    elif isinstance(data, list):
        odds, chiavi = data, []
    else:
        odds, chiavi = [], []
    return {"ok": True, "errore": "", "odds": odds if isinstance(odds, list) else [], "chiavi": chiavi}


def _quota(v):
    try:
        return float(v)
    except Exception:
        return None


def mostra_quote_prepartita(tab, matches):
    with tab:
        st.subheader("💰 Quote Prepartita")
        st.caption("Confronto quote 1X2 tra i bookmaker disponibili.")

        if not matches:
            st.info("Nessuna partita disponibile.")
            return

        periodo = st.selectbox(
            "Periodo",
            ["Prossimi 7 giorni", "Prossimi 14 giorni", "Prossimi 30 giorni"],
            key=f"quote_periodo_{campionato_top}_{stagione_selezionata}",
        )
        oggi = now.date()
        limite = oggi + timedelta(days=int(periodo.split()[1]))

        candidate = []
        for m in matches:
            if not isinstance(m, dict) or not m.get("team1") or not m.get("team2"):
                continue
            try:
                d = datetime.strptime(str(m.get("date", ""))[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
            if oggi <= d <= limite:
                candidate.append((d, m))
        candidate.sort(key=lambda x: (x[0], str(x[1].get("time") or "")))

        if not candidate:
            st.info("Nessuna partita nel periodo scelto.")
            return

        per_etichetta = {}
        for d, m in candidate:
            ora = f' {m["time"]}' if m.get("time") else ""
            per_etichetta[f'{m["team1"]} vs {m["team2"]} — {d}{ora}'] = m

        scelta = st.selectbox(
            "⚽ Seleziona la partita",
            list(per_etichetta.keys()),
            key=f"quote_partita_{campionato_top}_{stagione_selezionata}",
        )
        m_sel = per_etichetta[scelta]
        casa, ospite = m_sel["team1"], m_sel["team2"]

        if not ODDS_API_KEY:
            st.error("🔴 Chiave ODDS_API_KEY non trovata nei Secrets.")
            return

        res = carica_quote_api(ODDS_API_KEY)
        if not res["ok"]:
            st.error(f"🔴 Errore API quote: {res['errore']}")
            return
        odds_list = res["odds"]

        with st.expander("🔧 Diagnostica API"):
            st.write(f"Eventi ricevuti: **{len(odds_list)}**")
            st.write("Campi della risposta:", res["chiavi"] or "—")
            if odds_list and isinstance(odds_list[0], dict):
                st.write("Campi di un evento:", list(odds_list[0].keys()))
                esempi = [
                    f'{e.get("home_team", "?")} vs {e.get("away_team", "?")}'
                    for e in odds_list[:8]
                    if isinstance(e, dict)
                ]
                st.write("Primi eventi:", esempi)
                st.json(odds_list[0])

        if not odds_list:
            st.warning("⚠️ L'API non ha restituito eventi.")
            return

        evento, punteggio = trova_evento_quote(odds_list, casa, ospite)
        if evento is None:
            st.warning(
                f"⚠️ Quote non trovate per {casa} - {ospite} "
                f"(somiglianza migliore {punteggio:.0%}). "
                "Guarda la diagnostica: se i nomi sono scritti diversamente, "
                "aggiungili ad ALIAS_SQUADRE."
            )
            return

        st.caption(f"Evento trovato: {evento.get('home_team')} vs {evento.get('away_team')}")
        bookmakers = evento.get("bookmakers", [])
        if not bookmakers:
            st.warning("⚠️ Nessun bookmaker disponibile per questa partita.")
            return

        righe = []
        migliori = {"1": None, "X": None, "2": None}
        for book in bookmakers:
            out = book.get("outcomes", {}) if isinstance(book, dict) else {}
            riga = {"Bookmaker": book.get("key", "N/D")}
            for etichetta, chiave in (("1", "HOME"), ("X", "DRAW"), ("2", "AWAY")):
                q = _quota(out.get(chiave))
                riga[etichetta] = q
                if q is not None and (migliori[etichetta] is None or q > migliori[etichetta]):
                    migliori[etichetta] = q
            righe.append(riga)

        st.markdown("### 📊 Confronto quote 1X2")
        st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Miglior quota 1", migliori["1"] if migliori["1"] else "—")
        c2.metric("Miglior quota X", migliori["X"] if migliori["X"] else "—")
        c3.metric("Miglior quota 2", migliori["2"] if migliori["2"] else "—")
        st.caption(f"{len(righe)} bookmaker. Verifica sempre le quote sul sito dell'operatore.")
        st.markdown("**➕ Aggiungi alla schedina (miglior quota)**")
        if st.session_state.get("quote_msg"):
            st.success(st.session_state.quote_msg)
            st.session_state.quote_msg = None
        b1, b2, b3 = st.columns(3)
        for col, esito, giocata_q in ((b1, "1", "1X2: 1"), (b2, "X", "1X2: X"), (b3, "2", "1X2: 2")):
            q_best = migliori[esito]
            if q_best is None:
                continue
            if col.button(f"{esito} @ {q_best:.2f}", key=f"quote_add_{esito}_{scelta}", use_container_width=True):
                nuova_q = pd.DataFrame([{
                    "Partita": f'{casa} - {ospite} ({str(m_sel.get("date", ""))[:10]})',
                    "Giocata": giocata_q,
                    "Quota": float(q_best),
                    "Vinta": True,
                    "Elimina": False,
                }])
                if "slip_df" not in st.session_state or st.session_state.slip_df.empty:
                    st.session_state.slip_df = nuova_q
                else:
                    st.session_state.slip_df = pd.concat([st.session_state.slip_df, nuova_q], ignore_index=True)
                st.session_state.slip_ver = st.session_state.get("slip_ver", 0) + 1
                st.session_state.quote_msg = f"Aggiunta alla schedina: {casa} - {ospite}, {giocata_q} @ {q_best:.2f}"
                st.rerun()
def mostra_schedina(tab, matches=None):
    with tab:
        st.subheader("📝 Schedina")
        st.caption("Seleziona partite e quote dai menu a tendina: calcola quota totale, bonus e vincita potenziale.")

        # Inizializzazione sicura di tutte le variabili di sessione necessarie
        if 'slip_df' not in st.session_state:
            st.session_state.slip_df = pd.DataFrame({
                "Partita": pd.Series([], dtype="object"),
                "Giocata": pd.Series([], dtype="object"),
                "Quota": pd.Series([], dtype="float"),
                "Vinta": pd.Series([], dtype="bool"),
                "Elimina": pd.Series([], dtype="bool"),
            })
        if 'slip_ver' not in st.session_state:
            st.session_state.slip_ver = 0
        if 'slip_arch' not in st.session_state:
            st.session_state.slip_arch = []
        if 'arch_ver' not in st.session_state:
            st.session_state.arch_ver = 0

        # Tentativo diretto di prelevare il dataframe del palinsesto dall'ambiente globale o di sessione
        partite_disponibili = []
        
        # 1. Controlla se esiste una variabile globale df_palinsesto
        global_vars = globals()
        if 'df_palinsesto' in global_vars and global_vars['df_palinsesto'] is not None and not global_vars['df_palinsesto'].empty:
            df_pali = global_vars['df_palinsesto']
            if 'Casa' in df_pali.columns and 'Ospite' in df_pali.columns:
                partite_disponibili = (df_pali['Casa'].astype(str) + " - " + df_pali['Ospite'].astype(str)).tolist()

        # 2. Se non trovato, controlla nello st.session_state
        if not partite_disponibili:
            for key in st.session_state:
                val = st.session_state[key]
                if isinstance(val, pd.DataFrame) and 'Casa' in val.columns and 'Ospite' in val.columns and not val.empty:
                    partite_disponibili = (val['Casa'].astype(str) + " - " + val['Ospite'].astype(str)).tolist()
                    break

        # 3. Fallback estremo se proprio non aggancia nulla
        if not partite_disponibili:
            partite_disponibili = ["Inter - Parma", "Milan - Juventus", "Napoli - Roma"]
        # Elenco completo delle partite caricate
        _lista = []
        for m in sorted(
            [x for x in (matches or []) if isinstance(x, dict) and x.get("team1") and x.get("team2")],
            key=lambda x: (str(x.get("date") or ""), str(x.get("time") or "")),
        ):
            et = f'{m["team1"]} - {m["team2"]}'
            if m.get("date"):
                et += f' ({m["date"]})'
            if et not in _lista:
                _lista.append(et)
        if _lista:
            partite_disponibili = _lista
        st.markdown("### 🔍 Schedina Rapida")
        
        # Menu a tendina con l'elenco completo delle partite
        partita_selezionata = st.selectbox("Seleziona Partita", options=partite_disponibili, key="sel_partita_dinamica")

        # Menu a tendina per la tipologia di giocata
        opzioni_giocata = [
            "1X2: 1", "1X2: X", "1X2: 2", 
            "1X", "X2", "12",
            "Over 1.5", "Under 1.5", 
            "Over 2.5", "Under 2.5", 
            "Goal", "No Goal"
        ]
        giocata_selezionata = st.selectbox("Seleziona Giocata", options=opzioni_giocata, key="sel_giocata_dinamica")

        # Quota numerica
        quota = st.number_input("Quota", min_value=1.01, max_value=100.0, value=1.50, step=0.01, format="%.2f", key="input_quota_dinamica")

        # Pulsante di aggiunta
        if st.button("➕ Aggiungi alla schedina", key="btn_aggiungi_schedina"):
            nuova_riga = pd.DataFrame([{
                "Partita": partita_selezionata,
                "Giocata": giocata_selezionata,
                "Quota": float(quota),
                "Vinta": True,
                "Elimina": False
            }])
            
            if st.session_state.slip_df.empty:
                st.session_state.slip_df = nuova_riga
            else:
                st.session_state.slip_df = pd.concat([st.session_state.slip_df, nuova_riga], ignore_index=True)
            st.session_state.slip_ver += 1
            st.rerun()

        # Visualizzazione e gestione della schedina attiva
        df = st.session_state.slip_df
        if len(df) == 0:
            st.info("La schedina è vuota: seleziona una partita e aggiungi la prima giocata.")
        else:
            edited = st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key=f"editor_schedina_attiva_{st.session_state.slip_ver}"
            )
            
            if st.button("🗑 Svuota Schedina", key="btn_svuota_schedina"):
                st.session_state.slip_df = pd.DataFrame(columns=["Partita", "Giocata", "Quota", "Vinta", "Elimina"])
                st.session_state.slip_ver += 1
                st.rerun()
                

                
                
                
        
        df = st.session_state.slip_df
        if len(df) == 0:
            st.info("La schedina è vuota: aggiungi la prima selezione.")
        else:
            edited = st.data_editor(
                df,
                key=f"slip_ed_{st.session_state.slip_ver}",
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                column_config={
                    "Quota": st.column_config.NumberColumn(
                        "Quota", min_value=1.0, step=0.01, format="%.2f"
                    ),
                    "Vinta": st.column_config.CheckboxColumn("Vinta (simula)"),
                    "Elimina": st.column_config.CheckboxColumn("🗑"),
                },
            )
            st.session_state.slip_df = edited
            b1, b2 = st.columns(2)
            with b1:
                if st.button("🗑 Rimuovi spuntate", key="slip_rimuovi"):
                    st.session_state.slip_df = edited[~edited["Elimina"]].reset_index(
                        drop=True
                    )
                    st.session_state.slip_ver += 1
                    st.rerun()
            with b2:
                if st.button("Svuota schedina", key="slip_svuota"):
                    st.session_state.slip_df = edited.iloc[0:0]
                    st.session_state.slip_ver += 1
                    st.rerun()

            validi = edited[edited["Quota"].notna() & (edited["Quota"] >= 1.0)]
            quote = [float(q) for q in validi["Quota"]]
            n = len(quote)
            vinte_idx = [i for i, v in enumerate(validi["Vinta"]) if bool(v)]

            tipo = st.radio(
                "Tipo di giocata", ["Multipla", "Sistema"], horizontal=True,
                key="slip_tipo",
            )
            etichetta = "Puntata (€)" if tipo == "Multipla" else "Puntata per combinazione (€)"
            puntata = st.number_input(
                etichetta, min_value=0.5, value=10.0, step=0.5, key="slip_puntata"
            )

            potenziale = 0.0
            puntata_tot = puntata
            tipo_label = "Multipla"
            quota_tot_salva = None

            if tipo == "Multipla":
                with st.expander("Bonus multipla (dipende dal tuo operatore)"):
                    bonus_pct = st.number_input(
                        "Bonus multipla (%)", min_value=0.0, max_value=500.0,
                        value=0.0, step=0.5, key="slip_bonus",
                    )
                    quota_min = st.number_input(
                        "Quota minima valida per evento", min_value=1.0, value=1.25,
                        step=0.01, format="%.2f", key="slip_qmin",
                    )
                    eventi_min = st.number_input(
                        "Eventi minimi per il bonus", min_value=1, value=5, step=1,
                        key="slip_emin",
                    )
                    base = st.radio(
                        "Il bonus si applica alla",
                        ["Vincita netta (senza puntata)", "Vincita lorda"],
                        key="slip_base",
                    )
                r = calcola_multipla(
                    quote, puntata, bonus_pct, quota_min, int(eventi_min),
                    base.startswith("Vincita netta"),
                )
                if bonus_pct > 0 and not r["attivo"]:
                    st.warning(
                        f"Bonus non attivo: eventi validi {r['validi']} su "
                        f"{int(eventi_min)} richiesti (quota almeno {quota_min:.2f})."
                    )
                m1, m2 = st.columns(2)
                m1.metric("Quota totale", f"{r['quota_tot']:.2f}")
                m2.metric("Vincita senza bonus", f"{r['lorda']:.2f} €")
                m3, m4 = st.columns(2)
                m3.metric("Bonus", f"{r['bonus']:.2f} €")
                m4.metric("Totale potenziale", f"{r['totale']:.2f} €")
                st.caption(
                    f"Guadagno netto se vinci: {r['totale'] - puntata:.2f} €. "
                    "Controlla sempre il calcolo sul sito del tuo operatore."
                )
                potenziale = r["totale"]
                quota_tot_salva = r["quota_tot"]
            else:
                if n < 3:
                    st.info("Per un sistema servono almeno 3 selezioni.")
                elif n > 10:
                    st.info("Per i sistemi il massimo è 10 selezioni.")
                else:
                    k = st.selectbox(
                        "Sistema",
                        list(range(2, n)),
                        format_func=lambda x: f"{x} su {n}",
                        key=f"slip_k_{n}",
                    )
                    s = calcola_sistema(quote, k, puntata, vinte_idx)
                    m1, m2 = st.columns(2)
                    m1.metric("Combinazioni", s["combinazioni"])
                    m2.metric("Puntata totale", f"{s['puntata_tot']:.2f} €")
                    m3, m4 = st.columns(2)
                    m3.metric("Vincita massima", f"{s['massimo']:.2f} €")
                    m4.metric(
                        "Esito simulato", f"{s['simulato']:.2f} €",
                        delta=f"{s['simulato'] - s['puntata_tot']:+.2f} €",
                    )
                    st.markdown("**Cosa succede se sbagli qualche partita**")
                    st.dataframe(
                        pd.DataFrame(s["tabella"]),
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.caption(
                        "L'esito simulato usa le caselle «Vinta» della tabella. "
                        "Con più errori di quelli in tabella perdi tutta la puntata. "
                        "Nei sistemi il bonus multipla di solito non si applica."
                    )
                    potenziale = s["massimo"]
                    puntata_tot = s["puntata_tot"]
                    tipo_label = f"Sistema {k}/{n}"

            with st.expander("💾 Salva questa schedina"):
                nome = st.text_input("Nome o nota", key="slip_nome")
                stato = st.selectbox("Stato", STATI_SCHEDINA, key="slip_stato")
                incasso_in = st.number_input(
                    "Incasso effettivo (€), solo se Vinta", min_value=0.0, value=0.0,
                    step=0.5, key="slip_incasso",
                )
                if st.button("Salva nell'archivio", key="slip_salva"):
                    if n == 0 or potenziale <= 0:
                        st.warning("Niente da salvare.")
                    else:
                        if stato == "Vinta":
                            incasso = incasso_in if incasso_in > 0 else potenziale
                        else:
                            incasso = 0.0
                        eventi = [
                            {
                                "partita": str(rw["Partita"]),
                                "giocata": str(rw["Giocata"]),
                                "quota": float(rw["Quota"]),
                            }
                            for _, rw in validi.iterrows()
                        ]
                        st.session_state.slip_arch.append(
                            {
                                "id": uuid.uuid4().hex[:8],
                                "data": now.strftime("%Y-%m-%d %H:%M"),
                                "nome": nome.strip(),
                                "tipo": tipo_label,
                                "puntata": round(float(puntata_tot), 2),
                                "quota_tot": quota_tot_salva,
                                "potenziale": round(float(potenziale), 2),
                                "stato": stato,
                                "incasso": round(float(incasso), 2),
                                "eventi": eventi,
                            }
                        )
                        st.session_state.arch_ver += 1
                        st.success("Schedina salvata nell'archivio qui sotto.")

        st.divider()
        st.markdown("### 📚 Archivio giocate")
        arch = st.session_state.slip_arch
        if not arch:
            st.info("Nessuna schedina salvata.")
        else:
            riquadro = st.container()
            tab_arch = pd.DataFrame(
                [
                    {
                        "ID": a["id"],
                        "Data": a["data"],
                        "Nome": a["nome"],
                        "Tipo": a["tipo"],
                        "Puntata": a["puntata"],
                        "Potenziale": a["potenziale"],
                        "Stato": a["stato"],
                        "Incasso": a["incasso"],
                        "Elimina": False,
                    }
                    for a in arch
                ]
            )
            mod = st.data_editor(
                tab_arch,
                key=f"arch_ed_{st.session_state.arch_ver}",
                use_container_width=True,
                hide_index=True,
                disabled=["Data", "Nome", "Tipo", "Puntata", "Potenziale"],
                column_config={
                    "ID": None,
                    "Stato": st.column_config.SelectboxColumn(
                        "Stato", options=STATI_SCHEDINA, required=True
                    ),
                    "Incasso": st.column_config.NumberColumn(
                        "Incasso", min_value=0.0, step=0.5, format="%.2f"
                    ),
                    "Elimina": st.column_config.CheckboxColumn("🗑"),
                },
            )
            per_id = {a["id"]: a for a in arch}
            for _, rw in mod.iterrows():
                a = per_id.get(rw["ID"])
                if not a:
                    continue
                a["stato"] = rw["Stato"]
                if rw["Stato"] == "Vinta":
                    inc = float(rw["Incasso"])
                    a["incasso"] = inc if inc > 0 else a["potenziale"]
                else:
                    a["incasso"] = 0.0
            stt = statistiche_archivio(arch)
            with riquadro:
                a1, a2 = st.columns(2)
                a1.metric("Puntato (chiuse)", f"{stt['puntato']:.2f} €")
                a2.metric("Incassato", f"{stt['incassato']:.2f} €")
                a3, a4 = st.columns(2)
                a3.metric("Netto", f"{stt['netto']:+.2f} €")
                a4.metric(
                    "Vinte", f"{stt['vinte']}/{stt['chiuse']}",
                    delta=f"{stt['pct']:.0f}%", delta_color="off",
                )
                if stt["in_attesa"]:
                    st.caption(f"{stt['in_attesa']} schedine ancora in attesa.")
            if st.button("🗑 Rimuovi spuntate", key="arch_rimuovi"):
                da_togliere = set(mod.loc[mod["Elimina"], "ID"])
                st.session_state.slip_arch = [
                    a for a in arch if a["id"] not in da_togliere
                ]
                st.session_state.arch_ver += 1
                st.rerun()

            etichette = {
                f"{a['data']} | {a['nome'] or '(senza nome)'} | {a['tipo']}": a
                for a in arch
            }
            scelta = st.selectbox(
                "Dettaglio schedina", list(etichette.keys()), key="arch_dettaglio"
            )
            ev = etichette[scelta].get("eventi", [])
            if ev:
                st.dataframe(
                    pd.DataFrame(ev), use_container_width=True, hide_index=True
                )

        with st.expander("📤 Backup e importazione"):
            st.caption(
                "L'archivio vive solo finché l'app resta aperta: se la pagina "
                "si ricarica o l'app si riavvia, si cancella. Copia il testo "
                "qui sotto (pulsante in alto a destra del riquadro) e salvalo "
                "nelle note del telefono."
            )
            testo = json.dumps(st.session_state.slip_arch, ensure_ascii=False)
            st.code(testo, language="json")
            st.download_button(
                "Scarica file", testo, file_name="schedine.json",
                mime="application/json", key="arch_download",
            )
            incolla = st.text_area(
                "Incolla qui un backup per importarlo", key="arch_incolla"
            )
            if st.button("Importa", key="arch_importa"):
                nuovo, msg = importa_archivio(incolla, st.session_state.slip_arch)
                st.session_state.slip_arch = nuovo
                st.session_state.arch_ver += 1
                st.info(msg)


import html as _html


def scritta_macchina():
    testo = "Wanna bet it works?"
    css = (
        "<style>"
        ".tw-wrap{display:flex;justify-content:center;margin:12px 0 4px 0;"
        "font-family:'Courier New',ui-monospace,monospace;font-size:18px;"
        "font-weight:700;}"
        ".tw-box{width:__W__ch;}"
        ".tw{width:0;overflow:hidden;white-space:nowrap;color:#7ee787;"
        "border-right:2px solid #7ee787;text-shadow:0 0 8px rgba(126,231,135,0.55);"
        "animation:tw-type 8s steps(__N__,end) infinite,"
        "tw-blink 0.8s step-end infinite;}"
        "@keyframes tw-type{0%{width:0}30%{width:__N__ch}70%{width:__N__ch}"
        "85%{width:0}100%{width:0}}"
        "@keyframes tw-blink{50%{border-color:transparent}}"
        "@media (prefers-reduced-motion:reduce){.tw{animation:none;"
        "width:__N__ch;border-right:none;}}"
        "</style>"
    )
    css = css.replace("__N__", str(len(testo))).replace("__W__", str(len(testo) + 1))
    st.markdown(
        css
        + f"<div class='tw-wrap'><div class='tw-box'><div class='tw'>{testo}</div></div></div>",
        unsafe_allow_html=True,
    )
def mostra_home():
    st.markdown(
        "<style>"
        "[data-testid='stHeaderActionElements']{display:none !important;}"
        "button[kind='primary'],button[data-testid='stBaseButton-primary']"
        "{background:linear-gradient(90deg,#1f6feb,#238636) !important;"
        "border:none !important;color:#fff !important;font-weight:700 !important;"
        "padding:0.7rem 1rem !important;border-radius:12px !important;"
        "box-shadow:0 0 18px rgba(31,111,235,0.35);}"
        ".hx-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0;}"
        ".hx-stat,.hx-card,.hx-tile{background:rgba(22,27,34,0.62);"
        "backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);"
        "border:1px solid rgba(255,255,255,0.09);border-radius:14px;}"
        ".hx-stat{padding:12px 6px;text-align:center;}"
        ".hx-stat b{display:block;font-size:24px;color:#fff;}"
        ".hx-stat span{font-size:11px;color:#8b949e;}"
        ".hx-card{padding:14px;margin:6px 0 14px 0;}"
        ".hx-title{font-weight:700;color:#fff;font-size:15px;margin-bottom:6px;}"
        ".hx-pick{display:flex;justify-content:space-between;gap:10px;padding:8px 0;"
        "border-bottom:1px solid rgba(255,255,255,0.07);font-size:13px;color:#c9d1d9;}"
        ".hx-note{font-size:11px;color:#8b949e;margin-top:8px;}"
        ".hx-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;}"
        ".hx-tile{display:flex;align-items:center;gap:10px;padding:12px;}"
        ".hx-tile:last-child{grid-column:1 / -1;}"
        ".hx-ico{font-size:24px;}"
        ".hx-tile b{color:#fff;font-size:14px;}"
        ".hx-tile span{color:#8b949e;font-size:11px;}"
        "</style>",
        unsafe_allow_html=True,
    )

    foto = immagine_base64(FILE_PORTIERE, 700, 72)
    if foto:
        sfondo_hero = (
            "linear-gradient(180deg,rgba(5,7,10,0.10) 0%,rgba(5,7,10,0.88) 100%),"
            f"url('{foto}')"
        )
    else:
        sfondo_hero = "linear-gradient(135deg,#161b22,#0d1117)"
    st.markdown(
        "<div style=\"border-radius:18px;overflow:hidden;"
        "border:1px solid rgba(88,166,255,0.35);min-height:230px;display:flex;"
        "flex-direction:column;justify-content:flex-end;padding:20px;"
        f"background:{sfondo_hero};background-size:cover;background-position:62% center;\">"
        "<div style='font-size:11px;letter-spacing:2px;color:#58a6ff;font-weight:700;'>"
        "FOOTBALL STATISTICS · ANALYSIS · PROBABILITIES</div>"
        "<div style='font-size:34px;font-weight:800;color:#fff;line-height:1.15;'>"
        "⚽ b-betting</div>"
        "<div style='color:#c9d1d9;font-size:13px;margin-top:6px;'>"
        "Statistiche, modello di Poisson e pronostici su cinque campionati.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button(
        "🚀 Entra nella Dashboard", use_container_width=True, type="primary"
    ):
        st.session_state.pagina = "dashboard"
        st.rerun()

    consigli = []
    try:
        with st.spinner("Carico i dati live..."):
            consigli = raccogli_consigli(stagione_selezionata, 7, False)
    except Exception:
        consigli = []
    arch = st.session_state.get("slip_arch", [])
    stt = statistiche_archivio(arch)
    netto = f"{stt['netto']:+.0f} €" if stt["chiuse"] else "—"
    campionati = len({c["campionato"] for c in consigli})
    st.markdown(
        "<div class='hx-stats'>"
        f"<div class='hx-stat'><b>{len(consigli)}</b><span>Partite in arrivo (7 gg)</span></div>"
        f"<div class='hx-stat'><b>{campionati}</b><span>Campionati in campo</span></div>"
        f"<div class='hx-stat'><b>{netto}</b><span>Netto schedine</span></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    scritta_macchina()

    righe = ""
    for c in consigli[:3]:
        righe += (
            "<div class='hx-pick'>"
            f"<span>{stelle_difficolta(c['p'])}<br><b>{_html.escape(c['partita'])}</b></span>"
            f"<span style='text-align:right'>{_html.escape(c['giocata'])}"
            f"<br><b>{c['p']:.0f}%</b></span>"
            "</div>"
        )
    if not righe:
        righe = (
            "<div class='hx-pick'>Nessuna partita nei prossimi 7 giorni: "
            "prova la tab AI Advice con 14 giorni.</div>"
        )
    st.markdown(
        "<div class='hx-card'><div class='hx-title'>💡 Le 3 giocate più solide</div>"
        + righe
        + "<div class='hx-note'>Stima del modello, non una garanzia.</div></div>",
        unsafe_allow_html=True,
    )

    sezioni = [
        ("📅", "Palinsesto", "Calendario e risultati", "#238636"),
        ("📊", "Classifica", "Punti e differenza reti", "#d29922"),
        ("📈", "Analisi Match", "Statistiche e confronti", "#da3633"),
        ("🎯", "Riepilogo", "Pronostici in arrivo", "#58a6ff"),
        ("🧪", "Backtest", "Verifica il modello", "#a371f7"),
        ("💡", "AI Advice", "Top 10 e multiple", "#f2cc60"),
        ("🧾", "Schedina", "Quote, bonus, sistemi", "#3fb950"),
    ]
    tessere = "".join(
        f"<div class='hx-tile' style='border-left:3px solid {col}'>"
        f"<div class='hx-ico'>{ico}</div>"
        f"<div><b>{nome}</b><br><span>{desc}</span></div></div>"
        for ico, nome, desc, col in sezioni
    )
    st.markdown("<div class='hx-grid'>" + tessere + "</div>", unsafe_allow_html=True)
    st.caption(
        "Strumento di analisi statistica: nessuna previsione è garantita. "
        "Solo maggiorenni, gioca responsabilmente."
    )
def mostra_quote_confronto(t1, t2, dettagli):
    st.markdown("### 💰 Quote bookmaker")
    if not ODDS_API_KEY:
        st.info("Chiave ODDS_API_KEY non configurata: quote non disponibili.")
        return
    try:
        res = carica_quote_api(ODDS_API_KEY)
        if not res["ok"]:
            st.info(f"Quote non disponibili: {res['errore']}")
            return
        evento, _ = trova_evento_quote(res["odds"], t1, t2)
        if evento is None:
            st.info(
                "Quote non trovate per questa partita: di solito sono "
                "disponibili solo per le gare dei prossimi giorni."
            )
            return
        valori = {"1": [], "X": [], "2": []}
        righe_book = []
        for book in evento.get("bookmakers", []):
            out = book.get("outcomes", {}) if isinstance(book, dict) else {}
            riga = {"Bookmaker": book.get("key", "N/D")}
            for et, ch in (("1", "HOME"), ("X", "DRAW"), ("2", "AWAY")):
                q = _quota(out.get(ch))
                riga[et] = q
                if q is not None:
                    valori[et].append(q)
            righe_book.append(riga)
        if not righe_book or not any(valori.values()):
            st.info("Nessuna quota disponibile per questa partita.")
            return

        e = dettagli.get("e", {}) if dettagli else {}
        nomi = {"1": f"1 - {t1}", "X": "X - Pareggio", "2": f"2 - {t2}"}
        righe = []
        for et in ("1", "X", "2"):
            v = valori[et]
            if not v:
                continue
            best = max(v)
            p_mod = e.get(et)
            riga = {
                "Esito": nomi[et],
                "Miglior quota": round(best, 2),
                "Quota media": round(sum(v) / len(v), 2),
            }
            if p_mod:
                riga["Modello %"] = round(p_mod, 1)
                riga["Quota equa modello"] = round(100 / p_mod, 2)
                riga["Modello - mercato (punti %)"] = round(p_mod - 100 / best, 1)
            righe.append(riga)
        st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)
        st.caption(
            "Modello - mercato: positivo se il modello stima l'esito più "
            "probabile di quanto indichi la miglior quota. Il modello è una "
            "stima semplice e le quote includono il margine del bookmaker: "
            "non è un segnale di vincita garantita."
        )
        with st.expander(f"Tutte le quote ({len(righe_book)} bookmaker)"):
            st.dataframe(pd.DataFrame(righe_book), use_container_width=True, hide_index=True)
    except Exception as ex:
        st.info(f"Quote non disponibili: {ex}")
def sezione_confronto(matches):
    oggi = now.strftime("%Y-%m-%d")
    prossime = [
        m
        for m in matches
        if isinstance(m, dict)
        and m.get("team1")
        and m.get("team2")
        and str(m.get("date", "")) >= oggi
    ]

    if not prossime:
        st.info("Nessuna partita futura disponibile per questo torneo/stagione.")
        return

    match_dict = {
        f"{m.get('date', 'Data n.d.')} | {m['team1']} vs {m['team2']}": m
        for m in prossime
    }

    st.markdown("🎯 *Seleziona una partita per il Confronto Diretto e Pronostico IA:*")
    scelta = st.selectbox(
        "Seleziona la Partita della Giornata",
        list(match_dict.keys()),
        key=f"match_scelto_{campionato_top}_{stagione_selezionata}",
    )

    m_sel = match_dict[scelta]
    t1, t2 = m_sel["team1"], m_sel["team2"]

    stats_t1 = calcola_statistiche_squadra(matches, t1)
    stats_t2 = calcola_statistiche_squadra(matches, t2)
    
    prob_1, prob_x, prob_2, dettagli_v2 = probabilita_v2(matches, t1, t2, stats_t1, stats_t2)
    mostra_dna_pronostico(t1, t2, dettagli_v2)
    st.markdown("---")
    st.markdown(f"### ⚔️ Confronto Diretto: {t1} vs {t2}")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        mostra_metriche_squadra(f"#### 🏠 {badge_squadra(t1)} {t1}", stats_t1)
    with col_s2:
        mostra_metriche_squadra(f"#### ✈️ {badge_squadra(t2)} {t2}", stats_t2)
    mostra_scontri_diretti(campionato_top, t1, t2)
    mostra_grafico_forma({t1: stats_t1, t2: stats_t2})
    mostra_stats_tempi(f"#### ⏱️ Gol per tempo: {t1}", calcola_stats_tempi(matches, t1))
    mostra_stats_tempi(f"#### ⏱️ Gol per tempo: {t2}", calcola_stats_tempi(matches, t2))
    mostra_stats_extra(f"#### 📊 Angoli e tiri: {t1}", t1)
    mostra_stats_extra(f"#### 📊 Angoli e tiri: {t2}", t2)
    mostra_pronostico_v2(matches, t1, t2)
    mostra_quote_confronto(t1, t2, dettagli_v2)
    st.markdown("---")
    analisi = genera_analisi_v2(t1, t2, prob_1, prob_x, prob_2, dettagli_v2)
    st.markdown(
        f"<div class='ai-box'>{analisi}<br><br><b>Previsioni Esito 1X2:</b><br>"
        f"• {t1} (1): <b>{prob_1}%</b><br>"
        f"• Pareggio (X): <b>{prob_x}%</b><br>"
        f"• {t2} (2): <b>{prob_2}%</b></div>",
        unsafe_allow_html=True,
        )
if st.session_state.pagina == "home":
    mostra_home()
    st.stop()
    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; padding: 35px; border-radius: 16px; margin-top: 20px; text-align: center;'>
            <h1 style='color: #58a6ff; font-size: 38px; margin-bottom: 10px;'>⚽ b-betting Hub</h1>
            <p style='color: #8b949e; font-size: 16px; margin-bottom: 30px;'>Piattaforma avanzata di Live Data Architecture, Statistiche Sportive e Previsioni Algoritmiche.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_h1, col_h2, col_h3 = st.columns([1, 2, 1])
    with col_h2:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        if st.button(
            "🚀 ACCEDI ALLA DASHBOARD", use_container_width=True, type="primary"
        ):
            st.session_state.pagina = "dashboard"
            st.rerun()

    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

    feature_box = (
        "<div style='background: #161b22; padding: 20px; border-radius: 12px;"
        " border: 1px solid #30363d; text-align: center;'><h3>{icona}</h3>"
        "<h4>{titolo}</h4><p style='color: #8b949e; font-size: 13px;'>{testo}</p></div>"
    )
    col_feat1, col_feat2, col_feat3 = st.columns(3)
    with col_feat1:
        st.markdown(
            feature_box.format(
                icona="📅",
                titolo="Palinsesto Live",
                testo="Consulta calendari e partite aggiornate dai principali tornei.",
            ),
            unsafe_allow_html=True,
        )
    with col_feat2:
        st.markdown(
            feature_box.format(
                icona="📊",
                titolo="Classifiche Aggiornate",
                testo="Analizza punti, gol fatti, subiti e differenza reti.",
            ),
            unsafe_allow_html=True,
        )
    with col_feat3:
        st.markdown(
            feature_box.format(
                icona="🤖",
                titolo="Analisi IA & Pronostici",
                testo="Algoritmi predittivi per stimare le probabilità di match.",
            ),
            unsafe_allow_html=True,
        )

else:
    col_title, col_home_btn = st.columns([0.80, 0.20])
    with col_title:
        st.title("⚽ b-betting")
        st.markdown(
    "<p style='color:#8b949e; font-size:14px; margin-top:-10px;'>"
    "Football Statistics • Analysis • Probabilities"
    "</p>",
    unsafe_allow_html=True,
        )
    with col_home_btn:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🏠 Home", use_container_width=True, help="Torna alla Home"):
            st.session_state.pagina = "home"
            st.rerun()

    st.divider()

    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; padding: 25px; border-radius: 16px; margin-bottom: 20px;'>
            <h2 style='color: #58a6ff; margin-bottom: 5px;'>⚽ b-betting Hub</h2>
            <p style='color: #8b949e; font-size: 14px; margin-top: 0;'>Piattaforma avanzata di Live Data Architecture, Statistiche Sportive e Previsioni Algoritmiche.</p>
            <div style='display: flex; gap: 10px; flex-wrap: wrap; margin-top: 15px;'>
                <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>⚡ Engine: <b>Attivo</b></span>
                <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>📊 Modello IA: <b>v4.2 Pro</b></span>
                <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>🕒 Sync: <b>Real-time</b></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    data = carica_dati_campionato(campionato_top, stagione_selezionata)
    matches = data.get("matches", [])

    tab1, tab2, tab3, tab4,tab5,tab6,tab7,tab8 = st.tabs(
        ["📅 Palinsesto", "📊 Classifica", "📈 Analisi Match & Statistiche", "🎯 Riepilogo", "🧪 Backtest", "💡 AI Advice", "🧾 Schedina", "💰 Quote Prepartita"]
    )
    mostra_riepilogo(matches, tab4)
    mostra_backtest(matches, tab5)
    mostra_ai_advice(tab6)
    mostra_schedina(tab7, matches)
    mostra_quote_prepartita(tab8,matches)
    with tab1:
        st.subheader("Palinsesto Match")
        partite = [m for m in matches if isinstance(m, dict)]
        if partite:
            giornate = []
            for m in partite:
                g = m.get("round")
                if g and g not in giornate:
                    giornate.append(g)

            filtro = "Tutte le giornate"
            if giornate:
                filtro = st.selectbox(
                    "Filtra per giornata",
                    ["Tutte le giornate"] + giornate,
                    key=f"filtro_giornata_{campionato_top}_{stagione_selezionata}",
                )

            lista = []
            for m in partite:
                if filtro != "Tutte le giornate" and m.get("round") != filtro:
                    continue
                sc = m.get("score")
                ft = sc.get("ft") if isinstance(sc, dict) else None
                lista.append(
                    {
                        "Giornata": m.get("round", ""),
                        "Data": m.get("date", ""),
                        "Casa": m.get("team1", ""),
                        "Ospite": m.get("team2", ""),
                        "Risultato": f"{ft[0]}-{ft[1]}" if ft else "-",
                    }
                )
            st.dataframe(
                pd.DataFrame(lista), use_container_width=True, hide_index=True
            )
        else:
            st.warning("Dati non disponibili per questo torneo.")

    with tab2:
        st.subheader("Classifica Live")
        classifica = {}
        for m in matches:
            if (
                isinstance(m, dict)
                and isinstance(m.get("score"), dict)
                and m["score"].get("ft")
            ):
                t1, t2 = m.get("team1"), m.get("team2")
                if not t1 or not t2:
                    continue
                g1, g2 = m["score"]["ft"][0], m["score"]["ft"][1]
                for sq in (t1, t2):
                    if sq not in classifica:
                        classifica[sq] = {
                            "Squadra": sq,
                            "PG": 0,
                            "Pt": 0,
                            "GF": 0,
                            "GS": 0,
                        }
                classifica[t1]["PG"] += 1
                classifica[t2]["PG"] += 1
                classifica[t1]["GF"] += g1
                classifica[t1]["GS"] += g2
                classifica[t2]["GF"] += g2
                classifica[t2]["GS"] += g1
                if g1 > g2:
                    classifica[t1]["Pt"] += 3
                elif g1 < g2:
                    classifica[t2]["Pt"] += 3
                else:
                    classifica[t1]["Pt"] += 1
                    classifica[t2]["Pt"] += 1

        if classifica:
            df_c = pd.DataFrame(list(classifica.values()))
            df_c["DR"] = df_c["GF"] - df_c["GS"]
            df_c = df_c.sort_values(
                by=["Pt", "DR"], ascending=False
            ).reset_index(drop=True)
            df_c.index += 1
            st.dataframe(df_c, use_container_width=True)
        else:
            st.warning("Classifica non disponibile.")

    with tab3:
        st.subheader("📊 Analisi Match & Statistiche")

        tutte_squadre = sorted(
            {m.get("team1") for m in matches if isinstance(m, dict) and m.get("team1")}
            | {m.get("team2") for m in matches if isinstance(m, dict) and m.get("team2")}
        )

        if not tutte_squadre:
            st.warning("Dati non disponibili per questo torneo.")
        else:
            st.markdown("🔍 **Cerca Statistiche per Singola Squadra:**")
            squadra_singola = st.selectbox(
                "Seleziona o digita una squadra per visualizzare le sue statistiche",
                ["-- Seleziona una squadra --"] + tutte_squadre,
                key="ricerca_singola_squadra",
            )

            if squadra_singola != "-- Seleziona una squadra --":
                st.markdown(f"### 📋 Report: {badge_squadra(squadra_singola)} {squadra_singola}", unsafe_allow_html=True)
                stats_singola = calcola_statistiche_squadra(matches, squadra_singola)
                if stats_singola:
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("Punti a Partita (PPG)", stats_singola["ppg"])
                        st.metric("Partite Giocate", stats_singola["tot"])
                    with c2:
                        st.metric("Media Gol Fatti", stats_singola["gf_avg"])
                        st.metric("Over 2.5 %", f"{stats_singola['over_2_5_pct']}%")
                    with c3:
                        st.metric("Media Gol Subiti", stats_singola["gs_avg"])
                        st.metric(
                            "Clean Sheet %", f"{stats_singola['clean_sheets_pct']}%"
                        )
                    with c4:
                        st.metric("BTTS %", f"{stats_singola['btts_pct']}%")

                    st.markdown("**Stato di Forma (Ultime 5):**")
                    classi = {"V": "badge-v", "N": "badge-n", "P": "badge-p"}
                    forma_html = "".join(
                        f"<span class='{classi[r]}'>{r}</span>"
                        for r in stats_singola["forma"][-5:]
                    )
                    st.markdown(forma_html or "N.D.", unsafe_allow_html=True)
                    mostra_stats_tempi("#### ⏱️ Gol per tempo", calcola_stats_tempi(matches, squadra_singola))
                    mostra_grafico_forma({squadra_singola: stats_singola})
                    mostra_stats_extra("#### 📊 Angoli, tiri e disciplina", squadra_singola)
                else:
                    st.info(
                        "Nessun dato di match disputati disponibile per questa"
                        " squadra nella stagione selezionata."
                    )

            st.markdown("---")
            sezione_confronto(matches)

