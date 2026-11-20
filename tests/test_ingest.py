"""Testes unitários para o orquestrador de ingestão (ingest.py)."""
import logging
from unittest.mock import MagicMock

import ingest
from tests.conftest import default_inmet_row


def _criar_fake_conn(ja_ingeridos=None):
    """Cria conexão e cursor falsos mantendo estado simples de ingestao_status."""
    ingeridos = set(ja_ingeridos or [])
    pendentes_marcacao = []
    marcados_commitados = []

    cur = MagicMock()
    last_row = {"value": None}

    def execute(sql, params=None):
        if "SELECT 1 FROM ingestao_status" in sql:
            last_row["value"] = (1,) if params[0] in ingeridos else None
        elif "INSERT INTO ingestao_status" in sql:
            pendentes_marcacao.append((params[0], params[1]))

    def fetchone():
        return last_row["value"]

    cur.execute.side_effect = execute
    cur.fetchone.side_effect = fetchone

    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cur

    def commit():
        marcados_commitados.extend(pendentes_marcacao)
        ingeridos.update(nome for nome, _ in pendentes_marcacao)
        pendentes_marcacao.clear()

    def rollback():
        pendentes_marcacao.clear()

    conn.commit.side_effect = commit
    conn.rollback.side_effect = rollback
    conn.marcados_commitados = marcados_commitados
    return conn, cur


def test_ja_ingerido_retorna_bool_conforme_fetchone():
    cur = MagicMock()
    cur.fetchone.side_effect = [(1,), None]

    assert ingest.ja_ingerido(cur, "arq1.CSV") is True
    assert ingest.ja_ingerido(cur, "arq2.CSV") is False
    assert cur.execute.call_count == 2
    assert cur.execute.call_args_list[0].args[1] == ("arq1.CSV",)


def test_marcar_executa_upsert_em_ingestao_status():
    cur = MagicMock()

    ingest.marcar(cur, "INMET_CO_DF_A001_BRASILIA_2023.CSV", 1234)

    sql, params = cur.execute.call_args.args
    assert "INSERT INTO ingestao_status" in sql
    assert "ON CONFLICT (arquivo) DO UPDATE" in sql
    assert params == ("INMET_CO_DF_A001_BRASILIA_2023.CSV", 1234)


def test_ingerir_arquivo_respeita_chunksize_e_batchsize(
    make_inmet_csv, meta_brasilia, monkeypatch
):
    rows = [
        default_inmet_row(data="2023/01/01", hora=f"{h:02d}00 UTC")
        for h in range(5)
    ]
    csv_path = make_inmet_csv(
        "INMET_CO_DF_A001_BRASILIA_01-01-2023_A_31-12-2023.CSV", rows=rows
    )

    lotes_enviados = []
    monkeypatch.setattr(ingest, "CHUNK_SIZE", 2)
    monkeypatch.setattr(ingest, "BATCH_SIZE", 3)
    monkeypatch.setattr(
        ingest, "copy_rows", lambda cur, lote: lotes_enviados.append(list(lote))
    )

    cur = MagicMock()
    total = ingest.ingerir_arquivo(cur, str(csv_path), meta_brasilia)

    assert total == 5
    assert [len(lote) for lote in lotes_enviados] == [3, 2]
    assert len(lotes_enviados[0][0]) == 22


def test_ingerir_arquivo_multiplo_exato_de_batchsize_nao_envia_lote_vazio(
    make_inmet_csv, meta_brasilia, monkeypatch
):
    rows = [
        default_inmet_row(data="2023/01/01", hora=f"{h:02d}00 UTC")
        for h in range(4)
    ]
    csv_path = make_inmet_csv(
        "INMET_CO_DF_A001_BRASILIA_01-01-2023_A_31-12-2023.CSV", rows=rows
    )

    lotes_enviados = []
    monkeypatch.setattr(ingest, "CHUNK_SIZE", 4)
    monkeypatch.setattr(ingest, "BATCH_SIZE", 2)
    monkeypatch.setattr(
        ingest, "copy_rows", lambda cur, lote: lotes_enviados.append(list(lote))
    )

    total = ingest.ingerir_arquivo(MagicMock(), str(csv_path), meta_brasilia)

    assert total == 4
    assert [len(lote) for lote in lotes_enviados] == [2, 2]


def test_ingerir_arquivo_vazio_retorna_zero_sem_chamar_copy(
    make_inmet_csv, meta_brasilia, monkeypatch
):
    csv_path = make_inmet_csv(
        "INMET_CO_DF_A001_BRASILIA_01-01-2023_A_31-12-2023.CSV", rows=[]
    )
    copy_mock = MagicMock()
    monkeypatch.setattr(ingest, "copy_rows", copy_mock)

    total = ingest.ingerir_arquivo(MagicMock(), str(csv_path), meta_brasilia)

    assert total == 0
    copy_mock.assert_not_called()


