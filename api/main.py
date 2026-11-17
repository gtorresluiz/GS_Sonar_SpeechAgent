"""API do assistente Sonar (FastAPI).

Rode da raiz do repositório:  uvicorn api.main:app --port 8000

Endpoints:
- POST /assistente/perguntar  {pergunta, config?} -> RespostaSonar + ferramenta
- GET  /saude                 status do Ollama, do índice de busca e do GTFS

LGPD (privacidade por padrão):
- A pergunta NÃO é gravada com identificador de usuário: a API não recebe nem guarda nome, id, IP ou token
  de quem pergunta, e não mantém histórico nem sessão.
- Nenhum áudio é persistido: esta API só recebe texto (a transcrição de voz, se houver, fica no cliente/demo).
- O log guarda só a configuração, a ferramenta usada e a latência. O texto da pergunta e o da resposta nunca
  vão para o log.
- O LLM é local (Ollama): nenhum dado sai da máquina para APIs em nuvem.
"""
from __future__ import annotations

import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import ollama  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from sonar_ia import agente as ag  # noqa: E402
from sonar_ia import configs  # noqa: E402
from sonar_ia.esquema import RespostaSonar  # noqa: E402
from sonar_ia.llm import nome_modelo  # noqa: E402

log = logging.getLogger("sonar.api")  # só config, ferramenta e latência (ver docstring de LGPD)
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)

ConfigNome = Literal["agente_v2", "agente", "rag"]
CONFIGS = {"agente_v2": ag.agente_v2, "agente": ag.agente, "rag": configs.rag}


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=1, max_length=500)
    config: ConfigNome = "agente_v2"


class RespostaAPI(RespostaSonar):
    """RespostaSonar + qual ferramenta respondeu (`buscar_base`, `consultar_gtfs`, `previsao_onibus`,
    `nenhuma`; no `rag` é sempre `buscar_base`)."""

    ferramenta: str | None = None
    config: ConfigNome


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Carrega uma vez o índice de busca (embeddings + FAISS) e o GTFS (v1 e v2)."""
    configs.buscador()
    ag.gtfs(v2=False)
    ag.gtfs(v2=True)
    yield


app = FastAPI(title="Sonar: assistente de mobilidade acessível", version="0.1.0", lifespan=ciclo_de_vida)


@app.post("/assistente/perguntar", response_model=RespostaAPI)
def perguntar(corpo: Pergunta) -> RespostaAPI:
    """Responde com fonte, sem inventar: `recusou=true` e "Não consta na base de conhecimento." se não souber."""
    t0 = time.perf_counter()
    saida = CONFIGS[corpo.config](corpo.pergunta)
    ferramenta = saida.get("ferramenta") or ("buscar_base" if corpo.config == "rag" else None)
    log.info("config=%s ferramenta=%s latencia_s=%.2f", corpo.config, ferramenta, time.perf_counter() - t0)
    return RespostaAPI(resposta=saida["resposta"], fonte=saida["fonte"], confianca=saida["confianca"],
                       recusou=saida["recusou"], ferramenta=ferramenta, config=corpo.config)


@app.get("/saude")
def saude() -> dict:
    """Status do Ollama (e se o modelo está instalado), do índice de busca e do GTFS."""
    try:
        instalados = [m.model for m in ollama.list().models]
        modelo = nome_modelo()
        ollama_ok = {"ok": any(i == modelo or i.startswith(modelo + ":") for i in instalados), "modelo": modelo,
                     "instalado": modelo in instalados}
    except Exception as erro:  # servidor do Ollama fora do ar
        ollama_ok = {"ok": False, "modelo": nome_modelo(), "erro": type(erro).__name__}
    b = configs.buscador()
    indice = {"ok": b.indice.ntotal > 0, "trechos": int(b.indice.ntotal), "limiar": b.limiar}
    g = ag.gtfs(v2=True)
    gtfs = {"ok": len(g.stops) > 0, "paradas": int(len(g.stops)), "rotas": int(len(g.routes))}
    return {"status": "ok" if ollama_ok["ok"] and indice["ok"] and gtfs["ok"] else "degradado",
            "ollama": ollama_ok, "indice": indice, "gtfs": gtfs}
