# Amapá — extração própria do documento nativo614 e confronto inicial339

O pacote usa exclusivamente o conteúdo do PDF nativo de614páginas, fonte `ap-rca-ei-ef-mec`, SHA-256 `23c42348e0b0e00d4135a108366141a257bec54b7b1bff79e521c822d9903f89`. A cópia CEDOC614 tem identidade de conteúdo previamente comprovada e não recebeu adapter duplicado. A fonte339, `ap-rca-ei-ef`, SHA `fc40788a0165eb6fa61d713cee87d4b0b95b45435e496b43bb477f9471a103c4`, continua separada.

## Produto implementado

`data/manifests/uncoded/ap-rca614-extract.py` e `ap-rca614-labelled.py` produzem `ap-rca614-items.json`, com2441registros rastreáveis. Todos têm evidência própria, localizador, página física, fólio, geometria e procedência automatizada. Não foi criado código local para unidade sem código oficial.

| Parte/grão | Quantidade |
|---|---:|
| Campos de experiência EI | 5 |
| Organizadores etários EI | 15 |
| Objetivos de aprendizagem EI com código impresso | 93 |
| Experiências locais EI por faixa etária | 465 |
| Organizadores físicos EF | 84 |
| Habilidades EF com código impresso | 1632 |
| Habilidade EF sem código, História529 | 1 |
| Competências gerais | 10 |
| Direitos de aprendizagem EI | 6 |
| Competências específicas, listas e dois diagramas | 101 |
| Objetivos formativos explícitos ER | 4 |
| Objetivos normativos da educação indígena | 8 |
| Nós de seções das listas/diagramas | 17 |

As465experiências têm limites mensais explícitos de seis cabeçalhos microetários, além da prova do cabeçalho macro no array `age_evidence`; os93objetivos têm limites de seus cabeçalhos macro numéricos. `age_min_months`/`age_max_months` são inclusivos: as sobreposições escritas nos cabeçalhos foram preservadas. Não se deduzem limites do nome do grupo ou do código.

Os8objetivos normativos indígenas são metas dos sistemas/escolas, têm esse papel registrado e posições vazias; não são apresentados como habilidades de estudantes. As10competências gerais têm escopo EI+EF do documento, sem anos inventados. As101competências específicas preservam ocorrências distintas quando o documento as publica em mais de uma seção; a contagem não é de competências nacionais únicas.

A extração registra campo e rótulo etário literal, inclusive `PEQUENAS (...)` na119 e `CAMPO DE EXPERIÊNCIAS` na125. Experiências são filhas do objetivo físico correspondente; os objetivos pertencem a organizadores/ campos. No EF, anos são lidos de cabeçalhos e da extensão física da célula: por exemplo,244 EF12LP01 abrange1º+2º, enquanto EF01LP01 ocupa só1º;355 EF89LP32 abrange8º+9º. Código não determina ano. Unidades, práticas, objetos de conhecimento e eixos ficam como contexto com suas próprias caixas, sem virarem habilidades; outra coluna de habilidade paralela não vira objeto de conhecimento.

Há373ocorrências de códigos que contêm AP. Hífens e formatos próprios foram conservados: `EF15LP-AP01` continua distinto do nacional; `EF089LP-AP04`, `EF08ER – AP01` e o código sem parêntese inicial/final da578 conservam suas formas originais. Espaçamento de código tem `code_original`; não se remove AP para inventar correspondência nacional. A triagem de códigos no meio de oração das colunas de aprendizagem retornou zero: os códigos selecionados são âncoras de unidades, não referências internas promovidas a novas habilidades.

A ordem nativa das palavras é preservada ao recortar a coluna. Os sobrescritos são transcritos a partir do indicador tipográfico nativo do PDF: `cm³` e `2⁴` conservam seu significado e possuem prova de span/caixa. Não se usa ordenação pelo topo de palavras, que deslocava expoentes para a linha anterior.

## Denominador anterior ao adapter

`ap614-source-census.py` foi executado antes da primeira saída do adapter. Percorreu614páginas e345tabelas detectadas; conservou um censo compacto de células, âncoras, marcadores e cabeçalhos, sem criar um cache completo de texto. A triagem source-only em `ap614-close-denominators.py` não importa nem lê o adapter. Ela distingue cabeçalhos, células de conteúdo e continuações; quadros de objetos de conhecimento da Educação Física379–380 foram excluídos das habilidades.

O denominador é1638células físicas selecionadas:93de objetivos EI,188de experiências EI,1continuação de objetivo EI,1321células EF com códigos,34continuações EF sem código e1habilidade EF sem código. Nessas células aparecem93âncoras de objetivos EI,465marcadores de experiências e1632âncoras de habilidades EF. Células com prefixo de continuação e novo código também são reunidas pelo fluxo documental, preservando evidências de cada fragmento e sem concatenar objetivos diferentes. A lista `ap614-continuation-locators.json` contém só localizadores para a contrapova independente.

## Verificação executada

