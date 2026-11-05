"""Testes de pipeline/db.py."""
import pandas as pd
import pytest
from pathlib import Path
from pipeline import db


def test_conectar_cria_banco_na_raiz(tmp_path, monkeypatch):
    # Redireciona RAIZ para tmp_path para não tocar no banco real.
    monkeypatch.setattr(db, "RAIZ", tmp_path)
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "teste.duckdb")
    con = db.conectar()
    con.close()
    assert (tmp_path / "teste.duckdb").exists()


def test_conectar_nao_cria_banco_no_diretorio_corrente(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RAIZ", tmp_path)
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "teste.duckdb")
    monkeypatch.chdir(tmp_path / "..")
    con = db.conectar()
    con.close()
    assert not (tmp_path.parent / "teste.duckdb").exists()


def test_gravar_devolve_contagem_do_banco(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "teste.duckdb")
    con = db.conectar()
    df = pd.DataFrame({"a": ["x", "y", "z"]})
    db.criar_schema(con, "raw")
    n = db.gravar(con, df, "raw", "teste")
    con.close()
    assert n == 3


def test_gravar_duas_vezes_nao_duplica(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "teste.duckdb")
    con = db.conectar()
    df = pd.DataFrame({"a": ["x", "y"]})
    db.criar_schema(con, "raw")
    db.gravar(con, df, "raw", "teste")
    n = db.gravar(con, df, "raw", "teste")
    con.close()
    assert n == 2