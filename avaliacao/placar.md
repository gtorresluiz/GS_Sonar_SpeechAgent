# Placar das configurações (63 casos)

Modelo: `qwen2.5:3b` local (Ollama, temperatura 0, seed 42). Casos: `avaliacao/casos_teste.jsonl` (30 `texto`, 18 `rota`, 15 `nao_consta`). Resultados: `avaliacao/resultados/*.jsonl`; notebook `notebooks/06_placar_e_erros.ipynb`; gráficos `avaliacao/placar.png` e `avaliacao/roteador.png`.

Definições: **acerto** e **alucinação** valem sobre todos os casos do grupo; **recusa correta** só sobre os 15 `nao_consta`; **falsa recusa** sobre os casos que tinham resposta (30 `texto` + as 12 rotas com linha esperada); **citação correta** só sobre os 30 `texto`. Alucinação = não recusou e não acertou (inclui `nao_consta` respondido).

## Métrica de recusa: antiga × estrita

- **Antiga:** é recusa quando o campo `recusou` é `true`.
- **Estrita (a oficial deste placar):** só é recusa se `recusou=true` **e** o texto da resposta é uma recusa. Um caso com `recusou=true` e resposta afirmativa é tratado como **resposta** (acerta ou alucina pelo que foi escrito).

**Por que a estrita:** o app **lê a resposta em voz alta** para uma pessoa cega. Ela ouve o texto, não o campo `recusou`. No `nao_consta_12` ("como faço pra conseguir um cão-guia, quanto custa?") o RAG e o agente marcam `recusou=true`, mas a resposta é "Para conseguir um cão-guia, é necessário se inscrever em um centro de treinamento autorizado. O custo varia dependendo do centro, mas geralmente inclui taxas de inscrição…". A pessoa ouve uma resposta inventada, e a métrica antiga a contava como recusa correta. As métricas foram recalculadas sobre os jsonl já gravados, sem rodar o LLM de novo (`avaliar.reavaliar`).

| config | recusa correta antiga → estrita | alucinação antiga → estrita | acerto antiga → estrita |
|---|---|---|---|
| 1 sem_contexto | 0,067 → 0,067 | 0,762 → 0,762 | 0,238 → 0,238 |
| 2 rag | 0,933 → **0,867** | 0,095 → **0,111** | 0,683 → **0,667** |
| 3 agente | 0,933 → **0,867** | 0,159 → **0,175** | 0,746 → **0,730** |

Só o `nao_consta_12` muda (RAG e agente). Na config 1, `nao_consta_06` e `nao_consta_08` têm `recusou=false` mas o texto é uma recusa ("Não tenho informações sobre…"); a regra estrita, como definida, não os conta como recusa, o que soma 2 casos à alucinação da config 1 (se fossem contados, 0,762 cairia para 0,730).

## Placar oficial (métrica estrita)

| config | acerto | alucinação | recusa correta | falsa recusa | JSON válido | citação correta | latência média |
|---|---|---|---|---|---|---|---|
| 1 sem_contexto (LLM sem base, sem instrução de recusa) | 0,238 | **0,762** | 0,067 | 0,000 | 1,00 | 0,00 | 0,74 s |
| 2 rag (top-3, duas barreiras) | 0,667 | **0,111** | 0,867 | 0,333 | 1,00 | 0,80 | 2,87 s |
| 3 agente (roteador + ferramentas) | **0,730** | 0,175 | 0,867 | 0,143 | 1,00 | 0,67 | 1,87 s |

### Por tipo (métrica estrita)

| tipo | config | acerto | alucinação | falsa recusa |
|---|---|---|---|---|
| texto (30) | 1 sem_contexto | 0,367 | 0,633 | 0,000 |
| texto (30) | 2 rag | **0,767** | 0,167 | 0,067 |
| texto (30) | 3 agente | 0,667 | 0,167 | 0,167 |
| rota (18) | 1 sem_contexto | 0,167 | 0,833 | 0,000 |
| rota (18) | 2 rag | 0,333 | 0,000 | **1,000 (esperado: o RAG não tem o GTFS)** |
| rota (18) | 3 agente | **0,722** | 0,222 | 0,083 |
| nao_consta (15) | 1 sem_contexto | 0,067 | 0,933 | n/a |
| nao_consta (15) | 2 rag | 0,867 | 0,133 | n/a |
| nao_consta (15) | 3 agente | 0,867 | 0,133 | n/a |

