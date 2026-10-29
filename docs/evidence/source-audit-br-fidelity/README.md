# BR: conferência de fidelidade de 394 ocorrências

Ator: auditor automatizado independente. Esta pasta não substitui reconciliação nacional nem revisão pedagógica humana. Nenhum cache, manifesto, PDF, dataset de origem ou nó de estrutura foi editado pelo auditor. A proposta de nova extração corrige explicitamente oito textos, sob a decisão B registrada abaixo, preservando IDs, códigos e redações anteriores.

## Denominador e fontes

O denominador foi fixado antes das propostas: 305 falhas do documento BNCC 2018 e 89 do complemento Computação 2022, extraídas de `data-preflight-native-baseline.json`. `inventory.py` verificou os SHA-256 dos dois PDFs e inventariou todas as ocorrências nativas de códigos nas páginas completas, sem consultar as redações esperadas: 1.637 ocorrências BNCC e 142 de Computação. Depois congelou os 394 payloads de origem e hashes de caches em `baseline-records.json`. Os caches permaneceram intocados e seus hashes foram reconferidos ao fim.

Os dados estruturados reutilizados preservam atribuição `bncc-dev/bncc-dados`, commit `9c268978efa2aa250834c6a9edb6074432752838`, CC-BY-4.0. Os PDFs primários mantêm seus direitos e proveniência próprios; os recortes desta pasta servem à conferência técnica. Não há redistribuição dos PDFs aqui.

## Resultado original, antes da integração ao pipeline

As 394 ocorrências foram confrontadas por palavras nativas, rawdict, trace, limites da célula, código e render real do recorte. Os 394 recortes foram renderizados e tiveram checksum, dimensões e pixels não vazios conferidos. Nenhum bbox contém código de outra célula; todos permanecem na página física original indicada pelo dataset. O texto completo destas 394 aprendizagens foi localizado na respectiva página; não foi necessário inventar continuação multipágina.

- 372: bbox de texto nativo exato. Três delas também aparecem como exemplo na página 28; foi mantida a página 50 expressamente indicada na proveniência, com código e texto completos comprovados nessa própria página. Não foi feita união de ocorrências de páginas distintas.
- 2: bbox de bloco resolveu ligaturas da extração nativa.
- 7: trace dos glifos visíveis, pelo método já existente, resolveu diferenças de serialização de quebras, barras e hífens.
- 5: prova tipográfica por registro, usando somente a política já existente de quebra/whitespace/hífen, com palavras e texto canônico preservados.
- 8: diferença tipográfica real: o PDF contém U+2013 EN DASH e o dataset reutilizado U+002D HYPHEN-MINUS. São 16 glifos. A igualdade de todos os demais caracteres foi comprovada após colapso de whitespace e essa única substituição explícita. O verificador original continua recusando esses oito; isso não foi escondido como correção de locator.

`verification.json` e `proposals.json` preservam o resultado histórico **386/394 no verificador original antes da decisão B**. `dash-typography-proof.json` conserva o texto primário literal, hashes, posições e bboxes de cada um dos 16 glifos. A hipótese inicial A manteria o texto do dataset e exigiria um contrato adicional de equivalência tipográfica; foi rejeitada pelo coordenador em favor de transcrever a pontuação primária no texto canônico de uma nova extração.

## Decisão B e conferência integrada executada

`transcription-decision.json` registra a decisão explícita do coordenador para DAT-01/04/05: nas oito redações, `text` recebe a pontuação literal U+2013 do PDF, com somente whitespace de apresentação colapsado. `upstream_text` conserva exatamente a string CC-BY anterior; `primary_source_text` conserva as quebras e a pontuação do excerto nativo. `primary_transcription_correction` registra origem, hashes, diferenças, glifos, bboxes e a decisão. O evento automatizado descreve correção de extração, sem alegar emenda ao currículo oficial nem aprovação pedagógica humana. As publicações anteriores permanecem imutáveis. A futura revisão cumulativa de extração será `page-cell-v1.5.0`.

