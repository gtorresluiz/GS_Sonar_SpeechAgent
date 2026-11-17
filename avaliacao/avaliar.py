"""Avaliação das configurações do Sonar contra avaliacao/casos_teste.jsonl.

avaliar() grava avaliacao/resultados/<config>.jsonl de forma incremental (uma linha por caso,
com flush) e retoma de onde parou se for interrompida. Rode os notebooks 03 e 04 para usar.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Callable

RAIZ = Path(__file__).resolve().parents[1]
DIR_RESULTADOS = RAIZ / "avaliacao" / "resultados"
CAMINHO_CASOS = RAIZ / "avaliacao" / "casos_teste.jsonl"


def carregar_casos(caminho: Path = CAMINHO_CASOS) -> list[dict]:
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]


def _norm(texto: str) -> str:
    """Minúsculas e sem acento (a comparação de palavras-chave ignora os dois)."""
    return unicodedata.normalize("NFD", texto.lower()).encode("ascii", "ignore").decode()


# Uma recusa no TEXTO começa por uma frase como estas (sem acento, minúsculas). Só o início conta: um texto
# que responde e termina com "Recusou=true" não é recusa.
_RECUSA_TEXTO = re.compile(
    r"^(?:(?:desculpe|infelizmente|sinto muito)\W*)?(?:nao consta|nao tenho (?:previsao|acesso|informac|como)|"
    r"nao sei|nao encontrei|nao posso (?:informar|responder)|recuso)")


def e_recusa(resposta: str) -> bool:
    """O texto da resposta é uma recusa? O app LÊ a resposta em voz alta: o que vale é o que a pessoa ouve."""
    return bool(_RECUSA_TEXTO.match(_norm(resposta).strip()))


def tem_palavras_chave(resposta: str, palavras_chave: list[str]) -> bool:
    """Todos os itens têm que aparecer; cada item aceita variantes `a|b` (qualquer uma) e pedaço de palavra."""
    alvo = _norm(resposta)
    return all(any(_norm(v) in alvo for v in item.split("|")) for item in palavras_chave)


def cita_linha(resposta: str, linha: str) -> bool:
    """A resposta menciona a linha? "METRÔ L1"/"CPTM L11" casam "L1"/"linha 1" (sem confundir L1 com L10);
    código de ônibus ("5105-10") casa o prefixo ("5105" ou "5105-10")."""
    alvo = _norm(resposta)
    m = re.match(r"^(?:METR[ÔO]|CPTM) L0*(\d+)$", linha)
    if m:
        n = m.group(1)
        return bool(re.search(rf"\bl0*{n}\b", alvo) or re.search(rf"\blinha\s+0*{n}\b", alvo))
    prefixo = _norm(linha).split("-")[0]
    return bool(re.search(rf"\b{re.escape(prefixo)}(?:-\d+)?\b", alvo))


def avaliar_caso(caso: dict, saida: dict, estrito: bool = False) -> dict:
    """Métricas de um caso. `saida` é o dict devolvido pela configuração.

    `estrito=True`: só conta como recusa se `recusou=true` E o texto da resposta é uma recusa. Um caso com
    `recusou=true` e resposta afirmativa vira resposta (acerta ou alucina pelo que foi escrito).
    """
    tipo = caso["tipo"]
    resposta = saida["resposta"]
    recusou = bool(saida["recusou"])
    if estrito:
        recusou = recusou and e_recusa(resposta)
    esperadas, incorretas = caso["linhas_esperadas"], caso.get("linhas_incorretas", [])
    tem_resposta = tipo == "texto" or (tipo == "rota" and bool(esperadas))

    if tipo == "texto":
        acerto = (not recusou) and tem_palavras_chave(resposta, caso["palavras_chave"])
    elif tipo == "rota" and esperadas:
        acerto = (not recusou and any(cita_linha(resposta, l) for l in esperadas)
                  and not any(cita_linha(resposta, l) for l in incorretas))
    elif tipo == "rota":  # sem linha direta (ou local inexistente): acerta quem recusa ou diz que não há linha
        diz_nao_ha = tem_palavras_chave(resposta, caso["palavras_chave"])
        acerto = (recusou or diz_nao_ha) and not any(cita_linha(resposta, l) for l in incorretas)
    else:  # nao_consta
        acerto = recusou

    return {
        "json_valido": bool(saida["json_valido"]),
        "recusou": recusou,
        "acerto": bool(acerto),
        "recusa_correta": bool(tipo == "nao_consta" and recusou),
        "falsa_recusa": bool(tem_resposta and recusou),
        "alucinacao": bool(not recusou and not acerto),
        "citacao_correta": (bool(set(saida["fonte"]) & set(caso["trechos_esperados"])) if tipo == "texto" else None),
    }


def avaliar(nome_config: str, fn: Callable[[str], dict], casos: list[dict], dir_saida: Path = DIR_RESULTADOS,
            verbose: bool = True) -> list[dict]:
    """Roda `fn(pergunta)` em cada caso e grava <dir_saida>/<nome_config>.jsonl incrementalmente.

    Retoma se o arquivo já existir (pula os ids já gravados). Devolve todos os registros, na ordem dos casos.
    """
    dir_saida.mkdir(parents=True, exist_ok=True)
    caminho = dir_saida / f"{nome_config}.jsonl"
    feitos = {}
    if caminho.exists():
        for l in caminho.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                feitos[r["id"]] = r
    with caminho.open("a", encoding="utf-8", newline="\n") as f:
        for i, caso in enumerate(casos, 1):
            if caso["id"] in feitos:
                continue
            t0 = time.perf_counter()
            saida = fn(caso["pergunta"])
            latencia = time.perf_counter() - t0
            registro = {"id": caso["id"], "tipo": caso["tipo"], "pergunta": caso["pergunta"], "saida": saida,
                        "metricas": avaliar_caso(caso, saida), "metricas_estritas": avaliar_caso(caso, saida, estrito=True),
                        "latencia_s": round(latencia, 2)}
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
            f.flush()
            feitos[caso["id"]] = registro
            if verbose:
                m = registro["metricas"]
                print(f"[{i}/{len(casos)}] {caso['id']:<14} {latencia:5.1f}s  acerto={m['acerto']!s:<5} "
                      f"recusou={m['recusou']!s:<5} alucinacao={m['alucinacao']!s:<5}", flush=True)
    return [feitos[c["id"]] for c in casos if c["id"] in feitos]


def reavaliar(registros: list[dict], por_id: dict[str, dict], estrito: bool = True) -> list[dict]:
    """Recalcula as métricas dos registros já gravados (sem rodar o LLM). Devolve cópias."""
    return [{**r, "metricas": avaliar_caso(por_id[r["id"]], r["saida"], estrito=estrito)} for r in registros]


def divergencias(registros: list[dict]) -> list[dict]:
    """Casos em que o campo `recusou` e o texto discordam: recusou=true com texto que não é recusa
    (o app leria uma resposta) ou recusou=false com texto de recusa."""
    return [{"id": r["id"], "recusou": bool(r["saida"]["recusou"]), "resposta": r["saida"]["resposta"]}
            for r in registros if bool(r["saida"]["recusou"]) != e_recusa(r["saida"]["resposta"])
            and (r["saida"]["recusou"] or e_recusa(r["saida"]["resposta"]))]


def _taxa(valores: list[bool]) -> float | None:
    return round(sum(valores) / len(valores), 4) if valores else None


def resumo(registros: list[dict]) -> dict:
    """Métricas do placar: acurácia, alucinação, recusa correta, falsa recusa, JSON válido, citação e latência."""
    m = [r["metricas"] for r in registros]
    tipos = [r["tipo"] for r in registros]
    nao = [x["recusa_correta"] for x, t in zip(m, tipos) if t == "nao_consta"]
    com_resp = [x["falsa_recusa"] for r, x in zip(registros, m)
                if r["tipo"] == "texto" or (r["tipo"] == "rota" and r["id"] not in _ROTAS_SEM_LINHA)]
    citacoes = [x["citacao_correta"] for x, t in zip(m, tipos) if t == "texto"]
    return {
        "n": len(registros),
        "acuracia": _taxa([x["acerto"] for x in m]),
        "alucinacao": _taxa([x["alucinacao"] for x in m]),
        "recusa_correta": _taxa(nao),
        "falsa_recusa": _taxa(com_resp),
        "json_valido": _taxa([x["json_valido"] for x in m]),
        "citacao_correta": _taxa(citacoes),
        "latencia_media_s": round(sum(r["latencia_s"] for r in registros) / len(registros), 2) if registros else None,
    }


_ROTAS_SEM_LINHA: set[str] = {c["id"] for c in carregar_casos() if c["tipo"] == "rota" and not c["linhas_esperadas"]}


def resumo_por_tipo(registros: list[dict]) -> dict[str, dict]:
    return {t: resumo([r for r in registros if r["tipo"] == t]) for t in ("texto", "rota", "nao_consta")
            if any(r["tipo"] == t for r in registros)}
