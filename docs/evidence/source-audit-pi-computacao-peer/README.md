# Peer técnico independente — PI Computação, referências narrativas

Resultado: **PASS técnico automatizado**, limitado às 28 páginas declaradas. Não é revisão humana, aprovação pedagógica, reconciliação integral das 137 páginas, UF pronta ou autorização de lançamento nacional.

Fonte `pi-computacao-em-2025`, PDF `data/raw/PI/pi-computacao-em.pdf`, SHA256 `e6eda1fbcf82e4fb5554ce121ec3b6c1bdf13c9345ef716658c0946a1a71e61f` (2.156.942 bytes, 137 páginas físicas). Candidato `data/manifests/uncoded/pi-computacao-narrative-reference-items.json`, SHA256 `473df933616bf2dc6d67b75a93de210ca7d4202298d032848a43a474f0c29627` (1.394.376 bytes). Ambos ficaram inalterados durante o peer.

## Inventário primário anterior ao candidato

O dono forneceu inicialmente somente Source, SHA, páginas e limites físicos. `primary-census.py` leu o original, capturou as linhas e geometria e fixou `primary-census.json` **antes** de abrir candidato ou ledger autoral. SHA do censo: `feeaced17ee5f385178282bb5c1ad4356fd9613c1ba238c5a01cc62ba1fc0af7`.

Recorte físico: 51, 52, 55, 59, 61, 63, 67, 69, 71, 75, 79, 81, 84, 86, 91, 93, 96, 97, 99, 100, 102, 104, 107, 108, 109, 111, 116 e 123; corpo [40,40,805,555] após normalização nativa em memória. Denominador independente: 28 páginas, 595 linhas nativas, 172 ocorrências de citações a 50 códigos diferentes e **zero novas definições de habilidades nesse recorte**. Repetições permanecem ocorrências distintas, sem deduplicar evidência.

Cada página continua a seção impressa “RELAÇÃO ENTRE AS HABILIDADES” de página anterior; o censo registra essa âncora. São comentários sobre articulação, paráfrases, exemplos e propostas pedagógicas. Citar um código em tal comentário não cria nova habilidade local nem autoriza herdar o texto nacional.

As imagens privadas 51/77/116/128/136 foram inspecionadas. A página 116 contém o quadro “Habilidade / Contribuição à Relação”, seguido de comentário; não é matriz de definições. A página 77 é **somente comentário**, com cabeçalho “RELAÇÃO ENTRE AS HABILIDADES”, e permanece excluída por conservadorismo do recorte. Corrige-se assim a descrição inicial de que 77 seria mista. As páginas 128 e 136 combinam matriz de definições e comentário e ficam fora da authority. Não se suprimiu nada nessas três páginas.

## Cotejo e replay reais em memória

`audit.py` compara todos os 172 códigos com a ordem e a posição físicas do censo próprio. Cada registro deve ter `kind=referencia_no_documento`, `text=code=code_original`, `positions=[]`, pai nulo, evidência nativa do código e contexto integral da página. O contexto integral e a âncora de seção foram conferidos contra o PDF, preservando acentos, caixa e pontuação; apenas whitespace de extração é normalizado na comparação.

Executou-se o loader, finalizer, verificador literal e schema 1.1 de produção, com Source **clonada** em memória: `coded_learning_ranges` contém somente os 28 intervalos unitários; não há supressão `uncoded_page_sections`. O cache 1.5 real, SHA `4e843a787df4d49f081f5bcdeb38c858ba11e09a192bdab42d45bffb3d190219`, correspondia à Source real e permaneceu byte-idêntico.

Resultado: 172 referências específicas, 638 registros finais totais (não são 638 habilidades). Os 438 itens fora do recorte e todos os 136 registros genéricos de contexto de página permaneceram byte-idênticos. Nas páginas excluídas 77/128/136, respectivamente 14/11/11 itens de baseline foram preservados. Nenhuma hipótese genérica codificada permaneceu dentro dos 28 intervalos substituídos.

O teste de correspondências incluiu contexto nacional real dos caches existentes, com 48 códigos coincidentes. Nenhum vínculo foi emitido envolvendo as 172 referências. Vínculos próprios do contexto nacional são alheios a essa asserção: a primeira versão do checker exigiu incorretamente ausência de todos os vínculos, inclusive internos ao contexto; a correção restringiu a asserção aos membros do recorte auditado. A falha inicial foi preservada em `execution-initial-context-assertion.log`; não houve alteração de dados para obter PASS.

Seis controles negativos recusaram promoção de referência a habilidade, posição de ano inventada, texto nacional inventado, pai inventado, alteração do comentário da última página e texto inventado no checker de produção.

## Recibos e limites

- `verification.json`: SHA256 `5ca80919680e0da9a071a2b7dbbe27d65d5f29cdbd6d95d63cfeb751989ec0e7`.
- `ids-receipt.json`: os 172 IDs esperados pelo inventário físico e os 172 IDs verificados, com o hash do relatório.
- `execution.log`: execução final do replay; `primary-census.py` e `audit.py` são reproduzíveis na raiz do repositório usando `var/venv-pipeline/bin/python`.

Não houve alteração Source/MF, core, sidecar, cache ou banco; não se executaram builder autoral, extração, OCR, build ou aquisição. SourceWhole, páginas mistas fora do recorte, vigência, adoção e prontidão estadual/nacional não foram aprovadas por este peer. Binding e refresh posteriores são responsabilidades separadas do dono e da integração.
