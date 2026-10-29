# Peer independente RN FGB — cobertura nativa e limites do candidato

**Cobertura textual nativa verificada; aceite integral da FGB pendente.** Este recibo não autoriza binding, não valida SourceWhole/UF ready e não revisa pedagogia. O único primário é `data/raw/RN/rn-referencial-oficial.pdf`, SHA `5f894abaa0309169597c7c9b7841aebaa9faaeb45e4cb759e5058b359e2ed845`, 570 páginas. O recorte auditado é PDF72–540, 469 páginas. A outra cópia de RN não foi usada.

O censo primário foi executado e pinado antes da abertura do candidato: `primary-census.json` SHA `ec6b60c0c04dc413b74d27f4e18060771ed3f58fc536cea10331b6f700f2cf63`, e `source-only-structure.json` SHA `95e6c69844fcc971ade6fcab8549c971dab3ec73ffe3dac0dd5b9151d80f1a54`. Ambos declaram que não leram outputs/helpers do produtor. A lista de páginas veio do proprietário; não se adotou sua contagem de registros como denominador. O conteúdo nativo integral das regiões, palavras e coordenadas está pinado em `primary-cells.jsonl`.

## Denominadores e reconciliação

O censo encontrou 406 páginas com tabelas, 410 tabelas detectadas, 4.140 regiões únicas e 3.814 não vazias. A detecção inclui uma ficha aninhada de oito colunas na p311: 50 regiões, dez não vazias, 17 palavras. Ela está fisicamente dentro da sugestão didática da matriz de Educação Física; seus tokens foram preservados pelo candidato no bloco pai, mas a ordem/estrutura visual apresentou o achado P1 descrito abaixo. Excluí-la do denominador principal de três colunas explica exatamente a diferença com as 4.090 regiões/3.804 não vazias informadas pelo produtor; a diferença não foi descartada silenciosamente.

As 409 tabelas principais têm três colunas e 409 linhas explícitas de rótulos. Suas 3.804 regiões não vazias se reconciliam como:

- 2.045 cabeçalhos físicos (título/eixo ou definição de competência, mais três rótulos por tabela), todos cobertos por evidência canônica ou ocorrência repetida contextual literal;
- 1.178 blocos das colunas de articulação, objetos e sugestões, todos iguais em sequência completa e whitespace colapsado pela API independente de palavras;
- 581 regiões não vazias da coluna de habilidades, contendo 667 ocorrências codificadas e suas continuações.

Foram encontradas 671 âncoras alfanuméricas nativas no recorte completo: 667 nas matrizes e quatro em prosa fora da grade. Estas quatro não foram promovidas a novas aprendizagens. A reconstrução independente da coluna de habilidades confirmou os 667 corpos e o multiconjunto página/código integralmente, sem normalizar letras, hífens, pontuação ou identificadores. Todos os 469 textos nativos fora da grade também coincidiram com o candidato. A ordem das duas colunas internas de articulação da p150 foi verificada visualmente e pela sequência de palavras: o candidato preserva a leitura, embora `table.extract()` intercale essas duas colunas.

O primeiro oráculo de corpos encontrou 19 diferenças que eram defeito do próprio oráculo: não coletava o prefixo de continuação localizado antes de um novo código dentro da mesma célula da página seguinte. A conferência geométrica das palavras primárias corrigiu essa coleta. O resultado inicial foi preservado em `coded-comparison-before-leading-fragment-recheck.json`; ele não é apresentado como falha do candidato. O checkpoint de contagens primárias anterior ao candidato permanece imutável. A reconstrução detalhada de corpos e essa correção ocorreram depois daquele checkpoint e da abertura do candidato.

## Execução real

Candidato privado SHA `505ef93e5f24f36d0d03c537f5dcfea5823be56df4c5d3bbe83432cdc69a3050`, 3.681 nós. Em clone privado do Source, sem alterar o registro vigente nem seu adapter IFA, passaram importer, finalizador, hierarquia, JSON Schema e checker literal reais: 3.681/3.681 nós, zero falhas, órfãos ou ciclos. As 695 ocorrências repetidas contextuais também foram conferidas no PDF real. A execução `runtime.json` levou 155,735 s, com fingerprint de parser `541aa3377fd409f9c172e1580ae988f5869b25e5331c98528ab68fb9a09360db`; Source e cache foram rehasheados inalterados ao final.

Seis negativos do replay e sete controles próprios de completude bloquearam corrupção de código/pin/bbox, série inventada, remoção de habilidade, objeto, sugestão, ocorrência repetida de cabeçalho, prosa externa e continuação real. Foi demonstrado que encurtar corpo e evidência simultaneamente pode continuar passando pelo checker literal: o corpo independente completo da fonte bloqueou essa omissão. Um resultado literal verdadeiro não foi usado como prova automática de completude.

