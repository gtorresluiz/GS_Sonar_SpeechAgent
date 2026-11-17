# Erros e achados (registro corrente)

Registrados assim que aparecem. Os "5 erros reais" do relatório saem só da seção "Erros do sistema", ou seja, das saídas do sistema na avaliação.

## Problemas encontrados na base

1. **Acentos decompostos no `lei_caoguia`** (16/11/2026): o HTML do Planalto trazia caracteres em NFD ("a" + acento combinante). Uma busca por texto exato ("à pessoa") falhava no trecho. Correção aplicada em `base.py`: normalização NFC na limpeza do texto (HTML e PDF).
2. **`lbi_002` com o § 3º duplicado**: o trecho traz as duas redações do § 3º do art. 47 (incisos XVII e XX do art. 181 do CTB). A redação antiga não estava em tag de texto riscado e passou pelo filtro. Impacto baixo (nenhum caso de teste depende desse parágrafo). Correção possível: filtrar também estilo `text-decoration: line-through`.
3. **`metro_guia` descartada** (URL 404 e sem cópia no Wayback em 16/11/2026): sem fonte para piso tátil e acompanhamento no Metrô. O caso `nao_consta_13` depende disso. Os trechos da CPTM falam de "pisos e rotas táteis", mas só das estações novas da CPTM.
4. **Gabarito do 	exto_08 incompleto** (etapa 3): listava só metro_elev_007, mas o metro_elev_008 também traz Sapopemba, lado ímpar (rampa ou elevador, a mesma resposta). O chunking por linha repetia essa estação nos dois trechos por causa da sobreposição. Gabarito corrigido (007 e 008) em valiacao/gerar_casos.py.

## Erros do sistema

1. **Busca semântica não encontra o trecho certo por diferença de vocabulário (`texto_19`).** Pergunta: "quando eu for guiado por alguem, em que braço devo segurar?". O trecho esperado (`sptrans_manual_004`: "acompanhe a pessoa com deficiência visual oferecendo o braço oposto à bengala") fica fora do top-3 (recuperados: `sptrans_manual_005` 0,854, `sptrans_manual_011` 0,854, `sptrans_manual_003` 0,850). "Ser guiado" e "acompanhe… oferecendo o braço" são o mesmo conceito com palavras diferentes, um limite do e5-small. Correção proposta: modelo de embedding maior (e5-base ou bge-m3) ou expansão de consulta. Não corrigido.

Config 2 (RAG), saídas em `avaliacao/resultados/rag.jsonl`. 6 alucinações em 63 casos; as cinco abaixo (2 a 6) são as de maior valor para o relatório.

2. **Fonte inventada e estação trocada (`nao_consta_01`, Faria Lima, Linha 4).** O score do top-1 (0,873) passou do pré-filtro, e o LLM respondeu "Sim, a estação tem acesso à plataforma por elevador", citando `metro_elev_l1-azul_luz` (recuperado) e `metro_elev_l3-vermelha_lima`, um id que não existe (a pós-checagem marcou `citacao_invalida`). Correção proposta: tratar `citacao_invalida` como recusa; e checar se o nome da estação da pergunta aparece no texto dos trechos (barreira lexical por entidade), já que o embedding não separa estações.
3. **Inversão de sentido (`texto_30`, Táxi Acessível).** O trecho diz "exclusivo para pessoas com deficiência físico-motora"; o LLM respondeu "Sim, uma pessoa cega pode usar o táxi acessível da CPTM", com a fonte certa (`cptm_acess_001`). O modelo de 3B ignora a restrição de público. Correção proposta: modelo maior (`qwen2.5:7b-instruct` no Colab) e regra no prompt: "confira para quem o serviço é destinado antes de dizer sim".
4. **Resposta incompleta ou trocada em tabela (`texto_03` Ana Rosa, `texto_04` Armênia).** Para Ana Rosa o trecho diz "plataforma de elevação inclinada" e o LLM disse "há elevador para acesso à estação e à plataforma"; para Armênia o trecho diz "Em nível" (sem elevador nem rampa) e o LLM respondeu só "Elevador". Ele copia a coluna "acesso à plataforma" e ignora a de "acesso à estação". Correção proposta: reescrever a frase do chunk para dizer claramente "a entrada é em nível / por plataforma de elevação inclinada", ou usar a ferramenta determinística (agente).
5. **Trecho errado no top-1 vira resposta errada (`texto_15`, motorista deve parar para pessoa cega).** O top-1 foi `lei_caoguia_001` (0,865) e o certo, `sptrans_manual_005`, ficou em 2º (0,858). O LLM usou o primeiro e respondeu "o motorista é obrigado a parar para pessoas com deficiência visual acompanhadas de cão-guia". Correção proposta: re-ranqueamento ou modelo de embedding maior, e instruir o LLM a usar o trecho mais específico para a pergunta.
6. **Erro de busca vira alucinação (`texto_19`, braço oposto à bengala).** Consequência do erro 1: sem o `sptrans_manual_004`, o LLM inventou "segure no braço do guia para manter o contato seguro e seguro durante a viagem". Correção proposta: a mesma do erro 1 (embedding maior ou expansão de consulta).

