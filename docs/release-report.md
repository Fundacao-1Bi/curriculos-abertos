# Relatório de entrega — integração em execução

Atualizado em 28/10/2026, 14:27 BRT (17:27 UTC). O MVP nacional **não está concluído**. ACE-01/ACE-02 exigem todas as partes obrigatórias das 27 UFs estruturadas, reconciliadas e verificadas. Inventário, arquivos e interfaces não substituem esse aceite.

## Estado operacional atual

O runtime local foi recuperado por **um único reinício normal do Docker Desktop autorizado pelo usuário**. Portal, worker e PostgreSQL17.11 voltaram saudáveis; `/api/ready` retornou200 para ca77. O banco concluiu redo/checkpoint de WAL; contagens, SHA da publicação, migrations001–010, collation2.36, índices e backup foram novamente conferidos. `pg_amcheck` passou. O banco ContentiZAP, no mesmo Docker, voltou a aceitar conexões.

A falta de espaço anterior causou EIO e uma imagem nova incompleta (package.json vazio); ela não foi utilizada para recriar os serviços. Os containers antigos foram preservados. Um export **somente do filesystem**, privado0600 e sem volumes/segredos de configuração, foi comprimido, conferido e restaurado em teste descartável: health200 e fingerprint iguais ao runtime antigo. Configuração reconstruída exclusivamente dos valores estáticos do Dockerfile. Não houve reset, exclusão de volumes ou prune global.

GC dirigido de artefatos próprios recuperou margem superior a15GiB antes da nova extração. Guardas pré-build e pós-build agora verificam espaço, JSONs críticos e fingerprint efetivo da imagem antes do `up`. O build final e as jornadas de produção ainda não foram repetidos. Evidências: [recuperação](evidence/docker-desktop-normal-restart-recovery.json), [rollback](evidence/docker-recovery-runtime-rollback-archive.json) e [proposta original](evidence/docker-io-recovery-proposal.md).

## Produto implementado em código

Portal em português com busca, estrutura/hierarquia de currículos, fichas com evidências, panorama nacional, comparação de duas/três UFs, análises, fontes, histórico e downloads. API REST `/api/v1`, OpenAPI `/desenvolvedores/openapi`, MCP oficial Streamable HTTP `/mcp` e stdio. Administração autenticada, contribuições, rascunhos e revisão auditada, preparação privada, publicação e rollback. Worker PostgreSQL com checkpoint, pausa, retomada e atualização global que preserva as fontes fora do alvo.

Distribuição Docker Compose com Node22.23.4, PostgreSQL17.11 e Python3.11.2, healthchecks e volumes persistentes. Builds e execução em modo de produção foram realizados antes do incidente; isso não valida o estado final nem instalação limpa. Não há implantação remota nem alvo remoto autorizado. URLs locais de execução, quando o runtime for recuperado: portal `http://localhost:3000`, administração `/admin`, API `/api/v1` e MCP `/mcp`.

## Dados e processamento

O inventário do lote1.5 reúne **303 fontes**, com286 arquivos locais elegíveis para a extração final, nas 27 UFs e BR. Esses números incluem referência histórica auxiliar, distribuição alternativa e arquivos com integridade ou procedência pendentes; não são contagem de currículos aprovados. Nenhuma UF foi declarada pronta.

A última publicação padrão conferida antes da interrupção é `ca-77fb8076598b567e1ba3`: **38.322 itens, 13.007 relações e 247 fontes**. Sua identidade e integridade foram novamente conferidas após a recuperação do banco. O gzip original e os manifestos foram preservados; o JSON descompactado redundante foi retirado somente após igualdade integral de SHA, ausência de leitor ativo e registro de restauração.

`data/bundles/latest.json` ainda aponta para candidata parcial `ca-9d9b45e82947bd8fe35c` (20.612 itens/2.851 relações/269 fontes), que **não foi promovida**, pois reduziria a cobertura carregada. O lote consolidado1.5 iniciou após congelamento dos helpers: snapshot303fontes,286 elegíveis, revisão de mapeamento1.2.0. Ainda não foi consolidado, importado nem promovido. Não instalar essa candidata parcial como se fosse a entrega nacional final.

Os arquivos CEDOC de AP614 e PB392 indicados pelo usuário passaram HTTP/MIME/assinatura/parser, todas as páginas, bytes e SHA exatos. Escopo exclusivo EI/EF. AP614 tem conteúdo de páginas idêntico ao snapshot MEC614 e foi registrado como distribuição alternativa sem duplicação. PB392 tem diferenças materiais frente ao PB635 e recebeu adaptador próprio obrigatório: 1.946 itens, com auditoria independente e binding real. Edição e vigência não foram inferidas de metadados ou do catálogo. Evidências em `evidence/source-audit-cedoc-ap-pb/`.

As auditorias integrais encontraram e estão corrigindo omissões de colunas, objetivos sem código, continuações, posições explícitas e referências indevidamente promovidas a definições. RN, ES, MA, RS/MS e AM têm verificações específicas; Norte, Sudeste e complementos recém-coletados continuam com tarefas internas reais. O relatório de cada frente distingue o denominador original do número de itens emitidos. Cópias de páginas permanecem privadas quando a redistribuição não está estabelecida.

A referência histórica MEC de itinerários, distribuída pela SEDU/ES, foi adicionada separadamente: 14 páginas/217 registros, 72 habilidades, 16 finalidades formativas e 129 registros estruturais/contextuais. As 24 células, os códigos, as evidências e a cobertura de glifos foram conferidos; binding/finalizador reais passaram217/217. CHSA deste booklet não foi transformado em CHS da impressão DOU; não há alegação de identidade editorial ou vigência atual.

