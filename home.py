import streamlit as st
import stile
from config import stagione_corrente
from modello import raccogli_consigli, stelle_difficolta
from schedina import statistiche_archivio
from stile import immagine_base64, scritta_macchina


import html as _html


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

    foto = immagine_base64(stile.FILE_PORTIERE, 700, 72)
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
            consigli = raccogli_consigli(stagione_corrente(), 7, False)
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