**Leia a linha `rota` do RAG com cuidado:** o RAG não consulta o GTFS, então não tem como responder rota. Os 0,333 de acerto são só os 6 casos sem linha esperada (em que recusar é a resposta certa), e os 12 casos com linha foram todos recusados (falsa recusa de 100%). Não é falha de implementação, é o limite da configuração.

Roteador do agente (métrica estrita): acerta **56 de 63 (0,889)**. `texto` → `buscar_base`: 27/30; `rota` → `consultar_gtfs`: 16/18; `nao_consta` recusado de verdade: 13/15. Os 7 erros: `texto_23`, `texto_25`, `texto_29`, `rota_06` e `rota_14` caíram em "nenhuma"; `nao_consta_01` e `nao_consta_12` foram para `buscar_base` e responderam.

Apêndice, config 1b (LLM sem contexto **com** instrução de recusa): acerto 0,460; alucinação 0,270; recusa correta 0,933; falsa recusa 0,405; JSON 1,00; citação 0,00; latência 0,63 s (idêntica nas duas métricas). A instrução faz o modelo recusar quase tudo que não sabe, mas também 40% do que tinha resposta.

## Interpretação: onde cada config ganha e perde, e por quê

**Config 1 (sem contexto) perde em quase tudo, e ganha só onde não faz nada.** Tem a menor latência (0,74 s) e zero falsa recusa, mas só porque quase nunca recusa (1 recusa em 63 casos): responde tudo com confiança. Resultado: alucinação de 76% (48 de 63) e 14 dos 15 `nao_consta` respondidos, por exemplo "Não há elevador na estação Adolfo Pinheiro da linha 5 Lilás" (confiança 1,0). Os 11 acertos em `texto` vêm de conhecimento geral ("posso entrar de ônibus com cão-guia?") ou de coincidência de palavra-chave: no `texto_19` ("em que braço devo segurar?") ele "acerta" ao escrever "no braço oposto ao seu", que contém a palavra-chave mas diz outra coisa (o trecho fala em braço oposto à bengala). O acerto da config 1 é, portanto, otimista. Não tem fonte nenhuma (citação 0%).

**Config 2 (RAG) ganha em segurança e em texto.** É a menor alucinação (11,1%: 5 de `texto` e 2 de `nao_consta`, `nao_consta_01` e `nao_consta_12`) e o melhor acerto em `texto` (0,767). As duas barreiras funcionam: o pré-filtro barrou 6 dos 15 `nao_consta` e o LLM mais 7 (13 recusas de verdade; `nao_consta_01` e `nao_consta_12` passaram). Cita a fonte certa em 80% dos `texto`. Perde em duas frentes. (a) Rota: sem GTFS, só recusa (falsa recusa 100% das rotas com linha). (b) Latência: 2,87 s em média, 4,5 s em `texto` (o prompt leva 3 trechos, até ~1.800 tokens). Os erros que sobram são de leitura do modelo de 3B (`texto_30` inverte "exclusivo"; `texto_03` e `texto_04` copiam a coluna errada da tabela do Metrô) ou de busca (`texto_15`, `texto_19`).

**Config 3 (agente) ganha em cobertura, e paga em alucinação.** É o melhor acerto geral (0,730) e o único que responde rota (0,722 contra 0,333 do RAG): das 12 rotas com linha, acertou 10 (os 2 erros: falso positivo do GTFS no `rota_04` e o `rota_06`, que o roteador mandou para "nenhuma"); nos 6 casos sem linha esperada, acertou 3 (`rota_13`, `14` e `15`) e errou 3 (`rota_08`, `10` e `12`, respondendo com linhas que o GTFS devolveu por engano). Também é mais rápido que o RAG (1,87 s), porque as rotas são rápidas e a ferramenta é determinística. Mas a alucinação sobe para 17,5% (11 de 63, contra 7 do RAG): as 4 de rota (`rota_04`, `08`, `10`, `12`) são a diferença.

**O agente herda a confiança da ferramenta.** O `consultar_gtfs` é determinístico, e isso dá à resposta uma aparência de certeza que ele não merece: o GTFS casa o nome do local também em `stop_desc` e em paradas num raio de 300 m, e então devolve "linhas" cujo embarque é "Av. Brás de Abreu" ou "R. Bom Pastor, 3047". O LLM só redige o que recebeu, com confiança alta; a única barreira desse caminho é "a ferramenta devolveu algo?". A pós-checagem `linha_inventada` só pega linha que **não** veio da ferramenta, e aqui as linhas vieram dela. O RAG, por não ter ferramenta, recusa as mesmas rotas e fica com alucinação 0 em rota (à custa de responder nada). O agente, sem uma barreira própria para a saída da ferramenta, troca "recusar" por "responder errado com confiança".

