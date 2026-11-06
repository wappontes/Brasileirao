"""
app_v2.py — Brasileirão Analytics v2
Layout inspirado em dashboards modernos de esporte.
Cores da bandeira do Brasil: verde (#009C3B), amarelo (#FFDF00), azul (#002776).
"""
import base64
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ══════════════════════════════════════════════════════════════════
# Página
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Brasileirão Analytics",
    page_icon="🇧🇷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════
# Paleta — cores da bandeira do Brasil
# ══════════════════════════════════════════════════════════════════
VERDE   = "#009C3B"
AMARELO = "#FFDF00"
AZUL    = "#002776"
CIANO   = "#00B4D8"
VERMELHO = "#E63946"
FUNDO   = "#071525"
CARD    = "#0C1E3A"
CARD2   = "#0F2548"
BORDA   = "#1A3A6B"
TEXTO   = "#E8EFF5"
MUTED   = "#6B87A4"

# Categorias dos gráficos (ordem fixa, nunca ciclada)
COR_ZONA = {
    "Libertadores":  VERDE,
    "Sul-Americana": CIANO,
    "Meio":          AMARELO,
    "Rebaixamento":  VERMELHO,
}


def _rgba(hex_color: str, alpha: float = 0.18) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# Template Plotly com paleta brasileira
pio.templates["brasil"] = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXTO, family="Inter, sans-serif", size=12),
        colorway=[VERDE, AMARELO, CIANO, VERMELHO, "#FF9F1C", "#6B2FBB", "#06D6A0"],
        xaxis=dict(gridcolor=BORDA, linecolor=BORDA, tickfont=dict(color=MUTED)),
        yaxis=dict(gridcolor=BORDA, linecolor=BORDA, tickfont=dict(color=MUTED)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXTO)),
        hoverlabel=dict(bgcolor=CARD2, font=dict(color=TEXTO, size=12)),
    )
)
pio.templates.default = "brasil"

