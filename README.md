# Currículos Abertos

Consulta e integração de referenciais curriculares brasileiros, com portal em português, API REST, MCP oficial, downloads versionados e curadoria autenticada. Código de autoria do projeto sob MIT; dependências e materiais de terceiros têm condições próprias. Detalhes em [DATA-RIGHTS.md](DATA-RIGHTS.md) e em cada fonte.

**Estado do aceite:** consulte [docs/release-report.md](docs/release-report.md), [docs/verification.md](docs/verification.md) e o manifesto gerado `data/coverage-manifest.json`. Inventário de 27 UFs não equivale a 27 UFs prontas. O gate recusa lançamento nacional enquanto faltar qualquer documento/parte/etapa/componente ou verificação obrigatória. A publicação candidata é utilizável para conferência, mas não comprova completude.

## Executar

Pré-requisitos: Docker Engine com Compose v2, Node.js22/24/25 suportado, npm11 e Make. Não é necessária chave de IA ou serviço de e-mail.

```sh
npm ci
make bootstrap
make admin-create EMAIL=seu-email NAME='Seu nome' ACTOR_TYPE=human
```

A criação do administrador lê senha por stdin; nunca há senha padrão. Execute manualmente para uma pessoa; automações devem usar `ACTOR_TYPE=automated`. O bootstrap gera `.env` local privado com segredos aleatórios somente quando ausente, aplica migrations e importa o bundle pronto sem coletar novamente as fontes. Uma nova execução preserva publicações existentes. Não grave `.env` no Git.

- Portal: <http://localhost:3000>
- API: <http://localhost:3000/api/v1/publicacoes>
- OpenAPI navegável: <http://localhost:3000/desenvolvedores/openapi>
- MCP Streamable HTTP: <http://localhost:3000/mcp>
- Administração: <http://localhost:3000/admin>
- Liveness/readiness: `/api/health` e `/api/ready`.

```sh
make up
make verify
make release-check
make down
```

`verify` verifica as jornadas técnicas e não substitui o aceite documental. `release-check` retorna código diferente de zero para qualquer requisito obrigatório não verificado. Relatórios contêm publicação, comando, ator automatizado e identificação do código.

## Dados e manutenção

O ponteiro `data/bundles/latest.json` identifica um arquivo JSON real entregue, tamanho e SHA-256. Cada bundle tem sidecar `.sha256`. A importação verifica o checksum e a estrutura antes da transação; snapshots anteriores permanecem imutáveis. JSONs de teste ficam apenas em bancos descartáveis, fora do corpus.

```sh
make data-import DATA_BUNDLE=data/bundles/ID.json
make data-ingest
make sources-check
make backup
make restore BACKUP=var/backups/ARQUIVO.tar.gz RESTORE_DB=curriculos_restore_check
make admin-reset EMAIL=seu-email
```

A ingestão é executada pelo worker, com checkpoint e cache por hash. Monitoramento detecta mudança e abre avaliação; não troca automaticamente a versão pública. A reconstrução pelas fontes é separada da instalação normal e exige acesso legítimo às fontes e ferramentas documentais. PDFs privados de conferência ficam fora do Git. Consulte [docs/data-reconciliation.md](docs/data-reconciliation.md), [docs/operations.md](docs/operations.md) e o inventário `data/manifests/`.

## Integração

```sh
curl -fsS 'http://localhost:3000/api/v1/aprendizagens?q=EF01MA01&limit=2'
curl -fsS -H 'Content-Type: application/json' \
  -d '{"ufs":["SP","PE","MG"],"stage":"EF","limit":10}' \
  http://localhost:3000/api/v1/comparacoes
```

Fixe `publication` retornada nas próximas consultas, páginas e exports. Um código pode ocorrer em diversas fontes; o ID canônico é a chave de integração. Referência BNCC comum não demonstra equivalência integral nem ausência de ensino onde não houver mapeamento.

```sh
node --env-file=.env --import tsx scripts/mcp-verify.ts --stdio
```

Configurações do cliente, negociação, ferramentas e limites estão em [docs/api-mcp.md](docs/api-mcp.md). MCP é somente leitura; não há SQL, shell, proxy livre, importação de conteúdos privados ou diagnóstico de acervo.

## Desenvolvimento e verificação

```sh
npm run typecheck
npm run lint
npm test
npm run build
npx tsx scripts/api-verify.ts
node --env-file=.env --import tsx scripts/mcp-verify.ts --stdio
npx playwright test
npx tsx scripts/qa-performance.ts
npx tsx scripts/qa-production.ts
npx tsx scripts/qa-recovery.ts
```

`npm test` cria banco isolado e executa integração PostgreSQL real. Instalação limpa/reinício/recuperação usam projetos Compose descartáveis separados. As evidências de QA ficam em `docs/evidence/`; existir um script não prova execução. Para desenvolvimento local com o banco Compose: `node --env-file=.env --import tsx scripts/local-run.ts -- npm run dev`.

Arquitetura e contratos: [docs/architecture.md](docs/architecture.md). Especificação integral de aceite: [docs/requirements.md](docs/requirements.md). Progresso e ponto de retomada: [docs/progress.md](docs/progress.md). Contribuições: [CONTRIBUTING.md](CONTRIBUTING.md).
