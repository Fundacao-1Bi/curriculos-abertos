# API REST e MCP

Implementação: src/app/api/v1/[[...path]]/route.ts, src/mcp/ e src/app/mcp/route.ts. Compartilha src/domain/service.ts e a mesma publicação PostgreSQL com o portal. Não depende de modelo pago.

## Contrato e limites

Especificação efetiva em GET /api/v1/openapi.json, documentação pública em /desenvolvedores. Todas operações do mandato API-01 estão roteadas. Toda consulta curricular retorna `{publication,data,total?,page?,limit?,next?}`; não confundir publication com versão oficial do currículo. Queries aceitam publication, uf, curriculum, edition, q, stage, component, area, year, age_group, period, kind, relation_type, origin, technical_validation_status, pedagogical_review_status, publication_status, item_id, national_id, page e limit. Aliases portugueses: publicacao, curriculo, edicao, etapa, componente, ano, tipo, pagina, limite, codigo e busca. include_unpositioned é alias de include_unknown_positions; anos/blocos documentados são preservados.

Aprendizagens, relações, panorama, comparação e matriz usam páginas de 1–100 registros (padrão 25); catálogos de UFs/redes/currículos/fontes/publicações retornam a coleção completa sem corte, e page/limit não se aplicam a essas coleções. Páginas de aprendizagens com 1–100 registros (padrão 25), lote 1–100 IDs, comparação 2–3 UFs distintas, JSON até 64 KiB. O lote permite entradas inválidas (inclusive string vazia/longa, null ou objeto), retornando o resultado individual; somente o envelope inválido ou limites totais excedidos são recusados antes da consulta. Comparação admite `curricula:{SP:"id",PE:"id"}` e `editions:{SP:"edição",PE:"edição"}` por UF. Filtros desconhecidos são erros 400. Busca exata de código tem precedência, seguidos de prefixo e correspondência textual/índice português. Normalização de busca preserva a redação/código canônicos.

Sem configuração, PUBLIC_RATE_LIMIT=600/minuto por instância/categoria/transporte, EXPORT_RATE_LIMIT=30/minuto e CONTRIBUTION_RATE_LIMIT=10/hora. A distribuição Compose/.env.example configura 120/10/10; o ambiente de QA pode usar um override documentado (por exemplo1200/minuto) sem alterar os defaults do produto. /desenvolvedores e OpenAPI mostram os valores efetivos do ambiente. Sob TRUST_PROXY=true, o operador garante que o proxy sobrescreve X-Forwarded-For, e os limites passam a ser por cliente. Não confiar em cabeçalhos do cliente por padrão. Host e Origin exigem PUBLIC_URL/ALLOWED_HOSTS/ALLOWED_ORIGINS; não há CORS aberto. API e MCP registram contagens, códigos HTTP e latência agregada no banco, usando padrões de rota sem parâmetros ou dados pessoais. GET retorna ETag, X-Data-Publication e X-Request-ID, permitindo 304. Erros: `{error:{code,message,request_id,details?}}`; 400 entrada, 403 origem/host, 404 inexistente, 409 export não pronta, 413 payload, 415 tipo, 429 limite, 502 contrato de saída incompatível, 503 publicação/serviço indisponível. Logs estruturados não registram corpos de contribuições.

## Exemplo executável de consulta e paginação

```sh
curl -fsS 'http://localhost:3000/api/v1/publicacoes'
curl -fsS 'http://localhost:3000/api/v1/aprendizagens?q=EF01MA01&limit=2'
```

Use o publication retornado em todas as próximas páginas/consultas. GET por código pode retornar múltiplos documentos; use o ID canônico retornado em `/aprendizagens/{id}`. Nunca use código isolado como chave global.

```sh
curl -fsS -H 'Content-Type: application/json' \
  -d '{"ufs":["SP","PE"],"stage":"EF","limit":10}' \
  http://localhost:3000/api/v1/comparacoes
```

O script `scripts/mcp-verify.ts` descobre IDs reais, compara HTTP/API/MCP por ID, texto, fonte, publicação e resultados. Não contém IDs fictícios no caminho de sucesso. A inexistência controlada ocorre apenas no caso negativo.

