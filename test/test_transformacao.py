"""Testes de pipeline/transformacao.py."""
import pytest
import duckdb
from pipeline import db
import pipeline.transformacao as tr


@pytest.fixture
def banco_raw(tmp_path, monkeypatch):
    """Cria um banco com raw.partidas, estatisticas, gols e cartoes mínimos."""
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "teste.duckdb")
    con = duckdb.connect(str(tmp_path / "teste.duckdb"))
    con.execute("CREATE SCHEMA raw")
    con.execute("""
        CREATE TABLE raw.partidas AS SELECT * FROM (VALUES
            ('1','1','29/03/2003','16:00','Guarani','Vasco','','','','',
             'Guarani',' Brinco de Ouro','4','2','SP','RJ'),
            ('2','1','29/03/2003','16:00','Flamengo','Fluminense','','','','',
             '-',' Maracana','1','1','RJ','RJ')
        ) t(ID,rodata,data,hora,mandante,visitante,formacao_mandante,
            formacao_visitante,tecnico_mandante,tecnico_visitante,vencedor,
            arena,mandante_Placar,visitante_Placar,mandante_Estado,visitante_Estado)
    """)
    con.execute("""
        CREATE TABLE raw.estatisticas AS SELECT * FROM (VALUES
            ('1','1','Guarani','10','5','55%','300','80%','12','2','0','1','3'),
            ('1','1','Vasco','8','3','45%','250','75%','10','1','0','0','2'),
            ('2','1','Flamengo','12','6',NULL,'320',NULL,'8','1','0','2','4'),
            ('2','1','Fluminense','9','4',NULL,'280',NULL,'11','3','1','1','3')
        ) t(partida_id,rodata,clube,chutes,chutes_no_alvo,posse_de_bola,
            passes,precisao_passes,faltas,cartao_amarelo,cartao_vermelho,
            impedimentos,escanteios)
    """)
    con.execute("""
        CREATE TABLE raw.gols AS SELECT * FROM (VALUES
            ('1','1','Guarani','Joao','10',''),
            ('1','1','Guarani','Pedro','45+2',''),
            ('1','1','Guarani','Carlos','60','Penalty'),
            ('1','1','Guarani','Andre','80',''),
            ('2','1','Flamengo','Lucas','55',''),
            ('2','1','Fluminense','Marcos','70','Gol Contra')
        ) t(partida_id,rodata,clube,atleta,minuto,tipo_de_gol)
    """)
    con.execute("""
        CREATE TABLE raw.cartoes AS SELECT * FROM (VALUES
            ('1','1','Vasco','Amarelo','Paulo','5','Zagueiro','30'),
            ('2','1','Flamengo','Amarelo','Joao','10','Atacante','66')
        ) t(partida_id,rodata,clube,cartao,atleta,num_camisa,posicao,minuto)
    """)
    con.close()
    return tmp_path


def abrir(tmp_path):
    return duckdb.connect(str(tmp_path / "teste.duckdb"), read_only=True)


def test_transformacao_nao_perde_linhas(banco_raw):
    tr.main()
    con = abrir(banco_raw)
    assert con.execute("SELECT count(*) FROM refined.partidas").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM refined.estatisticas").fetchone()[0] == 4
    assert con.execute("SELECT count(*) FROM refined.gols").fetchone()[0] == 6
    assert con.execute("SELECT count(*) FROM refined.cartoes").fetchone()[0] == 2
    con.close()


def test_resultado_vem_do_placar(banco_raw):
    tr.main()
    con = abrir(banco_raw)
    # Guarani 4x2 Vasco -> mandante
    r = con.execute(
        "SELECT resultado FROM refined.partidas WHERE partida_id = 1"
    ).fetchone()[0]
    assert r == "mandante"
    # Flamengo 1x1 Fluminense -> empate
    r = con.execute(
        "SELECT resultado FROM refined.partidas WHERE partida_id = 2"
    ).fetchone()[0]
    assert r == "empate"
    con.close()


def test_empate_com_vencedor_traco(banco_raw):
    # Partida 2 tem vencedor='-' e placar empate. Resultado é empate.
    tr.main()
    con = abrir(banco_raw)
    row = con.execute(
        "SELECT vencedor_original, resultado FROM refined.partidas WHERE partida_id = 2"
    ).fetchone()
    assert row[0] == "-"
    assert row[1] == "empate"
    con.close()


def test_minuto_com_acrescimo(banco_raw):
    tr.main()
    con = abrir(banco_raw)
    row = con.execute(
        "SELECT minuto, acrescimo FROM refined.gols "
        "WHERE atleta = 'Pedro'"
    ).fetchone()
    assert row[0] == 45
    assert row[1] == 2
    con.close()


def test_minuto_sem_acrescimo_nulo(banco_raw):
    tr.main()
    con = abrir(banco_raw)
    row = con.execute(
        "SELECT minuto, acrescimo FROM refined.gols "
        "WHERE atleta = 'Joao' AND partida_id = 1"
    ).fetchone()
    assert row[0] == 10
    assert row[1] is None
    con.close()


def test_posse_com_percentual_convertida(banco_raw):
    tr.main()
    con = abrir(banco_raw)
    row = con.execute(
        "SELECT posse_bola FROM refined.estatisticas "
        "WHERE partida_id = 1 AND clube = 'Guarani'"
    ).fetchone()
    assert float(row[0]) == 55.0
    con.close()


def test_posse_vazia_vira_null(banco_raw):
    tr.main()
    con = abrir(banco_raw)
    n = con.execute(
        "SELECT count(*) FROM refined.estatisticas "
        "WHERE partida_id = 2 AND posse_bola IS NULL"
    ).fetchone()[0]
    assert n == 2
    con.close()


def test_arena_sem_nbsp(banco_raw):
    tr.main()
    con = abrir(banco_raw)
    arena = con.execute(
        "SELECT arena FROM refined.partidas WHERE partida_id = 1"
    ).fetchone()[0]
    assert "\u00a0" not in arena
    assert not arena.startswith(" ")
    con.close()


def test_gols_registrados(banco_raw):
    tr.main()
    con = abrir(banco_raw)
    # Partidas 1 e 2 têm gols no arquivo.
    n = con.execute(
        "SELECT count(*) FROM refined.partidas WHERE gols_registrados = true"
    ).fetchone()[0]
    assert n == 2
    con.close()


def test_cartoes_registrados(banco_raw):
    tr.main()
    con = abrir(banco_raw)
    n = con.execute(
        "SELECT count(*) FROM refined.partidas WHERE cartoes_registrados = true"
    ).fetchone()[0]
    assert n == 2
    con.close()