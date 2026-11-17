# Sonar: assistente de mobilidade acessível (GenAI for Engineering, FIAP)

> Rascunho. O README completo (como rodar, resultados, reprodutibilidade) fica para o fim do projeto.

## Base de conhecimento (etapa 1)

- `base/fontes.md`: tabela das fontes (formato, licença, nº de trechos) e observações.
- `base/trechos.jsonl`: trechos com `id, fonte, url, formato, licenca, data_coleta, texto`. No campo `fonte` vai o id da fonte (ex.: `lbi`), que liga o trecho à tabela de `fontes.md`.
- `base/brutos/`: **os arquivos originais coletados (HTML/PDF) são versionados de propósito.** As páginas mudam ou saem do ar (o Guia do Passageiro do Metrô, por exemplo, passou a retornar 404 e ficou fora da base), então os originais garantem que `notebooks/01_coleta_e_chunking.ipynb` seja reproduzível. Se o download falhar, o notebook usa o arquivo salvo em `base/brutos/<id>.<ext>` e avisa.
- Fonte descartada: `metro_guia` (URL 404 e sem cópia no Wayback em 16/11/2026). Limitação registrada no relatório.