## Downloads persistentes

POST `/api/v1/exportacoes` com `{format:"json"|"csv",...filtros}` fixa a publicação antes de enfileirar. Resposta 202 contém id/status/status_url; o worker executa fora da requisição. GET `/exportacoes/{id}` mostra progresso, SHA256, tamanho e download_url quando status=succeeded. GET `/exportacoes/{id}/arquivo` verifica checksum antes do download. O arquivo é persistente no volume STORAGE_DIR, chave validada `exports/{uuid}.{json|csv}`; não é aceita URL/caminho livre. JSON preserva o bundle relacional; CSV usa tabelas lógicas relacionadas em linhas record_type,id,payload_json (manifest/source/item/relation/coverage), preservando posições, evidências e relações como JSON; relatórios usam uma célula json_report integral. Ambos aplicam proteção contra fórmulas. Não há corte silencioso de resultados nem vazamento de contribuições ou administração.

## Contribuições

POST `/api/v1/contribuicoes` recebe kind error/source/relation, record_url ou record_id, description e evidence_url opcional; website/honeypot é antispam. Sem GitHub ou coleta de contato. Cria fila privada persistente, não modifica publicação. GET `/contribuicoes/{uuid}` expõe somente identificador, situação e datas. A decisão autenticada ocorre no admin, com auditoria do ator real.

## MCP real

SDK oficial `@modelcontextprotocol/sdk` fixado em 1.32.2. O SDK entregue anuncia 2025-11-25 e negocia também 2025-06-18, 2025-03-26, 2024-11-05 e 2024-10-07. Não reivindicamos implementação da revisão documental 2026-07-28, que o SDK fixado ainda não anuncia. Transporte remoto `/mcp`: **Streamable HTTP stateless**, WebStandardStreamableHTTPServerTransport oficial, com initialize/notifications, tools/list e tools/call reais, resposta JSON admitida pelo transporte. GET SSE e DELETE têm semântica do SDK para modo stateless; não há sessões persistentes falsas. Schema Zod de entrada e saída, ferramentas somente de leitura com readOnlyHint/idempotentHint. structuredContent preserva resultado completo; content contém apoio breve derivado.

Ferramentas: listar_curriculos, buscar_aprendizagens, consultar_aprendizagens, consultar_correspondencias, consultar_panorama_bncc, comparar_curriculos, consultar_analises, consultar_fontes, consultar_cobertura, consultar_publicacoes. Sem SQL/shell/proxy/escrita ou diagnóstico de acervo.

Configuração local stdio (Node 24/25 e DATABASE_URL fornecido no ambiente do processo):

```json
{"mcpServers":{"curriculos-abertos":{"command":"node","args":["--import","tsx","/caminho/absoluto/Curriculo-Aprendizap/scripts/mcp-stdio.ts"],"env":{"DATABASE_URL":"postgresql://usuario:senha@localhost:5432/curriculos"}}}}
```

O stdout do processo é reservado ao protocolo. Também pode usar `npm run mcp` em host que aceite comando npm e cwd do projeto; a configuração canônica usa node diretamente para evitar mensagens do runner no stdout. O processo stdio não exige autenticação administrativa; a credencial PostgreSQL deve ser mantida somente no host confiável, de preferência com papel read-only para as tabelas curriculares.

Cliente remoto: configure o host para URL `http://localhost:3000/mcp`, tipo streamable-http (varia conforme o host). Teste de referência usa Client/StreamableHTTPClientTransport do SDK oficial, não uma função handler direta:

```sh
VERIFY_BASE_URL=http://localhost:3000 npx tsx scripts/mcp-verify.ts --stdio
```

O script grava `docs/evidence/mcp-interoperability.json` com cliente, SDK, protocolo anunciado/suportado, transporte, IDs reais, publicação, comparação API, paginação/lote, erro controlado e resultado. Evidências de execução ainda dependem da aplicação e publicação carregadas; a existência deste guia não prova uma execução bem-sucedida.

## Estado de verificação desta frente