O helper do pipeline aplica a proposta por SHA do PDF, ID, código e hash da redação de entrada. Apenas os oito códigos autorizados podem mudar texto; exige `whitespace(primary_source_text) == text` e que a reversão **apenas nesses registros** de EN DASH para hífen ASCII reproduza o upstream byte a byte. Isso é uma guarda sobre as oito alterações autorizadas, não um normalizador de busca ou um bypass do verificador. O método provisório A `primary_pdf_exact_glyph_mapping_v1` foi removido do checker comum.

`verify-integrated.py` executou a extração dos dois PDFs reais em memória e o checker comum sobre **1.721/1.721 registros licenciados**, incluindo **394/394 locadores revisados**. Conferiu os 1.713 outros textos byte a byte, as oito strings upstream, todos os IDs/códigos/aliases/posições/pais/atribuições e os dois sidecars estruturais congelados. Conferiu também a ausência do bypass A e o isolamento por deep copy das provas. `integrated-verification.json` contém os hashes do helper, checker, proposta e entradas. Não houve escrita de cache, importação, promoção ou modificação da publicação servida; esta prova não substitui a conferência da futura candidata FULL.

Os negativos controlados incluem SHA da fonte incorreto, ID sem correspondência, código/redação adulterados, prova pinada alterada, corrupção de upstream/primário e tentativas de alterar palavras, dígitos ou outra pontuação — inclusive recomputando os hashes internos da proposta. Cada uma das oito redações também foi desafiada contra o PDF com palavra, dígito, pontuação e upstream ASCII incorretos. Todos devem permanecer bloqueados; o relatório conserva cada resultado.

## Fronteiras e inspeção visual

A comparação de blocos completos revelou merges de células adjacentes por ano escolar, rótulos da coluna de objetos e números da coluna de competências. Esses elementos não foram incorporados à redação da habilidade. Em especial, o `7` ao lado de EM13LP11 é a coluna de competências, e não nota ou continuação da habilidade. A prova e render `bncc-p510-adjacent-competency-column.png` mostram essa fronteira.

Foram inspecionados visualmente os dois painéis de oito registros com travessões destacados, os cinco painéis de 21 casos críticos (quebras, ligaturas, células mescladas, códigos repetidos e colunas adjacentes) e páginas de contexto. Isso complementa, sem se passar por leitura humana individual das 394 redações, a conferência automatizada integral de todos os registros.

A regressão EF05CO011 foi conferida em palavras nativas e imagem da página 36. Mantêm-se ID `ca:br-bncc-computacao-2022:EF05CO11`, código literal `EF05CO011` e alias documentado `EF05CO11`. Nada foi corrigido por igualdade de código ou proximidade textual.

## Reprodução sem publicação

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-br-fidelity/inventory.py
var/venv-pipeline/bin/python docs/evidence/source-audit-br-fidelity/analyze.py
var/venv-pipeline/bin/python docs/evidence/source-audit-br-fidelity/propose.py
var/venv-pipeline/bin/python docs/evidence/source-audit-br-fidelity/verify-proposals.py
var/venv-pipeline/bin/python docs/evidence/source-audit-br-fidelity/verify-integrated.py
var/venv-pipeline/bin/python docs/evidence/source-audit-br-fidelity/normative-2024-2025/verify.py
```

A primeira etapa só deve ser repetida quando houver razão para substituir o baseline congelado. `verify-proposals.py` reproduz o estado histórico anterior à decisão B e sobrescreve a proposta final; não deve ser executado sobre a prova pinada final sem preservar a versão vigente e coordenar novo SHA com o pipeline. A conferência corrente é `verify-integrated.py`. As verificações gravam exclusivamente esta pasta e não importam ou publicam dados.

`normative-2024-2025/` separa o inventário independente das fontes normativas posteriores da conferência das saídas: 22 páginas da DCN 2024, 24 dos parâmetros IFA 2025 e 13 da Educação Digital/Midiática 2025. Retenção de páginas jurídicas não é contagem de aprendizagens; o anexo IFA tem denominador próprio de objetivos/competências/capacidades. Qualquer fonte ainda sem saída permanece explicitamente pendente no relatório.
