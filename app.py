"""
SmartMat — Automotive Material Selection Advisor
Progressive page-based UI with slider + number sync.
"""

from __future__ import annotations
from typing import Any
from urllib.parse import quote_plus
import pandas as pd
import requests
import streamlit as st

API_BASE = "http://127.0.0.1:5000"
TIMEOUT  = 30

COMPONENT_PRESETS = {
    "Chassis / Frame":        {"strength":10,"weight":7,"cost":5,"temp":6,"sustainability":6},
    "Body Panel / Skin":      {"strength":6, "weight":9,"cost":6,"temp":5,"sustainability":7},
    "Engine Block":           {"strength":9, "weight":5,"cost":5,"temp":10,"sustainability":5},
    "Suspension Component":   {"strength":9, "weight":8,"cost":6,"temp":7,"sustainability":6},
    "Brake System":           {"strength":8, "weight":6,"cost":6,"temp":9,"sustainability":5},
    "Wheel / Rim":            {"strength":8, "weight":9,"cost":6,"temp":6,"sustainability":6},
    "Interior Structure":     {"strength":5, "weight":7,"cost":7,"temp":4,"sustainability":8},
    "Exhaust System":         {"strength":7, "weight":6,"cost":5,"temp":10,"sustainability":6},
}

FAMILY_ICONS = {
    "steel":"🔩","aluminum":"🔘","cast iron":"⚫",
    "magnesium":"🔋","copper alloys":"🔶",
    "stainless steel":"✨","tin alloys":"◼️","other":"🔷",
}

PARAM_META = {
    "strength":      {"label":"Strength",      "unit":"MPa",        "icon":"💪","hint":"Higher → favours high yield strength", "col":"Yield_Strength_MPa", "higher":True},
    "weight":        {"label":"Weight",         "unit":"kg/m³",      "icon":"🪶","hint":"Higher → favours lighter alloys (low density)", "col":"Density_kg_m3", "higher":False},
    "cost":          {"label":"Cost",           "unit":"₹/kg",       "icon":"💰","hint":"Higher → favours economical alloys", "col":"Material_Cost_INR_per_kg", "higher":False},
    "temp":          {"label":"Temperature",    "unit":"°C",         "icon":"🌡","hint":"Higher → favours heat-resistant grades", "col":"Max_Service_Temperature_C", "higher":True},
    "sustainability":{"label":"Sustainability", "unit":"kgCO₂e/kg",  "icon":"🌱","hint":"Higher → favours lower embodied CO₂", "col":"Embodied_Carbon_kgCO2e_per_kg", "higher":False},
}

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SmartMat · Automotive Material Advisor",
    page_icon="🔩",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');

/* ── Typography & Global Reset ── */
html, body, [class*="css"], .stApp {
    font-family: 'Rajdhani', -apple-system, BlinkMacSystemFont, sans-serif !important;
    letter-spacing: 0.015em;
}

.stApp {
    background: #EEF3F8;
    color: #0B192C;
}

/* ── Header & Sidebar Toggle Visibility Fix ── */
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 2.4rem !important;
    padding: 0 !important;
    z-index: 100 !important;
}
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    z-index: 999999 !important;
    top: 0.5rem !important;
    left: 0.75rem !important;
    background: #091729 !important;
    color: #FFFFFF !important;
    border: 1.5px solid #1A395E !important;
    border-radius: 8px !important;
    padding: 0.35rem !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.3) !important;
}
[data-testid="collapsedControl"] svg {
    fill: #FFFFFF !important;
}
#MainMenu, footer {
    visibility: hidden;
}
.block-container {
    max-width: 1440px !important;
    padding-top: 0.6rem !important;
    padding-bottom: 2.2rem !important;
    padding-left: 1.8rem !important;
    padding-right: 1.8rem !important;
}

/* ── Sidebar Styles & Cards ── */
[data-testid="stSidebar"] {
    background: #091729 !important;
    border-right: 1px solid #162F4D;
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 1.0rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}
[data-testid="stSidebar"] * {
    font-family: 'Rajdhani', sans-serif !important;
    color: #D3E2F2 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-weight: 700 !important;
    letter-spacing: 0.03em;
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] label {
    font-weight: 700 !important;
    color: #8EB4D8 !important;
    font-size: 0.85rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Sidebar Cards */
.sb-card {
    background: #0F233B;
    border: 1px solid #1A395E;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 4px 14px rgba(0,0,0,0.22);
}

.sb-card-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 1.1rem;
    font-weight: 700;
    color: #FFFFFF !important;
    letter-spacing: 0.03em;
    margin-bottom: 0.2rem;
}

.sb-card-subtitle {
    font-size: 0.8rem;
    color: #7AA5CB !important;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.6rem;
}

