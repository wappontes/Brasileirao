# pipeline/db.py
from pathlib import Path
import duckdb

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "raw"
CAMINHO_BANCO = RAIZ / "brasileirao.duckdb"


def conectar() -> duckdb.DuckDBPyConnection:
    """Abre (ou cria) o banco. Quem chama é quem fecha."""
    return duckdb.connect(str(CAMINHO_BANCO))


def criar_schema(con: duckdb.DuckDBPyConnection, nome: str) -> None:
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {nome}")


def gravar(con, df, schema: str, tabela: str) -> int:
    """Recria a tabela com o DataFrame, sem alterar nada. Devolve a contagem do banco."""
    con.register("_df_entrada", df)
    con.execute(f"CREATE OR REPLACE TABLE {schema}.{tabela} AS SELECT * FROM _df_entrada")
    con.unregister("_df_entrada")
    return con.execute(f"SELECT count(*) FROM {schema}.{tabela}").fetchall()[0][0]