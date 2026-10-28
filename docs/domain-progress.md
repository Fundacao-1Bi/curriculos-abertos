# Domínio — checkpoint

Estado: implementado e verificado em PostgreSQL descartável. Integração com corpus documental real depende do bundle em preparação e da verificação nacional independente.

Responsável automatizado: `/root/domain`. Arquivos: `src/domain/*`, `src/db/client.ts`, `src/db/schema.ts`, `src/db/migrations/001-domain.sql`, `src/db/migrations/004-domain-search.sql`, `scripts/migrate.ts`, `scripts/import-data.ts`, `scripts/test-all.ts`, `tests/domain.integration.test.ts`, `docs/domain-model.md`.

## Verificações executadas

- `npx tsx scripts/test-all.ts`: container PostgreSQL 17 e banco de testes com nome aleatório criados e removidos pelo harness; 12 testes, 12 aprovados, zero skips, zero falhas. Evidência: `docs/evidence/all-tests.log`.
- Testes isolados do domínio verificam migrations em banco vazio e segunda execução, importação idempotente e imutabilidade SQL, revisão e rollback com ator automatizado, pin de publicação antiga, busca com acentos/código/sufixos, blocos de anos e desconhecidos, lote por item, panorama muitos-para-muitos, matriz nacional, comparação e exports completos, grafo de suporte reimportável e CSV.
- `tsc --noEmit`: sem erros nos caminhos de domínio, schema, scripts ou testes desta frente. Integração global pode mudar com trabalho concorrente.

- Modo sem Docker socket: `TEST_DATABASE_ADMIN_URL` explicitamente configurada permite criar/remover somente banco aleatório próprio. Executado contra a conexão administrativa dedicada do projeto: 12/12 aprovados, zero skips; `docs/evidence/all-tests-admin-database.log`. Nenhum schema da base pública foi apagado.
- Índices adicionais `004-domain-search.sql`: trigramas de texto/código e código normalizado com transliteração portuguesa determinística. Migrations testadas em banco novo e rerun.

## Contratos entregues

Todas as funções de `docs/architecture.md`, além de `resolvePublication`. `exportData` retorna `Result.data {content,mime_type,filename,record_count,manifest}`. Views `panorama`, `comparison` e `analyses` exportam o relatório integral. Recortes são grafos autocontidos com registros de suporte identificados. Base nacional JSON mantém o snapshot original para reimportação idempotente. CSV usa `record_type,id,payload_json` (manifest/source/item/relation/coverage).

## Desempenho e riscos

Consultas públicas de cobertura, UFs, matriz e panorama leem somente metadados JSONB e tabelas indexadas; o snapshot integral é carregado somente pelo worker em exportações. A publicação default é resolvida uma vez por operação. A matriz não executa uma consulta por célula.

Nenhuma UF nem o lançamento nacional foi declarado pronto por esta frente. O gate independente deve verificar corpus completo, inventário, amostras e reconciliação. Testes com fixtures sintéticas só usam banco descartável `curriculum_test_*`; não são evidência de cobertura do corpus nacional.

## Retomada

1. Finalizar/importar bundle documental: `DATABASE_URL=... npm run data:import` resolve `data/bundles/latest.json` e exige sidecar SHA-256.
2. Exercitar API/MCP/portal contra essa publicação e medir desempenho real.
3. Verificar amostras e denominadores da cobertura com auditor independente; manter bloqueio nacional enquanto faltar qualquer parte.


## Checkpoint adicional — gzip e escala nacional

- `src/domain/bundle-file.ts` suporta JSON/gzip com checagem de hash dos bytes comprimidos, decodificação limitada, checksum/tamanho decodificado e caminhos resolvidos sob a raiz permitida. CLI de importação usa o mesmo loader da instalação.
- Artefato real `ca-77fb8076598b567e1ba3` gzip validado: 24.253.561 bytes comprimidos, 237.695.811 bytes decodificados; 247 fontes, 38.322 itens, 13.007 relações. Evidência `docs/evidence/gzip-bundle-validation.json`. Validação é técnica; não aprova cobertura editorial nacional.
- `005-domain-metadata.sql` evita detoastar o snapshot de 237 MB nas consultas públicas. Backfill único preserva snapshots existentes. Importação posterior grava os derivados atomicamente.
- Importação serializa uma vez e insere relações/membros em lotes de 500. Export nacional JSON lê uma única representação textual do snapshot; recortes selecionam IDs sem duplicar payloads.
- Guard de testes agora analisa o nome exato do banco na URL e confere `current_database()` antes de `DROP SCHEMA`; substrings em usuário/senha/host/query não passam.
- Opção de incluir desconhecidos cobre `positions: []` sem atribuir anos; teste valida exclusão padrão e contexto documental explícito.
- Última execução: 18 testes aprovados, zero falhas/skips, banco descartável removido. `docs/evidence/all-tests-admin-database.log`.
