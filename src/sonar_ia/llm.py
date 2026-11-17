"""Cliente do LLM local (Ollama). Nada de API em nuvem: o modelo roda na máquina."""
from __future__ import annotations

import os
from typing import TypeVar

import ollama
from pydantic import BaseModel, ValidationError

from sonar_ia.esquema import RespostaLLM, RespostaSonar, esquema_json

MODELO_PADRAO = "qwen2.5:3b"
OPCOES = {"temperature": 0, "seed": 42, "num_ctx": 4096}
LEMBRETE = "Sua resposta anterior não era um JSON válido. Responda só com o JSON no formato pedido."


def nome_modelo() -> str:
    """Modelo escolhido pela variável de ambiente SONAR_MODELO (padrão qwen2.5:3b)."""
    return os.environ.get("SONAR_MODELO", MODELO_PADRAO)


def gerar(sistema: str, usuario: str, tentativas: int = 2) -> RespostaLLM:
    """Chama o LLM pedindo JSON no esquema de RespostaSonar e valida com pydantic.

    Se a validação falhar, tenta mais 1 vez (com um lembrete); depois devolve um objeto com
    `json_valido=False` e o texto bruto em `resposta`.
    """
    mensagens = [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]
    bruto = ""
    for tentativa in range(tentativas):
        retorno = ollama.chat(model=nome_modelo(), messages=mensagens, format=esquema_json(), options=OPCOES)
        bruto = retorno["message"]["content"]
        try:
            valida = RespostaSonar.model_validate_json(bruto)
            return RespostaLLM(**valida.model_dump(), json_valido=True, bruto=bruto)
        except ValidationError:
            mensagens = mensagens[:2] + [{"role": "assistant", "content": bruto}, {"role": "user", "content": LEMBRETE}]
    return RespostaLLM(resposta=bruto, fonte=[], confianca=0.0, recusou=False, json_valido=False, bruto=bruto)


T = TypeVar("T", bound=BaseModel)


def gerar_estruturado(sistema: str, usuario: str, classe: type[T], tentativas: int = 2) -> tuple[T | None, str]:
    """Como `gerar`, mas para qualquer esquema pydantic (usado pelo roteador do agente).

    Devolve (objeto, bruto); objeto é None se a saída não validar depois das tentativas.
    """
    mensagens = [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]
    bruto = ""
    for _ in range(tentativas):
        retorno = ollama.chat(model=nome_modelo(), messages=mensagens, format=classe.model_json_schema(),
                              options=OPCOES)
        bruto = retorno["message"]["content"]
        try:
            return classe.model_validate_json(bruto), bruto
        except ValidationError:
            mensagens = mensagens[:2] + [{"role": "assistant", "content": bruto}, {"role": "user", "content": LEMBRETE}]
    return None, bruto