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


## Checkpoint de escala — publicação relacional e reimportação em fluxo

A coordenação autorizou separar o snapshot nacional em partes após caches reais ultrapassarem 614 MiB e 89 mil candidatos. O limite V8 de strings não foi elevado para esconder o problema.

- Manifesto: `format: curriculos-abertos/sharded-v1`; metadata/sources/coverage/changelog e contagens, sem arrays nacionais; `parts` JSONL/gzip <=20 MiB decodificados e <=5000 registros (registro <=8 MiB), SHA do gzip/JSONL, tamanhos e contagens. `src/domain/shards.ts` verifica todas as partes, schemas, unicidade, referências e ciclos antes da promoção. A transação relê/valida partes e só muda o padrão ao concluir.
- `006-relational-publications.sql` diferencia `embedded-v1` legado de `relational-v1` novo. Novas publicações guardam metadados pequenos; itens/relações/membros estão nas tabelas imutáveis. Publicações anteriores permanecem intactas.
- `streamExportToFile` em `src/domain/stream-exports.ts` usa versão fixada, paginação keyset, temporárias de seleção/grafo, escrita incremental 0600 e SHA dos bytes. Nacional JSON/CSV não é materializado como string/array global no worker.
- `src/domain/revisions.ts` valida somente patches e clones relacionais por INSERT SELECT; aceitar publicação não vira revisão pedagógica. A origem é preservada. Resumos de cobertura afetados ficam pendentes de revalidação.
- Subagente real `/root/domain/flat_json_import` foi delegado para `json-snapshot-file.ts` e teste correspondente. Implementou `stream-json@3.7.0`, budgets de string/registro/metadados, hashes antes/durante, cache determinístico e transcode de snapshots JSON completos para partes. O importador detecta JSONs >32 MiB/gzip legados e usa esse caminho. O mesmo ID pode ser reimportado em outra representação apenas se metadados e todos os registros canônicos forem equivalentes no PostgreSQL.
- Prova real: gzip legado ca77, 237.695.811 bytes decodificados, 38.322 itens e 13.007 relações, convertido em 14 partes em 45,3 s, pico RSS de aproximadamente 389 MiB. `docs/evidence/json-transcode-legacy.json`.
- A prova real encontrou `readline` separando U+2028/U+2029 dentro de strings JSON válidas. Foi corrigido genericamente com separação por byte LF e UTF-8 fatal. Todas as 51.329 linhas reais foram relidas; quatro registros com esses separadores foram preservados. Cache/fonte permaneceram intactos. `docs/evidence/sharded-unicode-read.json` e regressão red→green.
- `007-hierarchy-and-code-aliases.sql`: índice por parent_id e GIN de expressão para aliases. A primeira forma de coluna gerada reescrevia dados/índices e excedeu o timeout; foi substituída antes de aplicar. Qualificação explícita public.curriculum_search_code resolve search_path restrito na construção do índice. 007 foi aplicada com hash e66d3d52d73382930aae11a8c114c694429f8a0e3539b46d7331433aef132bed. Não alterar migration aplicada.
- `getStructure` mantém data agregada e acrescenta hierarchy.nodes com parent_id, contexto, evidência e contagens de filhos. Busca por parent_id navega filhos diretos. Aliases documentados localizam grafias oficiais preservadas (EF05CO011 / alias EF05CO11). Atos/documentos/temas não contam como habilidades; métricas expõem kinds incluídos.
- Suíte de 32 testes passou com zero falhas/skips em PostgreSQL descartável antes da última regressão Unicode adicional. O subagente executou 5/5 testes do conversor após o fix. Repetir suíte integrada após a janela operacional.
- Janela atual: congelamento de mutações do banco principal para backup/restore/cutover PostgreSQL 17.11 pelo agente de operações. Aguarda sinal desse responsável para retomar reimportação real ca77 --prepare-only e importação do candidato sharded novo. Não confundir esses candidatos com lançamento nacional reconciliado.

## Checkpoint de integração — 28/10/2026

