"""
app_v3.py — Brasileirão Scout v3
Tema claro. Layout: hero + coluna principal (tabs) + painel fixo à direita.
Indicadores: taxa de vitória%, invicto%, gols/jogo, disciplina, presenças históricas.
"""
import base64
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ══════════════════════════════════════════════════════════════════
# Página
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Brasileirão Scout",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════
# Paleta — tema claro (diferente do v1 e v2)
# ══════════════════════════════════════════════════════════════════
VERDE    = "#009C3B"
AMARELO  = "#D97706"   # âmbar — legível em fundo claro
AZUL     = "#002776"
VERMELHO = "#DC2626"
CIANO    = "#0891B2"

FUNDO    = "#F1F5F9"
CARD     = "#FFFFFF"
CARD2    = "#F8FAFC"
BORDA    = "#E2E8F0"
TEXTO    = "#0F172A"
MUTED    = "#64748B"
HERO_BG  = f"linear-gradient(135deg, {AZUL} 0%, #004BB5 50%, {VERDE} 100%)"

# ══════════════════════════════════════════════════════════════════
# CSS — tema claro
# ══════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main {{
    background: {FUNDO} !important;
}}
.main .block-container {{
    padding: 1.25rem 1.5rem 2rem;
    max-width: 100%;
}}
[data-testid="stSidebar"] {{
    background: {CARD} !important;
    border-right: 1px solid {BORDA} !important;
}}
[data-testid="stSidebar"] * {{ color: {TEXTO} !important; }}
h1, h2, h3, h4 {{
    font-family: 'Barlow Condensed', sans-serif !important;
    font-weight: 800 !important;
    color: {TEXTO} !important;
}}
button[role="tab"] {{
    background: {CARD} !important;
    color: {MUTED} !important;
    border-radius: 8px 8px 0 0 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    border: 1px solid {BORDA} !important;
    border-bottom: none !important;
    margin-right: 4px !important;
    padding: 0.4rem 1rem !important;
}}
button[role="tab"][aria-selected="true"] {{
    background: {AZUL} !important;
    color: white !important;
    font-weight: 600 !important;
    border-color: {AZUL} !important;
}}
[data-testid="stTabsContent"] {{
    background: {CARD};
    border: 1px solid {BORDA};
    border-radius: 0 12px 12px 12px;
    padding: 1.25rem 1.4rem;
}}
[data-testid="stMetric"] {{
    background: {CARD};
    border: 1px solid {BORDA};
    border-radius: 12px;
    padding: 0.9rem 1rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
[data-testid="stMetricLabel"] > div {{
    color: {MUTED} !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-family: 'Inter', sans-serif;
}}
[data-testid="stMetricValue"] > div {{
    color: {TEXTO} !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 1.9rem !important;
    font-weight: 700 !important;
}}
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] {{
    background: {CARD} !important;
    border-color: {BORDA} !important;
    color: {TEXTO} !important;
}}
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: {FUNDO}; }}
::-webkit-scrollbar-thumb {{ background: {BORDA}; border-radius: 3px; }}
[data-testid="stCaptionContainer"] {{ color: {MUTED} !important; font-size: 0.72rem !important; }}
p, label, .stMarkdown, [data-testid="stMarkdownContainer"] {{ color: {TEXTO} !important; }}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# Escudos
# ══════════════════════════════════════════════════════════════════
_ASSETS = Path(__file__).parent / "assets"


