# Pipeline Brasileirão

Pipeline de dados em Python sobre o histórico do Campeonato Brasileiro de Futebol, de 2003 a 2024. Projeto final do curso Pipeline Olist.

> **Status:** em construção. A camada `raw` (ingestão) está pronta. As camadas `refined` (transformação) e `marts` (indicadores) estão em desenvolvimento.

## Fonte dos dados

Os dados vêm do repositório [adaoduque/Brasileirao_Dataset](https://github.com/adaoduque/Brasileirao_Dataset), de autoria de adaoduque.

**Licença:** não confirmada. Este repositório não inclui os arquivos CSV por esse motivo.

## Como obter os CSVs

Os quatro arquivos não estão neste repositório. Para rodar o projeto, baixe-os do repositório de origem e coloque-os na pasta `raw/`:

- `campeonato-brasileiro-full.csv`
- `campeonato-brasileiro-estatisticas-full.csv`
- `campeonato-brasileiro-gols.csv`
- `campeonato-brasileiro-cartoes.csv`

Os arquivos devem estar em UTF-8, sem alterações. A ingestão confere os nomes das colunas e para se algo estiver diferente.

## Como rodar do zero

Pré-requisitos: [uv](https://docs.astral.sh/uv/) instalado.

```bash
uv sync
uv run python -m pipeline.ingestao
```

A saída esperada é:

raw.partidas 8.785
raw.estatisticas 17.570
raw.gols 9.861
raw.cartoes 20.953
total 57.169


O banco é o arquivo `brasileirao.duckdb`, criado na raiz do projeto.

## Camadas

| Camada | Schema | O que contém | Status |
|---|---|---|---|
| Bruta | `raw` | Espelho fiel dos quatro CSVs. Todas as colunas como texto, sem alterações | Pronta |
| Transformada | `refined` | Tipos convertidos, nomes padronizados, colunas derivadas | Em desenvolvimento |
| Indicadores | `marts` | Tabelas agregadas para responder perguntas específicas | Em desenvolvimento |

## Limitações do dado

Antes de usar os dados, conheça estes pontos. Eles estão medidos nos arquivos:

- **Posse de bola e precisão de passes** não foram registradas entre 2003 e 2013, e aparecem vazias ou como `None` nesse período. Os valores preenchidos vêm com `%`.
- **Cartões** não foram registrados entre 2003 e 2013. Em 2014 a 2024, 63 partidas não têm nenhum cartão registrado.
- **Gols** não foram registrados para as partidas de 2003 a 2013 que não terminaram 0 a 0. Por isso, o total de gols desse período é menor que o real.
- **2016** tem 379 partidas no arquivo. A temporada tem 380. A partida que falta não foi identificada.
- **2020 e 2021:** parte das partidas da temporada de 2020 está registrada com data de 2021 (janeiro e fevereiro). A transformação atribui essas partidas à temporada correta.
- **Minuto com acréscimo** aparece como `90+2`, `45+1` etc. Não é um número inteiro.
- **Arena:** alguns nomes começam com um espaço não separável (U+00A0).

## Estrutura do projeto

pipeline/ código do pipeline (db.py, ingestao.py)
specs/ especificações de cada camada
raw/ CSVs de origem (não versionados)