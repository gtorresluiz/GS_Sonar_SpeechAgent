"""Gera os resultados do agente_v2 (63 casos) e da validação (12 casos).

Rode da raiz do repositório, com o Ollama ligado:
    python avaliacao/rodar_v2_e_validacao.py

`avaliar()` retoma de onde parou: os casos já gravados em avaliacao/resultados/ são pulados.
Para rodar do zero, apague antes os arquivos listados em SAIDAS.

Observação: `agente_v2_c1_c3.jsonl` e `validacao_agente_v2_c1_c3.jsonl` são registros históricos da versão
intermediária (antes de C1b e C4). O código atual não reproduz essa versão; os arquivos ficam no repositório
como evidência do antes e depois.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "avaliacao"))

import avaliar as av  # noqa: E402
from sonar_ia import agente as ag  # noqa: E402

CASOS_VALIDACAO = RAIZ / "avaliacao" / "casos_validacao.jsonl"
SAIDAS = ["agente_v2.jsonl", "validacao_agente.jsonl", "validacao_agente_v2.jsonl"]


def main() -> None:
    teste = av.carregar_casos()
    validacao = av.carregar_casos(CASOS_VALIDACAO)

    av.avaliar("agente_v2", ag.agente_v2, teste)
    av.avaliar("validacao_agente", ag.agente, validacao)
    av.avaliar("validacao_agente_v2", ag.agente_v2, validacao)
    print("Pronto. Rode notebooks/06_placar_e_erros.ipynb para recalcular o placar.")


if __name__ == "__main__":
    main()
