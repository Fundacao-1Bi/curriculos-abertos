# Produtores de atualização por fonte

O extrator nativo permanece em `page-cell-v1.5.0`, fingerprint `541aa3377fd409f9c172e1580ae988f5869b25e5331c98528ab68fb9a09360db`. Os módulos abaixo constituem uma etapa separada de validação e produção. Uma mudança nessa etapa altera sua identidade e seus artefatos derivados; não autoriza relabelar ou aceitar caches nativos incompatíveis.

## Referências raster AM

`pipeline/raster_augmentation.py` expõe `augment_source_update(repo, storage, original_raw_receipt, job_scope)`. O recibo original tem exatamente `publication`, `artifact` relativo ao storage e `artifact_sha256`. O escopo fixa `base_publication`, `base_publication_sha256`, `base_artifact_sha256`, `target_source_ids` e `context_source_ids`.

O SHA da publicação no banco é distinto do SHA do contexto BR. Ambos são exigidos e preservados. O resultado contém três campos:

- `original_raw_receipt`: recibo original inalterado.
- `augmentation_receipt`: versão, fingerprint do produtor/dependências, validação primária, escopo e contagens reais, com digest próprio.
- `effective_raw_receipt`: artefato efetivamente destinado ao compositor.

Em RN ou outro alvo sem AM, o recibo efetivo conserva exatamente caminho, ID e SHA do original; nenhum PDF AM é aberto e nenhum artefato alternativo é escrito. Em AM, somente as fontes explicitamente selecionadas são revalidadas contra os pixels das imagens incorporadas no PDF original, usando o ledger/review pinado. O resumo global também integra o digest do catálogo e não pode ser alterado em memória.

Os novos registros são `referencia_no_documento`, com texto igual ao identificador literal, sem posições, pais ou relações. A revisão automatizada comprova apenas o código do recorte: não aprova corpo, equivalência, ano/idade, completude ou revisão humana. Colisão de ID com payload diferente falha. Dados originais, BR, relações e cobertura são preservados; a etapa não promove prontidão.

Instalar e consultar o artefato pronto depende dos registros, evidências e hashes públicos armazenados nele. Não exige PDFs brutos, crops ou imagens privadas. Reprocessar administrativamente uma fonte AM exige obter e conferir o PDF alvo e os metadados pinados de revisão. Um crop privado ausente pode ser reconstruído do original; um crop presente com hash divergente é erro.

A CLI `scripts/augment-ingestion-raw.py` recebe recibo original e escopo em arquivos JSON com SHA explícito. Grava o recibo de transição por criação exclusiva e atômica em `var/`, sem substituir o RAW, atualizar `latest`, importar banco ou publicar. O worker deverá persistir e conferir toda a cadeia; comparar o resultado do domínio com o recibo efetivo, preservando o original para auditoria.

## Correções técnicas e identidade

`pipeline/technical_provenance.py` avalia ledgers públicos pinados de supersessão e correção textual, verifica presença dos replacements na mesma Source, ausência dos IDs inválidos e ausência de relações órfãs com esses IDs. O compositor não deve aceitar somente uma flag de validação.

A segunda fase confronta os IDs procurados com a publicação BASE pinada. Se um ID antigo existe na BASE, o evento registra o efeito efetivo sobre essa base. Se está ausente, registra correção histórica documentada e rejeita alegar remoção atual. Correção textual com mesmo ID preserva os hashes e textos anterior/posterior, sem exigir supersessão de identidade.

O digest contém eventos, proofs, base, alvos e fingerprint do produtor. Esse digest deve integrar a identidade do candidato global e o seu header/changelog. Uma alteração repinada de prova ou código gera identidade nova; a mesma identidade não pode produzir bytes diferentes. A etapa técnica é separada da augmentação AM para que o bypass RN continue exato.

## Estado de execução

A prova real de quatro Sources produziu 15.276 itens e 3.037 relações. Uma leitura sequencial do BASE de 200.724 itens confirmou 18 supersessões atuais e uma correção textual same-ID; oito negativos foram rejeitados. Os recibos e a captura de 19 registros estão em `var/technical-delta-real/`. Os testes versionados incluem dependências do produtor e colisões.

O replay AM EI após a correção do digest validou 153 slots e acrescentou 152 referências; o único slot restante é prosa, não código. O replay RN preservou o recibo exato. Os testes e recibos desta etapa estão em `var/am-augmentation-contract/`. A revisão independente e a integração de compositor/worker ainda precisam ser concluídas. O ensaio PostgreSQL/worker será isolado e coordenado com operações após a QA em curso.

Nada disso modifica o BASE `ca-7d302a9c674a97b83278`, publica um candidato ou resolve automaticamente as 3.012 pendências documentais do preflight histórico.

## CLI técnica em duas fases

A CLI única `scripts/technical-ingestion-provenance.py` tem dois subcomandos. Ambos usam o mesmo arquivo e SHA no recibo de orquestração:

1. `evaluate`: recebe `--storage-root`, `--proof-root`, `--raw-receipt`/`--raw-receipt-sha256`, `--job-scope`/`--job-scope-sha256` e `--output-receipt`. Processa somente os Sources alvo do RAW, não os ledgers do contexto BR. Emite avaliação, pins e `wanted_base_item_ids` ordenados.
2. O domínio consulta esses IDs na publicação SQL pinada e confere a identidade da base. Exporta `technical-base-record-capture-v1` com `base_publication`, `base_publication_sha256`, `queried_item_ids` exato, incluindo IDs consultados e ausentes, e `records` retornados.
3. `contextualize`: recebe `--storage-root`, `--proof-root`, `--evaluation-receipt`/`--evaluation-receipt-sha256`, `--base-record-capture`/`--base-record-capture-sha256` e `--output-receipt`. Reavalia o RAW e suas provas, confere a avaliação inteira, os denominadores e a captura. Emite `identity_payload`, `technical_events_sha256`, `identity_payload_sha256` e os pins dos recibos. Não afirma que capturou SQL; essa autoridade pertence ao domínio.

Os outputs ficam em `var/` do storage selecionado, por publicação atômica/exclusiva. O RAW e seus shards permanecem imutáveis. Um terceiro texto presente no BASE, diferente tanto do before quanto do after aprovados, bloqueia a correção same-ID. Relações com o mesmo ID e payload divergente também bloqueiam. Ausência real do ID antigo permite apenas a classificação histórica explícita.

A orquestração deve preservar `original_raw_receipt` e `effective_raw_receipt`, fixar os arquivos/SHAs das CLIs, os fingerprints dos produtores e os arquivos de worker/compositor. O digest do objeto inteiro participa da identidade e do header global junto ao digest dos eventos. Uma avaliação sem ledgers pode resultar em `technical_stage=null` explícito, sem fabricar eventos ou alterar o RAW.

O complemento PI foi verificado em `var/technical-pi-real/`: seis migrações de ID/localizador atuais no BASE, todas com corpo, código, kind, posição e pai preservados, sem correção redacional. Com os quatro Sources anteriores, a prova observada soma 24 migrações de ID e uma correção textual same-ID. Isso não mede o delta inteiro das fontes nem reduz automaticamente o contador de pendências do preflight histórico.