## Achados e limites antes de binding

**P1 — ordem e estrutura da tabela aninhada p311.** Na fonte, a Ficha de Registros está entre o parágrafo que termina em “cada uma delas.” e o seguinte que começa “Propor aos estudantes que se organizem em grupos...”. O candidato coloca seus 17 tokens depois do final da sugestão, imediatamente após “...foi suficiente para atender”, produzindo “atender Ficha de Registros Atividades Realizadas Dias e Tempo de Prática S T Q Q S S D”; a p312 continua “aos objetivos...”. O campo perde a disposição de oito colunas e oito linhas e ganha uma sequência de leitura que não corresponde ao layout primário. A tabela é contexto documental, não habilidade. É preciso representar sua estrutura/posição ou separar seus fragmentos com evidência própria, preservando a redação e os vizinhos. O caso prova por que igualdade com a ordem nativa do stream e checker literal não bastam para garantir a ordem física de leitura. A contrapova de 1.178 sequências nativas permanece válida como cobertura dos caracteres e ordem do stream; não é aprovação universal da estrutura visual. O achado foi transmitido ao proprietário e à integração antes de binding. `nested-table-order.json` prova geometricamente os grupos ANTES → tabela → DEPOIS, a presença de todos os caracteres e a ordem incorreta do candidato; seu negativo local bloqueia a troca da tabela para o fim. O proprietário confirmou a falha e manterá o pin original até este recibo, corrigindo em revisão posterior.

**P2 — rodapés como narrativa.** 388 nós `narrativa_curricular` contêm exclusivamente o número da própria página (por exemplo, p104 = `104` e p311 = `311`). O texto não foi perdido, mas o papel documental está incorreto e infla as narrativas. Os outros 81 blocos externos incluem prosa junto à paginação. A paginação deve ser preservada como localizador/metadado ou papel documental explícito, sem tratar o marcador isolado como narrativa curricular. O achado foi enviado ao proprietário antes de qualquer binding; o peer não alterou o candidato.

**Continuidade contextual ainda pendente.** Os 1.178 blocos físicos estão completos, mas isso não os torna 1.178 contextos lógicos completos. A p500 termina a articulação de EM13CNT102 em “ao possibilitar a identificação dos”; p501 começa em “processos de propagação de calor”. O candidato mantém dois itens distintos com declaração explícita de que a junção além da célula ainda não foi aprovada. Em Filosofia, a lista de objetos de RNCHFIL017 continua de p399 para p400 com a coluna de habilidade vazia. Há ainda sugestão interrompida em p311 e retomada em p312. O censo registra 642 adjacências prospectivas, que não foram convertidas automaticamente em 642 vínculos semânticos. É preciso representar e verificar essas continuações para declarar a estrutura lógica integral.

**Raster e cores ainda pendentes.** Há quatro imagens embutidas em p73–75: dois exemplos de matriz e dois diagramas de códigos. Seus xrefs, geometria, bytes e pixels originais foram pinados sem publicar/copiar imagens embutidas. Captions nativas preservadas não transcrevem o conteúdo das figuras. O inventário também registra 1.155 ocorrências literais de VP/PEP/JM/AVP/CA e fundos vetoriais; não inferiu o significado dos fundos. Na p300, por exemplo, VP, PEP e AVP têm realce e JM/CA não. A lista textual com os cinco rótulos não preserva sozinha essa diferenciação. Não se certificaram seleção por cor, diagramas ou figuras como conteúdo estruturado.

Renderizações primárias pequenas ficaram privadas em `var/private-evidence/rn-fgb-peer`; hashes em `private-renders.json`. O conjunto não substitui revisão visual de todas as páginas. Não houve criação de PDF derivado, rasterização massiva, novo OCR, parser nacional, banco, worker, publicação ou alteração de Source/cache/core/candidato. O adapter IFA vigente não foi sobrescrito, nem sua conservação em uma futura composição foi inferida deste clone FGB.

## Reprodução

A partir da raiz, preservando os pins e usando namespace novo para não apagar recibos históricos:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb-peer/primary-census.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb-peer/source-only-structure.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb-peer/compare-coded.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb-peer/compare-context.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb-peer/compare-headers.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb-peer/compare-outside.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb-peer/negative-completeness.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb-peer/runtime.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fgb-peer/nested-table-order.py
```

A inspeção primária e os checkpoints antecederam a leitura do candidato nesta execução. Reexecutar tudo depois de conhecer o candidato reproduz as provas geométricas, mas não recria retrospectivamente a condição cega original.
