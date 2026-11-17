"""Config 3: agente com ferramentas (roteador -> ferramenta -> redação).

Ferramentas: buscar_base (mesmo fluxo do RAG), consultar_gtfs (determinística, SPTrans) e
previsao_onibus (Olho Vivo, só demo e só com SPTRANS_TOKEN). O LLM é local (Ollama).
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

import requests
from pydantic import BaseModel

from sonar_ia import configs
from sonar_ia.base import RAIZ
from sonar_ia.esquema import RECUSA, RespostaLLM
from sonar_ia.gtfs import GTFS
from sonar_ia.llm import gerar, gerar_estruturado

FERRAMENTAS = ("buscar_base", "consultar_gtfs", "previsao_onibus", "nenhuma")
SEM_PREVISAO = "Não tenho previsão em tempo real agora."


class Roteamento(BaseModel):
    """Saída do roteador. Campos de argumento vazios quando não se aplicam."""

    ferramenta: Literal["buscar_base", "consultar_gtfs", "previsao_onibus", "nenhuma"]
    origem: str = ""
    destino: str = ""
    linha: str = ""
    parada: str = ""


SISTEMA_ROTEADOR = """Você escolhe a ferramenta certa para a pergunta de uma pessoa cega sobre transporte público em São Paulo.
Responda SOMENTE em JSON com os campos "ferramenta", "origem", "destino", "linha" e "parada" (deixe vazio o que não se aplica).

Ferramentas:
- buscar_base: perguntas sobre acessibilidade, direitos, regras, serviços (elevador, cão-guia, Bilhete Único Especial, conduta do motorista).
- consultar_gtfs: "qual linha vai de A até B?" (preencha origem e destino com os nomes dos locais).
- previsao_onibus: horário em que um ônibus chega a um ponto, em tempo real (preencha linha e parada).
- nenhuma: assunto que não é transporte público de São Paulo.

