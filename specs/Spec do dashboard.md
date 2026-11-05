# Spec do Dashboard — Campeonato Brasileiro de Futebol

## 1. Objetivo

Exibir indicadores analíticos do Campeonato Brasileiro (2003–2024) a partir
exclusivamente da camada **marts** do banco `brasileirao.duckdb`. O dashboard
não realiza nenhum cálculo — apenas executa `SELECT` nas tabelas marts e
apresenta os resultados com gráficos e tabelas interativas.

## 2. Restrições da camada de visualização

| Restrição | Detalhe |
|---|---|
| Fonte de dados | Somente `marts.*` via DuckDB |
| Operações permitidas | `SELECT` puro; sem `JOIN`, `GROUP BY`, `CASE`, `SUM` etc. |
| Arquivos lidos | `brasileirao.duckdb` (mesmo diretório do `app.py`) |
| Framework | Streamlit |
| Dependências extras | plotly (gráficos interativos); `st.plotly_chart` usa `width='stretch'` (substitui `use_container_width`, depreciado) |

## 3. Tabelas marts disponíveis

| Tabela | Colunas principais | Cobertura |
|---|---|---|
| `marts.classificacao` | temporada, clube, posicao, pontos, vitorias, empates, derrotas, gols_pro, gols_contra, saldo | 2003–2024 |
| `marts.mandante_visitante` | temporada, partidas, vitorias_mandante, empates, vitorias_visitante, pct_mandante, pct_empate, pct_visitante | 2003–2024 |
| `marts.media_gols` | temporada, partidas_com_gol, total_gols, media_gols | 2014–2024 |
| `marts.posse_media` | temporada, clube, partidas_com_posse, posse_media | onde há dado (2014–2023) |
| `marts.cartoes_clube` | temporada, clube, partidas, amarelos, vermelhos, amarelos_por_jogo, vermelhos_por_jogo | 2014–2024 |

## 4. Layout e seções

### 4.1 Cabeçalho
- Título: **Brasileirão Analytics** com brasão estilizado em texto
- Subtítulo: "Campeonato Brasileiro Série A · 2003–2024"
- Seletor de temporada global (sidebar): `selectbox` ou `slider` para filtrar
  todas as seções pela temporada selecionada (padrão: temporada mais recente)

### 4.2 Seção 1 — KPIs da Temporada
Quatro métricas em destaque (tiles grandes) para a temporada selecionada:
- **Campeão** — clube na posição 1
- **Artilheiro coletivo** — clube com mais gols_pro
- **Média de gols/jogo** — de `marts.media_gols` (exibir "s/d" para 2003–2013)
- **Vantagem de mando** — percentual de vitórias mandantes

### 4.3 Seção 2 — Tabela de Classificação
Tabela completa da temporada selecionada, colunas:
`Pos | Clube | P | J | V | E | D | GP | GC | SG`

Regras visuais:
- Escudo do clube exibido antes do nome, via SVG sprite inline (`assets/escudos.svg` + `assets/escudos-b.svg`).
  Times sem escudo no sprite usam arquivo local base64 de `assets/logos/`, depois URL direta do Wikimedia Commons,
  e por último um badge circular com sigla colorida. Cobertura atual: 43 dos 45 times do dataset.
- Top 4: faixa verde (Libertadores)
- 5°–6°: faixa azul (Sul-Americana)
- Últimos 4: faixa vermelha (rebaixamento)
- Coluna `SG` colorida: verde se positivo, vermelho se negativo

### 4.4 Seção 3 — Histórico de Gols por Temporada
Gráfico de linhas: média de gols por jogo × temporada (2014–2024).
Nota visível: "Dados de gols indisponíveis para 2003–2013."

### 4.5 Seção 4 — Vantagem do Mandante
Gráfico de barras empilhadas 100%: % vitórias mandante / empate / visitante
por temporada. Série histórica completa (2003–2024).

### 4.6 Seção 5 — Cartões por Clube
Para a temporada selecionada: gráfico de barras horizontais com os 10 clubes
com mais cartões amarelos por jogo.
Toggle para alternar entre amarelos e vermelhos.

### 4.7 Seção 6 — Posse de Bola
Para a temporada selecionada: gráfico de barras com os 10 clubes com maior
posse média (onde disponível: 2014–2023).
Nota visível quando temporada fora da cobertura.

### 4.8 Rodapé
- Fonte: Kaggle / Adão Duque · Licença GPL 2
- Link GitHub do projeto
- "Dashboard gerado a partir da camada marts — nenhum cálculo realizado aqui"

## 5. Paleta e identidade visual

Inspirada nas cores do Campeonato Brasileiro (CBF):

| Token | Cor | Uso |
|---|---|---|
| `verde_cbf` | `#00A86B` | Acento principal, top 4 |
| `amarelo_cbf` | `#FFD700` | Destaques, cartões amarelos |
| `azul_cbf` | `#003580` | Sul-Americana, elementos secundários |
| `vermelho` | `#E63946` | Rebaixamento, cartões vermelhos |
| `fundo_escuro` | `#0F1923` | Fundo do tema escuro |
| `fundo_card` | `#1A2535` | Cards no tema escuro |

Fonte display: **Barlow Condensed** (impacto, remete a placar/estadio)
Fonte corpo: **Inter** (legibilidade em tabelas e labels)

## 6. Configuração Streamlit

```toml
# .streamlit/config.toml
[theme]
base = "dark"
primaryColor = "#00A86B"
backgroundColor = "#0F1923"
secondaryBackgroundColor = "#1A2535"
textColor = "#F0F4F8"
font = "sans serif"
```

## 7. Arquivo principal

`app.py` na raiz do projeto, executado com:
```bash
uv run streamlit run app.py
```

## 8. Critério de aceite

- [x] Roda sem erro com `uv run streamlit run app.py`
- [x] Todas as 6 seções renderizam com a temporada padrão (2024)
- [x] Trocar a temporada na sidebar atualiza todas as seções
- [x] Nenhum cálculo fora do banco (apenas SELECT nos marts)
- [x] Notas de cobertura exibidas quando dados indisponíveis
- [ ] README menciona `uv run streamlit run app.py` como comando de execução
- [x] Escudos exibidos antes do nome de cada clube na tabela de classificação