def _lê(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


_SVG_SPRITE = _lê(_ASSETS / "escudos.svg") + _lê(_ASSETS / "escudos-b.svg")

ESCUDO_ID: dict[str, str] = {
    "Flamengo": "flamengo", "Fluminense": "fluminense", "Vasco": "vasco",
    "Corinthians": "corinthians", "Palmeiras": "palmeiras", "Santos": "santos",
    "Sao Paulo": "sao-paulo", "Internacional": "internacional", "Gremio": "gremio",
    "Cruzeiro": "cruzeiro", "Atletico-MG": "atletico-mg", "Athletico-PR": "atletico-pr",
    "Avai": "avai", "Chapecoense": "chapecoense", "Coritiba": "coritiba",
    "Figueirense": "figueirense", "Goias": "goias", "Joinville": "joinville",
    "Ponte Preta": "ponte-preta", "Sport": "sport",
    "America-MG": "america-mg", "Atletico-GO": "atletico-go", "Bahia": "bahia",
    "Botafogo-RJ": "botafogo", "Bragantino": "bragantino", "Ceara": "ceara",
    "Criciuma": "criciuma", "Nautico": "nautico", "Parana": "parana",
    "Paysandu": "paysandu", "Santa Cruz": "santa-cruz", "Vitoria": "vitoria",
}

_logos_dir = _ASSETS / "logos"
_LOGO_B64: dict[str, str] = {}
for _nome, _arquivo in {
    "Fortaleza": "fortaleza.svg", "Portuguesa": "portuguesa.svg",
    "Juventude": "juventude.svg", "Cuiaba": "cuiaba.svg",
    "Santo Andre": "santo-andre.png", "Sao Caetano": "sao-caetano.png",
    "Brasiliense": "brasiliense.png", "Ipatinga": "ipatinga.png",
}.items():
    _p = _logos_dir / _arquivo
    if _p.exists():
        _mime = "image/svg+xml" if _arquivo.endswith(".svg") else "image/png"
        _LOGO_B64[_nome] = f"data:{_mime};base64,{base64.b64encode(_p.read_bytes()).decode()}"

LOGO_URL: dict[str, str] = {
    "Guarani": "https://upload.wikimedia.org/wikipedia/commons/0/04/Guarani_Futebol_Clube_logo.svg",
    "CSA": "https://upload.wikimedia.org/wikipedia/commons/f/fa/Centro_Sportivo_Alagoano_logo.png",
    "America-RN": "https://upload.wikimedia.org/wikipedia/commons/f/f3/Am%C3%A9rica_Futebol_Clube_%28Natal%2C_Rio_Grande_do_Norte%29_logo.svg",
}

FALLBACK_BADGE: dict[str, tuple[str, str, str]] = {
    "Barueri": ("BAR", "#003399", "#ffffff"),
    "Gremio Prudente": ("GRP", "#0033cc", "#ffffff"),
}

_BADGE_S = (
    "display:inline-flex;align-items:center;justify-content:center;"
    "border-radius:50%;font-weight:800;letter-spacing:0.02em;"
    "vertical-align:middle;flex-shrink:0;"
)


def escudo_html(clube: str, size: int = 22) -> str:
    s = str(size)
    css = "vertical-align:middle;margin-right:6px;flex-shrink:0;object-fit:contain;"
    if svg_id := ESCUDO_ID.get(clube):
        return f'<svg width="{s}" height="{s}" style="{css}"><use href="#{svg_id}"/></svg>'
    if uri := _LOGO_B64.get(clube):
        return f'<img src="{uri}" width="{s}" height="{s}" style="{css}" />'
    if url := LOGO_URL.get(clube):
        return f'<img src="{url}" width="{s}" height="{s}" style="{css}" />'
    if fb := FALLBACK_BADGE.get(clube):
        sigla, bg, fg = fb
        fs = max(5, size // 4)
        return (f'<span style="{_BADGE_S}width:{s}px;height:{s}px;'
                f'font-size:{fs}px;background:{bg};color:{fg};margin-right:6px;">'
                f'{sigla}</span>')
    abbr = "".join(w[0] for w in clube.split()[:2]).upper()
    fs = max(5, size // 4)
    return (f'<span style="{_BADGE_S}width:{s}px;height:{s}px;'
            f'font-size:{fs}px;background:{BORDA};color:{MUTED};margin-right:6px;">'
            f'{abbr}</span>')


# ══════════════════════════════════════════════════════════════════
# Banco de dados
# ══════════════════════════════════════════════════════════════════
@st.cache_resource
def _con():
    con = duckdb.connect()
    con.execute("ATTACH 'brasileirao.duckdb' (READ_ONLY)")
    con.execute("USE brasileirao")
    return con


@st.cache_data
def _q(_con, sql: str) -> pd.DataFrame:
    return _con.execute(sql).df()


con = _con()

# ══════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════
_todas_temp = _q(con, "SELECT DISTINCT temporada FROM marts.classificacao ORDER BY temporada DESC")["temporada"].tolist()

with st.sidebar:
    st.markdown(
        f'<div style="padding:0.5rem 0 0.75rem;">'
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.9rem;'
        f'font-weight:800;color:{AZUL};line-height:1.1;">'
        f'<span style="color:{VERDE};">BRASI</span>LEIRÃO</div>'
        f'<div style="font-size:0.65rem;color:{MUTED};text-transform:uppercase;'
        f'letter-spacing:0.12em;margin-top:3px;">Scout · 2003 – 2024</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    temporada = st.selectbox("Temporada", _todas_temp, index=0, key="season")

# ══════════════════════════════════════════════════════════════════
# Dados
# ══════════════════════════════════════════════════════════════════
df_cl = _q(con, f"SELECT * FROM marts.classificacao WHERE temporada = {temporada} ORDER BY posicao")
df_mv = _q(con, f"SELECT * FROM marts.mandante_visitante WHERE temporada = {temporada}")
df_cart = _q(con, f"SELECT * FROM marts.cartoes_clube WHERE temporada = {temporada} ORDER BY amarelos_por_jogo DESC")

# Métricas derivadas (calculadas em pandas)
df_cl = df_cl.copy()
df_cl["taxa_vitoria"]  = (df_cl["vitorias"] / df_cl["jogos"] * 100).round(1)
df_cl["taxa_empate"]   = (df_cl["empates"]  / df_cl["jogos"] * 100).round(1)
df_cl["taxa_derrota"]  = (df_cl["derrotas"] / df_cl["jogos"] * 100).round(1)
df_cl["invicto_pct"]   = ((df_cl["vitorias"] + df_cl["empates"]) / df_cl["jogos"] * 100).round(1)
df_cl["gols_pro_jogo"] = (df_cl["gols_pro"]    / df_cl["jogos"]).round(2)
df_cl["gols_def_jogo"] = (df_cl["gols_contra"] / df_cl["jogos"]).round(2)

# Dados históricos
df_hist = _q(con, "SELECT temporada, clube, posicao, vitorias, jogos FROM marts.classificacao ORDER BY temporada, posicao")
df_presenca = df_hist.groupby("clube")["temporada"].count().reset_index()
df_presenca.columns = ["clube", "temporadas"]
df_presenca = df_presenca.sort_values("temporadas", ascending=False)

df_mv_hist = _q(con, "SELECT * FROM marts.mandante_visitante ORDER BY temporada")
df_mv_hist = df_mv_hist.copy()
df_mv_hist["pct_m"] = df_mv_hist["pct_mandante"].round(1)
df_mv_hist["pct_e"] = df_mv_hist["pct_empate"].round(1)
df_mv_hist["pct_v"] = df_mv_hist["pct_visitante"].round(1)

n_cl = len(df_cl)

# ══════════════════════════════════════════════════════════════════
# SVG sprite hidden
# ══════════════════════════════════════════════════════════════════
st.markdown(f'<div style="display:none;">{_SVG_SPRITE}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# Hero banner — Campeão × Lanterna
# ══════════════════════════════════════════════════════════════════
cam = df_cl[df_cl["posicao"] == 1].iloc[0] if not df_cl.empty else None
reb = df_cl[df_cl["posicao"] == n_cl].iloc[0] if not df_cl.empty else None

if cam is not None and reb is not None:
    logo_cam = escudo_html(cam["clube"], 36)
    logo_reb = escudo_html(reb["clube"], 36)
    hero = (
        f'<div style="background:{HERO_BG};border-radius:16px;padding:1.4rem 2rem;'
        f'margin-bottom:1.4rem;display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="display:flex;align-items:center;gap:1rem;">'
        f'{logo_cam}'
        f'<div>'
        f'<div style="font-size:0.65rem;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:0.1em;">🏆 Campeão</div>'
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.6rem;font-weight:800;color:white;">{cam["clube"]}</div>'
        f'<div style="font-size:0.8rem;color:rgba(255,255,255,0.75);margin-top:2px;">'
        f'{int(cam["pontos"])} pts · {cam["taxa_vitoria"]:.0f}% vitórias · Invicto {cam["invicto_pct"]:.0f}%'
        f'</div></div></div>'
        f'<div style="display:flex;flex-direction:column;align-items:center;gap:0.4rem;">'
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:0.65rem;'
        f'color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:0.12em;">Temporada</div>'
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:2.5rem;font-weight:800;color:#FFDF00;">{temporada}</div>'
        f'<div style="font-size:0.7rem;color:rgba(255,255,255,0.4);">{n_cl} clubes</div>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:1rem;">'
        f'<div style="text-align:right;">'
        f'<div style="font-size:0.65rem;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:0.1em;">📉 Lanterna</div>'
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.6rem;font-weight:800;color:rgba(255,255,255,0.75);">{reb["clube"]}</div>'
        f'<div style="font-size:0.8rem;color:rgba(255,255,255,0.5);margin-top:2px;">'
        f'{int(reb["pontos"])} pts · {reb["taxa_vitoria"]:.0f}% vitórias · Invicto {reb["invicto_pct"]:.0f}%'
        f'</div></div>'
        f'{logo_reb}'
        f'</div>'
        f'</div>'
    )
    st.markdown(hero, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# Layout: coluna principal (tabs) + painel direito fixo
# ══════════════════════════════════════════════════════════════════
col_main, col_right = st.columns([13, 7])

# ── Painel direito ────────────────────────────────────────────────
with col_right:

    # Top Aproveitamento
    st.markdown(
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.1rem;'
        f'font-weight:700;color:{TEXTO};text-transform:uppercase;letter-spacing:0.06em;'
        f'margin-bottom:0.5rem;">🏅 Top Aproveitamento</div>',
        unsafe_allow_html=True,
    )
    top5_tv = df_cl.nlargest(5, "taxa_vitoria")
    rows_tv = ""
    for _, r in top5_tv.iterrows():
        logo = escudo_html(r["clube"], 26)
        bar_w = int(r["taxa_vitoria"] * 0.95)
        rows_tv += (
            f'<div style="display:flex;align-items:center;padding:0.5rem 0;border-bottom:1px solid {BORDA};">'
            f'<div style="flex:1;min-width:0;display:flex;align-items:center;">'
            f'{logo}'
            f'<div style="min-width:0;">'
            f'<div style="font-weight:600;font-size:0.85rem;color:{TEXTO};white-space:nowrap;">{r["clube"]}</div>'
            f'<div style="height:4px;background:{BORDA};border-radius:2px;margin-top:3px;width:100px;">'
            f'<div style="height:4px;background:{VERDE};border-radius:2px;width:{bar_w}px;"></div>'
            f'</div></div></div>'
            f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.15rem;font-weight:700;color:{VERDE};white-space:nowrap;margin-left:0.5rem;">{r["taxa_vitoria"]:.0f}%</div>'
            f'</div>'
        )
    st.markdown(
        f'<div style="background:{CARD};border:1px solid {BORDA};border-radius:14px;'
        f'padding:1rem 1.1rem;margin-bottom:1rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
        + rows_tv + '</div>',
        unsafe_allow_html=True,
    )

    # Melhor Defesa
    st.markdown(
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.1rem;'
        f'font-weight:700;color:{TEXTO};text-transform:uppercase;letter-spacing:0.06em;'
        f'margin-bottom:0.5rem;">🛡️ Melhor Defesa</div>',
        unsafe_allow_html=True,
    )
    top5_def = df_cl.nsmallest(5, "gols_def_jogo")
    max_def = df_cl["gols_def_jogo"].max()
    rows_def = ""
    for _, r in top5_def.iterrows():
        logo = escudo_html(r["clube"], 26)
        bar_w = int((1 - r["gols_def_jogo"] / max_def) * 95) if max_def > 0 else 0
        rows_def += (
            f'<div style="display:flex;align-items:center;padding:0.5rem 0;border-bottom:1px solid {BORDA};">'
            f'<div style="flex:1;min-width:0;display:flex;align-items:center;">'
            f'{logo}'
            f'<div style="min-width:0;">'
            f'<div style="font-weight:600;font-size:0.85rem;color:{TEXTO};white-space:nowrap;">{r["clube"]}</div>'
            f'<div style="height:4px;background:{BORDA};border-radius:2px;margin-top:3px;width:100px;">'
            f'<div style="height:4px;background:{AZUL};border-radius:2px;width:{bar_w}px;"></div>'
            f'</div></div></div>'
            f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.05rem;font-weight:700;color:{AZUL};white-space:nowrap;margin-left:0.5rem;">'
            f'{r["gols_def_jogo"]:.2f}<span style="font-size:0.65rem;font-weight:400;color:{MUTED};"> g/j</span></div>'
            f'</div>'
        )
    st.markdown(
        f'<div style="background:{CARD};border:1px solid {BORDA};border-radius:14px;'
        f'padding:1rem 1.1rem;margin-bottom:1rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
        + rows_def + '</div>',
        unsafe_allow_html=True,
    )

    # Vantagem de Mando
    if not df_mv.empty:
        mv = df_mv.iloc[0]
        pct_m = mv["pct_mandante"]
        pct_e = mv["pct_empate"]
        pct_v = mv["pct_visitante"]
        st.markdown(
            f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.1rem;'
            f'font-weight:700;color:{TEXTO};text-transform:uppercase;letter-spacing:0.06em;'
            f'margin-bottom:0.5rem;">🏟️ Mando de Campo</div>',
            unsafe_allow_html=True,
        )
        mando = (
            f'<div style="background:{CARD};border:1px solid {BORDA};border-radius:14px;'
            f'padding:1rem 1.1rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
            f'<div style="display:flex;border-radius:8px;overflow:hidden;height:10px;margin-bottom:0.75rem;">'
            f'<div style="flex:{pct_m:.0f};background:{VERDE};"></div>'
            f'<div style="flex:{pct_e:.0f};background:{AMARELO};"></div>'
            f'<div style="flex:{pct_v:.0f};background:{VERMELHO};"></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;font-size:0.78rem;">'
            f'<span style="color:{VERDE};font-weight:600;">⌂ {pct_m:.0f}%</span>'
            f'<span style="color:{MUTED};">Empate {pct_e:.0f}%</span>'
            f'<span style="color:{VERMELHO};font-weight:600;">✈ {pct_v:.0f}%</span>'
            f'</div></div>'
        )
        st.markdown(mando, unsafe_allow_html=True)

# ── Coluna principal — tabs ───────────────────────────────────────
with col_main:
    tab_res, tab_ef, tab_disc, tab_hist = st.tabs([
        "⚽  Resultados por Clube",
        "📊  Eficiência",
        "🟨  Disciplina",
        "📅  Histórico",
    ])

    # ── Tab 1: Resultados por Clube ──────────────────────────────
    with tab_res:
        st.markdown(
            f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.3rem;'
            f'font-weight:700;color:{TEXTO};margin-bottom:0.75rem;">Clubes · {temporada}</div>',
            unsafe_allow_html=True,
        )
        # cabeçalho
        hdr = (
            f'<div style="display:grid;grid-template-columns:2fr 0.6fr 0.8fr 0.8fr 0.8fr 0.8fr;'
            f'gap:0.5rem;padding:0.4rem 0.75rem;background:{FUNDO};border-radius:8px;'
            f'font-size:0.65rem;text-transform:uppercase;letter-spacing:0.07em;'
            f'color:{MUTED};font-weight:600;margin-bottom:4px;">'
            f'<div>Clube</div>'
            f'<div style="text-align:center;">Pos</div>'
            f'<div style="text-align:center;">V%</div>'
            f'<div style="text-align:center;">Inv%</div>'
            f'<div style="text-align:center;">G+/J</div>'
            f'<div style="text-align:center;">G−/J</div>'
            f'</div>'
        )
        rows_cl = ""
        for _, r in df_cl.iterrows():
            pos = int(r["posicao"])
            if pos <= 4:
                pos_cor, pos_bg = VERDE, "rgba(0,156,59,0.12)"
            elif pos <= 6:
                pos_cor, pos_bg = CIANO, "rgba(8,145,178,0.12)"
            elif pos > n_cl - 4:
                pos_cor, pos_bg = VERMELHO, "rgba(220,38,38,0.12)"
            else:
                pos_cor, pos_bg = MUTED, "transparent"

            logo = escudo_html(r["clube"], 20)
            rows_cl += (
                f'<div style="display:grid;grid-template-columns:2fr 0.6fr 0.8fr 0.8fr 0.8fr 0.8fr;'
                f'gap:0.5rem;padding:0.55rem 0.75rem;border-bottom:1px solid {BORDA};align-items:center;">'
                f'<div style="display:flex;align-items:center;">'
                f'{logo}'
                f'<span style="font-weight:600;font-size:0.85rem;color:{TEXTO};white-space:nowrap;">{r["clube"]}</span>'
                f'</div>'
                f'<div style="text-align:center;">'
                f'<span style="background:{pos_bg};color:{pos_cor};font-weight:700;'
                f'font-size:0.8rem;padding:2px 7px;border-radius:12px;">{pos}°</span>'
                f'</div>'
                f'<div style="text-align:center;font-family:\'Barlow Condensed\',sans-serif;'
                f'font-size:0.95rem;font-weight:700;color:{VERDE};">{r["taxa_vitoria"]:.0f}%</div>'
                f'<div style="text-align:center;font-family:\'Barlow Condensed\',sans-serif;'
                f'font-size:0.95rem;font-weight:600;color:{AZUL};">{r["invicto_pct"]:.0f}%</div>'
                f'<div style="text-align:center;font-family:\'Barlow Condensed\',sans-serif;'
                f'font-size:0.95rem;font-weight:600;color:{TEXTO};">{r["gols_pro_jogo"]:.2f}</div>'
                f'<div style="text-align:center;font-family:\'Barlow Condensed\',sans-serif;'
                f'font-size:0.95rem;font-weight:600;color:{MUTED};">{r["gols_def_jogo"]:.2f}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div style="background:{CARD};border:1px solid {BORDA};border-radius:12px;'
            f'overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
            + hdr + rows_cl + '</div>',
            unsafe_allow_html=True,
        )
        st.caption("V% = % vitórias · Inv% = % jogos sem derrota · G+/J = gols marcados/jogo · G−/J = gols sofridos/jogo")

    # ── Tab 2: Eficiência ────────────────────────────────────────
    with tab_ef:
        c1, c2 = st.columns(2)

        with c1:
            df_ef = df_cl.sort_values("taxa_vitoria", ascending=True)
            fig_tv = go.Figure()
            fig_tv.add_trace(go.Bar(
                y=df_ef["clube"],
                x=df_ef["taxa_vitoria"],
                orientation="h",
                marker=dict(
                    color=df_ef["taxa_vitoria"],
                    colorscale=[[0.0, VERMELHO], [0.5, AMARELO], [1.0, VERDE]],
                    showscale=False,
                    line=dict(color="rgba(0,0,0,0)", width=0),
                ),
                text=df_ef["taxa_vitoria"].apply(lambda x: f"{x:.0f}%"),
                textposition="outside",
                textfont=dict(size=10, color=TEXTO),
                hovertemplate="<b>%{y}</b><br>Taxa de vitória: %{x:.1f}%<extra></extra>",
                showlegend=False,
            ))
            fig_tv.update_layout(
                title=dict(text=f"Taxa de Vitória — {temporada}", font=dict(size=14, color=TEXTO)),
                xaxis=dict(
                    title="% vitórias",
                    range=[0, df_ef["taxa_vitoria"].max() + 10],
                    gridcolor=BORDA,
                    tickfont=dict(color=MUTED),
                ),
                yaxis=dict(tickfont=dict(size=9, color=TEXTO), gridcolor="rgba(0,0,0,0)"),
                height=460,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=TEXTO, family="Inter, sans-serif"),
                margin=dict(l=10, r=50, t=40, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig_tv, width="stretch")

        with c2:
            # Scatter: gols_pro_jogo × invicto_pct — bolha = pontos
            fig_inv = go.Figure()
            fig_inv.add_trace(go.Scatter(
                x=df_cl["gols_pro_jogo"],
                y=df_cl["invicto_pct"],
                mode="markers+text",
                showlegend=False,
                marker=dict(
                    size=df_cl["pontos"] / df_cl["pontos"].max() * 32 + 10,
                    color=df_cl["posicao"],
                    colorscale=[[0.0, VERDE], [0.5, "#D97706"], [1.0, VERMELHO]],
                    cmin=1, cmax=n_cl,
                    colorbar=dict(
                        title=dict(text="Posição", side="right"),
                        tickvals=[1, n_cl // 2, n_cl],
                        ticktext=[f"1°", f"{n_cl // 2}°", f"{n_cl}°"],
                        thickness=12,
                        tickfont=dict(color=MUTED, size=10),
                    ),
                    opacity=0.85,
                    line=dict(color="white", width=1.5),
                    showscale=True,
                ),
                text=df_cl["clube"].str[:8],
                textposition="top center",
                textfont=dict(size=8, color=TEXTO),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Gols marcados/jogo: %{x:.2f}<br>"
                    "Invicto: %{y:.1f}%<br>"
                    "Pontos: %{customdata[1]}<br>"
                    "Posição: %{customdata[2]}°<extra></extra>"
                ),
                customdata=df_cl[["clube", "pontos", "posicao"]].values,
            ))
            fig_inv.update_layout(
                title=dict(text=f"Ataque × Invencibilidade — {temporada}", font=dict(size=14, color=TEXTO)),
                xaxis=dict(title="Gols marcados por jogo", gridcolor=BORDA, tickfont=dict(color=MUTED)),
                yaxis=dict(title="Invicto (%)", gridcolor=BORDA, tickfont=dict(color=MUTED)),
                height=460,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(241,245,249,0.6)",
                font=dict(color=TEXTO, family="Inter, sans-serif"),
                margin=dict(l=10, r=60, t=40, b=20),
            )
            st.plotly_chart(fig_inv, width="stretch")

    # ── Tab 3: Disciplina ────────────────────────────────────────
    with tab_disc:
        if df_cart.empty:
            st.info("Dados de cartões indisponíveis para esta temporada (cobertura: 2014–2024).")
        else:
            c1, c2 = st.columns(2)

            with c1:
                fig_disc = go.Figure()
                fig_disc.add_trace(go.Scatter(
                    x=df_cart["amarelos_por_jogo"],
                    y=df_cart["vermelhos_por_jogo"],
                    mode="markers+text",
                    showlegend=False,
                    marker=dict(
                        size=14,
                        color=df_cart["amarelos"],
                        colorscale=[[0.0, VERDE], [0.5, "#D97706"], [1.0, VERMELHO]],
                        colorbar=dict(
                            title=dict(text="Amarelos<br>Total", side="right"),
                            thickness=12,
                            tickfont=dict(color=MUTED, size=10),
                        ),
                        opacity=0.85,
                        line=dict(color="white", width=1.5),
                        showscale=True,
                    ),
                    text=df_cart["clube"].str[:8],
                    textposition="top center",
                    textfont=dict(size=8, color=TEXTO),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Amarelos/jogo: %{x:.2f}<br>"
                        "Vermelhos/jogo: %{y:.3f}<br>"
                        "Total amarelos: %{customdata[1]}<br>"
                        "Total vermelhos: %{customdata[2]}<extra></extra>"
                    ),
                    customdata=df_cart[["clube", "amarelos", "vermelhos"]].values,
                ))
                fig_disc.update_layout(
                    title=dict(text=f"Mapa de Disciplina — {temporada}", font=dict(size=14, color=TEXTO)),
                    xaxis=dict(title="Amarelos por jogo", gridcolor=BORDA, tickfont=dict(color=MUTED)),
                    yaxis=dict(title="Vermelhos por jogo", gridcolor=BORDA, tickfont=dict(color=MUTED)),
                    height=400,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(241,245,249,0.6)",
                    font=dict(color=TEXTO, family="Inter, sans-serif"),
                    margin=dict(l=10, r=60, t=40, b=20),
                )
                st.plotly_chart(fig_disc, width="stretch")

            with c2:
                top_disc = df_cart.nsmallest(10, "amarelos_por_jogo").sort_values("amarelos_por_jogo", ascending=False)
                fig_am = go.Figure()
                fig_am.add_trace(go.Bar(
                    y=top_disc["clube"],
                    x=top_disc["amarelos_por_jogo"],
                    orientation="h",
                    marker=dict(
                        color="#D97706",
                        line=dict(color="rgba(0,0,0,0)", width=0),
                    ),
                    text=top_disc["amarelos_por_jogo"].apply(lambda x: f"{x:.2f}"),
                    textposition="outside",
                    textfont=dict(size=10, color=TEXTO),
                    hovertemplate="<b>%{y}</b><br>Amarelos/jogo: %{x:.2f}<extra></extra>",
                    showlegend=False,
                    name="Amarelos/jogo",
                ))
                fig_am.update_layout(
                    title=dict(text=f"Mais Disciplinados — {temporada}", font=dict(size=14, color=TEXTO)),
                    xaxis=dict(
                        title="Amarelos/jogo",
                        range=[0, top_disc["amarelos_por_jogo"].max() + 0.4],
                        gridcolor=BORDA,
                        tickfont=dict(color=MUTED),
                    ),
                    yaxis=dict(tickfont=dict(size=9, color=TEXTO), gridcolor="rgba(0,0,0,0)"),
                    height=400,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=TEXTO, family="Inter, sans-serif"),
                    margin=dict(l=10, r=50, t=40, b=20),
                    showlegend=False,
                )
                st.plotly_chart(fig_am, width="stretch")

            st.caption("Dados de cartões disponíveis apenas para 2014–2024.")

    # ── Tab 4: Histórico ─────────────────────────────────────────
    with tab_hist:
        c1, c2 = st.columns([6, 4])

        with c1:
            top20 = df_presenca.head(20)
            fig_pres = go.Figure()
            fig_pres.add_trace(go.Bar(
                x=top20["clube"],
                y=top20["temporadas"],
                marker=dict(
                    color=top20["temporadas"],
                    colorscale=[[0.0, f"rgba(0,39,118,0.35)"], [1.0, AZUL]],
                    showscale=False,
                    line=dict(color="rgba(0,0,0,0)", width=0),
                ),
                text=top20["temporadas"],
                textposition="outside",
                textfont=dict(size=10, color=TEXTO),
                hovertemplate="<b>%{x}</b><br>Temporadas no Brasileirão: %{y}<extra></extra>",
                showlegend=False,
                name="Temporadas",
            ))
            fig_pres.update_layout(
                title=dict(text="Presenças no Brasileirão 2003–2024 · Top 20", font=dict(size=14, color=TEXTO)),
                xaxis=dict(tickangle=-40, tickfont=dict(size=8, color=TEXTO), gridcolor=BORDA),
                yaxis=dict(title="Temporadas", gridcolor=BORDA, tickfont=dict(color=MUTED)),
                height=410,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=TEXTO, family="Inter, sans-serif"),
                margin=dict(l=10, r=20, t=40, b=90),
                showlegend=False,
            )
            st.plotly_chart(fig_pres, width="stretch")

        with c2:
            # Evolução % por mando — linha (diferente do stacked bar do app.py)
            fig_mv = go.Figure()
            for label, col, cor in [
                ("Mandante", "pct_m", VERDE),
                ("Visitante", "pct_v", VERMELHO),
                ("Empate",   "pct_e", AMARELO),
            ]:
                fig_mv.add_trace(go.Scatter(
                    x=df_mv_hist["temporada"],
                    y=df_mv_hist[col],
                    mode="lines+markers",
                    name=label,
                    line=dict(color=cor, width=2.5),
                    marker=dict(size=6, color=cor),
                    hovertemplate=f"<b>{label}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
                ))
            fig_mv.update_layout(
                title=dict(text="% Resultados por Mando (2003–2024)", font=dict(size=14, color=TEXTO)),
                xaxis=dict(tickformat="d", gridcolor=BORDA, tickfont=dict(color=MUTED)),
                yaxis=dict(title="%", gridcolor=BORDA, tickfont=dict(color=MUTED)),
                height=410,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(241,245,249,0.6)",
                font=dict(color=TEXTO, family="Inter, sans-serif"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXTO, size=11)),
                margin=dict(l=10, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_mv, width="stretch")

# ── Rodapé ───────────────────────────────────────────────────────
st.markdown(
    f'<div style="text-align:center;padding:1.5rem 0 0.5rem;font-size:0.68rem;'
    f'color:{MUTED};border-top:1px solid {BORDA};margin-top:1rem;">'
    f'Fonte: Kaggle / Adão Duque · Licença GPL 2 · '
    f'Dashboard gerado a partir da camada marts — nenhum cálculo realizado no banco'
    f'</div>',
    unsafe_allow_html=True,
)