2026-10-28: `npx tsx --test tests/api-contract.test.ts` executado: 8 testes, 8 aprovados, 0 skip. Cobrem aliases/código preservado, limites, combinação de UFs, lote com entrada inválida, protocolos de contribuição, host/origin, corpo limitado e operações OpenAPI. Incluem rejeição de contexto de exportação inválido antes de criar jobs e rate limit com Retry-After. Interoperabilidade real e jornadas HTTP serão registradas após integração com banco e corpus reais. Sem homologação humana implícita.

### Execução integrada inicial (não é aceite nacional)

Em 2026-10-28T03:40:43Z–03:40:48Z, `npx tsx scripts/api-verify.ts` executou 54 verificações HTTP contra `http://localhost:3000`, publicação `ca-64e60bb2c92be368dcd7` (2.108 itens SP, nenhum item BR naquele instante). Todos os status/contratos executados passaram, incluindo ETag 304, limites/erros 400/403/404/409/413/415, lote por item, comparação de 2/3 UFs, contribuição persistente, dois jobs reais de export JSON/CSV e checksum de download. O resultado global permaneceu **false / exit 1**, pois panorama exigia BNCC real ausente. Evidência: `docs/evidence/api-verification.json` (pode ser substituída pela execução final mais recente).

Em 2026-10-28T03:39Z, o cliente MCP oficial conectou via Streamable HTTP, negociou inicialização, descobriu as dez ferramentas e executou busca, lote e paginação com item SP real/consistência da API. Resultado global **false / exit 1** por BNCC ausente antes de concluir o panorama; não declarar MCP-03 completo com essa execução parcial. Evidência: `docs/evidence/mcp-interoperability.json` (a execução final deverá testar também stdio e as demais operações).

No host com o arquivo `.env` criado pelo bootstrap, uma execução que fornece as credenciais de stdio sem imprimi-las é:

```sh
node --env-file=.env --import tsx scripts/mcp-verify.ts --stdio
```

A suíte HTTP `scripts/api-verify.ts` mantém falhas de corpus explícitas e ainda executa as frentes independentes; ela não substitui a reconciliação nacional nem declara UFs prontas.

### Interoperabilidade e exports completos verificados em 2026-10-28

Execução diagnóstica integrada com a publicação real `ca-77fb8076598b567e1ba3` (38.322 itens, 13.007 relações, 247 fontes):

- `TEST_PUBLICATION=ca-77fb8076598b567e1ba3 node --env-file=.env --import tsx scripts/mcp-verify.ts --stdio`: **exit 0**, Streamable HTTP e stdio com cliente SDK oficial; HTTP negociou 2025-11-25. As dez ferramentas, panorama BNCC, comparação, lote com entradas inválidas individuais, paginação, erros e paridade API foram exercitados.
- `TEST_PUBLICATION=ca-77fb8076598b567e1ba3 node --env-file=.env --import tsx scripts/api-verify.ts`: **exit 0**, de 04:09:22Z a 04:10:17Z. Todas as operações REST, erros/limites/ETag, contribuição e cinco exports reais (base JSON/CSV, comparação, análises e panorama) foram exercitados. Os relatórios confirmaram contagem integral dos respectivos recortes, sem corte por paginação.
- O JSON nacional baixado teve 241.529.822 bytes e SHA256 `8e55a6fbb4a2df18c20f0b4f282597f943c0a176139ed0f2bd4c304b943a1be3`. O CSV teve 247.018.913 bytes e SHA256 `ecdc4f20a78ace0e5938209987237f7abe09ddf951ff85e96bd5484e2246387d`. Ambos reconciliaram 38.322 itens, 13.007 relações, 247 fontes e 307 linhas de cobertura. IDs únicos, referências, schema de cada registro e texto/evidência de amostra real da API foram conferidos.