O cutover foi concluído e verificado por operações: PostgreSQL 17.11-bookworm dedicado na porta 55437. Migrations 008 (visibilidade preparada/publicada), 009 (códigos com espaços documentais) e 010 (palavras hifenizadas em quebra de PDF) foram aplicadas. Publicações preparadas ficam fora dos leitores públicos, API, MCP e downloads; helpers administrativos internos preservam a inspeção autenticada. A última suíte integrada registrada em `docs/evidence/all-tests.log` passou 48/48, sem skips. Esses testes técnicos não substituem reconciliação editorial nacional.

A matriz restringe o denominador aos tipos explícitos de aprendizagem e projeta referências nacionais a partir do coorte local quando há filtros locais. Ela informa recorte, denominador, itens locais com/sem vínculo e filtros de coluna; não chama referências projetadas de total da BNCC. A estrutura conserva numeração/ordem documental e os índices de busca preservam texto e códigos canônicos.

### Diagnóstico do detalhe que demorou 14 segundos

Operações observou duas chamadas reais lentas para `ca:ac-cru-em:0090948210886854c3a6` (fonte AC, código EM13MAT505), no snapshot ca77 e em revisão publicada, entre 05:41:18 e 05:41:47 UTC. A consulta ativa observada era a busca de relações. O incidente existiu; a causa permanece não demonstrada.

- O plano coletado posteriormente para o ID exato usa `members_item_idx` e `relations_pkey`, com uma relação retornada e execução de 0,268 ms; busca do item 0,087 ms. É um plano posterior, não o plano das chamadas lentas. Evidência: `docs/evidence/detail-query-ac-before.json` (nome histórico do arquivo).
- As estatísticas observadas indicam autoANALYZE de items/relation_members/relations às 05:41:58–05:42:00 UTC, após a lentidão. Isso é uma correlação e hipótese diagnóstica; não prova que estatísticas causaram o incidente. Não há plano lento nem perfil CPU dessas duas chamadas para confirmar essa explicação. Migração, revisão e outras atividades também coincidiam com a janela, sem atribuição causal comprovada.
- Probe posterior do ID exato em duas publicações: 24 GETs, quatro clientes, resposta completa consumida e IDs/publicação/fonte/relação conferidos, 24 respostas 200, p50 9,22 ms, p95 47,62 ms e máximo 63,72 ms. Evidência com cada request ID e estatísticas observadas: `docs/evidence/detail-http-probe.json`. Comando reproduzível: `node --env-file=.env --import tsx scripts/domain-detail-probe.ts`.
- Não houve alteração de SQL, índices, estatísticas, timeouts, proteção HTTP ou snapshot para obter esses tempos. O backend permanece congelado. Não se declarou uma correção de causa que não foi reproduzida. O probe pequeno e aquecido não é o gate final de desempenho: a coordenação executará dez clientes/200 requisições após consolidar o corpus, sem OCR concorrente, incluindo detalhes e não apenas listagens.

O container `ca-domain-test` na porta 55433 pertence à frente domínio, é fixture descartável e não é o banco principal. Nenhum container ou dado foi removido nesta investigação.

## Atualização global por fonte — correção J11

O auditor identificou que um recibo parcial do produtor não poderia substituir a publicação global: caches incompatíveis poderiam deixar apenas a fonte reprocessada. O contrato foi alterado conjuntamente com produtor e operações.

