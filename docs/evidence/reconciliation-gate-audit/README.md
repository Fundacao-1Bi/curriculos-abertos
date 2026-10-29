# Gate de reconciliação documental por parte e por fonte

O achado P1 em `coverage_for` era a promoção de `expected_item_ids == verified_item_ids ⊆ actual` a completude de uma fonte inteira. A comparação é útil para uma parte, mas deixa registros adicionais sem papel, não vincula o texto aos IDs e não demonstra que o inventário obrigatório estava completo. Isso viola ING-03, ING-05 e ACE-01/03 quando usado como prova integral.

`pipeline/reconciliation.py` implementa uma avaliação pura e fechada em caso de falha. Os campos manuais `inventory_complete`, `reconciliation_status`, `ready` e os nomes de tipos de registro não constituem prova de completude. A revisão automatizada continua identificada como automatizada.

## Contrato e integração

```python
reports[source_id] = evaluate_source_reconciliation(
    source, extracted, actual_items_for_source, receipt,
    extraction_revision, expected_parts=mandatory_part_names,
)
reports = resolve_source_dependencies(reports)
```

O produtor deve calcular todos os reports novamente em memória; o resolvedor de dependências não aceita relatórios declarados por manifestos como substituto dessa execução. O chamador continua responsável por incluir todas as fontes mandatórias, todos os recortes exigidos e todos os demais critérios de aceite.

A avaliação retorna `reconciled_parts` (partes com conteúdo vinculado), `partial_parts` (comprovantes legados somente por ID), `part_results`, `own_source_reconciled`, `whole_source_reconciled`, `required_related_documents`, `issues`, denominadores e IDs não contabilizados. Apenas `whole_source_reconciled` pode contribuir para `ready`. Uma parte pode conter um subconjunto legítimo de registros; não se exige que cada parte individual contenha todos os registros da fonte.

## Comprovante integral v2

O comprovante mantém `source_id`, `artifact_sha256`, revisão de extração, `method`, `actor_id`, `actor_type` e `reviewed_at`/`executed_at` com fuso. Source e extração precisam identificar o mesmo artefato e revisão. Acrescenta `reconciliation_scope: "whole_source"` e `document_inventory`:

- `basis: "primary_document_review"`, método e evidência localizável do inventário independente;
- `required_parts`: todas as partes obrigatórias da fonte;
- `source_scope_sha256`: resultado de `source_scope_sha256(source)`, vinculando partes, etapas/componentes e seletores documentais;
- `units`: unidades documentais identificadas com `unit_id`, `part`, `role`, `page_ranges`, método, evidência, `expected_record_count`, denominador e checks de conteúdo.

Cada unidade tem papel `curricular`, `structure`, `normative` ou `documentary_context`. Sua classificação não basta: o denominador exige `basis: "primary_document_review"`, `unit: "documentary_records"`, `expected_count`, método e evidência. A quantidade precisa coincidir com os checks. Unidades sem registros exigem `no_record_reason`, método e evidência documental; isso permite registrar capa/créditos sem inventar aprendizagens.

Cada `item_checks` contém `item_id`, `text_sha256` e `evidence`. O hash é SHA256 do texto UTF-8 exato, sem normalização. A evidência v2 exige `source_id` explícito, trecho não vazio e página ou seção. A união de IDs verificados das unidades deve ser exatamente o conjunto de registros reais da fonte, sem duplicação entre unidades. Registros extras também precisam de denominação, papel, texto vinculado e prova; classificá-los apenas como contexto não libera o gate. O inventário e hashes devem resultar de confronto com o documento primário, não da cópia da saída de extração para produzir um recibo de sucesso.

As páginas esperadas vêm do escopo editorial declarado na Source (`extraction_pages`/`scope_pages`, em interseção com `extraction_page_ranges`), ou de todo o documento quando não há seleção. Não são inferidas apenas das páginas que a extração conseguiu produzir. Isso permite recortes legítimos de Diário Oficial sem exigir matérias alheias e bloqueia a redução silenciosa do denominador quando uma página falta. Alterações de regiões/seletores invalidam o vínculo do inventário anterior.

Documentos externos obrigatórios são dependências entre fontes, não partes falsas da Source atual. Cada declaração deve ter `related_source_id`, `artifact_sha256` e evidência. `resolve_source_dependencies` exige o report documental íntegro da outra Source, com mesmo ID/hash/revisão e dependências transitivas satisfeitas. Ausência, divergência de hash, falha documental e ciclos bloqueiam. Um `status: "resolved"` isolado não satisfaz a dependência.

O exemplo completo em [isolated-whole-source-example.json](isolated-whole-source-example.json) é **sintético e isolado de teste**, sem valor de cobertura curricular. Não deve ser importado no corpus. Comprovantes legados preservam seu valor parcial; não são convertidos automaticamente em prova integral.

## Execução e limites da evidência

```sh
python3 -m unittest discover -s pipeline/tests -p test_reconciliation_gate.py -v
python3 docs/evidence/reconciliation-gate-audit/audit.py
```

Os testes incluem partes legítimas, legado parcial, extra desconhecido, contexto sem prova, inventário incompleto, texto alterado com mesmo ID, denominador divergente, escopo de Diário Oficial, página faltante, mudança de escopo, fonte relacionada adquirida, hash errado, ciclo e flag manual insuficiente. O `audit.json` identifica os manifestos reais lidos por hash e, quando disponível, o cache de extração verificado e limitado a 32 MiB.

Contagens de caches anteriores à finalização são diagnósticas: excluem sidecars e transformações finais e não representam totais publicados. A validação do novo corpus pelo hook integrado, build, API, navegador e release-check permanece responsabilidade da verificação integrada; este relatório não a declara executada.
