"""Integracao arquitetural para exportacao do TimescaleDB ao Google BigQuery.

Em producao:
  1. Autenticacao via Service Account (GOOGLE_APPLICATION_CREDENTIALS).
  2. Execucao em Cloud Run / Cloud Functions ou Airflow (Cloud Composer).
  3. Defina `dry_run=False` (ou `BQ_DRY_RUN=false`) com `google-cloud-bigquery` instalado.
"""

import logging
import os

from dotenv import load_dotenv
import pandas as pd

try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None

logger = logging.getLogger("export_to_bigquery")


def exportar_para_bq(
    df: pd.DataFrame,
    table_id: str,
    *,
    dry_run: bool = True,
) -> None:
    """Exporta um DataFrame para o BigQuery (ou simula em modo dry_run/stub).

    Args:
        df: DataFrame com os dados meteorologicos.
        table_id: ID da tabela no BigQuery (`projeto.dataset.tabela`).
        dry_run: Quando True (padrao), apenas registra a operacao em log sem
            enviar dados para a nuvem.
    """
    try:
        if dry_run or bigquery is None:
            motivo = (
                "dry_run=True" if dry_run else "google-cloud-bigquery nao instalado"
            )
            logger.info(
                "Simulando exportacao para BigQuery (%s): table_id=%s linhas=%d",
                motivo,
                table_id,
                len(df),
            )
            return

        client = bigquery.Client()
        logger.info(
            "Exportando para BigQuery: table_id=%s linhas=%d", table_id, len(df)
        )
        job = client.load_table_from_dataframe(df, table_id)
        job.result()
        logger.info("Dados exportados com sucesso: table_id=%s", table_id)

    except Exception:
        logger.exception("Erro ao exportar para o BigQuery: table_id=%s", table_id)
        raise


def main() -> None:
    load_dotenv()

    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    table_id = os.getenv("BQ_TABLE_ID", "seu-projeto-gcp.meteo.dados_inmet")
    dry_run = os.getenv("BQ_DRY_RUN", "true").lower() not in ("0", "false", "no")

    df_amostra = pd.DataFrame({"data": ["2024-01-15"], "temp_ar": [25.5]})
    exportar_para_bq(df_amostra, table_id, dry_run=dry_run)


if __name__ == "__main__":
    main()
