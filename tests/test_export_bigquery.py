"""Smoke test para o stub de exportação ao BigQuery."""
import pandas as pd

from analytics.export_to_bigquery import exportar_para_bq


def test_exportar_para_bq_executa_stub_sem_google_cloud_bigquery(caplog):
    df = pd.DataFrame({"data": ["2023-01-01"], "temp": [25.5]})

    with caplog.at_level("INFO"):
        exportar_para_bq(df, "projeto-teste.meteo.dados_inmet")

    assert "projeto-teste.meteo.dados_inmet" in caplog.text