- O enqueue fixa `base_publication`, seu SHA e as fontes alvo; retries conservam esse payload. `exportIngestionBase` exporta contexto BR real dessa base em partes, com schema/hash fixado. O produtor recebe `--base-artifact` e `--base-publication`, verifica o contexto e gera um recibo parcial identificado `source_update_receipt`; não altera `latest` nem inventa correspondências quando uma referência não existe.
- `prepareGlobalIngestionUpdate` em `src/domain/ingestion-update.ts` verifica recibo/contexto/base e compõe novo artefato GLOBAL por páginas de 50 registros. Somente fontes alvo e seus itens/vínculos afetados são substituídos. Fontes, textos, evidências, posições, metadados e relações fora do escopo são preservados. Recibos raw e global possuem IDs/SHA distintos e linhagem explícita; o raw não é importado como publicação pública.
- O writer `src/domain/shard-writer.ts`, implementado pelo subagente real `/root/domain/flat_json_import`, grava gzip em fluxo, limites de 8 MiB/registro e 20 MiB/parte, contagens derivadas, hashes das coleções e arquivos, sidecars e publicação imutável do manifesto. Não cria string ou grafo nacional inteiro.
- `src/domain/ingestion-coverage.ts`, da mesma frente delegada, preserva linhas fora dos recortes afetados. Nas linhas compartilhadas, mantém partes atribuídas às outras fontes e recalcula contagens sobre a união final exata; não soma percentuais. O recorte alterado exige reconciliação novamente. Agregados legados mistos sem atribuição suficiente são recusados explicitamente.
- A prova independente de preservação confere inventário completo, SHA/contagens por fonte fora do alvo, relações e cobertura fora dos recortes afetados. Além dos hashes de valores JSON, compara os payloads por igualdade JSONB no banco, que distingue perda de precisão numérica e não confunde grafias numéricas equivalentes (`1.0`/`1`). Escopos de cobertura declarados precisam coincidir com os recortes derivados das fontes alvo; não podem excluir outras UFs da prova.
- Dependências documentais cruzadas não podem desaparecer: alteração de uma edição citada por itens fora do alvo, ou perda de membros locais fora do alvo numa relação muitos-para-muitos, bloqueia a atualização e pede escopo explícito dessas dependências. Dimensões de revisão/origem dos registros não são convertidas em equivalência ou aprovação humana.
- `publishGlobalIngestionUpdate` revalida preservação e, na mesma transação com advisory lock, exige `current_default === base_publication`, publica a visibilidade e registra o evento. Base vencida retorna 409 e não expõe o candidato. A base anterior permanece imutável e consultável no histórico.
- Última suíte registrada: 75/75 testes, zero falhas/skips (`docs/evidence/global-source-update-tests.log`), incluindo PostgreSQL real descartável, cobertura compartilhada, muitos-para-muitos, idempotência, contexto BR adulterado, escopo de cobertura forjado, dependências cruzadas, colisão de serialização numérica e corrida de publicação. ESLint e TypeScript passaram; o auditor repetiu 75/75 independentemente. CSV 1.1 exporta os mesmos pins de schema; 1.0 legado não recebe pins inventados. A jornada HTTP/worker/restart continua sob responsabilidade de operações e auditoria; a prova nacional editorial permanece separada.

Comando para exportar contexto fixado: `node --env-file=.env --import tsx scripts/export-ingestion-base.ts --publication ID --directory data/bundles/DIRETORIO`. A cópia de ensaio com dados reais em banco aleatório próprio é executada por `scripts/domain-global-update-real.ts`; nenhuma tabela administrativa é copiada e o banco de ensaio é removido ao final.

### Ensaio global real executado

Base ca77: 247 fontes, 38.322 itens, 13.007 relações. Recibo PE: 99 itens da fonte `pe-historia-pernambuco-2026`, mais 1.767 itens BR exatos de contexto. O novo global `ca-update-e93e7f67dee4718af70cc37f2fc0cedc` contém as mesmas 247 fontes, 38.413 itens e 13.007 relações: os 99 registros substituíram oito anteriores dessa fonte, sem remover dados das outras 246 fontes nem inventar vínculos. Partes estruturais são itens documentais; não foram rotuladas como 99 habilidades.

O ensaio copiou somente o snapshot público por páginas para banco aleatório próprio na porta 55433, preparou o global, comparou todas as provas de preservação e exerceu publicação CAS apenas nesse banco. O banco foi removido ao final; o principal permaneceu somente em leitura. A execução levou 200,5 s, pico RSS 424.574.976 bytes (~405 MiB), sem string nacional integral. Não é um ensaio de latência HTTP nem de completude editorial.

Artefato global real: `data/bundles/global-update-real-curriculum_test_0c28b6c00f65/snapshot.manifest.json`, SHA `ab8fbec349ee98460005c81e1e641285bb3fbf3bde0ec99b8ccac3ca9f41471e`, 14 partes. O validador Python independente verificou todos os hashes, registros, contagens, referências, hierarquia e JSON Schema 1.1.0. Evidências: `docs/evidence/global-source-update-real.json`, `.log` e `global-source-update-real-artifact-validation.json`.

