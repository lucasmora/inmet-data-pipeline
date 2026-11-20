<div align="center">

# 🌦️ ETL Análise INMET

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![TimescaleDB](https://img.shields.io/badge/TimescaleDB-PostgreSQL--17-336791?style=flat-square&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=flat-square&logo=docker&logoColor=white)
![Licença](https://img.shields.io/badge/Licen%C3%A7a-MIT-22c55e?style=flat-square)
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
Os dados brutos são baixados do **portal oficial do INMET** (Instituto Nacional de Meteorologia). O portal fornece um arquivo **compactado em ZIP** por estação, contendo **um CSV por dia** para todo o ano. Os arquivos seguem o padrão `INMET_<REGIÃO>_<UF>_<CÓDIGO>_<CIDADE>_<datas>.CSV`, com ~8 linhas de cabeçalho antes dos dados (descartadas via `skiprows=8`), separador `;`, encoding `latin-1` e a última coluna vazia. O parsing é feito **na borda, arquivo a arquivo**: o `transform.py` extrai os metadados (região, UF, código, cidade) do próprio nome do arquivo e normaliza as colunas do formato INMET para o formato canônico da tabela.

**Stack Tecnológico**
--------------------
| Camada | Tecnologia |
|--------|------------|
| **Linguagem** | Python ≥ 3.11 |
| **ETL/Transform** | Pandas (`read_csv` em *chunks*) + `re` (parsing de metadados) |
| **Banco** | TimescaleDB (extensão de PostgreSQL 17 para séries temporais) |
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
    E["API Pública INMET (/estacoes/M e /T)"] --> F["fetch_estacoes.py (UPSERT idempotente)"]
    F --> G[("Dimensão estacoes (Star Schema)")]
    D --> H["EDA_INMET.ipynb / BI (time_bucket + JOIN)"]
    G --> H
```

**Estrutura do Projeto**
-----------------------
```
inmet-data-pipeline/
├── ingest.py                # Orquestrador ETL: lista CSVs, pula já ingeridos, insere em lotes via COPY binário
├── transform.py             # Extrai metadados do nome do arquivo + normaliza colunas + data_hora TIMESTAMPTZ
├── db.py                    # Conexão (.env) + helper de COPY FROM STDIN binário (psycopg3)
├── requirements.txt         # Dependências Python
├── docker-compose.yml       # TimescaleDB (PostgreSQL 17) em container, porta 5433
├── .env.example             # Template de variáveis de ambiente
├── LICENSE                  # Licença MIT
├── db-init/
│   └── 01-init-timescaledb.sql  # Extensão + hypertable dados_estacoes + ingestao_status + estacoes (dimensão)
├── analytics/
│   ├── EDA_INMET.ipynb          # Análise Exploratória (time_bucket + Matplotlib/Seaborn)
│   └── export_to_bigquery.py    # Stub de integração com Google BigQuery
```

**Banco de Dados (TimescaleDB via Docker)**
------------------------------------------
O projeto usa **TimescaleDB** (extensão de PostgreSQL para séries temporais) rodando em container Docker. O `docker-compose.yml` sobe um PostgreSQL 17 com a extensão já compilada, expondo a porta `5433` (para não conflitar com um PostgreSQL nativo que já ocupe a `5432`).

1. Crie o `.env` a partir do exemplo e ajuste a senha se quiser:
   ```bash
   cp .env.example .env
   ```
2. Suba o container:
   ```bash
   docker compose up -d
   ```
3. O script em `db-init/01-init-timescaledb.sql` roda automaticamente no primeiro boot e cria:
   - a extensão `timescaledb`;
   - a tabela `dados_estacoes` (coluna `data_hora` como `TIMESTAMPTZ`, demais como `TEXT`/`NUMERIC`);
   - a **hypertable** particionada por `data_hora`;
   - índices compostos B-tree em `(cidade, data_hora DESC)`, `(estado, data_hora DESC)` e `(regiao, data_hora DESC)`;
   - a tabela de controle `ingestao_status` (retomada idempotente);
   - a tabela-dimensão `estacoes` (metadados das estações: lat/long/uf/tipo).

Como a **hypertable** é particionada por `data_hora`, os lotes enviados via *COPY* binário caem direto no chunk correto — sem varrer a tabela —, enquanto os índices compostos nas colunas mais filtradas evitam *full table scans* em consultas analíticas e *JOINs*, preservando a performance mesmo na escala de milhões de registros.

Conexão a partir do código Python (fora do container):
```
postgresql+psycopg://postgres:***@localhost:5433/inmet
```

> Nota: o `docker-entrypoint-initdb.d` só executa no primeiro boot de um volume vazio.
> Para recriar o banco do zero: `docker compose down -v && docker compose up -d`.
> Para evoluir o schema sem perder dados, use `ALTER TABLE` (ou ferramenta de migrations como Alembic) — não edite o init esperando reaplicação.

**Modelo de Dados (TimescaleDB)**
-------------------------------
| Tabela | Descrição |
|--------|-----------|
| `dados_estacoes` | Hypertable particionada por `data_hora` (TIMESTAMPTZ). Colunas de dimensão: `regiao`, `estado`, `estacao`, `cidade` (TEXT). Medidas meteorológicas (NUMERIC): `precipitacao`, `pressao`, `pressao_max_ant`, `pressao_min_ant`, `radiacao`, `temp_ar`, `temp_orvalho`, `temp_max_ant`, `temp_min_ant`, `temp_orvalho_max_ant`, `temp_orvalho_min_ant`, `umidade_max_ant`, `umidade_min_ant`, `umidade_ar`, `vento_dir`, `vento_rajada`, `vento_vel`. |
| `ingestao_status` | Controle de ingestão: `arquivo` (TEXT PK), `total_linhas` (BIGINT), `processado_em` (TIMESTAMPTZ), `status` (TEXT). Permite reiniciar o pipeline só dos arquivos pendentes. |
| `estacoes` | **Dimensão** de estações (star schema): `nome` (TEXT PK = `DC_NOME` do INMET, chave de join com `dados_estacoes.cidade`), `cod_estacao` (código oficial INMET), `uf`, `latitude`, `longitude`, `altitude`, `tipo`, `situacao`. Populada por `fetch_estacoes.py`. |

**Analytics & Cloud Ready**
---------------------------
A pasta `/analytics` concentra a análise e a integração com nuvem:
- `analytics/EDA_INMET.ipynb`: Notebook de Análise Exploratória de Dados (EDA) — conecta no TimescaleDB via SQLAlchemy, explora as séries temporais com funções TimescaleDB como `time_bucket` e JOINs com a dimensão `estacoes`, e visualiza os resultados com Matplotlib/Seaborn (temperatura média mensal por região, precipitação acumulada por estado e temperatura média por faixa de altitude).
- `analytics/export_to_bigquery.py`: *Stub* de integração com Google BigQuery, demonstrando conhecimento em arquitetura Cloud (GCP) e preparação de dados para Data Warehouse.

**Arquitetura Cloud Recomendada**
---------------------------------
Embora executado localmente via Docker, este pipeline é *Cloud-Native*:
- **Ingestão:** Substituição de execução local por *Cloud Functions* ou *Cloud Run* disparado por eventos.
- **Armazenamento:** Migração do TimescaleDB (local) para o *BigQuery* (Data Warehouse Serverless), ideal para escala petabyte.
- **Orquestração:** Uso de ferramentas como *Cloud Composer (Airflow)* ou *Cloud Scheduler* para automação de tarefas ETL.

**Dimensão de Estações (`estacoes`)**
-------------------------------------
Para habilitar mapas (latitude/longitude) e filtros por UF/tipo no Power BI/Metabase, o projeto traz uma **tabela-dimensão** `estacoes`, separada da tabela-fato `dados_estacoes`. O join é por **nome da cidade**: `estacoes.nome` (= `DC_NOME` do INMET) = `dados_estacoes.cidade`.

- Metadados vindos do **endpoint oficial do INMET** (sem autenticação):
  - `https://apitempo.inmet.gov.br/estacoes/M` (manuais/convencionais)
  - `https://apitempo.inmet.gov.br/estacoes/T` (automáticas)
- `fetch_estacoes.py` faz GET nos dois endpoints, normaliza os campos (`CD_ESTACAO`, `SG_ESTADO`, `VL_LATITUDE`, `VL_LONGITUDE`, `VL_ALTITUDE`, `TP_ESTACAO`, `CD_SITUACAO`) e faz **UPSERT** em `estacoes.nome` (idempotente — roda quantas vezes quiser).
- **Cobertura:** das ~563 cidades em `dados_estacoes`, ~546 casam com `estacoes.nome` (~96,6%). As ~17 restantes divergem por acento/maiúsculas/sufixos no nome (ex.: `BELO HORIZONTE (PAMPULHA)`, `Paty do Alferes - Avelar`) e podem ser ajustadas com um join tolerante no futuro.
- A tabela **não** é hypertable: é dimensão pequena (~700 linhas), não série temporal.

**Como Rodar**
-------------
> **Onde cada parte roda:** Apenas o **banco de dados (TimescaleDB)** roda no Docker (`docker-compose.yml`, expondo a porta `5433`). Todo o restante do projeto — scripts ETL (`ingest.py`, `fetch_estacoes.py`), testes (`pytest`) e o notebook de análise (`analytics/EDA_INMET.ipynb`) — roda **localmente fora do container**, utilizando um ambiente virtual Python (`venv`) e conectando-se ao banco em `localhost:5433`.

### 1. Subir o banco (Docker)
```bash
cp .env.example .env
docker compose up -d
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
python fetch_estacoes.py   # puxa metadados do INMET -> tabela 'estacoes' (lat/long/uf/tipo)
```
Útil para mapas e filtros no Power BI/Metabase. Idempotente (UPSERT).

### 3. Análise Exploratória (EDA)
Abra o notebook de análise em `analytics/EDA_INMET.ipynb`:
```bash
jupyter notebook analytics/EDA_INMET.ipynb
```

### 4. Testes Automatizados
Execute a suíte de testes unitários e de contrato (sem necessidade de Docker):
```bash
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
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5433/inmet` | URL de conexão usada pelo notebook de análise (SQLAlchemy + `psycopg`) |

> O `.env` **não** vai para o git (veja `.gitignore`). Use `.env.example` como template.

**Dependências Principais** (`requirements.txt`)
------------------------------------------------
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
# google-cloud-bigquery>=3.0  # opcional: apenas para analytics/export_to_bigquery.py
```

Todas as dependências necessárias para o ETL e para o notebook de análise (`analytics/EDA_INMET.ipynb`) já estão incluídas no `requirements.txt`. O pacote `google-cloud-bigquery` permanece opcional (comentado) para quem quiser estender o *stub* `analytics/export_to_bigquery.py`.

**Licença**
----------
MIT. Sinta-se livre para usar, modificar e distribuir, contanto que essa licença seja mantida.

**Como este projeto foi desenvolvido**
--------------------------------------
- Definição dos requisitos e funcionalidades por mim.
- Desenvolvimento assistido por agentes e ferramentas de IA.
- Revisão e adaptação manual de todo o código gerado.
- Testes e validação das funcionalidades.
- Documentação escrita e mantida por mim.

**Versões/Alterações**
---------------------
- **1.0.0** – Versão inicial: pipeline ETL incremental (ingestão idempotente via COPY binário), TimescaleDB em Docker (hypertable + ingestao_status), transform na borda e 4 consultas analíticas de série temporal.
- **1.1.0** – Tabela-dimensão `estacoes` (star schema) alimentada por `fetch_estacoes.py` a partir do endpoint oficial do INMET; habilita mapas (lat/long) e filtros por UF/tipo no Power BI/Metabase.
