"""Consultas de exemplo sobre a hypertable dados_estacoes (TimescaleDB).

Cada funcao e uma questao de negocio sobre series temporais meteorologicas.
Use o bloco `if __name__ == "__main__"` no final para rodar todas, ou
importe e chame individualmente.

Padrao de retomada: todas usam a conexao de db.py (le o .env, porta 5433).
"""

from db import get_conn


def total_precipitacao_por_mes(cur):
    """Volume mensal de precipitacao (soma por mes via time_bucket)."""
    cur.execute("""
        SELECT time_bucket('1 month', data_hora) AS mes,
               sum(precipitacao) AS precip_total
        FROM dados_estacoes
        WHERE precipitacao IS NOT NULL
        GROUP BY mes
        ORDER BY mes
        LIMIT 50;
        """)
    return cur.fetchall()


def temperatura_maxima_por_estado(cur):
    """Maior temperatura registrada por estado (extremos)."""
    cur.execute("""
        SELECT estado, max(temp_ar) AS temp_max
        FROM dados_estacoes
        WHERE temp_ar IS NOT NULL
        GROUP BY estado
        ORDER BY temp_max DESC;
        """)
    return cur.fetchall()


def janela_movel_umidade(cur):
    """Media movel de 24h de umidade relativa (analytics de serie temporal)."""
    cur.execute("""
        SELECT estacao,
               data_hora,
               avg(umidade_ar) OVER (
                   PARTITION BY estacao
                   ORDER BY data_hora
                   RANGE BETWEEN INTERVAL '23 hours' PRECEDING AND CURRENT ROW
               ) AS umidade_movel_24h
        FROM dados_estacoes
        WHERE umidade_ar IS NOT NULL
        ORDER BY estacao, data_hora
        LIMIT 100;
        """)
    return cur.fetchall()


def contagens_por_regiao(cur):
    """Quantidade de medicoes por regiao (visao de distribuicao do dataset)."""
    cur.execute("""
        SELECT regiao, count(*) AS n_medicoes
        FROM dados_estacoes
        GROUP BY regiao
        ORDER BY n_medicoes DESC;
        """)
    return cur.fetchall()


def ultimas_medicoes(cur, n=20):
    """n medicoes mais recentes do dataset."""
    cur.execute(
        """
        SELECT data_hora, estacao, temp_ar, umidade_ar, vento_vel
        FROM dados_estacoes
        ORDER BY data_hora DESC
        LIMIT %s;
        """,
        (n,),
    )
    return cur.fetchall()


def main():
    """Executa todas as consultas e imprime os resultados."""
    conn = get_conn()
    cur = conn.cursor()
    funcoes = [
        # ("Total de precipitacao por mes", total_precipitacao_por_mes),
        # ("Temperatura maxima por estado", temperatura_maxima_por_estado),
        # ("Janela movel de umidade (24h)", janela_movel_umidade),
        # ("Contagens por regiao", contagens_por_regiao),
        ("Ultimas medicoes", ultimas_medicoes),
    ]
    for titulo, fn in funcoes:
        print(f"\n=== {titulo} ===")
        for linha in fn(cur):
            print(linha)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
