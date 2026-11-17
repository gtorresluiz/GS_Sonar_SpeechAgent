# Placar das configurações (63 casos)

Modelo: `qwen2.5:3b` local (Ollama, temperatura 0, seed 42). Casos: `avaliacao/casos_teste.jsonl` (30 `texto`, 18 `rota`, 15 `nao_consta`). Resultados: `avaliacao/resultados/*.jsonl`; notebook `notebooks/06_placar_e_erros.ipynb`; gráficos `avaliacao/placar.png` e `avaliacao/roteador.png`.

Definições: **acerto** e **alucinação** valem sobre todos os casos do grupo; **recusa correta** só sobre os 15 `nao_consta`; **falsa recusa** sobre os casos que tinham resposta (30 `texto` + as 12 rotas com linha esperada); **citação correta** só sobre os 30 `texto`. Alucinação = não recusou e não acertou (inclui `nao_consta` respondido).

## Placar oficial

| config | acerto | alucinação | recusa correta | falsa recusa | JSON válido | citação correta | latência média |
|---|---|---|---|---|---|---|---|
| 1 sem_contexto (LLM sem base, sem instrução de recusa) | 0,238 | **0,762** | 0,067 | 0,000 | 1,00 | 0,00 | 0,74 s |
| 2 rag (top-3, duas barreiras) | 0,683 | **0,095** | 0,933 | 0,333 | 1,00 | 0,80 | 2,87 s |
| 3 agente (roteador + ferramentas) | **0,746** | 0,159 | 0,933 | 0,143 | 1,00 | 0,67 | 1,87 s |

### Por tipo

| tipo | config | acerto | alucinação | falsa recusa |
|---|---|---|---|---|
| texto (30) | 1 sem_contexto | 0,367 | 0,633 | 0,000 |
| texto (30) | 2 rag | **0,767** | 0,167 | 0,067 |
| texto (30) | 3 agente | 0,667 | 0,167 | 0,167 |
| rota (18) | 1 sem_contexto | 0,167 | 0,833 | 0,000 |
| rota (18) | 2 rag | 0,333 | 0,000 | **1,000 (esperado: o RAG não tem o GTFS)** |
| rota (18) | 3 agente | **0,722** | 0,222 | 0,083 |
| nao_consta (15) | 1 sem_contexto | 0,067 | 0,933 | n/a |
| nao_consta (15) | 2 rag | 0,933 | 0,067 | n/a |
| nao_consta (15) | 3 agente | 0,933 | 0,067 | n/a |

**Leia a linha `rota` do RAG com cuidado:** o RAG não consulta o GTFS, então não tem como responder rota. Os 0,333 de acerto são só os 6 casos sem linha esperada (em que recusar é a resposta certa), e os 12 casos com linha foram todos recusados (falsa recusa de 100%). Não é falha de implementação, é o limite da configuração.

Roteador do agente: acerta **57 de 63 (0,905)**. `texto` → `buscar_base`: 27/30; `rota` → `consultar_gtfs`: 16/18; `nao_consta` recusado: 14/15. Os 6 erros: `texto_23`, `texto_25`, `texto_29`, `rota_06` e `rota_14` caíram em "nenhuma", e `nao_consta_01` foi para `buscar_base` e alucinou.

Apêndice, config 1b (LLM sem contexto **com** instrução de recusa): acerto 0,460; alucinação 0,270; recusa correta 0,933; falsa recusa 0,405; JSON 1,00; citação 0,00; latência 0,63 s. A instrução faz o modelo recusar quase tudo que não sabe, mas também 40% do que tinha resposta.

## Interpretação: onde cada config ganha e perde, e por quê

