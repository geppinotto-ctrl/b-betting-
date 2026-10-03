from pathlib import Path
import base64
import io
import os
import streamlit as st
import streamlit.components.v1 as components


FILE_TEXTURE = "17909154919832446827610680716341.jpg"
FILE_PORTIERE = "1000023096.jpg"
OPACITA_PORTIERE = 0.30


@st.cache_data
def carica_audio_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            audio_bytes = f.read()
        return base64.b64encode(audio_bytes).decode()
    return None


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


def audio_sottofondo():
    st.sidebar.markdown("### 🎵 Atmosfera Sonora")
    silenziatore = st.sidebar.checkbox("Silenzia sottofondo", value=False)
    audio_path = "calculated_grace (1).mp3"
    if not silenziatore:
        audio_base64 = carica_audio_base64(audio_path)
        if audio_base64:
            audio_html = f"""
                <audio autoplay loop volume="0.05">
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                    Il tuo browser non supporta l'elemento audio.
                </audio>
            """
            components.html(audio_html + "<script>var a=document.querySelector('audio');a.volume=0.05;a.play().catch(function(){try{window.parent.document.addEventListener('click',function(){a.play();},{once:true});}catch(e){}});</script>", height=0)
        else:
            st.sidebar.caption("⚠️ File audio non trovato.")


def applica_css_vetro():
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


def applica_css_principale():
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


def prepara_sfondo():
    global FILE_TEXTURE, FILE_PORTIERE
    applica_sfondo(OPACITA_PORTIERE)
    _trama, _portiere = trova_immagini()
    if _trama:
        FILE_TEXTURE = _trama
    if _portiere:
        FILE_PORTIERE = _portiere
    applica_sfondo(OPACITA_PORTIERE)