`scripts/api-export-stream.ts` grava o corpo HTTP diretamente em arquivo e calcula SHA256 por chunk. O parser mantido `stream-json@3.7.0` valida toda a gramática JSON e descarta os payloads após conferir cada registro; conserva somente metadados, contagens e conjuntos de IDs necessários à integridade referencial. O CSV é lido por máquina de estados incremental que preserva aspas, vírgulas e quebras de linha entre chunks, validando cada payload JSON. Não há `Response.text()`, `arrayBuffer()` ou `JSON.parse()` do arquivo nacional completo no teste. O maior registro desta execução foi 226.622 bytes. Relatórios menores têm teto explícito de 128 MiB antes de materialização no teste; o teto não corta exportações do produto.

Três testes específicos do processamento em fluxo passaram, incluindo JSON truncado, referência ausente, CSV com aspas/quebras e checksum de bytes UTF-8. Fixtures ficam exclusivamente nos testes. Evidências sanitizadas: `docs/evidence/api-verification.json` e `docs/evidence/mcp-interoperability.json`; arquivos baixados ficam em `var/qa-downloads/`, fora do Git.

O download do servidor também foi alterado para conferir SHA256 por stream e entregar `ReadableStream`, preservando a rota e seus headers. Essa alteração de runtime ainda requer build/reexecução na próxima versão integrada. As execuções acima comprovam a terceira build e o corpus indicado, não a reconciliação documental completa das 27 UFs nem um gate final para código posterior.

### Estrutura documental, filhos diretos e aliases

`GET /api/v1/curriculos/{id}/estrutura?publication=...` preserva `data` como a lista anterior de agrupamentos por etapa/componente/área, com `item_count`, `kinds`, `year_labels` e `age_groups`. O campo adicional `hierarchy` contém `nodes`, `total`, `origin`, `methodology` e `pending_reason` quando pertinente. Cada nó preserva `id`, `parent_id`, `code` (inclusive nulo), `text`, `kind`, `source_id`, `positions`, `evidence`, `child_count` e `learning_child_count`. `hierarchy.total` conta nós retornados; o `total` da resposta conta agrupamentos. `child_count` e `learning_child_count` contam filhos diretos, não todos os descendentes. Aprendizagens leaf são obtidas pela busca e não duplicadas na lista de nós.

A hierarquia representa estrutura documental publicada e não estabelece pré-requisito pedagógico. Campos e localizadores são validados em runtime com `StructureResultSchema`, também disponibilizado no OpenAPI. Hierarquia vazia permanece explícita, com a pendência informada; o serviço não inventa nós para completar a navegação.

`GET /api/v1/aprendizagens?parent_id={id}&publication={publicação}` e a ferramenta MCP `buscar_aprendizagens` com `parent_id` retornam somente filhos diretos no snapshot fixado, com os filtros/paginação usuais. IDs de nós são opacos e escopados; não são códigos oficiais inventados.

`code_aliases`, quando presente numa aprendizagem, contém até cem aliases documentados para busca. `q` pode encontrá-los, mas a resposta conserva `code` com a grafia canônica e os aliases separadamente. Por exemplo, a importação da BNCC Computação preserva o código impresso `EF05CO011` e registra `EF05CO11` como alias, com a explicação documental na anotação; isso não cria equivalência curricular nem corrige silenciosamente a fonte.

Os novos testes `tests/api-structure.test.ts` verificam os dois denominadores, preservação de evidência/código nulo, hierarquia vazia, rejeição de IDs duplicados/contagens impossíveis/autorreferência, filtro opaco `parent_id`, aliases sem alteração do código e vinculação da resposta no OpenAPI. São fixtures isoladas de contrato; o teste PostgreSQL do domínio verifica a navegação de filhos e busca pelo alias em banco descartável. O script HTTP também valida a estrutura real e, quando encontra um nó com filhos, reconcilia `child_count` com a busca correspondente. Nenhuma fixture é importada no corpus público.

Jobs de exportação mantêm a publicação em `GET /exportacoes/{id}` desde o estado pendente, usando o snapshot gravado no payload do job; a consulta de progresso não resolve novamente a publicação padrão.

### QA de navegador da administração (preparada; execução pendente)

