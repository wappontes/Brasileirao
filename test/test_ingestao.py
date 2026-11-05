"""Testes de pipeline/ingestao.py."""
import gzip
import pytest
from pathlib import Path
from pipeline import db
import pipeline.ingestao as ing


CABECALHO_PARTIDAS = ",".join([
    "ID", "rodata", "data", "hora", "mandante", "visitante",
    "formacao_mandante", "formacao_visitante", "tecnico_mandante",
    "tecnico_visitante", "vencedor", "arena", "mandante_Placar",
    "visitante_Placar", "mandante_Estado", "visitante_Estado",
])

CABECALHO_ESTATISTICAS = ",".join([
    "partida_id", "rodata", "clube", "chutes", "chutes_no_alvo",
    "posse_de_bola", "passes", "precisao_passes", "faltas",
    "cartao_amarelo", "cartao_vermelho", "impedimentos", "escanteios",
])

CABECALHO_GOLS = ",".join([
    "partida_id", "rodata", "clube", "atleta", "minuto", "tipo_de_gol",
])

CABECALHO_CARTOES = ",".join([
    "partida_id", "rodata", "clube", "cartao", "atleta",
    "num_camisa", "posicao", "minuto",
])


def criar_csvs(raw_dir: Path) -> None:
    """Cria quatro CSVs mínimos válidos em raw_dir."""
    (raw_dir / "campeonato-brasileiro-full.csv").write_text(
        f"{CABECALHO_PARTIDAS}\n"
        '"1","1","29/03/2003","16:00","Guarani","Vasco","","","","","Guarani",'
        '" Brinco de Ouro","4","2","SP","RJ"\n',
        encoding="utf-8",
    )
    (raw_dir / "campeonato-brasileiro-estatisticas-full.csv").write_text(
        f"{CABECALHO_ESTATISTICAS}\n"
        '"1","1","Vasco","0","0","","0","","0","0","0","0","0"\n'
        '"1","1","Guarani","0","0","","0","","0","0","0","0","0"\n',
        encoding="utf-8",
    )
    (raw_dir / "campeonato-brasileiro-gols.csv").write_text(
        f"{CABECALHO_GOLS}\n"
        '"1","1","Guarani","Joao","10",""\n',
        encoding="utf-8",
    )
    (raw_dir / "campeonato-brasileiro-cartoes.csv").write_text(
        f"{CABECALHO_CARTOES}\n"
        '"1","1","Vasco","Amarelo","Pedro","5","Zagueiro","30"\n',
        encoding="utf-8",
    )


@pytest.fixture
def projeto(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    criar_csvs(raw_dir)
    monkeypatch.setattr(db, "RAIZ", tmp_path)
    monkeypatch.setattr(db, "PASTA_RAW", raw_dir)
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "teste.duckdb")
    return tmp_path


def test_ingestao_grava_quatro_tabelas(projeto):
    ing.main()
    import duckdb
    con = duckdb.connect(str(projeto / "teste.duckdb"), read_only=True)
    assert con.execute("SELECT count(*) FROM raw.partidas").fetchone()[0] == 1
    assert con.execute("SELECT count(*) FROM raw.estatisticas").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM raw.gols").fetchone()[0] == 1
    assert con.execute("SELECT count(*) FROM raw.cartoes").fetchone()[0] == 1
    con.close()


def test_ingestao_duas_vezes_nao_duplica(projeto):
    ing.main()
    ing.main()
    import duckdb
    con = duckdb.connect(str(projeto / "teste.duckdb"), read_only=True)
    assert con.execute("SELECT count(*) FROM raw.partidas").fetchone()[0] == 1
    con.close()


def test_ingestao_colunas_sao_varchar(projeto):
    ing.main()
    import duckdb
    con = duckdb.connect(str(projeto / "teste.duckdb"), read_only=True)
    tipos = {
        r[0]: r[1]
        for r in con.execute("DESCRIBE raw.partidas").fetchall()
    }
    assert all(t == "VARCHAR" for t in tipos.values())
    con.close()


def test_ingestao_arquivo_faltando_para(projeto):
    (projeto / "raw" / "campeonato-brasileiro-full.csv").unlink()
    with pytest.raises(SystemExit):
        ing.main()


def test_ingestao_cabecalho_errado_para(projeto):
    (projeto / "raw" / "campeonato-brasileiro-full.csv").write_text(
        "col_errada,outra\n1,2\n", encoding="utf-8"
    )
    with pytest.raises(SystemExit):
        ing.main()


def test_ingestao_vazio_vira_null(projeto):
    ing.main()
    import duckdb
    con = duckdb.connect(str(projeto / "teste.duckdb"), read_only=True)
    # formacao_mandante está vazio no CSV de teste, deve ser NULL no banco.
    n = con.execute(
        "SELECT count(*) FROM raw.partidas WHERE formacao_mandante IS NULL"
    ).fetchone()[0]
    assert n == 1
    con.close()