`ap-rca614-verify.py` lê o fonte novamente, confronta o denominador físico, confere todas as evidências e a concatenação semântica e executa o loader e o finalizador reais do pipeline. `ap614-verification.json` é a autoridade sobre hashes, totais e resultado da última execução. O ensaio inicial com `get_text(sort=False)` não reproduzia a ordenação de produção: o peer encontrou25falhas em títulos/diagramas. As evidências desses registros foram subdivididas em linhas próprias, sem alterar texto/código/key/parent. O verificador atual usa `get_text(sort=True)` e não afrouxa o checker. Também identificou metadata legada com `position_contexts.pages`; o proprietário corrigiu o manifesto. O verificador registra se precisou de qualquer substituição em memória, portanto um ensaio isolado não pode ser confundido com integração real.

Foram examinadas visualmente23páginas do nativo, cobrindo EI, os9componentes, quadros com anos paralelos/mesclados, códigos AP irregulares, a habilidade sem código e os três casos de expoentes; quatro páginas do339 foram confrontadas visualmente. As imagens JPEG são pequenas. Não foi produzido novo OCR nem novo cache pesado. O peer `/root/auditor` realiza uma contrapova separada, com propriedade em `docs/evidence/source-audit-ap-peer/`; sua conclusão deve ser consultada antes do aceite desta frente. Não houve revisão pedagógica humana.

## Documento339: o que está e não está demonstrado

`ap339-scope-review.py` leu os339caches de OCR existentes, com zero páginas ausentes e sem gerar OCR. Isso mede disponibilidade de texto OCR, não aprendizagens extraídas ou reconciliadas. O sumário original5–6 declara EI, EF e as modalidades;43 e116 foram confirmadas no corpo com fólios iguais às páginas físicas nesses dois exemplos. Não se presume esse deslocamento para todo o arquivo.

A43 contém EI01EO01 e EI01EO02 em uma página, enquanto o614 as distribui em93–94. A116 agrupa conteúdo que ocupa240–241 no614. Há reflow claro em amostras. A leitura inicial do hífen no código AP da116 não ficou firmada na escala visual usada e foi retirada do confronto; não se afirma variante literal339 nem alias. Amostras semelhantes e títulos iguais não estabelecem identidade integral de texto, código, edição ou vigência. A matriz rastreável está em `ap339-vs614-scope-comparison.json`.

O vínculo à Resolução15/2019 foi informado na delegação, mas este pacote não localizou e reconciliou autonomamente o ato normativo. A aprovação/vigência não foi inferida da data técnica do PDF ou do ano do catálogo CEDOC. Permanecem tarefas internas reais do339: denominadores por coluna/idade/ano/componente, transcrição estruturada própria, verificação de todas as continuações e códigos, confronto integral com614 e reconciliação do ato de aprovação. Não são bloqueios de acesso ao614 nem justificativa para descartar trabalho disponível.

## Reprodução e integração

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ap-eief/ap614-source-census.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ap-eief/ap614-close-denominators.py
var/venv-pipeline/bin/python data/manifests/uncoded/ap-rca614-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/ap-rca614-verify.py
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python docs/evidence/source-audit-ap-eief/ap339-scope-review.py
```

O proprietário do manifesto poderá vincular `uncoded_items_path` ao sidecar após a contrapova e suprimir definições genéricas duplicadas das páginas estruturadas. Não inferir equivalência339/614 ou nacional por similaridade de código. Fonte614 íntegra, censo físico, aprendizagens verificadas e integração no pipeline são fatos distintos da completude normativa da UF e da distribuição de produção. Este pacote não declara AP pronto nem cobertura nacional.

O censo literal de caracteres por todas1638células está em `ap614-cell-character-check.json`: compara acentos, pontuação e hífens, com equivalência explícita do glifo nativo U+FB02→fl e sobrescritos comprovados. A grafia original `fccional` da257 foi mantida, não corrigida por expectativa lexical. As imagens de fonte estão exclusivamente em `var/private-evidence/source-audit-ap-eief/`; o inventário lossless está em `ap-private-image-relocation.json`.

O proprietário adquiriu a alternativa oficial MEC `ap_curriculo_amapa.pdf` por GET padrão200 e comprovou que é byte a byte o mesmo339 já existente,29.560.905B/SHAfc407...: apenas mirror oficial, sem fonte/adapter duplicado ou ganho de texto nativo. O HEAD200 e a falha403 do canal web foram registrados separadamente. A referência anterior de91MB para o339 foi incorreta e não fundamenta a comparação.

## Fecho do snapshot técnico

Sidecar final: `98ea0d2503f69bfd0ab488ebb87a1b606a21e39987bc51294b317dabbe814bdf`. A contrapova independente passou os2441registros com a ordenação real de produção e bloqueou9mutações controladas. O pin final próprio tem4483fragmentos, schema/idade/loader/finalizer sem falhas,1638células sem falta/extra e nenhuma mudança de helper/source durante o teste. A reconstrução em memória é byte a byte idêntica.

`ap614-source-binding-proposal.json` está com `binding_ready=true` somente para o vínculo técnico deste adapter: contém caminho/hash, componentes, inventário, recortes de autoridade e partes realmente reconciliadas versus contexto pendente. O proprietário do manifesto integra e verifica a Source real. O339 permanece separado e sua extração estruturada integral ainda é trabalho interno pendente; a UF não foi declarada pronta.
