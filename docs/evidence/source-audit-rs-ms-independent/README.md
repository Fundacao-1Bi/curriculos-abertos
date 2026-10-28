# Auditoria independente RS EI / MS EF

Ator `agent:df_digital`, tipo `automated`, diferente do autor do helper. Não houve revisão pedagógica humana. Esta frente alterou somente este diretório de evidências.

O confronto final passou nas **25 verificações**, contra o helper congelado `f85f208c88957570f85fc6802745fff53b358f58c3c2c46a99e5aec1bee16e4e`. O arquivo `frozen-output-independent-verification.json` registra o resultado, e `ms-independent-anchor-comparison.json` fixa os checksums dos dois outputs completos. O comparador exige que o marker de execução concluída e o arquivo efetivo do helper tenham o mesmo hash antes de ler os outputs.

O inventário foi calculado nos PDFs originais sem usar IDs extraídos como denominador. Em RS, encontrou 340 ocorrências físicas de códigos (93 BNCC e 247 RS), 15 seções de faixa etária, cinco campos e 30 cabeçalhos de coluna. Em MS, o sumário das páginas 16–17 define dez componentes, incluindo Espanhol. O inventário geométrico reconheceu 713 regiões de cabeçalho pintado e **1.737 âncoras de definição** na coluna curricular. Todas as 2.077 posições foram comparadas com os campos/faixas ou componentes/anos/blocos explicitamente impressos, com zero faltas, extras ou divergências posicionais.

A revisão visual cobriu os 92 estratos MS de componente e ano/bloco, os 15 estratos RS de campo e faixa e páginas dirigidas de continuação, transição intrapágina, código anômalo e borda. Os PNGs são renderizações reais dos originais; `render-review.json` fixa hashes e autoria. A seleção visual não demonstra completude de todas as partes dos documentos.

## Achados e fechamento

`audit-checkpoint.json` preserva o histórico dos erros encontrados e a verificação final. Os snapshots anteriores mostraram: cabeçalho singular em Espanhol; sufixos de código separados em palavras nativas; grafias originais fora da regex; rodapés anexados ao texto; perda/projeção do 8º ano de Espanhol; corte de primeiras palavras em quatro páginas; código439 sem prosa própria seguido de objetivo na440; e letras da coluna esquerda emprestadas aos objetivos da direita em RS126. As verificações do output congelado passaram após as correções executadas pelo autor do helper. Os relatórios antigos continuam como evidência histórica.

O denominador MS foi ampliado de 1.734 para 1.737 após busca documental além da gramática inicial: duas definições na352 imprimem `MS. EF...`, e uma na674 imprime `MS.F...`. Os três rótulos foram confirmados nas imagens originais; a grafia não foi reparada. Em119, o censo independente havia removido o espaço interno antes do parêntese final de `(MS.EF15LP02.s.02 )`; esse erro do comparador foi corrigido e documentado sem alterar o helper ou o denominador.

RS88 imprime `EI01E003RS-01` com zero; RS126 repete `EI03EF08RS-02` para dois textos. Os dois fatos foram preservados. A imagem ampliada de RS126 mostra clipping real de finais de palavras na borda; o output mantém a camada textual nativa e uma nota de qualidade da fonte, sem reconstruir glifos ausentes. A grafia original `por mo` também foi preservada.

A varredura original das 713 regiões encontrou 16 sem âncora própria, somente duas com prosa:441 e522. Todas as palavras desses dois prefixos estão nas evidências dos objetivos anteriores. Depois de441 começa explicitamente o9ºano; a região523 não tem palavra residual antes do próximo código. Nenhuma segunda página consecutiva de prosa sem âncora foi encontrada. A continuação439→440 também passou. O teste de rodapé retornou zero sufixos numéricos da própria página nos 1.737 textos; os casos dirigidos de continuação também passaram sem rodapé intermediário.

As citações de códigos em Ações Didáticas nas páginas155 e567 foram conferidas como negativos: não são definições adicionais. Uma suspeita visual inicial sobre567 foi descartada após confronto das coordenadas; esse resultado continua explícito no checkpoint.

## Execução

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-rs-ms-independent/inventory_originals.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rs-ms-independent/inventory_rs_original.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rs-ms-independent/scan_nonstandard_identifiers.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rs-ms-independent/scan_zero_anchor_prefixes.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rs-ms-independent/verify_frozen_output.py --expected-helper-sha f85f208c88957570f85fc6802745fff53b358f58c3c2c46a99e5aec1bee16e4e
```

`render_samples.py` gera imagens e reinicia o estado da revisão visual como pendente; renderizar não equivale a inspecionar. O runtime utilizado foi `var/venv-pipeline`, Python3.11/PyMuPDF1.26.7.

Não há bloqueio externo nesta frente. O fechamento valida o recorte de ocorrências codificadas, suas posições e os casos textuais dirigidos. Não representa prontidão de UF nem reconciliação independente integral de todos os textos, narrativas, competências e estruturas sem código. A incorporação nacional e os demais requisitos de aceite pertencem à integração central.