def test_ingerir_arquivo_pula_linhas_malformadas(
    make_inmet_csv, meta_brasilia, monkeypatch
):
    validas = [
        default_inmet_row(data="2023/01/01", hora="0000 UTC"),
        default_inmet_row(data="2023/01/01", hora="0100 UTC"),
    ]
    # Linha com excesso de delimitadores que pandas com on_bad_lines="skip" descarta
    linha_ruim = "linha;quebrada;" + ";".join(["x"] * 30)
    csv_path = make_inmet_csv(
        "INMET_CO_DF_A001_BRASILIA_01-01-2023_A_31-12-2023.CSV",
        rows=validas,
        raw_extra_lines=[linha_ruim],
    )

    lotes_enviados = []
    monkeypatch.setattr(
        ingest, "copy_rows", lambda cur, lote: lotes_enviados.append(list(lote))
    )

    total = ingest.ingerir_arquivo(MagicMock(), str(csv_path), meta_brasilia)

    assert total == 2
    assert len(lotes_enviados) == 1
    assert len(lotes_enviados[0]) == 2


def test_main_pasta_vazia_nao_abre_conexao(tmp_path, monkeypatch, caplog):
    get_conn_mock = MagicMock()
    monkeypatch.setattr(ingest, "PASTA_ENTRADA", str(tmp_path))
    monkeypatch.setattr(ingest, "get_conn", get_conn_mock)

    with caplog.at_level(logging.WARNING, logger="ingest"):
        ingest.main()

    get_conn_mock.assert_not_called()
    assert "Nenhum CSV encontrado" in caplog.text


def test_main_aceita_extensao_csv_em_minusculo_e_maiusculo(
    tmp_path, make_inmet_csv, monkeypatch
):
    arq_min = "INMET_CO_DF_A001_BRASILIA_01-01-2022_A_31-12-2022.csv"
    arq_mai = "INMET_CO_DF_A001_BRASILIA_01-01-2023_A_31-12-2023.CSV"
    make_inmet_csv(arq_min, rows=[default_inmet_row()])
    make_inmet_csv(arq_mai, rows=[default_inmet_row()])
    (tmp_path / "subpasta.csv").mkdir()

    conn, _ = _criar_fake_conn()
    monkeypatch.setattr(ingest, "PASTA_ENTRADA", str(tmp_path))
    monkeypatch.setattr(ingest, "get_conn", lambda: conn)
    monkeypatch.setattr(ingest, "copy_rows", MagicMock())

    ingest.main()

    assert conn.marcados_commitados == [(arq_min, 1), (arq_mai, 1)]


def test_main_pula_padrao_invalido_e_ja_ingerido_e_commita_novo(
    tmp_path, make_inmet_csv, monkeypatch
):
    make_inmet_csv("arquivo_qualquer.CSV", rows=[default_inmet_row()])
    nome_ja_ok = "INMET_CO_DF_A001_BRASILIA_01-01-2022_A_31-12-2022.CSV"
    make_inmet_csv(nome_ja_ok, rows=[default_inmet_row()])
    nome_novo = "INMET_CO_DF_A001_BRASILIA_01-01-2023_A_31-12-2023.CSV"
    make_inmet_csv(nome_novo, rows=[default_inmet_row(), default_inmet_row(hora="1300 UTC")])

    conn, _ = _criar_fake_conn(ja_ingeridos={nome_ja_ok})
    copy_mock = MagicMock()

    monkeypatch.setattr(ingest, "PASTA_ENTRADA", str(tmp_path))
    monkeypatch.setattr(ingest, "get_conn", lambda: conn)
    monkeypatch.setattr(ingest, "copy_rows", copy_mock)

    ingest.main()

    assert copy_mock.call_count == 1
    assert len(copy_mock.call_args.args[1]) == 2
    assert conn.commit.call_count == 1
    assert conn.rollback.call_count == 0
    assert conn.marcados_commitados == [(nome_novo, 2)]


def test_main_faz_rollback_isolado_em_erro_sem_afetar_outros_arquivos(
    tmp_path, make_inmet_csv, monkeypatch
):
    arq1 = "INMET_CO_DF_A001_BRASILIA_01-01-2021_A_31-12-2021.CSV"
    arq2 = "INMET_CO_DF_A001_BRASILIA_01-01-2022_A_31-12-2022.CSV"
    arq3 = "INMET_CO_DF_A001_BRASILIA_01-01-2023_A_31-12-2023.CSV"

    make_inmet_csv(arq1, rows=[default_inmet_row()])
    make_inmet_csv(arq2, rows=[default_inmet_row()])
    make_inmet_csv(arq3, rows=[default_inmet_row()])

    conn, _ = _criar_fake_conn()
    chamadas = {"n": 0}

    def copy_com_falha_no_segundo(cur, lote):
        chamadas["n"] += 1
        if chamadas["n"] == 2:
            raise RuntimeError("falha simulada no COPY")

    monkeypatch.setattr(ingest, "PASTA_ENTRADA", str(tmp_path))
    monkeypatch.setattr(ingest, "get_conn", lambda: conn)
    monkeypatch.setattr(ingest, "copy_rows", copy_com_falha_no_segundo)

    ingest.main()

    assert conn.commit.call_count == 2
    assert conn.rollback.call_count == 1
    assert conn.marcados_commitados == [(arq1, 1), (arq3, 1)]
