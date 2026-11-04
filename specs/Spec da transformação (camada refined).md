CONTEXTO
Mesmo projeto. A ingestão já criou o schema raw com as quatro tabelas.

ARTEFATO A PRODUZIR
pipeline/transformacao.py, executável com:
  uv run python -m pipeline.transformacao

SPEC

1. ESCOPO
   Lê de raw, escreve em refined. Nunca escreve em raw.
   Entram: partidas, estatisticas, gols, cartoes.

2. NOMES
   Mapa completo na seção 12.

3. TIPOS
   partidas.ID                 -> partida_id INTEGER
   partidas.rodata             -> rodada INTEGER
   partidas.data               -> data_partida DATE. Formato declarado '%d/%m/%Y'.
                                  Medido: dd/mm/aaaa nos primeiros registros.
                                  A conferir em todas as 8.785 linhas.
   partidas.hora               -> hora_partida TIME. Formato '%H:%M'.
                                  Medido: HH:MM nos primeiros registros.
                                  A conferir em todas as linhas.
   partidas.mandante_Placar,
   partidas.visitante_Placar   -> INTEGER
   estatisticas: chutes, chutes_no_alvo, passes, faltas, cartao_amarelo,
                 cartao_vermelho, impedimentos, escanteios -> INTEGER
   estatisticas.posse_de_bola,
   estatisticas.precisao_passes -> DECIMAL(5,2). A confirmar: os valores
                                  não vazios são só números? Se tiverem "%"
                                  ou vírgula decimal, tirar antes da conversão.
   gols.minuto, cartoes.minuto -> minuto INTEGER + acrescimo INTEGER (seção 4)
   cartoes.num_camisa          -> INTEGER
   Identificadores (partida_id, rodada se for só referência, clube, atleta,
   mandante, visitante, arena, UFs, técnicos, cartao, posicao) -> VARCHAR.
   Motivo: identificador nunca é somado.

4. MINUTO COM ACRÉSCIMO
   Padrão aceito: ^(\d+)(\+(\d+))?$
   minuto = grupo 1. acrescimo = grupo 3, ou NULL quando não houver "+".
   Valor fora do padrão, inclusive vazio: para tudo e mostra o valor.
   Motivo: "90+2" é o minuto 90 com 2 de acréscimo. Separar preserva a
   informação e permite ordenar.

5. CONVERSÃO QUE FALHA
   Para tudo. Usar strptime e CAST, que estouram. Nunca TRY_CAST,
   try_strptime ou errors='coerce'.
   Ao falhar: mostra tabela, coluna e valor, e sys.exit(1).
   Motivo: nulo criado pela conversão é indistinguível do nulo verdadeiro.

6. LIMPEZA DE TEXTO (única alteração de texto da refined)
   partidas.arena: remover U+00A0 e espaços nas bordas.
   Medido: no arquivo lido como cp1252, a arena aparece com "Â" antes do nome.
   Isso indica U+00A0 gravado em UTF-8. A confirmar com
   Get-Content -Encoding UTF8 antes de codificar a regra.
   Motivo: espaço invisível quebra GROUP BY e JOIN com outras tabelas.
   Outras colunas de texto: sem alteração.

7. RESULTADO E VENCEDOR
   Criar em partidas:
     resultado VARCHAR: 'mandante' se gols_mandante > gols_visitante;
                        'visitante' se menor; 'empate' se igual.
   vencedor_original: mantém o valor da fonte (nome do clube ou "-").
   Teste de consistência: se vencedor_original = '-', resultado = 'empate';
   caso contrário, vencedor_original é igual ao mandante ou ao visitante
   conforme o resultado. Medido: nenhum vencedor vazio; 2.322 partidas com "-".
   Se o teste falhar: para e lista as partidas.

8. TEMPORADA
   Criar em partidas: temporada INTEGER.
     Regra: é o ano de data_partida, EXCETO quando data_partida está em
     janeiro ou fevereiro de 2021. Nesse caso, temporada = 2020.
   Motivo medido: as 112 partidas de jan/fev de 2021 são as rodadas 28 a 38
   (10 por rodada) mais uma partida da rodada 1 e uma da rodada 23. Com as
   268 partidas de 2020 com data de 2020, a temporada 2020 soma 380.
   Todo marto que agrupa por ano usa temporada, não o ano da data.

9. COBERTURA DE GOLS E CARTÕES
   Criar em partidas:
     gols_registrados BOOLEAN    -- true se existe linha em gols para a partida
     cartoes_registrados BOOLEAN -- true se existe linha em cartoes para a partida
   Não corrige o dado. Diz quais partidas têm o evento registrado.
   Motivo: 2003–2013 não tem cartão para nenhuma partida, e parte das partidas
   não tem gol. Sem a coluna, zero e ausência de registro ficam iguais.

