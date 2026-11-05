"""Testes dos marts SQL."""
import pytest
import duckdb
from pathlib import Path
from pipeline import db
import pipeline.transformacao as tr
import pipeline.marts as mr


@pytest.fixture
def banco_completo(tmp_path, monkeypatch):
    """Banco com raw e refined, usando os mesmos dados de test_transformacao."""
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "teste.duckdb")
    monkeypatch.setattr(mr, "PASTA_SQL", Path("sql") / "marts")
    con = duckdb.connect(str(tmp_path / "teste.duckdb"))
    con.execute("CREATE SCHEMA raw")
    con.execute("""
        CREATE TABLE raw.partidas AS SELECT * FROM (VALUES
            ('1','1','29/03/2014','16:00','Guarani','Vasco','','','','',
             'Guarani',' Arena','4','2','SP','RJ'),
            ('2','1','30/03/2014','16:00','Flamengo','Fluminense','','','','',
             '-',' Maracana','1','1','RJ','RJ'),
            ('3','1','31/03/2014','16:00','Santos','Palmeiras','','','','',
             'Palmeiras',' Vila Belmiro','0','1','SP','SP')
        ) t(ID,rodata,data,hora,mandante,visitante,formacao_mandante,
            formacao_visitante,tecnico_mandante,tecnico_visitante,vencedor,
            arena,mandante_Placar,visitante_Placar,mandante_Estado,visitante_Estado)
    """)
    con.execute("""
        CREATE TABLE raw.estatisticas AS SELECT * FROM (VALUES
            ('1','1','Guarani','10','5','55%','300','80%','12','2','0','1','3'),
            ('1','1','Vasco','8','3','45%','250','75%','10','1','0','0','2'),
            ('2','1','Flamengo','12','6','50%','320','70%','8','1','0','2','4'),
            ('2','1','Fluminense','9','4','50%','280','65%','11','3','1','1','3'),
            ('3','1','Santos','11','4','48%','310','72%','9','2','0','1','2'),
            ('3','1','Palmeiras','10','5','52%','290','68%','7','1','0','0','3')
        ) t(partida_id,rodata,clube,chutes,chutes_no_alvo,posse_de_bola,
            passes,precisao_passes,faltas,cartao_amarelo,cartao_vermelho,
            impedimentos,escanteios)
    """)
    con.execute("""
        CREATE TABLE raw.gols AS SELECT * FROM (VALUES
            ('1','1','Guarani','Joao','10',''),
            ('1','1','Guarani','Pedro','20',''),
            ('1','1','Guarani','Carlos','60',''),
            ('1','1','Guarani','Andre','80',''),
            ('1','1','Vasco','Paulo','30',''),
            ('1','1','Vasco','Lucas','50',''),
            ('2','1','Flamengo','Marcos','55',''),
            ('2','1','Fluminense','Rafael','70','Gol Contra'),
            ('3','1','Palmeiras','Roni','45','')
        ) t(partida_id,rodata,clube,atleta,minuto,tipo_de_gol)
    """)
    con.execute("""
        CREATE TABLE raw.cartoes AS SELECT * FROM (VALUES
            ('1','1','Vasco','Amarelo','Paulo','5','Zagueiro','30'),
            ('2','1','Flamengo','Amarelo','Joao','10','Atacante','66'),
            ('3','1','Santos','Amarelo','Mario','8','Lateral','44'),
            ('3','1','Palmeiras','Vermelho','Neto','3','Goleiro','89')
        ) t(partida_id,rodata,clube,cartao,atleta,num_camisa,posicao,minuto)
    """)
    con.close()
    tr.main()
    return tmp_path


def abrir(tmp_path):
    return duckdb.connect(str(tmp_path / "teste.duckdb"), read_only=True)


def test_marts_rodam_sem_erro(banco_completo):
    mr.main()
    con = abrir(banco_completo)
    tabelas = {
        r[0] for r in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'marts'"
        ).fetchall()
    }
    assert "classificacao" in tabelas
    assert "mandante_visitante" in tabelas
    assert "media_gols" in tabelas
    assert "posse_media" in tabelas
    assert "cartoes_clube" in tabelas
    con.close()


def test_classificacao_soma_jogos(banco_completo):
    mr.main()
    con = abrir(banco_completo)
    # 3 partidas, cada clube joga 1. sum(jogos) = 3 * 2 = 6.
    total = con.execute(
        "SELECT sum(jogos) FROM marts.classificacao"
    ).fetchone()[0]
    assert total == 6
    con.close()


def test_classificacao_pontos_guarani(banco_completo):
    mr.main()
    con = abrir(banco_completo)
    # Guarani ganhou 1 partida: 3 pontos.
    pontos = con.execute(
        "SELECT pontos FROM marts.classificacao "
        "WHERE clube = 'Guarani' AND temporada = 2014"
    ).fetchone()[0]
    assert pontos == 3
    con.close()


def test_mandante_visitante_soma_partidas(banco_completo):
    mr.main()
    con = abrir(banco_completo)
    row = con.execute(
        "SELECT vitorias_mandante + empates + vitorias_visitante, partidas "
        "FROM marts.mandante_visitante WHERE temporada = 2014"
    ).fetchone()
    assert row[0] == row[1]
    con.close()


def test_media_gols_so_com_registro(banco_completo):
    mr.main()
    con = abrir(banco_completo)
    # Dados inventados têm data de 2014, que tem gols registrados.
    n = con.execute(
        "SELECT count(*) FROM marts.media_gols"
    ).fetchone()[0]
    assert n >= 1
    con.close()


def test_posse_exclui_nulos(banco_completo):
    mr.main()
    con = abrir(banco_completo)
    # Todos os dados têm posse preenchida.
    n = con.execute(
        "SELECT count(*) FROM marts.posse_media WHERE posse_media IS NULL"
    ).fetchone()[0]
    assert n == 0
    con.close()


def test_cartoes_clube_sem_2003_a_2013(banco_completo):
    mr.main()
    con = abrir(banco_completo)
    n = con.execute(
        "SELECT count(*) FROM marts.cartoes_clube WHERE temporada < 2014"
    ).fetchone()[0]
    assert n == 0
    con.close()