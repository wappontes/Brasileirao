"""
Executor de marts: sql/marts/*.sql -> schema marts do brasileirao.duckdb.

- Lê todos os arquivos sql/marts/NN_*.sql em ordem alfabética.
- Cada arquivo vira uma tabela em marts com o nome sem prefixo e sem extensão.
- Executa tudo numa transação. Se qualquer arquivo falhar, marts volta ao estado anterior.
- Mart vazio encerra com erro.
"""

import io
import sys
from pathlib import Path

import duckdb

from pipeline import db



PASTA_SQL = db.RAIZ / "sql" / "marts"


def nome_tabela(caminho: Path) -> str:
    """Remove o prefixo numérico e a extensão: 01_classificacao.sql -> classificacao."""
    stem = caminho.stem
    if "_" in stem:
        stem = stem.split("_", 1)[1]
    return stem


def verificar_pasta() -> list[Path]:
    if not PASTA_SQL.exists():
        print(f"Pasta não encontrada: {PASTA_SQL}")
        sys.exit(1)
    arquivos = sorted(PASTA_SQL.glob("*.sql"))
    if not arquivos:
        print(f"Nenhum arquivo .sql em {PASTA_SQL}")
        sys.exit(1)
    nomes = [nome_tabela(a) for a in arquivos]
    if len(nomes) != len(set(nomes)):
        duplicados = [n for n in nomes if nomes.count(n) > 1]
        print(f"Dois arquivos geram o mesmo nome de tabela: {set(duplicados)}")
        sys.exit(1)
    return arquivos


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    arquivos = verificar_pasta()

    con = db.conectar()
    try:
        con.execute("DROP SCHEMA IF EXISTS marts CASCADE")
        db.criar_schema(con, "marts")
        con.execute("BEGIN TRANSACTION")

        for arq in arquivos:
            tabela = nome_tabela(arq)
            sql = arq.read_text(encoding="utf-8").rstrip().rstrip(";")
            try:
                con.execute(f"CREATE TABLE marts.{tabela} AS {sql}")
            except duckdb.Error as erro:
                con.execute("ROLLBACK")
                print(f"Falhou ao criar marts.{tabela} ({arq.name}). Nada foi gravado.")
                print(erro)
                sys.exit(1)
            n = con.execute(f"SELECT count(*) FROM marts.{tabela}").fetchall()[0][0]
            if n == 0:
                con.execute("ROLLBACK")
                print(f"marts.{tabela} voltou vazio. Nada foi gravado.")
                sys.exit(1)

        con.execute("COMMIT")

        total = 0
        for arq in arquivos:
            tabela = nome_tabela(arq)
            n = con.execute(f"SELECT count(*) FROM marts.{tabela}").fetchall()[0][0]
            total += n
            print(f"marts.{tabela:<20} {fmt(n):>8} linhas")
        print(f"{'total':<24} {fmt(total):>8} linhas")

    finally:
        con.close()


if __name__ == "__main__":
    main()
