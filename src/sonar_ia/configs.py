"""Configurações avaliadas: (1) LLM sem contexto e (2) RAG simples top-3 com duas barreiras de recusa."""
from __future__ import annotations

from sonar_ia.busca import Buscador
from sonar_ia.esquema import RECUSA, RespostaLLM
from sonar_ia.llm import gerar

PERSONA = ("Você é o Sonar, assistente de transporte público acessível para pessoas cegas em São Paulo. "
           "Sua resposta será falada em voz alta. Responda SOMENTE em JSON com os campos "
           '"resposta", "fonte", "confianca" (número de 0 a 1) e "recusou".')

SISTEMA_SEM_CONTEXTO = (
    "Você é o Sonar, assistente de transporte público acessível para pessoas cegas em São Paulo. "
    "Sua resposta será falada em voz alta. Responda a pergunta em JSON com os campos "
    '"resposta", "fonte", "confianca" (número de 0 a 1) e "recusou". '
    'Use fonte = [] se você não tiver fonte. Responda curto, em português simples (no máximo 2 frases).'
)

# Config 1b (apêndice): a mesma coisa, com a instrução de recusar se não souber.
SISTEMA_SEM_CONTEXTO_INSTR = (
    PERSONA + " Responda curto, em português simples (no máximo 2 frases). "
    "Se você não souber a resposta com segurança, recuse: recusou=true, "
    f'resposta="{RECUSA}", fonte=[] e confianca=0. Em "fonte" use sempre [] (você não tem trechos).'
)

SISTEMA_RAG = (
    PERSONA + " Você recebe trechos de uma base de conhecimento, cada um marcado por um id entre colchetes.\n"
    "Regras:\n"
    "(a) Responda SOMENTE com o que está escrito nos trechos. Não use conhecimento próprio.\n"
    '(b) Em "fonte" liste os ids dos trechos que você usou, exatamente como aparecem entre colchetes.\n'
    "(c) Se os trechos falam de outra estação, outra linha, outra cidade ou outro serviço que não o perguntado, "
    "ou se a pergunta pede dado em tempo real (agora, hoje, funcionando, horário de passagem), recuse com "
    f'recusou=true, resposta="{RECUSA}", fonte=[] e confianca=0.\n'
    "(d) Resposta curta (no máximo 2 frases), em português simples, sem listas nem símbolos, "
    "para ser falada a uma pessoa cega."
)

_buscador: Buscador | None = None


def buscador() -> Buscador:
    """Buscador único (carregar o modelo de embedding custa alguns segundos)."""
    global _buscador
    if _buscador is None:
        _buscador = Buscador()
    return _buscador


def _saida(r: RespostaLLM, barreira: str | None, recuperados: list[str], scores: list[float],
           citacao_invalida: bool = False) -> dict:
    return {**r.model_dump(), "barreira": barreira, "recuperados": recuperados, "scores": scores,
            "citacao_invalida": citacao_invalida}


def sem_contexto(pergunta: str) -> dict:
    """Config 1 (oficial): só o LLM, sem consultar a base e sem instrução de recusa."""
    return _saida(gerar(SISTEMA_SEM_CONTEXTO, f"Pergunta: {pergunta}"), None, [], [])


def sem_contexto_instr(pergunta: str) -> dict:
    """Config 1b (apêndice): só o LLM, com a instrução de recusar se não souber."""
    return _saida(gerar(SISTEMA_SEM_CONTEXTO_INSTR, f"Pergunta: {pergunta}"), None, [], [])


def rag(pergunta: str) -> dict:
    """Config 2: RAG simples (top-3) com duas barreiras.

    Barreira 1 (pré-filtro): score do top-1 abaixo do limiar de avaliacao/busca.json -> recusa sem chamar o LLM.
    Barreira 2: o LLM recusa seguindo as regras do prompt. Pós-checagem: id citado que não foi recuperado.
    """
    b = buscador()
    achados = b.buscar(pergunta, k=3)
    ids = [t["id"] for t, _ in achados]
    scores = [round(s, 4) for _, s in achados]
    if b.limiar is not None and (not achados or achados[0][1] < b.limiar):
        r = RespostaLLM(resposta=RECUSA, fonte=[], confianca=0.0, recusou=True, json_valido=True)
        return _saida(r, "pre_filtro", ids, scores)
    trechos = "\n\n".join(f"[{t['id']}]\n{t['texto']}" for t, _ in achados)
    r = gerar(SISTEMA_RAG, f"Trechos:\n\n{trechos}\n\nPergunta: {pergunta}")
    citacao_invalida = any(i not in ids for i in r.fonte)
    return _saida(r, "llm" if r.recusou else None, ids, scores, citacao_invalida)
