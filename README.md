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
Pipeline **ETL** para dados meteorológicos do **INMET** (Instituto Nacional de Meteorologia) com Analytics simples. O pipeline lê arquivo a arquivo, em *chunks*, e alimenta o **TimescaleDB** em lotes via protocolo *COPY* binário.

**Objetivo**
-----------
Ingerir de forma incremental, retomável e idempotente milhões de linhas de séries temporais meteorológicas (4,9M+ registros) em um banco particionado por tempo, pronto para *analytics*, com o mínimo de memória e sem dependência de instalação nativa de banco no Windows.

**Origem dos Dados**
-------------------
Os dados brutos são baixados do **portal oficial do INMET** (Instituto Nacional de Meteorologia). O portal fornece um arquivo **compactado em ZIP** por estação, contendo **um CSV por dia** para todo o ano. Os arquivos seguem o padrão `INMET_<REGIÃO>_<UF>_<CÓDIGO>_<CIDADE>_<datas>.CSV`, com ~8 linhas de cabeçalho antes dos dados (descartadas via `skiprows=8`), separador `;`, encoding `latin-1` e a última coluna vazia — detalhes que o `transform.py` normaliza.

**Stack Tecnológico**
--------------------
| Camada | Tecnologia |
|--------|------------|
| **Linguagem** | Python ≥ 3.11 |
| **ETL/Transform** | Pandas (`read_csv` em *chunks*) + `re` (parsing de metadados) |
| **Banco** | TimescaleDB (extensão de PostgreSQL 17 para séries temporais) |
| **Driver** | `psycopg[binary]` 3.x — *COPY* binário de alta performance |
| **Container** | Docker + docker compose (PostgreSQL 17 com TimescaleDB pré-compilado) |
| **Config** | `python-dotenv` (variáveis de ambiente em `.env`) |

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
├── init/
│   └── 01-init-timescaledb.sql  # Extensão + hypertable dados_estacoes + ingestao_status + estacoes (dimensão)
├── analytics/
│   ├── EDA_INMET.ipynb          # Análise Exploratória de Dados (SQL + Matplotlib)
│   └── export_to_bigquery.py    # Stub de integração com Google BigQuery
```

**Arquitetura Big Data (5 Vs)**
-----------------------------
- **Volume** — Ingestão em lotes de 50 mil linhas via *COPY* binário; nunca carrega o dataset inteiro (4,9M linhas) na memória.
- **Velocity** — *COPY* binário do psycopg3 + *hypertable* particionada por `data_hora` (inserts caem no chunk certo, sem varrer a tabela).
- **Variety** — Parsing por arquivo na borda: metadados do nome do arquivo + normalização de colunas INMET para o formato canônico da tabela.
- **Veracity** — Retomada por arquivo (`ingestao_status`) + tipos fortes (`TIMESTAMPTZ`, `NUMERIC`); falhas não corrompem o que já foi ingerido.
- **Value** — Dado consultável em segundos, particionado, pronto para *analytics* de série temporal.

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
3. O script em `init/01-init-timescaledb.sql` roda automaticamente no primeiro boot e cria:
   - a extensão `timescaledb`;
   - a tabela `dados_estacoes` (coluna `data_hora` como `TIMESTAMPTZ`, demais como `TEXT`/`NUMERIC`);
   - a **hypertable** particionada por `data_hora`;
   - a tabela de controle `ingestao_status` (retomada idempotente);
   - a tabela-dimensão `estacoes` (metadados das estações: lat/long/uf/tipo).

Conexão a partir do código Python (fora do container):
```
postgresql://postgres:***@localhost:5433/inmet
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
O projeto agora inclui uma pasta `/analytics` com ferramentas para análise e integração com nuvem:
- `analytics/consultas.py`: módulo de consultas analíticas (CLI + SQL em `analytics/sql/`), executável via `python -m analytics.consultas`.
- `analytics/EDA_INMET.ipynb`: Notebook para Análise Exploratória de Dados (EDA) usando queries SQL e visualização com Matplotlib.
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
### 1. Subir o banco (Docker)
```bash
cp .env.example .env
docker compose up -d
```

### 2. Instalar dependências e ingerir
```bash
pip install -r requirements.txt
python ingest.py      # lê os CSVs de PASTA_ENTRADA, pula os já ingeridos e insere em lotes via COPY binário
```
O `ingest.py` é **idempotente e retomável**: se falhar no meio, reinicia só dos pendentes (`ingestao_status`).

### 2b. (Opcional) Popular a dimensão de estações
```bash
python fetch_estacoes.py   # puxa metadados do INMET -> tabela 'estacoes' (lat/long/uf/tipo)
```
Útil para mapas e filtros no Power BI/Metabase. Idempotente (UPSERT).

### 3. Consultar (analytics temporais)
```bash
python -m analytics.consultas   # roda as consultas analíticas do módulo
```

**Consultas Analíticas** (`analytics/consultas.py`)
------------------------------------------------------
As consultas vivem em `analytics/consultas.py` e leem o SQL de `analytics/sql/` — a **fonte única** do SQL, reutilizável diretamente no Metabase/BI.

| Função | Recurso demonstrado |
|--------|---------------------|
| `precipitacao_media_por_regiao` | `avg(precipitacao)` por região — média de precipitação (somente não-nulas) |

Uso da CLI:
```bash
python -m analytics.consultas                 # roda todas as consultas
python -m analytics.consultas --list          # lista as consultas disponíveis
python -m analytics.consultas <nome>          # roda uma consulta específica
```

**Variáveis de Ambiente**
------------------------
| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `POSTGRES_USER` | `postgres` | Usuário do banco (TimescaleDB) |
| `POSTGRES_PASSWORD` | `postgres` | Senha do banco |
| `POSTGRES_DB` | `inmet` | Nome do banco |
| `POSTGRES_HOST` | `localhost` | Host do TimescaleDB |
| `POSTGRES_PORT` | `5433` | Porta do TimescaleDB |
| `PASTA_ENTRADA` | `C:\Users\moral\Downloads\meteorologia` | Pasta com os CSVs do INMET (arquivos `*.CSV`) |
| `BATCH_SIZE` | `50000` | Linhas por lote no COPY binário |
| `CHUNK_SIZE` | `100000` | Linhas por chunk do `read_csv` |

> O `.env` **não** vai para o git (veja `.gitignore`). Use `.env.example` como template.

**Dependências Principais** (`requirements.txt`)
------------------------------------------------
```
psycopg[binary]>=3.1
pandas>=2.0
python-dotenv>=1.0
requests>=2.31
```

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
