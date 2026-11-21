"""Testes unitários para coleta e UPSERT da dimensão de estações (sincronizar_estacoes.py)."""
from unittest.mock import MagicMock

import pytest
import requests

import sincronizar_estacoes


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("-15.7894", -15.7894),
        ("1160", 1160.0),
        (42, 42.0),
        (None, None),
        ("", None),
        ("N/A", None),
        ("abc", None),
    ],
)
def test_to_float(entrada, esperado):
    assert sincronizar_estacoes._to_float(entrada) == esperado


def test_coletar_consulta_ambos_endpoints_e_deduplica_por_cd_estacao(monkeypatch):
    payload_m = [
        {
            "DC_NOME": "BRASILIA",
            "CD_ESTACAO": "83377",
            "SG_ESTADO": "DF",
            "VL_LATITUDE": "-15.789",
            "VL_LONGITUDE": "-47.925",
            "VL_ALTITUDE": "1160.9",
            "TP_ESTACAO": "Convencional",
            "CD_SITUACAO": "Operante",
        },
        {
            "DC_NOME": "SEM CODIGO",
            "CD_ESTACAO": None,
            "SG_ESTADO": "DF",
        },
    ]
    payload_t = [
        {
            "DC_NOME": "BRASILIA DUPLICADA",
            "CD_ESTACAO": "83377",  # duplicada do endpoint /M -> deve ser ignorada
            "SG_ESTADO": "DF",
            "VL_LATITUDE": "-15.0",
            "VL_LONGITUDE": "-47.0",
            "VL_ALTITUDE": "1000",
            "TP_ESTACAO": "Automatica",
            "CD_SITUACAO": "Operante",
        },
        {
            "DC_NOME": "BRASILIA",
            "CD_ESTACAO": "A001",  # automatica na mesma cidade -> deve ser mantida
            "SG_ESTADO": "DF",
            "VL_LATITUDE": "-15.789",
            "VL_LONGITUDE": "-47.925",
            "VL_ALTITUDE": "1160.9",
            "TP_ESTACAO": "Automatica",
            "CD_SITUACAO": "Operante",
        },
        {
            "DC_NOME": "GOIANIA",
            "CD_ESTACAO": "A002",
            "SG_ESTADO": "GO",
            "VL_LATITUDE": "-16.64",
            "VL_LONGITUDE": "-49.22",
            "VL_ALTITUDE": "",
            "TP_ESTACAO": "Automatica",
            "CD_SITUACAO": "Operante",
        },
    ]

    urls_chamadas = []

    def fake_get(url, timeout):
        urls_chamadas.append((url, timeout))
        resp = MagicMock()
        resp.json.return_value = payload_m if url.endswith("/M") else payload_t
        return resp

    monkeypatch.setattr(sincronizar_estacoes.requests, "get", fake_get)

    rows = sincronizar_estacoes.coletar()

    assert urls_chamadas == [
        (sincronizar_estacoes.ENDPOINTS[0], 30),
        (sincronizar_estacoes.ENDPOINTS[1], 30),
    ]
    assert rows == [
        ("BRASILIA", "83377", "DF", -15.789, -47.925, 1160.9, "Convencional", "Operante"),
        ("BRASILIA", "A001", "DF", -15.789, -47.925, 1160.9, "Automatica", "Operante"),
        ("GOIANIA", "A002", "GO", -16.64, -49.22, None, "Automatica", "Operante"),
    ]
    assert all(len(r) == len(sincronizar_estacoes.COLS) for r in rows)


def test_coletar_propaga_erro_http(monkeypatch):
    def fake_get(url, timeout):
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")
        return resp

    monkeypatch.setattr(sincronizar_estacoes.requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        sincronizar_estacoes.coletar()


def test_upsert_executa_insert_on_conflict_e_fecha_recursos(monkeypatch):
    cur = MagicMock()
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(sincronizar_estacoes, "get_conn", lambda: conn)

    rows = [
        ("BRASILIA", "A001", "DF", -15.78, -47.92, 1160.0, "Automatica", "Operante"),
    ]

    sincronizar_estacoes.upsert(rows)

    sql, arg_rows = cur.executemany.call_args.args
    assert "INSERT INTO estacoes" in sql
    assert "ON CONFLICT (cod_estacao) DO UPDATE SET" in sql
    assert arg_rows == rows
    conn.commit.assert_called_once()
    conn.cursor.return_value.__exit__.assert_called_once()
    conn.__exit__.assert_called_once()


def test_upsert_fecha_recursos_mesmo_em_excecao(monkeypatch):
    cur = MagicMock()
    cur.executemany.side_effect = RuntimeError("erro simulado no banco")
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cur
    monkeypatch.setattr(sincronizar_estacoes, "get_conn", lambda: conn)

    with pytest.raises(RuntimeError, match="erro simulado"):
        sincronizar_estacoes.upsert([("BRASILIA", "A001", "DF", -15.78, -47.92, 1160.0, "Automatica", "Operante")])

    conn.commit.assert_not_called()
    conn.cursor.return_value.__exit__.assert_called_once()
    conn.__exit__.assert_called_once()
