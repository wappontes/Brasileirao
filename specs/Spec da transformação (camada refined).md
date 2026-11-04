# Spec da transformação (camada refined)

## Contexto

Projeto final do curso Engenheiro de Dados Junior. Dataset: Campeonato Brasileiro 2003 a 2024
(github.com/adaoduque/Brasileirao_Dataset).

Pré-requisito: ingestão concluída, com o schema `raw` e 57.169 registros.

Artefato: `pipeline/transformacao.py`, executado com:

```
uv run python -m pipeline.transformacao
```

## 1. Escopo

- Lê de `raw` e escreve em `refined`. Nunca escreve em `raw`.
- Entram: `partidas`, `estatisticas`, `gols`, `cartoes`.
- Tudo acontece numa transação. Se uma validação que bloqueia falhar, nada é gravado em `refined`.

## 2. Nomes

Mapa completo, aplicado pelo código:

- `partidas`: `ID` → `partida_id`, `rodata` → `rodada`, `data` → `data_partida`, `hora` → `hora_partida`, `vencedor` → `vencedor_original`, `mandante_Placar` → `gols_mandante`, `visitante_Placar` → `gols_visitante`, `mandante_Estado` → `uf_mandante`, `visitante_Estado` → `uf_visitante`. Os demais nomes ficam iguais.
- `estatisticas`: `rodata` → `rodada`, `posse_de_bola` → `posse_bola`, `cartao_amarelo` → `cartoes_amarelos`, `cartao_vermelho` → `cartoes_vermelhos`, `chutes_no_alvo` → `chutes_no_alvo` (mantido).
- `gols`: `rodata` → `rodada`, `tipo_de_gol` → `tipo_gol`. São criadas as colunas `acrescimo`.
- `cartoes`: `rodata` → `rodada`. São criadas as colunas `acrescimo`.

## 3. Tipos

- `partida_id`, `rodada`, placares, contagens de estatísticas e `num_camisa`: `INTEGER`.
- `data_partida`: `DATE`, formato `%d/%m/%Y`.
- `hora_partida`: `TIME`, formato `%H:%M`.
- `posse_bola` e `precisao_passes`: `DECIMAL(5,2)`. O `%` é removido antes da conversão.
- `mandante`, `visitante`, `clube`, `atleta`, `arena`, UFs, técnicos, `cartao`, `posicao` e `tipo_gol`: texto.

## 4. Conversão que falha

Para tudo, sem `TRY_CAST`, `try_strptime` ou `errors='coerce'`. A mensagem mostra a tabela e o valor. `refined` fica como estava antes da execução.

Motivo: um nulo criado pela conversão é indistinguível de um nulo verdadeiro da fonte.

## 5. Limpeza de texto

- `arena`: U+00A0 vira espaço, e espaços das bordas saem.
- Demais colunas de texto: sem alteração.

## 6. Campos derivados

- `resultado`: `mandante`, `visitante` ou `empate`, calculado a partir dos placares.
- `temporada`: ano de `data_partida`, exceto partidas com data em janeiro ou fevereiro de 2021, que pertencem à temporada 2020 (ver seção 9).
- `gols_registrados`: verdadeiro se a partida tem pelo menos uma linha em `gols`.
- `cartoes_registrados`: verdadeiro se a partida tem pelo menos uma linha em `cartoes`.
- `minuto` e `acrescimo`: `90+2` vira `minuto = 90` e `acrescimo = 2`. Valor sem acréscimo deixa `acrescimo` nulo.

Motivo dos campos de cobertura: sem eles, "não houve gol" e "não foi registrado" ficam iguais.

## 7. Temporada

Partidas com `data_partida` em janeiro ou fevereiro de 2021 pertencem à temporada 2020.

Medido nos arquivos: são 112 partidas nessa condição. Elas são as rodadas 28 a 38 do Brasileirão 2020 (10 por rodada), mais uma partida da rodada 1 e uma da rodada 23. A temporada 2020 fecha em 380 com essa regra.

## 8. Nulos

Nenhuma linha é apagada por ter nulo, e nenhum nulo é preenchido.

Posse de bola (`posse_bola`): 10.750 nulos. São 9.212 vazios e 1.538 com o texto `None`. Distribuição por temporada, medida:

| Temporada | Nulos | Linhas |
|---|---|---|
| 2003 a 2013 | todas | 1.104 / 1.104 / 924 / 760 cada a partir de 2006 |
| 2014 | 728 | 760 |
| 2015, 2016, 2018, 2021, 2022, 2023 | 0 | 760 |
| 2017 e 2020 | 2 | 760 |
| 2019 | 46 | 760 |
| 2024 | todas | 760 |

