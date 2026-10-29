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


## Contratos de integração consolidados — 2026-10-28

### Dados e proveniência

As versões locais de JSON Schema são imutáveis. A versão1.0.0 permanece byte a byte preservada;1.1.0 permite `Source.artifact_url=null` quando o arquivo não foi localizado. Página de procedência não substitui URL de download. Versão/caminho/SHA devem concordar com o registro revisado e os bytes locais; importação e transcode validam o contrato antes de SQL, sem resolver schemas na rede. Compatibilidade legada sem pin é declarada apenas para1.0.0.

Código nulo não afirma ausência de código na fonte. `official_code_present_in_source=true` com `code=null` representa leitura pendente; candidatos OCR não são exibidos como código confirmado. Ausência original exige evidência própria. A apresentação de datas preserva ano, ano/mês ou data completa; não inventa dia01 ou converte um calendário sem horário por fuso. Timestamps são apresentados no fuso America/Sao_Paulo. Os dados canônicos permanecem intactos.

### Atualização por fonte

O enqueue autenticado fixa a publicação pública base, seu SHA e as fontes-alvo sob lock. O worker exporta contexto nacional da mesma base, reprocessa o arquivo oficial conferido e recebe um artefato parcial técnico. Esse artefato não é importado como publicação global nem substitui o padrão.

O domínio compõe um novo artefato global em partes: substitui somente as fontes-alvo e seus registros afetados; preserva metadados, itens, evidências, posições, relações e cobertura fora do alvo. Dependências cruzadas e recortes mistos têm verificações explícitas. Hashes por fonte são complementados por igualdade JSONB exata; não se aceita apenas contagem. O recibo global tem identidade e checksum próprios, separados do recibo bruto e do arquivo de referência.

O job persiste sua preparação privada para pausa/restart/retomada. Replay deve conferir base/alvo/ator, artefatos, schema e recibos e reutilizar a mesma publicação, sem duplicação. A publicação autenticada usa comparação e troca: se o padrão já não for a base fixada, retorna conflito, preservando a preparação e a versão concorrente. Revisores e jobs automatizados não se tornam humanos pelo uso da administração.

Provas reais preliminares: a base ca77(247fontes/38322itens/13007relações) gerou candidata global com38413itens ao substituir PE8→99; as246fontes fora do alvo foram preservadas. Isso não comprova cobertura nacional nem substitui a jornada final HTTP/worker/restart, instalação limpa ou recuperação.

### Coleta e execução

O parser e o runtime possuem fingerprints próprios; mudanças durante processamento abortam a confirmação. Caches produzidos em runtime diferente não são rotulados como execução do runtime atual. Probes paralelos usam snapshots de código imutáveis e preservam os caches nacionais. Após os helpers estabilizarem, o lote completo acessível será reexecutado e cotejado com inventários independentes. Caches antigos, integridade de chunks ou sucesso de OCR não comprovam completude editorial.

Os assets CEDOC AP614/PB392 solicitados pelo usuário são EI/EF, sem crédito para EM. AP contém o mesmo conteúdo do snapshot MEC614 e é registrado como distribuição alternativa sem duplicar cobertura. PB392 possui alterações e escopo distintos do635; suas transcrições, IDs, contexto e evidências são separados, sem inferir vigência pelo catálogo.