Exemplos:
Pergunta: qual linha leva do terminal varginha ao terminal grajau?
{"ferramenta": "consultar_gtfs", "origem": "Terminal Varginha", "destino": "Terminal Grajaú", "linha": "", "parada": ""}
Pergunta: tem metro direto da vila mariana ate a liberdade?
{"ferramenta": "consultar_gtfs", "origem": "Vila Mariana", "destino": "Liberdade", "linha": "", "parada": ""}
Pergunta: a estaçao anhangabau tem elevador?
{"ferramenta": "buscar_base", "origem": "", "destino": "", "linha": "", "parada": ""}
Pergunta: o cao guia pode entrar num restaurante?
{"ferramenta": "buscar_base", "origem": "", "destino": "", "linha": "", "parada": ""}
Pergunta: que horas chega o onibus 8000-10 no ponto da praça da sé?
{"ferramenta": "previsao_onibus", "origem": "", "destino": "", "linha": "8000-10", "parada": "Praça da Sé"}
Pergunta: vai chover amanha?
{"ferramenta": "nenhuma", "origem": "", "destino": "", "linha": "", "parada": ""}"""

SISTEMA_REDACAO_ROTA = (
    "Você é o Sonar, assistente de transporte público acessível para pessoas cegas em São Paulo. "
    "Sua resposta será falada em voz alta. Responda SOMENTE em JSON com os campos "
    '"resposta", "fonte", "confianca" (número de 0 a 1) e "recusou".\n'
    "Você recebe o resultado da ferramenta de rotas (lista de linhas diretas). Regras:\n"
    "(a) Use SÓ as linhas que estão no resultado. Não invente linha, sentido nem parada.\n"
    '(b) Cite o código ou nome de cada linha, exatamente como no resultado, e o sentido.\n'
    '(c) Use fonte = ["gtfs_sptrans"] e recusou = false.\n'
    "(d) Resposta curta (no máximo 2 frases), em português simples, sem listas nem símbolos, "
    "para ser falada a uma pessoa cega."
)

_gtfs: dict[str, GTFS] = {}


def gtfs(v2: bool = False) -> GTFS:
    """GTFS único por modo: "v1" (agente oficial) ou "v2" (correção C1, agente_v2)."""
    modo = "v2" if v2 else "v1"
    if modo not in _gtfs:
        _gtfs[modo] = GTFS(RAIZ / "base" / "gtfs", modo=modo)
    return _gtfs[modo]


# ---------------------------------------------------------------- ferramentas


def consultar_gtfs(origem: str, destino: str, v2: bool = False) -> dict:
    """Ferramenta determinística: linhas diretas entre dois locais (sobre o GTFS da SPTrans)."""
    return gtfs(v2).linhas_diretas(origem, destino)


def previsao_onibus(linha: str, parada: str) -> dict:
    """Previsão de chegada pelo Olho Vivo (SPTrans). Só funciona com SPTRANS_TOKEN; é demo (tempo real).

    NÃO TESTADO: não havia token na máquina. Sem token devolve {"disponivel": False}.
    """
    token = os.environ.get("SPTRANS_TOKEN")
    if not token:
        return {"disponivel": False, "motivo": "SPTRANS_TOKEN ausente"}
    base = "http://api.olhovivo.sptrans.com.br/v2.1"
    try:
        s = requests.Session()
        if not s.post(f"{base}/Login/Autenticar", params={"token": token}, timeout=15).json():
            return {"disponivel": False, "motivo": "autenticação recusada"}
        paradas = s.get(f"{base}/Parada/Buscar", params={"termosBusca": parada}, timeout=15).json()
        linhas = s.get(f"{base}/Linha/Buscar", params={"termosBusca": linha}, timeout=15).json()
        if not paradas or not linhas:
            return {"disponivel": False, "motivo": "parada ou linha não encontrada"}
        prev = s.get(f"{base}/Previsao", params={"codigoParada": paradas[0]["cp"], "codigoLinha": linhas[0]["cl"]},
                     timeout=15).json()
        return {"disponivel": True, "parada": paradas[0].get("np"), "linha": linhas[0].get("lt"), "previsao": prev}
    except (requests.RequestException, ValueError, KeyError) as erro:
        return {"disponivel": False, "motivo": f"erro no Olho Vivo: {erro}"}


# -------------------------------------------------------- pós-checagem de linhas


def chaves_de_linhas(texto: str) -> set[tuple[str, str]]:
    """Linhas mencionadas num texto, normalizadas: ("trilho", "11") p/ metrô/CPTM e ("onibus", "5105") p/ ônibus.

    Reconhece "L11", "L07", "linha 3", códigos de ônibus ("5105-10", "N103-11", "875C").
    """
    chaves: set[tuple[str, str]] = set()
    for n in re.findall(r"\bL\s?0*(\d{1,2})\b", texto):
        chaves.add(("trilho", n))
    for n in re.findall(r"\blinha\s+0*(\d{1,2})\b", texto, flags=re.I):
        chaves.add(("trilho", n))
    # ônibus: só com sufixo ("5105-10"), letra ("476A", "N103") ou depois de "ônibus/linha" (evita número de rua)
    for cod in re.findall(r"\b(N\d{3}|\d{3,4}[A-Z])(?:-\d{1,2})?\b", texto):
        chaves.add(("onibus", cod.upper()))
    for cod in re.findall(r"\b(\d{3,4})-\d{1,2}\b", texto):
        chaves.add(("onibus", cod))
    for cod in re.findall(r"\b(?:ônibus|onibus|linha)\s+(\d{3,4})\b", texto, flags=re.I):
        chaves.add(("onibus", cod))
    return chaves


def linhas_da_ferramenta(resultado: dict) -> set[tuple[str, str]]:
    """As mesmas chaves, a partir das linhas devolvidas por `consultar_gtfs`."""
    chaves: set[tuple[str, str]] = set()
    for l in resultado.get("linhas", []):
        codigo = l["linha"]
        m = re.match(r"^(?:METRÔ|CPTM) L0*(\d+)$", codigo)
        if m:
            chaves.add(("trilho", m.group(1)))
        else:
            chaves.add(("onibus", codigo.split("-")[0].upper()))
    return chaves


# ------------------------------------------------------------------- o agente


def _recusa(ferramenta: str, args: dict, bruto, barreira: str, resposta: str = RECUSA, **extra) -> dict:
    r = RespostaLLM(resposta=resposta, fonte=[], confianca=0.0, recusou=True, json_valido=True)
    return {**r.model_dump(), "barreira": barreira, "recuperados": [], "scores": [], "citacao_invalida": False,
            "ferramenta": ferramenta, "argumentos": args, "saida_ferramenta": bruto, "linha_inventada": False,
            "roteador_valido": True, **extra}


def rotear(pergunta: str) -> tuple[Roteamento, bool, str]:
    """Roteador: devolve (roteamento, json_valido, bruto). Se o JSON do roteador for inválido, cai em buscar_base."""
    r, bruto = gerar_estruturado(SISTEMA_ROTEADOR, f"Pergunta: {pergunta}", Roteamento)
    if r is None:
        return Roteamento(ferramenta="buscar_base"), False, bruto
    return r, True, bruto


def agente(pergunta: str) -> dict:
    """Config 3 (oficial): roteador -> ferramenta -> redação. Grava ferramenta, argumentos e saída bruta."""
    return _agente(pergunta, v2=False)


def agente_v2(pergunta: str) -> dict:
    """Config 3 com as correções da etapa 6: C1/C1b (GTFS v2 com abreviações), C2 (citação inválida -> recusa),
    C3 (roteador diz "nenhuma", mas a busca acha trecho acima do limiar -> usa buscar_base) e C4 (recusou=true
    -> texto de recusa padrão)."""
    return _normalizar_recusa(_agente(pergunta, v2=True))


def _normalizar_recusa(saida: dict) -> dict:
    """C4: se `recusou=true`, o texto tem que ser a recusa padrão (o app lê a resposta em voz alta).
    Mantém a recusa de tempo real ("Não tenho previsão em tempo real agora."), que já é uma recusa."""
    if saida["recusou"] and saida["resposta"] not in (RECUSA, SEM_PREVISAO):
        return {**saida, "resposta_original": saida["resposta"], "resposta": RECUSA, "fonte": [], "confianca": 0.0}
    return saida


def _agente(pergunta: str, v2: bool) -> dict:
    rot, rot_valido, rot_bruto = rotear(pergunta)
    args = {k: v for k, v in rot.model_dump().items() if k != "ferramenta" and v}
    extra = {"roteador_valido": rot_valido, "roteador_bruto": rot_bruto}

    if rot.ferramenta == "buscar_base":
        saida = configs.rag(pergunta)
        if v2 and saida["citacao_invalida"]:  # C2: barreira 3
            return {**_recusa("buscar_base", args, {"recuperados": saida["recuperados"], "scores": saida["scores"],
                                                    "resposta_descartada": saida["resposta"],
                                                    "fonte_descartada": saida["fonte"]}, "citacao_invalida",
                              recuperados=saida["recuperados"], scores=saida["scores"], citacao_invalida=True), **extra}
        return {**saida, "ferramenta": "buscar_base", "argumentos": args, "linha_inventada": False,
                "saida_ferramenta": {"recuperados": saida["recuperados"], "scores": saida["scores"]}, **extra}

    if rot.ferramenta == "consultar_gtfs":
        if not rot.origem or not rot.destino:
            return {**_recusa("consultar_gtfs", args, None, "roteador"), **extra}
        res = consultar_gtfs(rot.origem, rot.destino, v2)
        if not res.get("encontrado") or not res.get("linhas"):
            return {**_recusa("consultar_gtfs", args, res, "ferramenta"), **extra}
        r = gerar(SISTEMA_REDACAO_ROTA,
                  f"Pergunta: {pergunta}\n\nResultado da ferramenta (linhas diretas de {rot.origem} até {rot.destino}):\n"
                  + "\n".join(f"- {l['linha']} ({l['tipo']}), sentido {l['sentido']}, embarca em {l['parada_embarque']}, "
                              f"desembarca em {l['parada_desembarque']}" for l in res["linhas"]))
        inventadas = chaves_de_linhas(r.resposta) - linhas_da_ferramenta(res)
        out = r.model_dump()
        if not r.recusou:
            out["fonte"] = ["gtfs_sptrans"]
        return {**out, "barreira": None, "recuperados": [], "scores": [], "citacao_invalida": False,
                "ferramenta": "consultar_gtfs", "argumentos": args, "saida_ferramenta": res,
                "linha_inventada": bool(inventadas), "linhas_inventadas": sorted("/".join(c) for c in inventadas), **extra}

    if rot.ferramenta == "previsao_onibus":
        res = previsao_onibus(rot.linha, rot.parada)
        if not res.get("disponivel"):
            return {**_recusa("previsao_onibus", args, res, "ferramenta", resposta=SEM_PREVISAO), **extra}
        r = RespostaLLM(resposta=f"Previsão do Olho Vivo: {res.get('previsao')}", fonte=["olho_vivo"], confianca=0.5,
                        recusou=False, json_valido=True)  # demo, sem redação pelo LLM (não testado: sem token)
        return {**r.model_dump(), "barreira": None, "recuperados": [], "scores": [], "citacao_invalida": False,
                "ferramenta": "previsao_onibus", "argumentos": args, "saida_ferramenta": res,
                "linha_inventada": False, **extra}

    if v2:  # C3: o roteador desistiu, mas a base tem trecho acima do limiar
        b = configs.buscador()
        achados = b.buscar(pergunta, k=1)
        if b.limiar is not None and achados and achados[0][1] >= b.limiar:
            saida = configs.rag(pergunta)
            if saida["citacao_invalida"]:
                return {**_recusa("buscar_base", args, {"recuperados": saida["recuperados"], "scores": saida["scores"]},
                                  "citacao_invalida", recuperados=saida["recuperados"], scores=saida["scores"],
                                  citacao_invalida=True), **extra, "fallback_roteador": True}
            return {**saida, "ferramenta": "buscar_base", "argumentos": args, "linha_inventada": False,
                    "saida_ferramenta": {"recuperados": saida["recuperados"], "scores": saida["scores"]},
                    "fallback_roteador": True, **extra}
    return {**_recusa("nenhuma", args, None, "roteador"), **extra}
