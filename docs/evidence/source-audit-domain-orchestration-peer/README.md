# Peer técnico independente — compositor/proveniência

Revisão read-only em 28/10/2026, antes dos fixes de follow-up. Ownership das saídas restrito a este diretório. Não executou SQL, Docker, build, imports de dados, cargas ou publicação. Nenhum arquivo de produto foi alterado por este peer.

## Resultado

**Três achados P2 no snapshot revisado; PASS limitado dos demais invariantes descritos abaixo.** A revisão não aprova produto nacional, FULL, SourceWhole ou UF ready.

1. **P2 — declaração técnica malformada pode escapar do gate sem proveniência** (`src/domain/ingestion-update.ts:106-107`). `technical_supersessions`/`technical_extraction_corrections` só ativam o requisito quando são arrays não vazios. `Source` tem propriedades adicionais permitidas e não tipa esses campos; objeto/null/string são aceitos pelo schema 1.1.0. Portanto um caller direto que omita `provenance` com uma dessas declarações não executa a avaliação que recusaria metadados inválidos. Controle puro abaixo confirma passagem até a entrada SQL substituída por sentinel. Recomendação: recusar tipo inválido quando a propriedade existe, ou exigir a etapa por presença e deixar o produtor validar; array vazio válido não implica fabricar eventos.
2. **P2 — pin de arquivo no disco não comprova o módulo carregado no processo** (`src/domain/ingestion-provenance.ts:111,116,147`). O fingerprint é calculado quando começa a preparação. Se módulos TS foram carregados antes de uma edição, `runtimePins()` e a checagem final podem ler os mesmos bytes novos enquanto o processo executa funções antigas em memória. O candidato rotula a execução com identidade de código diferente. Limite: não ocorre em uma imagem realmente imutável, mas a função não impõe esse pressuposto. Recomendação: capturar/validar fingerprints no carregamento do módulo e recusar drift anterior à chamada; manter checks durante a composição. Achado por leitura, sem alterar arquivos de runtime para repro.
3. **P2 — cancelamento não cobre o restante da composição e pode abandonar o subprocesso** (`src/domain/ingestion-provenance.ts:62-66`; `src/domain/ingestion-update.ts:150-155`). `signal` só chega ao subprocesso técnico. Se for abortado após essa fase ou durante o writer, o fluxo continua para COMMIT e import privado. No caminho de abort do spawn, o evento `error` limpa os timers antes de `close`; um filho que ignore/atrase SIGTERM perde a escalada SIGKILL. O resultado permanece privado: isto não demonstra publicação indevida. Recomendação: checkpoints de aborto antes/depois das fases e antes de commit/import; preservar limpeza/escalada até o fechamento efetivo do filho. Achado por leitura; nenhum processo adversarial foi executado.

## Controles e evidência

- `pure-controls.mjs` compila o snapshot do compositor em memória, substituindo load/verify de artefato e pool.connect por stubs; não há SQL nem escrita de artefato. O validador real do schema local 1.1.0 valida cada Source. `pure-controls.json` registra que object/null/string chegam ao sentinel `PEER_SQL_ENTRY`, enquanto array não vazio resulta em `INGESTION_PROVENANCE_REQUIRED`.
- Controle executado com `node_modules/.bin/tsx docs/evidence/source-audit-domain-orchestration-peer/pure-controls.mjs`; saída fixada no JSON adjacente.
- Log existente inspecionado, não reexecutado por este peer: `docs/evidence/domain-orchestration-verification/sql-tests-final.log`, 10 testes aprovados, zero falhas/skips, incluindo SQL exato, replay, imutabilidade, dependências muitos-para-muitos e CAS.

## PASS limitado por leitura e testes existentes

- A captura consulta `publications` com visibilidade published e SHA fixado e consulta os IDs exclusivamente no PostgreSQL, na transação repeatable-read aberta pelo compositor. O caller não fornece records de captura para a preparação.
- `payload::text` é escrito diretamente: integer/decimal JSONB não passam por Number JS. `queried_item_ids` preserva também IDs ausentes. Quantidade, tamanho, batches, arquivos temporários, link exclusivo e colisão imutável são limitados/conferidos.
- `contextualize` reavalia RAW/provas e confere a avaliação inteira; não confia só em um digest caller. O domínio verifica efeitos sobre source/text SQL e não aceita autoridade SQL afirmada pela CLI. Revisão detalhada do Python foi delegada separadamente pelo pai; aqui foi lido o contrato e o trecho invocado.
- `orchestration_sha256` e `technical_events_sha256` entram no ID e header; eventos técnicos entram no changelog sobre histórico preservado; recibos original/efetivo e arquivos de CLI/produtores/provas são pinados. Repin legítimo muda identidade e drift durante a preparação falha.
- Revalidação de candidato persistido compara base, ator, alvos, RAW e digests, recalcula as provas sem recompor o grafo. Preservação fora do alvo, membership muitos-para-muitos e publicação via CAS permanecem separadas da preparação privada.

## Hashes do snapshot revisado

```
d3618284be8617f5b7e37ef1d589fabb0583e0395d7822194b6dfeb3db02e4c8  src/domain/ingestion-provenance.ts
feee0e25e42434f911178b1e1d43b12594cad6737a861e02a0ad3d0a6f698c57  src/domain/ingestion-update.ts
eebaf49eaaaead66de8c2a8499e94fbba3ef9d9acea594582b762a6ab361ea14  tests/domain.ingestion-provenance.test.ts
107d13c3d7e3030fec70b533306b16314e491fa68acb1783fa5905b1cf555318  tests/domain.ingestion-update.test.ts
9a056c4f90b203cd3bd527ac33c632d87447c89cfdca2874c8805c2d37d38cbf  docs/domain-ingestion-augmentation-contract.md
dbd3f3cdfd9d887b95b294c710658653897ab4b5af8d5d511b40f30fce42a493  docs/data-source-update-producers.md
```

Esses hashes congelam a revisão anterior ao follow-up. Fixes posteriores exigem reavaliação dos pontos alterados.
