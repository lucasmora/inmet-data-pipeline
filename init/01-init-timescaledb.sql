-- Roda automaticamente no PRIMEIRO boot do container (docker-entrypoint-initdb.d)
-- Ordem importa: extensao -> tabela -> hypertable

-- 1) Ativa a extensao TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 2) Recria a tabela do projeto (mesma estrutura de criar_tabela_postgre.sql)
--    Usa TIMESTAMPTZ (dados UTC) e TEXT (recomendacao TimescaleDB) conforme
--    sugerido nos warnings do init.
DROP TABLE IF EXISTS dados_estacoes;

CREATE TABLE dados_estacoes (
    data_hora           TIMESTAMPTZ NOT NULL,
    regiao              TEXT,
    estado              TEXT,
    estacao             TEXT,
    cidade              TEXT,

    precipitacao        NUMERIC(6,2),
    pressao             NUMERIC(6,1),
    pressao_max_ant     NUMERIC(6,1),
    pressao_min_ant     NUMERIC(6,1),

    radiacao            NUMERIC(8,2),

    temp_ar             NUMERIC(4,1),
    temp_orvalho        NUMERIC(4,1),
    temp_max_ant        NUMERIC(4,1),
    temp_min_ant        NUMERIC(4,1),
    temp_orvalho_max_ant NUMERIC(4,1),
    temp_orvalho_min_ant NUMERIC(4,1),

    umidade_max_ant     NUMERIC(4,1),
    umidade_min_ant     NUMERIC(4,1),
    umidade_ar          NUMERIC(4,1),

    vento_dir           NUMERIC(5,1),
    vento_rajada        NUMERIC(4,1),
    vento_vel           NUMERIC(4,1)
);

-- 3) Transforma em hypertable (particiona por data_hora = ganho de performance)
--    Isso eh o "pulo do gato" do TimescaleDB para series temporais.
SELECT create_hypertable('dados_estacoes', 'data_hora', if_not_exists => TRUE);

-- 4) Tabela de controle de ingestao (retomada idempotente / Big Data)
--    Permite reiniciar o pipeline apenas dos arquivos pendentes.
CREATE TABLE IF NOT EXISTS ingestao_status (
    arquivo        TEXT PRIMARY KEY,
    total_linhas   BIGINT,
    processado_em  TIMESTAMPTZ DEFAULT now(),
    status         TEXT
);