**Onde os três empatam:** JSON válido (100% nas três; o formato por esquema + pydantic não falhou) e recusa correta em `nao_consta` entre RAG e agente (0,867), porque o agente usa o mesmo fluxo e as mesmas barreiras para `buscar_base`.

### Cuidados com os números

- 63 casos: um caso vale 1,6 ponto percentual. A diferença entre RAG e agente em `texto` (0,767 contra 0,667) são 3 casos, todos de roteamento.
- **Ruído entre execuções: cerca de 1 caso.** Rodei o `agente` original uma segunda vez (`resultados/agente_rerun.jsonl`): mesma ferramenta e mesmos trechos recuperados nos 63 casos, mas o texto da resposta mudou em 16 e o acerto mudou em 1 (`texto_16`). Acerto (métrica antiga): 0,746 na execução oficial e 0,730 na repetição. O Ollama não é 100% determinístico mesmo com temperatura 0 e seed 42.
- Os casos foram escritos pelo mesmo autor que escolheu o limiar, o roteador e os prompts; o conjunto separado está na validação, mais abaixo.
- O acerto usa palavras-chave e pode ser generoso (config 1, `texto_19`) ou conservador (o agente às vezes não cita o código da linha).
- Um único modelo (`qwen2.5:3b`).

## Após as correções (agente_v2: C1, C1b, C2, C3, C4)

Implementadas sem alterar o `agente` original nem o gabarito (`avaliacao/resultados/agente_v2.jsonl`, versão final; `agente_v2_c1_c3.jsonl`, a execução anterior sem C1b e C4):

- **C1 (`gtfs.py` modo `v2`):** casa só `stop_name`; o local casa com o grupo de paradas mais denso (≤ 300 m), com prioridade para "Terminal"/"Estação" e, ajuste feito ao ver o teste Tucuruvi → Jabaquara quebrar, preferência por nome igual ao pedido.
- **C1b:** normaliza abreviações do GTFS antes de casar (Sto., Sta., Pq., Vl., Jd., Term., Est.).
- **C2:** `citacao_invalida` → recusa.
- **C3:** roteador "nenhuma" + top-1 da busca ≥ limiar (0,8537) → `buscar_base`.
- **C4:** `recusou=true` → resposta "Não consta na base de conhecimento." (mantém "Não tenho previsão em tempo real agora.").

Métrica estrita nos 63 casos:

| | agente (original) | v2 (C1-C3) | v2 final (C1b+C4) |
|---|---|---|---|
| acerto | 0,730 | **0,825** | **0,825** |
| alucinação | 0,175 | 0,111 | 0,127 |
| recusa correta | 0,867 | 0,933 | 1,000 |
| falsa recusa | 0,143 | 0,095 | 0,071 |
| JSON válido | 1,00 | 1,00 | 1,00 |
| citação correta | 0,667 | 0,800 | 0,800 |
| latência média | 1,87 s | 3,57 s | 3,60 s |
| acerto texto / rota / nao_consta | 0,667 / 0,722 / 0,867 | 0,733 / 0,889 / 0,933 | 0,733 / 0,833 / 1,000 |

Erro selecionado × antes × depois (agente original → v2 final):

| erro | casos | antes | depois | correção |
|---|---|---|---|---|
| 1 busca | texto_19 | erra | erra | nenhuma (precisa de embedding melhor) |
| 2 id inventado | nao_consta_01 | erra | **corrigido** | C2 |
| 3 inversão de "exclusivo" | texto_30 | erra | erra | nenhuma (limite do 3B) |
| 4 falsos positivos GTFS | rota_04, rota_12 | erram | **corrigidos** | C1 |
| 4 falsos positivos GTFS | rota_08 | erra | erra | ver nota abaixo |
| 5 roteador → "nenhuma" | texto_23, 25, 29 | erram | **corrigidos** | C3 |
| 5 roteador → "nenhuma" | rota_06 | erra | erra | C3 aciona, mas o RAG não tem o GTFS e recusa |
| 5 roteador → "nenhuma" | rota_14 | acerta | acerta | n/a |
| extra: extração | rota_10 | erra | **corrigido** | C1 (a extração ainda erra o nome, mas a ferramenta não casa e o agente recusa) |
| efeito colateral do C1 | rota_09 | acerta (v1) → erra (C1-C3) | acerta | **C1b** ("Terminal Sto. Amaro") |
| `recusou=true` com resposta | nao_consta_12 | erra | **corrigido** | C4 |
| ruído de execução | texto_16 | acerta | erra | nenhuma (variação do LLM) |

