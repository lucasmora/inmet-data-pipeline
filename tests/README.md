# Suíte de Testes (`pytest`)

Esta pasta contém os testes unitários e de contrato do pipeline **ETL Análise INMET**. Eles validam parsing, contratos de schema e regras de orquestração sem depender de Docker, banco TimescaleDB em execução ou acesso à internet.

## Como rodar

Após instalar as dependências (`pip install -r requirements.txt`), execute na raiz do repositório:

```bash
ruff check .
pytest -v
```

Os mesmos checks são executados automaticamente no GitHub Actions (`.github/workflows/ci.yml`) em Python 3.12 a cada `push` e `pull_request`.

## Estrutura dos testes

| Arquivo | Alvo | O que valida |
|---------|------|--------------|
| `conftest.py` | Fixtures compartilhadas | Geradores de CSVs sintéticos no formato INMET (`latin_1`, `;`, `skiprows=8`) e `DataFrame`s brutos de teste. |
| `test_transform.py` | `transform.py` e `data/*.CSV` | Extração de metadados do nome do arquivo (`extrair_metadados`), remoção da coluna vazia final, conversão de `data_hora` para `TIMESTAMPTZ` em UTC, conversão de vírgula para `Decimal` sem perda de precisão, nulos e valores sentinela do INMET (`-9999`) como `None`, erros em entradas malformadas e validação dos 5 CSVs reais de amostra em `data/`. |
| `test_schema_contract.py` | `transform.py` × `db.py` × `sincronizar_estacoes.py` × `db-init/01-init-timescaledb.sql` | Alinhamento exato (quantidade, ordem e tipos) entre a saída de `parse_chunk`, `db.COLUMNS`, `db.COPY_TYPES` e o DDL da tabela `dados_estacoes`, além do contrato de colunas e `PRIMARY KEY` (`cod_estacao`) entre `sincronizar_estacoes.COLS` e o DDL da tabela `estacoes`. |
| `test_db.py` | `db.py` | Montagem do comando `COPY ... FROM STDIN (FORMAT BINARY)`, `set_types`, escrita ordenada em `copy_rows` e leitura de `DB_CONFIG` via variáveis de ambiente (com mocks de `psycopg`). |
| `test_ingest.py` | `ingest.py` | Controle de `ingestao_status` (`ja_ingerido`, `marcar`), fatiamento por `CHUNK_SIZE` e `BATCH_SIZE`, tratamento de CSV vazio e `on_bad_lines="skip"`, skip de arquivos inválidos/já ingeridos e `commit`/`rollback` isolados por arquivo em `main()`. |
| `test_sincronizar_estacoes.py` | `sincronizar_estacoes.py` | Conversão numérica (`_to_float`), consulta aos endpoints `/M` e `/T` com deduplicação por `CD_ESTACAO` (preservando estações manuais e automáticas da mesma cidade), propagação de erro HTTP e comando de `UPSERT` por `cod_estacao` em `estacoes` (com mocks de `requests` e banco). |
| `test_export_bigquery.py` | `analytics/export_to_bigquery.py` | Execução em modo `dry_run` (sem `google-cloud-bigquery` instalado) e envio ao cliente BigQuery quando `dry_run=False`. |

## Escopo e limites desta camada

- **Sem dependências externas:** banco (`psycopg`), API do INMET (`requests`) e sistema de arquivos usam mocks e pastas temporárias (`tmp_path`).
- **Fora do escopo atual:** testes de integração ponta a ponta contra um container TimescaleDB real (precisão `NUMERIC(x,y)`, `create_hypertable`, queries `time_bucket`) e execução do notebook `analytics/EDA_INMET.ipynb`.