Observações do placar do RAG:
- Falsa recusa de rota = 100% (18/18: 12 pelo LLM e 6 pelo pré-filtro): o RAG não tem o GTFS, então recusar é o comportamento esperado. A config 3 (agente com `consultar_gtfs`) deve resolver.
- Falsa recusa de `texto_09` pelo pré-filtro (score 0,852, abaixo do limiar 0,8537): era o caso que o critério de 1/30 já previa.

Config 3 (agente), saídas em `avaliacao/resultados/agente.jsonl`:

7. **Falsos positivos do GTFS viram resposta confiante (`rota_04`, `rota_08`, `rota_12`).** `consultar_gtfs` casa o nome do local também em `stop_desc` e em paradas num raio de 300 m: "Brás" → "Av. Brás de Abreu", "Bandeira" → "Parada Antônio Bandeira", "Pinheiros" → "Clube Pinheiros", e para terminais devolve paradas de rua (ex.: embarque em "R. Bom Pastor, 3047"). O agente redige com esses resultados sem desconfiar: no `rota_04` mistura as 3 linhas corretas com 2 ônibus que não fazem o trajeto (2582-10, 2769-10); no `rota_08` e no `rota_12`, onde não há linha direta confirmada, afirma uma linha de ônibus. A pós-checagem `linha_inventada` não pega, porque as linhas vieram da ferramenta. Correção proposta (em `gtfs.py`): casar só `stop_name` (não `stop_desc`), preferir estações e terminais, exigir que embarque e desembarque sejam o local pedido (não só a 300 m dele) e conferir o `route_long_name`.
8. **Extração de origem trocando o nome próprio (`rota_10`).** "terminal bandeira" virou "Terminal Bandeirantes", e o agente respondeu com as linhas de outro terminal (7267-10, 7272-10, ...). O modelo de 3B reescreve o nome em vez de copiar. Correção proposta: validar o nome extraído contra os nomes do GTFS (casamento aproximado) e, se não existir igual, recusar ou pedir confirmação; instruir o roteador a copiar o nome literalmente.
9. **Roteador escolhe "nenhuma" para pergunta respondível (`texto_23`, `texto_25`, `texto_29`, `rota_06`).** São 4 recusas indevidas (5 de 30 `texto` com falsa recusa no agente contra 2 no RAG). Correção proposta: mais exemplos no roteador, ou usar "nenhuma" só depois de `buscar_base` também falhar (as barreiras do RAG já protegem contra alucinação).

Observação de método: o agente às vezes não cita o código da linha ("Trem (CPTM) sentido ESTUDANTES"), então o acerto automático de rota (que procura o código) pode ser conservador nesses casos.

## 5 erros selecionados

Saídas copiadas de `avaliacao/resultados/*.jsonl` (modelo `qwen2.5:3b`, temperatura 0, seed 42). "Camada" é onde a falha nasce: busca, geração, ferramenta ou roteamento.