Um ensaio anterior encontrou statement timeout após importar no banco descartável. O ensaio final passou sem aumento de timeout; a submissão concorrente de consultas pelo mesmo cliente PG foi removida. A causa específica do timeout anterior não foi demonstrada, portanto não se atribui uma correção causal nem se usa este resultado para explicar o antigo incidente de 14 segundos no detalhe HTTP.

### Correção após falha real do worker J11

O ensaio HTTP de operações encontrou nova falha às 15:04:09 UTC, agora identificada como `candidate unaffected relation hashes`. O candidato `ca-update-030922b2b405195b333a3e97b0e39be9` já estava importado e privado (38.413 itens/247 fontes/13.007 relações); a base ca77 continuou padrão. O job permaneceu pausado, sem publicação.

A captura posterior mostrou autoANALYZE às 15:04:12–15. O plano da execução fria original já não estava disponível, portanto não se atribuiu o timeout integral às estatísticas. O plano observado revelou desperdício independente disso: cada página de 50 relações reconstruía um anti-join sobre toda a fonte/membros, com varredura de 155.487 itens, 29.720 blocos lidos e 2.575.386 comparações descartadas. A primeira página medida custou 362,043 ms.

`relationProof` agora lê primeiro 50 relações por chave primária, consulta apenas os IDs de membros dessa página (lotes de até 250) e classifica fontes/evidências alvo. A igualdade JSONB exata das relações preservadas também é comparada por lote. Não reconstrói o join global por página. `sourceProofs` mantém hashes por fonte durante uma única passagem indexada dos itens, preservando a mesma ordem e os mesmos digests anteriores.

No mesmo candidato real, a página medida passou a 0,483 ms na leitura e 2,458 ms no lookup dos 100 membros, usando índices. As medições foram sequenciais e o cache posterior estava aquecido; não constituem comparação A/B em cache frio nem provam o p95 sob carga. O plano demonstra a eliminação da varredura e do join globais por página. A verificação integral concluiu em 30,5 s durante outros checks concorrentes, com as 246 fontes e 13.007 relações preservadas e hashes idênticos; esse tempo total não é benchmark isolado. Nenhuma DDL, ANALYZE manual, alteração de timeout ou mutação do snapshot foi usada. Evidências: `docs/evidence/global-cold-relation-plan-before.json`, `global-cold-relation-plan-warm-execution.json`, `global-cold-relation-plan-after.json` e `global-cold-relation-verified-after.json`.

Última suíte após a correção: **79/79**, zero falhas/skips; ESLint e TypeScript passaram. Regressão adicional cobre uma primeira página inteiramente afetada pelo alvo, garantindo que a próxima página de relações externas não seja omitida. Operações retomará a jornada HTTP/worker/oracle na imagem reconstruída; somente essa jornada pode provar a integração operacional corrigida.

## Revisão da política de tipos documentais

A coordenação identificou que seis tipos de aprendizagem eram insuficientes para os adaptadores reais. `src/domain/item-kinds.ts` agora define 21 tipos explícitos, usados pelas métricas, projeção local, matriz nacional e contagem de filhos de aprendizagem. Inclui competências comuns IFA e gerais de Computação sem código, capacidades do Acre, aprendizagens específicas, habilidades de componentes/eixos e qualificações profissionais. A formação docente do Magistério EM é formação dos estudantes futuros docentes, conforme o caderno SC p. 37; não foi excluída pelo termo “docente”.

Finalidades de curso/trilha/organização (`objetivo_curso_geral`, `objetivo_trilha`, `objetivo_formativo`), direitos, avaliação, normas e contextos têm categorias/contagens separadas. Tipos desconhecidos permanecem não classificados. O complemento histórico `structural_or_documentary_items` conserva compatibilidade e informa que inclui também finalidades/direitos/avaliação; esses registros não são rebatizados como estrutura. Nenhum tipo, texto, código, vínculo ou snapshot foi alterado. Regras e bases documentais: `docs/methodology.md`.

O inventário `docs/evidence/item-kind-inventory.json` registra 83 tipos observados em 36 sidecars reais, SHA dos arquivos e categoria explícita para todos. Há versões sobrepostas: ocorrências dos sidecars não são totais de publicação nem cobertura nacional. Dois testes leves passaram, incluindo o inventário real e a distinção de finalidades/direitos/avaliação/referências; TypeScript e ESLint passaram. A regressão SQL adicionada cobre os dois tipos nacionais sem código, expectativas locais antes omitidas, categorias negativas, contagens de coorte e filhos da hierarquia.

