"""Testes de contrato de schema entre transform.py, db.py, sincronizar_estacoes.py e o DDL SQL."""
import re
from pathlib import Path

import db
import sincronizar_estacoes
from transform import parse_chunk


DDL_PATH = Path(__file__).resolve().parent.parent / "db-init" / "01-init-timescaledb.sql"


def _extrair_colunas_ddl(tabela: str) -> list[tuple[str, str]]:
    sql = DDL_PATH.read_text(encoding="utf-8")
    match = re.search(
        rf"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?{re.escape(tabela)}\s*\((.*?)\n\);",
        sql,
        flags=re.DOTALL | re.IGNORECASE,
    )
    assert match is not None, f"Tabela {tabela} nao encontrada no DDL"

    colunas = []
    for linha in match.group(1).splitlines():
        sem_comentario = linha.split("--", 1)[0].strip().rstrip(",")
        if not sem_comentario:
            continue
        partes = sem_comentario.split(None, 1)
        colunas.append((partes[0], partes[1]))
    return colunas


def test_db_columns_e_copy_types_tem_mesmo_tamanho():
    assert len(db.COLUMNS) == 22
    assert len(db.COPY_TYPES) == len(db.COLUMNS)


def test_parse_chunk_alinha_exatamente_com_db_columns(build_raw_df, meta_brasilia):
    df = parse_chunk(build_raw_df(), meta_brasilia)
    assert df.columns.tolist() == db.COLUMNS


def test_ddl_dados_estacoes_alinha_com_db_columns_e_copy_types():
    colunas_ddl = _extrair_colunas_ddl("dados_estacoes")

    nomes_ddl = [nome for nome, _ in colunas_ddl]
    assert nomes_ddl == db.COLUMNS

    for (nome, tipo_sql), tipo_copy in zip(colunas_ddl, db.COPY_TYPES):
        tipo_upper = tipo_sql.upper()
        if tipo_copy == "timestamptz":
            assert tipo_upper.startswith("TIMESTAMPTZ"), f"{nome}: esperado TIMESTAMPTZ, veio {tipo_sql}"
        elif tipo_copy == "text":
            assert tipo_upper.startswith("TEXT"), f"{nome}: esperado TEXT, veio {tipo_sql}"
        elif tipo_copy == "numeric":
            assert tipo_upper.startswith("NUMERIC"), f"{nome}: esperado NUMERIC, veio {tipo_sql}"
        else:
            raise AssertionError(f"Tipo COPY inesperado: {tipo_copy}")


def test_ddl_estacoes_alinha_com_sincronizar_estacoes_e_pk_cod_estacao():
    colunas_ddl = dict(_extrair_colunas_ddl("estacoes"))

    assert set(colunas_ddl.keys()) == set(sincronizar_estacoes.COLS)
    assert "PRIMARY KEY" in colunas_ddl["cod_estacao"].upper()
    assert "PRIMARY KEY" not in colunas_ddl["nome"].upper()