## Verificações executadas e limites

- Tipos e lint passaram em checkpoints recentes. A suíte completa teve **79/79** antes da nova política de tipos de aprendizagem; esse resultado não aprova alterações posteriores. A suíte diagnóstica posterior teve **91/91 testes aprovados, zero skips**, incluindo SQL real das categorias e interseção de idades. O PostgreSQL descartável foi removido. Como arquivos de dados mudaram durante a execução, esse resultado ainda não é o aceite congelado final.
- Schema1.0.0 foi preservado byte a byte;1.1.0 admite artefato ainda não localizado como null. Importadores Node e Python validam versão/caminho/hash e os registros, com paridade e testes negativos. Ca77 e a candidata de sete partes foram lidos integralmente em ensaios anteriores.
- O ensaio real de atualização global preservou **246 fontes, 38.314 itens externos ao alvo, 13.007 relações e307 linhas de cobertura**, com oracle SQL independente em2,91s. O fluxo HTTP/worker encontrou timeout de uma consulta; a correção foi implementada e verificada isoladamente, mas replay/reinício/retomada/publicação/rollback finais aguardam nova imagem congelada e verificações. Não houve promoção do recibo parcial.
- API e MCP passaram anteriormente sobre a publicação principal, com cliente oficial HTTP e stdio, dez ferramentas, erros, lote, paginação, panorama e paridade. Cinco exportações completas foram conferidas por streaming. Devem ser repetidos na versão final.
- Administração teve verificações reais de autorização, contribuições, revisão automatizada identificada, publicação/rollback e privacidade de preparados. Navegador administrativo passou2/2 desktop/mobile após correções de acessibilidade, com conta temporária removida. O conjunto final precisa nova execução vinculada ao código/publicação finais.
- Jornadas públicas selecionadas passaram em desktop/mobile, inclusive relação ao chegar pela página2 da busca. A execução diagnóstica integral antiga falhou por dados/hierarquia ausentes; esses requisitos continuam nos testes. A suíte atual tem10 casos considerando os dois projetos e ainda requer execução integral, sem filtros.
- Benchmark diagnóstico de200 requisições/10 clientes passou no corpus antigo, em runtime host. O benchmark de aceite Docker, com corpus consolidado e sem carga concorrente de OCR, está pendente.
- Migração lógica para PostgreSQL17.11 e comparação de contagens/digests foram verificadas antes do incidente. Isso não substitui instalação limpa, reinício e restauração integral do estado final.
- As oito dependências Python fixadas foram consultadas no PyPI em28/10: nenhuma vulnerabilidade ativa informada para essas versões. Npm audit também foi executado; os relatórios têm escopo explícito, sem alegação de auditoria completa do sistema operacional.

`docs/verification.md` e os registros de execução não devem ser promovidos a verdes por existência de scripts ou flags manuais. O gate permanece reprovado enquanto dados ou verificações obrigatórias estiverem pendentes.

## Acesso externo e outros impedimentos

| Parte | Evidência e limite atual |
|---|---|
| AP EM | Arquivo oficial147MB com árvore de páginas corrompida em aquisições repetidas do mesmo SHA; reparos incompletos rejeitados. Necessária cópia íntegra verificável. |
| PB EM | O navegador normal renderizou o PDF oficial de867p e a ficha informa7,6MB; aquisição local ainda não concluída. GETs anônimos inclusive no novo@@download retornamHTML, e salvamento normal do navegador está em investigação. Não converter acesso em inexistência curricular. |
| AC Computação | Resolução667/2025 obtida; currículo integral incorporado pelo ato ainda não localizado. |
| MS Núcleo Integrador/ementas2023 | URL oficial retorna página inicialHTML; fonte integral continua necessária. Projeto de Vida2024 não a substitui. |
| AL Computação | Cópia de pesquisa sem cadeia primária confirmada permanece fora do corpus publicado. |
| BA novo referencial EM | Ato249/2026 obtido, com aplicação em2027; edição integral ainda não localizada. Referência2022 não foi declarada inaplicável em2026. |
| MA Educação Digital | Atos de aprovação/diretrizes obtidos e estruturados; documento curricular integral aprovado continua necessário. |

Esta tabela não transforma trabalho interno em bloqueio externo. Há extração, tipagem, hierarquia, OCR, revisão de transcrição e reconciliação de fontes acessíveis ainda em execução.

## Execução e retomada

Com o Docker recuperado, e respeitando a guarda de capacidade e os artefatos selecionados:

```sh
npm ci
make bootstrap
make admin-create EMAIL=seu-email NAME='Seu nome' ACTOR_TYPE=human
make verify
make release-check
```

A senha é lida por stdin, sem padrão; `.env` permanece privado. O bootstrap utiliza o artefato entregue e não depende de recoletar todos os PDFs. Antes do aceite, será necessário substituir o ponteiro parcial por candidata consolidada verificada e repetir os comandos através dos wrappers de evidência.

Ordem obrigatória da validação operacional final: `qa-production.ts` → `qa-reimport.ts` → `qa-recovery.ts`, além de API/MCP, navegador integral, administração, ingestão global, performance, fontes e auditoria. Cada ensaio deve identificar código, imagem, publicação e artefatos observados. Não houve execução final desses três ensaios no estado novo.

Checkpoints: `docs/progress.md`, `docs/admin-ops-progress.md`, `docs/domain-progress.md`, relatórios regionais e `var/jobs/`. O trabalho continua; este relatório não é declaração de entrega nacional concluída.