**Verificação SQL e suíte completa desta alteração ainda pendentes.** Operações informou EIO no content store/metadados Docker após falta de espaço, banco principal encerrado e worker não saudável. A coordenação suspendeu novos testes/exports até recuperar a infraestrutura. Nenhum container, banco novo ou teste pesado foi iniciado por esta frente. O resultado anterior 79/79 não cobre esta revisão de tipos; não pode ser usado para aprová-la. Retomar `npm test` em banco descartável quando operações liberar a janela, então repetir a integração na imagem reconstruída.

### Checkpoint 2026-10-28 — experiências e idade documentada (SQL pendente)

Política v2 mantém os 21 tipos de aprendizagem e acrescenta `experience`/`experience_items` para as 465 experiências AP, separadas dos 93 objetivos. `objetivo_normativo` recebe categoria normativa; organizadores AP e os novos contextos RN/RR/PI foram classificados explicitamente pelos papéis literais, sem promoção por substring. As análises retornam `by_kind.category` e categorias disjuntas cuja soma fecha `unique_items`; o complemento legado esclarece experiências, finalidades, direitos e avaliação. Inventário atualizado em `docs/evidence/item-kind-inventory.json`: 125 tipos/56 sidecars, 34 vinculados e 22 não vinculados/pesquisa; o tipo concorrente `experiencia_sugerida` apareceu ao fechar o checkpoint e fica `unclassified` até confirmar papel com o responsável da fonte (o gate de inventário precisa dessa decisão antes do próximo teste). SHA por sidecar, vínculo configurado via `uncoded_items_path` e ocorrências com limites explícitos; nenhum contador desse inventário é total publicado ou prova de reconciliação.

`src/domain/age.ts` implementa `parseAgeMonths` (0..1800, inteiro/faixa inclusiva) e `validatePositionAge` (limites em par, prova `Evidence[]` com fonte/página ou seção/trecho, origem explícita opcional). `publication.ts` usa o validador também no import sharded, que já chama `validateBundle` por lote. `service.ts` filtra interseção numérica somente com limites/evidência documentados; `age_group` compara macro ou micro `age_label`, normalizando português/espaços. Desconhecidos só entram no filtro numérico com `include_unknown_positions`, sem inventar idades. O filtro foi propagado a `matrixContext.common`, `listRelations`; comparação, exportadores e URLs genéricas de continuação preservam a query. Nenhuma alteração nos schemas JSON imutáveis, core do produtor, J11 ou snapshots.

Verificação: `tests/domain.age.test.ts` + `tests/domain.item-kinds.test.ts` passaram 5/5 sem skips antes da chegada concorrente de `experiencia_sugerida`; ESLint direcionado passou. O inventário final registra essa nova pendência explicitamente, sem alegar que o gate anterior cobre os arquivos posteriores. As regressões SQL de `tests/domain.integration.test.ts` foram ampliadas para experiências/normas e faixas inclusivas/unknown/macro-micro/relações/matriz, mas **não foram executadas** por bloqueio de infraestrutura. TypeScript ainda aguarda agente API/MCP atualizar `src/shared/contracts.ts` Position/Query (erros esperados age_label e age_months); não se afirma contrato MCP/OpenAPI concluído. Root solicitou fechar este turno para liberar a capacidade desse agente. Rodar SQL/full npm test somente após janela explícita ops/root, sem containers adicionais agora; resultados antigos 79/79 não validam este patch.

### Checkpoint 2026-10-28T17:15Z — diagnóstico integrado após recuperação

Root liberou testes SQL pequenos após recuperação da infraestrutura. `npm test` executou a suíte completa: **91 testes passaram, 0 falhas, 0 skips**, 21 arquivos, em PostgreSQL `postgres:17.11-bookworm` local, container descartável próprio `ca-tests-0b0dbc22faa2` e banco `curriculum_test_0b0dbc22faa2`. O runner removeu o container ao terminar; nenhuma publicação/default do banco principal foi alterada. As regressões SQL de categorias e idade passaram, incluindo competências BR sem código, experiências fora do denominador de aprendizagem, soma das categorias, interseção inclusiva no limite de 12 meses, macro/microrótulos, opção explícita de desconhecidos, propagação às relações/matriz. Contratos API/MCP já atualizados pelo agente responsável; TypeScript global e ESLint direcionado passaram.

