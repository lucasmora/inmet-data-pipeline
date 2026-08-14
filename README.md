<div align="center">

# 🌦️ ETL Análise INMET

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![TimescaleDB](https://img.shields.io/badge/TimescaleDB-PostgreSQL--17-336791?style=flat-square&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=flat-square&logo=docker&logoColor=white)
![Licença](https://img.shields.io/badge/Licen%C3%A7a-MIT-22c55e?style=flat-square)
![Versão](https://img.shields.io/badge/Vers%C3%A3o-1.0.0-blue?style=flat-square)

</div>

**Descrição**
-------------
Pipeline **ETL** para dados meteorológicos do **INMET** (Instituto Nacional de Meteorologia). Segue um desenho de *Big Data*: lê arquivo a arquivo, em *chunks*, e alimenta o **TimescaleDB** em lotes via protocolo *COPY* binário — **sem** concatenar tudo em um CSV gigante.

**Objetivo**
-----------
Ingerir de forma incremental, retomável e idempotente milhões de linhas de séries temporais meteorológicas (4,9M+ registros) em um banco particionado por tempo, pronto para *analytics* em segundos, com o mínimo de memória e sem dependência de instalação nativa de banco no Windows.

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
├── ingest.py                 # Orquestrador ETL: lista CSVs, pula já ingeridos, insere em lotes via COPY binário
├── transform.py             # Extrai metadados do nome do arquivo + normaliza colunas + data_hora TIMESTAMPTZ
├── db.py                    # Conexão (.env) + helper de COPY FROM STDIN binário (psycopg3)
├── consultas.py             # 6 consultas analíticas (time_bucket, janela móvel, etc.)
├── requirements.txt         # Dependências Python
├── docker-compose.yml       # TimescaleDB (PostgreSQL 17) em container, porta 5433
├── .env.example             # Template de variáveis de ambiente
├── init/
│   └── 01-init-timescaledb.sql  # Extensão + hypertable dados_estacoes + tabela ingestao_status
└── dados_estacoes.csv       # (opcional) CSV de entrada para ingestão
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
O projeto usa **TimescaleDB** (extensão de PostgreSQL para séries temporais) rodando em container, evitando instalação nativa no Windows. O `docker-compose.yml` sobe um PostgreSQL 17 com a extensão já compilada, expondo a porta `5433` (para não conflitar com um PostgreSQL nativo que já ocupe a `5432`).

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
   - a **hypertable** particionada por `data_hora` (ganho de performance em séries temporais);
   - a tabela de controle `ingestao_status` (retomada idempotente).

Conexão a partir do código Python (fora do container):
```
postgresql://postgres:***@localhost:5433/inmet
```

> Nota: o `docker-entrypoint-initdb.d` só executa no primeiro boot de um volume vazio.
> Para recriar o banco do zero: `docker compose down -v && docker compose up -d`.
> Para evoluir o schema sem perdar dados, use `ALTER TABLE` (ou ferramenta de migrations como Alembic) — não edite o init esperando reaplicação.

**Modelo de Dados (TimescaleDB)**
-------------------------------
| Tabela | Descrição |
|--------|-----------|
| `dados_estacoes` | Hypertable particionada por `data_hora` (TIMESTAMPTZ). Colunas de dimensão: `regiao`, `estado`, `estacao`, `cidade` (TEXT). Medidas meteorológicas (NUMERIC): `precipitacao`, `pressao`, `pressao_max_ant`, `pressao_min_ant`, `radiacao`, `temp_ar`, `temp_orvalho`, `temp_max_ant`, `temp_min_ant`, `temp_orvalho_max_ant`, `temp_orvalho_min_ant`, `umidade_max_ant`, `umidade_min_ant`, `umidade_ar`, `vento_dir`, `vento_rajada`, `vento_vel`. |
| `ingestao_status` | Controle de ingestão: `arquivo` (TEXT PK), `total_linhas` (BIGINT), `processado_em` (TIMESTAMPTZ), `status` (TEXT). Permite reiniciar o pipeline só dos arquivos pendentes. |

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
python ingest.py      # lista os CSVs, pula os já ingeridos e insere em lotes via COPY binário
```
O `ingest.py` é **idempotente e retomável**: se falhar no meio, reinicia só dos pendentes (`ingestao_status`).

### 3. Consultar (analytics temporais)
```bash
python consultas.py   # demonstra recursos do TimescaleDB/PostgreSQL
```

**Consultas Analíticas** (`consultas.py`)
-----------------------------------------
| Função | Recurso demonstrado |
|--------|---------------------|
| `total_precipitacao_por_mes` | `time_bucket('1 month')` + `sum` — volume mensal de chuva |
| `temperatura_maxima_por_estado` | `max(temp_ar)` agrupado por estado — detecção de extremos |
| `janela_movel_umidade` | `avg() OVER (... RANGE BETWEEN INTERVAL '23 hours' PRECEDING)` — média móvel de 24h por estação |
| `contagens_por_regiao` | `count(*)` por região — distribuição do dataset (Volume/Variety) |
| `ultimas_medicoes(n)` | `ORDER BY data_hora DESC LIMIT n` — medições mais recentes |

**Variáveis de Ambiente**
------------------------
| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `POSTGRES_USER` | `postgres` | Usuário do banco (TimescaleDB) |
| `POSTGRES_PASSWORD` | `postgres` | Senha do banco |
| `POSTGRES_DB` | `inmet` | Nome do banco |

> O `.env` **não** vai para o git (veja `.gitignore`). Use `.env.example` como template.

**Dependências Principais** (`requirements.txt`)
------------------------------------------------
```
psycopg[binary]>=3.1
pandas>=2.0
python-dotenv>=1.0
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
- **1.0.0** – Versão inicial: pipeline ETL incremental (ingestão idempotente via COPY binário), TimescaleDB em Docker (hypertable + ingestao_status), transform na borda e 5 consultas analíticas de série temporal.