10. DUPLICATAS
   partidas:     chave partida_id. Repetição com conteúdo idêntico: sai.
                 Repetição com conteúdo diferente: para e lista a chave.
   estatisticas: chave (partida_id, clube). Medido: 0 repetições.
   gols:         sem chave natural. Linha inteira repetida sai. Medido: 0.
   cartoes:      sem chave natural. Linha inteira repetida sai. Medido: 0.
   Em todas as tabelas, mostra quantas linhas saíram.

11. LIGAÇÃO
   estatisticas.partida_id, gols.partida_id, cartoes.partida_id
   devem existir em partidas.partida_id. Medido: 0 órfãos.
   Teste obrigatório. Se houver órfão: para e lista.
   O nome do clube em estatisticas, gols e cartoes deve ser igual ao
   mandante ou ao visitante da partida correspondente. Se não for: para e lista.

12. NULOS E ANOMALIAS
   Nenhuma linha apagada por nulo. Nenhum nulo preenchido.
   Posse de bola: NULL em 2003–2013 (medido: todas as linhas vazias).
     NULL não é zero. Não preencher.
   tipo_de_gol: vazio vira NULL. Valores encontrados: "Gol Contra" e "Penalty".
     A confirmar que o vazio significa gol comum.
   posicao (cartoes) vazia: NULL.

   Anomalias conhecidas que aparecem na saída, sem parar a execução:
     - 2016: 379 partidas (758 linhas em estatisticas). Anos vizinhos: 380.
       Causa não investigada. Verificar antes de declarar a temporada completa.
     - 63 partidas de 2014 a 2024 sem cartão registrado. Lista em docs/.
     - Partidas de 2003 a 2005 têm contagens por ano diferentes de 380
       (552, 552 e 462). Não entram como critério de temporada.

13. SAÍDA NA TELA
   Por tabela: linhas que entram, linhas que saem, duplicatas removidas,
   nulos mantidos por coluna com nulo.
   Lista das temporadas com contagem diferente de 380.
   Linha final com o total. stdout em utf-8.

14. REEXECUÇÃO E ERRO
   CREATE OR REPLACE. Antes de transformar, confirma que as quatro tabelas
   existem em raw. Faltando qualquer uma: sys.exit(1).

CRITÉRIOS DE ACEITE
- Contagens que entram = contagens que saem, sem duplicatas esperadas:
    partidas 8.785 · estatisticas 17.570 · gols 9.861 · cartoes 20.953
- Zero órfãos nas ligações da seção 11.
- temporada: 2014, 2015, 2017, 2018, 2019, 2020, 2021, 2022, 2023 e 2024
  com 380 partidas cada. 2016 com 379 (anomalia conhecida).
- resultado = 'empate' exatamente quando os placares são iguais.
- posse_bola é NULL em todas as partidas de 2003 a 2013, e nunca é NULL em 2014 a 2024.
- gols_registrados = false nas partidas de 2003 a 2013 que têm placar
  diferente de 0-0, e true em todas as outras partidas com gol no arquivo.
- cartoes_registrados = false em 4.669 partidas: 4.606 de 2003 a 2013
  e 63 de 2014 a 2024.
- minuto e acrescimo: nenhum valor fora do padrão da seção 4.
- arena sem U+00A0 e sem espaço nas bordas.
- Rodar duas vezes imprime exatamente a mesma coisa.

MAPA DE NOMES
  partidas: ID->partida_id, rodata->rodada, data->data_partida, hora->hora_partida,
    mandante->mandante, visitante->visitante, formacao_mandante->formacao_mandante,
    formacao_visitante->formacao_visitante, tecnico_mandante->tecnico_mandante,
    tecnico_visitante->tecnico_visitante, vencedor->vencedor_original,
    arena->arena, mandante_Placar->gols_mandante, visitante_Placar->gols_visitante,
    mandante_Estado->uf_mandante, visitante_Estado->uf_visitante
  estatisticas: partida_id->partida_id, rodata->rodada, clube->clube,
    chutes->chutes, chutes_no_alvo->chutes_no_alvo, posse_de_bola->posse_bola,
    passes->passes, precisao_passes->precisao_passes, faltas->faltas,
    cartao_amarelo->cartoes_amarelos, cartao_vermelho->cartoes_vermelhos,
    impedimentos->impedimentos, escanteios->escanteios
  gols: partida_id->partida_id, rodata->rodada, clube->clube, atleta->atleta,
    minuto->minuto, acrescimo (novo), tipo_de_gol->tipo_gol
  cartoes: partida_id->partida_id, rodata->rodada, clube->clube, cartao->cartao,
    atleta->atleta, num_camisa->num_camisa, posicao->posicao,
    minuto->minuto, acrescimo (novo)

ENTREGA
1. A spec como docstring no topo do arquivo, com o motivo de cada regra.
2. O código, comentado só onde a decisão não é óbvia.
3. Lista final do que você assumiu e não estava na spec.