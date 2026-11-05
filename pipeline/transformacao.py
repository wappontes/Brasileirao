"""
Transformação: raw -> refined no brasileirao.duckdb.

Spec: specs/Spec da transformação (camada refined).md
- Lê de raw, escreve em refined. Nunca escreve em raw.
- Tudo em uma transação: se qualquer validação falhar, nada é gravado em refined.
- Conversão que falha para o processo (sem TRY_CAST nem try_strptime).
- Posse e precisão de passes: '%' sai, 'None' e vazio viram NULL.
- Minuto com acréscimo ('90+2') vira minuto + acrescimo.
- temporada: partidas com data em jan/fev de 2021 pertencem à temporada 2020.
- gols_registrados e cartoes_registrados marcam a cobertura de cada partida.
"""

import io
import sys

import duckdb

from pipeline import db



ESPERADO = {"partidas": 8785, "estatisticas": 17570, "gols": 9861, "cartoes": 20953}

CRIAR = [
    ("partidas", """
        CREATE OR REPLACE TABLE refined.partidas AS
        WITH base AS (
            SELECT DISTINCT * FROM raw.partidas
        ),
        tipadas AS (
            SELECT
                CAST(ID AS INTEGER)                        AS partida_id,
                CAST(rodata AS INTEGER)                    AS rodada,
                strptime(data, '%d/%m/%Y')::DATE           AS data_partida,
                strptime(hora, '%H:%M')::TIME              AS hora_partida,
                mandante,
                visitante,
                formacao_mandante,
                formacao_visitante,
                tecnico_mandante,
                tecnico_visitante,
                vencedor                                   AS vencedor_original,
                trim(replace(arena, chr(160), ' '))        AS arena,
                CAST(mandante_Placar AS INTEGER)           AS gols_mandante,
                CAST(visitante_Placar AS INTEGER)          AS gols_visitante,
                mandante_Estado                            AS uf_mandante,
                visitante_Estado                           AS uf_visitante
            FROM base
        )
        SELECT
            t.*,
            CASE WHEN gols_mandante > gols_visitante THEN 'mandante'
                 WHEN gols_mandante < gols_visitante THEN 'visitante'
                 ELSE 'empate' END                         AS resultado,
            CASE WHEN year(data_partida) = 2021 AND month(data_partida) <= 2 THEN 2020
                 ELSE year(data_partida) END               AS temporada,
            EXISTS (SELECT 1 FROM raw.gols g
                    WHERE g.partida_id = CAST(t.partida_id AS VARCHAR)) AS gols_registrados,
            EXISTS (SELECT 1 FROM raw.cartoes c
                    WHERE c.partida_id = CAST(t.partida_id AS VARCHAR)) AS cartoes_registrados
        FROM tipadas t
    """),
    ("estatisticas", """
        CREATE OR REPLACE TABLE refined.estatisticas AS
        SELECT DISTINCT
            CAST(partida_id AS INTEGER)                    AS partida_id,
            CAST(rodata AS INTEGER)                        AS rodada,
            clube,
            CAST(chutes AS INTEGER)                        AS chutes,
            CAST(chutes_no_alvo AS INTEGER)                AS chutes_no_alvo,
            CASE WHEN posse_de_bola IS NULL OR posse_de_bola = 'None' THEN NULL
                 ELSE CAST(replace(posse_de_bola, '%', '') AS DECIMAL(5,2)) END AS posse_bola,
            CAST(passes AS INTEGER)                        AS passes,
            CASE WHEN precisao_passes IS NULL OR precisao_passes = 'None' THEN NULL
                 ELSE CAST(replace(precisao_passes, '%', '') AS DECIMAL(5,2)) END AS precisao_passes,
            CAST(faltas AS INTEGER)                        AS faltas,
            CAST(cartao_amarelo AS INTEGER)                AS cartoes_amarelos,
            CAST(cartao_vermelho AS INTEGER)               AS cartoes_vermelhos,
            CAST(impedimentos AS INTEGER)                  AS impedimentos,
            CAST(escanteios AS INTEGER)                    AS escanteios
        FROM raw.estatisticas
    """),
    ("gols", """
        CREATE OR REPLACE TABLE refined.gols AS
        SELECT DISTINCT
            CAST(partida_id AS INTEGER)                              AS partida_id,
            CAST(rodata AS INTEGER)                                  AS rodada,
            clube,
            atleta,
            CAST(regexp_extract(minuto, '^([0-9]+)', 1) AS INTEGER)  AS minuto,
            CASE WHEN minuto LIKE '%+%'
                 THEN CAST(split_part(minuto, '+', 2) AS INTEGER) END AS acrescimo,
            tipo_de_gol                                              AS tipo_gol
        FROM raw.gols
    """),
    ("cartoes", """
        CREATE OR REPLACE TABLE refined.cartoes AS
        SELECT DISTINCT
            CAST(partida_id AS INTEGER)                              AS partida_id,
            CAST(rodata AS INTEGER)                                  AS rodada,
            clube,
            cartao,
            atleta,
            CAST(num_camisa AS INTEGER)                              AS num_camisa,
            posicao,
            CAST(regexp_extract(minuto, '^([0-9]+)', 1) AS INTEGER)  AS minuto,
            CASE WHEN minuto LIKE '%+%'
                 THEN CAST(split_part(minuto, '+', 2) AS INTEGER) END AS acrescimo
        FROM raw.cartoes
    """),
]