Do agente original ao v2 final mudaram de acerto 10 casos: 8 passaram a acertar (`texto_23`, `25`, `29`, `rota_04`, `10`, `12`, `nao_consta_01`, `nao_consta_12`) e 2 a errar (`texto_16`, ruído; `rota_07`, efeito colateral da C1b). Saldo +6 (46 → 52 acertos).

**Efeitos da C1b que merecem atenção:**
- **`rota_07` (Pinheiros → Santo Amaro) passou a errar.** Com as abreviações expandidas, "Santo Amaro" casa dois grupos com nome igual ao pedido (a estação da CPTM e o terminal de ônibus "Terminal Sto. Amaro"), e a ferramenta fica com o mais denso (o terminal), perdendo o trem da Linha 9. A resposta passou a ser "Não há linhas de trem disponíveis para você". A correção é a mesma família do C1: para um local sem "Terminal" na pergunta, preferir a estação.
- **`rota_08` (Sacomã → Terminal Santo Amaro): o gabarito merece revisão.** Com a C1b a ferramenta devolve `476A-10` ("Ipiranga - Term. Sto. Amaro") embarcando em "Terminal Sacomã" e desembarcando em "Terminal Sto. Amaro, 1": os dois são os terminais pedidos. O gabarito (sem linha direta) foi verificado olhando as paradas de rua que o v1 devolvia ("R. Bom Pastor, 3047"); com os terminais certos a linha parece de fato fazer o trajeto. O gabarito **não foi alterado** (decisão sua), então o caso continua contado como erro.

### Aviso: a melhora no conjunto de teste é otimista

As correções foram desenhadas olhando as falhas destes mesmos 63 casos, e o C1 foi ajustado depois de um teste quebrar. Parte do +0,095 de acerto é ajuste ao conjunto. A variação entre execuções é de cerca de ±1 caso. E três dos casos "corrigidos" (`rota_10`, `rota_12`, mais o `rota_08` na versão C1-C3) viram recusa por falta de linha direta, que é o gabarito mas também o jeito mais fácil de acertar.

### Validação (`avaliacao/casos_validacao.jsonl`, 12 casos escritos à parte; métrica estrita)

| | acerto | alucinação | recusa correta | falsa recusa | JSON válido | citação correta |
|---|---|---|---|---|---|---|
| agente (original) | 0,667 | 0,250 | 0,800 | 0,143 | 1,00 | 1,000 |
| v2 (C1-C3) | 0,667 | 0,250 | 0,800 | 0,143 | 1,00 | 1,000 |
| v2 final (C1b+C4) | 0,667 | 0,250 | 0,800 | 0,143 | 1,00 | 1,000 |

(Pela métrica antiga o acerto era 0,750 nos dois primeiros: o `val_nao_consta_05` marcava `recusou=true` com a resposta "Não, você não pode trocar de linha sem pagar novamente…", e a estrita a conta como alucinação.)

**Leitura.** Os três agentes dão o mesmo resultado na validação (8 de 12): as correções **resolvem os padrões que atacaram** (falsos positivos do GTFS, roteador "nenhuma", id de fonte inventado, `recusou=true` com resposta) e nenhum desses padrões aparece nos 12 casos novos. A validação mostra **erros de tipos novos**, que nenhuma correção cobre:
- `val_rota_01` (Luz → Fradique Coutinho): **troca de origem e destino na extração**: o roteador extraiu origem "Fradique Coutinho" e destino "Vila São João" (que não está na pergunta); a ferramenta não achou e o agente recusou (falsa recusa).
- `val_texto_01` (Anhangabaú tem elevador?): **resposta parcial**: diz só "elevador" para a plataforma e omite que a entrada é por rampa.
- `val_rota_03` (Chácara Klabin → Santa Cruz): diz que existe trem direto sem citar a linha 5 (correta na substância, o acerto automático exige o código da linha).
- `val_nao_consta_05` (trocar para a linha Lilás sem pagar de novo): responde "Não, você não pode trocar…" (alucinação); na versão final o modelo nem marca `recusou`, então o C4 não atua.

Com 12 casos (um caso = 8 pp) a validação não prova que as correções não generalizam, mas também não mostra ganho: o +0,095 do conjunto de teste **não aparece** nela, como se esperava de um ajuste feito sobre aqueles mesmos casos.
