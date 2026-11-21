-- Roda automaticamente no PRIMEIRO boot do container (docker-entrypoint-initdb.d)
-- Ordem importa: extensao -> tabela -> hypertable

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS dados_estacoes (
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

-- 3) Transforma em hypertable (particiona por data_hora)
SELECT create_hypertable('dados_estacoes', 'data_hora', if_not_exists => TRUE);

-- Indices para filtros analiticos e JOIN com a dimensao 'estacoes'
CREATE INDEX IF NOT EXISTS idx_dados_estacoes_estacao_data
    ON dados_estacoes (estacao, data_hora DESC);
CREATE INDEX IF NOT EXISTS idx_dados_estacoes_cidade_data
    ON dados_estacoes (cidade, data_hora DESC);
CREATE INDEX IF NOT EXISTS idx_dados_estacoes_estado_data
    ON dados_estacoes (estado, data_hora DESC);
CREATE INDEX IF NOT EXISTS idx_dados_estacoes_regiao_data
    ON dados_estacoes (regiao, data_hora DESC);

-- 4) Tabela de controle de ingestao (retomada idempotente)
--    Permite reiniciar o pipeline apenas dos arquivos pendentes.
CREATE TABLE IF NOT EXISTS ingestao_status (
    arquivo        TEXT PRIMARY KEY,
    total_linhas   BIGINT,
    processado_em  TIMESTAMPTZ DEFAULT now(),
    status         TEXT
);

-- 5) Tabela-dimensao de estacoes (star schema) alimentada por sincronizar_estacoes.py.
--    'cod_estacao' = CD_ESTACAO oficial do INMET = PK e chave de join com dados_estacoes.estacao.
--    Permite multiplas estacoes (Automatica e Convencional) na mesma cidade sem colisao.
--    Nao eh hypertable: é dimensao pequena (~600 linhas), nao serie temporal.
CREATE TABLE IF NOT EXISTS estacoes (
    cod_estacao TEXT PRIMARY KEY,    -- codigo oficial INMET (CD_ESTACAO); join com dados_estacoes.estacao
    nome        TEXT,                -- DC_NOME (nome da cidade/estacao no INMET)
    uf          TEXT,                -- SG_ESTADO
    latitude    DOUBLE PRECISION,    -- VL_LATITUDE
    longitude   DOUBLE PRECISION,    -- VL_LONGITUDE
    altitude    DOUBLE PRECISION,    -- VL_ALTITUDE
    tipo        TEXT,                -- TP_ESTACAO (Automatica/Convencional)
    situacao    TEXT                 -- CD_SITUACAO (Operante/Pane/...)
);