# Cada validação devolve quantos casos estão errados. Zero é o esperado.
VALIDACOES = [
    ("minuto fora do padrão em raw.gols",
     "SELECT count(*) FROM raw.gols WHERE minuto IS NOT NULL "
     "AND NOT regexp_matches(minuto, '^[0-9]+([+][0-9]+)?$')"),
    ("minuto fora do padrão em raw.cartoes",
     "SELECT count(*) FROM raw.cartoes WHERE minuto IS NOT NULL "
     "AND NOT regexp_matches(minuto, '^[0-9]+([+][0-9]+)?$')"),
    ("partidas com ID repetido",
     "SELECT count(*) - count(DISTINCT partida_id) FROM refined.partidas"),
    ("estatisticas órfãs (sem partida)",
     "SELECT count(*) FROM refined.estatisticas e WHERE NOT EXISTS "
     "(SELECT 1 FROM refined.partidas p WHERE p.partida_id = e.partida_id)"),
    ("gols órfãos (sem partida)",
     "SELECT count(*) FROM refined.gols g WHERE NOT EXISTS "
     "(SELECT 1 FROM refined.partidas p WHERE p.partida_id = g.partida_id)"),
    ("cartoes órfãos (sem partida)",
     "SELECT count(*) FROM refined.cartoes c WHERE NOT EXISTS "
     "(SELECT 1 FROM refined.partidas p WHERE p.partida_id = c.partida_id)"),
    ("partidas sem exatamente 2 linhas em estatisticas",
     "SELECT count(*) FROM refined.partidas p WHERE "
     "(SELECT count(*) FROM refined.estatisticas e WHERE e.partida_id = p.partida_id) <> 2"),
    ("estatisticas com chave (partida_id, clube) repetida",
     "SELECT count(*) - (SELECT count(*) FROM "
     "(SELECT DISTINCT partida_id, clube FROM refined.estatisticas)) FROM refined.estatisticas"),
    ("estatisticas com clube que não jogou a partida",
     "SELECT count(*) FROM refined.estatisticas e JOIN refined.partidas p "
     "ON p.partida_id = e.partida_id WHERE e.clube NOT IN (p.mandante, p.visitante)"),
    ("gols com clube que não jogou a partida",
     "SELECT count(*) FROM refined.gols g JOIN refined.partidas p "
     "ON p.partida_id = g.partida_id WHERE g.clube NOT IN (p.mandante, p.visitante)"),
    ("cartoes com clube que não jogou a partida",
     "SELECT count(*) FROM refined.cartoes c JOIN refined.partidas p "
     "ON p.partida_id = c.partida_id WHERE c.clube NOT IN (p.mandante, p.visitante)"),
]

