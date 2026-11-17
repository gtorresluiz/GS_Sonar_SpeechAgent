"""Testes da ferramenta GTFS. Rode com: pytest -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sonar_ia.gtfs import GTFS  # noqa: E402

g = GTFS(Path(__file__).resolve().parents[1] / "base" / "gtfs")


def test_metro_linha_direta():
    r = g.linhas_diretas("Vila Madalena", "Paraíso")
    assert r["encontrado"] and r["linhas"][0]["linha"] == "METRÔ L2"


def test_sentido_respeitado():
    ida = g.linhas_diretas("Tucuruvi", "Jabaquara")
    assert ida["linhas"][0]["sentido"] == "JABAQUARA"


def test_local_inexistente_recusa():
    r = g.linhas_diretas("Xyzlândia", "Sé")
    assert not r["encontrado"] and "não encontrado" in r["motivo"]
