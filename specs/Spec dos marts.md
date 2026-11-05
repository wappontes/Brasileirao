# Spec da camada marts

## Contexto

Pré-requisito: transformação concluída, com o schema `refined` e 57.169 registros.

Executor: `pipeline/marts.py`, chamado com:

```
uv run python -m pipeline.marts
```

Cada arquivo em `sql/marts/` vira uma tabela em `marts`. O executor cria o schema, lê os arquivos em ordem alfabética e executa cada um numa transação única.

## Regras que valem para todos os marts

- Nenhum cálculo fora do SQL. O Python só executa os arquivos.
- Mart vazio para a execução.
- Se qualquer mart falhar, o schema `marts` volta ao estado anterior.
- `CREATE OR REPLACE`: rodar de novo dá o mesmo resultado.
- Não usa `gols` nem `cartoes` sem filtrar pela coluna de cobertura.
- Não usa `posse_bola` sem excluir nulos.

## Palavras com definição fechada

| Palavra | Definição |
|---|---|
| **Partida válida** | Partida com `resultado` em `mandante`, `visitante` ou `empate`. Todas as partidas de `refined.partidas` são válidas, porque o resultado vem do placar |
| **Pontos** | Vitória: 3. Empate: 1. Derrota: 0 |
| **Temporada** | A coluna `temporada` de `refined.partidas`, não o ano de `data_partida` |
| **Gol registrado** | Partida com `gols_registrados = true` |
| **Cartão registrado** | Partida com `cartoes_registrados = true` |

## Mart 01 · Classificação por temporada

**Arquivo:** `sql/marts/01_classificacao.sql`
**Grão:** um clube em uma temporada.
**Pergunta:** quantos pontos cada clube fez em cada temporada?

Colunas:

| Coluna | Conteúdo |
|---|---|
| `temporada` | Ano da temporada |
| `clube` | Nome do clube |
| `jogos` | Partidas disputadas |
| `vitorias` | Partidas vencidas |
| `empates` | Partidas empatadas |
| `derrotas` | Partidas perdidas |
| `gols_pro` | Gols marcados (pelo placar) |
| `gols_contra` | Gols sofridos (pelo placar) |
| `saldo` | `gols_pro - gols_contra` |
| `pontos` | `vitorias * 3 + empates` |
| `posicao` | Posição no ranking da temporada (maior pontuação primeiro; empate pelo saldo) |

Critérios:
- `sum(jogos)` por temporada = número de partidas × 2.
- `sum(pontos)` por temporada = número de vitórias × 6 + número de empates × 2.
- `posicao` vai de 1 ao número de clubes naquela temporada.

## Mart 02 · Mandante x visitante

**Arquivo:** `sql/marts/02_mandante_visitante.sql`
**Grão:** uma temporada.
**Pergunta:** o mandante ganha mais que o visitante?

Colunas:

| Coluna | Conteúdo |
|---|---|
| `temporada` | Ano da temporada |
| `partidas` | Total de partidas |
| `vitorias_mandante` | Partidas vencidas pelo mandante |
| `empates` | Empates |
| `vitorias_visitante` | Partidas vencidas pelo visitante |
| `pct_mandante` | `vitorias_mandante / partidas`, em %, uma casa |
| `pct_empate` | `empates / partidas`, em %, uma casa |
| `pct_visitante` | `vitorias_visitante / partidas`, em %, uma casa |

Critério: `vitorias_mandante + empates + vitorias_visitante = partidas` em toda linha.

## Mart 03 · Média de gols por jogo

**Arquivo:** `sql/marts/03_media_gols.sql`
**Grão:** uma temporada.
**Pergunta:** quantos gols há por jogo, por temporada?

Apenas partidas com `gols_registrados = true`.

Colunas:

| Coluna | Conteúdo |
|---|---|
| `temporada` | Ano da temporada |
| `partidas_com_gol` | Partidas com `gols_registrados = true` |
| `total_gols` | Total de gols |
| `media_gols` | `total_gols / partidas_com_gol`, duas casas |

Critério: 2003 a 2013 não aparecem no resultado, ou aparecem com `partidas_com_gol` menor que o total de partidas da temporada.

## Mart 04 · Posse média por clube

**Arquivo:** `sql/marts/04_posse_media.sql`
**Grão:** um clube em uma temporada.
**Pergunta:** qual é a posse média de cada clube por temporada?

Apenas linhas com `posse_bola` não nulo.

Colunas:

| Coluna | Conteúdo |
|---|---|
| `temporada` | Ano da temporada |
| `clube` | Nome do clube |
| `partidas_com_posse` | Linhas com `posse_bola` não nulo |
| `posse_media` | Média de `posse_bola`, uma casa |

Critério: 2003 a 2013 e 2024 não aparecem, porque não têm nenhuma linha com `posse_bola` preenchida.

## Mart 05 · Cartões por clube

**Arquivo:** `sql/marts/05_cartoes_clube.sql`
**Grão:** um clube em uma temporada.
**Pergunta:** quantos cartões cada clube recebe por temporada?

Apenas partidas com `cartoes_registrados = true`.

Colunas:

| Coluna | Conteúdo |
|---|---|
| `temporada` | Ano da temporada |
| `clube` | Nome do clube |
| `partidas` | Partidas com cartão registrado |
| `amarelos` | Total de cartões amarelos |
| `vermelhos` | Total de cartões vermelhos |
| `amarelos_por_jogo` | `amarelos / partidas`, duas casas |
| `vermelhos_por_jogo` | `vermelhos / partidas`, duas casas |

Critério: 2003 a 2013 não aparecem.