"""Esquema pydantic da resposta do Sonar (o JSON que o LLM deve devolver)."""
from __future__ import annotations

from pydantic import BaseModel, Field

RECUSA = "Não consta na base de conhecimento."


class RespostaSonar(BaseModel):
    """Formato único de saída: {"resposta": "...", "fonte": ["id_trecho"], "confianca": 0.0, "recusou": false}."""

    resposta: str
    fonte: list[str] = Field(default_factory=list)
    confianca: float = Field(ge=0.0, le=1.0)
    recusou: bool


class RespostaLLM(RespostaSonar):
    """Resposta + marcas de execução. `json_valido=False` quando o LLM não devolveu JSON válido
    (nesse caso `resposta` guarda o texto bruto, `recusou=False` e `confianca=0`)."""

    json_valido: bool = True
    bruto: str = ""


def esquema_json() -> dict:
    """JSON schema que vai no parâmetro `format` do Ollama (só os 4 campos da resposta)."""
    return RespostaSonar.model_json_schema()
