from datetime import datetime, timedelta, timezone

import streamlit as st

try:
    from zoneinfo import ZoneInfo

    TZ_ITALIA = ZoneInfo("Europe/Rome")
except Exception:  # tzdata assente (es. Windows senza pacchetto tzdata)
    TZ_ITALIA = timezone(timedelta(hours=2))


def _secret(nome, default=""):
    """Legge un secret senza mai sollevare eccezioni.

    ``st.secrets`` solleva se manca il file secrets.toml: all'import di questo
    modulo avrebbe fatto crashare l'intera app prima ancora di partire.
    """
    try:
        valore = st.secrets.get(nome, default)
    except Exception:
        return default
    return default if valore is None else valore


ODDS_API_KEY = str(_secret("ODDS_API_KEY", "")).strip()
# Base URL del provider quote. Sovrascrivibile da secrets senza toccare il codice.
ODDS_API_BASE = str(_secret("ODDS_API_BASE", "https://odss-api.com/api/v1")).rstrip("/")

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