**Config 1 (sem contexto) perde em quase tudo, e ganha só onde não faz nada.** Tem a menor latência (0,74 s) e zero falsa recusa, mas só porque quase nunca recusa (1 recusa em 63 casos): responde tudo com confiança. Resultado: alucinação de 76% (48 de 63) e 14 dos 15 `nao_consta` respondidos, por exemplo "Não há elevador na estação Adolfo Pinheiro da linha 5 Lilás" (confiança 1,0). Os 11 acertos em `texto` vêm de conhecimento geral ("posso entrar de ônibus com cão-guia?") ou de coincidência de palavra-chave. Um exemplo: no `texto_19` ("em que braço devo segurar?") ele "acerta" ao escrever "no braço oposto ao seu", que contém a palavra-chave mas diz outra coisa (o trecho fala em braço oposto à bengala). O acerto da config 1 é, portanto, otimista. Não tem fonte nenhuma (citação 0%).

**Config 2 (RAG) ganha em segurança e em texto.** É a menor alucinação (9,5%: 5 de `texto` e 1 de `nao_consta`) e o melhor acerto em `texto` (0,767). As duas barreiras funcionam: o pré-filtro barrou 6 dos 15 `nao_consta` e o LLM mais 8 (só o `nao_consta_01` passou). Cita a fonte certa em 80% dos `texto`. Perde em duas frentes. (a) Rota: sem GTFS, só recusa (falsa recusa 100% das rotas com linha). (b) Latência: 2,87 s em média, 4,5 s em `texto` (o prompt leva 3 trechos, até ~1.800 tokens). Os 6 erros que sobram são de leitura do modelo de 3B (`texto_30` inverte "exclusivo"; `texto_03` e `texto_04` copiam a coluna errada da tabela do Metrô) ou de busca (`texto_15`, `texto_19`).

**Config 3 (agente) ganha em cobertura, e paga em alucinação.** É o melhor acerto geral (0,746) e o único que responde rota (0,722 contra 0,333 do RAG): das 12 rotas com linha, acertou 10 (os 2 erros: falso positivo do GTFS no `rota_04` e o `rota_06`, que o roteador mandou para "nenhuma"); nos 6 casos sem linha esperada, acertou 3 (`rota_13`, `14` e `15`) e errou 3 (`rota_08`, `10` e `12`, respondendo com linhas que o GTFS devolveu por engano). Também é mais rápido que o RAG (1,87 s), porque as rotas são rápidas e a ferramenta é determinística. Mas a alucinação sobe para 15,9% (10 de 63, contra 6 do RAG): as 4 novas estão em rota (`rota_04`, `rota_08`, `rota_10`, `rota_12`).

**O agente herda a confiança da ferramenta.** O `consultar_gtfs` é determinístico, e isso dá à resposta uma aparência de certeza que ele não merece: o GTFS casa o nome do local também em `stop_desc` e em paradas num raio de 300 m, e então devolve "linhas" cujo embarque é "Av. Brás de Abreu" ou "R. Bom Pastor, 3047". O LLM só redige o que recebeu, com confiança alta; a única barreira desse caminho é "a ferramenta devolveu algo?". A pós-checagem `linha_inventada` só pega linha que **não** veio da ferramenta, e aqui as linhas vieram dela. O RAG, por não ter ferramenta, recusa as mesmas rotas e fica com alucinação 0 em rota (à custa de responder nada). O agente, sem uma barreira própria para a saída da ferramenta, troca "recusar" por "responder errado com confiança" nos 3 casos em que o GTFS erra e no `rota_10` (extração).

**Onde os três empatam:** JSON válido (100% nas três; o formato por esquema + pydantic não falhou) e recusa correta em `nao_consta` entre RAG e agente (0,933), porque o agente usa o mesmo fluxo e as mesmas barreiras para `buscar_base`.

### Cuidados com os números

- 63 casos: um caso vale 1,6 ponto percentual. As diferenças entre RAG e agente em `texto` (0,767 contra 0,667) são de 3 casos, todos de roteamento.
- Os casos foram escritos pelo mesmo autor que escolheu o limiar, o roteador e os prompts; não há conjunto separado ainda (ver "após correções").
- O acerto usa palavras-chave e pode ser generoso (config 1, `texto_19`) ou conservador (o agente às vezes não cita o código da linha).
- Um único modelo (`qwen2.5:3b`) e uma execução (temperatura 0, seed 42).
