from datetime import datetime, timedelta, timezone

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
    giorno_corrente = giorni_it[now.weekday()]
    data_ora_formattata = f"{giorno_corrente}, {now.strftime('%d/%m/%Y - %H:%M')}"
    st.markdown(
        f"<div class='timer-box'>🕒 Riferimento Live (Italia):<br>{data_ora_formattata}</div>",
        unsafe_allow_html=True,
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
    st.markdown(titolo)
    if stats:
        st.metric("Punti a Partita (PPG)", stats["ppg"])
        st.metric("Media Gol Fatti", stats["gf_avg"])
        st.metric("Media Gol Subiti", stats["gs_avg"])
        st.metric("Over 2.5 %", f"{stats['over_2_5_pct']}%")
        st.metric("Clean Sheet %", f"{stats['clean_sheets_pct']}%")
        st.metric("BTTS %", f"{stats['btts_pct']}%")
    else:
        st.info("Dati insufficienti per questa squadra.")


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
    prob_1, prob_x, prob_2 = calcola_pronostico_ia(stats_t1, stats_t2)

    st.markdown("---")
    st.markdown(f"### ⚔️ Confronto Diretto: {t1} vs {t2}")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        mostra_metriche_squadra(f"#### 🏠 {t1}", stats_t1)
    with col_s2:
        mostra_metriche_squadra(f"#### ✈️ {t2}", stats_t2)

    st.markdown("---")
    analisi = genera_analisi_ia_match(t1, t2, prob_1, prob_x, prob_2)
    st.markdown(
        f"<div class='ai-box'>{analisi}<br><br><b>Previsioni Esito 1X2:</b><br>"
        f"• {t1} (1): <b>{prob_1}%</b><br>"
        f"• Pareggio (X): <b>{prob_x}%</b><br>"
        f"• {t2} (2): <b>{prob_2}%</b></div>",
        unsafe_allow_html=True,
        )
