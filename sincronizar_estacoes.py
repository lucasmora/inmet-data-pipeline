"""Busca metadados das estacoes do INMET e popula a tabela-dimensao 'estacoes'.

Fontes oficiais (endpoint publico do INMET):
  - https://apitempo.inmet.gov.br/estacoes/M  (manuais/convencionais)
  - https://apitempo.inmet.gov.br/estacoes/T  (automaticas)

Idempotente: roda quantas vezes quiser (UPSERT em 'cod_estacao').
Permite multiplas estacoes (Automatica e Convencional) na mesma cidade.
NAO toca em dados_estacoes (tabela de fatos) -- so cria/atualiza a dimensao.

Chave de join com dados_estacoes: estacoes.cod_estacao (CD_ESTACAO) = dados_estacoes.estacao
"""
import logging
import os
import time
from collections.abc import Sequence
from typing import Any

import requests

from db import get_conn

logger = logging.getLogger("sincronizar_estacoes")

ENDPOINTS: list[str] = [
    "https://apitempo.inmet.gov.br/estacoes/M",
    "https://apitempo.inmet.gov.br/estacoes/T",
]

# Ordem das colunas do INSERT (deve bater com a tabela 'estacoes')
COLS: list[str] = [
    "nome", "cod_estacao", "uf", "latitude", "longitude",
    "altitude", "tipo", "situacao",
]

EstacaoRow = tuple[
    str | None,
    str,
    str | None,
    float | None,
    float | None,
    float | None,
    str | None,
    str | None,
]


def _to_float(v: Any) -> float | None:
    """Converte para float ou None (campos VL_* do INMET vêm como string)."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def coletar() -> list[EstacaoRow]:
    """Retorna lista de tuplas em COLS, sem duplicar cod_estacao entre endpoints."""
    rows: list[EstacaoRow] = []
    visto: set[str] = set()
    for url in ENDPOINTS:
        logger.info("Consultando API INMET: url=%s", url)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        estacoes_api = resp.json()
        antes = len(rows)
        for st in estacoes_api:
            cod = st.get("CD_ESTACAO")
            if not cod or cod in visto:
                continue
            visto.add(cod)
            rows.append((
                st.get("DC_NOME"),       # nome (cidade/estacao)
                cod,                     # cod_estacao (PK / join)
                st.get("SG_ESTADO"),     # uf
                _to_float(st.get("VL_LATITUDE")),
                _to_float(st.get("VL_LONGITUDE")),
                _to_float(st.get("VL_ALTITUDE")),
                st.get("TP_ESTACAO"),    # tipo
                st.get("CD_SITUACAO"),   # situacao
            ))
        logger.debug(
            "Endpoint processado: url=%s recebidas=%d novas=%d",
            url,
            len(estacoes_api),
            len(rows) - antes,
        )
    return rows


def upsert(rows: Sequence[EstacaoRow]) -> None:
    """Insere ou atualiza em lote (UPSERT em 'cod_estacao')."""
    sql = """
        INSERT INTO estacoes (nome, cod_estacao, uf, latitude, longitude,
                              altitude, tipo, situacao)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (cod_estacao) DO UPDATE SET
            nome        = EXCLUDED.nome,
            uf          = EXCLUDED.uf,
            latitude    = EXCLUDED.latitude,
            longitude   = EXCLUDED.longitude,
            altitude    = EXCLUDED.altitude,
            tipo        = EXCLUDED.tipo,
            situacao    = EXCLUDED.situacao;
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.executemany(sql, rows)
        conn.commit()


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    inicio = time.perf_counter()
    try:
        dados = coletar()
        if not dados:
            logger.warning("Nenhuma estacao retornada pelos endpoints do INMET")
            return
        upsert(dados)
        duracao = time.perf_counter() - inicio
        logger.info(
            "Dimensao 'estacoes' atualizada: total=%d duracao_s=%.2f",
            len(dados),
            duracao,
        )
    except Exception:
        logger.exception("Falha ao coletar/atualizar estacoes do INMET")
        raise


if __name__ == "__main__":
    main()
