CONTEXTO
Projeto final do curso Engenharia de Dados Junior. Dataset: Campeonato Brasileiro 2003 a 2024
(github.com/adaoduque/Brasileirao_Dataset). Spec-driven: esta spec é a fonte da
verdade. Se algo estiver ambíguo, pergunte antes de escrever código.

STACK
- Python 3.13, uv, DuckDB (brasileirao.duckdb na raiz do projeto)
- pandas para leitura

O QUE JÁ EXISTE
pipeline/db.py do curso: conectar(), criar_schema(con, nome), gravar(con, df, schema, tabela).
Ajuste: o arquivo do banco passa a ser brasileirao.duckdb.
Pasta raw/ com os quatro CSV, sem alterações.

ARTEFATO A PRODUZIR
pipeline/ingestao.py, executável com:
  uv run python -m pipeline.ingestao

SPEC

1. ESCOPO E NOMES
   Schema de destino: raw.
   Mapa arquivo -> tabela:
     campeonato-brasileiro-full.csv               -> partidas      (16 colunas)
     campeonato-brasileiro-estatisticas-full.csv  -> estatisticas  (13 colunas)
     campeonato-brasileiro-gols.csv               -> gols          (6 colunas)
     campeonato-brasileiro-cartoes.csv            -> cartoes       (8 colunas)
   Nomes de coluna: exatamente como estão no cabeçalho do arquivo, inclusive
   os que têm erro ("rodata", "mandante_Placar", "chutes_no_alvo").
   Motivo: raw espelha a fonte. Renomear é trabalho da refined.
   Fora da ingestão: Legenda.txt (copiar para docs/ à mão), pasta data/,
   pasta notebooks/. Nenhum desses foi verificado.

2. PROIBIÇÕES
   Nenhuma conversão de tipo. Nenhuma linha descartada. Nenhum nome de coluna
   alterado. Nenhum valor corrigido: "-" continua "-", "90+2" continua "90+2",
   "Â Brinco de Ouro" continua como está.
   Motivo: a fronteira entre o dado que chegou e o dado que eu decidi precisa
   existir. Ela é a passagem de raw para refined.

3. LEITURA
   Separador: vírgula. Aspas duplas. Cabeçalho na primeira linha.
   Encoding: utf-8. Confirmado no gols.csv. Antes da primeira execução, confirme
   nos outros três com Get-Content -Encoding UTF8.
   Leitura com dtype=str e keep_default_na=False: nenhum texto vira NaN
   automaticamente, nem "NA", nem "null".
   Campo vazio ("") vira NULL: df.replace("", None) antes de gravar.
   Motivo: o curso fixa campo vazio como nulo; a transformação decide o que fazer.
   Campos com quebra de linha dentro de aspas são lidos corretamente.
   A contagem vem da leitura, não de contar quebras de linha no arquivo.

4. REEXECUÇÃO
   CREATE OR REPLACE TABLE. Nunca acrescenta. Rodar duas vezes = rodar uma.

5. ERRO
   Antes de abrir o banco: confirma que os quatro arquivos existem em raw/.
   Faltando qualquer um: lista os que faltam, diz em que pasta procurou, sys.exit(1).
   Cabeçalho diferente do esperado (nomes ou quantidade de colunas): para com
   erro, mostra os nomes lidos e sys.exit(1).
   Motivo: mudança de schema na fonte não pode passar em silêncio.

6. SAÍDA NA TELA
   Uma linha por tabela, com contagem vinda do banco (SELECT count(*)),
   milhar com ponto. Linha final com o total. stdout em utf-8.

CRITÉRIOS DE ACEITE
- Contagens esperadas (medidas com Import-Csv nos arquivos):
    partidas      8.785
    estatisticas 17.570
    gols          9.861
    cartoes      20.953
    total        57.169
  Se o banco der outro número, investigar. Não ajustar o número esperado.
- Rodar duas vezes seguidas imprime exatamente a mesma coisa.
- SELECT * FROM raw.partidas devolve todas as colunas como VARCHAR.
- Renomear um dos quatro arquivos faz o script parar antes de gravar qualquer tabela.
- Arena: o caractere original (U+00A0) está preservado em raw.partidas.arena.
- O script termina sozinho e devolve o terminal.

ENTREGA
1. A spec como docstring no topo do arquivo, com o motivo de cada regra.
2. O código, comentado só onde a decisão não é óbvia.
3. Lista final do que você assumiu e não estava na spec.