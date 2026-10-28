# Adaptador de objetivos sem código — Paraná 2025

Implementa a parte documental de DAT-01, DAT-02, DAT-05, ING-02, ING-03 e ESC-02 na fonte `pr-referencial-eief-2025`. A execução é local, automatizada; não houve revisão humana, publicação remota ou commit.

A fonte é o Anexo I da Deliberação CEE/PR 07/2025, Volumes 1 e 2, 1.028 páginas. Seu SHA-256 é `ce72aefb003c006d41e0912bc0744eaf2fb6dfca941d6de716293b593a495f46`; o caminho e a URL oficiais são resolvidos pelo manifesto `data/manifests/central-south.json`. O PDF permanece no cache local e não foi republicado.

## Extração implementada e executada

`data/manifests/uncoded/pr-extract.py` lê todas as páginas da fonte e inventaria cabeçalhos explícitos e linhas da grade. Localiza exclusivamente a coluna OBJETIVOS do Volume 1. Na EI, separa cada marcador de objetivo; no EF, separa parágrafos locais em fonte regular e mantém os trechos codificados como contexto, sem duplicá-los como objetivos sem código. As colunas SABERES, OBJETOS DE CONHECIMENTO e demais conteúdos não viram aprendizagens.

`pr-digital.py`, chamado pelo adaptador principal, inventaria todas as tabelas HABILIDADE do Volume 2. Extrai as células sem código da subcoluna de habilidades locais e exclui EXPLICAÇÃO DA HABILIDADE e EXEMPLOS. As tabelas do próprio PDF reaparecem fisicamente nas páginas 925–964 e 987–1026; as ocorrências são conservadas por página/célula. As 68 ocorrências locais digitais não são uma afirmação de 68 habilidades distintas: há 34 ocorrências em cada cópia física.

O arquivo integrado `data/manifests/uncoded/pr-items.json` tem 3.971 registros: 3.896 objetivos de aprendizagem, 7 orientações docentes e 68 ocorrências de habilidade local sem código. Destes, 3.903 pertencem ao Volume 1 e 68 ao Volume 2. O Volume 1 tem 727 páginas de tabelas; o Volume 2 tem 80 tabelas examinadas, incluindo as colunas de habilidade sem objetivos locais adicionais.

Cada registro tem `code:null`, ID técnico derivado de fonte/página/localizador, texto, tipo, faixa etária/ano ou bloco, componente/campo, hierarquia documental e evidência com caixa de texto e página. Cabeçalhos da EI distinguem bebês de zero a 1 ano, crianças bem pequenas de 1, 2 e 3 anos e crianças pequenas de 4 e 5 anos. O bloco 6º–9º é mantido como bloco.

`source_context.reference_codes` registra somente códigos presentes na mesma linha da grade. O vínculo de agrupamento documental não declara equivalência pedagógica. O item preserva seu código nulo mesmo quando aparece abaixo de uma habilidade BNCC. Orientações explícitas ao professor e redações iniciadas por “Proporcionar” conservam o texto, mas usam `orientacao_docente`; a classificação é automatizada e sua base está registrada. Outros objetivos que mencionam mediação docente continuam sendo objetivos do estudante.

Frações bidimensionais mantêm os glifos extraídos e suas caixas em `two_dimensional_text_layout`. A transcrição linear não introduz uma barra que não exista como caractere no PDF. A consulta ao trecho renderizado é necessária para reconstruir sua disposição visual.

## Verificação executável

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/pr-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/pr-verify.py
```

É necessário PyMuPDF 1.26.7 ou posterior, no ambiente corrigido `var/venv-pipeline`. Os scripts não usam rede, modelos ou o cache de extração central. Rotação é removida em memória quando necessária; os bytes da fonte permanecem imutáveis.

O denominador do Volume 1 vem de uma segunda leitura independente por palavras, marcadores, intervalos de parágrafo, fonte e grade, sem importar a função extratora nem copiar IDs dos resultados. Inclui todas as páginas, partes, campos/componentes e cabeçalhos etários/anos encontrados. A primeira comparação revelou oito falsos candidatos derivados de títulos transversais de Língua Inglesa; a conferência com as caixas da linha inteira corrigiu o denominador. O conjunto final contém 3.903 IDs esperados e verificados. Os IDs esperados, suas caixas e seus textos brutos estão em `pr-independent-denominator.json`.

O denominador digital enumera as células da coluna HABILIDADE antes de produzir os registros. As caixas e os IDs esperados estão em `pr-digital-cell-denominator.json`. A validação integrada compara ambos os denominadores aos registros, verifica unicidade, hash, código nulo, posicionamentos, ID determinístico e conteúdo de cada caixa. `pr-all-verification.json` registra o resultado final.

Reexecução integral produziu bytes idênticos, SHA-256 `91073732d14d44f735ab000d6b5473a73e526d08b3c8a4edd19f55faba1c3ad3`, conforme `pr-reproducibility.json`.

Amostra visual estratificada inclui os seis cabeçalhos etários da EI, todos os cinco campos, os nove componentes do EF e Computação por ano e por bloco. `pr-visual-sample-selection.json` distingue páginas renderizadas de páginas efetivamente inspecionadas e informa os IDs amostrados. Os PNGs ficam em `docs/evidence/source-audit-pr/`. Essa inspeção por agente é automatizada, não validação pedagógica humana.

## Integração e limites

O responsável pelo manifesto deve associar `uncoded_items_path: data/manifests/uncoded/pr-items.json` à fonte. A importação e as relações devem preservar `source_context`, tipos, evidências e posições. Esta frente não altera pipeline central nem declara pronta a UF: a reconciliação dos itens codificados, das demais fontes obrigatórias do Paraná e das jornadas integradas permanece responsabilidade da coordenação.
