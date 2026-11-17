"""Busca semântica na base: embeddings multilingual-e5-small + índice FAISS (produto interno)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from sonar_ia.base import RAIZ, carregar_trechos

MODELO = "intfloat/multilingual-e5-small"
CAMINHO_BUSCA_JSON = RAIZ / "avaliacao" / "busca.json"


class Buscador:
    """Indexa os trechos e devolve os mais parecidos com a pergunta.

    O e5 exige os prefixos "query: " (pergunta) e "passage: " (trecho). Os vetores são normalizados,
    então o produto interno do `IndexFlatIP` é o cosseno (score entre -1 e 1).
    `limiar` vem de avaliacao/busca.json (None se o arquivo ainda não existir).
    """

    def __init__(self, trechos: list[dict] | None = None, modelo: str = MODELO,
                 caminho_busca_json: Path = CAMINHO_BUSCA_JSON) -> None:
        self.trechos = trechos if trechos is not None else carregar_trechos()
        self.modelo_nome = modelo
        self.modelo = SentenceTransformer(modelo, device="cpu")
        self.limiar = self._carregar_limiar(caminho_busca_json)
        vetores = self._codificar([f"passage: {t['texto']}" for t in self.trechos])
        self.indice = faiss.IndexFlatIP(vetores.shape[1])
        self.indice.add(vetores)

    @staticmethod
    def _carregar_limiar(caminho: Path) -> float | None:
        if Path(caminho).exists():
            return json.loads(Path(caminho).read_text(encoding="utf-8")).get("limiar")
        return None

    def _codificar(self, textos: list[str]) -> np.ndarray:
        vetores = self.modelo.encode(textos, normalize_embeddings=True, batch_size=16, show_progress_bar=False)
        return np.asarray(vetores, dtype="float32")

    def buscar(self, pergunta: str, k: int = 3) -> list[tuple[dict, float]]:
        """Os k trechos mais parecidos, do maior para o menor score."""
        consulta = self._codificar([f"query: {pergunta}"])
        scores, posicoes = self.indice.search(consulta, min(k, len(self.trechos)))
        return [(self.trechos[i], float(s)) for s, i in zip(scores[0], posicoes[0]) if i >= 0]

    def deve_recusar(self, pergunta: str) -> bool:
        """True se o melhor score fica abaixo do limiar (a base não cobre a pergunta)."""
        if self.limiar is None:
            raise ValueError("limiar ainda não definido: rode o notebook 02 (avaliacao/busca.json)")
        achados = self.buscar(pergunta, k=1)
        return not achados or achados[0][1] < self.limiar


def limiar_prefiltro(scores_texto: list[float] | np.ndarray, max_falsas: int = 1) -> float:
    """Maior limiar que recusa no máximo `max_falsas` perguntas respondíveis (score < limiar).

    O limiar é só um pré-filtro: a segunda barreira é o LLM ("recuse se não estiver nos trechos").
    Com `max_falsas`=1 o limiar fica no segundo menor score dos casos `texto`, arredondado para baixo
    na 4ª casa para que esse caso ainda passe (a regra é `score >= limiar` passa).
    """
    ordenados = sorted(float(s) for s in scores_texto)
    if len(ordenados) <= max_falsas:
        return 0.0
    return math.floor(ordenados[max_falsas] * 1e4) / 1e4