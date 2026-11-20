"""Fixtures compartilhadas para a suíte de testes unitários e de contrato."""
import pandas as pd
import pytest

from transform import COLUNAS_BRUTAS


INMET_HEADER_METADATA = [
    "REGIAO:;CO",
    "UF:;DF",
    "ESTACAO:;BRASILIA",
    "CODIGO (WMO):;A001",
    "LATITUDE:;-15,78944444",
    "LONGITUDE:;-47,92583333",
    "ALTITUDE:;1160,96",
    "DATA DE FUNDACAO:;07/05/00",
]

INMET_COLUMN_NAMES = [
    "Data",
    "Hora UTC",
    "PRECIPITACAO TOTAL, HORARIO (mm)",
    "PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)",
    "PRESSAO ATMOSFERICA MAX.NA HORA ANT. (AUT) (mB)",
    "PRESSAO ATMOSFERICA MIN. NA HORA ANT. (AUT) (mB)",
    "RADIACAO GLOBAL (Kj/m2)",
    "TEMPERATURA DO AR - BULBO SECO, HORARIA (C)",
    "TEMPERATURA DO PONTO DE ORVALHO (C)",
    "TEMPERATURA MAXIMA NA HORA ANT. (AUT) (C)",
    "TEMPERATURA MINIMA NA HORA ANT. (AUT) (C)",
    "TEMPERATURA ORVALHO MAX. NA HORA ANT. (AUT) (C)",
    "TEMPERATURA ORVALHO MIN. NA HORA ANT. (AUT) (C)",
    "UMIDADE REL. MAX. NA HORA ANT. (AUT) (%)",
    "UMIDADE REL. MIN. NA HORA ANT. (AUT) (%)",
    "UMIDADE RELATIVA DO AR, HORARIA (%)",
    "VENTO, DIRECAO HORARIA (gr) ((gr))",
    "VENTO, RAJADA MAXIMA (m/s)",
    "VENTO, VELOCIDADE HORARIA (m/s)",
]


def default_inmet_row(data="2023/01/15", hora="1200 UTC", temp_ar="25,4"):
    """Retorna uma linha com os 19 campos brutos esperados de um CSV do INMET."""
    return [
        data,
        hora,
        "0,0",      # precipitacao
        "887,2",    # pressao
        "887,5",    # pressao_max_ant
        "886,9",    # pressao_min_ant
        "1234,56",  # radiacao
        temp_ar,    # temp_ar
        "18,1",     # temp_orvalho
        "26,0",     # temp_max_ant
        "24,8",     # temp_min_ant
        "18,5",     # temp_orvalho_max_ant
        "17,9",     # temp_orvalho_min_ant
        "68",       # umidade_max_ant
        "62",       # umidade_min_ant
        "65",       # umidade_ar
        "180",      # vento_dir
        "4,2",      # vento_rajada
        "2,1",      # vento_vel
    ]


@pytest.fixture
def meta_brasilia():
    """Metadados canônicos de exemplo para a estação de Brasília."""
    return {
        "regiao": "CO",
        "estado": "DF",
        "estacao": "A001",
        "cidade": "BRASILIA",
    }


@pytest.fixture
def build_raw_df():
    """Fábrica de DataFrames brutos simulando leitura após skiprows=8."""

    def _build(rows=None, trailing_empty_col=True):
        if rows is None:
            rows = [default_inmet_row()]
        cols = list(INMET_COLUMN_NAMES)
        data_rows = [list(r) for r in rows]
        if trailing_empty_col:
            cols.append("Unnamed: 19")
            data_rows = [r + [float("nan")] for r in data_rows]
        assert len(cols) >= len(COLUNAS_BRUTAS)
        return pd.DataFrame(data_rows, columns=cols)

    return _build


@pytest.fixture
def make_inmet_csv(tmp_path):
    """Cria arquivos CSV sintéticos no formato bruto do INMET (latin_1, ';')."""

    def _make(filename, rows=None, trailing_semicolon=True, raw_extra_lines=None):
        path = tmp_path / filename
        lines = list(INMET_HEADER_METADATA)
        header_suffix = ";" if trailing_semicolon else ""
        lines.append(";".join(INMET_COLUMN_NAMES) + header_suffix)

        for row in rows or []:
            lines.append(";".join(row) + header_suffix)

        for extra in raw_extra_lines or []:
            lines.append(extra)

        path.write_text("\n".join(lines) + "\n", encoding="latin_1")
        return path

    return _make