# ══════════════════════════════════════════════════════════════════
# CSS
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
    background: {AZUL} !important;
    border-right: 1px solid rgba(255,223,0,0.2) !important;
}}
[data-testid="stSidebar"] * {{ color: {TEXTO} !important; }}
h1, h2, h3, h4 {{
    font-family: 'Barlow Condensed', sans-serif !important;
    font-weight: 800 !important;
}}
/* tabs */
button[role="tab"] {{
    background: {CARD2} !important;
    color: {MUTED} !important;
    border-radius: 8px 8px 0 0 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    border: none !important;
    margin-right: 4px !important;
    padding: 0.4rem 1rem !important;
}}
button[role="tab"][aria-selected="true"] {{
    background: {VERDE} !important;
    color: white !important;
    font-weight: 600 !important;
}}
[data-testid="stTabsContent"] {{
    background: {CARD};
    border: 1px solid {BORDA};
    border-radius: 0 12px 12px 12px;
    padding: 1.25rem 1.4rem;
}}
/* metrics */
[data-testid="stMetric"] {{
    background: {CARD};
    border: 1px solid {BORDA};
    border-radius: 12px;
    padding: 0.9rem 1rem !important;
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
/* selectbox e multiselect */
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] {{
    background: {CARD2} !important;
    border-color: {BORDA} !important;
}}
/* scrollbar */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: {FUNDO}; }}
::-webkit-scrollbar-thumb {{ background: {BORDA}; border-radius: 3px; }}
/* caption */
[data-testid="stCaptionContainer"] {{ color: {MUTED} !important; font-size: 0.72rem !important; }}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# Escudos (mesma lógica do app.py)
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
    css = f"vertical-align:middle;margin-right:6px;flex-shrink:0;object-fit:contain;"
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
            f'font-size:{fs}px;background:{CARD2};color:{TEXTO};margin-right:6px;">'
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
with st.sidebar:
    st.markdown(f"""
    <div style="padding:0.5rem 0 0.75rem;">
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:1.9rem;
                  font-weight:800;color:white;line-height:1.1;">
        <span style="color:{AMARELO};">BRASI</span>LEIRÃO
      </div>
      <div style="font-size:0.65rem;color:rgba(255,255,255,0.4);text-transform:uppercase;
                  letter-spacing:0.12em;margin-top:3px;">Analytics · 2003 – 2024</div>
    </div>
    <hr style="border-color:rgba(255,223,0,0.2);margin:0 0 1rem;">
    <div style="font-size:0.65rem;color:rgba(255,255,255,0.45);text-transform:uppercase;
                letter-spacing:0.1em;margin-bottom:0.4rem;">Temporada</div>
    """, unsafe_allow_html=True)

    temporadas = _q(con, "SELECT DISTINCT temporada FROM marts.classificacao ORDER BY temporada DESC")[
        "temporada"
    ].tolist()
    temporada = st.selectbox("Temporada", temporadas, index=0, label_visibility="collapsed")

    st.markdown(f"""
    <div style="font-size:0.65rem;color:rgba(255,255,255,0.45);text-transform:uppercase;
                letter-spacing:0.1em;margin:1rem 0 0.4rem;">Comparar Clubes</div>
    """, unsafe_allow_html=True)

    clubes_temporada = _q(
        con,
        f"SELECT clube FROM marts.classificacao WHERE temporada={temporada} ORDER BY posicao",
    )["clube"].tolist()
    clubes_selecionados = st.multiselect(
        "Comparar",
        clubes_temporada,
        default=clubes_temporada[:3] if len(clubes_temporada) >= 3 else clubes_temporada,
        label_visibility="collapsed",
    )

    st.markdown(f"""
    <hr style="border-color:rgba(255,223,0,0.1);margin:1rem 0 0.75rem;">
    <div style="font-size:0.65rem;color:rgba(255,255,255,0.45);text-transform:uppercase;
                letter-spacing:0.1em;margin-bottom:0.5rem;">Competição</div>
    <div style="background:rgba(0,156,59,0.2);border:1px solid {VERDE};border-radius:8px;
                padding:0.45rem 0.75rem;">
      <span style="font-size:0.85rem;font-weight:600;color:{VERDE};">● Série A</span>
      <span style="float:right;font-size:0.7rem;color:{MUTED};">Brasil</span>
    </div>
    <hr style="border-color:rgba(255,223,0,0.1);margin:1.25rem 0 0.75rem;">
    <div style="font-size:0.68rem;color:rgba(255,255,255,0.3);line-height:1.6;">
      Dados: Kaggle / Adão Duque · GPL 2<br>
      Nenhum cálculo fora do banco
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# Dados
# ══════════════════════════════════════════════════════════════════
df_class = _q(con, f"""
    SELECT temporada, clube, posicao, pontos, jogos,
           vitorias, empates, derrotas,
           gols_pro, gols_contra, saldo,
           ROUND(pontos::DOUBLE / jogos, 2) AS pts_por_jogo
    FROM marts.classificacao
    WHERE temporada = {temporada}
    ORDER BY posicao
""")

df_mv = _q(con, f"SELECT * FROM marts.mandante_visitante WHERE temporada = {temporada}")

df_gols_hist = _q(con, """
    SELECT temporada, media_gols, total_gols
    FROM marts.media_gols ORDER BY temporada
""")

df_class_hist = _q(con, """
    SELECT temporada, clube, posicao, pontos
    FROM marts.classificacao ORDER BY temporada, posicao
""")

df_titulos = _q(con, """
    SELECT clube, COUNT(*) AS titulos
    FROM marts.classificacao WHERE posicao = 1
    GROUP BY clube ORDER BY titulos DESC
""")

df_cartoes = _q(con, f"""
    SELECT clube, amarelos, vermelhos,
           amarelos_por_jogo, vermelhos_por_jogo
    FROM marts.cartoes_clube WHERE temporada = {temporada}
    ORDER BY amarelos_por_jogo DESC
""")

gols_temporada = _q(con, f"""
    SELECT media_gols, total_gols
    FROM marts.media_gols WHERE temporada = {temporada}
""")

# ══════════════════════════════════════════════════════════════════
# SVG sprites (escudos)
# ══════════════════════════════════════════════════════════════════
if _SVG_SPRITE:
    st.markdown(f'<div style="display:none;">{_SVG_SPRITE}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# Layout: coluna principal (68%) + painel direito (32%)
# ══════════════════════════════════════════════════════════════════
col_main, col_right = st.columns([68, 32])

# ══════════════════════════════════════════════════════════════════
# PAINEL DIREITO
# ══════════════════════════════════════════════════════════════════
with col_right:

    # ── Destaques da temporada ────────────────────────────────────
    if not df_class.empty:
        campea = df_class.iloc[0]
        artilheiro = df_class.loc[df_class["gols_pro"].idxmax()]
        melhor_def = df_class.loc[df_class["gols_contra"].idxmin()]

        def _drow(ico_label, clube, valor, cor):
            logo = escudo_html(clube, 20)
            return (
                f'<div style="display:flex;align-items:center;padding:0.5rem 0;border-bottom:1px solid {BORDA};">'
                f'<div style="flex:1;min-width:0;">'
                f'<div style="font-size:0.62rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.07em;">{ico_label}</div>'
                f'<div style="font-weight:600;color:{TEXTO};display:flex;align-items:center;margin-top:2px;white-space:nowrap;">{logo}{clube}</div>'
                f'</div>'
                f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.35rem;font-weight:800;color:{cor};white-space:nowrap;">{valor}</div>'
                f'</div>'
            )

        titulo_div = (
            f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-weight:700;'
            f'font-size:0.82rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{AMARELO};margin-bottom:0.25rem;">Destaques {temporada}</div>'
        )
        rows = (
            _drow("🏆 Campeão", campea["clube"], f'{int(campea["pontos"])} pts', VERDE)
            + _drow("⚽ Mais gols", artilheiro["clube"], f'{int(artilheiro["gols_pro"])} gols', AMARELO)
            + _drow("🛡 Melhor defesa", melhor_def["clube"], f'{int(melhor_def["gols_contra"])} gc', CIANO)
        )
        card = (
            f'<div style="background:{CARD};border:1px solid {BORDA};border-radius:14px;'
            f'padding:1rem 1.1rem;margin-bottom:0.9rem;">'
            + titulo_div + rows + '</div>'
        )
        st.markdown(card, unsafe_allow_html=True)

    # ── Mando de campo — donut ────────────────────────────────────
    if not df_mv.empty:
        row = df_mv.iloc[0]
        fig_donut = go.Figure(go.Pie(
            labels=["Mandante", "Empate", "Visitante"],
            values=[row["pct_mandante"], row["pct_empate"], row["pct_visitante"]],
            hole=0.62,
            marker=dict(
                colors=[VERDE, AMARELO, CIANO],
                line=dict(color=FUNDO, width=2),
            ),
            textinfo="none",
            hovertemplate="<b>%{label}</b>: %{value:.1f}%<extra></extra>",
        ))
        fig_donut.update_layout(
            height=210,
            margin=dict(l=0, r=70, t=10, b=10),
            showlegend=True,
            legend=dict(
                orientation="v", x=1.02, y=0.5,
                font=dict(size=10, color=TEXTO),
                bgcolor="rgba(0,0,0,0)",
            ),
            annotations=[dict(
                text=(f"<b style='font-size:18px;color:{VERDE}'>"
                      f"{row['pct_mandante']:.0f}%</b><br>"
                      f"<span style='font-size:9px;color:{MUTED}'>mandante</span>"),
                x=0.38, y=0.5, showarrow=False, align="center",
                font=dict(size=12, color=TEXTO),
            )],
            paper_bgcolor=CARD,
        )
        st.markdown(f"""
        <div style="background:{CARD};border:1px solid {BORDA};border-radius:14px;
                    padding:0.9rem 1.1rem 0.4rem;margin-bottom:0.9rem;">
          <div style="font-family:'Barlow Condensed',sans-serif;font-weight:700;
                      font-size:0.82rem;text-transform:uppercase;letter-spacing:0.08em;
                      color:{AMARELO};margin-bottom:0;">🏟 Mando de Campo {temporada}</div>
        """, unsafe_allow_html=True)
        st.plotly_chart(fig_donut, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Títulos históricos ────────────────────────────────────────
    if not df_titulos.empty:
        top5 = df_titulos.head(5)
        medals = ["🥇", "🥈", "🥉", "4°", "5°"]
        rows_t = ""
        max_t = int(top5["titulos"].max())
        for i, (_, r) in enumerate(top5.iterrows()):
            bar_w = int(r["titulos"] / max_t * 100)
            logo = escudo_html(r["clube"], 20)
            rows_t += (
                f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:0.45rem;">'
                f'<span style="font-size:0.9rem;width:22px;">{medals[i]}</span>'
                f'{logo}'
                f'<span style="flex:1;font-size:0.82rem;color:{TEXTO};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{r["clube"]}</span>'
                f'<div style="width:50px;background:{BORDA};border-radius:4px;height:5px;">'
                f'<div style="width:{bar_w}%;background:{VERDE};height:100%;border-radius:4px;"></div></div>'
                f'<span style="font-family:\'Barlow Condensed\',sans-serif;font-size:1.05rem;font-weight:800;color:{VERDE};width:16px;text-align:right;">{int(r["titulos"])}</span>'
                f'</div>'
            )
        titulos_card = (
            f'<div style="background:{CARD};border:1px solid {BORDA};border-radius:14px;padding:1rem 1.1rem;margin-bottom:0.9rem;">'
            f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-weight:700;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.08em;color:{AMARELO};margin-bottom:0.75rem;">🏆 Maiores Campeões</div>'
            + rows_t + '</div>'
        )
        st.markdown(titulos_card, unsafe_allow_html=True)

    # ── Stat de gols da temporada ─────────────────────────────────
    if not gols_temporada.empty:
        mg = gols_temporada.iloc[0]["media_gols"]
        tg = int(gols_temporada.iloc[0]["total_gols"])
        gols_card = (
            f'<div style="background:{CARD};border:1px solid {BORDA};border-radius:14px;padding:1rem 1.1rem;">'
            f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-weight:700;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.08em;color:{AMARELO};margin-bottom:0.75rem;">⚽ Gols {temporada}</div>'
            f'<div style="display:flex;justify-content:space-around;text-align:center;">'
            f'<div><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:2.4rem;font-weight:800;color:{VERDE};line-height:1;">{mg:.2f}</div>'
            f'<div style="font-size:0.62rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.07em;margin-top:2px;">por jogo</div></div>'
            f'<div style="border-left:1px solid {BORDA};"></div>'
            f'<div><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:2.4rem;font-weight:800;color:{AMARELO};line-height:1;">{tg}</div>'
            f'<div style="font-size:0.62rem;color:{MUTED};text-transform:uppercase;letter-spacing:0.07em;margin-top:2px;">total</div></div>'
            f'</div></div>'
        )
        st.markdown(gols_card, unsafe_allow_html=True)
    else:
        gols_sd = (
            f'<div style="background:{CARD};border:1px solid {BORDA};border-radius:14px;padding:1rem 1.1rem;">'
            f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-weight:700;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.08em;color:{AMARELO};margin-bottom:0.5rem;">⚽ Gols {temporada}</div>'
            f'<div style="color:{MUTED};font-size:0.8rem;">Dados de gols indisponíveis para 2003–2013.</div>'
            f'</div>'
        )
        st.markdown(gols_sd, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# COLUNA PRINCIPAL
# ══════════════════════════════════════════════════════════════════
with col_main:

    # ── Hero banner do campeão ────────────────────────────────────
    if not df_class.empty:
        c = df_class.iloc[0]
        saldo_str = ("+" if int(c["saldo"]) > 0 else "") + str(int(c["saldo"]))
        saldo_cor = VERDE if int(c["saldo"]) > 0 else VERMELHO
        st.markdown(f"""
        <div style="
          background: linear-gradient(120deg, {AZUL} 0%, #0A1E3A 45%, rgba(0,80,20,0.5) 100%);
          border: 1px solid {VERDE};
          border-radius: 16px;
          padding: 1.4rem 1.8rem;
          margin-bottom: 1.1rem;
          position: relative;
          overflow: hidden;
        ">
          <div style="position:absolute;top:-40px;right:-40px;width:220px;height:220px;
                      background:radial-gradient(circle,rgba(0,156,59,0.18) 0%,transparent 70%);
                      pointer-events:none;"></div>
          <div style="font-size:0.62rem;color:{AMARELO};text-transform:uppercase;
                      letter-spacing:0.14em;font-weight:700;margin-bottom:0.3rem;">
            ★ Campeão Brasileiro {temporada}
          </div>
          <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap;">
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:2.5rem;
                        font-weight:800;color:white;line-height:1;
                        display:flex;align-items:center;gap:0.4rem;">
              {escudo_html(c["clube"], 44)}{c["clube"]}
            </div>
            <div style="display:flex;gap:1.5rem;margin-left:auto;flex-wrap:wrap;">
              <div style="text-align:center;">
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:2rem;
                            font-weight:800;color:{VERDE};">{int(c["pontos"])}</div>
                <div style="font-size:0.58rem;color:{MUTED};text-transform:uppercase;
                            letter-spacing:0.08em;">pontos</div>
              </div>
              <div style="text-align:center;">
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:2rem;
                            font-weight:800;color:{AMARELO};">{int(c["vitorias"])}</div>
                <div style="font-size:0.58rem;color:{MUTED};text-transform:uppercase;
                            letter-spacing:0.08em;">vitórias</div>
              </div>
              <div style="text-align:center;">
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:2rem;
                            font-weight:800;color:{CIANO};">{int(c["gols_pro"])}</div>
                <div style="font-size:0.58rem;color:{MUTED};text-transform:uppercase;
                            letter-spacing:0.08em;">gols pró</div>
              </div>
              <div style="text-align:center;">
                <div style="font-family:'Barlow Condensed',sans-serif;font-size:2rem;
                            font-weight:800;color:{saldo_cor};">{saldo_str}</div>
                <div style="font-size:0.58rem;color:{MUTED};text-transform:uppercase;
                            letter-spacing:0.08em;">saldo</div>
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋  Tabela + Eficiência",
        "⚽  Ataque × Defesa",
        "📈  Histórico",
        "🎯  Comparar Clubes",
    ])

    # ── TAB 1: Tabela de classificação ────────────────────────────
    with tab1:
        if df_class.empty:
            st.warning("Sem dados para esta temporada.")
        else:
            n = len(df_class)
            linhas = ""
            for _, r in df_class.iterrows():
                pos = int(r["posicao"])
                saldo = int(r["saldo"])
                saldo_str = ("+" if saldo > 0 else "") + str(saldo)
                s_cor = VERDE if saldo > 0 else (VERMELHO if saldo < 0 else MUTED)
                pts_j = f"{r['pts_por_jogo']:.2f}" if r["pts_por_jogo"] is not None else "-"

                if pos <= 4:
                    zona_b = f"border-left:3px solid {VERDE};"
                    p_bg, p_col = VERDE, "white"
                elif pos <= 6:
                    zona_b = f"border-left:3px solid {CIANO};"
                    p_bg, p_col = CIANO, "white"
                elif pos > n - 4:
                    zona_b = f"border-left:3px solid {VERMELHO};"
                    p_bg, p_col = VERMELHO, "white"
                else:
                    zona_b = ""
                    p_bg, p_col = CARD2, MUTED

                pos_badge = (
                    f'<span style="display:inline-flex;align-items:center;'
                    f'justify-content:center;width:22px;height:22px;border-radius:50%;'
                    f'background:{p_bg};color:{p_col};font-size:0.68rem;font-weight:700;">'
                    f'{pos}</span>'
                )

                linhas += f"""
                <tr style="border-bottom:1px solid {BORDA};">
                  <td style="{zona_b}padding:0.5rem 0.3rem 0.5rem 0.6rem;">{pos_badge}</td>
                  <td style="padding:0.5rem 0.8rem;white-space:nowrap;text-align:left;">
                    {escudo_html(r["clube"])}{r["clube"]}
                  </td>
                  <td style="font-weight:700;color:{VERDE};font-family:'Barlow Condensed',
                              sans-serif;font-size:1.05rem;">{int(r["pontos"])}</td>
                  <td>{int(r["jogos"])}</td>
                  <td style="color:{VERDE};">{int(r["vitorias"])}</td>
                  <td style="color:{MUTED};">{int(r["empates"])}</td>
                  <td style="color:{VERMELHO};">{int(r["derrotas"])}</td>
                  <td>{int(r["gols_pro"])}</td>
                  <td>{int(r["gols_contra"])}</td>
                  <td style="color:{s_cor};font-weight:600;">{saldo_str}</td>
                  <td style="color:{MUTED};">{pts_j}</td>
                </tr>"""

            th = (f"color:{MUTED};font-size:0.63rem;text-transform:uppercase;"
                  f"letter-spacing:0.08em;padding:0.55rem 0.5rem;text-align:center;")
            st.markdown(f"""
            <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;font-family:'Inter',sans-serif;
                          font-size:0.83rem;color:{TEXTO};">
              <thead>
                <tr style="background:{CARD2};">
                  <th style="{th}text-align:center;">#</th>
                  <th style="{th}text-align:left;padding-left:0.8rem;">Clube</th>
                  <th style="{th}">P</th><th style="{th}">J</th>
                  <th style="{th}">V</th><th style="{th}">E</th>
                  <th style="{th}">D</th><th style="{th}">GP</th>
                  <th style="{th}">GC</th><th style="{th}">SG</th>
                  <th style="{th}">P/J</th>
                </tr>
              </thead>
              <tbody>{linhas}</tbody>
            </table>
            <div style="display:flex;gap:1.5rem;margin-top:0.75rem;font-size:0.7rem;
                        color:{MUTED};">
              <span style="color:{VERDE};">● 1°–4°</span>
              <span style="color:{CIANO};">● 5°–6°</span>
              <span style="color:{VERMELHO};">● Rebaixamento</span>
            </div>
            </div>
            """, unsafe_allow_html=True)

    # ── TAB 2: Scatter Ataque × Defesa ────────────────────────────
    with tab2:
        if df_class.empty:
            st.warning("Sem dados para esta temporada.")
        else:
            df_s = df_class.copy()
            n_s = len(df_s)

            fig_sc = go.Figure()
            med_x = df_s["gols_pro"].median()
            med_y = df_s["gols_contra"].median()
            fig_sc.add_hline(y=med_y, line_dash="dot", line_color=BORDA, line_width=1)
            fig_sc.add_vline(x=med_x, line_dash="dot", line_color=BORDA, line_width=1)

            # Escala sequencial por posição: 1° (verde) → n° (vermelho)
            fig_sc.add_trace(go.Scatter(
                x=df_s["gols_pro"],
                y=df_s["gols_contra"],
                mode="markers+text",
                showlegend=False,
                marker=dict(
                    size=df_s["pontos"] / df_s["pontos"].max() * 38 + 10,
                    color=df_s["posicao"],
                    colorscale=[[0.0, VERDE], [0.5, AMARELO], [1.0, VERMELHO]],
                    cmin=1,
                    cmax=n_s,
                    colorbar=dict(
                        title=dict(text="Posição", side="right"),
                        tickvals=[1, n_s // 2, n_s],
                        ticktext=[f"1°", f"{n_s // 2}°", f"{n_s}°"],
                        thickness=12,
                        tickfont=dict(color=MUTED, size=10),
                    ),
                    opacity=0.88,
                    line=dict(color="white", width=1.5),
                    showscale=True,
                ),
                text=df_s["clube"].str[:9],
                textposition="top center",
                textfont=dict(size=9, color=TEXTO),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Gols marcados: %{x}<br>"
                    "Gols sofridos: %{y}<br>"
                    "Pontos: %{customdata[1]}<br>"
                    "Posição: %{customdata[2]}°<extra></extra>"
                ),
                customdata=df_s[["clube", "pontos", "posicao"]].values,
            ))

            # Rótulos de quadrante
            x_max, x_min = df_s["gols_pro"].max(), df_s["gols_pro"].min()
            y_max, y_min = df_s["gols_contra"].max(), df_s["gols_contra"].min()
            quadrantes = [
                (x_max, y_min * 1.05, "right", VERDE,    "Domínio total"),
                (x_min, y_max * 0.97, "left",  VERMELHO, "Desastre"),
                (x_max, y_max * 0.97, "right", AMARELO,  "Ataque forte, defesa frágil"),
                (x_min, y_min * 1.05, "left",  CIANO,    "Defesa forte, ataque tímido"),
            ]
            for x, y, anchor, cor, txt in quadrantes:
                fig_sc.add_annotation(
                    x=x, y=y, text=txt,
                    font=dict(size=9, color=cor),
                    showarrow=False, xanchor=anchor,
                )

            fig_sc.update_layout(
                height=490,
                xaxis_title="Gols marcados",
                yaxis_title="Gols sofridos",
                xaxis=dict(title_font=dict(color=MUTED, size=11)),
                yaxis=dict(title_font=dict(color=MUTED, size=11)),
                legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
                margin=dict(l=10, r=10, t=40, b=10),
            )
            st.plotly_chart(fig_sc, width="stretch")
            st.caption(
                "Tamanho da bolha proporcional aos pontos conquistados. "
                "Linha tracejada = mediana da temporada."
            )

    # ── TAB 3: Histórico ──────────────────────────────────────────
    with tab3:
        # Heatmap divergente: 1° (verde) → 10-11° (neutro) → 20° (vermelho)
        df_pivot = df_class_hist.pivot_table(
            index="clube", columns="temporada", values="posicao"
        )
        df_pivot["_ap"] = df_pivot.notna().sum(axis=1)
        top20 = df_pivot.nlargest(20, "_ap").drop(columns=["_ap"])
        top20 = top20.sort_values(
            by=top20.columns[-1], ascending=True, na_position="last"
        )

        fig_heat = go.Figure(go.Heatmap(
            z=top20.values,
            x=[str(c) for c in top20.columns],
            y=top20.index.tolist(),
            colorscale=[
                [0.0,  VERDE],
                [0.3,  "#7EC850"],
                [0.5,  MUTED],       # neutro no meio (posição ~10)
                [0.7,  "#FF8C00"],
                [1.0,  VERMELHO],
            ],
            zmin=1, zmax=20,
            hovertemplate="<b>%{y}</b><br>%{x}: %{z}° lugar<extra></extra>",
            colorbar=dict(
                title=dict(text="Posição", side="right"),
                tickvals=[1, 5, 10, 15, 20],
                ticktext=["1°", "5°", "10°", "15°", "20°"],
                thickness=12,
                tickfont=dict(color=MUTED, size=10),
            ),
            xgap=1, ygap=1,
        ))
        fig_heat.update_layout(
            height=580,
            xaxis=dict(tickangle=-45, tickfont=dict(size=9.5), side="bottom"),
            yaxis=dict(tickfont=dict(size=10), autorange="reversed"),
            margin=dict(l=10, r=70, t=10, b=10),
        )

        st.markdown(f"""
        <div style="font-family:'Barlow Condensed',sans-serif;font-weight:700;
                    font-size:1.05rem;color:{AMARELO};margin-bottom:0.4rem;
                    text-transform:uppercase;letter-spacing:0.06em;">
          Mapa Histórico de Posições — 20 Clubes com Mais Participações
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(fig_heat, width="stretch")

        # Área: evolução de gols
        if not df_gols_hist.empty:
            st.markdown(f"""
            <div style="font-family:'Barlow Condensed',sans-serif;font-weight:700;
                        font-size:1.05rem;color:{AMARELO};margin:1rem 0 0.4rem;
                        text-transform:uppercase;letter-spacing:0.06em;">
              Média de Gols por Jogo · 2014 – 2024
            </div>""", unsafe_allow_html=True)

            fig_gols = go.Figure()
            fig_gols.add_trace(go.Scatter(
                x=df_gols_hist["temporada"],
                y=df_gols_hist["media_gols"],
                mode="lines+markers",
                name="Média gols/jogo",
                line=dict(color=VERDE, width=2),
                marker=dict(size=7, color=VERDE, line=dict(color="white", width=1.5)),
                fill="tozeroy",
                fillcolor=_rgba(VERDE, 0.14),
                hovertemplate="<b>%{x}</b><br>%{y:.2f} gols/jogo<extra></extra>",
            ))
            fig_gols.update_layout(
                height=240,
                xaxis=dict(tickmode="linear", dtick=1, tickangle=-45),
                yaxis=dict(title="gols/jogo", title_font=dict(color=MUTED, size=10)),
                showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig_gols, width="stretch")
            st.caption("Dados de gols disponíveis apenas a partir de 2014.")

    # ── TAB 4: Comparar Clubes ─────────────────────────────────────
    with tab4:
        if not clubes_selecionados:
            st.info("Selecione ao menos um clube no painel lateral.")
        else:
            df_comp = df_class[df_class["clube"].isin(clubes_selecionados)].copy()

            if df_comp.empty:
                st.warning("Os clubes selecionados não disputaram esta temporada.")
            else:
                # Normaliza 0-100 relativo à temporada (para radar)
                df_all = df_class.copy()

                def _norm(serie: pd.Series, invert: bool = False) -> pd.Series:
                    mn, mx = serie.min(), serie.max()
                    if mx == mn:
                        return pd.Series([50.0] * len(serie), index=serie.index)
                    n = (serie - mn) / (mx - mn) * 100.0
                    return 100.0 - n if invert else n

                df_all["n_pontos"]   = _norm(df_all["pontos"])
                df_all["n_ataque"]   = _norm(df_all["gols_pro"])
                df_all["n_defesa"]   = _norm(df_all["gols_contra"], invert=True)
                df_all["n_vitorias"] = _norm(df_all["vitorias"])
                df_all["n_saldo"]    = _norm(df_all["saldo"])

                df_comp_norm = df_all[df_all["clube"].isin(clubes_selecionados)]

                cats = ["Pontos", "Ataque", "Defesa", "Vitórias", "Saldo"]
                cores_r = [VERDE, AMARELO, CIANO, VERMELHO, "#FF9F1C"]

                fig_radar = go.Figure()
                for i, (_, row) in enumerate(df_comp_norm.iterrows()):
                    vals = [row["n_pontos"], row["n_ataque"], row["n_defesa"],
                            row["n_vitorias"], row["n_saldo"]]
                    vals_c = vals + [vals[0]]
                    cats_c = cats + [cats[0]]
                    cor = cores_r[i % len(cores_r)]
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals_c, theta=cats_c,
                        name=row["clube"],
                        fill="toself",
                        fillcolor=_rgba(cor, 0.14),
                        line=dict(color=cor, width=2),
                        marker=dict(color=cor, size=6,
                                    line=dict(color="white", width=1)),
                        hovertemplate=(
                            f"<b>{row['clube']}</b><br>"
                            "%{theta}: %{r:.0f}/100<extra></extra>"
                        ),
                    ))

                fig_radar.update_layout(
                    polar=dict(
                        bgcolor="rgba(0,0,0,0)",
                        radialaxis=dict(
                            visible=True, range=[0, 100],
                            tickfont=dict(size=8, color=MUTED),
                            gridcolor=BORDA, linecolor=BORDA,
                        ),
                        angularaxis=dict(
                            tickfont=dict(size=11, color=TEXTO),
                            gridcolor=BORDA, linecolor=BORDA,
                        ),
                    ),
                    height=400,
                    showlegend=True,
                    legend=dict(
                        orientation="h", yanchor="bottom", y=-0.18,
                        xanchor="center", x=0.5,
                    ),
                    margin=dict(l=40, r=40, t=20, b=70),
                )

                st.markdown(f"""
                <div style="font-family:'Barlow Condensed',sans-serif;font-weight:700;
                            font-size:1.05rem;color:{AMARELO};margin-bottom:0.4rem;
                            text-transform:uppercase;letter-spacing:0.06em;">
                  Radar Comparativo — {temporada} (escala normalizada)
                </div>""", unsafe_allow_html=True)
                st.plotly_chart(fig_radar, width="stretch")
                st.caption(
                    "Valores normalizados de 0 a 100 em relação aos demais clubes da temporada. "
                    "Defesa: maior = menos gols sofridos."
                )

                # Evolução histórica de pontos
                nomes_sql = ",".join(f"'{c.replace(chr(39), chr(39)*2)}'" for c in clubes_selecionados)
                df_hist = _q(con, f"""
                    SELECT temporada, clube, pontos
                    FROM marts.classificacao
                    WHERE clube IN ({nomes_sql})
                    ORDER BY temporada
                """)

                if not df_hist.empty:
                    st.markdown(f"""
                    <div style="font-family:'Barlow Condensed',sans-serif;font-weight:700;
                                font-size:1.05rem;color:{AMARELO};margin:1rem 0 0.4rem;
                                text-transform:uppercase;letter-spacing:0.06em;">
                      Evolução Histórica de Pontos
                    </div>""", unsafe_allow_html=True)

                    fig_ev = go.Figure()
                    for i, clube in enumerate(clubes_selecionados):
                        df_c = df_hist[df_hist["clube"] == clube]
                        if df_c.empty:
                            continue
                        cor = cores_r[i % len(cores_r)]
                        fig_ev.add_trace(go.Scatter(
                            x=df_c["temporada"],
                            y=df_c["pontos"],
                            mode="lines+markers",
                            name=clube,
                            line=dict(color=cor, width=2),
                            marker=dict(size=6, color=cor,
                                        line=dict(color="white", width=1)),
                            hovertemplate=f"<b>{clube}</b><br>%{{x}}: %{{y}} pts<extra></extra>",
                        ))

                    fig_ev.update_layout(
                        height=320,
                        xaxis=dict(tickmode="linear", dtick=1, tickangle=-45),
                        yaxis=dict(title="Pontos", title_font=dict(color=MUTED, size=10)),
                        legend=dict(
                            orientation="h", yanchor="bottom", y=1.01,
                            xanchor="left", x=0,
                        ),
                        margin=dict(l=10, r=10, t=40, b=10),
                        hovermode="x unified",
                    )
                    st.plotly_chart(fig_ev, width="stretch")
                    st.caption(
                        "Temporadas sem dado = clube não disputou a Série A naquele ano."
                    )