/* Highlighted Action Card in Sidebar */
.sb-action-card-prompt {
    background: linear-gradient(145deg, #102C4E 0%, #0D2138 100%);
    border: 2px solid #00B4D8;
    border-radius: 12px;
    padding: 1.1rem;
    margin-bottom: 1rem;
    box-shadow: 0 0 18px rgba(0, 180, 216, 0.35);
    position: relative;
    animation: sb-pulse 2.8s infinite ease-in-out;
}

@keyframes sb-pulse {
    0%   { box-shadow: 0 0 12px rgba(0,180,216,0.30); border-color: #00B4D8; }
    50%  { box-shadow: 0 0 24px rgba(0,180,216,0.65); border-color: #38BDF8; }
    100% { box-shadow: 0 0 12px rgba(0,180,216,0.30); border-color: #00B4D8; }
}

.sb-action-card-done {
    background: linear-gradient(145deg, #0C2822 0%, #0A1C1A 100%);
    border: 1.5px solid #10B981;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.2);
}

.sb-badge-action {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #00B4D8;
    color: #061826 !important;
    font-weight: 800;
    font-size: 0.76rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.22rem 0.65rem;
    border-radius: 6px;
    margin-bottom: 0.6rem;
}

.sb-badge-done {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #10B981;
    color: #042217 !important;
    font-weight: 800;
    font-size: 0.74rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    margin-bottom: 0.5rem;
}

.sb-select-label {
    font-size: 0.84rem;
    font-weight: 700;
    color: #E2EBF5 !important;
    margin-top: 0.4rem;
    margin-bottom: 0.2rem;
    letter-spacing: 0.03em;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background: #132B47 !important;
    border: 1.5px solid #284F78 !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    border-radius: 8px !important;
}

[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:hover,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:focus-within {
    border-color: #00B4D8 !important;
}

/* ── Header Banner Card ── */
.sm-header {
    background: linear-gradient(135deg, #091729 0%, #102B4C 55%, #183C66 100%);
    border: 1px solid #204A75;
    border-radius: 14px;
    padding: 1.1rem 1.6rem;
    display: flex;
    align-items: center;
    gap: 1.3rem;
    margin-bottom: 1.1rem;
    box-shadow: 0 4px 20px rgba(9,23,41,0.18);
}
.sm-header-title {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 2.2rem;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: 0.03em;
    margin: 0;
    line-height: 1.1;
    text-transform: uppercase;
}
.sm-header-sub {
    color: #92B9DC;
    font-size: 0.92rem;
    font-weight: 600;
    margin: 0.2rem 0 0;
    letter-spacing: 0.02em;
}

/* ── Pipeline Step Bar ── */
.step-bar {
    display: flex;
    gap: 0.6rem;
    margin-bottom: 1.2rem;
    background: #FFFFFF;
    border: 1px solid #CFDEEB;
    border-radius: 12px;
    padding: 0.65rem 0.9rem;
    box-shadow: 0 2px 10px rgba(11,25,44,0.04);
}
.step-pip {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.35rem 0.85rem;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 700;
    color: #6C89A5;
    border: 1px solid transparent;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    transition: all 0.2s ease;
}
.step-pip.active {
    background: #E8F4FD;
    border-color: #0096C7;
    color: #00609C;
    box-shadow: 0 2px 8px rgba(0,150,199,0.14);
}
.step-pip.done {
    background: #EAF8F2;
    border-color: #10B981;
    color: #066746;
}
.step-dot {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.74rem;
    font-weight: 800;
    background: #D9E5F0;
    color: #4C6B86;
}
.step-pip.active .step-dot {
    background: #0096C7;
    color: #FFFFFF;
}
.step-pip.done .step-dot {
    background: #10B981;
    color: #FFFFFF;
}

/* ── General Cards & Sections ── */
.sm-card {
    background: #FFFFFF;
    border: 1px solid #D1DFEC;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 3px 14px rgba(11,25,44,0.05);
}
.sm-section {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1.25rem;
    font-weight: 700;
    color: #0B192C;
    margin: 0.8rem 0 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* ── Requirements & Slider Cards ── */
.req-row {
    background: #FFFFFF;
    border: 1.5px solid #D1DFEC;
    border-radius: 12px;
    padding: 0.85rem 1.1rem 0.5rem;
    margin-bottom: 0.65rem;
    box-shadow: 0 2px 10px rgba(11,25,44,0.03);
    transition: border-color 0.2s ease;
}
.req-row:hover {
    border-color: #90BFE6;
}
.req-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.2rem;
}
.req-label {
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700;
    font-size: 1.05rem;
    color: #0B192C;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
.req-hint {
    font-size: 0.82rem;
    font-weight: 600;
    color: #6C89A5;
    margin-bottom: 0.2rem;
}
.req-range {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #0077B6;
    font-weight: 700;
    background: #E8F4FD;
    border: 1px solid #BEE1F5;
    border-radius: 6px;
    padding: 0.15rem 0.55rem;
}

/* ── Material Rows & Badges ── */
.mat-row {
    background: #FFFFFF;
    border: 1.5px solid #D1DFEC;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 3px 12px rgba(11,25,44,0.04);
    transition: all 0.2s ease;
}
.mat-row:hover {
    box-shadow: 0 6px 18px rgba(11,25,44,0.08);
    border-color: #88BCE2;
}
.mat-row.selected {
    border: 2px solid #0096C7;
    background: #F2F9FD;
    box-shadow: 0 4px 16px rgba(0,150,199,0.18);
}
.mat-name {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1.2rem;
    font-weight: 700;
    color: #0B192C;
    letter-spacing: 0.02em;
}
.mat-family {
    font-size: 0.82rem;
    font-weight: 700;
    color: #6C89A5;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.score-track {
    height: 7px;
    background: #DFE8F2;
    border-radius: 4px;
    margin: 0.35rem 0;
    overflow: hidden;
}
.score-fill {
    height: 7px;
    border-radius: 4px;
    background: linear-gradient(90deg, #0096C7, #10B981);
}

.sbadge {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    min-width: 50px;
    background: #F3F7FA;
    border: 1px solid #D1DFEC;
    border-radius: 8px;
    padding: 0.25rem 0.4rem;
    margin: 0.12rem 0.1rem;
}
.sbadge-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    font-weight: 700;
    color: #084B83;
}
.sbadge-key {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.66rem;
    font-weight: 700;
    color: #6C89A5;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.rank-badge {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 0.9rem;
    flex-shrink: 0;
    font-family: 'Rajdhani', sans-serif !important;
}
.rank-1 { background: #FFB703; color: #2B1C00; box-shadow: 0 2px 8px rgba(255,183,3,0.35); }
.rank-2 { background: #94A3B8; color: #0F172A; }
.rank-3 { background: #D97706; color: #2B1000; }
.rank-n { background: #DFE8F2; color: #355370; }

.cmp-header {
    background: linear-gradient(135deg, #091729 0%, #16365C 100%);
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    color: #FFFFFF;
    display: flex;
    align-items: center;
    gap: 0.9rem;
    margin-bottom: 1.1rem;
    box-shadow: 0 4px 16px rgba(9,23,41,0.18);
}
.cmp-cell {
    background: #F8FAFD;
    border: 1px solid #D1DFEC;
    border-radius: 8px;
    padding: 0.45rem 0.7rem;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.88rem;
    font-weight: 600;
}
.cmp-win {
    background: #E4F9F1;
    border-color: #10B981;
    color: #066746;
    font-weight: 800;
}
.cmp-prop {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.95rem;
    color: #355370;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

/* Callout Info / Alert Boxes */
.infobox {
    background: #E8F4FD;
    border-left: 4px solid #0096C7;
    border-radius: 0 10px 10px 0;
    padding: 0.9rem 1.1rem;
    color: #0E365E;
    margin: 0.6rem 0;
    font-weight: 500;
}
.warnbox {
    background: #FFF9EB;
    border-left: 4px solid #F59E0B;
    border-radius: 0 10px 10px 0;
    padding: 0.9rem 1.1rem;
    color: #7D4F00;
    margin: 0.6rem 0;
    font-weight: 600;
}
.riskbox {
    background: #FEF2F2;
    border-left: 4px solid #EF4444;
    border-radius: 0 10px 10px 0;
    padding: 0.9rem 1.1rem;
    color: #8C1F1F;
    margin: 0.6rem 0;
    font-weight: 600;
}
.ecobox {
    background: #EAF8F2;
    border-left: 4px solid #10B981;
    border-radius: 0 10px 10px 0;
    padding: 0.9rem 1.1rem;
    color: #06543A;
    margin: 0.6rem 0;
    font-weight: 600;
}

.chip {
    display: inline-block;
    background: #EAF8F2;
    color: #066746;
    border: 1px solid #A4E5CC;
    border-radius: 999px;
    padding: 0.15rem 0.55rem;
    font-size: 0.78rem;
    font-weight: 700;
    margin: 0.12rem 0.12rem 0 0;
    letter-spacing: 0.02em;
}
.chip-blue {
    background: #E8F4FD;
    color: #065389;
    border-color: #BAE1F7;
}

/* Buttons */
div.stButton > button {
    border-radius: 9px;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.96rem !important;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    transition: all 0.2s ease;
}
div.stButton > button[kind="primary"] {
    background: #0077B6 !important;
    color: #FFFFFF !important;
    border: none !important;
    padding: 0.5rem 1.5rem !important;
    box-shadow: 0 2px 10px rgba(0,119,182,0.25);
}
div.stButton > button[kind="primary"]:hover {
    background: #0096C7 !important;
    box-shadow: 0 4px 16px rgba(0,150,199,0.4);
}
div.stButton > button[kind="secondary"] {
    background: #FFFFFF !important;
    color: #0B2B4E !important;
    border: 1.5px solid #CFDEEB !important;
}
div.stButton > button[kind="secondary"]:hover {
    border-color: #0096C7 !important;
    color: #0077B6 !important;
}


/* Sliders */
[data-testid="stSlider"] [data-testid="stSliderTrack"] > div:last-child {
    background: #0077B6 !important;
}
[data-testid="stSlider"] {
    padding-top: 0.1rem !important;
}

/* Number input */
[data-testid="stNumberInput"] input {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    font-weight: 700;
    border-radius: 8px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


# ── helpers ────────────────────────────────────────────────────────────────────

def fv(data:Any, *keys:str, default:Any="") -> Any:
    if not isinstance(data, dict): return default
    for k in keys:
        if k in data and data[k] is not None: return data[k]
    return default

def mat_name(item:dict) -> str:
    return str(fv(item,"Material_Name","material_name","name","material",default="Unknown"))

def mat_family(item:dict) -> str:
    return str(fv(item,"Material_Family","material_family","family",default="Other"))

def mat_score(item:dict, *keys:str) -> float:
    v = fv(item, *keys, default=0.0)
    try: return float(v)
    except: return 0.0

def mat_icon(item:dict) -> str:
    f = mat_family(item).lower()
    return next((ic for nm,ic in FAMILY_ICONS.items() if nm in f), FAMILY_ICONS["other"])

def ranked_items(payload) -> list:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    for k in ("recommendations","results","materials","ranked_results","data"):
        if isinstance(payload.get(k), list):
            return [x for x in payload[k] if isinstance(x, dict)]
    return []

def api_get(endpoint:str, params:dict):
    r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def fmt(v:Any) -> str:
    try:
        x = float(v)
        if abs(x) >= 1000: return f"{x:,.0f}"
        return f"{x:.1f}".rstrip("0").rstrip(".")
    except: return "—"


# ── session state ──────────────────────────────────────────────────────────────

def init():
    defs = {
        "page":1,"industry":"Automobile","component":None,
        "results":[],"meta":{},"compare_sel":[],"comparison":None,
        "ranges":{},"submitted":False,
    }
    for k,v in defs.items():
        st.session_state.setdefault(k,v)
    # init slider values
    for k in PARAM_META:
        st.session_state.setdefault(f"s_{k}", 5)
        st.session_state.setdefault(f"n_{k}", 5)

def set_component(c:str):
    st.session_state.component = c
    p = COMPONENT_PRESETS[c]
    for k,v in p.items():
        st.session_state[f"s_{k}"] = v
        st.session_state[f"n_{k}"] = v
    st.session_state.results=[]
    st.session_state.compare_sel=[]
    st.session_state.comparison=None
    st.session_state.submitted=False
    st.session_state.page=2

def cur_req() -> dict:
    return {k: int(st.session_state.get(f"s_{k}",5)) for k in PARAM_META}


# ── dataset quantile calculation for live ranges ──────────────────────────────

@st.cache_data
def _load_master_df():
    try:
        return pd.read_csv("SmartMat_Master.csv")
    except Exception:
        return None

def compute_ranges() -> dict:
    """
    Calculate dynamic engineering ranges for current slider weights.
    Prioritizes /ranges API; uses local Master CSV quantile calculation as instant fallback.
    """
    req = cur_req()
    comp = st.session_state.component or "Chassis / Frame"
    params = {
        **req,
        "component": comp,
        **{k: st.session_state.get(k, False)
           for k in ["must_recycle", "low_carbon", "eco_label", "bio_based"]}
    }

    try:
        data = api_get("/ranges", params)
        if isinstance(data, dict) and "ranges" in data and data["ranges"]:
            return data["ranges"]
    except Exception:
        pass

    # Instant dataset quantile fallback
    df = _load_master_df()
    if df is None or df.empty:
        return {}

    col_map = {
        "strength": ("Yield_Strength_MPa", True),
        "weight": ("Density_kg_m3", False),
        "cost": ("Material_Cost_INR_per_kg", False),
        "temp": ("Max_Service_Temperature_C", True),
        "sustainability": ("Embodied_Carbon_kgCO2e_per_kg", False),
    }

    out = {}
    for k, (col, higher_is_better) in col_map.items():
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue
        p = max(1, min(10, req.get(k, 5)))
        q_low = 0.10 + (p - 1) * 0.40 / 9.0
        q_high = 0.50 + (p - 1) * 0.50 / 9.0
        if not higher_is_better:
            q_low, q_high = 1.0 - q_high, 1.0 - q_low
        out[k] = {
            "favored_low": float(series.quantile(q_low)),
            "favored_high": float(series.quantile(q_high)),
            "dataset_min": float(series.min()),
            "dataset_max": float(series.max()),
        }
    return out


# ── callbacks — defined at module level so widget keys are stable ──────────────

def _sync_s_to_n(k:str):
    """Slider moved → update number box."""
    st.session_state[f"n_{k}"] = st.session_state[f"s_{k}"]

def _sync_n_to_s(k:str):
    """Number box changed → update slider."""
    st.session_state[f"s_{k}"] = int(st.session_state[f"n_{k}"])


# ── sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        # Brand Card
        st.markdown("""
        <div class="sb-card" style="margin-bottom:0.8rem">
            <div class="sb-card-header">
                <span style="font-size:1.5rem">🔩</span>
                <span style="font-size:1.3rem;font-weight:700;letter-spacing:0.04em">SMARTMAT</span>
            </div>
            <div class="sb-card-subtitle">Automotive Material Advisor</div>
            <div style="font-size:0.78rem;color:#8EB4D8;line-height:1.3">
                Automobile decision engine for automotive alloys & structural metals.
            </div>
        </div>
        """, unsafe_allow_html=True)

        comp = st.session_state.component
        has_comp = comp is not None

        # Highlighted Action Card for Component Selection
        if not has_comp:
            st.markdown("""
            <div class="sb-action-card-prompt">
                <div class="sb-badge-action">⚡ STEP 1 · ACTION REQUIRED</div>
                <div style="font-size:1.02rem;font-weight:700;color:#FFFFFF;text-transform:uppercase;letter-spacing:0.03em;margin-bottom:0.25rem">
                    Target Component
                </div>
                <div style="font-size:0.82rem;color:#BAE6FD;line-height:1.35;margin-bottom:0.6rem">
                    Select your vehicle component below to load baseline weights and unlock material matching.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="sb-action-card-done">
                <div class="sb-badge-done">✓ STEP 1 · CONFIGURED</div>
                <div style="font-size:0.82rem;color:#A7F3D0;text-transform:uppercase;letter-spacing:0.04em">Selected Component:</div>
                <div style="font-size:1.1rem;font-weight:700;color:#FFFFFF;letter-spacing:0.02em;margin-top:0.15rem">
                    🚗 {comp}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Input Card Container
        st.markdown('<div class="sb-card">', unsafe_allow_html=True)
        st.markdown('<div class="sb-select-label">🏭 DOMAIN</div>', unsafe_allow_html=True)
        st.selectbox("Domain", ["Automobile"], key="industry", label_visibility="collapsed")

        st.markdown('<div class="sb-select-label" style="margin-top:0.6rem">⚙️ COMPONENT PRESET</div>', unsafe_allow_html=True)
        comp_opts = list(COMPONENT_PRESETS)
        prev = st.session_state.component
        sel = st.selectbox(
            "Product type",
            ["— pick a product type —"] + comp_opts,
            index=(comp_opts.index(prev)+1 if prev in comp_opts else 0),
            label_visibility="collapsed",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if sel != "— pick a product type —" and sel != prev:
            set_component(sel)
            st.rerun()

        # Step 2: Requirements summary card (if component configured)
        if has_comp:
            done2 = st.session_state.submitted
            st.markdown(f"""
            <div class="sb-card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem">
                    <span style="font-size:0.88rem;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;color:{'#10B981' if done2 else '#90CDF4'}">
                        {'✓' if done2 else '02'} REQUIREMENTS
                    </span>
                    <span style="font-size:0.75rem;color:#8EB4D8">{'Evaluated' if done2 else 'Configuring'}</span>
                </div>
            """, unsafe_allow_html=True)
            if done2:
                for k, meta in PARAM_META.items():
                    v = st.session_state.get(f"s_{k}", 5)
                    st.markdown(f"<div style='font-size:0.84rem;margin:0.2rem 0;color:#D3E2F2'>{meta['icon']} <b>{meta['label']}</b>: {v}/10</div>", unsafe_allow_html=True)
            else:
                st.caption("Adjust engineering priority sliders on the main panel.")
            st.markdown('</div>', unsafe_allow_html=True)

        # Step 3: Results summary card (if submitted)
        if st.session_state.submitted:
            done3 = st.session_state.comparison is not None
            st.markdown(f"""
            <div class="sb-card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem">
                    <span style="font-size:0.88rem;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;color:{'#10B981' if done3 else '#90CDF4'}">
                        {'✓' if done3 else '03'} RANKED RESULTS
                    </span>
                    <span style="font-size:0.75rem;color:#8EB4D8">{len(st.session_state.results)} Grades</span>
                </div>
                <div style="font-size:0.82rem;color:#8EB4D8">Top automotive alloys scored against Pareto frontier.</div>
            </div>
            """, unsafe_allow_html=True)

        # System Info Card & Start Over
        st.markdown("""
        <div class="sb-card" style="margin-top:0.4rem">
            <div style="font-size:0.82rem;font-weight:700;color:#8EB4D8;letter-spacing:0.04em;text-transform:uppercase;margin-bottom:0.4rem">System Info</div>
            <div style="font-size:0.82rem;color:#C4D9ED;margin:0.2rem 0">📊 <b>Dataset:</b> 1,568 Automotive Grades</div>
            <div style="font-size:0.82rem;color:#C4D9ED;margin:0.2rem 0">🛡️ <b>Validation:</b> OEM Field-Validated</div>
            <div style="font-size:0.82rem;color:#C4D9ED;margin:0.2rem 0">🏎️ <b>Domain:</b> Automobile</div>
            <div style="font-size:0.82rem;color:#C4D9ED;margin:0.2rem 0">⚡ <b>AI Engine:</b> Qualcomm Cloud AI</div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.page > 1:
            if st.button("↺ Start New Evaluation", use_container_width=True):
                for k in ["page","component","results","meta","compare_sel","comparison","submitted","ranges"]:
                    st.session_state[k] = {"page":1,"component":None,"results":[],"meta":{},
                        "compare_sel":[],"comparison":None,"submitted":False,"ranges":{}}.get(k)
                st.rerun()


# ── step bar — visual indicator + click navigation ────────────────────────────

def render_stepbar():
    p = st.session_state.page
    has_comp    = st.session_state.component is not None
    has_results = bool(st.session_state.results) or st.session_state.submitted
    has_cmp     = st.session_state.comparison is not None

    steps = [
        (1, "Step 1", "Field & Product",  True),
        (2, "Step 2", "Requirements",     has_comp),
        (3, "Step 3", "Ranked Materials", has_results),
        (4, "Step 4", "Comparison",       has_cmp),
    ]

    # Inject per-step CSS so each st.button looks like the correct pill
    css_rules = []
    for n, step_num, step_name, enabled in steps:
        is_active = (n == p)
        is_done   = (n < p and enabled)
        sel = f'div[data-testid="stHorizontalBlock"] > div:nth-child({n}) button'
        if is_active:
            css_rules.append(
                f'{sel} {{ background:#0077B6 !important; color:#FFFFFF !important;'
                f'border:2px solid #0096C7 !important; box-shadow:0 4px 14px rgba(0,119,182,0.35) !important; }}'
            )
        elif is_done:
            css_rules.append(
                f'{sel} {{ background:#10B981 !important; color:#FFFFFF !important;'
                f'border:1.5px solid #10B981 !important; }}'
            )
        elif enabled:
            css_rules.append(
                f'{sel} {{ background:#FFFFFF !important; color:#355370 !important;'
                f'border:1.5px solid #C8D8E8 !important; }}'
            )
        else:
            css_rules.append(
                f'{sel} {{ background:#F0F4F8 !important; color:#9BB0C4 !important;'
                f'border:1.5px solid #DDE7EF !important; opacity:0.6 !important; }}'
            )

    st.markdown(
        f'<style>{"".join(css_rules)}'
        # General step-button overrides
        f' div[data-testid="stHorizontalBlock"] > div button {{'
        f'   font-family:\'Rajdhani\',sans-serif !important; font-weight:700 !important;'
        f'   font-size:0.88rem !important; text-transform:uppercase !important;'
        f'   letter-spacing:0.04em !important; border-radius:10px !important;'
        f'   padding:0.5rem 0.6rem !important; height:3rem !important;'
        f'   white-space:normal !important; line-height:1.15 !important;'
        f' }}'
        f'</style>',
        unsafe_allow_html=True,
    )

    cols = st.columns(4, gap="small")
    for idx, (n, step_num, step_name, enabled) in enumerate(steps):
        is_done = (n < p and enabled)
        prefix  = "✓ " if is_done else f"{n}  "
        label   = f"{prefix}{step_num}\n{step_name}"
        with cols[idx]:
            if st.button(
                label,
                key=f"nav_step_{n}",
                disabled=not enabled,
                use_container_width=True,
                help=(f"Go to {step_num}: {step_name}" if enabled
                      else "Step locked — complete previous stage first"),
            ):
                if enabled and n != p:
                    st.session_state.page = n
                    st.rerun()


# ── header ─────────────────────────────────────────────────────────────────────

def render_header():
    st.markdown("""
    <div class="sm-header">
        <div style="font-size:2.4rem;line-height:1">🔩</div>
        <div style="flex:1">
            <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap">
                <span class="sm-header-title">SmartMat</span>
                <span style="background:rgba(0,180,216,0.18);border:1px solid #00B4D8;color:#E0F2FE;font-size:0.76rem;font-weight:700;padding:0.18rem 0.55rem;border-radius:6px;text-transform:uppercase;letter-spacing:0.05em">
                    Automobile Domain
                </span>
                <span style="background:rgba(16,185,129,0.18);border:1px solid #10B981;color:#D1FAE5;font-size:0.76rem;font-weight:700;padding:0.18rem 0.55rem;border-radius:6px;text-transform:uppercase;letter-spacing:0.05em">
                    OEM Field-Validated
                </span>
                <span style="background:rgba(245,158,11,0.18);border:1px solid #F59E0B;color:#FEF3C7;font-size:0.76rem;font-weight:700;padding:0.18rem 0.55rem;border-radius:6px;text-transform:uppercase;letter-spacing:0.05em">
                    Qualcomm Cloud AI
                </span>
            </div>
            <div class="sm-header-sub">
                Automotive Material Selection Engine · 1568 Automotive Alloys &amp; Metals · OEM Field-Validated Dataset · Multi-Objective Pareto Optimization
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── PAGE 1: empty / onboarding ──────────────────────────────────────────────────

def page_empty():
    st.markdown("""
    <div class="sm-card" style="border:2px solid #BAE6FD;background:linear-gradient(180deg,#FFFFFF 0%,#F3F8FC 100%);">
        <div style="display:flex;align-items:center;gap:0.8rem;margin-bottom:0.6rem">
            <div style="background:#0077B6;color:white;width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:800">
                👉
            </div>
            <div>
                <div style="font-size:1.35rem;font-weight:700;color:#0B192C;text-transform:uppercase;letter-spacing:0.03em">
                    Step 1: Select Automotive Component to Begin
                </div>
                <div style="font-size:0.92rem;color:#4A6B8A;font-weight:600">
                    Look at the highlighted sidebar panel on the left to choose your product type, or click one of the quick presets below.
                </div>
            </div>
        </div>
        <div style="background:#E8F4FD;border-left:4px solid #0096C7;padding:0.75rem 1rem;border-radius:0 8px 8px 0;margin:0.8rem 0 1.2rem;font-size:0.9rem;color:#09385F;font-weight:600">
            💡 <b>How it works:</b> Choosing a component loads baseline engineering criteria (yield strength, heat tolerance, density, cost) and activates Pareto multi-objective scoring across the full automotive alloys dataset.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sm-section">⚡ Quick Start Component Presets</div>', unsafe_allow_html=True)
    st.caption("Click any automotive component below to immediately configure priorities:")

    # Quick selection card buttons
    row1 = st.columns(4)
    preset_items = list(COMPONENT_PRESETS.items())
    for idx, (comp_name, preset_weights) in enumerate(preset_items[:4]):
        with row1[idx]:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1.5px solid #D1DFEC;border-radius:12px;padding:0.9rem;margin-bottom:0.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.03)">
                <div style="font-size:1.05rem;font-weight:700;color:#0B192C;text-transform:uppercase;letter-spacing:0.02em">{comp_name}</div>
                <div style="font-size:0.8rem;color:#6A88A4;margin:0.25rem 0 0.5rem">Strength: {preset_weights['strength']}/10 · Weight: {preset_weights['weight']}/10</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Configure {comp_name.split()[0]}", key=f"quick_{idx}", use_container_width=True):
                set_component(comp_name)
                st.rerun()

    row2 = st.columns(4)
    for idx, (comp_name, preset_weights) in enumerate(preset_items[4:8]):
        with row2[idx]:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1.5px solid #D1DFEC;border-radius:12px;padding:0.9rem;margin-bottom:0.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.03)">
                <div style="font-size:1.05rem;font-weight:700;color:#0B192C;text-transform:uppercase;letter-spacing:0.02em">{comp_name}</div>
                <div style="font-size:0.8rem;color:#6A88A4;margin:0.25rem 0 0.5rem">Strength: {preset_weights['strength']}/10 · Temp: {preset_weights['temp']}/10</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Configure {comp_name.split()[0]}", key=f"quick_{idx+4}", use_container_width=True):
                set_component(comp_name)
                st.rerun()

    st.markdown('<div class="sm-section" style="margin-top:1.5rem">🏗️ Engineering Pipeline Overview</div>', unsafe_allow_html=True)
    c_p1, c_p2, c_p3 = st.columns(3)
    with c_p1:
        st.markdown("""
        <div class="sm-card" style="height:100%">
            <div style="font-size:1.8rem;margin-bottom:0.4rem">🛡️</div>
            <div style="font-size:1.05rem;font-weight:700;color:#0B192C;text-transform:uppercase;margin-bottom:0.3rem">
                1. Hard Constraint Filter
            </div>
            <div style="font-size:0.86rem;color:#4A6B8A;line-height:1.4">
                Screen automotive grades against component mechanical minimums and sustainability rules before ranking.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c_p2:
        st.markdown("""
        <div class="sm-card" style="height:100%">
            <div style="font-size:1.8rem;margin-bottom:0.4rem">📊</div>
            <div style="font-size:1.05rem;font-weight:700;color:#0B192C;text-transform:uppercase;margin-bottom:0.3rem">
                2. Multi-Objective Scoring
            </div>
            <div style="font-size:0.86rem;color:#4A6B8A;line-height:1.4">
                Weighs Yield Strength, Density, Raw Material Cost, Service Temperature, and Embodied CO₂ simultaneously.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c_p3:
        st.markdown("""
        <div class="sm-card" style="height:100%">
            <div style="font-size:1.8rem;margin-bottom:0.4rem">🤖</div>
            <div style="font-size:1.05rem;font-weight:700;color:#0B192C;text-transform:uppercase;margin-bottom:0.3rem">
                3. Qualcomm Cloud AI
            </div>
            <div style="font-size:0.86rem;color:#4A6B8A;line-height:1.4">
                Generates OEM manufacturing evidence, supply chain risk ratings, and trade-off insights.
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── PAGE 2: requirements (2-column layout, top sustainability, live ranges) ───

def page_requirements():
    # ── 1. Sustainability Presets on TOP ──
    st.markdown("""
    <div class="sm-card" style="padding:0.9rem 1.3rem;margin-bottom:0.9rem;background:linear-gradient(180deg,#FFFFFF 0%,#F6FAF8 100%);border:1.5px solid #A7F3D0">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.3rem;flex-wrap:wrap">
            <span style="font-size:1.1rem;font-weight:700;color:#06543A;text-transform:uppercase;letter-spacing:0.03em">
                🌱 Sustainability Presets & Hard Constraints
            </span>
            <span style="font-size:0.74rem;font-weight:700;background:#EAF8F2;color:#066746;padding:0.18rem 0.55rem;border-radius:6px;text-transform:uppercase;letter-spacing:0.04em">
                OEM Environmental Screening
            </span>
        </div>
        <div style="font-size:0.83rem;color:#4A6B8A;font-weight:600;margin-bottom:0.4rem">
            Checked constraints act as strict gatekeepers: candidate materials failing any checked requirement are eliminated before ranking.
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.checkbox("♻ Must be recyclable", key="must_recycle")
    with c2: st.checkbox("🌱 Low carbon footprint", key="low_carbon")
    with c3: st.checkbox("🏷 Eco label required", key="eco_label")
    with c4: st.checkbox("🌿 Bio-based acceptable", key="bio_based")

    # ── 2. Live Dataset Ranges ──
    ranges = compute_ranges()
    st.session_state.ranges = ranges

    # ── 3. Engineering Priorities in 2 Columns (adjusts in one screen) ──
    st.markdown('<div class="sm-section" style="margin-top:0.8rem">⚡ Engineering Priorities & Live Dataset Ranges</div>', unsafe_allow_html=True)
    st.caption("Each slider is a priority weight (1 = low, 10 = critical). Target dataset ranges update dynamically based on your chosen weights:")

    def render_param_card(k: str):
        meta = PARAM_META[k]
        r = ranges.get(k, {}) if isinstance(ranges, dict) else {}
        lo = r.get("favored_low", r.get("dataset_min", "—"))
        hi = r.get("favored_high", r.get("dataset_max", "—"))

        if lo != "—" and hi != "—":
            range_text = f"Target Range: {fmt(lo)} – {fmt(hi)} {meta['unit']}"
        else:
            range_text = f"Range: 1 – 10 ({meta['unit']})"

        st.markdown(
            f'<div class="req-row">'
            f'<div class="req-head">'
            f'<span class="req-label">{meta["icon"]} {meta["label"]}</span>'
            f'<span class="req-range">{range_text}</span>'
            f'</div>'
            f'<div class="req-hint">{meta["hint"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        sl_col, num_col = st.columns([3, 1])
        with sl_col:
            st.slider(
                meta["label"],
                min_value=1, max_value=10,
                key=f"s_{k}",
                label_visibility="collapsed",
                on_change=_sync_s_to_n,
                args=(k,),
            )
        with num_col:
            st.number_input(
                f"{meta['label']} value",
                min_value=1, max_value=10, step=1,
                key=f"n_{k}",
                label_visibility="collapsed",
                on_change=_sync_n_to_s,
                args=(k,),
            )

    col_left, col_right = st.columns(2, gap="medium")

    with col_left:
        render_param_card("strength")
        render_param_card("weight")
        render_param_card("cost")

    with col_right:
        render_param_card("temp")
        render_param_card("sustainability")

        # Action card
        st.markdown("""
        <div style="background:#FFFFFF;border:1.5px solid #BAE6FD;border-radius:12px;padding:0.9rem 1.1rem;margin-top:0.65rem;box-shadow:0 3px 12px rgba(0,119,182,0.06)">
            <div style="font-size:0.86rem;font-weight:700;color:#0077B6;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:0.5rem">
                🚀 Ready to Evaluate Materials?
            </div>
        """, unsafe_allow_html=True)
        btn_c1, btn_c2 = st.columns([1.2, 1.0])
        with btn_c1:
            if st.button("Find materials →", type="primary", use_container_width=True, key="find_mats_btn"):
                req = cur_req()
                params = {
                    **req,
                    "component": st.session_state.component,
                    **{k: st.session_state.get(k, False)
                       for k in ["must_recycle", "low_carbon", "eco_label", "bio_based"]}
                }
                try:
                    with st.spinner("Scoring automotive materials against your requirements…"):
                        payload = api_get("/recommend", params)
                    st.session_state.results = ranked_items(payload)
                    st.session_state.meta = payload if isinstance(payload, dict) else {}
                    st.session_state.compare_sel = []
                    st.session_state.comparison = None
                    st.session_state.submitted = True
                    st.session_state.page = 3
                    st.rerun()
                except requests.RequestException:
                    st.error("⚠ API not reachable. Ensure python api.py is running on port 5000.")
                except ValueError:
                    st.error("⚠ API returned unexpected data. Check backend logs.")
        with btn_c2:
            if st.button("↻ Refresh ranges", use_container_width=True, key="refresh_ranges_btn"):
                st.session_state.ranges = compute_ranges()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 4. HOW THIS WORKS section pushed below horizontally ──
    st.markdown('<div class="sm-section" style="margin-top:1.4rem">ℹ️ How This Decision Engine Works</div>', unsafe_allow_html=True)
    hw1, hw2, hw3 = st.columns(3, gap="medium")
    with hw1:
        st.markdown("""
        <div class="sm-card" style="height:100%">
            <div style="font-size:1.05rem;font-weight:700;color:#0B192C;text-transform:uppercase;margin-bottom:0.35rem">
                ⚙️ Multi-Objective Scoring
            </div>
            <div style="font-size:0.86rem;color:#4A6B8A;line-height:1.4">
                Each priority weight converts into a Pareto scoring coefficient. All 1568 automotive materials are evaluated across strength, density, cost, heat, and embodied carbon.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with hw2:
        st.markdown("""
        <div class="sm-card" style="height:100%">
            <div style="font-size:1.05rem;font-weight:700;color:#0B192C;text-transform:uppercase;margin-bottom:0.35rem">
                🌱 Sustainability & OEM Evidence
            </div>
            <div style="font-size:0.86rem;color:#4A6B8A;line-height:1.4">
                Evaluates verified embodied carbon (kgCO₂e/kg) from the SmartMat master dataset. Materials include OEM &amp; Tier-1 automotive production evidence where available.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with hw3:
        st.markdown("""
        <div class="sm-card" style="height:100%">
            <div style="font-size:1.05rem;font-weight:700;color:#0B192C;text-transform:uppercase;margin-bottom:0.35rem">
                🎯 Dynamic Range Targeting
            </div>
            <div style="font-size:0.86rem;color:#4A6B8A;line-height:1.4">
                Type any weight 1–10 in the box or move the slider. The target engineering range reflects the subset of alloys favored at that priority level in real time.
            </div>
        </div>
        """, unsafe_allow_html=True)



# ── PAGE 3: ranked results ─────────────────────────────────────────────────────

def page_results():
    results = st.session_state.results
    meta    = st.session_state.meta

    if fv(meta,"conflict",default=False):
        st.markdown(
            f'<div class="warnbox">⚠ {fv(meta,"conflict_message",default="Requirements conflict detected.")}</div>',
            unsafe_allow_html=True)

    req_col, res_col = st.columns([1.0, 2.2], gap="large")

    with req_col:
        st.markdown('<div class="sm-section">Active requirements</div>', unsafe_allow_html=True)
        req = cur_req()
        st.markdown('<div class="sm-card" style="padding:0.85rem 1rem">', unsafe_allow_html=True)
        for k, meta_p in PARAM_META.items():
            v      = req[k]
            filled = int(v / 10 * 10)
            bar_fill = "#0096C7"
            pct = v * 10
            st.markdown(
                f'<div style="margin:0.45rem 0">'
                f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.15rem">'
                f'    <span style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.88rem;color:#0B192C;text-transform:uppercase;letter-spacing:0.03em">{meta_p["icon"]} {meta_p["label"]}</span>'
                f'    <span style="font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;font-weight:700;color:#0096C7;background:#E8F4FD;padding:0.1rem 0.45rem;border-radius:5px">{v}/10</span>'
                f'  </div>'
                f'  <div style="height:6px;background:#DFE8F2;border-radius:3px;overflow:hidden">'
                f'    <div style="height:6px;width:{pct}%;background:linear-gradient(90deg,#0096C7,#10B981);border-radius:3px"></div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

        active_eco = [nm for nm, k in [
            ("Recyclable","must_recycle"),("Low carbon","low_carbon"),
            ("Eco label","eco_label"),("Bio-based","bio_based"),
        ] if st.session_state.get(k,False)]
        if active_eco:
            st.markdown('<div style="margin-top:0.6rem;font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.88rem;text-transform:uppercase;letter-spacing:0.03em;color:#0B192C">🌿 Hard Filters Active</div>',
                        unsafe_allow_html=True)
            chips_html = " ".join([f'<span class="chip">✓ {nm}</span>' for nm in active_eco])
            st.markdown(chips_html, unsafe_allow_html=True)

        st.markdown('<div style="height:0.8rem"></div>', unsafe_allow_html=True)
        if st.button("← Edit requirements", use_container_width=True, key="edit_req_btn"):
            st.session_state.page = 2
            st.session_state.submitted  = False
            st.session_state.results    = []
            st.session_state.compare_sel= []
            st.session_state.comparison = None
            st.rerun()

    with res_col:
        n = min(len(results), 5)
        st.markdown(
            f'<div class="sm-section">Top {n} materials for {st.session_state.component}</div>',
            unsafe_allow_html=True)
        st.caption("Select two materials with the Compare button, then click the confirm button to open the trade-off view.")

        for idx, item in enumerate(results[:5], 1):
            rank_cls = {1:"rank-1",2:"rank-2",3:"rank-3"}.get(idx,"rank-n")
            total    = max(0.0, min(100.0, mat_score(item,"Total_Score","total_score","score")))
            key_field= fv(item,"Material_Key","material_name","name")
            sel      = any(fv(x,"Material_Key","material_name","name") == key_field
                           for x in st.session_state.compare_sel)

            row_cls = "mat-row selected" if sel else "mat-row"
            st.markdown(f'<div class="{row_cls}">', unsafe_allow_html=True)

            c_info, c_sc, c_btn = st.columns([4.5, 4.0, 1.5])

            with c_info:
                st.markdown(
                    f'<span class="rank-badge {rank_cls}">#{idx}</span> '
                    f'<span class="mat-name">{mat_icon(item)} {mat_name(item)}</span><br>'
                    f'<span class="mat-family">{mat_family(item)}</span>',
                    unsafe_allow_html=True)
                ys   = mat_score(item,"Yield_Strength_MPa","yield_strength_mpa")
                den  = mat_score(item,"Density_kg_m3","density_kg_m3")
                cost = mat_score(item,"Material_Cost","material_cost","cost_inr_kg")
                eco  = mat_score(item,"Embodied_Carbon","embodied_carbon")
                chips = []
                if ys:   chips.append(f"<span class='chip chip-blue'>{ys:,.0f} MPa</span>")
                if den:  chips.append(f"<span class='chip chip-blue'>{den:,.0f} kg/m³</span>")
                if cost: chips.append(f"<span class='chip'>₹{cost:,.0f}/kg</span>")
                if eco:  chips.append(f"<span class='chip'>CO₂ {eco:.1f}</span>")
                if chips: st.markdown(" ".join(chips), unsafe_allow_html=True)

            with c_sc:
                st.markdown(
                    f'<div class="score-track"><div class="score-fill" style="width:{total}%"></div></div>',
                    unsafe_allow_html=True)
                st.caption(f"Overall {total:.1f}/100")
                badges = []
                for k, meta_p in PARAM_META.items():
                    sv = mat_score(item,
                                   f"{k.capitalize()}_Score", f"{k}_score",
                                   "Strength_Score" if k=="strength" else f"{k}_score")
                    badges.append(
                        f'<span class="sbadge">'
                        f'<span class="sbadge-val">{sv:.1f}</span>'
                        f'<span class="sbadge-key">{meta_p["label"][:3]}</span>'
                        f'</span>')
                st.markdown("".join(badges), unsafe_allow_html=True)

            with c_btn:
                btn_lbl = "✓ Added" if sel else "Compare"
                if st.button(btn_lbl, key=f"cmp_{idx}",
                             type="primary" if sel else "secondary"):
                    if sel:
                        st.session_state.compare_sel = [
                            x for x in st.session_state.compare_sel
                            if fv(x,"Material_Key","material_name","name") != key_field
                        ]
                    elif len(st.session_state.compare_sel) < 2:
                        st.session_state.compare_sel.append(item)
                    else:
                        st.toast("Remove one selection first — only 2 can be compared.")
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        count = len(st.session_state.compare_sel)
        if count:
            st.markdown(
                f'<div class="infobox" style="margin-top:.6rem">'
                f'<b>{count} of 2 selected</b> — '
                f'{"ready — click Compare below." if count==2 else "select one more."}'
                f'</div>',
                unsafe_allow_html=True)

        if count == 2:
            if st.button("⚖ Compare these two materials →", type="primary", use_container_width=True):
                sel0, sel1 = st.session_state.compare_sel
                params = {"mat1": mat_name(sel0), "mat2": mat_name(sel1),
                          "component": st.session_state.component, **cur_req()}
                try:
                    with st.spinner("Building trade-off analysis…"):
                        st.session_state.comparison = api_get("/compare", params)
                    st.session_state.page = 4
                    st.rerun()
                except requests.RequestException:
                    st.error("API not running. Run: python api.py")
                except ValueError:
                    st.error("API returned invalid data.")


# ── comparison helpers ─────────────────────────────────────────────────────────

def render_credibility(item:dict):
    india  = fv(item,"India_Availability","india_availability",  default="—")
    globe  = fv(item,"Global_Availability","global_availability",default="—")
    risk   = fv(item,"Procurement_Risk","procurement_risk",      default="—")
    used   = fv(item,"Industry_Examples","industry_examples",    default="")
    comps  = fv(item,"Common_Components","common_components",    default="")
    ev_st  = fv(item,"Evidence_Status","evidence_status",        default="")
    ev_src = fv(item,"Evidence_Source","evidence_source",        default="")

    st.markdown("""
    <div style="background:#EAF8F2;border-left:4px solid #10B981;border-radius:0 10px 10px 0;padding:0.65rem 1rem;margin-bottom:0.6rem">
        <span style="font-family:'Rajdhani',sans-serif;font-weight:700;font-size:0.92rem;color:#066746;text-transform:uppercase;letter-spacing:0.04em">✅ Verified Evidence</span>
    </div>""", unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    for col, lbl, val in [(m1, "India", india), (m2, "Global", globe), (m3, "Proc. Risk", risk)]:
        with col:
            color = "#066746" if val not in ("—", "", None) else "#999"
            st.markdown(
                f'<div style="background:#F3FAF7;border:1px solid #A4E5CC;border-radius:8px;padding:0.45rem 0.5rem;text-align:center">'
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.9rem;font-weight:700;color:{color}">{val}</div>'
                f'<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.7rem;font-weight:700;color:#7AAE95;text-transform:uppercase;letter-spacing:0.04em">{lbl}</div>'
                f'</div>', unsafe_allow_html=True)

    if used:
        st.markdown(f'<div style="margin-top:0.5rem;font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.82rem;color:#355370;text-transform:uppercase;letter-spacing:0.03em">Used by</div><div style="font-size:0.84rem;color:#1A3855">{used}</div>', unsafe_allow_html=True)
    if comps:
        st.markdown(f'<div style="margin-top:0.35rem;font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.82rem;color:#355370;text-transform:uppercase;letter-spacing:0.03em">Key Components</div><div style="font-size:0.84rem;color:#1A3855">{comps}</div>', unsafe_allow_html=True)
    if ev_st:
        st.markdown(f'<div style="margin-top:0.35rem;font-size:0.78rem;color:#6C89A5"><b>Evidence:</b> {ev_st}</div>', unsafe_allow_html=True)
    if ev_src:
        st.markdown(f'<div style="font-size:0.78rem;color:#6C89A5"><b>Source:</b> {ev_src}</div>', unsafe_allow_html=True)

def render_insights(item:dict):
    st.markdown("""
    <div style="background:#E8F4FD;border-left:4px solid #0096C7;border-radius:0 10px 10px 0;padding:0.65rem 1rem;margin-bottom:0.6rem">
        <span style="font-family:'Rajdhani',sans-serif;font-weight:700;font-size:0.92rem;color:#0E365E;text-transform:uppercase;letter-spacing:0.04em">🤖 AI Research Insights</span>
        <span style="font-size:0.72rem;color:#4A87B4;margin-left:0.5rem">Qualcomm Cloud AI · Decision Support</span>
    </div>""", unsafe_allow_html=True)

    insight_items = [
        ("OEM Usage",     ("Global_OEM_Usage","global_oem_usage"),     "#0077B6"),
        ("Industry Trend",("Industry_Trend","industry_trend"),         "#0077B6"),
        ("Why Preferred", ("Why_Preferred","why_preferred"),           "#0077B6"),
    ]
    for label, keys, color in insight_items:
        v = fv(item, *keys, default="")
        if v:
            st.markdown(
                f'<div style="margin:0.45rem 0">'
                f'<div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.8rem;color:#355370;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:0.1rem">{label}</div>'
                f'<div style="font-size:0.84rem;color:#1A3855;line-height:1.4">{v}</div>'
                f'</div>', unsafe_allow_html=True)

    risk = fv(item,"Risk_if_Wrong_Material","risk_if_wrong_material",default="")
    if risk:
        st.markdown(
            f'<div style="background:#FEF2F2;border-left:4px solid #EF4444;border-radius:0 10px 10px 0;padding:0.65rem 1rem;margin-top:0.5rem">'
            f'<div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.8rem;color:#8C1F1F;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:0.1rem">⚠ Risk if Wrong Material</div>'
            f'<div style="font-size:0.84rem;color:#7A1E1E;line-height:1.4">{risk}</div>'
            f'</div>', unsafe_allow_html=True)

    conf = str(fv(item,"Confidence","confidence",default="MEDIUM")).upper()
    conf_color = {"HIGH": "#10B981", "LOW": "#EF4444"}.get(conf, "#F59E0B")
    dot = "🟢" if conf=="HIGH" else "🔴" if conf=="LOW" else "🟡"
    st.markdown(
        f'<div style="margin-top:0.5rem;font-size:0.78rem;color:#6C89A5">'
        f'<b style="color:{conf_color}">{dot} Confidence: {conf}</b>'
        f'</div>', unsafe_allow_html=True)


# ── PAGE 4: comparison ─────────────────────────────────────────────────────────

def page_comparison():
    sel0, sel1 = st.session_state.compare_sel[:2]
    comparison  = st.session_state.comparison

    # Top nav row
    nav_c1, nav_c2 = st.columns([1, 5])
    with nav_c1:
        if st.button("← Back", use_container_width=True, key="cmp_back_btn"):
            st.session_state.page = 3
            st.session_state.comparison = None
            st.rerun()

    st.markdown(
        f'<div class="cmp-header">'
        f'<span style="font-size:1.8rem">⚖</span>'
        f'<div style="flex:1">'
        f'  <div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:1.3rem;color:#FFFFFF;text-transform:uppercase;letter-spacing:0.03em">'
        f'  {mat_name(sel0)[:28]} <span style="color:#5BA4CF">vs</span> {mat_name(sel1)[:28]}'
        f'  </div>'
        f'  <div style="font-size:0.82rem;color:#7DAAC8;margin-top:0.15rem">'
        f'  {st.session_state.component} · {st.session_state.industry} Domain'
        f'  </div>'
        f'</div></div>',
        unsafe_allow_html=True)

    items = ranked_items(comparison)
    left  = items[0] if len(items) >= 1 else sel0
    right = items[1] if len(items) >= 2 else sel1

    tab1, tab2, tab3 = st.tabs(["⚖ Trade-off", "🏭 Evidence & Insights", "🔗 Substitutes & Links"])

    with tab1:
        hc = st.columns([5,1,5])
        for col, item in ((hc[0],left),(hc[2],right)):
            with col:
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #D8E4EF;border-radius:12px;'
                    f'padding:.85rem 1rem;text-align:center">'
                    f'<div style="font-size:2.2rem">{mat_icon(item)}</div>'
                    f'<div style="font-weight:800;font-size:1.0rem;color:#0E1F35;margin:.2rem 0">{mat_name(item)}</div>'
                    f'<span class="chip chip-blue">{mat_family(item)}</span>'
                    f'</div>',
                    unsafe_allow_html=True)
        with hc[1]:
            st.markdown('<div style="text-align:center;padding-top:2rem;font-size:1rem;font-weight:800;color:#1A6FBF">VS</div>',
                        unsafe_allow_html=True)

        rows = [
            ("Strength score",       ("Strength_Score","strength_score"),           True),
            ("Weight score",         ("Weight_Score","weight_score"),               True),
            ("Cost score",           ("Cost_Score","cost_score"),                   True),
            ("Temperature score",    ("Temperature_Score","temperature_score"),     True),
            ("Sustainability score", ("Sustainability_Score","sustainability_score"),True),
            ("Overall score",        ("Total_Score","total_score","score"),         True),
            ("Material cost (₹/kg)", ("Material_Cost","material_cost","cost_inr_kg"),False),
            ("Embodied carbon",      ("Embodied_Carbon","embodied_carbon"),         False),
            ("India availability",   ("India_Availability","india_availability"),   False),
            ("Procurement risk",     ("Procurement_Risk","procurement_risk"),       False),
        ]

        # Build full comparison table as one HTML block for visible labels
        st.markdown('<div style="margin-top:1rem"></div>', unsafe_allow_html=True)

        # Compute wins before building HTML
        row_html_parts = []
        for label, keys, hi_better in rows:
            lv = fv(left,  *keys, default="—")
            rv = fv(right, *keys, default="—")
            lwin = rwin = False
            if hi_better:
                try: lwin = float(lv) > float(rv); rwin = float(rv) > float(lv)
                except: pass
            lv_d = fmt(lv) if lv != "—" else "—"
            rv_d = fmt(rv) if rv != "—" else "—"
            lcls = "cmp-win" if lwin else ""
            rcls = "cmp-win" if rwin else ""
            row_html_parts.append(
                f'<div style="display:grid;grid-template-columns:2fr 1.5fr 1.5fr;gap:0.4rem;'
                f'margin-bottom:0.35rem;align-items:center">'
                f'  <div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.88rem;'
                f'color:#355370;text-transform:uppercase;letter-spacing:0.02em">{label}</div>'
                f'  <div class="cmp-cell {lcls}">{lv_d}</div>'
                f'  <div class="cmp-cell {rcls}">{rv_d}</div>'
                f'</div>'
            )

        table_html = (
            f'<div style="background:#F8FAFD;border:1px solid #D1DFEC;border-radius:12px;padding:1rem 1.1rem">'
            f'  <div style="display:grid;grid-template-columns:2fr 1.5fr 1.5fr;gap:0.4rem;margin-bottom:0.5rem">'
            f'    <div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.78rem;color:#6C89A5;text-transform:uppercase;letter-spacing:0.05em">Property</div>'
            f'    <div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.78rem;color:#0096C7;text-transform:uppercase;letter-spacing:0.04em">{mat_name(left)[:20]}</div>'
            f'    <div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.78rem;color:#0096C7;text-transform:uppercase;letter-spacing:0.04em">{mat_name(right)[:20]}</div>'
            f'  </div>'
            f'  <div style="height:1px;background:#D1DFEC;margin-bottom:0.6rem"></div>'
            + "".join(row_html_parts) +
            f'</div>'
        )
        st.markdown(table_html, unsafe_allow_html=True)

        conclusion = fv(comparison,"conclusion","comparison_conclusion","Conclusion",default="")
        st.markdown(
            f'<div class="infobox" style="margin-top:1.2rem">'
            f'<div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.9rem;'
            f'text-transform:uppercase;letter-spacing:0.04em;margin-bottom:0.35rem">🎯 Engineering Conclusion</div>'
            f'<div style="font-size:0.9rem;line-height:1.5">'
            f'{conclusion or "Review the scores above and the Evidence tab for a complete picture."}'
            f'</div></div>',
            unsafe_allow_html=True)

    with tab2:
        cols = st.columns(2)
        for col, item in zip(cols,(left,right)):
            with col:
                st.markdown(
                    f'<div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:1.05rem;'
                    f'color:#0B192C;text-transform:uppercase;letter-spacing:0.03em;margin-bottom:0.6rem">'
                    f'{mat_icon(item)} {mat_name(item)}</div>',
                    unsafe_allow_html=True)
                render_credibility(item)
                st.markdown('<div style="height:0.6rem"></div>', unsafe_allow_html=True)
                render_insights(item)

    with tab3:
        st.markdown(
            '<div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:1.0rem;'
            'color:#0B192C;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:0.3rem">'
            '🔄 Substitute Candidates</div>',
            unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.84rem;color:#6C89A5;margin-bottom:0.6rem">Alternatives worth investigating — not guaranteed drop-in replacements. Verify independently.</div>', unsafe_allow_html=True)
        subs = comparison.get("substitutes",[]) if isinstance(comparison,dict) else []
        if subs:
            for s in subs:
                name   = s.get('material', s.get('name','Candidate'))
                reason = s.get('reason','Potential alternative')
                st.markdown(
                    f'<div style="background:#F3F7FA;border:1px solid #D1DFEC;border-radius:10px;padding:0.65rem 1rem;margin-bottom:0.4rem">'
                    f'<div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:0.92rem;color:#0B192C">{name}</div>'
                    f'<div style="font-size:0.82rem;color:#4A6B8A;margin-top:0.1rem">{reason}</div>'
                    f'</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="infobox">Substitute candidates are generated from the same material family when available from the ranking engine.</div>',
                unsafe_allow_html=True)

        st.markdown(
            '<div style="font-family:\'Rajdhani\',sans-serif;font-weight:700;font-size:1.0rem;'
            'color:#0B192C;text-transform:uppercase;letter-spacing:0.04em;margin:1rem 0 0.3rem">'
            '🔗 Reference Links</div>',
            unsafe_allow_html=True)
        for item in (left, right):
            nm  = mat_name(item)
            url = f"https://www.matweb.com/search/QuickText.aspx?SearchText={quote_plus(nm)}"
            st.markdown(
                f'<div style="background:#F3F7FA;border:1px solid #D1DFEC;border-radius:10px;padding:0.5rem 1rem;margin-bottom:0.4rem">'
                f'🔗 <a href="{url}" target="_blank" style="font-family:\'Rajdhani\',sans-serif;font-weight:700;color:#0077B6;text-decoration:none">View <b>{nm}</b> on MatWeb</a>'
                f'</div>', unsafe_allow_html=True)


# ── main ───────────────────────────────────────────────────────────────────────

init()
render_sidebar()
render_header()
render_stepbar()

p = st.session_state.page

if not st.session_state.component:
    page_empty()
elif p == 2:
    page_requirements()
elif p == 3:
    if st.session_state.results:
        page_results()
    else:
        # Results were cleared or not yet fetched — go back to requirements
        st.session_state.page = 2
        st.rerun()
elif p == 4 and st.session_state.comparison:
    page_comparison()
else:
    page_empty()
