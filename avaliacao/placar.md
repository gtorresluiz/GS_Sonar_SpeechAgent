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


- **Variação entre execuções.** Rodei o `agente` original uma segunda vez (`avaliacao/resultados/agente_rerun.jsonl`): mesma ferramenta e mesmos trechos recuperados nos 63 casos, mas o texto da resposta mudou em 16 e o acerto mudou em 1 (`texto_16`). Acerto geral: 0,746 na execução oficial e 0,730 na repetição. O Ollama não é 100% determinístico mesmo com temperatura 0 e seed 42, então diferenças de 1 caso (1,6 pp) são ruído.
- **A recusa correta é um pouco otimista.** A métrica lê o campo `recusou`. No `nao_consta_12` (conseguir cão-guia) o RAG, o agente e o agente_v2 marcam `recusou=true` mas escrevem uma resposta ("Para conseguir um cão-guia, é necessário se inscrever em um centro de treinamento…"). Contando só recusas em que o texto também recusa, a recusa correta cai de 0,933 para 0,867 (RAG e agente) e de 1,000 para 0,933 (agente_v2). O mesmo acontece na validação (`val_nao_consta_05`).

## Após as correções (agente_v2: C1 GTFS, C2 citação inválida → recusa, C3 fallback do roteador)

As três correções foram implementadas sem alterar o `agente` original nem o gabarito (`avaliacao/resultados/agente_v2.jsonl`, notebook 06, seções 7 e 8).

| | agente (original) | agente_v2 |
|---|---|---|
| acerto | 0,746 | **0,841** |
| alucinação | 0,159 | **0,095** |
| recusa correta | 0,933 | 1,000 |
| falsa recusa | 0,143 | 0,095 |
| JSON válido | 1,00 | 1,00 |
| citação correta | 0,667 | 0,800 |
| latência média | 1,87 s | 3,57 s |
| acerto em texto / rota / nao_consta | 0,667 / 0,722 / 0,933 | 0,733 / 0,889 / 1,000 |

Resultado nos erros selecionados:

| erro | casos | antes | depois |
|---|---|---|---|
| 1 busca | texto_19 | erra | erra (sem correção, precisa de embedding melhor) |
| 2 id inventado | nao_consta_01 | erra | **corrigido** (C2) |
| 3 inversão de "exclusivo" | texto_30 | erra | erra (limite do modelo de 3B) |
| 4 falsos positivos do GTFS | rota_04, rota_08, rota_12 | erram | **corrigidos** (C1) |
| 5 roteador → "nenhuma" | texto_23, texto_25, texto_29 | erram | **corrigidos** (C3) |
| 5 roteador → "nenhuma" | rota_06 | erra | erra (C3 aciona, mas o RAG não tem o GTFS e recusa) |
| 5 roteador → "nenhuma" | rota_14 | acerta (recusa) | acerta |
| extra: extração | rota_10 | erra | **corrigido** (a extração ainda sai "Terminal Bandeirantes", mas agora a ferramenta não casa e o agente recusa) |

Mudaram de acerto 10 casos: 8 passaram a acertar e 2 passaram a errar, saldo +6.
- `rota_09` (Capelinha → Terminal Santo Amaro) **piorou por causa do C1**: no GTFS os terminais se chamam "Terminal Sto. Amaro, 1", então casar só `stop_name` não acha "Santo Amaro"; a v1 achava pelo `stop_desc`. Correção possível (não feita): normalizar abreviações do GTFS (Sto., Sta., Pq., Vl., Jd.).
- `texto_16` piorou **sem relação com as correções**: é a variação entre execuções descrita acima (mesmos trechos, texto diferente).
- O C1 precisou de um ajuste durante a implementação: a regra "grupo mais denso" escolhia a avenida em vez da estação (quebrava o teste Tucuruvi → Jabaquara), então entre grupos o que tem nome igual ao pedido vem primeiro. Os 3 testes originais e os mesmos 3 no modo v2 passam.
- A latência sobe porque o C3 manda mais perguntas para o fluxo do RAG (3 trechos no prompt).

### Aviso: a melhora no conjunto de teste é otimista

As correções foram desenhadas olhando as falhas destes mesmos 63 casos, e o C1 foi ajustado depois de um teste quebrar. Parte do +0,095 de acerto é ajuste ao conjunto. Além disso, a variação entre execuções é de cerca de ±1 caso, e três dos 8 casos "corrigidos" (`rota_08`, `rota_10`, `rota_12`) viram recusa por falta de linha direta, que é o gabarito mas também o jeito mais fácil de acertar.

### Validação (`avaliacao/casos_validacao.jsonl`, 12 casos, escritos à parte)

Separadamente, nos 12 casos (4 `texto`, 3 `rota`, 5 `nao_consta`):

| | acerto | alucinação | recusa correta | falsa recusa | JSON válido | citação correta |
|---|---|---|---|---|---|---|
| agente (original) | 0,750 | 0,167 | 1,000 | 0,143 | 1,00 | 1,000 |
| agente_v2 | 0,750 | 0,167 | 1,000 | 0,143 | 1,00 | 1,000 |

**Na validação o agente_v2 empata com o original (9 de 12 nos dois, mesmos casos certos e errados).** Nenhuma das correções mudou um resultado: o único caso que mudou de ferramenta (`val_nao_consta_03`, "nenhuma" → `buscar_base` pelo C3) continuou recusando. Os erros são os mesmos nos dois: `val_texto_01` (Anhangabaú: responde só "elevador", faltando a rampa da entrada), `val_rota_01` (a extração trocou os locais: "Fradique Coutinho" → "Vila São João"; falsa recusa) e `val_rota_03` (Chácara Klabin → Santa Cruz: diz que há trem direto mas sem citar a linha 5, e pelo sentido "Capão Redondo"). Ou seja, o ganho de +0,095 do conjunto de teste **não apareceu** na validação; com 12 casos a validação é muito pequena (um caso = 8 pp) para concluir que as correções não generalizam, mas também não confirma que generalizam. A recusa correta de 1,000 da validação tem o mesmo problema do conjunto de teste: no `val_nao_consta_05` o modelo marca `recusou=true` mas escreve "Não, você não pode trocar de linha sem pagar novamente…", então a recusa "de verdade" é 4 de 5.