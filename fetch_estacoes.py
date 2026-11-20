"""Busca metadados das estacoes do INMET e popula a tabela-dimensao 'estacoes'.

Fontes oficiais (endpoint publico do INMET):
  - https://apitempo.inmet.gov.br/estacoes/M  (manuais/convencionais)
  - https://apitempo.inmet.gov.br/estacoes/T  (automaticas)

Idempotente: roda quantas vezes quiser (UPSERT em 'nome').
NAO toca em dados_estacoes (tabela de fatos) -- so cria/atualiza a dimensao.

Chave de join com dados_estacoes: estacoes.nome (DC_NOME) = dados_estacoes.cidade
"""
import requests

from db import get_conn

ENDPOINTS = [
    "https://apitempo.inmet.gov.br/estacoes/M",
    "https://apitempo.inmet.gov.br/estacoes/T",
]

# Ordem das colunas do INSERT (deve bater com a tabela 'estacoes')
COLS = ["nome", "cod_estacao", "uf", "latitude", "longitude",
        "altitude", "tipo", "situacao"]


def _to_float(v):
    """Converte para float ou None (campos VL_* do INMET vêm como string)."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def coletar():
    """Retorna lista de tuplas em COLS, sem duplicar cod_estacao entre endpoints."""
    rows = []
    visto = set()
    for url in ENDPOINTS:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        for st in resp.json():
            cod = st.get("CD_ESTACAO")
            if not cod or cod in visto:
                continue
            visto.add(cod)
            rows.append((
                st.get("DC_NOME"),       # nome (PK / join)
                cod,                     # cod_estacao
                st.get("SG_ESTADO"),     # uf
                _to_float(st.get("VL_LATITUDE")),
                _to_float(st.get("VL_LONGITUDE")),
                _to_float(st.get("VL_ALTITUDE")),
                st.get("TP_ESTACAO"),    # tipo
                st.get("CD_SITUACAO"),   # situacao
            ))
    return rows


def upsert(rows):
    """Insere ou atualiza em lote (UPSERT em 'nome')."""
    conn = get_conn()
    cur = conn.cursor()
    sql = """
        INSERT INTO estacoes (nome, cod_estacao, uf, latitude, longitude,
                              altitude, tipo, situacao)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (nome) DO UPDATE SET
            cod_estacao = EXCLUDED.cod_estacao,
            uf          = EXCLUDED.uf,
            latitude    = EXCLUDED.latitude,
            longitude   = EXCLUDED.longitude,
            altitude    = EXCLUDED.altitude,
            tipo        = EXCLUDED.tipo,
            situacao    = EXCLUDED.situacao;
    """
    cur.executemany(sql, rows)
    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    dados = coletar()
    upsert(dados)
    print(f"[ok] {len(dados)} estacoes inseridas/atualizadas na tabela 'estacoes'")
