# Follow-up pinado v1.0.1 — PASS no escopo revisto

Produtor: `pipeline/technical_provenance.py`, SHA `bc00fa550bd0147f2ac440accdb5581436480d27938bd468ebfcc2f91fca3c2b`. Testes: SHA `47513c10042e00069b45a516bc6022ee027e905268973827fd8dbb02fe901d07`. A revisão anterior e seu recibo SHA `f71beb8e32cbe7cb64c82c9ad05025185e86c4b1189c8ccb356b47597e9f0a18` foram preservados sem alteração.

Os17 testes existentes passaram, zero falhas/skips, em12,606s. O peer adicional reabriu os shards RAW pinados (15.276 itens e3.037 relações) e a captura de19 registros do BASE; não repetiu o scan nacional nem fez extração, build, wiring, import ou SQL.

As três correções foram reproduzidas independentemente:

- Terceiro texto existente no mesmo ID/Source do BASE agora falha. `before` real continua `corrects_text_in_pinned_base`, `after` em memória é explicitamente `already_corrected_in_pinned_base`, e ausência em memória permanece `documented_historical_text_correction`. Os18 IDs antigos do BASE real continuam identificados como supersessões atuais. A ausência contrafactual de um deles continua histórica e a alegação de remoção atual falha.
- Relação com mesmo ID e tipo divergente agora falha. Repetição com payload idêntico permanece permitida e não altera os eventos.
- Oito classes de SHA-base malformado foram rejeitadas por ambas as funções `contextualize` e `global_id`, incluindo64 caracteres não hexadecimais, comprimentos incorretos, tipos não string e quebra de linha.

O digest de eventos para este produtor e runtime é `210a92651a550a2d02327d14161ce04b159bcfd8f801452085a34f4aa536e28f`. Não é o digest das versões anteriores nem uma publicação criada. As chamadas preservaram os pins do produtor/testes e os bytes do relatório histórico.

Comandos executados:

```sh
env PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -m unittest discover -s pipeline/tests -p test_technical_provenance.py -v
env PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python docs/evidence/source-audit-technical-provenance-peer/verify_followup_v101.py
```

O recibo novo é `followup-v1.0.1-verification.json`. PASS se limita aos achados reproduzidos no produtor standalone pinado. O integrador ainda precisa confrontar os bytes do manifesto BASE, preservar o bypass fora do escopo e verificar seu próprio wiring/compositor. Gramática hexadecimal não prova que um checksum corresponde ao arquivo. A deriva de `raster_review_scoped.py` registrada no primeiro peer continua sendo informação daquele checkpoint; este follow-up não renova os99 pins históricos nem afirma produção, prontidão nacional ou revisão pedagógica.
