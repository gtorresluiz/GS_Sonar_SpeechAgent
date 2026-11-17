# Fontes da base de conhecimento

> Tabela exigida no relatório: fonte, formato, licença e nº de trechos.
> A coluna "Nº de trechos" é preenchida automaticamente pelo notebook 01.

| ID | Fonte | URL | Formato | Licença / termos | Responde a | Nº de trechos |
|---|---|---|---|---|---|---|
| lbi | Lei 13.146/2015 (Lei Brasileira de Inclusão), só os capítulos de acessibilidade e transporte (arts. 46 a 52) | https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13146.htm | HTML | Texto legal, sem proteção autoral (Lei 9.610/98, art. 8º, IV) | direitos no transporte, prioridade | — |
| lei_caoguia | Lei 11.126/2005 (cão-guia) | https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2005/lei/l11126.htm | HTML | Texto legal, sem proteção autoral | "posso embarcar com cão-guia?" | — |
| dec_caoguia | Decreto 5.904/2006 (regulamenta a Lei 11.126) | https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/decreto/d5904.htm | HTML | Texto legal, sem proteção autoral | regras do cão-guia no transporte | — |
| smped_guia | SMPED/Prefeitura de SP, Guia de Serviços: Transporte e Mobilidade | https://prefeitura.sp.gov.br/web/pessoa_com_deficiencia/w/publicacoes/307915 | HTML | Conteúdo público institucional; citar fonte | Atende+, Bilhete Único Especial, cão-guia, desembarque fora do ponto | — |
| sptrans_manual | SPTrans, manual de atendimento a pessoas com deficiência (treinamento de operadores) | https://www.mobilize.org.br/midias/pesquisas/sptransacessibilidade-treinamento.pdf | PDF | Material público da SPTrans; citar fonte | o que o motorista deve fazer ao ver uma pessoa cega no ponto | — |
| sptrans_pcd | SPTrans, página de serviços para pessoas com deficiência | http://www.sptrans.com.br/deficiente/ | HTML | Conteúdo público institucional; citar fonte | Bilhete Único Especial, Atende+ | — |
| metro_acess | Metrô SP, página de acessibilidade | TODO: localizar a URL oficial em metro.sp.gov.br | HTML | Conteúdo público institucional; citar fonte | elevador, piso tátil, atendimento na estação | — |
| cptm_acess | CPTM, página de acessibilidade | TODO: localizar a URL oficial em cptm.sp.gov.br | HTML | Conteúdo público institucional; citar fonte | porta preferencial, embarque assistido | — |
| gtfs_sptrans | GTFS SPTrans, versão de 12/11/2026 (1.366 linhas: 1.350 de ônibus, 9 de metrô e 7 da CPTM; 22.266 paradas) | https://www.sptrans.com.br/desenvolvedores/ (exige cadastro) | CSV/ZIP | Termos de uso da SPTrans: ler no cadastro e NÃO versionar o ZIP completo se os termos não permitirem | "qual linha vai de A a B?" (ferramenta, não trecho) | n/a |

## Observações
- O GTFS não vira trecho de texto: ele alimenta a ferramenta `consultar_gtfs` do agente (config 3).
- Matérias de jornal não entram como fonte de fatos; a base usa só fontes oficiais ou legais.
- Data de coleta registrada em cada trecho (`data_coleta`).
