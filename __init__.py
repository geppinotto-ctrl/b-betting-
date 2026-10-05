"""Finto streamlit per test di logica (nessuna UI reale)."""
import functools, sys, types
from unittest.mock import MagicMock

LOG = []          # (tipo, testo) di ogni st.warning / st.error / st.info / ...
_REGISTRO_CACHE = []


class _Stato(dict):
    __getattr__ = lambda self, k: self[k] if k in self else (_ for _ in ()).throw(AttributeError(k))
    def __setattr__(self, k, v): self[k] = v


session_state = _Stato()


class _Secrets:
    presente = False
    def get(self, k, d=None):
        if not self.presente:
            raise FileNotFoundError("No secrets found")  # come Streamlit senza secrets.toml
        return {"ODDS_API_KEY": "CHIAVE"}.get(k, d)

secrets = _Secrets()


def cache_data(func=None, **kw):
    def deco(f):
        memo = {}
        @functools.wraps(f)
        def w(*a, **k):
            chiave = repr((a, sorted(k.items())))
            if chiave in memo:
                return memo[chiave]
            r = f(*a, **k)          # se solleva, NON viene memorizzato
            memo[chiave] = r
            return r
        w.clear = memo.clear
        w.calls = lambda: len(memo)
        return w
    return deco(func) if callable(func) else deco


class _Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, n): return MagicMock()


class _Barra(_Ctx):
    def progress(self, f, text=""): LOG.append(("progress", f"{f:.2f} {text}"))
    def empty(self): LOG.append(("progress", "vuota"))


def progress(f=0.0, text=""):
    LOG.append(("progress", f"{f:.2f} {text}")); return _Barra()
def spinner(testo=""): LOG.append(("spinner", testo)); return _Ctx()
def _msg(tipo):
    return lambda testo="", *a, **k: LOG.append((tipo, str(testo)))
warning, error, info, success, caption = (_msg(t) for t in ("warning", "error", "info", "success", "caption"))
def expander(*a, **k): return _Ctx()
def columns(n, *a, **k):
    n = n if isinstance(n, int) else len(n); return [_Ctx() for _ in range(n)]
def tabs(nomi): return [_Ctx() for _ in nomi]
def code(*a, **k): LOG.append(("code", "traceback"))
def stop(): raise SystemExit
def rerun(): pass

def button(*a, **k): return False
def checkbox(label, value=False, key=None, **k):
    if key is not None: session_state.setdefault(key, value); return session_state[key]
    return value
def toggle(*a, **k): return checkbox(*a, **k)
def selectbox(label, options=(), index=0, key=None, **k):
    options = list(options)
    if key is not None and key in session_state: return session_state[key]
    v = options[index] if options and index is not None and index < len(options) else None
    if key is not None: session_state[key] = v
    return v
def radio(label, options=(), index=0, key=None, **k): return selectbox(label, options, index, key)
def number_input(label, min_value=None, max_value=None, value=0, key=None, **k):
    if key is not None: session_state.setdefault(key, value); return session_state[key]
    return value
def multiselect(*a, **k): return []
def text_input(label, value="", key=None, **k):
    if key is not None: session_state.setdefault(key, value); return session_state[key]
    return value

def __getattr__(nome):                      # tutto il resto: finto e muto
    return MagicMock(name=nome)

components = types.ModuleType("streamlit.components"); components.v1 = types.ModuleType("streamlit.components.v1")
components.v1.html = lambda *a, **k: None
sys.modules["streamlit.components"] = components
sys.modules["streamlit.components.v1"] = components.v1
