"""
Ingestão: CSV -> schema raw do brasileirao.duckdb.

Spec: specs/Spec da Ingestão (camda raw).md
Resumo:
- Nomes de coluna exatamente como no cabeçalho do arquivo.
- Nenhuma conversão de tipo, nenhuma linha descartada, nenhum valor alterado.
- Vazio vira NULL na gravação. Nenhum outro valor é modificado.
- CREATE OR REPLACE: rodar de novo dá o mesmo resultado.
- Arquivo faltando ou cabeçalho diferente: para antes de gravar qualquer tabela.
"""

import io
import sys

import pandas as pd

from pipeline import db

# O terminal do Windows não fala UTF-8 por padrão.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

MAPA = {
    "campeonato-brasileiro-full.csv": "partidas",
    "campeonato-brasileiro-estatisticas-full.csv": "estatisticas",
    "campeonato-brasileiro-gols.csv": "gols",
    "campeonato-brasileiro-cartoes.csv": "cartoes",
}

# Cabeçalhos medidos nos arquivos, na ordem exata.
CABECALHOS = {
    "partidas": [
        "ID", "rodata", "data", "hora", "mandante", "visitante",
        "formacao_mandante", "formacao_visitante", "tecnico_mandante",
        "tecnico_visitante", "vencedor", "arena", "mandante_Placar",
        "visitante_Placar", "mandante_Estado", "visitante_Estado",
    ],
    "estatisticas": [
        "partida_id", "rodata", "clube", "chutes", "chutes_no_alvo",
        "posse_de_bola", "passes", "precisao_passes", "faltas",
        "cartao_amarelo", "cartao_vermelho", "impedimentos", "escanteios",
    ],
    "gols": ["partida_id", "rodata", "clube", "atleta", "minuto", "tipo_de_gol"],
    "cartoes": [
        "partida_id", "rodata", "clube", "cartao", "atleta",
        "num_camisa", "posicao", "minuto",
    ],
}

# Contagens medidas com Import-Csv nos arquivos (linhas de dados, sem cabeçalho).
ESPERADO = {"partidas": 8785, "estatisticas": 17570, "gols": 9861, "cartoes": 20953}


def verificar_arquivos() -> None:
    faltando = [arq for arq in MAPA if not (db.PASTA_RAW / arq).exists()]
    if faltando:
        print(f"Arquivos faltando em {db.PASTA_RAW}:")
        for arq in faltando:
            print(f"  - {arq}")
        sys.exit(1)


def ler(arquivo: str, tabela: str) -> pd.DataFrame:
    df = pd.read_csv(
        db.PASTA_RAW / arquivo,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8",
    )
    if list(df.columns) != CABECALHOS[tabela]:
        print(f"Cabeçalho de {arquivo} diferente do esperado.")
        print(f"  Lido:     {list(df.columns)}")
        print(f"  Esperado: {CABECALHOS[tabela]}")
        sys.exit(1)
    # Vazio vira NULL. Nenhum outro valor é alterado.
    return df.where(df != "", None)


def formatar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def main() -> None:
    verificar_arquivos()

    # Lê tudo antes de abrir o banco: se um arquivo falhar, nada é gravado.
    dados = {tabela: ler(arq, tabela) for arq, tabela in MAPA.items()}

    con = db.conectar()
    try:
        db.criar_schema(con, "raw")
        total = 0
        for tabela, df in dados.items():
            n = db.gravar(con, df, "raw", tabela)
            total += n
            marca = ""
            if n != ESPERADO[tabela]:
                marca = f"   <- esperado {formatar(ESPERADO[tabela])}"
            print(f"raw.{tabela:<14} {formatar(n):>8}{marca}")
        print(f"{'total':<18} {formatar(total):>8}")
    finally:
        con.close()


if __name__ == "__main__":
    main()