# Fontes da base de conhecimento

> Tabela exigida no relatório: fonte, formato, licença e nº de trechos.
> A coluna "Nº de trechos" é preenchida automaticamente pelo notebook 01.

| ID | Fonte | URL | Formato | Licença / termos | Responde a | Nº de trechos |
|---|---|---|---|---|---|---|
| lbi | Lei 13.146/2015 (Lei Brasileira de Inclusão), só os capítulos de acessibilidade e transporte (arts. 46 a 52) | https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13146.htm | HTML | Texto legal, sem proteção autoral (Lei 9.610/98, art. 8º, IV) | direitos no transporte, prioridade | 7 |
| lei_caoguia | Lei 11.126/2005 (cão-guia) | https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2005/lei/l11126.htm | HTML | Texto legal, sem proteção autoral | "posso embarcar com cão-guia?" | 4 |
| dec_caoguia | Decreto 5.904/2006 (regulamenta a Lei 11.126) | https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/decreto/d5904.htm | HTML | Texto legal, sem proteção autoral | regras do cão-guia no transporte | 9 |
| smped_guia | SMPED/Prefeitura de SP, Guia de Serviços: Transporte e Mobilidade | https://prefeitura.sp.gov.br/web/pessoa_com_deficiencia/w/publicacoes/307915 | HTML | Conteúdo público institucional; citar fonte | Atende+, Bilhete Único Especial, cão-guia, desembarque fora do ponto | 4 |
| sptrans_manual | SPTrans, manual de atendimento a pessoas com deficiência (treinamento de operadores) | https://www.mobilize.org.br/midias/pesquisas/sptransacessibilidade-treinamento.pdf | PDF | Material público da SPTrans; citar fonte | o que o motorista deve fazer ao ver uma pessoa cega no ponto | 15 |
| sptrans_pcd | SPTrans, página de serviços para pessoas com deficiência | http://www.sptrans.com.br/deficiente/ | HTML | Conteúdo público institucional; citar fonte | Bilhete Único Especial, Atende+ | 1 |
| metro_guia | Metrô SP, Guia do Passageiro | https://www.metro.sp.gov.br/wp-content/uploads/2026/07/guia_do_passageiro_online.html | HTML | Conteúdo público institucional; citar fonte | descartada — URL 404 e sem cópia no Wayback em 16/11/2026 | — |
| metro_elev | Metrô SP, Elevadores (a página redireciona para o PDF "Formas de acesso às estações e plataformas para pessoas com deficiência ou mobilidade reduzida") | https://www.metro.sp.gov.br/sua-viagem/acessibilidade/elevadores/ | PDF | Conteúdo público institucional; citar fonte | "a estação X tem elevador / rampa?" | 66 |
| metro_pref | Metrô SP, Atendimento Preferencial | https://www.metro.sp.gov.br/sua-viagem/acessibilidade/atendimento-preferencial/ | HTML | Conteúdo público institucional; citar fonte | atendimento preferencial, cão-guia no Metrô, embarque preferencial | 1 |
| cptm_acess | CPTM, página de acessibilidade | https://www.cptm.sp.gov.br/cptm/sua-viagem/acessibilidade | HTML | Conteúdo público institucional; citar fonte | estações acessíveis (35 de 41), piso tátil, braille, apoio da equipe, Táxi Acessível | 1 |
| gtfs_sptrans | GTFS SPTrans, versão de 12/11/2026 (1.366 linhas: 1.350 de ônibus, 9 de metrô e 7 da CPTM; 22.266 paradas) | https://www.sptrans.com.br/desenvolvedores/ (exige cadastro) | CSV/ZIP | Termos de uso da SPTrans: ler no cadastro e NÃO versionar o ZIP completo se os termos não permitirem | "qual linha vai de A a B?" (ferramenta, não trecho) | n/a |

## Observações
- O GTFS não vira trecho de texto: ele alimenta a ferramenta `consultar_gtfs` do agente (config 3).
- Matérias de jornal não entram como fonte de fatos; a base usa só fontes oficiais ou legais.
- Data de coleta registrada em cada trecho (`data_coleta`).
- CPTM: a página cobre 41 estações, e não as 94 de antes. Parte das linhas que aparecem como "CPTM" no GTFS (as linhas 8 e 9, por exemplo) foi concedida à iniciativa privada, e a página só cobre as linhas que a CPTM ainda opera. Não é erro. Nos casos de teste, perguntas sobre acessibilidade de estações das linhas concedidas são `nao_consta`.
- `metro_elev`: a subpágina só tem um redirecionamento automático para um PDF. O notebook 01 segue o redirecionamento, salva o PDF em `base/brutos/metro_elev.pdf` e usa a URL do PDF como `url` dos trechos. O PDF é uma tabela (colunas ESTAÇÃO, LOCAL, ACESSO À ESTAÇÃO, ACESSO À PLATAFORMA; linhas 1-Azul, 2-Verde, 3-Vermelha e 15-Prata). Ela não traz número de elevadores: cada linha vira uma frase com exatamente essas colunas, e há um trecho por estação e linha (ids `metro_elev_<linha>_<estacao>`; a estação em duas linhas gera dois trechos). Na v1 (etapa 3) os trechos agrupavam ~15 estações por linha do Metrô, o que diluía o embedding. As notas de rodapé (¹ ² ³) entram entre parênteses na célula a que se referem.
- `metro_guia` (descartada): em 16/11/2026 a URL retornava 404 e não havia cópia no Wayback Machine. Fica registrada aqui e sai do notebook. Entra no relatório como limitação: o Guia do Passageiro era a fonte prevista para piso tátil e acompanhamento.
- `sptrans_pcd`: a página só tem uma frase (29 palavras): o Bilhete Único Especial deve ser solicitado pelo Site de Atendimento, mediante cadastro e envio de dados pessoais. Não é menu nem lista de links, então foi mantida como um trecho curto (o `smped_guia` cobre o resto do tema).
- `base/brutos/` é versionado: as páginas mudam (o 404 do Guia mostra isso) e os originais garantem a reprodutibilidade.
