from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import streamlit as st


try:
    from zoneinfo import ZoneInfo

    TZ_ITALIA = ZoneInfo("Europe/Rome")
except Exception:
    TZ_ITALIA = timezone(timedelta(hours=2))
ODDS_API_KEY = st.secrets.get("ODDS_API_KEY", "")
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

STAGIONI = ["2026-27", "2025-26", "2024-25"]


def torneo_corrente():
    """Torneo scelto nella barra laterale."""
    return st.session_state.get("torneo", campionati_disponibili[0])


def stagione_corrente():
    """Stagione scelta nella barra laterale."""
    return st.session_state.get("stagione", STAGIONI[0])


def adesso():
    """Data e ora attuali in Italia."""
    return datetime.now(TZ_ITALIA)
