# Sonar — Assistente de Mobilidade Acessível (GenAI for Engineering · FIAP GS)

## Contexto
O Sonar é um app de acessibilidade para pessoas cegas no transporte público de São Paulo.
Este repositório é a **entrega da disciplina Generative AI for Engineering**: o componente de
Inteligência do Sonar, um assistente que responde perguntas sobre transporte **com fonte, sem inventar**.

Exemplos de perguntas:
- "Qual linha vai do Terminal A ao Metrô B?"
- "A estação X tem elevador?"
- "Posso embarcar com cão-guia?"

Prazo: **19/11/2026 às 23h55** (link do repositório no Teams). Desenvolvedor único.

## Regras inegociáveis
1. **O LLM do produto é LOCAL e pequeno (3B a 8B)**: `qwen2.5:3b` (CPU, via Ollama) ou `qwen2.5:7b-instruct` (Colab T4).
   Nunca chamar APIs de LLM em nuvem (Anthropic, OpenAI, Gemini) dentro do código do produto ou da avaliação.
   Assistentes de código (Claude Code, Gemini no Antigravity) só ajudam a ESCREVER o código.
2. **Toda resposta do assistente é JSON válido** neste formato:
   ```json
   {"resposta": "...", "fonte": ["id_trecho"], "confianca": 0.0, "recusou": false}
   ```
   Se a informação não está na base (similaridade abaixo do limiar), `recusou: true` e
   `resposta: "Não consta na base de conhecimento."`. Nunca inventar.
3. **Todo trecho da base tem metadados**: `id, fonte, url, formato, licenca, data_coleta, texto`.
4. **Notebooks são entregáveis**: rodar do início ao fim e SALVAR as saídas antes do commit.
5. **Reprodutibilidade**: seeds fixas, versões em `requirements.txt`, caminhos relativos.
6. Não inventar dados de linhas, estações ou leis. Se não tiver a fonte, deixar TODO e avisar.

## Estrutura do repositório
```
base/
  brutos/           # HTML/PDF/CSV coletados (ou o link, se a licença não permitir copiar)
  trechos.jsonl     # trechos com metadados
  fontes.md         # tabela: fonte, formato, licença, nº de trechos
avaliacao/
  casos_teste.jsonl # pergunta, resposta_esperada, trecho_esperado, tipo (respondivel | nao_consta)
  resultados/       # saídas de cada configuração
  placar.md         # placar interpretado das 3 configurações
notebooks/
  01_coleta_e_chunking.ipynb
  02_busca_recall_limiar.ipynb
  03_config1_sem_contexto.ipynb
  04_config2_rag.ipynb
  05_config3_agente.ipynb
  06_placar_e_erros.ipynb
src/sonar_ia/
  base.py           # carregar trechos
  busca.py          # embeddings + FAISS + limiar
  llm.py            # cliente Ollama local
  rag.py            # config 2
  agente.py         # config 3 (ferramentas: buscar_base, consultar_gtfs, previsao_onibus)
  esquema.py        # pydantic do JSON de saída
api/
  main.py           # FastAPI: POST /assistente/perguntar
voz/
  stt_demo.py       # opcional: faster-whisper -> API (demo, não pontua)
RELATORIO.md
README.md
```

## Componentes técnicos
- **Embeddings**: `intfloat/multilingual-e5-small` (prefixos `query:` / `passage:`), índice FAISS.
- **Busca**: medir recall@1 e recall@3 em `casos_teste.jsonl` (só perguntas respondíveis).
- **Limiar**: escolher pela distribuição de similaridade respondíveis × não consta; maximizar o F1 da recusa; salvar o gráfico.
- **3 configurações**: (1) LLM sem contexto, (2) RAG simples top-3, (3) agente com ferramentas.
- **Ferramenta GTFS**: determinística, sobre `stops.txt`, `routes.txt`, `trips.txt` e `stop_times.txt` da SPTrans.
  A previsão Olho Vivo é só demo (dado em tempo real, sem gabarito fixo).
- **Métricas do placar**: acurácia, taxa de alucinação, recusa correta (nas não consta),
  % JSON válido, citação correta da fonte, latência média.

## Pontuação (guia de prioridade)
| Item | Pts |
|---|---|
| Tarefa + casos de teste com gabarito, incluindo "não consta" | 0,5 |
| Base em trechos com fonte | 1,0 |
| Busca com recall@1/@3 e limiar justificado | 1,0 |
| Geração fundamentada: JSON válido, citação, recusa | 2,0 |
| Especialização (agente) comparada ao RAG | 2,0 |
| Placar das 3 configurações interpretado | 2,0 |
| 5 erros reais com proposta de correção | 1,0 |
| README e reprodutibilidade | 0,5 |

## Como trabalhar
- Fazer uma etapa por vez, na ordem dos notebooks. Ao final de cada etapa: rodar, conferir a saída e commitar.
- Código e comentários em português. Funções pequenas e com type hints.
- Registrar erros encontrados em `avaliacao/erros.md` assim que aparecerem (viram os "5 erros reais").
