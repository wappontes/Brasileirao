# Pipeline Brasileirão

Pipeline de dados em Python sobre o histórico do Campeonato Brasileiro de Futebol, de 2003 a 2024. Projeto final do curso Pipeline Olist.

> **Status:** ingestão (`raw`) e transformação (`refined`) prontas. Indicadores (`marts`) em desenvolvimento.

## Fonte dos dados

Os dados vêm do repositório [adaoduque/Brasileirao_Dataset](https://github.com/adaoduque/Brasileirao_Dataset), de autoria de adaoduque.

**Licença:** não confirmada. Por isso, os CSVs não estão neste repositório.

## Como obter os CSVs

Baixe estes quatro arquivos do repositório de origem e coloque-os na pasta `raw/`, sem alterações:

- `campeonato-brasileiro-full.csv`
- `campeonato-brasileiro-estatisticas-full.csv`
- `campeonato-brasileiro-gols.csv`
- `campeonato-brasileiro-cartoes.csv`

Os arquivos devem estar em UTF-8. A ingestão confere os nomes das colunas e para se algo estiver diferente.

## Como rodar do zero

Pré-requisito: [uv](https://docs.astral.sh/uv/) instalado.

```bash
uv sync
uv run python -m pipeline.ingestao
uv run python -m pipeline.transformacao
```

Saída esperada da ingestão:

```
raw.partidas          8.785
raw.estatisticas     17.570
raw.gols              9.861
raw.cartoes          20.953
total                57.169
```

O banco é o arquivo `brasileirao.duckdb`, criado na raiz do projeto.

## Camadas

| Camada | Schema | O que contém | Status |
|---|---|---|---|
| Bruta | `raw` | Espelho dos quatro CSVs. Todas as colunas como texto | Pronta |
| Transformada | `refined` | Tipos convertidos, nomes padronizados, campos derivados e marcadores de cobertura | Pronta |
| Indicadores | `marts` | Tabelas agregadas para perguntas específicas | Em desenvolvimento |

As regras de cada camada estão em `specs/`.

## Limitações do dado

Estes pontos estão medidos nos arquivos. Antes de usar os dados em indicadores, leia a lista inteira.

- **Posse de bola** é nula em 10.750 linhas. Ela não existe em nenhuma partida de 2003 a 2013 nem em 2024. Em 2014 a 2020, aparece ausente em partidas específicas: 728 linhas em 2014, 46 em 2019, 2 em 2017 e 2 em 2020. A causa não está registrada na fonte.
- **Precisão de passes** é nula em 13.058 linhas, incluindo valores escritos como `None`.
- **Cartões** não foram registrados para nenhuma partida de 2003 a 2013. Em 2014 a 2024, 63 partidas não têm cartão registrado. A coluna `cartoes_registrados` indica quais partidas têm o evento.
- **Gols** não foram registrados para 4.269 partidas de 2003 a 2013 que não terminaram 0 a 0. A coluna `gols_registrados` indica quais partidas têm o evento.
- **Calendário:** 2003, 2004 e 2005 têm 552, 552 e 462 partidas, porque o calendário era outro. 2016 tem 379 partidas; a partida que falta não foi identificada.
- **Temporada 2020:** partidas das rodadas 28 a 38, mais uma da rodada 1 e uma da rodada 23, estão datadas em janeiro e fevereiro de 2021. A transformação as atribui à temporada 2020, que então fecha em 380 partidas.
- **Partida 1114** (24/04/2005, Brasiliense 0 x 1 Vasco): na fonte, `vencedor` é `-`, que significa empate, mas o placar dá vitória do Vasco. O campo `resultado` segue o placar. O valor original fica em `vencedor_original`.
- **Minuto com acréscimo:** `90+2` é separado em `minuto` e `acrescimo`.

## Estrutura do projeto

```
pipeline/       código do pipeline (db.py, ingestao.py, transformacao.py)
specs/          especificações de cada camada, com decisões e critérios de aceite
raw/            CSVs de origem (não versionados)
```