`experiencia_sugerida` foi confirmada por Root como coluna literal TO e incluída em `experience`, mantendo a lista de 21 tipos de aprendizagem. O inventário refeito registra 125 tipos/62 sidecars, 38 vinculados por configuração e 24 não vinculados/pesquisa, sem tipos não classificados naquele instante. São 49.472 ocorrências de registros sobrepostos (37.422 em sidecars vinculados), **não** totais publicados/deduplicados ou cobertura nacional.

Evidências: `docs/evidence/domain-suite-diagnostic.log`, `domain-suite-diagnostic.json`, `domain-suite-diagnostic-before.json` e `domain-suite-diagnostic-after.json`. Fingerprint antes `a2abf16f56400ef9d17107ad7fbe4b7cf4f5387b1ba5da87786eb43beb06b75a`; depois `ab7bcb3e8042f6c10e56a7d603e36d421e370124e2641d70924c436a91a53513`. Houve alterações concorrentes em seis arquivos de sidecars/verificadores ES/MS/RO, listadas na evidência; por isso o resultado é **diagnóstico integrado, não aceite imutável de release**. Nenhum benchmark/carga nacional/build/alteração de pipeline foi executado nesta rodada; o wrapper final deve rodar depois do congelamento de código/dados.

### Checkpoint política v4 — 16 novos papéis e sínteses EI

A política `documentary-item-roles-2026-10-28-v4` classifica explicitamente os 16 tipos novos ES/TO e os dois tipos adicionais de síntese. O responsável TO confirmou `rotulo_direito` como rótulo de contexto, distinto do enunciado completo do direito. O responsável ES (`pr_adapter`) confirmou `objetivo_curricular` como finalidade do componente, `saber_curricular` e pilares como exposição conceitual/contexto, ações docentes/contextos como contexto e indicadores/orientações de avaliação como avaliação. Não se promove por prefixo, verbo ou semelhança de nome.

Após leitura dos 19 enunciados observáveis e do aviso primário do quadro, Root autorizou explicitamente `sintese_aprendizagem` como **22º tipo** de expectativa discente, confirmado pelo responsável ES em nível geral do segmento EI. `campo_sintese_aprendizagem` é contexto. A nova identidade v4 evita reutilizar políticas anteriores com 21 tipos. Preservam-se tipos/textos/códigos, posições desconhecidas, aviso de que sínteses NÃO são pré-requisito de acesso ao EF e estados OCR/revisão pendentes. Classificação não comprova desenvolvimento individual, literalidade OCR, revisão pedagógica nem completude. Nenhuma fonte, artefato ou registro foi alterado por esta frente.

Evidência documental: `docs/evidence/item-kind-decisions-v4.json` (amostras literais, fontes, páginas, SHA e razões por papel), `docs/methodology.md` e inventário atualizado. Nesse instante: 143 tipos em 82 sidecars, 43 vinculados por configuração e 39 não vinculados/pesquisa, 66.394 ocorrências sobrepostas, 41.323 nos sidecars vinculados, zero tipos não classificados; esses números NÃO são total deduplicado publicado ou cobertura nacional.

Verificação focada: **7/7 testes puros passaram, zero skips**, TypeScript global e ESLint direcionado passaram. Primeiro teste novo assumiu incorretamente que todas as 221 ações docentes tinham cabeçalho Dicas; onze estão no quadro de princípios p60. Corrigida apenas essa suposição do teste, sem relaxar o gate de inventário; log de falha preservado. Relatório e hashes: `docs/evidence/item-kind-v4-verification.json`; log final `item-kind-v4-pure-tests.log`. Por instrução Root, NÃO foram executados nova suíte SQL/full, build, pipeline ou mutação no banco nesta rodada. O diagnóstico anterior 91/91 antecede v4 e não serve de aceite desta revisão; wrapper final deve verificar a versão congelada depois das mudanças concorrentes de Source.
