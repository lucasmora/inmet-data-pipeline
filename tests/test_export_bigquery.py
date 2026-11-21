"""Testes para o módulo de exportação ao BigQuery."""
from unittest.mock import MagicMock

import pandas as pd

from analytics import export_to_bigquery
from analytics.export_to_bigquery import exportar_para_bq


def test_exportar_para_bq_executa_stub_sem_google_cloud_bigquery(caplog):
    df = pd.DataFrame({"data": ["2024-01-01"], "temp": [25.5]})

    with caplog.at_level("INFO"):
        exportar_para_bq(df, "projeto-teste.meteo.dados_inmet")

    assert "projeto-teste.meteo.dados_inmet" in caplog.text


def test_exportar_para_bq_envia_dataframe_quando_dry_run_false(monkeypatch):
    df = pd.DataFrame({"data": ["2024-01-01"], "temp": [25.5]})
    fake_bq = MagicMock()
    fake_client = fake_bq.Client.return_value
    monkeypatch.setattr(export_to_bigquery, "bigquery", fake_bq)

    exportar_para_bq(df, "projeto-teste.meteo.dados_inmet", dry_run=False)

    fake_bq.Client.assert_called_once_with()
    fake_client.load_table_from_dataframe.assert_called_once_with(
        df, "projeto-teste.meteo.dados_inmet"
    )
    fake_client.load_table_from_dataframe.return_value.result.assert_called_once_with()