### Erro 1. Busca semântica não encontra o trecho certo (`texto_19`)
- **Pergunta:** "quando eu for guiado por alguem, em que braço devo segurar?"
- **Saída real (RAG e agente, iguais):** "Se você for guiado por alguém, segure no braço do guia para manter o contato seguro e seguro durante a viagem." (fonte ['sptrans_manual_005'], confiança 1.0, recusou=false); top-3 `sptrans_manual_005` 0.8537, `sptrans_manual_011` 0.8536, `sptrans_manual_003` 0.8501
- **Esperado:** O acompanhante deve oferecer o braço oposto ao da bengala para a pessoa com deficiência visual segurar, o que dá um trajeto menos acidentado. Trecho certo: `sptrans_manual_004` ("acompanhe a pessoa com deficiência visual oferecendo o braço oposto à bengala").
- **Camada:** busca (recuperação).
- **Causa:** vocabulário diferente para o mesmo conceito ("ser guiado" × "acompanhe… oferecendo o braço"). O e5-small não aproxima os dois e o trecho certo fica fora do top-3. Sem o trecho, o LLM inventou a resposta.
- **Correção proposta:** modelo de embedding maior (e5-base ou bge-m3) ou expansão de consulta ("guiar" → "acompanhar", "conduzir"); e, na geração, recusar quando nenhum trecho falar de guiar/acompanhar.

### Erro 2. Fonte inventada e estação trocada (`nao_consta_01`)
- **Pergunta:** "a estação faria lima da linha 4 amarela tem elevador?"
- **Saída real (RAG e agente, iguais):** "Sim, a estação tem acesso à plataforma por elevador." (fonte ['metro_elev_l1-azul_luz', 'metro_elev_l3-vermelha_lima'], confiança 1.0, recusou=false); top-3 `metro_elev_l1-azul_luz` 0.8733, `metro_elev_l3-vermelha_republica` 0.8658, `metro_elev_l3-vermelha_belem` 0.8624; `citacao_invalida=true` (`metro_elev_l3-vermelha_lima` não existe).
- **Esperado:** "Não consta na base de conhecimento." (a Linha 4-Amarela não está no PDF do Metrô).
- **Camada:** geração (barreira 2) e pós-checagem. O pré-filtro também deixou passar (score 0,873, acima do limiar 0,8537).
- **Causa:** o embedding trata "estação + elevador" como um tema só e recupera uma estação qualquer (`l1-azul_luz`, que cita "Conexão Linha 4-Amarela"); o LLM de 3B responde como se fosse a estação perguntada e ainda inventa um id de fonte. A pós-checagem detecta o id inválido, mas só marca `citacao_invalida`, sem mudar a resposta.
- **Correção proposta:** tratar `citacao_invalida` como recusa (barreira 3) e checar se o nome da estação da pergunta aparece no texto dos trechos recuperados.

### Erro 3. Inversão do sentido de "exclusivo" (`texto_30`)
- **Pergunta:** "uma pessoa cega pode usar o táxi acessivel da cptm?"
- **Saída real (RAG e agente, iguais):** "Sim, uma pessoa cega pode usar o táxi acessível da CPTM." (fonte ['cptm_acess_001'], confiança 1.0, recusou=false); top-3 `cptm_acess_001` 0.8993, `lbi_006` 0.8736, `sptrans_manual_012` 0.8652
- **Esperado:** Não. O Táxi Acessível da CPTM é um serviço gratuito e exclusivo para pessoas com deficiência físico-motora. Trecho: `cptm_acess_001` ("serviço gratuito e exclusivo para pessoas com deficiência físico-motora").
- **Camada:** geração (LLM de 3B). A busca acertou (top-1 `cptm_acess_001`, 0,899) e a citação está correta.
- **Causa:** o modelo não compara o público do serviço com o público da pergunta e responde "sim" com confiança 1,0.
- **Correção proposta:** modelo maior (`qwen2.5:7b-instruct`, no Colab T4) e regra no prompt: "antes de dizer sim, confira para quem o serviço é destinado".

### Erro 4. Falsos positivos do GTFS viram resposta confiante (`rota_04`, `rota_08`, `rota_12`)
- **rota_04:** "o que vai do brás ate o tatuapé?"
  - saída real do agente: "Você pode usar o Trem (CPTM) sentido ESTUDANTES ou o Trem (CPTM) sentido CALMON VIANA. Ou ainda, o Metrô sentido CORINTHIANS - ITAQUERA. Para uma opção mais rápida, use o ônibus 2582-10 sentido Term. Pq. D. Pedro Ii ou o ônibus 2769-10 sentido Metrô Tatuapé." (ferramenta `consultar_gtfs`, args {'origem': 'Brás', 'destino': 'Tatuapé'})
  - esperado: linhas CPTM L11, CPTM L12, METRÔ L3 (incorretas: 2582-10, 2769-10)
