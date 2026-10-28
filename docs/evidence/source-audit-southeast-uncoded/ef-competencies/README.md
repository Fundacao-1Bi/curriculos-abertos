# Competências do Ensino Fundamental — Espírito Santo, volumes 02–09

Este adaptador cobre as oito partes oficiais selecionadas, com 1.956 páginas.
Os PDFs e seus hashes vêm de `data/manifests/bncc-southeast.json`. O censo de
todas as páginas precedeu os sidecars e inclui páginas sem códigos nacionais,
textos introdutórios, figuras, títulos, cabeçalhos e células originais. Nenhuma
fonte, manifesto, cache de produção ou arquivo do pipeline foi alterado.

## Denominador e grão documental

O censo físico independente identifica **4.603 ocorrências de competências
específicas**, em **1.553 células de redação**. São preservadas todas as
repetições nas colunas próprias; o número não pretende medir competências
semânticas distintas. O censo lexical ampliado examina qualquer prefixo
alfabético seguido de número dentro desses campos e confirma o alfabeto
completo, inclusive `CE1`, `CE01`, `CEAR06`, `CELI01`, `CElI01`, `CIEF03`,
`CIEF04`, `LPEFO9` e `LPEF010`, sem corrigir grafia ou atribuir equivalência.

Há **80 competências gerais** nas oito figuras originais de dez dimensões,
**8 objetivos curriculares de Ensino Religioso** em figuras explicitamente
rotuladas e **623 nós estruturais** (613 desta frente e 10 das figuras).
Total consolidado: **5.314 registros**. Nas figuras gerais, a fonte não imprime
numeração oficial 1–10; os registros têm `code:null` e ordem técnica da figura.
Os oito objetivos curriculares têm tipo próprio e não são automaticamente
classificados como competência individual de aluno.

O denominador das folhas vem de `competence-field-denominator.json` e de
`prose/physical-prose-inventory.json`. Os 613 nós adicionais têm seu próprio
denominador anterior aos outputs, `structural-denominator.json`: 596 campos
reais de tabela e 17 títulos/capas reais de capítulo ou componente. Seus IDs
são técnicos. Os IDs das folhas usam fonte, página, localizador físico e código
literal, com ocorrência; nenhum identificador oficial é fabricado.

## Regras de fidelidade

- A definição é identificada pelo campo original **Competência(s)
  Específica(s)** ou **Descrição da Competência**, nunca por regex isolada.
  Os identificadores impressos são competências locais, não habilidades EF.
- Nas linhas inline, o texto canônico mantém inclusive o marcador impresso;
  nas tabelas com coluna separada, o texto corresponde à descrição e o código
  tem sua própria evidência `code_locator`. O caso e a pontuação são preservados.
- Volumes 04 e 08, página PDF 78: a descrição de CEAR05 contém também uma
  definição completa de CEAR06. As duas definições são separadas por posição
  real na redação. A ocorrência de CEAR06 na página seguinte também é
  preservada. A linha física de CEAR05 não torna CEAR06 sua filha semântica.
- Volume 03, página PDF 79: `EF01GE05/ES` aparece como referência ao objetivo
  da página 78 dentro da célula CE. Esse texto permanece em contexto com prova
  própria; não gera outra competência nem outro objetivo de aprendizagem.
- Volume 08, páginas PDF 246–247: a legenda do quadro nomeia **Artes**, enquanto
  o capítulo/título diz **Língua Inglesa** e os identificadores são CELI. Ambas
  as provas são mantidas, a continuação do quadro conserva o conflito e o
  componente estruturado fica nulo nesses seis registros. Não há escolha
  silenciosa de uma interpretação.
- As páginas das competências não trazem ano local explícito. `years`,
  `year_label`, idade e período ficam nulos. Não se herda o ano de uma habilidade
  vizinha nem se transforma um código local em código nacional. A etapa e o
  componente, quando preenchidos, têm prova em título/capa/banner original.
- Prefixos sem marcador foram censados integralmente. Restam apenas rótulos
  **(Continuação)** e a redação de CEAR05 antes da definição adicional CEAR06;
  não há prosa de competência sem marcador descartada por presumir uma
  continuação. A cobertura integral de cada célula é conferida separadamente.

## Reprodução

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-uncoded/ef-competencies/inventory_physical.py --volumes 2 3 4 5
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-uncoded/ef-competencies/inventory_physical.py --volumes 6 7 8 9
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-uncoded/ef-competencies/census_roles.py
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-uncoded/ef-competencies/census_structure.py
var/venv-pipeline/bin/python data/manifests/uncoded/es-ef-competencies-prose-extract.py inventory
var/venv-pipeline/bin/python data/manifests/uncoded/es-ef-competencies-prose-extract.py extract
var/venv-pipeline/bin/python data/manifests/uncoded/es-ef-competencies-prose-extract.py verify
var/venv-pipeline/bin/python data/manifests/uncoded/es-ef-competencies-extract.py extract
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-uncoded/ef-competencies/verify_cell_coverage.py
var/venv-pipeline/bin/python data/manifests/uncoded/es-ef-competencies-extract.py verify
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-uncoded/ef-competencies/visual_sample.py
```

`prose/README.md` documenta também o inventário independente das figuras e o
fechamento de candidatas numeradas/imagens. O extrator consolidado apenas lê o
sidecar separado dessa subfrente e o incorpora nos oito wrappers finais.

## Evidências e integração

`verification.json` executa `source_uncoded_items` e `finalize_items` reais,
com textos de páginas em RAM e PDFs originais abertos somente para leitura.
Confronta IDs esperados de denominadores independentes, identidade exata de
texto/código/tipo/posições, resolução de todos os pais, todos os fragmentos
canônicos e metadados por NativeGlyphText e glifos visíveis. Registra ainda os
hashes de todo `pipeline/*.py` antes/depois. `full-cell-coverage.json` contabiliza
todo o texto de cada célula, incluindo referências secundárias, com comparação
exata salvo espaços; passar apenas a contagem de marcadores não seria suficiente.

As amostras estratificadas usam rasterizações dos PDFs originais, em diretório
privado `var/private-evidence/`, sem cópias dos PDFs ou rasterização em massa.
A revisão visual é feita pelo agente e é distinta de revisão humana. Os
relatórios não declaram revisão humana, prontidão da UF ou equivalência BNCC.

O contrato de integração proposto é um `uncoded_items_path` por fonte, apontando
para `data/manifests/uncoded/es-ef-competencies-vol02.json` até `vol09.json`.
Os wrappers já incluem a parte geral; apontar só para o sidecar `prose-items`
perderia as competências específicas. Os hashes finais e a proposta exata de
fonte/caminho ficam em `integration-proposal.json`. A integração ao manifesto e
ao corpus global cabe ao owner e não é presumida por esta auditoria local.
