"""
Dashboard do Campeonato Brasileiro de Futebol — Brasileirão Série A.

Regra da camada de visualização: apenas SELECT nos marts.
Nenhum cálculo é realizado aqui; toda a lógica está nos marts.
"""

import base64
import sys
from pathlib import Path

import duckdb
import plotly.graph_objects as go
import streamlit as st


# ── escudos SVG ───────────────────────────────────────────────────────────────
_ASSETS = Path(__file__).parent / "assets"

def _lê(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

_SVG_SPRITE = _lê(_ASSETS / "escudos.svg") + _lê(_ASSETS / "escudos-b.svg")

# Times cobertos pelos sprites SVG inline (série A + série B)
ESCUDO_ID: dict[str, str] = {
    "Flamengo":      "flamengo",
    "Fluminense":    "fluminense",
    "Vasco":         "vasco",
    "Corinthians":   "corinthians",
    "Palmeiras":     "palmeiras",
    "Santos":        "santos",
    "Sao Paulo":     "sao-paulo",
    "Internacional": "internacional",
    "Gremio":        "gremio",
    "Cruzeiro":      "cruzeiro",
    "Atletico-MG":   "atletico-mg",
    "Athletico-PR":  "atletico-pr",
    "Avai":          "avai",
    "Chapecoense":   "chapecoense",
    "Coritiba":      "coritiba",
    "Figueirense":   "figueirense",
    "Goias":         "goias",
    "Joinville":     "joinville",
    "Ponte Preta":   "ponte-preta",
    "Sport":         "sport",
    "America-MG":    "america-mg",
    "Atletico-GO":   "atletico-go",
    "Bahia":         "bahia",
    "Botafogo-RJ":   "botafogo",
    "Bragantino":    "bragantino",
    "Ceara":         "ceara",
    "Criciuma":      "criciuma",
    "Nautico":       "nautico",
    "Parana":        "parana",
    "Paysandu":      "paysandu",
    "Santa Cruz":    "santa-cruz",
    "Vitoria":       "vitoria",
}

# Times com arquivo de logo baixado em assets/logos/
LOGO_FILE: dict[str, str] = {
    "Fortaleza":   "fortaleza.svg",
    "Guarani":     None,          # não baixado (rate-limit) — cai para URL
    "Portuguesa":  "portuguesa.svg",
    "Juventude":   "juventude.svg",
    "Santo Andre": "santo-andre.png",
    "Sao Caetano": "sao-caetano.png",
    "CSA":         None,          # não baixado — cai para URL
    "Cuiaba":      "cuiaba.svg",
    "Brasiliense": "brasiliense.png",
    "Ipatinga":    "ipatinga.png",
    "America-RN":  None,          # não baixado — cai para URL
}

# URLs diretas para os 3 que não foram baixados (Wikimedia Commons)
LOGO_URL: dict[str, str] = {
    "Guarani":    "https://upload.wikimedia.org/wikipedia/commons/0/04/Guarani_Futebol_Clube_logo.svg",
    "CSA":        "https://upload.wikimedia.org/wikipedia/commons/f/fa/Centro_Sportivo_Alagoano_logo.png",
    "America-RN": "https://upload.wikimedia.org/wikipedia/commons/f/f3/Am%C3%A9rica_Futebol_Clube_%28Natal%2C_Rio_Grande_do_Norte%29_logo.svg",
}

# Carrega arquivos locais como data-URI uma única vez
_logos_dir = _ASSETS / "logos"
_LOGO_B64: dict[str, str] = {}
for _nome, _arquivo in LOGO_FILE.items():
    if _arquivo:
        _p = _logos_dir / _arquivo
        if _p.exists():
            _mime = "image/svg+xml" if _arquivo.endswith(".svg") else "image/png"
            _LOGO_B64[_nome] = f"data:{_mime};base64,{base64.b64encode(_p.read_bytes()).decode()}"

# Fallback de texto para Barueri e Gremio Prudente (sem logo disponível)
ESCUDO_FALLBACK: dict[str, tuple[str, str, str]] = {
    "Barueri":         ("BAR", "#003399", "#ffffff"),
    "Gremio Prudente": ("GRP", "#0033cc", "#ffffff"),
}

_BADGE = (
    'display:inline-flex;align-items:center;justify-content:center;'
    'width:26px;height:26px;border-radius:50%;'
    'font-size:6px;font-weight:800;letter-spacing:0.02em;'
    'margin-right:7px;vertical-align:middle;flex-shrink:0;'
)
_IMG = 'width="26" height="26" style="vertical-align:middle;margin-right:7px;flex-shrink:0;object-fit:contain;"'

def escudo_html(clube: str) -> str:
    if svg_id := ESCUDO_ID.get(clube):
        return f'<svg width="26" height="26" style="vertical-align:middle;margin-right:7px;flex-shrink:0;"><use href="#{svg_id}"/></svg>'
    if data_uri := _LOGO_B64.get(clube):
        return f'<img src="{data_uri}" {_IMG} />'
    if url := LOGO_URL.get(clube):
        return f'<img src="{url}" {_IMG} />'
    if fallback := ESCUDO_FALLBACK.get(clube):
        sigla, bg, fg = fallback
        return f'<span style="{_BADGE}background:{bg};color:{fg};">{sigla}</span>'
    return ""

# ── encoding seguro para Windows ─────────────────────────────────────────────
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Brasileirão Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── paleta CBF ────────────────────────────────────────────────────────────────
VERDE = "#00A86B"
AMARELO = "#FFD700"
AZUL = "#003580"
VERMELHO = "#E63946"
FUNDO = "#0F1923"
CARD = "#1A2535"
TEXTO = "#F0F4F8"
TEXTO_MUTED = "#8A99A8"

# ── CSS global ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');

  html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    background-color: {FUNDO};
    color: {TEXTO};
  }}

  h1, h2, h3 {{
    font-family: 'Barlow Condensed', sans-serif !important;
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }}

  /* Cabeçalho hero */
  .hero {{
    background: linear-gradient(135deg, #0a1520 0%, #0f2d1a 60%, #0F1923 100%);
    border-bottom: 3px solid {VERDE};
    padding: 2rem 2.5rem 1.5rem;
    margin-bottom: 1.5rem;
    border-radius: 0 0 12px 12px;
  }}
  .hero-title {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 3rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    line-height: 1;
    color: {TEXTO};
  }}
  .hero-title span {{ color: {VERDE}; }}
  .hero-sub {{
    font-size: 0.95rem;
    color: {TEXTO_MUTED};
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 0.4rem;
  }}

  /* KPI tiles */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 2rem;
  }}
  @media (max-width: 900px) {{
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .hero-title {{ font-size: 2rem; }}
  }}
  .kpi-card {{
    background: {CARD};
    border: 1px solid rgba(255,255,255,0.07);
    border-top: 3px solid {VERDE};
    border-radius: 10px;
    padding: 1.2rem 1.5rem 1rem;
  }}
  .kpi-card.amarelo {{ border-top-color: {AMARELO}; }}
  .kpi-card.azul    {{ border-top-color: {AZUL}; }}
  .kpi-card.verde2  {{ border-top-color: #2ecc71; }}
  .kpi-label {{
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: {TEXTO_MUTED};
    margin-bottom: 0.5rem;
  }}
  .kpi-value {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.9rem;
    font-weight: 700;
    color: {TEXTO};
    line-height: 1.1;
  }}
  .kpi-sub {{
    font-size: 0.75rem;
    color: {TEXTO_MUTED};
    margin-top: 0.25rem;
  }}

  /* Seção títulos */
  .section-title {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {TEXTO};
    padding-bottom: 0.5rem;
    border-bottom: 2px solid rgba(0,168,107,0.3);
    margin-bottom: 1rem;
  }}
  .section-title::before {{
    content: "▍ ";
    color: {VERDE};
  }}

  /* Tabela de classificação */
  .tabela-wrap {{ overflow-x: auto; }}
  table.classificacao {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
  }}
  table.classificacao th {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {TEXTO_MUTED};
    padding: 0.5rem 0.75rem;
    text-align: center;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }}
  table.classificacao th:nth-child(2) {{ text-align: left; }}
  table.classificacao td {{
    padding: 0.55rem 0.75rem;
    text-align: center;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    color: {TEXTO};
    font-variant-numeric: tabular-nums;
  }}
  table.classificacao td:nth-child(2) {{ text-align: left; font-weight: 600; }}
  table.classificacao tr:hover td {{ background: rgba(255,255,255,0.03); }}

  /* Faixas na tabela */
  .faixa-verde td:first-child {{ border-left: 3px solid {VERDE}; }}
  .faixa-azul  td:first-child {{ border-left: 3px solid {AZUL}; }}
  .faixa-verm  td:first-child {{ border-left: 3px solid {VERMELHO}; }}

  .saldo-pos {{ color: #2ecc71; font-weight: 600; }}
  .saldo-neg {{ color: {VERMELHO}; font-weight: 600; }}

  /* Nota de cobertura */
  .nota-cobertura {{
    background: rgba(255,215,0,0.08);
    border-left: 3px solid {AMARELO};
    padding: 0.6rem 1rem;
    border-radius: 0 6px 6px 0;
    font-size: 0.82rem;
    color: {AMARELO};
    margin-bottom: 1rem;
  }}

  /* Rodapé */
  .rodape {{
    margin-top: 3rem;
    padding: 1.5rem 0;
    border-top: 1px solid rgba(255,255,255,0.08);
    text-align: center;
    font-size: 0.75rem;
    color: {TEXTO_MUTED};
  }}
  .rodape a {{ color: {VERDE}; text-decoration: none; }}
</style>
""", unsafe_allow_html=True)

# Injeta os sprites de escudos (série A + série B) uma única vez
if _SVG_SPRITE:
    st.markdown(_SVG_SPRITE, unsafe_allow_html=True)

# ── conexão ao banco ──────────────────────────────────────────────────────────
@st.cache_resource
def get_con() -> duckdb.DuckDBPyConnection:
    db_path = str(Path(__file__).parent / "brasileirao.duckdb")
    con = duckdb.connect()
    con.execute(f"ATTACH '{db_path}' AS brasileirao (READ_ONLY)")
    con.execute("USE brasileirao")
    return con


@st.cache_data
def query(_con: duckdb.DuckDBPyConnection, sql: str) -> list:
    return _con.execute(sql).fetchall()


con = get_con()

# ── temporadas disponíveis ────────────────────────────────────────────────────
temporadas_raw = query(con, "SELECT DISTINCT temporada FROM marts.classificacao ORDER BY temporada DESC")
temporadas = [r[0] for r in temporadas_raw]

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding: 1rem 0 1.5rem;">
      <div style="font-family:'Barlow Condensed',sans-serif; font-size:2.2rem;
                  font-weight:800; color:{VERDE}; letter-spacing:0.06em;">⚽ BRASILEIRÃO</div>
      <div style="font-size:0.72rem; color:{TEXTO_MUTED}; letter-spacing:0.14em;
                  text-transform:uppercase; margin-top:0.2rem;">Analytics</div>
    </div>
    """, unsafe_allow_html=True)

    temporada = st.selectbox(
        "🗓️ Temporada",
        temporadas,
        index=0,
        help="Filtra todas as seções pela temporada selecionada",
    )

    st.markdown("---")
    st.markdown(f"<div style='font-size:0.75rem; color:{TEXTO_MUTED};'>"
                "Fonte: Kaggle · Adão Duque<br>Licença GPL 2</div>",
                unsafe_allow_html=True)

# ── CABEÇALHO HERO ────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <div class="hero-title">BRASILEIRÃO <span>ANALYTICS</span></div>
  <div class="hero-sub">Campeonato Brasileiro Série A &nbsp;·&nbsp; 2003–2024
    &nbsp;·&nbsp; Temporada <strong style="color:{TEXTO}">{temporada}</strong></div>
</div>
""", unsafe_allow_html=True)

# ── SEÇÃO 1 — KPIs ───────────────────────────────────────────────────────────
campeao_rows = query(con, f"""
    SELECT clube, pontos, vitorias
    FROM marts.classificacao
    WHERE temporada = {temporada} AND posicao = 1
""")
artilheiro_rows = query(con, f"""
    SELECT clube, gols_pro
    FROM marts.classificacao
    WHERE temporada = {temporada}
    ORDER BY gols_pro DESC
    LIMIT 1
""")
media_gols_rows = query(con, f"""
    SELECT media_gols
    FROM marts.media_gols
    WHERE temporada = {temporada}
""")
mandante_rows = query(con, f"""
    SELECT pct_mandante, pct_empate, pct_visitante
    FROM marts.mandante_visitante
    WHERE temporada = {temporada}
""")

campeao = campeao_rows[0] if campeao_rows else ("-", "-", "-")
artilheiro = artilheiro_rows[0] if artilheiro_rows else ("-", "-")
media_gols_val = f"{media_gols_rows[0][0]:.2f}" if media_gols_rows else "s/d"
media_gols_nota = "" if media_gols_rows else "(dado disponível a partir de 2014)"
pct_mand = f"{mandante_rows[0][0]:.1f}%" if mandante_rows else "s/d"
pct_emp  = f"{mandante_rows[0][1]:.1f}%" if mandante_rows else ""
pct_vis  = f"{mandante_rows[0][2]:.1f}%" if mandante_rows else ""

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">🏆 Campeão</div>
    <div class="kpi-value">{campeao[0]}</div>
    <div class="kpi-sub">{campeao[1]} pts · {campeao[2]} vitórias</div>
  </div>
  <div class="kpi-card amarelo">
    <div class="kpi-label">⚽ Mais gols</div>
    <div class="kpi-value">{artilheiro[0]}</div>
    <div class="kpi-sub">{artilheiro[1]} gols marcados</div>
  </div>
  <div class="kpi-card azul">
    <div class="kpi-label">📊 Média gols/jogo</div>
    <div class="kpi-value">{media_gols_val}</div>
    <div class="kpi-sub">{media_gols_nota}</div>
  </div>
  <div class="kpi-card verde2">
    <div class="kpi-label">🏠 Vantagem mandante</div>
    <div class="kpi-value">{pct_mand}</div>
    <div class="kpi-sub">Empate {pct_emp} · Visitante {pct_vis}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── SEÇÃO 2 — CLASSIFICAÇÃO ───────────────────────────────────────────────────

st.markdown('<div class="section-title">Classificação Final</div>', unsafe_allow_html=True)

classif = query(con, f"""
    SELECT posicao, clube, pontos, vitorias + empates + derrotas AS jogos,
           vitorias, empates, derrotas, gols_pro, gols_contra, saldo
    FROM marts.classificacao
    WHERE temporada = {temporada}
    ORDER BY posicao
""")

if classif:
    linhas_html = []
    for row in classif:
        pos, clube, pts, j, v, e, d, gp, gc, sg = row
        if pos <= 4:
            cls = "faixa-verde"
        elif pos <= 6:
            cls = "faixa-azul"
        elif pos >= len(classif) - 3:
            cls = "faixa-verm"
        else:
            cls = ""
        sg_cls = "saldo-pos" if sg > 0 else ("saldo-neg" if sg < 0 else "")
        sg_txt = f"+{sg}" if sg > 0 else str(sg)
        linhas_html.append(f"""
        <tr class="{cls}">
          <td>{pos}</td>
          <td style="white-space:nowrap">{escudo_html(clube)}{clube}</td>
          <td><strong>{pts}</strong></td>
          <td>{j}</td><td>{v}</td><td>{e}</td><td>{d}</td>
          <td>{gp}</td><td>{gc}</td>
          <td class="{sg_cls}">{sg_txt}</td>
        </tr>""")

    st.markdown(f"""
    <div class="tabela-wrap">
    <table class="classificacao">
      <thead><tr>
        <th>Pos</th><th>Clube</th><th>P</th>
        <th>J</th><th>V</th><th>E</th><th>D</th>
        <th>GP</th><th>GC</th><th>SG</th>
      </tr></thead>
      <tbody>{''.join(linhas_html)}</tbody>
    </table>
    </div>
    <div style="font-size:0.72rem; margin-top:0.5rem; color:{TEXTO_MUTED}">
      <span style="color:{VERDE}">▍</span> Libertadores &nbsp;
      <span style="color:{AZUL}">▍</span> Sul-Americana &nbsp;
      <span style="color:{VERMELHO}">▍</span> Rebaixamento
    </div>
    """, unsafe_allow_html=True)

# ── SEÇÃO 3 — HISTÓRICO DE GOLS ───────────────────────────────────────────────
st.markdown("")
st.markdown('<div class="section-title">Histórico — Média de Gols por Jogo</div>',
            unsafe_allow_html=True)

st.markdown('<div class="nota-cobertura">⚠️ Dados de gols individuais disponíveis apenas a partir de 2014.</div>',
            unsafe_allow_html=True)

gols_hist = query(con, """
    SELECT temporada, media_gols
    FROM marts.media_gols
    ORDER BY temporada
""")

if gols_hist:
    anos = [r[0] for r in gols_hist]
    medias = [r[1] for r in gols_hist]
    media_geral = sum(medias) / len(medias)

    fig_gols = go.Figure()
    fig_gols.add_trace(go.Scatter(
        x=anos, y=medias, mode="lines+markers",
        line=dict(color=VERDE, width=2.5),
        marker=dict(size=7, color=VERDE, line=dict(color=FUNDO, width=2)),
        fill="tozeroy",
        fillcolor="rgba(0,168,107,0.10)",
        name="Média gols/jogo",
        hovertemplate="<b>%{x}</b><br>%{y:.2f} gols/jogo<extra></extra>",
    ))
    fig_gols.add_hline(
        y=media_geral, line_dash="dot", line_color=AMARELO, opacity=0.7,
        annotation_text=f"Média histórica: {media_geral:.2f}",
        annotation_position="top right",
        annotation_font_color=AMARELO,
    )
    fig_gols.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(color=TEXTO, family="Inter"),
        xaxis=dict(showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   title="Gols por jogo", range=[0, max(medias) * 1.2]),
        margin=dict(l=50, r=20, t=20, b=40),
        height=320,
        showlegend=False,
        hovermode="x unified",
    )
    st.plotly_chart(fig_gols, width='stretch')

# ── SEÇÃO 4 — VANTAGEM DO MANDANTE ───────────────────────────────────────────
st.markdown('<div class="section-title">Vantagem do Mandante — Série histórica</div>',
            unsafe_allow_html=True)

mandante_hist = query(con, """
    SELECT temporada, pct_mandante, pct_empate, pct_visitante
    FROM marts.mandante_visitante
    ORDER BY temporada
""")

if mandante_hist:
    anos_m = [r[0] for r in mandante_hist]
    pct_m  = [r[1] for r in mandante_hist]
    pct_e  = [r[2] for r in mandante_hist]
    pct_v  = [r[3] for r in mandante_hist]

    fig_mand = go.Figure()
    fig_mand.add_trace(go.Bar(
        name="Mandante", x=anos_m, y=pct_m,
        marker_color=VERDE,
        hovertemplate="%{y:.1f}%<extra>Mandante</extra>",
    ))
    fig_mand.add_trace(go.Bar(
        name="Empate", x=anos_m, y=pct_e,
        marker_color=TEXTO_MUTED,
        hovertemplate="%{y:.1f}%<extra>Empate</extra>",
    ))
    fig_mand.add_trace(go.Bar(
        name="Visitante", x=anos_m, y=pct_v,
        marker_color=AZUL,
        hovertemplate="%{y:.1f}%<extra>Visitante</extra>",
    ))
    fig_mand.update_layout(
        barmode="stack",
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(color=TEXTO, family="Inter"),
        xaxis=dict(showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   title="% das partidas", ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1,
                    font=dict(size=11)),
        margin=dict(l=50, r=20, t=40, b=40),
        height=340,
        hovermode="x unified",
    )
    st.plotly_chart(fig_mand, width='stretch')

# ── SEÇÃO 5 — CARTÕES ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Cartões por Clube</div>',
            unsafe_allow_html=True)

cartoes_cob = query(con, f"""
    SELECT count(*) FROM marts.cartoes_clube WHERE temporada = {temporada}
""")
tem_cartoes = cartoes_cob[0][0] > 0 if cartoes_cob else False

if not tem_cartoes:
    st.markdown('<div class="nota-cobertura">⚠️ Dados de cartões disponíveis apenas a partir de 2014.</div>',
                unsafe_allow_html=True)
else:
    tipo_cartao = st.radio(
        "Tipo de cartão",
        ["🟡 Amarelos por jogo", "🔴 Vermelhos por jogo"],
        horizontal=True,
        label_visibility="collapsed",
    )
    coluna = "amarelos_por_jogo" if "Amarelo" in tipo_cartao else "vermelhos_por_jogo"
    cor_barra = AMARELO if "Amarelo" in tipo_cartao else VERMELHO

    cartoes = query(con, f"""
        SELECT clube, {coluna}
        FROM marts.cartoes_clube
        WHERE temporada = {temporada}
        ORDER BY {coluna} DESC
        LIMIT 10
    """)

    if cartoes:
        clubes_c = [r[0] for r in reversed(cartoes)]
        vals_c   = [r[1] for r in reversed(cartoes)]
        label_c  = "Amarelos/jogo" if "Amarelo" in tipo_cartao else "Vermelhos/jogo"

        fig_cart = go.Figure(go.Bar(
            x=vals_c, y=clubes_c, orientation="h",
            marker_color=cor_barra,
            text=[f"{v:.2f}" for v in vals_c],
            textposition="outside",
            textfont=dict(color=TEXTO, size=11),
            hovertemplate="%{y}<br>%{x:.2f} " + label_c + "<extra></extra>",
        ))
        fig_cart.update_layout(
            paper_bgcolor=CARD, plot_bgcolor=CARD,
            font=dict(color=TEXTO, family="Inter"),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                       title=label_c),
            yaxis=dict(showgrid=False),
            margin=dict(l=130, r=60, t=20, b=40),
            height=360,
            showlegend=False,
        )
        st.plotly_chart(fig_cart, width='stretch')

# ── SEÇÃO 6 — POSSE DE BOLA ───────────────────────────────────────────────────
st.markdown('<div class="section-title">Posse de Bola por Clube</div>',
            unsafe_allow_html=True)

posse_cob = query(con, f"""
    SELECT count(*) FROM marts.posse_media WHERE temporada = {temporada}
""")
tem_posse = posse_cob[0][0] > 0 if posse_cob else False

if not tem_posse:
    st.markdown('<div class="nota-cobertura">⚠️ Dados de posse de bola disponíveis apenas para 2014–2023.</div>',
                unsafe_allow_html=True)
else:
    posse = query(con, f"""
        SELECT clube, posse_media
        FROM marts.posse_media
        WHERE temporada = {temporada}
        ORDER BY posse_media DESC
        LIMIT 10
    """)

    if posse:
        clubes_p = [r[0] for r in reversed(posse)]
        vals_p   = [r[1] for r in reversed(posse)]

        # gradiente de cor por % de posse
        fig_posse = go.Figure(go.Bar(
            x=vals_p, y=clubes_p, orientation="h",
            marker=dict(
                color=vals_p,
                colorscale=[[0, "#1A5C3A"], [0.5, VERDE], [1, "#7FFFC4"]],
                cmin=40, cmax=60,
                colorbar=dict(
                    title=dict(text="% posse", side="right"),
                    tickformat=".0f",
                    ticksuffix="%",
                    thickness=12,
                ),
            ),
            text=[f"{v:.1f}%" for v in vals_p],
            textposition="outside",
            textfont=dict(color=TEXTO, size=11),
            hovertemplate="%{y}<br>%{x:.1f}% posse média<extra></extra>",
        ))
        fig_posse.add_vline(
            x=50, line_dash="dot", line_color=AMARELO, opacity=0.6,
            annotation_text="50%", annotation_font_color=AMARELO,
        )
        fig_posse.update_layout(
            paper_bgcolor=CARD, plot_bgcolor=CARD,
            font=dict(color=TEXTO, family="Inter"),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                       title="Posse média (%)", ticksuffix="%", range=[30, 65]),
            yaxis=dict(showgrid=False),
            margin=dict(l=130, r=80, t=20, b=40),
            height=360,
            showlegend=False,
        )
        st.plotly_chart(fig_posse, width='stretch')

# ── RODAPÉ ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="rodape">
  Fonte: <a href="https://www.kaggle.com/datasets/adaoduque/campeonato-brasileiro-de-futebol"
  target="_blank">Kaggle · Adão Duque</a> · Licença GPL 2 ·
  <a href="https://github.com/wappontes/brasileirao" target="_blank">GitHub</a>
  <br>
  Dashboard gerado a partir da camada marts — nenhum cálculo realizado aqui.
</div>
""", unsafe_allow_html=True)
