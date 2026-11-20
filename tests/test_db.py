"""Testes unitários para db.py (helper de COPY binário e configuração)."""
import importlib
from unittest.mock import MagicMock

import db


def test_copy_rows_configura_tipos_e_escreve_linhas_em_ordem():
    copy_ctx = MagicMock()
    copy_obj = copy_ctx.__enter__.return_value
    cur = MagicMock()
    cur.copy.return_value = copy_ctx

    rows = [
        ("row1_a", "row1_b"),
        ("row2_a", "row2_b"),
    ]

    db.copy_rows(cur, rows)

    sql_esperado = (
        "COPY dados_estacoes (" + ", ".join(db.COLUMNS) + ") FROM STDIN (FORMAT BINARY)"
    )
    cur.copy.assert_called_once_with(sql_esperado)
    copy_obj.set_types.assert_called_once_with(db.COPY_TYPES)
    assert [c.args[0] for c in copy_obj.write_row.call_args_list] == rows
    copy_ctx.__exit__.assert_called_once()


def test_copy_rows_com_lista_vazia_nao_escreve_linhas():
    copy_ctx = MagicMock()
    copy_obj = copy_ctx.__enter__.return_value
    cur = MagicMock()
    cur.copy.return_value = copy_ctx

    db.copy_rows(cur, [])

    copy_obj.set_types.assert_called_once_with(db.COPY_TYPES)
    copy_obj.write_row.assert_not_called()


def test_get_conn_usa_db_config(monkeypatch):
    mock_connect = MagicMock()
    monkeypatch.setattr(db.psycopg, "connect", mock_connect)

    conn = db.get_conn()

    mock_connect.assert_called_once_with(**db.DB_CONFIG)
    assert conn is mock_connect.return_value


def test_db_config_respeita_variaveis_de_ambiente(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "db.exemplo.internal")
    monkeypatch.setenv("POSTGRES_PORT", "5439")
    monkeypatch.setenv("POSTGRES_USER", "etl_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "segredo")
    monkeypatch.setenv("POSTGRES_DB", "inmet_test")

    reloaded = importlib.reload(db)
    try:
        assert reloaded.DB_CONFIG == {
            "host": "db.exemplo.internal",
            "port": 5439,
            "user": "etl_user",
            "password": "segredo",
            "dbname": "inmet_test",
        }
        assert isinstance(reloaded.DB_CONFIG["port"], int)
    finally:
        monkeypatch.undo()
        importlib.reload(db)
