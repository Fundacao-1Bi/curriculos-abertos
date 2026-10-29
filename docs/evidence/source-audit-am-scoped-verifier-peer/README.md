# Peer do verificador de pixels por Source

Aceite técnico automatizado de `pipeline/raster_review_scoped.py`, SHA `3808cc1a5ab930bfac8edeebc853bc6f5716e1abd394fd0352de792c13eda2b3`, dependência geométrica legada byte-idêntica SHA `8774d4372d0c0d83e73ccabd80d98dafec28f0723e7e5da8ead0c9aa78413781`. Este peer verifica a reconstrução e a proveniência de recortes de **códigos documentais**; não confere corpos de habilidades, aprendizagem, equivalência nacional ou integralidade de Source.

O replay real selecionou somente `am-rca-ei`: 153 slots pinados, 152 referências `referencia_no_documento` e um slot de prosa rejeitado sem item. As referências mantêm `code == text`, posições vazias, pai ausente e nenhuma relação. O catálogo global permanece 2.629 slots/2.628 referências confirmadas, porém esses números são denominadores da ledger pinada, não prova de que este peer refez os quatro PDFs. O teste não executou OCR nem reconhecedor de códigos.

`replay.py` usou o namespace portátil com somente o PDF EI. Três PDFs não alvo e todos os 158 arquivos privados de recortes/folhas estavam ausentes. Cada recorte foi reconstruído do PDF alvo, conferindo SHA do artefato e da imagem embutida, xref, matriz afim, bbox, pixels nativos, orientação e hash dos pixels orientados. `present-assets.py` repetiu a operação com os 158 arquivos presentes e conferidos: os hashes dos registros e da trace, o slot rejeitado e todos os denominadores ficaram iguais. Nos dois replays, o único primário lido foi `data/raw/AM/am-rca-ei.pdf`.

Sete testes do produtor passaram sem skips. Os controles independentes bloquearam sete casos: proposta, revisão, Source e resumo global mutados em RAM; asset privado presente e corrompido; PDF alvo ausente; código Python alterado após importação em sandbox próprio. Nove controles geométricos reais bloquearam bytes da imagem, xref, matriz, bbox solicitado, caixa nativa, hashes nativo/orientado, rotação e coordenada não finita divergentes. A ausência autorizada de PNG privado não permite ausência ou divergência do PDF alvo, metadados JSON ou pin externo.

O primeiro replay encontrou P2: `global_catalog`, copiado para o recibo, não integrava o digest do catálogo. A mutação de sua contagem em RAM deixava o digest igual. `replay-before-summary-fix.*` e o log inicial preservam a prova histórica do SHA anterior `419a4d06b40d8099b6684b0f04dc3bc614d03b8d5b4099d9d5bec84cf3817cab`. O responsável incluiu o resumo no digest e adicionou regressão. O replay final exige bloqueio real dessa mutação e não tem achados em aberto neste escopo.

O texto confirmado pelo revisor automatizado anterior continua ancorado no handoff externo SHA `fdb2256668c0fc0fa323e232ae701f4792bdea8cc5289cfa20e39ef197792cca`. Este peer não relê visualmente todos os códigos para substituir aquela revisão: comprova que os bytes/pixels verificados correspondem aos recortes pinados e que somente a referência permitida é emitida. Modificar os metadados e recalcular seus próprios hashes não substitui a confiança externa desse pin.

Não foram executados replay completo dos 2.628 códigos, estágio de augmentação, SQL, worker, importação nacional ou publicação. A augmentação é revisada separadamente pelo domínio; nenhuma propriedade desse estágio é inferida destes testes. Nenhum Source, cache, BASE, banco ou publicação foi modificado por este peer. SourceWhole, UF ready, revisão humana/pedagógica e completude dos corpos continuam fora deste aceite.

Com pins/insumos preservados, a partir da raiz:

```sh
var/venv-pipeline/bin/python -m unittest discover -s pipeline/tests -p test_raster_review_scoped.py -v
var/venv-pipeline/bin/python docs/evidence/source-audit-am-scoped-verifier-peer/replay.py
var/venv-pipeline/bin/python docs/evidence/source-audit-am-scoped-verifier-peer/present-assets.py
```

Os controles negativos de arquivos escrevem apenas cópias próprias temporárias dentro de `var/`, removidas ao concluir. O código compartilhado nunca é modificado para provar a detecção de alterações.
