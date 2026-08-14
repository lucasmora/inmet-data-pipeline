"""Orquestrador de ingestao incremental (Big Data) para o TimescaleDB.

Fluxo:
  1. Lista os CSVs de entrada.
  2. Pula os ja ingeridos (tabela ingestao_status) -> retomavel/idempotente.
  3. Le cada arquivo EM CHUNKS (pandas.read_csv(chunksize)).
  4. Aplica transform.parse_chunk e acumula em buffer.
  5. A cada BATCH_SIZE linhas, faz COPY binario e commita.
  6. Marca o arquivo como ingerido.

Nunca carrega o dataset inteiro (4,9M linhas) na memoria (Volume).
"""
import os
import glob
import pandas as pd
from dotenv import load_dotenv

from db import get_conn, copy_rows
from transform import extrair_metadados, parse_chunk

load_dotenv()

PASTA_ENTRADA = os.getenv("PASTA_ENTRADA", r"C:\Users\moral\Downloads\meteorologia")
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


def main():
    conn = get_conn()
    cur = conn.cursor()
    arquivos = sorted(glob.glob(os.path.join(PASTA_ENTRADA, "*.CSV")))
    total_geral = 0

    if not arquivos:
        print(f"Nenhum CSV encontrado em {PASTA_ENTRADA}")

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        meta = extrair_metadados(nome)
        if not meta:
            print(f"[pular] padrao nao reconhecido: {nome}")
            continue
        if ja_ingerido(cur, nome):
            print(f"[skip] ja ingerido: {nome}")
            continue

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
                conn.commit()
                total_geral += len(lote)
                linhas_arquivo += len(lote)

        if buffer:
            copy_rows(cur, buffer)
            conn.commit()
            total_geral += len(buffer)
            linhas_arquivo += len(buffer)

        marcar(cur, nome, linhas_arquivo)
        conn.commit()
        print(f"[ok] {nome}: {linhas_arquivo} linhas")

    cur.close()
    conn.close()
    print(f"Fim. Total ingerido nesta execucao: {total_geral}")


if __name__ == "__main__":
    main()
