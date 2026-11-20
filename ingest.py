"""Orquestrador de ingestao incremental (Big Data) para o TimescaleDB.

Fluxo:
  1. Lista os CSVs de entrada.
  2. Pula os ja ingeridos (tabela ingestao_status) -> retomavel/idempotente.
  3. Le cada arquivo EM CHUNKS (pandas.read_csv(chunksize)).
  4. Aplica transform.parse_chunk e acumula em buffer.
  5. A cada BATCH_SIZE linhas, envia via COPY binario na transacao do arquivo.
  6. Ao concluir o arquivo, marca como ingerido e faz commit (rollback em erro).

Nunca carrega o dataset inteiro (4,9M linhas) na memoria (Volume).
"""
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

from db import get_conn, copy_rows
from transform import extrair_metadados, parse_chunk

load_dotenv()

PASTA_ENTRADA = os.getenv("PASTA_ENTRADA", "./data")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50000"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "100000"))


def ja_ingerido(cur, arquivo):
    cur.execute("SELECT 1 FROM ingestao_status WHERE arquivo = %s", (arquivo,))
    return cur.fetchone() is not None


def marcar(cur, arquivo, total):
    cur.execute(
        "INSERT INTO ingestao_status (arquivo, total_linhas, status) "
        "VALUES (%s, %s, 'ok') "
        "ON CONFLICT (arquivo) DO UPDATE SET "
        "total_linhas = EXCLUDED.total_linhas, "
        "processado_em = now(), status = 'ok'",
        (arquivo, total),
    )


def ingerir_arquivo(cur, caminho, meta):
    """Le um CSV em chunks e envia lotes via COPY binario sem commitar no meio."""
    buffer = []
    linhas_arquivo = 0

    for chunk in pd.read_csv(
        caminho,
        sep=";",
        encoding="latin_1",
        skiprows=8,
        chunksize=CHUNK_SIZE,
        on_bad_lines="skip",
    ):
        df = parse_chunk(chunk, meta)
        for row in df.itertuples(index=False, name=None):
            buffer.append(row)
        while len(buffer) >= BATCH_SIZE:
            lote = buffer[:BATCH_SIZE]
            del buffer[:BATCH_SIZE]
            copy_rows(cur, lote)
            linhas_arquivo += len(lote)

    if buffer:
        copy_rows(cur, buffer)
        linhas_arquivo += len(buffer)

    return linhas_arquivo


def main():
    pasta = Path(PASTA_ENTRADA)
    arquivos = (
        sorted(
            str(p)
            for p in pasta.iterdir()
            if p.is_file() and p.suffix.lower() == ".csv"
        )
        if pasta.is_dir()
        else []
    )
    total_geral = 0

    if not arquivos:
        print(f"Nenhum CSV encontrado em {PASTA_ENTRADA}")
        return

    with get_conn() as conn, conn.cursor() as cur:
        for caminho in arquivos:
            nome = os.path.basename(caminho)
            meta = extrair_metadados(nome)
            if not meta:
                print(f"[pular] padrao nao reconhecido: {nome}")
                continue
            if ja_ingerido(cur, nome):
                print(f"[skip] ja ingerido: {nome}")
                continue

            try:
                linhas_arquivo = ingerir_arquivo(cur, caminho, meta)
                marcar(cur, nome, linhas_arquivo)
                conn.commit()
                total_geral += linhas_arquivo
                print(f"[ok] {nome}: {linhas_arquivo} linhas")
            except Exception as exc:
                conn.rollback()
                print(f"[erro] {nome}: {exc}")

    print(f"Fim. Total ingerido nesta execucao: {total_geral}")


if __name__ == "__main__":
    main()
