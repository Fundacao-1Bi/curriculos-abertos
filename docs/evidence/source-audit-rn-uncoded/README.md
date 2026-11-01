# RN Trilhas — objetivos sem código e hierarquia documental

Fonte privada original `rn-trilhas-aprofundamento`, 485 páginas, SHA-256 `fac7333112fcfaac3d99d74f72f206bea8e9a4b256e770a9ea0f2eace99b027a`. Edição literal: **1ª versão**. A data do endereço do arquivo não foi transformada em edição, adoção ou vigência.

Ator autor: `agent:rs_adapter`, automatizado. Peer: `agent:portal`, automatizado, com inventário próprio anterior ao output. Não houve revisão humana ou certificação pedagógica. A integração nacional continua distinta da execução local.

## Denominador documental

O peer confrontou o sumário das páginas11–12 com o quadro sinóptico da21: **33 trilhas em7 grupos** (4/4/4/6/5/5/5), com variantes literais de título e numeração preservadas. A regra nominal das páginas24/29 (seis UCs e dois módulos) não foi usada para fabricar registros. Seu censo independente do corpo encontrou **198 cabeçalhos de UC**, seis por trilha; **33 pares de objetivos geral/específicos**; e **617 rótulos físicos de módulos**, separados das menções em prosa.

O censo autoral parte do original, não de IDs de aprendizagem. As33 regiões específicas contêm **152 círculos vetoriais impressos**. Cada círculo delimita um objetivo, mesmo quando o texto contém vários verbos ou ponto e vírgula. Há33 objetivos gerais, totalizando **185 objetivos locais sem código**. A concatenação das33 regiões gerais e das33 regiões específicas coincide integralmente com a transcrição independente do peer; contagem por pontuação não substitui os marcadores físicos.

O corpo contém1.875 cabeçalhos de campos:362 Ementas,396 Objetos do Conhecimento,323 Sugestões Didático-Metodológicas,199 Sugestões de Avaliação,199 Sugestões de Fontes,198 formações docentes e198 cabeçalhos de referências dos eixos. Seus175 fragmentos sem novo cabeçalho são continuações, preservadas com página/coluna/caixa e ligação ao campo anterior na ordem física esquerda→direita→página seguinte. São2.050 fragmentos físicos, não2.050 novos campos.

`rn-trilhas-complete-cell-inventory.json` guarda todos os campos, seus textos/caixas/continuações, todas as regiões de objetivos, rótulos de módulo e exclusões classificadas. Das26.731 linhas nativas horizontais em páginas de UC,24.892 pertencem a nós de conteúdo e1.839 são cabeçalhos/rodapés classificados; nenhuma ficou sem destino e não há propriedade duplicada de linha. A partição inclui os cartões e títulos, além dos campos. Incluindo também capas de trilha e overviews, o corpo31–484 tem29.145 linhas horizontais:27.186 atribuídas e1.959 exclusões classificadas, sem linhas perdidas. Os33 cabeçalhos de grupo, inclusive repetições, ficam preservados no contexto dos sete grupos.

## Semântica e hierarquia

O sidecar tem3.851 nós com `code:null`. Documento→grupo de áreas→trilha→UC→módulo quando delimitado por rótulo/barra. Há nós próprios para problemática, temas transversais, título do overview, índice de UCs, formação docente, Ementa, objetos, metodologia, avaliação e bibliografia. Esses campos não foram promovidos a habilidades. Os objetivos locais pertencem à trilha; a formação do professor não infere componente curricular de aprendizagem. Etapa EM e área vêm dos cabeçalhos; ano/período permanecem nulos.

As617 ocorrências de “Módulo n” pertencem a **395 chaves de número efetivamente impresso por UC**, com todas as ocorrências físicas no contexto. A UC iniciada na403 imprime somente Módulo1, inclusive nos dois blocos com Ementa: não existe Módulo2 fabricado para satisfazer396nominais. A UC436 imprime a sequência1→2→1; campos e barras conservam essa contradição. A última parte de Fontes na438 continua a bibliografia da437direita, mesmo fora da barra rotulada. Barras curtas podem acabar antes da última linha de um parágrafo; não há nova atribuição sem novo cabeçalho. Uma barra não rotulada contida numa barra maior da369 é redundante. A revisão visual de nove segmentos candidatos concluiu que os outros oito não têm rótulo próprio: permanecem no contexto da UC como traços visuais sem escopo atribuído e não criam chave de módulo nem recebem herança entre coluna/página. O registro da correção está em `rn-trilhas-cross-column-scope-fix-20261031.json`.

O original contém **741 cartões de referências** e **2.882 citações de códigos**. O helper compartilhado `rn_document_roles` conserva essas citações como `referencia_no_documento`, sem lhes atribuir a Ementa ou o texto vizinho. As **48 definições** reais das folhas16–19 continuam sob seus quatro quadros de área e16 rótulos de eixo. O sidecar adiciona2.930 vínculos por seletor exato `page/locator/code`; não busca o primeiro código repetido. A referência documental e o contexto de UC não declaram equivalência curricular ou vínculo objetivo↔código que o texto não imprima.

