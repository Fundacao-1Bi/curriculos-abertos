# Peer independente do estágio de augmentação AM e CLI

**PASS técnico automatizado**, limitado a `pipeline/raster_augmentation.py`, `scripts/augment-ingestion-raw.py`, contrato de recibos e replays EI/RN. Não é aprovação do corpo curricular, de todo o Amazonas, de prontidão nacional ou de revisão humana. A validação dos pixels/ledger/subconjunto foi revisada separadamente pelo auditor; seu recibo está em `docs/evidence/source-audit-am-scoped-verifier-peer/receipt.json`, SHA `b56c05c99adfddeba00ee1e78f5ef34f8cbcd507b1f044d65f915378f174902b`.

## Pins

- Módulo de augmentação: `414ce3f395dbaf7f38e04e073f0ce93747f3f965626099777d663508b3f81263`.
- CLI: `fdb357ce378c2aac84bb998c215fd4b377e90fdec5980b91cdff0dc4895f8698`.
- Verificador scoped: `3808cc1a5ab930bfac8edeebc853bc6f5716e1abd394fd0352de792c13eda2b3`.
- Relatório independente `verification.json`: `15b5db056488413d61c045260778eefd8e352cf384a84a0db27e785d9f53294c`.
- BASE preservado: `ca-7d302a9c674a97b83278`, SHA `be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d`. Foi lido apenas seu manifesto para conferir identidade; nenhum shard nacional ou banco foi importado por este peer.

## Executado

`pipeline/tests/test_raster_augmentation.py`: **8 testes, zero skips**. Fixtures pequenas verificam o conversor; não são prova de pixels. A prova real adicional está em `audit.py`, que chama a CLI em subprocessos e opera apenas em namespaces próprios `var/domain-am-augmentation-peer/`.

RN usou RAW real `ca-b3c8bbce0697d146fb2d`, SHA `9cf294b26493c0aa857b24a4cf3a9bbe5404c55f8229b894c870a49bcb902baa`, 5.359 itens/171 relações. A CLI recebeu **source-root vazio, sem qualquer PDF**, e o recibo efetivo foi exatamente o original por caminho relativo/ID/SHA. Uma chamada direta adicional, com o verificador raster substituído por uma função que lança erro caso invocada, também passou. A repetição da CLI manteve o recibo byte-idêntico. Isso verifica bypass sem dependência de PDFs AM não alvo.

EI usou RAW real `ca-45a51f784722d558a688`, SHA `7c9b88d39599dc705735938f9d6294709305f62751e91ec11bf364c7bc2598e3`, 4.928 itens/90 relações. O source-root portátil possuía **somente o PDF EI, zero PNGs privados e nenhum PDF das outras três fontes AM**; os demais arquivos eram metadados/provas pinados e o verificador legado. A CLI real reconstruiu a prova primária, acrescentou 152 referências e produziu `ca-4c544b50c4eb62a9ef98`, SHA `65683b6d804154c093582989d29627809273d8c68c739d9d124c9589b0aa80ae`. ID/SHA são exatamente os do replay independente anterior do produtor, executado com os assets normais. Não foi necessário um terceiro replay EI para provar essa igualdade entre ambientes.

Todos os 4.928 registros originais do RAW foram comparados por payload e ordem contra o prefixo do efetivo, incluindo o contexto BR. As 90 relações foram integralmente comparadas e preservadas; fontes, cobertura, direitos, build_context, alvos e os dois SHAs distintos da linhagem permaneceram iguais. As adições são somente `referencia_no_documento`, `text=code`, sem posições, pais ou revisão pedagógica. Nenhum corpo foi inventado e nenhuma prontidão foi promovida.

## Recibos e identidade

A cadeia conserva `original_raw_receipt`, `augmentation_receipt` e `effective_raw_receipt` separadamente. O hash interno do recibo é calculado sobre o objeto antes de adicionar `receipt_sha256`; ele **não é** o SHA do arquivo externo completo. O relatório registra ambos sem confundi-los. A CLI fixa por SHA os arquivos de entrada, limita sua saída a `storage/var/`, publica o recibo completo atomicamente e recusa substituir um recibo diferente.

A identidade do artefato inclui os metadados do produtor, a validação/prova, os hashes das coleções e os itens acrescentados. O módulo detecta drift de suas dependências entre carregamento, produção e materialização. O fingerprint da CLI foi fixado externamente por este peer; ele não faz parte da lista interna `PRODUCER_FILES` do módulo, portanto ambos os pins devem acompanhar a distribuição do estágio.

A proveniência de supersessões/correções técnicas é uma etapa **separada**, em revisão própria de `technical_provenance.py`. O PASS deste estágio raster não aprova essa etapa, a integração do compositor, ou o ensaio SQL/worker pendente.

## Controles negativos adicionais

Nove negativos recusados: troca entre SHA da publicação BASE e SHA do contexto BR; alvo incorreto; alvo duplicado; SHA RAW incorreto; dois escapes de caminho; colisão de ID com payload divergente; conservação indevida de `ready=true` após augmentação; e conflito imutável na saída da CLI. O conflito permaneceu byte-idêntico após a recusa. Somam-se às mutações de texto, tipo, idade, revisão/ator, SourceSHA e prova cobertas pelos oito testes de contrato.

Nenhum Source/MF, parser, cache, BASE, RAW original, default, banco ou worker foi alterado. Não houve OCR, extração, build ou carga nacional. SQL e HTTP/worker serão verificados em ambiente isolado somente após liberação da QA pelo responsável ops.
