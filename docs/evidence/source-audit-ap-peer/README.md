# Peer AP: censo primário e contrapova de integração

Ator automatizado independente do autor do adapter. A inspeção não altera Source, PDF, adapter, caches, código do produto, banco ou publicação. Não constitui revisão pedagógica humana e não declara a UF pronta.

O censo primário foi gravado antes da leitura do snapshot `c42e19c06479cce379d7663f161b08c9e82acb8f8fd483f0fd122b1ff0bad2b3`. São fontes distintas: o PDF nativo de 614 páginas, SHA `23c42348e0b0e00d4135a108366141a257bec54b7b1bff79e521c822d9903f89`, e o de 339 páginas, SHA `fc40788a0165eb6fa61d713cee87d4b0b95b45435e496b43bb477f9471a103c4`. Não se afirma identidade de edição ou alias global entre seus códigos.

`primary-census.json` inventaria todas as páginas nativas dos dois PDFs. A busca literal da edição 614 encontra 93 códigos EI únicos, uma ocorrência por código, nas páginas 93–131. Essas mesmas páginas contêm 465 glifos de apresentação U+F0B7. `ei-primary-inventory.json` congela cada código, cada glifo por índice rawdict e bbox e os cabeçalhos etários nativos. O censo não depende dos 93/465 registros do adapter. A busca de formas EF sobre o texto nativo completo conta ocorrências, incluindo referências dentro de parágrafos; não é tomada como denominador aprovado de habilidades distintas.

Os 35 localizadores de continuação foram fornecidos pelo autor sem texto ou item de destino. `continuation-primary-inventory.json` os relê no PDF com `find_tables(strategy='lines_strict')`, congela os textos/células físicas e acrescenta a célula própria de História na página 529. A lista é uma amostra direcionada de células sem código, e não um censo independente de todas as continuações do corpus. A prova confere toda a redação dessas células, não somente seus inícios. `structure-primary-inventory.json` guarda ainda as linhas, números, rótulos e direções dos diagramas/listas indicados no documento, antes de inspecionar as saídas correspondentes.

`verify614.py` usa o checker comum com páginas `sort=True`, como o `extract_pdf` real. A contrapova inicial encontrou **25 registros que falham em produção**, embora o verificador do autor passasse com páginas em `sort=False`: 16 competências em diagramas nas páginas 162/182 e nove seções/títulos com bboxes amplos. O achado foi enviado ao autor e ao coordenador para corrigir somente os fragmentos e regiões de evidência, mantendo texto, código, chave, pai e o checker. O resultado anterior permanece em `verification614-before-locator-fix.json`; esse estado não é apresentado como aprovado.

A conferência física dos 93 objetivos e 465 experiências compara os caracteres completos dos fragmentos, retirando apenas whitespace e os marcadores/códigos de apresentação que têm evidência própria. Usa palavras inteiras pelos centros dentro da região, evitando que o recorte textual importe apenas descenders de linhas adjacentes. Cada um dos 465 glifos tem um único registro de experiência na mesma linha nativa; quatro bullets cujo bbox está à esquerda do texto são vinculados pelo índice exato bloco/linha, sem aproximação semântica. Os pais são confrontados com a coluna física de objetivos e o fluxo de continuação; cada microfaixa é conferida contra o cabeçalho literal da própria coluna. As 35 continuações e o item sem código de História preservam integralmente as respectivas células; História529 não recebe à força um código anterior.

A origem primária mostra microfaixas numéricas distintas dos grupos amplos. A contrapova encontrou que `age_label` preservava a microfaixa, mas a evidência aninhada apontava o grupo macro e o portal/SQL só tratavam `age_group`. O coordenador confirmou FUN-03 e atribuiu ao domínio/portal o contrato de filtro por intervalo documentado; o autor do adapter acrescentará limites explícitos e evidências dos cabeçalhos micro/macro. Não se deduz intervalo de “BEBÊS”, de código EI ou de proximidade textual. Sobreposições de extremidade expressas na fonte permanecem sobrepostas, como 0–12/12–18 meses e 19–24/24–47 meses. `baseline2441-identities.json` congela as identidades, redações, códigos, pais e provas anteriores para conferir o delta autorizado.

