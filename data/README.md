# Dataset de Amostra (INMET)

Esta pasta contém um **dataset sintético de amostra** no formato oficial dos CSVs do **INMET** (`latin_1`, separador `;`, 8 linhas de cabeçalho de metadados), pensado para quem clonar o repositório conseguir executar o pipeline completo (`ingest.py` + `sincronizar_estacoes.py` + `analytics/EDA_INMET.ipynb`) imediatamente, sem precisar baixar dezenas de megabytes antes do primeiro teste.

## O que está incluído

São **5 arquivos** (128 linhas cada, **640 registros no total**), cobrindo **janeiro a abril de 2024** (8 dias por mês × 4 horários sinóticos: `0000`, `0600`, `1200` e `1800 UTC`), com 1 estação automática real por região do Brasil e pelas 5 faixas de altitude analisadas no notebook:

| Arquivo | Região | UF | Estação (`estacoes.cod_estacao`) | Cidade (`estacoes.nome`) | Altitude aproximada |
|---------|--------|----|---------|--------------------------|---------------------|
| `INMET_N_AM_A101_MANAUS_01-01-2024_A_30-04-2024.CSV` | `N` | `AM` | `A101` | `MANAUS` | ~61 m (`< 200 m`) |
| `INMET_NE_PE_A329_CABROBO_01-01-2024_A_30-04-2024.CSV` | `NE` | `PE` | `A329` | `CABROBO` | ~343 m (`200–500 m`) |
| `INMET_S_RS_A839_PASSO FUNDO_01-01-2024_A_30-04-2024.CSV` | `S` | `RS` | `A839` | `PASSO FUNDO` | ~681 m (`500–800 m`) |
| `INMET_CO_DF_A001_BRASILIA_01-01-2024_A_30-04-2024.CSV` | `CO` | `DF` | `A001` | `BRASILIA` | ~1161 m (`800–1200 m`) |
| `INMET_SE_MG_A509_MONTE VERDE_01-01-2024_A_30-04-2024.CSV` | `SE` | `MG` | `A509` | `MONTE VERDE` | ~1545 m (`≥ 1200 m`) |

## Como usar

1. Suba o TimescaleDB (`docker compose up -d --wait`).
2. Execute `python ingest.py` para ingerir os 5 CSVs desta pasta na hypertable `dados_estacoes`.
3. Execute `python sincronizar_estacoes.py` para popular a dimensão `estacoes` (necessária para o gráfico por faixa de altitude).
4. Abra e execute `analytics/EDA_INMET.ipynb`.

> **Quer usar dados completos do INMET?** Basta substituir ou adicionar novos `*.CSV` oficiais nesta pasta. Se quiser limpar os dados de amostra do banco antes de ingerir o histórico completo, recrie o volume com `docker compose down -v` seguido de `docker compose up -d --wait`.
