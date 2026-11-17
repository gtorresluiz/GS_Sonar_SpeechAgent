# Erros e achados (registro corrente)

Registrados assim que aparecem. Os "5 erros reais" do relatório saem só da seção "Erros do sistema", ou seja, das saídas do sistema na avaliação.

## Problemas encontrados na base

1. **Acentos decompostos no `lei_caoguia`** (16/11/2026): o HTML do Planalto trazia caracteres em NFD ("a" + acento combinante). Uma busca por texto exato ("à pessoa") falhava no trecho. Correção aplicada em `base.py`: normalização NFC na limpeza do texto (HTML e PDF).
2. **`lbi_002` com o § 3º duplicado**: o trecho traz as duas redações do § 3º do art. 47 (incisos XVII e XX do art. 181 do CTB). A redação antiga não estava em tag de texto riscado e passou pelo filtro. Impacto baixo (nenhum caso de teste depende desse parágrafo). Correção possível: filtrar também estilo `text-decoration: line-through`.
3. **`metro_guia` descartada** (URL 404 e sem cópia no Wayback em 16/11/2026): sem fonte para piso tátil e acompanhamento no Metrô. O caso `nao_consta_13` depende disso. Os trechos da CPTM falam de "pisos e rotas táteis", mas só das estações novas da CPTM.

## Erros do sistema

(vazia por enquanto: preenchida a partir das saídas das configurações 1, 2 e 3 na avaliação.)