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

    .stTabs [data-baseweb="tab-list"] button:nth-child(1) {
        background-color: rgba(35, 134, 54, 0.15);
        border: 1px solid #238636;
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
    "UEFA Champions League": ["cl.json", "champions-league/index.json"],
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
def carica_dati_campionato(nome_campionato, stagione):
    possibili_nomi = mapping_file_torneo.get(nome_campionato, ["it.1.json"])
    anno_inizio = stagione.split("-")[0]
    percorsi_da_tentare = []
    for nome_file in possibili_nomi:
        percorsi_da_tentare.append(f"{stagione}/{nome_file}")
        percorsi_da_tentare.append(nome_file)
        percorsi_da_tentare.append(f"{anno_inizio}/{nome_file}")

    for p in percorsi_da_tentare:
        url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{p}"
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
    media = (d["