# Divergências conhecidas na fonte. Não bloqueiam a transformação:
# o resultado vem do placar; vencedor_original mantém o valor da fonte.
AVISOS_VENCEDOR = (
    "SELECT partida_id, data_partida, mandante, visitante, vencedor_original, "
    "gols_mandante, gols_visitante, resultado "
    "FROM refined.partidas "
    "WHERE (vencedor_original = '-') <> (resultado = 'empate') "
    "ORDER BY partida_id"
)


def imprimir_avisos(con) -> None:
    linhas = con.execute(AVISOS_VENCEDOR).fetchall()
    print()
    print(f"avisos: vencedor_original diverge do placar em {len(linhas)} partida(s)")
    for partida_id, data, mandante, visitante, vencedor, gm, gv, resultado in linhas:
        print(f"  partida {partida_id} ({data}) {mandante} {gm} x {gv} {visitante}: "
              f"vencedor_original='{vencedor}', resultado='{resultado}'")
def fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def imprimir_resumo(con) -> None:
    print(f"{'tabela':<14}{'raw':>10}{'refined':>10}{'saíram':>9}{'esperado':>11}")
    total = 0
    for nome, esperado in ESPERADO.items():
        raw_n = con.execute(f"SELECT count(*) FROM raw.{nome}").fetchone()[0]
        ref_n = con.execute(f"SELECT count(*) FROM refined.{nome}").fetchone()[0]
        total += ref_n
        marca = "" if ref_n == esperado else "   <- diferente"
        print(f"{nome:<14}{fmt(raw_n):>10}{fmt(ref_n):>10}{fmt(raw_n - ref_n):>9}"
              f"{fmt(esperado):>11}{marca}")
    print(f"{'total':<14}{'':>10}{fmt(total):>10}")

    print()
    nulos_posse = con.execute(
        "SELECT count(*) FILTER (WHERE posse_bola IS NULL) FROM refined.estatisticas"
    ).fetchone()[0]
    nulos_precisao = con.execute(
        "SELECT count(*) FILTER (WHERE precisao_passes IS NULL) FROM refined.estatisticas"
    ).fetchone()[0]
    print(f"nulos mantidos: posse_bola {fmt(nulos_posse)}, precisao_passes {fmt(nulos_precisao)}")

    sem_gol = con.execute(
        "SELECT count(*) FROM refined.partidas WHERE NOT gols_registrados").fetchone()[0]
    sem_cartao = con.execute(
        "SELECT count(*) FROM refined.partidas WHERE NOT cartoes_registrados").fetchone()[0]
    print(f"partidas sem gol registrado: {fmt(sem_gol)}, sem cartão registrado: {fmt(sem_cartao)}")

    print()
    print("temporadas com número de partidas diferente de 380:")
    linhas = con.execute(
        "SELECT temporada, count(*) FROM refined.partidas "
        "GROUP BY temporada HAVING count(*) <> 380 ORDER BY temporada"
    ).fetchall()
    if not linhas:
        print("  nenhuma")
    for temporada, n in linhas:
        print(f"  {temporada}: {n}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    con = db.conectar()
    try:
        db.criar_schema(con, "refined")
        con.execute("BEGIN TRANSACTION")

        for nome, sql in CRIAR:
            try:
                con.execute(sql)
            except duckdb.Error as erro:
                con.execute("ROLLBACK")
                print(f"Conversão falhou ao criar refined.{nome}. Nada foi gravado.")
                print(erro)
                sys.exit(1)

        falhas = []
        for descricao, sql in VALIDACOES:
            n = con.execute(sql).fetchone()[0]
            if n:
                falhas.append((descricao, n))
        if falhas:
            con.execute("ROLLBACK")
            print("Validação falhou. Nada foi gravado em refined:")
            for descricao, n in falhas:
                print(f"  - {descricao}: {n}")
            sys.exit(1)

        con.execute("COMMIT")
        imprimir_resumo(con)
        imprimir_avisos(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
