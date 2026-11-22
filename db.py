"""Conexao com o TimescaleDB e helper de ingestao em lote (COPY binario).

O COPY binario do psycopg3 e o mecanismo de alta performance recomendado
pela Timescale para ingerir grandes volumes (Big Data / Velocity).
"""
import os
from collections.abc import Sequence
from typing import Any

import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG: dict[str, Any] = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5433")),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "dbname": os.getenv("POSTGRES_DB", "inmet"),
}

# Ordem EXATA das colunas da tabela dados_estacoes (22 colunas)
COLUMNS: list[str] = [
    "data_hora", "regiao", "estado", "estacao", "cidade",
    "precipitacao", "pressao", "pressao_max_ant", "pressao_min_ant",
    "radiacao", "temp_ar", "temp_orvalho", "temp_max_ant", "temp_min_ant",
    "temp_orvalho_max_ant", "temp_orvalho_min_ant", "umidade_max_ant",
    "umidade_min_ant", "umidade_ar", "vento_dir", "vento_rajada", "vento_vel",
]

# Tipos do COPY binario, na mesma ordem de COLUMNS
COPY_TYPES: list[str] = ["timestamptz", "text", "text", "text", "text"] + ["numeric"] * 17


def get_conn() -> psycopg.Connection[Any]:
    """Abre uma conexao com o banco."""
    return psycopg.connect(**DB_CONFIG)


def copy_rows(cur: psycopg.Cursor[Any], rows: Sequence[Sequence[Any]]) -> None:
    """Insere um lote de tuplas via COPY FROM STDIN (formato binario).

    `rows` deve ser uma lista de tuplas na ordem de COLUMNS.
    Valores nulos devem ser None (NAO NaN).
    """
    with cur.copy(
        "COPY dados_estacoes (" + ", ".join(COLUMNS) + ") FROM STDIN (FORMAT BINARY)"
    ) as copy:
        copy.set_types(COPY_TYPES)
        for row in rows:
            copy.write_row(row)
