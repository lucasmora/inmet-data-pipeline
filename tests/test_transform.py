"""Testes unitários para extração de metadados e transformação de chunks (transform.py)."""
from datetime import timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import db
from tests.conftest import default_inmet_row
from transform import NUMERICAS, extrair_metadados, parse_chunk


@pytest.mark.parametrize(
    ("nome_arquivo", "esperado"),
    [
        (
            "INMET_CO_DF_A001_BRASILIA_01-01-2023_A_31-12-2023.CSV",
            {"regiao": "CO", "estado": "DF", "estacao": "A001", "cidade": "BRASILIA"},
        ),
        (
            "INMET_N_AM_A101_MANAUS_01-01-2024_A_31-12-2024.CSV",
            {"regiao": "N", "estado": "AM", "estacao": "A101", "cidade": "MANAUS"},
        ),
        (
            "INMET_S_RS_A801_PORTO ALEGRE_01-01-2024_A_31-12-2024.CSV",
            {"regiao": "S", "estado": "RS", "estacao": "A801", "cidade": "PORTO ALEGRE"},
        ),
        (
            "INMET_SE_MG_A521_BELO HORIZONTE (PAMPULHA)_01-01-2024_A_31-12-2024.CSV",
            {
                "regiao": "SE",
                "estado": "MG",
                "estacao": "A521",
                "cidade": "BELO HORIZONTE (PAMPULHA)",
            },
        ),
        (
            "INMET_SE_SP_A701_SAO PAULO - MIRANTE_01-01-2024_A_31-12-2024.CSV",
            {
                "regiao": "SE",
                "estado": "SP",
                "estacao": "A701",
                "cidade": "SAO PAULO - MIRANTE",
            },
        ),
        (
            "INMET_NE_MA_A203_SÃO LUÍS_01-01-2024_A_31-12-2024.CSV",
            {"regiao": "NE", "estado": "MA", "estacao": "A203", "cidade": "SÃO LUÍS"},
        ),
        (
            "/dados/2024/INMET_SE_RJ_A602_Paty do Alferes - Avelar_01-01-2024.CSV",
            {
                "regiao": "SE",
                "estado": "RJ",
                "estacao": "A602",
                "cidade": "Paty do Alferes - Avelar",
            },
        ),
        (
            "INMET_NE_AL_A303_OLHO D'AGUA DO CASADO_01-01-2024_A_31-12-2024.CSV",
            {
                "regiao": "NE",
                "estado": "AL",
                "estacao": "A303",
                "cidade": "OLHO D'AGUA DO CASADO",
            },
        ),
    ],
)
def test_extrair_metadados_validos(nome_arquivo, esperado):
    assert extrair_metadados(nome_arquivo) == esperado


@pytest.mark.parametrize(
    "nome_invalido",
    [
        "README.md",
        "dados_2023.csv",
        "INMET_INVALIDO.CSV",
        "inmet_co_df_a001_brasilia_01-01-2023.csv",
        "INMET_CO_DF_BRASILIA_01-01-2023.CSV",
        "INMET_CO_DF_1234_BRASILIA_01-01-2023.CSV",
    ],
)
def test_extrair_metadados_invalidos_retorna_none(nome_invalido):
    assert extrair_metadados(nome_invalido) is None


@pytest.mark.parametrize("trailing_empty_col", [True, False])
def test_parse_chunk_aceita_19_ou_20_colunas_e_nao_muta_entrada(
    build_raw_df, meta_brasilia, trailing_empty_col
):
    raw = build_raw_df(trailing_empty_col=trailing_empty_col)
    copia_original = raw.copy(deep=True)

    resultado = parse_chunk(raw, meta_brasilia)

    pd.testing.assert_frame_equal(raw, copia_original)
    assert len(resultado.columns) == 22
    assert list(resultado.columns[:5]) == [
        "data_hora",
        "regiao",
        "estado",
        "estacao",
        "cidade",
    ]
    assert resultado.iloc[0]["regiao"] == "CO"
    assert resultado.iloc[0]["estado"] == "DF"
    assert resultado.iloc[0]["estacao"] == "A001"
    assert resultado.iloc[0]["cidade"] == "BRASILIA"


def test_parse_chunk_converte_data_hora_para_utc(build_raw_df, meta_brasilia):
    rows = [
        default_inmet_row(data="2023/01/01", hora="0000 UTC"),
        default_inmet_row(data="2023/12/31", hora="2300 UTC"),
    ]
    raw = build_raw_df(rows)

    resultado = parse_chunk(raw, meta_brasilia)

    ts0 = resultado.iloc[0]["data_hora"]
    ts1 = resultado.iloc[1]["data_hora"]
    assert ts0.tzinfo == timezone.utc
    assert ts0 == pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    assert ts1 == pd.Timestamp("2023-12-31 23:00:00", tz="UTC")


def test_parse_chunk_converte_numericas_para_decimal_sem_artefatos_float(
    build_raw_df, meta_brasilia
):
    row = default_inmet_row(temp_ar=" -12,3 ")
    row[2] = "0,1"      # precipitacao (0.1 tem representacao imprecisa em float binario)
    row[6] = "1234,56"  # radiacao
    row[15] = "100"     # umidade_ar (inteiro)
    raw = build_raw_df([row])

    resultado = parse_chunk(raw, meta_brasilia)
    linha = resultado.iloc[0]

    assert isinstance(linha["temp_ar"], Decimal)
    assert linha["temp_ar"] == Decimal("-12.3")
    assert isinstance(linha["precipitacao"], Decimal)
    assert linha["precipitacao"] == Decimal("0.1")
    assert linha["radiacao"] == Decimal("1234.56")
    assert linha["umidade_ar"] == Decimal("100")

    for col in NUMERICAS:
        assert isinstance(linha[col], Decimal)


def test_parse_chunk_converte_nulos_e_vazios_para_none_real(build_raw_df, meta_brasilia):
    row = default_inmet_row()
    row[2] = ""          # string vazia
    row[3] = "   "       # espacos
    row[4] = None        # None
    row[5] = np.nan      # NaN numerico
    raw = build_raw_df([row])

    resultado = parse_chunk(raw, meta_brasilia)
    linha = resultado.iloc[0]

    for col in ("precipitacao", "pressao", "pressao_max_ant", "pressao_min_ant"):
        assert linha[col] is None


def test_parse_chunk_falha_em_data_malformada(build_raw_df, meta_brasilia):
    row = default_inmet_row(data="15-01-2023", hora="12:00")
    raw = build_raw_df([row])

    with pytest.raises(ValueError):
        parse_chunk(raw, meta_brasilia)


def test_parse_chunk_falha_em_valor_nao_numerico(build_raw_df, meta_brasilia):
    row = default_inmet_row(temp_ar="INVALIDO")
    raw = build_raw_df([row])

    with pytest.raises(InvalidOperation):
        parse_chunk(raw, meta_brasilia)


def test_dataset_amostra_em_data_e_valido():
    pasta_data = Path(__file__).resolve().parent.parent / "data"
    arquivos = sorted(pasta_data.glob("*.CSV"))
    assert len(arquivos) == 5

    for caminho in arquivos:
        meta = extrair_metadados(caminho.name)
        assert meta is not None, f"Falha ao extrair metadados de {caminho.name}"

        df_bruto = pd.read_csv(caminho, sep=";", encoding="latin_1", skiprows=8)
        df_tratado = parse_chunk(df_bruto, meta)

        assert len(df_tratado) == 128
        assert df_tratado.columns.tolist() == db.COLUMNS
