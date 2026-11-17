"""Testes da API (TestClient). Usam o Ollama local de verdade; sem ele, pulam. Rode com: pytest -q"""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))

import ollama  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402


def _ollama_no_ar() -> bool:
    try:
        ollama.list()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _ollama_no_ar(), reason="Ollama não está rodando")


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:  # o `with` roda o startup (carrega índice e GTFS uma vez)
        yield c


def _perguntar(cliente, pergunta: str, **extra) -> dict:
    r = cliente.post("/assistente/perguntar", json={"pergunta": pergunta, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def test_saude(cliente):
    r = cliente.get("/saude").json()
    assert r["status"] == "ok" and r["indice"]["trechos"] > 0 and r["gtfs"]["paradas"] > 0


def test_texto_responde_com_fonte(cliente):
    r = _perguntar(cliente, "oi, a estaçao tucuruvi tem elevador?")
    assert not r["recusou"] and "elevador" in r["resposta"].lower()
    assert r["ferramenta"] == "buscar_base" and "metro_elev_l1-azul_tucuruvi" in r["fonte"]


def test_rota_usa_gtfs(cliente):
    r = _perguntar(cliente, "qual linha do metrô vai do tucuruvi ate o jabaquara?")
    assert not r["recusou"] and r["ferramenta"] == "consultar_gtfs" and r["fonte"] == ["gtfs_sptrans"]
    assert "l1" in r["resposta"].lower()


def test_nao_consta_recusa(cliente):
    r = _perguntar(cliente, "quanto custa uma corrida de uber do terminal santo amaro até a paulista?")
    assert r["recusou"] and r["resposta"] == "Não consta na base de conhecimento." and r["fonte"] == []


def test_pergunta_vazia_e_config_invalida(cliente):
    assert cliente.post("/assistente/perguntar", json={"pergunta": ""}).status_code == 422
    assert cliente.post("/assistente/perguntar", json={"pergunta": "oi", "config": "nuvem"}).status_code == 422
