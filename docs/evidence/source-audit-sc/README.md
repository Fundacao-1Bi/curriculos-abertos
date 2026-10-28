# Auditoria documental automatizada de Santa Catarina

Ator: `agent:data_central_south`, tipo `automated`. Não houve revisão humana ou validação pedagógica. Contagem de palavras ou correspondência literal não demonstra equivalência curricular com a BNCC.

## Extrações reproduzíveis

```sh
.venv/bin/python docs/evidence/source-audit-sc/extract_sc_uncoded.py
.venv/bin/python docs/evidence/source-audit-sc/extract_sc_em_uncoded.py
.venv/bin/python docs/evidence/source-audit-sc/extract_sc_c3_objectives.py
.venv/bin/python docs/evidence/source-audit-sc/extract_sc_c3_tables.py
.venv/bin/python docs/evidence/source-audit-sc/verify_sc_adapters.py
```

Os PDFs oficiais permanecem byte a byte em `data/raw/SC/`, fora do Git. Cada registro leva o SHA256 do original, página, caixa geométrica, localizador estável, contexto documental e método de extração. A validação confronta cada fragmento com o PDF original e verifica a junção dos fragmentos contra o texto canônico. Somente hifenização de quebra de linha e marcadores tipográficos são normalizados; o fragmento original permanece na evidência. Não são inventados códigos oficiais, séries ou equivalências.

## Denominadores e tipos

O sumário do Currículo Base EI/EF, páginas 12–13, define os organizadores de Alfabetização, Língua Portuguesa, Arte, Educação Física, Língua Inglesa, Matemática, Ciências, Geografia, História e Ensino Religioso. O inventário independente de cabeçalhos (`ef-header-inventory.json`) enumera as 218 páginas que apresentam coluna explícita `HABILIDADES`/`OBJETIVOS DE APRENDIZAGEM` nesses organizadores. Colunas `CONTEÚDOS`, orientações e objetos adjacentes são guardadas como contexto, sem virar habilidades.

O adaptador preserva 1.202 parágrafos dessas colunas. Três são subtítulos nominais e ficam como `objeto_conhecimento`; os outros 1.199 são habilidades/objetivos. As páginas 444 e 447 têm a coluna de habilidades vazia e somente continuação dos conteúdos: renderização das duas páginas confirma que zero habilidade nova é o resultado correto. O arquivo de auditoria registra também as células vazias.

O complemento Língua Inglesa dos Anos Iniciais contém organizadores dos cinco anos, páginas físicas 15–29. Há 143 habilidades sem código: 23 do 1º ano, 29 de cada ano do 2º ao 4º, e 33 do 5º. Os quadros deslocam a coluna entre páginas; seu reconhecimento considera os limites da coluna direita e exclui as linhas `EIXO` que atravessam o quadro. Todas as quinze páginas estão representadas. Número impresso não identificado automaticamente permanece nulo.

No caderno 2 do Ensino Médio, quatro habilidades adicionais explicitamente marcadas como demandadas da consulta pública aparecem nas páginas físicas 30, 32 e 33. Não recebem códigos BNCC por semelhança com outras habilidades. A extração restringe a caixa à coluna de habilidades, impedindo que rótulos como `Matrizes` e `Polinômios` da coluna vizinha se misturem ao objetivo.

O caderno 4 apresenta 25 listas gerais de objetivos das eletivas e 121 listas de objetivos das unidades. Os 146 cabeçalhos produzem 400 itens, preservando inclusive o marcador `»` e um marcador duplicado desenhado no original. `Resumo`, indicações e etapas de trabalho ficam fora dos objetivos. Contexto inclui curso, grupo, unidade, carga horária e caixas das células. Um título de unidade começa fisicamente na página seguinte: o objetivo da página 303 liga-se ao título `As Diferentes Moedas no Brasil` explicitamente impresso na primeira linha continuada da página 304; a prova das duas páginas fica no registro. Não se herda o título da unidade anterior.

O caderno 3 contém 33 cabeçalhos explicitamente rotulados `Objetivo(s)`, identificados independentemente antes da extração. Produzem 40 objetivos, uma introdução contextual e cinco unidades/subtemas. O cabeçalho 5.9.3 repete `Objetivo da trilha de aprofundamento`, mas seu corpo lista unidades e subtemas: a renderização da página 294 comprova que esses cinco registros são estrutura curricular, não habilidades. O adaptador complementar cobre as colunas e linhas explicitamente rotuladas de habilidades: 1.111 registros adicionais, com 22 continuações físicas conferidas em pares de páginas. Os 1.157 registros combinados preservam habilidades, estruturas, palavras-chave e fragmentos incompletos em tipos separados. O original imprime `Prom` isolado na página 232 e `nvestigar` na página 217; essas falhas não foram reconstruídas editorialmente. As hierarquias usam o cabeçalho acima de cada tabela, incluindo a divisória integrada sem número da página 163.

## Verificações efetivamente executadas

`all-record-literal-validation.json` fixa hashes dos adaptadores e registra a verificação de todos os seus registros, não somente uma amostra. A amostra visual inclui os nove componentes do EF, continuação de Língua Inglesa AI, habilidades de consulta pública, listas gerais e listas em células das eletivas, além de objetivos gerais, objetivos específicos e cabeçalho incorreto das trilhas. Os PNGs são renderizações reais dos originais.

Correspondência literal integral dos adaptadores não equivale à reconciliação integral das fontes. Fundamentos, competências, conteúdos, estruturas e tabelas adicionais continuam no inventário obrigatório. Não foi criado sinal de prontidão da UF nem sidecar de reconciliação com denominador copiado dos itens extraídos. Cadernos 5/6 são processados em frente independente, com evidências em `source-audit-sc-ept/`.

A revisão dos contextos do Caderno 4 confirmou na página 15 a declaração de 25 roteiros. As capas das páginas 107, 121, 181 e 230 não contêm RESUMO na mesma página; seu reconhecimento foi corrigido e renderizado em `c4-25-courses-corrected-covers.png`. A verificação literal mais recente cobre todos os 2.906 registros das cinco fontes, com zero falhas, sem alegação de prontidão da UF.