Na edição 339, o texto nativo não contém códigos EI/EF legíveis. `legacy339-ocr-inventory.json` confere a integridade dos 343 arquivos de OCR existentes, cobrindo todas as 339 páginas (a página 95 tem cinco configurações). Zero hashes de resultado ou identidades de cache divergiram. Isso prova apenas integridade e proveniência dos candidatos de OCR; os 72 matches literais de código não são aceitos como denominador ou redação correta. Não houve novo OCR, reparo de código ou equiparação entre as edições.

```sh
# Inventários primários; preservar os originais antes de reproduzir qualquer denominador.
var/venv-pipeline/bin/python docs/evidence/source-audit-ap-peer/inventory.py primary
var/venv-pipeline/bin/python docs/evidence/source-audit-ap-peer/inventory.py ei
var/venv-pipeline/bin/python docs/evidence/source-audit-ap-peer/inventory.py continuations
var/venv-pipeline/bin/python docs/evidence/source-audit-ap-peer/inventory.py legacy
# O verifier exige explicitamente o SHA do snapshot auditado.
var/venv-pipeline/bin/python docs/evidence/source-audit-ap-peer/verify614.py
```

As execuções completas de pipeline, importação, API/MCP/portal e produção continuam separadas. A fronteira desta contrapova é literal/documental; páginas processadas, OCR íntegro ou contagem de códigos não substituem reconciliação da UF.

## Resultado após correção verificado

O snapshot `98ea0d2503f69bfd0ab488ebb87a1b606a21e39987bc51294b317dabbe814bdf` passou **2.441/2.441 registros no checker de produção com `sort=True`**, zero falhas. A comparação ao baseline anterior confirmou igualdade de todos os textos, códigos, chaves, pais, tipos e campos de posição preexistentes. Trinta e três registros receberam localizadores mais precisos (17 seções e 16 competências dos dois diagramas); as 25 falhas de integração anteriores foram eliminadas sem modificar o checker ou o texto.

As 558 expectativas/experiências EI receberam intervalos derivados apenas dos números e unidades nos cabeçalhos primários, com evidência macro e, nas 465 experiências, também micro. O peer conferiu cada intervalo, trecho, caixa, coluna e dono de bullet. Todas as 36 células do recorte de continuação/História foram preservadas. `verification614.json` registra 12.457 verificações de campos/identidades e zero erros; isso não é apresentado como 12.457 testes funcionais do produto.

`negative-verification.json` registra nove corrupções reais apenas em cópias de memória e controles positivos: pai falso com campos internos consistentemente alterados; troca pela microfaixa real da outra coluna com limites/evidência válidos em si; limite numérico inventado; intervalo deduzido do nome macro sem cabeçalho numérico; omissão da última experiência; duplicação que mantém contagem465 mas perde uma âncora; palavra inventada; código inventado; e remoção da última palavra de continuação. Todas foram bloqueadas por suas respectivas provas independentes ou pelo checker comum. O adapter e a publicação permaneceram intactos.

O probe privado `cross-edition-printed-code-probe.json` corrigiu um exemplo impreciso recebido durante a coordenação: os pixels mostram **EF15LP-AP01 em ambas** as páginas selecionadas (339p116 e614p240). A forma OCR `EFISLR-APD1` não foi aceita como código. O exemplo não demonstra diferença de hífen nem identidade global entre as edições. Os dois recortes pequenos permanecem em `var/private-evidence/source-audit-ap-peer/`, fora da distribuição versionada, com seus hashes no relatório.

A contrapova literal/documental do recorte solicitado está sem achados residuais. A reconciliação integral da edição339, a decisão editorial de cobertura/edição, a consulta por idade no produto e a candidata/importação/portal/API/MCP/produção finais continuam verificações distintas.

O ensaio adicional `loader-schema-verification.json` executou o loader/finalizer reais com páginas `sort=True`: 2.441 carregados, zero rejeitados e 2.441 finalizados, todos válidos no schema1.1 e com campos canônicos/posicionamentos preservados. Validou a metadata de contexto real sem desativar regras legadas. O binding está explicitamente marcado `temporary_proposed_path_only`: no instante do ensaio o Source614 no manifesto ainda não apontava ao novo adapter. A aplicação serial do path/autoridade e o FULL permanecem passos de integração do coordenador, sem substituir esta distinção por um pronto manual.
