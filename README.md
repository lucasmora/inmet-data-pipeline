<div align="center">

# 🌦️ ETL Análise INMET

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![TimescaleDB](https://img.shields.io/badge/TimescaleDB-PostgreSQL--17-336791?style=flat-square&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=flat-square&logo=docker&logoColor=white)
[![CI](https://github.com/lucasmora/inmet-data-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/lucasmora/inmet-data-pipeline/actions/workflows/ci.yml)
[![Licença](https://img.shields.io/badge/Licen%C3%A7a-MIT-22c55e?style=flat-square)](LICENSE)
![Versão](https://img.shields.io/badge/Vers%C3%A3o-1.1.0-blue?style=flat-square)

</div>

**Descrição**
-------------
Pipeline **ETL** para dados meteorológicos do **INMET** (Instituto Nacional de Meteorologia) com camada analítica de séries temporais. O pipeline lê arquivo a arquivo, em *chunks*, e alimenta o **TimescaleDB** em lotes via protocolo *COPY* binário.

**Objetivo**
-----------
Ingerir de forma incremental, retomável e idempotente milhões de linhas de séries temporais meteorológicas (4,9M+ registros) em um banco particionado por tempo, consultável em segundos e pronto para *analytics* de série temporal, com o mínimo de memória e sem dependência de instalação nativa de banco no Windows.

**Origem dos Dados**
-------------------
Os dados brutos são baixados do **portal oficial do INMET** (Instituto Nacional de Meteorologia). O portal fornece arquivos **compactados em ZIP** por ano, contendo **um CSV por estação** para todo o período (com medições horárias). Os arquivos seguem o padrão `INMET_<REGIÃO>_<UF>_<CÓDIGO>_<CIDADE>_<datas>.CSV`, com ~8 linhas de cabeçalho antes dos dados (descartadas via `skiprows=8`), separador `;`, encoding `latin-1` e a última coluna vazia. O parsing é feito **na borda, arquivo a arquivo**: o `transform.py` extrai os metadados (região, UF, código, cidade) do próprio nome do arquivo e normaliza as colunas do formato INMET para o formato canônico da tabela.

**Stack Tecnológico**
--------------------
| Camada | Tecnologia |
|--------|------------|
| **Linguagem** | Python ≥ 3.11 |
| **ETL/Transform** | Pandas (`read_csv` em *chunks*) + `re` (parsing de metadados) |
| **Banco** | TimescaleDB (extensão de PostgreSQL 17 para séries temporais) rodando em Docker |
| **Driver** | `psycopg[binary]` 3.x — *COPY* binário de alta performance |
| **Container** | Docker + docker compose (apenas o banco: PostgreSQL 17 com TimescaleDB pré-compilado) |
| **Config** | `python-dotenv` (variáveis de ambiente em `.env`) |

**Arquitetura do Pipeline**
--------------------------
```mermaid
flowchart LR
    A["CSVs INMET (ZIPs por estação)"] --> B["transform.py (Parse em chunks + metadados)"]
    B --> C["ingest.py (Lotes via COPY binário)"]
    C --> D[("TimescaleDB (dados_estacoes + ingestao_status)")]
    E["API Pública INMET (/estacoes/M e /T)"] --> F["sincronizar_estacoes.py (UPSERT idempotente)"]
    F --> G[("Dimensão estacoes (Star Schema)")]
    D --> H["EDA_INMET.ipynb / BI (time_bucket + JOIN)"]
    G --> H
```

**Benchmark (Base Completa INMET 2024)**
----------------------------------------
Métricas medidas em execução real ponta a ponta contra o **TimescaleDB (PostgreSQL 17)** em Docker local (Windows), com `CHUNK_SIZE=100000`, `BATCH_SIZE=50000` e carga via protocolo `COPY FROM STDIN (FORMAT BINARY)`:

| Camada | Métrica | Resultado Medido |
|---|---|---|
| **Ingestão (`ingest.py`)** | Volume processado | **565 CSVs** (`386,7 MiB` brutos) → **4.962.960 registros** (5 regiões, 27 UFs) |
| **Ingestão (`ingest.py`)** | Tempo total e vazão | **245,73 s** (`4 min 06 s`) · **~20.197 linhas/s** (`0` erros) |
| **Memória (Python)** | Pico de RAM (`PeakWorkingSetSize`) | **121,20 MiB** constantes ao longo dos 565 arquivos |
| **Dimensão (`sincronizar_estacoes.py`)** | Coleta + UPSERT na API INMET | **752 estações** (`667` automáticas + `85` convencionais) em **1,42 s** |
| **Armazenamento (TimescaleDB)** | Hypertable `dados_estacoes` | **1,35 GiB** (`698,7 MiB` tabela + `679,3 MiB` índices) em **53 chunks** |
| **Analytics (`EXPLAIN ANALYZE`)** | Agregações temporais e por UF (`4,96M` linhas) | **936 ms** (`time_bucket` mensal/região) · **758 ms** (precipitação/UF) |
| **Analytics (`EXPLAIN ANALYZE`)** | `INNER JOIN estacoes` por altitude (`4,96M` linhas) | **8,31 s** (`d.estacao = e.cod_estacao` + `COUNT(DISTINCT)`) |

**Estrutura do Projeto**
-----------------------
```
inmet-data-pipeline/
├── .github/
│   └── workflows/
│       └── ci.yml                 # Pipeline CI (ruff check + pytest) no GitHub Actions
├── analytics/
│   ├── EDA_INMET.ipynb            # Análise Exploratória (time_bucket + Matplotlib/Seaborn)
│   └── export_to_bigquery.py      # Stub arquitetural de integração com Google BigQuery
├── data/
│   ├── README.md                  # Documentação do dataset sintético de amostra
│   └── INMET_*.CSV                # 5 CSVs de amostra (1 por região/faixa de altitude, 640 linhas)
├── db-init/
│   └── 01-init-timescaledb.sql    # Extensão + hypertable dados_estacoes + ingestao_status + estacoes
├── docs/
│   └── images/                    # Gráficos exportados do EDA_INMET.ipynb (base completa 2024)
├── tests/
│   ├── README.md                  # Escopo e estratégia da suíte de testes
│   ├── conftest.py                # Fixtures compartilhadas (CSVs e DataFrames sintéticos)
│   ├── test_db.py                 # Testes unitários de conexão e COPY binário
│   ├── test_export_bigquery.py    # Smoke test do stub de exportação ao BigQuery
│   ├── test_ingest.py             # Testes unitários do orquestrador (chunks, batches, rollback)
│   ├── test_schema_contract.py    # Contrato de schema entre transform.py, db.py e DDL SQL
│   ├── test_sincronizar_estacoes.py # Testes unitários de coleta e UPSERT da dimensão estacoes
│   └── test_transform.py          # Testes de parsing, Decimal, UTC e CSVs de amostra
├── db.py                          # Conexão (.env) + helper de COPY FROM STDIN binário (psycopg3)
├── ingest.py                      # Orquestrador ETL: lista CSVs, pula já ingeridos, COPY atômico por arquivo
├── sincronizar_estacoes.py        # Coleta metadados na API pública do INMET e faz UPSERT em estacoes
├── transform.py                   # Extrai metadados do nome do arquivo + normaliza colunas + TIMESTAMPTZ
├── docker-compose.yml             # TimescaleDB (PostgreSQL 17) em container, porta 5433
├── pyproject.toml                 # Metadados do projeto, dependências opcionais e config do Ruff
├── pytest.ini                     # Configuração do pytest (pythonpath e testpaths)
├── requirements.txt               # Dependências Python para execução local e CI
├── .env.example                   # Template de variáveis de ambiente
└── LICENSE                        # Licença MIT
```

**Banco de Dados (TimescaleDB via Docker)**
------------------------------------------
O projeto usa **TimescaleDB** (extensão de PostgreSQL para séries temporais) rodando em container Docker. O `docker-compose.yml` sobe um PostgreSQL 17 com a extensão já compilada, expondo a porta `5433` (para não conflitar com um PostgreSQL nativo que já ocupe a `5432`).

1. Crie o `.env` a partir do exemplo e ajuste a senha se quiser:
   ```bash
   cp .env.example .env
   ```
2. Suba o container (aguardando o `healthcheck` concluir a inicialização):
   ```bash
   docker compose up -d --wait
   ```
3. O script em `db-init/01-init-timescaledb.sql` roda automaticamente no primeiro boot e cria:
   - a extensão `timescaledb`;
   - a tabela `dados_estacoes` (coluna `data_hora` como `TIMESTAMPTZ`, demais como `TEXT`/`NUMERIC`);
   - a **hypertable** particionada por `data_hora`;
   - índices compostos B-tree em `(estacao, data_hora DESC)`, `(cidade, data_hora DESC)`, `(estado, data_hora DESC)` e `(regiao, data_hora DESC)`;
   - a tabela de controle `ingestao_status` (retomada idempotente);
   - a tabela-dimensão `estacoes` (metadados das estações: código/nome/lat/long/uf/tipo).

Como a **hypertable** é particionada por `data_hora`, os lotes enviados via *COPY* binário caem direto no chunk correto — sem varrer a tabela —, enquanto os índices compostos nas colunas mais filtradas evitam *full table scans* em consultas analíticas e *JOINs*, preservando a performance mesmo na escala de milhões de registros.

Conexão a partir do código Python (fora do container):
```
postgresql+psycopg://postgres:***@localhost:5433/inmet
```

> Nota: o `docker-entrypoint-initdb.d` só executa no primeiro boot de um volume vazio.
> Para recriar o banco do zero: `docker compose down -v` seguido de `docker compose up -d --wait`.
> Para evoluir o schema sem perder dados, use `ALTER TABLE` (ou ferramenta de migrations como Alembic) — não edite o init esperando reaplicação.

**Modelo de Dados (TimescaleDB)**
-------------------------------
| Tabela | Descrição |
|--------|-----------|
| `dados_estacoes` | Hypertable particionada por `data_hora` (TIMESTAMPTZ). Colunas de dimensão: `regiao`, `estado`, `estacao`, `cidade` (TEXT). Medidas meteorológicas (NUMERIC): `precipitacao`, `pressao`, `pressao_max_ant`, `pressao_min_ant`, `radiacao`, `temp_ar`, `temp_orvalho`, `temp_max_ant`, `temp_min_ant`, `temp_orvalho_max_ant`, `temp_orvalho_min_ant`, `umidade_max_ant`, `umidade_min_ant`, `umidade_ar`, `vento_dir`, `vento_rajada`, `vento_vel`. |
| `ingestao_status` | Controle de ingestão: `arquivo` (TEXT PK), `total_linhas` (BIGINT), `processado_em` (TIMESTAMPTZ), `status` (TEXT). Permite reiniciar o pipeline só dos arquivos pendentes. |
| `estacoes` | **Dimensão** de estações (star schema): `cod_estacao` (TEXT PK = `CD_ESTACAO` oficial do INMET, chave de join com `dados_estacoes.estacao`), `nome` (`DC_NOME` da cidade/estação), `uf`, `latitude`, `longitude`, `altitude`, `tipo`, `situacao`. Populada por `sincronizar_estacoes.py`. |

**Dimensão de Estações (`estacoes`)**
-------------------------------------
Para habilitar mapas (latitude/longitude), análises de altitude e filtros por UF/tipo no Power BI/Metabase, o projeto traz uma **tabela-dimensão** `estacoes`, separada da tabela-fato `dados_estacoes`. O join é feito pelo **código oficial da estação**: `estacoes.cod_estacao` (= `CD_ESTACAO` do INMET) = `dados_estacoes.estacao`.

- Metadados vindos do **endpoint oficial do INMET** (sem autenticação):
  - `https://apitempo.inmet.gov.br/estacoes/M` (manuais/convencionais)
  - `https://apitempo.inmet.gov.br/estacoes/T` (automáticas)
- `sincronizar_estacoes.py` faz GET nos dois endpoints, converte os campos da API para o formato da tabela (`CD_ESTACAO`, `DC_NOME`, `SG_ESTADO`, `VL_LATITUDE`, `VL_LONGITUDE`, `VL_ALTITUDE`, `TP_ESTACAO`, `CD_SITUACAO`) e faz **UPSERT** em `estacoes.cod_estacao` (idempotente — roda quantas vezes quiser).
- **Múltiplas estações por cidade e precisão de join:** usar `cod_estacao` como chave primária permite que um mesmo município possua estações **automáticas e convencionais** simultaneamente na dimensão (ex.: Brasília com `A001` automática e `83377` convencional) sem sobrescrita e sem multiplicação de linhas (*fan-out*) no `JOIN`, além de eliminar falhas de cruzamento por acentuação, caixa ou sufixos no nome da cidade.

**Analytics**
-------------
A pasta `/analytics` concentra a camada analítica do projeto:
- `analytics/EDA_INMET.ipynb`: Notebook de Análise Exploratória de Dados (EDA) — conecta no TimescaleDB local via SQLAlchemy, explora as séries temporais com funções TimescaleDB como `time_bucket` e `JOIN`s com a dimensão `estacoes`, e gera visualizações com Matplotlib/Seaborn sobre os **4,96M de registros de 2024**:
- `analytics/export_to_bigquery.py`: módulo de integração arquitetural com suporte a modo `dry_run` para exportação ao Google BigQuery (veja a seção **Próximos Passos** abaixo).

<details open>
<summary>Visualizações geradas pelo notebook (base histórica 2024 — 565 estações)</summary>

| Temperatura Média Mensal por Região (`time_bucket`) | Precipitação Acumulada Média por Estado |
|---|---|
| ![Temperatura Média Mensal por Região](docs/images/01-temperatura-media-regiao.png) | ![Precipitação Acumulada Média por Estado](docs/images/02-precipitacao-acumulada-estado.png) |

**Gradiente Térmico por Faixa de Altitude (`JOIN dados_estacoes × estacoes`)**

![Temperatura Média do Ar por Faixa de Altitude](docs/images/03-temperatura-faixa-altitude.png)

</details>


**Como Rodar**
-------------
> **Onde cada parte roda:** Apenas o **banco de dados (TimescaleDB)** roda no Docker (`docker-compose.yml`, expondo a porta `5433`). Todo o restante do projeto — scripts ETL (`ingest.py`, `sincronizar_estacoes.py`), testes (`pytest`) e o notebook de análise (`analytics/EDA_INMET.ipynb`) — roda **localmente fora do container**, utilizando um ambiente virtual Python (`venv`) e conectando-se ao banco em `localhost:5433`.

### 1. Subir o banco (Docker)
```bash
cp .env.example .env
docker compose up -d --wait
```

### 2. Criar ambiente virtual (`venv`), instalar dependências e ingerir
```bash
python -m venv .venv
# Windows (PowerShell): .\.venv\Scripts\Activate.ps1
# Linux/macOS:          source .venv/bin/activate

pip install -r requirements.txt
python ingest.py      # lê os CSVs de PASTA_ENTRADA, pula os já ingeridos e insere em lotes via COPY binário
```
O `ingest.py` é **idempotente e retomável**: lê cada CSV em *chunks* e descarrega lotes de 50 mil linhas por vez via *COPY* binário — o dataset completo (4,9M+ registros) nunca fica inteiro na memória. Se falhar no meio, reinicia só dos arquivos pendentes (`ingestao_status`) e nada do que já foi commitado é corrompido.

### 2b. (Opcional) Popular a dimensão de estações
```bash
python sincronizar_estacoes.py   # puxa metadados do INMET -> tabela 'estacoes' (lat/long/uf/tipo)
```
Útil para mapas e filtros no Power BI/Metabase. Idempotente (UPSERT).

### 3. Análise Exploratória (EDA)
Abra o notebook de análise em `analytics/EDA_INMET.ipynb`:
```bash
jupyter notebook analytics/EDA_INMET.ipynb
```

### 4. Testes Automatizados e Lint
Execute o linter e a suíte de testes unitários e de contrato (sem necessidade de Docker):
```bash
ruff check .
pytest -v
```
Mais detalhes sobre o que cada arquivo testa e a estratégia da suíte em [tests/README.md](tests/README.md).

**Variáveis de Ambiente**
------------------------
| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `POSTGRES_USER` | `postgres` | Usuário do banco (TimescaleDB) |
| `POSTGRES_PASSWORD` | `postgres` | Senha do banco |
| `POSTGRES_DB` | `inmet` | Nome do banco |
| `POSTGRES_HOST` | `localhost` | Host do TimescaleDB |
| `POSTGRES_PORT` | `5433` | Porta do TimescaleDB |
| `PASTA_ENTRADA` | `./data` | Pasta com os CSVs do INMET (arquivos `*.CSV`) |
| `BATCH_SIZE` | `50000` | Linhas por lote no COPY binário |
| `CHUNK_SIZE` | `100000` | Linhas por chunk do `read_csv` |
| `LOG_LEVEL` | `INFO` | Nível dos logs estruturados (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5433/inmet` | URL de conexão usada pelo notebook de análise (SQLAlchemy + `psycopg`) |

> O `.env` **não** vai para o git (veja `.gitignore`). Use `.env.example` como template.

**Dependências (`requirements.txt` e `pyproject.toml`)**
--------------------------------------------------------
O projeto mantém dois arquivos de dependências com papéis complementares:
- `requirements.txt`: lista direta para instalação em um único comando (`pip install -r requirements.txt`) usada localmente e no CI, reunindo dependências de runtime do ETL, notebook (`jupyter`) e qualidade/testes (`pytest`, `ruff`).
- `pyproject.toml`: metadados do projeto (`PEP 621`), requisito de versão do Python (`>=3.11`), configuração do Ruff (`[tool.ruff]`) e separação de extras em `[project.optional-dependencies]` (`dev` e `bigquery`).

```
psycopg[binary]>=3.1
pandas>=2.0
seaborn>=0.13
matplotlib>=3.8
sqlalchemy>=2.0
jupyter>=1.0
python-dotenv>=1.0
requests>=2.31
pytest>=8.0
ruff>=0.8
# google-cloud-bigquery>=3.0  # opcional: apenas para analytics/export_to_bigquery.py
```

O pacote `google-cloud-bigquery` permanece opcional (comentado no `requirements.txt` e isolado no extra `bigquery` do `pyproject.toml`) para quem quiser estender o *stub* `analytics/export_to_bigquery.py`.

**Próximos Passos (Roadmap)**
-----------------------------
O projeto foi desenhado para rodar **100% localmente via Docker** sem exigir infraestrutura ou custos em nuvem. Como evoluções planejadas para um ambiente produtivo ou futuras versões, ficam mapeados os seguintes pontos:

- **Integração Cloud / Google BigQuery (`analytics/export_to_bigquery.py`):** o script atual funciona como um *stub* arquitetural documentando o contrato de exportação via `google-cloud-bigquery` (sem carga ativa em nuvem nesta versão para manter o projeto gratuito e auto-contido). Em um cenário cloud, a evolução natural inclui:
  - **Ingestão:** execução via *Cloud Functions* ou *Cloud Run* disparada por eventos (ex.: chegada de novos arquivos no Cloud Storage).
  - **Armazenamento:** exportação/carga do TimescaleDB ou GCS para o *BigQuery* como Data Warehouse analítico.
  - **Orquestração:** agendamento e retry com *Cloud Composer (Airflow)* ou *Cloud Scheduler*.
- **Testes de integração em container:** execução ponta a ponta contra um TimescaleDB real no CI validando `create_hypertable`, precisão `NUMERIC(x,y)` e consultas `time_bucket`.


**Licença**
----------
Este projeto está sob a licença MIT. Para mais detalhes, consulte o arquivo [LICENSE](LICENSE).  