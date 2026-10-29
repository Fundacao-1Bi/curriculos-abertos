# Peer independente PI EI/EF: seis migrações técnicas

Aceite técnico automatizado restrito aos seis pares da ledger pinada `73817aff990326ca9cb7a1cb9456be9a7f942d2f73b24e4b12b0d0c97e9010ed`. Nenhum texto dos seis pares foi alterado. As migrações substituem IDs/localizadores de recuperação por regiões do parser direto; não são seis alterações de redação, equivalências curriculares ou alterações oficiais.

O censo `primary-census.json` foi fixado a partir somente do PDF primário de 313 páginas, SHA `609e955a2774afe6b25451b6d597005fcedc9b769cbf1a00916caaaab40f426e`, antes de ler os resultados do produtor. Cada código tem uma ocorrência nos seis slots: p257 EF02GE03 e EF02GE11; p265 EF07GE011.01PI; p269 EF09GE04; p279 EF05HI06; p281 EF06HI16. O identificador irregular de p265 foi preservado literalmente. Corpo completo, limites físicos, Unicode, fonte, glyph/origin e trechos são confrontados com a fonte. Os seis recortes privados tiveram leitura visual; seus hashes e caminhos estão em `private-crops.json`, sem publicar imagens do PDF.

O finalizador real confirmou os seis pares old/new IDs, código, tipo, posições e pai; o multiconjunto página/código do recorte permaneceu 392→392, com exatamente seis IDs removidos e seis adicionados. O checker literal real e o JSON Schema passaram nos 429 registros do candidato (392 codificados e 37 seções), sem erro. Seis controles negativos bloqueiam ID de outra ocorrência, truncamento simultâneo de texto/trecho, posição indevida, reparo convencional do código irregular, expansão ASCII de `ﬁ` alegando identidade Unicode, e promoção indevida do recorte de 37 para as 313 páginas.

O achado P2 foi corrigido nos metadados do produtor: as regiões novas de p265, p279 e p281 incluem linhas físicas adjacentes. Elas não devem ser descritas como células físicas exatas. O parágrafo alvo foi provado completo separadamente. As versões anteriores da ledger/prova estão preservadas nesta pasta; a revisão final conserva todos os IDs, códigos, localizadores, métodos e pins dos caches, acrescentando a descrição correta e a evidência física independente.

A cadeia completa de provas do produtor e seus seletores por par foi conferida criptograficamente. O relatório histórico `pi-eief-isolated-parser-probe.json` registra findings antes da ledger e não é apresentado como aprovação global. Os 1.145 witnesses da auditoria do produtor contam regiões/APIs; este peer não os apresenta como 1.145 ligaturas físicas únicas verificadas independentemente. A independência de corpo completo deste peer cobre os seis slots. Os demais registros do recorte passaram literal/schema, o que não prova completude de todos os seus corpos.

O cache de produção permaneceu com SHA `18087f5d7d80975c943577d56228d984678645f56fc84ff382843df096a12d5e`, idêntico ao cache anterior completo. O candidato `fa8ad3f4feeceb3032e7fc7e5ed89efbc8725ceb288c39254f70f13c16db889f` é apenas o recorte de 37 páginas e não deve substituir o cache integral. Source/core/cache/candidato/DB/publicação não foram modificados pelo peer. Binding e atualização integral pertencem a outra execução, seguida de nova verificação. Não há declaração de SourceWhole, UF pronta ou revisão humana/pedagógica.

Reprodução, a partir da raiz do repositório e preservando os pins dos insumos:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-pi-eief-glyph-peer/census.py
var/venv-pipeline/bin/python docs/evidence/source-audit-pi-eief-glyph-peer/verify.py
var/venv-pipeline/bin/python docs/evidence/source-audit-pi-eief-glyph-peer/receipt.py
```

`receipt.py` sela o hash da execução original de `verification.json`; uma repetição de `verify.py` gera novo timestamp/hash e requer recibo novo explicitamente revisado, sem substituir o aceite histórico silenciosamente.
