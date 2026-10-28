# Arquitetura e contratos de integração

Monólito modular Next.js 16 / React 19 / TypeScript estrito. PostgreSQL 17 como fonte de verdade, pg + migrations SQL versionadas e Drizzle para modelagem. Worker separado com fila PostgreSQL persistente. MCP SDK oficial TypeScript fixado 1.32.2 com Streamable HTTP e stdio. Leitura pública não requer IA paga. Distribuição autogerida Docker Compose; nenhum alvo remoto foi indicado/autorizado.

## Propriedade dos arquivos
- Coordenação: package.json, tsconfig, src/shared, documentação transversal, integração.
- Domínio: src/domain, src/db, scripts/migrate.ts, scripts/import-data.ts, tests/domain*.
- API/MCP: src/app/api/v1, src/app/mcp, src/mcp, scripts/mcp*, tests/api*, docs/api-mcp.md.
- Portal: src/app (exceto api, mcp e admin), src/components, public, docs/portal.md.
- Administração/operação: src/admin, src/app/admin, src/app/api/admin, src/app/api/auth, src/worker, scripts/admin*, scripts/ops*, Dockerfile, compose.yaml, Makefile, .env.example, docs/operations.md.
- Pipeline: pipeline/, scripts/data*, scripts/sources*, data/bundles/, data/coverage-manifest.json, docs/data*. Não alterar import-data.ts.
- Fontes: data/manifests/{batch}.json, data/raw/{UF}/, docs/sources-{batch}.md. Cada lote tem UFs exclusivas.

## Contrato de dados
src/shared/contracts.ts é o contrato canônico inicial. Fontes em data/manifests/{batch}.json: array Source (ou objeto com sources array, pipeline deve aceitar ambos). Arquivos de origem não redistribuídos até direitos verificados. data/raw ignorado no Git, metadados/checksums persistidos. bundle JSON imutável em data/bundles/{id}.json com Bundle. IDs de itens escopados por fonte e localização; nunca código isolado. Campos desconhecidos nulos. Extractions não reconciliadas não são UFs prontas.

## Contrato de serviços
src/domain/service.ts exporta funções assíncronas: listUfs(query?), listNetworks(query?), listCurricula(query?), getCurriculum(id,query?), getStructure(id,query?), searchLearnings(query), getLearning(id,query?), batchLearnings(ids,query?), listRelations(query?), panorama(id,query?), compare({ufs, ...query}), analyses(query?), coverage(query?), listSources(query?), getSource(id,query?), listPublications(query?), exportData(query?,format?). Todas retornam Result {publication,data,total?,page?,limit?,next?}. Lote retorna por ID found/not_found/invalid. Erros DomainError {status,code,message}. Filtros em inglês no domínio; API aceita aliases portugueses. Limite padrão 25 máximo 100; lote 100; comparação 2-3 UFs. Resolução da publicação uma vez por operação e paginação fixada. Domínio não lê fixtures nem usa seed sintética.

src/db/client.ts exporta pool pg. Tabelas administrativas acordadas com agente domínio/operação. Admin usa Better Auth, sem credenciais padrão. Mutações exigem sessão + papel + origem e auditoria real do ator.

## Escala: distribuição particionada

ADR003 define `curriculos-abertos/sharded-v1`: manifesto+partesJSONL.gz, integridade por parte e publicação relacional imutável. Transporte público mantémRESTv1/MCP; exports são escritos em streaming pelo worker. O formato monolítico inicial permanece importável. Detalhes concretos e limites implementados ficam em docs/domain-model.md e docs/data-reconciliation.md.
