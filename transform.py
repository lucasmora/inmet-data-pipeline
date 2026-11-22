"""Transformacao dos CSVs brutos do INMET para o formato canonico da tabela.

Opera por chunk (pandas.read_csv com chunksize) para manter o uso de memoria
constante mesmo ao processar milhoes de registros.
"""
import re
from decimal import Decimal
from typing import Any

import pandas as pd

# Metadados extraidos do NOME do arquivo (ex: INMET_CO_DF_A001_BRASILIA_...)
PADRAO_ARQUIVO: re.Pattern[str] = re.compile(
    r"INMET_(?P<regiao>[A-Z]{1,2})_"
    r"(?P<estado>[A-Z]{2})_"
    r"(?P<estacao>[A-Z]\d{3})_"
    r"(?P<cidade>[A-Za-zÀ-ÿ0-9().'\-\s]+)_"
)

# Ordem das colunas APOS skiprows=8 e descartar a ultima coluna vazia do INMET.
# Usamos posicao (nao nome) para nao depender de acentos/encoding do cabecalho.
COLUNAS_BRUTAS: list[str] = [
    "Data", "Hora UTC",
    "precipitacao", "pressao", "pressao_max_ant", "pressao_min_ant",
    "radiacao", "temp_ar", "temp_orvalho", "temp_max_ant", "temp_min_ant",
    "temp_orvalho_max_ant", "temp_orvalho_min_ant", "umidade_max_ant",
    "umidade_min_ant", "umidade_ar", "vento_dir", "vento_rajada", "vento_vel",
]

NUMERICAS: list[str] = COLUNAS_BRUTAS[2:]  # as 17 medicoes


def extrair_metadados(nome_arquivo: str) -> dict[str, str] | None:
    """Retorna dict {regiao, estado, estacao, cidade} ou None."""
    m = PADRAO_ARQUIVO.search(nome_arquivo)
    return m.groupdict() if m else None


def parse_chunk(df: pd.DataFrame, meta: dict[str, str]) -> pd.DataFrame:
    """Recebe um chunk bruto do CSV INMET e devolve DataFrame canonico.

    `df` ja vem com skiprows=8, sep=';', encoding='latin_1'.
    Retorna DataFrame com as 22 colunas na ordem da tabela dados_estacoes.
    """
    df = df.copy()
    # mantem so as 19 colunas conhecidas (descarta a ultima vazia do INMET)
    df = df.iloc[:, : len(COLUNAS_BRUTAS)]
    df.columns = COLUNAS_BRUTAS

    # metadados do arquivo (Variety: extraidos na borda)
    df.insert(0, "regiao", meta["regiao"])
    df.insert(1, "estado", meta["estado"])
    df.insert(2, "estacao", meta["estacao"])
    df.insert(3, "cidade", meta["cidade"])

    # data_hora como TIMESTAMPTZ (UTC aware) -> atende Veracity/tipos fortes
    hora = (
        df["Hora UTC"].astype(str).str.replace(" UTC", "", regex=False).str.strip()
    )
    df["data_hora"] = pd.to_datetime(
        df["Data"].astype(str) + " " + hora,
        format="%Y/%m/%d %H%M",
        utc=True,
    )
    df = df.drop(columns=["Data", "Hora UTC"])

    # numericas: virgula -> ponto, vazios/sentinelas (-9999) -> None, e converte para Decimal.
    # O psycopg3 em COPY binario exige Decimal para colunas numeric (nao aceita
    # float), preservando precisao. Converte da string para evitar artefatos de
    # ponto flutuante.
    def _para_decimal(v: Any) -> Decimal | None:
        if v is None or pd.isna(v) or (isinstance(v, str) and v.strip() in ("", "nan", "None")):
            return None
        d = Decimal(str(v))
        if d.is_nan() or d <= Decimal("-999"):
            return None
        return d

    for col in NUMERICAS:
        s = (
            df[col].astype(str)
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
        df[col] = s.map(_para_decimal)

    ordem = ["data_hora", "regiao", "estado", "estacao", "cidade"] + NUMERICAS
    df = df[ordem]
    # converte NaN remanescentes em None (NULL no banco)
    df = df.where(pd.notnull(df), None)
    return df