O sumário repete4.1.1.3 para duas trilhas; o corpo da75 imprime4.1.1.4. A numeração de cada representação fica em campo separado, e `source_number` usa a redação do corpo. O sumário trunca “O Corpo Humano Como”; “Emponderamento”/“Empoderamento” e “Serão”/“Sertão” também variam entre os quadros. Os campos preservam cada representação, com chaves técnicas diferentes. Objetivos com círculos não recebem números originais inventados; o ordinal é apenas técnico.

## Evidência e execução

`rn-trilhas-layout.py` usa o cache nativo geométrico comprimido e os inventários vetoriais fonte-only. `rn-trilhas-build.py` usa o helper compartilhado de códigos e `NativeGlyphText`; não modifica parser global, manifesto NE ou PDF. Evidências incluem trecho, página, caixa, localizador e ator automatizado. A ordenação nativa `sort=True` inverte rótulos rotacionados (“1 Módulo”); esses395 nós usam o ramo explícito `pymupdf-native-glyph-cluster-v1`, leitura literal no bbox exato, sem alegar certificação de visibilidade. O cartão guarda a leitura física por coordenadas no texto canônico e o stream nativo em `original_cell_text`/`reference_codes_literal`; a ordem do stream não é apresentada como ordem visual. A política de oclusão criada para MS não foi generalizada: a página90 tem rótulo visível que uma caixa de desenho composto classificaria incorretamente como coberto.

O teste real usa snapshot privado e imutável de `pipeline/*.py`, com hashes em `rn-trilhas-parser-snapshot.json`. Apenas `ingest.ROOT` aponta aos dados reais; `runtime.ROOT` permanece no snapshot e os guards de fingerprint continuam ativos. `write_extraction_cache` é interceptado integralmente no processo do teste: o parser real percorre485páginas e o resultado fica em RAM, sem invalidar ou escrever o cache compartilhado.

Comandos:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-uncoded/rn-trilhas-scan.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-uncoded/rn-trilhas-scope-census.py
var/venv-pipeline/bin/python data/manifests/uncoded/rn-trilhas-build.py
TESSDATA_PREFIX="$PWD/var/tessdata" RN_PROBE_PIPELINE="$PWD/var/private-evidence/source-audit-rn-uncoded/parser-snapshot-20261028-disjoint" var/venv-pipeline/bin/python data/manifests/uncoded/rn-trilhas-verify.py --full
```

O sidecar cobre integralmente o corpo curricular31–484 e a hierarquia das definições16–19. A página485 é contracapa gráfica com brasão/logo e ISBN: não contém texto nativo nem conteúdo curricular. O render privado confirmou que não é uma página em branco. O restante das páginas1–30 conserva contexto documental genérico; a autoridade proposta suprime somente seções genéricas16–19 e31–485, em intervalos disjuntos. Não se declara prontidão de RN, inclusão em release nacional ou revisão pedagógica a partir desta entrega. O peer integral e o relatório do importador/finalizador são evidências separadas.

## Estado

Implementado, executado e verificado: parser real de485páginas;3.851/3.851 nós importados;6.807 registros finais (3.851 estruturais/locais +2.930 codificados preservados +26 contextos documentais únicos); esquema1.1.0/pais/ciclos/idempotência sem falhas; nove controles negativos aprovados;21.423 regiões conferidas diretamente. Peer independente integral PASS:774.445 glifos elegíveis,1.875 cabeçalhos,198UCs,395 chaves de módulo,741 cartões e2.930 vínculos; nenhuma falta/extra. Seu testemunho preserva os controles específicos da fonte187/346 (soft-hyphen e U+200B), sem substituição no texto canônico.

O inventário dos30contêineres frontais prova cobertura de12.375 glifos nas folhas16–19, inclusive rodapés; quatro redundantes são suprimidos e26 contextos1–15/20–30 preservados. O SHA anterior do sidecar (`551f90cca125541f09975b3d62f8457695a4cdc7a742f096360f609854749602`) foi validado pelo relatório integral então vigente. Após a correção de atribuição de escopo, o sidecar atual tem SHA `269729c19ae872c599586306f84c6f229612d427ccd387d570e580590504028c`; a reexecução do importador/parser integral e a atualização do handoff estão pendentes. Não se reutiliza a validação anterior como prova do hash novo. Prova consolidada/hashes anterior: `rn-trilhas-integration-handoff.json`.

O proprietário NE integrou o Source. A conferência somente de leitura `rn-trilhas-active-source-wiring.json` confirma path, hash, helper e autoridade disjunta; não regrava cache nem comprova inclusão nacional. Pendente: futura incorporação no artefato nacional imutável. A contracapa485 tem OCR executado, com18/29 palavras de baixa confiança registradas; não é conteúdo curricular e não entrou como novo objetivo. Não se declara prontidão de UF. O cotejo MS681 no futuro FULL permanece aguardando caminho/SHA. Nenhum commit ou ação remota.