- **rota_08:** "qual onibus vai do terminal sacomã ate o terminal santo amaro?"
  - saída real do agente: "Use o ônibus 476A-10, sentido Term. Sto. Amaro, ele embarca na R. Bom Pastor e desembarca na Parada Da Paz, no sentido Santo Amaro." (ferramenta `consultar_gtfs`, args {'origem': 'Terminal Sacomã', 'destino': 'Terminal Santo Amaro'})
  - esperado: não há linha direta confirmada (476A-10, 477A-10, 477P-10 são falsos positivos)
- **rota_12:** "tem onibus direto do terminal santo amaro pro terminal lapa?"
  - saída real do agente: "Estão disponíveis os ônibus 875C-10 e 875C-1 para você, ambos no sentido Term. Lapa, partindo de R. Afonso Braz, 912." (ferramenta `consultar_gtfs`, args {'origem': 'Terminal Santo Amaro', 'destino': 'Terminal Lapa'})
  - esperado: não há linha direta confirmada (875C-1, 875C-10, 477P-10 são falsos positivos)
- **Camada:** ferramenta (`consultar_gtfs`).
- **Causa:** `encontrar_paradas` casa o nome do local também em `stop_desc` e acrescenta todas as paradas num raio de 300 m: "Brás" → "Av. Brás de Abreu", "Bandeira" → "Parada Antônio Bandeira", "Pinheiros" → "Clube Pinheiros"; para terminais, devolve paradas de rua (embarque em "R. Bom Pastor, 3047"). O agente redige com o que a ferramenta devolve; a pós-checagem `linha_inventada` não pega, porque as linhas vieram da ferramenta. É o "agente herda a confiança da ferramenta".
- **Correção proposta:** casar só `stop_name`; um local casa com o grupo de paradas mais denso (≤ 300 m), priorizando "Terminal" e "Estação" quando a pergunta tiver essas palavras; conferir o `route_long_name`. Medida na parte C (`agente_v2`).

### Erro 5. Roteador escolhe "nenhuma" para pergunta respondível (`texto_23`, `texto_25`, `texto_29`, `rota_06`, `rota_14`)
- **texto_23:** "quais documentos eu preciso levar pra me cadastrar no atende+?"
  - saída real: "Não consta na base de conhecimento." (ferramenta `nenhuma`, roteador: `{"ferramenta": "nenhuma", "origem": "", "destino": "", "linha": "", "parada": ""}`)
  - esperado: CPF (original e cópia), RG ou certidão de nascimento (original e cópia) e comprovante de endereço com CEP (original e cópia), além da Ficha de Avaliação Médica preenchida pelo médico.
- **texto_25:** "quantos por cento dos taxis tem que ser acessíveis?"
  - saída real: "Não consta na base de conhecimento." (ferramenta `nenhuma`, roteador: `{"ferramenta": "nenhuma", "origem": "", "destino": "", "linha": "", "parada": ""}`)
  - esperado: As frotas de empresas de táxi devem reservar 10% de seus veículos acessíveis à pessoa com deficiência.
- **texto_29:** "quantas estações da cptm são acessiveis?"
  - saída real: "Não consta na base de conhecimento." (ferramenta `nenhuma`, roteador: `{"ferramenta": "nenhuma", "origem": "", "destino": "", "linha": "", "parada": ""}`)
  - esperado: Das 41 estações da CPTM, 35 já possuem condições de acesso às pessoas com deficiência ou restrição de mobilidade.
- **rota_06:** "tem trem direto da lapa pro terminal pirituba?"
  - saída real: "Não consta na base de conhecimento." (ferramenta `nenhuma`, roteador: `{"ferramenta": "nenhuma", "origem": "Lapa", "destino": "Terminal Pirituba", "linha": "", "parada": ""}`)
  - esperado: linhas CPTM L07, N103-11, 8100-10, 8200-10, 8002-10 (incorretas: 9188-42, 8010-10)
- **rota_14:** "tem trem direto da luz ate osasco?"
  - saída real: "Não consta na base de conhecimento." (ferramenta `nenhuma`, roteador: `{"ferramenta": "nenhuma", "origem": "Luz", "destino": "Osasco", "linha": "", "parada": ""}`)
  - esperado: sem linha direta (recusar também serve)