A suíte independente `tests/admin.spec.ts` usa Playwright e axe em desktop e celular. O harness `scripts/qa-admin-browser.ts` cria uma única conta temporária com ator `automated` pelo CLI seguro, senha aleatória em stdin e credenciais somente em memória. O processo de navegador recebe ambiente mínimo, sem credenciais do banco ou segredo de sessão do servidor. A configuração dedicada `scripts/qa-admin-browser.config.ts` mantém trace, vídeo e screenshots automáticos desligados; o reporter sanitiza mensagens antes de persistir evidências. Screenshots manuais ocorrem no login vazio/limpo ou depois da autenticação, com campos de acesso mascarados.

O roteiro cobre login/logout, erro real de autenticação, teclado/foco, overview, fontes, inspeção de aprendizagem real com publicação explicitamente fixada, erro de registro inexistente, contribuições e rascunho com transcrição idêntica à original. A criação/validação de rascunho ocorre uma única vez no desktop; não prepara nem publica snapshot. O celular inspeciona a publicação e o rascunho existente, verificando responsividade e acessibilidade. O cleanup revoga/remove somente a conta aleatória criada pelo harness, mantendo os eventos de auditoria e os registros de verificação identificados.

```sh
# Descoberta de dois testes sem abrir navegador, chamar aplicação ou criar conta:
npx tsx scripts/qa-admin-browser.ts --list
# Executar somente com build/banco prontos:
TEST_BASE_URL=http://localhost:3000 TEST_PUBLICATION=PUBLICACAO \
  node --env-file=.env --import tsx scripts/qa-admin-browser.ts
```

O modo de descoberta encontrou dois testes (desktop/mobile). Lint e tipos da implementação foram verificados; dois testes isolados conferem sanitização de segredos e a política de captura. **As jornadas reais, axe e screenshots desta nova suíte ainda não foram executados** enquanto a aplicação aguarda o novo build. Quando executada, a suíte registra `docs/evidence/admin-browser-verification.json` e evidências por run em `docs/evidence/admin-browser/`; não se deve interpretar a existência dos arquivos de teste como aprovação de ADM-02 ou QA-03.


### Fontes com arquivo ainda não localizado — schema 1.1.0

`Source.artifact_url` admite `null` explícito quando o endereço do arquivo não foi localizado. `official_url` continua registrando a página de procedência conhecida; ela não é inventada como endereço de download. Os campos de autoria, edição, vigência, coleta e integridade permanecem independentes. A ausência de um arquivo obrigatório continua no inventário e no denominador de cobertura; não representa ausência de currículo ou aprendizagem.

O schema `data/schema/1.1.0.json` documenta essa ampliação. O arquivo `1.0.0.json` foi preservado byte a byte para os artefatos históricos. Publicações novas fixam versão, caminho e hash do schema. Os testes `tests/source-contract.test.ts` verificam a preservação de `null` nos contratos e na validação de importação, rejeição de campo omitido e recusa de URLs não HTTP(S). A interface não oferece um link de arquivo inexistente.


## Idade documental em meses (FUN-03)

`age_months` aceita string com inteiro ou faixa crescente inclusiva entre 0 e 1800, por exemplo `0`, `0-6` e `48-71`. API REST, ferramentas MCP, comparação e exportação compartilham esse contrato. A consulta usa interseção com limites explicitados pela fonte. `age_group` consulta o grupo macro ou rótulo específico com normalização portuguesa. Rótulo, código e agrupamento escolar não geram limites automaticamente. Posições sem limites continuam desconhecidas; entram no recorte etário apenas com `include_unknown_positions=true`.

`Position` pode preservar `age_label`, `age_min_months`, `age_max_months`, `age_evidence` (array de `Evidence`), `age_interval_origin` e `age_unknown_reason`. Limites são ambos ausentes/nulos ou ambos inteiros coerentes de 0 a 1800. Limites presentes exigem evidência com fonte, trecho literal não vazio e página ou seção. A origem admitida é `explicit_source_header_units_to_months`. Os campos são opcionais para preservar compatibilidade de publicações existentes; o schema documental 1.1 fixado permanece inalterado. `tests/api-age.test.ts` verifica limites, ausência documental, evidência e propagação a OpenAPI/comparação/exportação. A execução real depende da próxima publicação e build coordenados.
