# RN — inventário físico independente da Formação Geral Básica

Fonte: `rn-referencial-em`, original `data/raw/RN/rn-referencial-oficial.pdf`, SHA256 `5f894abaa0309169597c7c9b7841aebaa9faaeb45e4cb759e5058b359e2ed845`. O outro arquivo histórico `rn-referencial-em.pdf` tem bytes diferentes e não participa desta prova.

O inventário leu integralmente PDF72–540: **469 páginas**, com **17 matrizes** (4 áreas e 13 componentes), **406 páginas de matriz**, **63 narrativas/framework** e **4.090 células físicas**. As fronteiras vieram do sumário e das 17 aberturas impressas, antes de comparar com registros extraídos. Todas as páginas das matrizes apresentaram grade estrita de três colunas; não se tomou a grade padrão fragmentada como denominador.

Foram localizados **667 identificadores em colunas primárias**: **464 códigos locais RN distintos** e **203 ocorrências de códigos de área BNCC** (181 códigos distintos nessas matrizes). Quatro outras menções pertencem à narrativa/framework. Isso mede ocorrências/documentos, não quantidade de habilidades nacionais novas ou qualidade curricular.

O protótipo privado reconstrói a prosa dos 667 slots com **738 fragmentos físicos**, incluindo **71 continuações entre páginas**: 52 células sem novo identificador e 19 prefixos antes do próximo código. Todos os identificadores e fragmentos foram conferidos literalmente no original, sem textos vazios. Isso ainda não é um adaptador integrado: faltam a árvore completa, objetos/articulações/sugestões, narrativa e gráficos, importador/schema/pais, revisão independente e reconciliação.

## Regras e anomalias preservadas

A página74 declara que as habilidades dos componentes são específicas do RN. A Figura6 da página75, conferida no gráfico original, explica `RNLGPOR001`: RN é a UF, LG a área, POR o componente e001 uma sequência na matriz. Não declara ano escolar nem equivalência individual com a BNCC. O código literal `RNMAT001` da matriz de Matemática permanece como impresso, sem expansão artificial para caber no exemplo da figura.

A enumeração nativa de História passa de `RNCHHIS054` para `RNCHHIS057`;055/056 não foram criados nem completados. A existência de uma sequência numérica não prova que a fonte contém todos os números. A prosa de `RNCHHIS059` continua na página372.

Quatro imagens significativas estão nas páginas73–75. A Figura6 já teve leitura visual; as demais exigem transcrição/revisão explícita. O limiar de3% de área é somente triagem de imagens, não prova de ausência de conteúdo em imagens menores.

## Arquivos e reprodução

- `rn-fgb-physical-inventory.json`: fronteiras, aberturas, páginas e todos os slots.
- `rn-fgb-cell-inventory.json`: geometria, papéis observados e hashes das células.
- `rn-fgb-primary-boundary-prototype.json`: contagens e continuações do protótipo.
- `rn-fgb-primary-prototype-verification.json`: checagem literal dos667/738.
- `rn-local-code-legend-evidence.json`: leitura da Figura6 e limites de interpretação.
- `rn-fgb-narrative-image-inventory.json`: figuras pendentes.

```sh
/usr/bin/nice -n 10 var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb/inventory.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb/build-primary-column-prototype.py
/usr/bin/nice -n 10 var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb/verify-primary-prototype.py
```

Textos integrais intermediários e recortes gráficos permanecem privados em `var/ne-rn-fgb-inventory/` e `var/private-evidence/source-audit-rn-fgb/`. Nenhuma Source, sidecar vinculado, cache de produção, core, banco ou publicação foi alterado. **Source e UF continuam sem aceite integral; revisão pedagógica humana não realizada.** O sidecar IFA146 já vinculado permanece intacto no seu pin anterior.

## Candidato físico completo, ainda privado

O candidato em `var/ne-rn-fgb-inventory/fgb-physical-complete-candidate.json` tem **3.681 nós** e SHA256 `505ef93e5f24f36d0d03c537f5dcfea5823be56df4c5d3bbe83432cdc69a3050`. Preserva as 17 matrizes, 667 slots de habilidades, 21 competências específicas impressas, eixos, cabeçalhos, objetos, articulações, sugestões e os trechos nativos fora da grade. Todas as **3.804 células não vazias** têm proprietário; as outras **286 células** estão inventariadas como vazias. As 4.090 células são unidades físicas, sem inventar correspondência individual entre uma célula mesclada de sugestões e cada habilidade adjacente.

Importador e finalizador de produção importaram os **3.681/3.681 nós**, com **6.478 fragmentos**, zero falhas literais, erros de schema, órfãos ou ciclos. Outras **695 ocorrências repetidas** de cabeçalhos/eixos/competências foram verificadas literalmente como contexto documental. A primeira tentativa havia concatenado essas repetições contra um texto canônico único: o diagnóstico foi preservado em `rn-fgb-matrix-candidate-before-repeat-metadata-fix.json`. O teste atual não muda nenhuma flag nativa da Source: cada evidência do adaptador declara seu próprio método físico de glifos.

Os **11 controles negativos** incluem redação adulterada, código local inventado, hash e bbox falsos, pai ausente, ano/período inferidos, exclusão de slot e preenchimento indevido da lacuna numérica de História. Uma continuação real suprimida com o texto/evidência encurtados ainda passa pelo verificador meramente literal; o inventário primário de slots/fragmentos é o gate que rejeita essa omissão. Portanto zero falhas literais não demonstra completude.

A continuação dos blocos contextuais não foi fundida por conveniência: `rn-fgb-context-continuation-candidates.json` registra 99 pares geométricos candidatos e 43 sobreposições ambíguas para revisão. Os blocos físicos originais permanecem íntegros. O censo de imagens sem limiar de área confirmou quatro instâncias raster em73–75; cores e diagramas vetoriais exigem análise própria. As observações visuais autorais estão em `rn-fgb-source-figure-author-observations.json`, separadas da transcrição canônica e da revisão independente.

O peer independente recebe primeiro apenas Source e páginas para fixar seu denominador; o candidato será apresentado depois. **Nenhum binding, atualização do cache, equivalência BNCC individual, ano escolar, Source integral ou UF pronta foi aprovado.** A Source e o sidecar IFA146 continuam inalterados.

```sh
/usr/bin/nice -n 10 var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb/build-matrix-candidate.py
/usr/bin/nice -n 10 var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb/verify-matrix-candidate.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb/verify-matrix-negatives.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb/inventory-all-images.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb/inventory-context-continuations.py
```