Nos anos 2014 a 2020, a ausência acontece por partida inteira: os dois clubes do mesmo jogo aparecem com posse nula. A causa não está registrada na fonte.

Precisão de passes (`precisao_passes`): 13.058 nulos, incluindo os 3.846 com `None`. A distribuição por temporada ainda não foi medida.

Motivo: a posse ausente é dado faltante, e não zero. Preencher com zero criaria um valor falso.

## 9. Exceções conhecidas

**9.1 Partida 1114** (24/04/2005, Brasiliense 0 x 1 Vasco). Na fonte, `vencedor` é `-`, que significa empate, mas o placar dá vitória do Vasco. Decisão: `resultado` vem só do placar, e `vencedor_original` mantém `-` como veio. Não alterei a fonte, porque não confirmei o resultado em outra fonte.

**9.2 Temporada 2016** tem 379 partidas no arquivo, e o calendário tem 380. A partida que falta não foi identificada. Decisão: registrar a anomalia, sem corrigir.

**9.3 Temporadas 2003, 2004 e 2005** têm 552, 552 e 462 partidas. O calendário era outro naqueles anos, então a regra de 380 não se aplica a eles.

**9.4 Gols e cartões de 2003 a 2013.** Gols não foram registrados para 4.269 partidas com placar diferente de 0 a 0. Partidas 0 a 0 sem gol são normais. Cartões não foram registrados para nenhuma partida desse período (4.606). Em 2014 a 2024, 63 partidas não têm cartão registrado. Essas partidas ficam com `cartoes_registrados = false`, e a causa não está no arquivo.

## 10. Validações

**Bloqueiam a gravação** (qualquer falha para a transformação e não grava nada):

- minuto fora do padrão `N` ou `N+N` em `gols` e `cartoes`;
- `partida_id` repetido em `partidas`;
- órfãos em `estatisticas`, `gols` e `cartoes`;
- partida sem exatamente duas linhas em `estatisticas`;
- chave `(partida_id, clube)` repetida em `estatisticas`;
- clube que não jogou a partida, em `estatisticas`, `gols` ou `cartoes`.

**Avisos** (não bloqueiam; são listados na saída):

- `vencedor_original` diverge do placar. Hoje há 1 caso, a partida 1114.

## 11. Duplicatas

Linhas inteiras repetidas são removidas com `DISTINCT`. Medido na ingestão: zero em todas as tabelas.

## 12. Saída na tela

- Tabela com linhas em `raw`, linhas em `refined`, linhas que saíram e o esperado.
- Nulos mantidos em `posse_bola` e `precisao_passes`.
- Partidas sem gol e sem cartão registrado.
- Temporadas com número de partidas diferente de 380.
- Avisos de vencedor.

## 13. Reexecução

`CREATE OR REPLACE` dentro da transação. Rodar duas vezes dá a mesma saída.

## Critérios de aceite

- Contagens em `refined`: partidas 8.785, estatisticas 17.570, gols 9.861, cartoes 20.953. Nenhuma linha sai.
- Órfãos: zero nas três ligações.
- Chave `(partida_id, clube)` em `estatisticas`: sem repetição.
- `resultado` é `empate` exatamente quando os placares são iguais.
- `posse_bola` nula: 10.750.
- `temporada`: 380 partidas em todas, exceto 2003 (552), 2004 (552), 2005 (462) e 2016 (379).
- Avisos de vencedor: apenas a partida 1114.
- Rodar duas vezes dá a mesma saída.

## Mapa de colunas em refined

- `partidas`: `partida_id`, `rodada`, `data_partida`, `hora_partida`, `mandante`, `visitante`, `formacao_mandante`, `formacao_visitante`, `tecnico_mandante`, `tecnico_visitante`, `vencedor_original`, `arena`, `gols_mandante`, `gols_visitante`, `uf_mandante`, `uf_visitante`, `resultado`, `temporada`, `gols_registrados`, `cartoes_registrados`.
- `estatisticas`: `partida_id`, `rodada`, `clube`, `chutes`, `chutes_no_alvo`, `posse_bola`, `passes`, `precisao_passes`, `faltas`, `cartoes_amarelos`, `cartoes_vermelhos`, `impedimentos`, `escanteios`.
- `gols`: `partida_id`, `rodada`, `clube`, `atleta`, `minuto`, `acrescimo`, `tipo_gol`.
- `cartoes`: `partida_id`, `rodada`, `clube`, `cartao`, `atleta`, `num_camisa`, `posicao`, `minuto`, `acrescimo`.