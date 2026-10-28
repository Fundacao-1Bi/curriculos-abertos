# AM — Ensino Fundamental, anos iniciais: limites documentais verificados

Fonte `am-rca-ef-ai`, arquivo original `data/raw/AM/am-rca-ef-ai.pdf`, 670 páginas físicas. SHA-256 `38d9b9c5bf7534f48d9f5182fd9b43bc07555f56944eca2eaa11a9e120f82508` conferido pelo gerador antes de cada execução. A auditoria é de agente automatizado, sem revisão pedagógica humana; verifica capítulos e paginação, sem declarar extração integral das aprendizagens ou aceite da UF.

Proposta para integração: `ai-structure-sections-proposal.json`. O campo `evidence` de cada seção é objeto; `scope_evidence` conserva sumário, abertura, fólio da abertura, cabeçalho do quadro final e fólio final. As caixas estão no espaço de coordenadas original de cada página do PDF e são envelopes visuais, não segmentação exata de glifos. Imagens e seus hashes acompanham cada evidência. Todos os limites abaixo foram lidos visualmente no original renderizado, além de confrontados com o OCR cacheado.

| Componente/título declarado | Físicas inclusivas | Impressas verificadas na abertura e fecho |
|---|---:|---:|
| Língua Portuguesa | 110–344 | 108–342 |
| Arte | 345–397 | 343–395 |
| Educação Física | 398–460 | 396–458 |
| Língua Inglesa | 461–488 | 459–486 |
| Língua espanhola | 489–515 | 487–513 |
| Matemática | 516–556 | 514–554 |
| Ciências da Natureza | 557–588 | 555–586 |
| Geografia | 590–615 | 588–613 |
| História | 616–641 | 614–639 |
| Ensino Religioso | 642–656 | 640–654 |

Os dez componentes totalizam 546 páginas. A página física 109, impressa107, contém somente o conjunto de competências de Linguagens; a física589, impressa587, contém competências de Ciências Humanas. Foram propostas como seções próprias de uma página, com componente nulo. Juntas, as duas e os componentes cobrem sem sobreposição as físicas109–656. Não criar intervalos de área sobrepostos aos componentes: a ordem de aplicação de regras pode ocultar o componente específico.

O sumário físico16, conferido visualmente, lista os títulos e números impressos das aberturas. Ele não apresenta fólio impresso visível: seus carimbos são protocolo. Há salto explícito do capítulo17 para19, conservado sem inventar capítulo18. O sumário escreve literalmente “Matemátia”; a abertura516 escreve “Matemática”. O título “Ciências da Natureza” foi preservado; o nome canônico Ciências é documentado também pela narrativa da própria abertura557. A chamada sobrescrita1 em “Língua espanhola” é nota de autoria, não ano.

Referências começam na física657, impressa655, e terminam na668, impressa666. A669 é vazia salvo carimbo e a670 é contracapa decorativa. Elas não foram anexadas ao conteúdo curricular. As físicas1–108 permanecem fora deste mapeamento de capítulos de componentes; isso não as declara dispensáveis para a reconciliação normativa global.

## Geometria e orientação

A física109 tem dimensões PDF reais1413×2000 pontos, enquanto as páginas testadas adjacentes são595×842; suas coordenadas maiores são legítimas. O fólio107 foi confirmado na imagem original.

A física488 está lateral no original. O cache OCR devolve rotação0 e texto ilegível, mas a renderização manual90° confirma o cabeçalho “COMPONENTE CURRICULAR - LÍNGUA INGLESA” e fólio486. A prova é `ai-page-488-verified-upright.png`, com transformação explícita de seu espaço visual para o original. Nenhum cache compartilhado foi modificado. Este achado foi comunicado ao proprietário do adapter OCR para avaliação da extração dessa página.

## Aplicação e limites

A proposta inclui13seções: dez componentes, duas páginas de competências de área e referências. `position_contexts` está vazio deliberadamente: o finalizador atual substitui campos de ano ausentes por nulo ao aplicar um intervalo amplo, podendo apagar um ano efetivamente lido no quadro. Aplicar `structure_sections` para o componente e conservar a detecção de ano por título físico de cada quadro. O5ºano presente em alguns quadros finais não foi atribuído ao capítulo inteiro; nenhum ano foi inferido por código.

As28páginas examinadas visualmente e a geometria estão em `ai-verified-boundaries.json`; OCR e transformações em `ai-boundary-ocr.json` e `ai-boundary-images.json`. As dez aberturas, dez fechos, duas competências de área, duas páginas do sumário e o fim das referências/contracapa foram examinados. O mapeamento do PDF de anos finais é uma frente separada e não deve herdar o deslocamento de duas páginas deste arquivo.

## Reprodução

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-am-sections/ai-propose-sections.py
```

O gerador verifica SHA, 670 páginas, caixas dentro das dimensões reais, objeto de evidência, dez componentes/546páginas, intervalos sem sobreposição e ausência de atribuição de anos. Reexecução confirmou saída byte a byte idêntica. Não consulta rede nem altera manifestos, PDF, cache ou módulos centrais.

Implementado: proposta rastreável e gerador. Executado: reconstrução e validações locais. Verificado: sumário e todos os limites dos dez componentes em imagens originais. Pendente externo a esta frente: integração pelo proprietário do manifesto, extração estruturada e auditoria das aprendizagens/quadros por componente; tratamento da orientação da488 pelo adapter. Nenhuma liberação nacional ou aceite da UF é inferido destes limites.