- **Camada:** roteamento.
- **Causa:** o roteador de 3B, só com 6 exemplos, decide "nenhuma" (assunto fora de transporte) em perguntas curtas sobre números ou cadastro e em duas rotas. Quatro delas (`texto_23`, `25`, `29`, `rota_06`) eram respondíveis: viram falsa recusa (o RAG acertou `texto_23`, `25` e `29`). O `rota_14` (Luz → Osasco) recusa, que também é aceito, mas por acaso: a ferramenta nem foi consultada.
- **Correção proposta:** mais exemplos no roteador e, quando escolher "nenhuma", ainda rodar `buscar_base` se o score do top-1 passar do limiar (as barreiras do RAG já protegem contra alucinação). Medida na parte C (C3).

### Erro extra. Extração de origem trocando o nome próprio (`rota_10`)
- **Pergunta:** "que onibus vai do terminal bandeira ate o terminal princesa isabel?"
- **Saída real (agente):** "Você pode usar o ônibus 7267-10, 7272-10, 7281-10, 7903-10 ou 8700-21 para ir do Terminal Bandeirantes até o Terminal Princesa Isabel." (ferramenta `consultar_gtfs`, args {'origem': 'Terminal Bandeirantes', 'destino': 'Terminal Princesa Isabel'})
- **Esperado:** não há linha direta confirmada (origem esperada: "Terminal Bandeira").
- **Camada:** roteamento (extração de argumentos).
- **Causa:** o roteador escreveu "Terminal Bandeirantes" no lugar de "Terminal Bandeira" e o agente respondeu com as linhas de outro terminal.
- **Correção proposta:** validar o nome extraído contra os nomes do GTFS (casamento aproximado) e recusar se não existir igual.

### Resultado medido das correções (`agente_v2`, etapa 6, parte C)

C1 = GTFS só por `stop_name` com grupo de paradas (`gtfs.py`, modo `v2`); C2 = `citacao_invalida` → recusa; C3 = roteador "nenhuma" + top-1 da busca ≥ limiar → `buscar_base`.

| erro | casos | antes | depois | correção |
|---|---|---|---|---|
| 1 busca | texto_19 | erra | erra | nenhuma (precisa de embedding maior ou expansão de consulta) |
| 2 id inventado | nao_consta_01 | erra | corrigido | C2 |
| 3 inversão de "exclusivo" | texto_30 | erra | erra | nenhuma (modelo de 3B) |
| 4 falsos positivos do GTFS | rota_04, rota_08, rota_12 | erram | corrigidos | C1 |
| 5 roteador → nenhuma | texto_23, texto_25, texto_29 | erram | corrigidos | C3 |
| 5 roteador → nenhuma | rota_06 | erra | erra | C3 aciona, mas o RAG não tem o GTFS e recusa |
| extra: extração | rota_10 | erra | corrigido | C1 (a extração ainda erra o nome, mas a ferramenta não casa e o agente recusa) |

Efeito colateral do C1: `rota_09` (Capelinha → Terminal Santo Amaro) passou de acerto a erro, porque no GTFS os terminais se chamam "Terminal Sto. Amaro, 1" e casar só `stop_name` não acha "Santo Amaro". Correção possível, não feita: normalizar as abreviações do GTFS (Sto., Sta., Pq., Vl., Jd.).

### Erros extras encontrados na medição

- **`recusou=true` com resposta no texto (`nao_consta_12` no RAG, no agente e no agente_v2; `val_nao_consta_05` na validação).** O modelo marca a recusa no campo, mas escreve uma resposta ("Para conseguir um cão-guia, é necessário se inscrever em um centro de treinamento…"). A métrica conta recusa correta e o usuário ouve uma resposta possivelmente inventada. Por isso a recusa correta dos placares é otimista em 1 caso de 15 (0,933 → 0,867 no RAG e no agente). Correção proposta: normalizar a saída (se `recusou=true`, forçar `resposta = "Não consta na base de conhecimento."` e `fonte = []`) ou tratar a divergência como alucinação.
- **Variação entre execuções.** O mesmo `agente` rodado duas vezes deu texto diferente em 16 dos 63 casos (mesmos trechos e mesma ferramenta) e acerto de 0,746 e 0,730 (`agente_rerun.jsonl`). O modelo roda com temperatura 0 e seed 42, mas o Ollama não é totalmente determinístico. As comparações abaixo de ~1 caso (1,6 pp) são ruído.