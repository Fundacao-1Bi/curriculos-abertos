# Relatório de entrega — integração em execução

## Atualização de estado — 2026-10-31

### Gate corrente — 2026-10-31

Gate fonte-corrente reexecutado sobre `data/bundles/latest.json`: `ca-7d302a9c674a97b83278`, SHA `be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d`, reprovado 0/27 UFs. ING-03 = 307 (256 recibos ausentes, 42 partes sem denominador, 6 V2 recusados, 3 dependências com alvo/hash inválidos); cobertura tem 3 recortes ausentes, 51 escopos sem inventário, 90 sem aprendizagem estruturada e 10 partes mapeadas não reconciliadas; J03 tem 5.609 amostras, 125 falhas literais, 90 estratos sem amostra e zero erros de âncora. AM Resolução 85/2021 foi reconciliada integralmente no nível da fonte; não há erro ING-03 próprio de AM. `docs/evidence/data-release-check.json` reflete exclusivamente o `latest.json` ativo, não um candidato privado.

#### Candidata QA AM — atualização de OCR e SourceWhole (31/10)

A Resolução CEE/AM 85/2021 recebeu inventário visual das duas páginas e transcrição corrigida ligada ao PDF, render e cache atuais. SourceWhole V2 passou 2/2 itens e 2/2 páginas, sem parte pendente; isso não declara revisão pedagógica nem vigência atual. RAW `ca-4d90ef8117cb73995b8b` foi íntegro e composto como candidato privado `ca-update-d64b2929d1b171072e807a601c8000be` / SHA `6a5efdaac1f6a4c5d09326e048c05712c5e0b740c43a9bdea36521b01f2b6592`, 303 fontes/200.724 itens/57.425 relações. A prova confirmou 302 fontes, 57.425 relações e 563 registros de cobertura fora do alvo preservados, default QA inalterado. O gate privado também fica em 0/27 e 307 erros ING-03; esse candidato de um alvo não substitui a candidata separada de 11 fontes (`ca-update-a5299305c188bec5ace5e0b4e20db16c`, gate 267 erros no relatório daquela composição) e ainda precisa ser unido numa composição atual antes de qualquer promoção. Evidências: `docs/evidence/source-audit-am-85-2021/`.

#### Candidata QA posterior — PI+AC+SP+ES, nove fontes (31/10)

O RAW `ca-9dc9353aee85ee3c6b15` (SHA `0fd09cfebed21b176c987e2bd2d2196103aaad7351e922137669fa6abd60010c`) contém nove fontes alvo correntes sobre a base publicada fixada, 17.544 itens e 2.102 relações. O bundle `data/bundles/ingestion-update-pi-sp-ac-es-nine-source-qa/snapshot.manifest.json` foi composto e importado somente no banco QA isolado. Candidato `ca-update-a69067f66c0332ca67308b0b1e7a4f2b`, SHA `e5c8dcb773ee61aa26ff7947bea3eaac4fdb41edd47f32ee603ec6b01341e4b6`, contém 303 fontes, 206.391 itens e 57.422 relações. A prova de preservação confirmou 294 fontes, 55.320 relações e 523 recortes fora do escopo; `current_publication` manteve `ca-297c7ec9ab33fcaae579` antes/depois. Gate fresco em `docs/evidence/source-audit-northeast/pi-sp-ac-es-nine-source-release-check.json`: conteúdo e integridade passam, mas o candidato ainda falha ACE-01/ACE-02 com 0/27 UFs, 271 erros ING-03, zero recortes ausentes, 51 escopos sem inventário, 89 sem aprendizagem estruturada, 17 dependências documentais projetadas a recortes sem componente e J03 com 5.649 amostras, 123 falhas literais, 90 estratos ausentes e zero erros de âncora. O gate atual de `latest.json` continua separado e sem alteração: 312 erros ING-03, 3 recortes SP–Computação ausentes e J03 5.609/125/90. O relatório padrão foi reexecutado contra `latest.json` após salvar a evidência candidata. Nenhuma promoção foi feita.

Auditoria independente read-only das 24 reconciliações locais identificou 19 recibos SourceWhole V2 atuais; todos já aparecem no resumo `source_reconciliation` da candidata e não produzem erro próprio no gate. Reempacotar recibos aprovados seria duplicação, sem redução mensurável. Os próximos possíveis alvos de correção são AC Computação e AP por dependências obrigatórias sem artefato/identidade explícitos, e MS Projeto de Vida por escopo ainda restrito a partes, runtime sem pin corrente e denominador narrativo incompleto.

A candidata anterior AC+SP+ES foi `ca-update-5441e502ccaf691cf7b472b0c0f5fa21` (206.386 itens, 303 fontes, 57.422 relações), superada pela candidata privada de nove fontes descrita acima. Seu gate e evidência permanecem históricos em `docs/evidence/source-audit-central-south/sp-ac-es-seven-source-current-receipts-release-check-20261031.json`.

Branch atual `checkpoint/2026-10-29-j11-diagnostic` (`6f93ed1`), cinco commits após `main` local (`84de9d9`). `origin/main` está em `9ffddef`, sem merge-base com o histórico local, então ahead/behind remoto é indefinido. Permanecem 246 caminhos modificados/não rastreados no worktree; todos foram preservados. Nenhum merge, push, PR, promoção ou deploy foi feito.


### Compositor de atualização v2 — 2026-10-31

A regressão em `prepareGlobalIngestionUpdate()` foi corrigida. O gate consome somente `bundle.verification.samples`; por isso o compositor agora entrega no nível superior a união por escopo: amostras da base fora do alvo e do recibo para fontes alvo. São rejeitadas amostras com identidade/escopo/página/hash/literalidade inválidos, recibos fora do alvo e duplicatas. A identidade do compositor mudou para `base-plus-source-update-v2`.

O candidato ES privado `ca-update-5377bd88acc541aeb61625cfaa0c79d4` tem 219.673 itens e 57.719 relações. A prova SQL confirmou igualdade de metadados e itens para as 302 fontes fora do alvo, igualdade JSONB estruturada, relações fora do alvo com SHA idêntico (`71889c…68fea5`) e cobertura fora do alvo com SHA idêntico (`92bc47…dc09b`). A amostragem passou de 565 para 89 estratos sem amostra; ainda há 84 falhas literais. O gate permanece reprovado em coverage, ING-03 e J03, com 1/27 UFs prontas. Candidato preparado somente, `national_release_ready=false`; QA default `ca-297c` e `latest.json` `ca-7d30` não mudaram.

Evidências específicas: `docs/evidence/diagnostic-base-20261028195651-4a29dd/es-5777-global-qa-ca297-v2-preservation.json` e `.../es-5777-global-qa-ca297-v2-release-check.json`. `npx tsc --noEmit` continua reportando três imports relativos quebrados em scripts antigos da evidência SP; os erros são nos caminhos dos scripts da pasta de evidência.

### Compositor de atualização v3 — 2026-10-31

O compositor agora também substitui `source_reconciliation` para as fontes alvo pelo relatório correspondente do RAW e conserva os relatórios da base para fontes fora do alvo. Falha fechado quando um inventário está ausente, duplicado ou não coincide com a lista de fontes. A revisão do fluxo é `base-plus-source-update-v3`. `npx tsc --noEmit` não reportou erros em `src/domain/ingestion-update.ts`; permanece falhando apenas nos três imports relativos quebrados dos scripts de evidência SP listados acima.

Uma execução isolada direta da função de domínio no PostgreSQL de QA gerou o candidato privado `ca-update-281fe684282fada5b00ff8eb183f49f7` (SHA `1af09365d55f3fbd0b50fab50db059b360aade59400aefa9ad5f974ba8a3f00c`), 303 fontes, 200.724 itens e 57.425 relações. A prova de preservação conferiu 302 fontes fora do alvo, além de hashes iguais de relações e cobertura fora do alvo. No escopo AC, a contagem segue 3.885; foram removidas duas referências espúrias das pp.1416/1444 e acrescentadas duas continuações contextuais das pp.625/830. Dos 1.692 payloads compartilhados diferentes, remover `review_events` resulta em zero diferenças curriculares/canônicas. O relatório do candidato reconcilia 3.885/3.885 itens AC e seu gate não tem mais erro ING-03 de AC; total ING-03 caiu de 309 para 307. O gate continua reprovado em 0/27 UFs e 125 falhas J03. A publicação está `prepared` no QA, o default QA ficou em `ca-297c7ec9ab33fcaae579` e `latest.json` continua `ca-7d302a9c674a97b83278`. A prova não usou o job/proveniência do worker, então não valida esse fluxo operacional. Evidências `docs/evidence/source-audit-ac/ac-global-composition-v3-qa.json`, `ac-global-composition-v3-release-check.json` e `ac-global-composition-v3-qa-verification.json`; verificador `verify_ac_global_v3_qa.py`.

Este relatório detalhado abaixo é histórico (28/10). Na revisão atual, o piloto SP está importado e aprovado em jornadas apenas no QA isolado; a migração 011 reduziu o tempo da busca `q=1.1` para 8,6 s, e os verificadores gerais API/MCP passaram nesse QA. Isso não é implantação principal nem ACE-01/ACE-02. `localhost:3000` continua servindo `ca-77fb8076598b567e1ba3`; `data/bundles/latest.json` segue no BASE `ca-7d302a9c674a97b83278`.

Em 2026-10-31, a Resolução CEE-ES 5.777/2020 teve 8 unidades documentais reconciliadas e foi empacotada no recibo incremental `ca-dd4d6ac7f763f39d62b9`, pinado à base `ca-7d302a9c674a97b83278`. O artefato passou validação estrutural e contém os 8 IDs verificados; permanece `national_release_ready=false`, não foi composto na publicação global e `latest.json` segue inalterado. O recibo é um ato de aprovação e mantém `UF_ready=false`; não representa currículo de aprendizagem nem prontidão de ES.

Relatório histórico do candidato `ca-update-5377bd88acc541aeb61625cfaa0c79d4` (base QA `ca-297c7ec9ab33fcaae579`, SHA `49216ad16734c72cc65e99b5ad1c1eaccdc43ef5c5db74c8f8cbe9d24a219981`), superado pelo gate corrente acima: naquela avaliação, ING-03 tinha 274 erros, coverage 10 partes AC EF mapeadas sem reconciliação e 51 escopos sem inventário, e J03 tinha 84 falhas literais em 6.588 amostras. O arquivo `docs/evidence/diagnostic-base-20261028195651-4a29dd/es-5777-global-qa-ca297-v2-release-check.json` documenta essa candidata histórica; não é o gate atual de `latest.json` nem da candidata `ca-update-5441...`.

Em 2026-10-31 foram atualizados, com backups preservados, os recibos DF Computação Digital II/III (1.947 registros, 0 falhas literais), SC Resolução 070 (53), Parecer 446 (5) e SC Língua Inglesa Anos Iniciais (362). Os cinco receberam pins runtime/cache/configuração/fingerprint atuais e passaram sua validação V2. As fontes e caches permaneceram inalteradas. Nenhum merge, push, PR, deploy ou troca de default/latest foi feito. A branch local de diagnóstico está cinco commits à frente da `main` local, mas os históricos local e remoto não têm ancestral comum; não há contagem remota válida de `ahead/behind`.

Em 2026-10-31, uma correção source-scoped no AC EF suprimiu dois itens `referencia_no_documento` espúrios de geometry spillover nas pp.1416/1444. O sidecar composto conserva os 2.191 registros de aprendizagem e acrescenta duas continuações literais das pp.625/830 como `secao_normativa`, sem código, ano ou tipagem de aprendizagem. Cache v1.5 foi refeita com Tesseract disponível: 1.714 páginas, OCR concluído, 1.779 itens extraídos; a composição final tem 3.885 registros e zero falhas literais. Comparação com backup: dois falsos registros removidos, dois fragmentos contextuais adicionados e nenhum payload semântico compartilhado alterado. O inventário direto do PDF confirma as 1.694 ocorrências de contexto esperadas (1.690 páginas com texto longo + quatro continuações), classifica visualmente 20 páginas sem texto curricular e deixa explícitas 16 páginas preliminares ainda sem parte atribuída. Evidências e geradores em `docs/evidence/source-audit-ac/`. AC passou o gate próprio de SourceWhole V2; recibo instalado localmente em `data/manifests/reconciliation/ac-cru-ei-ef.json` (3.885 registros, 1.714 páginas, 12 partes; zero falhas literais). O front matter pp.1–16 está agrupado sob `Texto introdutório` apenas como contexto documental geral. Edição, vigência e aplicabilidade atual seguem abertas; a SEE/AC informa atualização BNCC Computação em curso para 2026. A candidata imutável não foi recomposta/reavaliada para esta cache/recibo. Reavaliação isolada do bundle ativo: 309 erros ING-03; apenas dois itens AC novos (um em Educação Física, um em Espanhol) ainda não existem no bundle ativo. Foi criado o RAW privado `ca-ee5459db2c6e04162cac` (SHA `e9b23babd100201f710ad24c4c9b73d02b58f5c6c327921d77fcb76a18c99289`) sobre `ca-7d302a9c674a97b83278`; ele não foi composto nem anunciado, e `latest.json` segue igual. Evidência: `docs/evidence/source-audit-ac/active-bundle-after-ac-receipt-release-check.json`.

Continuidade técnica AC EF (`ac-cru-ei-ef`): as duas referências citacionais incorretas foram filtradas por página, e os fragmentos contextuais curtos das pp.625/830 foram preservados como registros documentais. O cache atual tem zero falhas literais em 3.885 registros finais. A fonte tem recibo SourceWhole V2 instalado localmente que reconcilia todas as páginas, partes e registros do PDF fixado; as pp.1–16 estão agrupadas apenas como contexto documental. Edição, vigência e aplicabilidade atual seguem sem confirmação. A candidata global é imutável e ainda não incorpora esta cache.

O caso negativo atualizado do gate de cobertura passou (`docs/evidence/data-release-negative.json`): o baseline sintético passa e a remoção de um recorte obrigatório falha com o recorte exato identificado. A auditoria das amostras em `docs/evidence/data-sample-failure-audit/` classificou as 84 falhas em cinco famílias, sem corrigir conteúdo do bundle.

Estado Git atual: branch `checkpoint/2026-10-29-j11-diagnostic` em `6f93ed1`, `main` local em `84de9d9` e `origin/main` em `9ffddef`, sem ancestral comum entre o histórico local e o remoto. Existem alterações e artefatos locais não commitados. Nenhum merge, push, PR ou deploy foi feito; preservar o trabalho antes de tratar a linhagem.

PR-EI/EF e PI Parecer ainda não são fontes reconciliadas: o primeiro tem lacunas no denominador dos itens de cache e uma falha literal em EF04MA22; o segundo é um parecer escaneado que cita anexos curriculares não verificados. Não se emitem recibos dessas fontes até fechar o escopo e o denominador primário.

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
| MS Núcleo Integrador/ementas2023 | O índice SED/MS e registro WordPress 80798 confirmam um anexo PDF anunciado de 63.530.818 bytes. REST, página do anexo, URL original e variantes de requisição retornaram HTML, sem URL alternativa. A auditoria não obteve o binário; ementa de 2022 e guia de Projeto de Vida 2024 não foram tratados como substitutos. Recuperação depende da restauração do arquivo ou indicação de espelho oficial. Evidência `docs/evidence/source-audit-central-south/ms-pv-2023-ementa-retrieval-audit-20261031.json`. |
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


Em 2026-10-31, o exemplo de habilidade fora do componente Projeto de Vida nas pp.19/23 recebeu duas regras geométricas limitadas às caixas azuis; ambas as referências foram preservadas com evidência literal. A reextração atual tem 127/127 páginas, OCR concluído, 735 itens finais (681 do adapter), zero falhas literais. Revisão visual delimitada classificou p.50 como abertura sem item curricular do organizador de EF Anos Iniciais, com p.51 como início da tabela; evidência e denominador zero em `docs/evidence/source-audit-central-south/ms-pv-page50-opening-attribution-20261031.json`. Isto não resolve a diferença entre 681 e 735 registros: os 54 registros adicionais ainda carecem denominador primário e associação exata; a narrativa/figuras p.1–49 e 126–127 não teve revisão visual integral. O infográfico raster p.30 continua sem transcrição canônica; não há SourceWhole V2. A segunda tentativa de aquisição da ementa Núcleo Integrador 2023 verificou mídia WordPress 80798, REST, página oficial do anexo, variantes do URL e `Range`, sem achar PDF binário ou outra mídia registrada: a resposta foi HTML (609.771 bytes; SHA `6f5a55d61a1821997459fd2843a6d7aaeaa25b18680d023aac30c3ea0e180e73`) apesar dos metadados declararem PDF de 63.530.818 bytes. Evidências em `docs/evidence/source-audit-central-south/`; a recuperação depende da SED/MS ou de espelho oficial e nenhum contato externo foi feito.

Verificação visual complementar das pp.38–39: o callout raster da p.38 foi transcrito em região separada, com texto e URL ausentes do cache e do registro genérico; a nota 4 da p.39 foi transcrita visualmente e confirmou corrupção de segmentação no cache. Renders 4x e transcrições com hashes/caixas: `docs/evidence/source-audit-central-south/ms2024-p38-p39/`. O ledger registra 736 unidades conhecidas sob a hipótese de um registro textual por página, com apenas uma unidade adicional comprovada na p.38; total esperado continua nulo, o denominador SourceWhole permanece aberto e o cache/registro de p.39 ainda precisa correção.

Replay isolado atualizado do bundle ativo `ca-7d302a9c674a97b83278`, depois dos recibos AC e da reextração MS: gate ainda reprovado, 309 erros ING-03; MS tem três falhas (recibo sem gate SourceWhole, pins runtime V2 ausentes e denominador pendente da parte narrativa); AC tem dois itens ainda ausentes do bundle ativo. J03 tem 125 falhas literais e coverage ainda aponta 3 recortes ausentes, 10 partes não reconciliadas, 51 escopos sem inventário e 90 sem aprendizagem estruturada. Evidência isolada: `docs/evidence/source-audit-central-south/active-bundle-after-ms-geometry-change-release-check.json`. O bundle publicado não foi alterado.

## Snapshot integrado mais recente — 2026-10-31

A composição QA de oito fontes `ca-update-990c550286307a7f20e7b2a9a9f89727` (SHA `8266fce1a4fbe6dcd25da70a457cd84d66cf4a3511277a47c093580c8118916a`) é posterior aos candidatos descritos acima e está somente preparada no banco `curriculos_qa`. Gate isolado: **FAIL, 0/27 UFs**, ING-03 = 269; restam 258 recibos de reconciliação ausentes, seis recusas SourceWhole V2, três dependências obrigatórias sem alvo/hash (AP, AC, RN) e o denominador MS. Foram resolvidos nessa composição os três recortes SP–Computação ausentes e dez partes AC mapeadas; escopos sem inventário = 51, sem aprendizagem estruturada = 89. J03 = 5.641 amostras, 123 falhas literais, 90 estratos sem amostra, zero âncoras inválidas. Evidências: `docs/evidence/source-audit-northeast/sp-ac-es-pi190-eight-current-receipts-composition-qa.json` e `sp-ac-es-pi190-eight-current-receipts-release-check-20261031.json`.

A candidata preserva os 295 sources fora do alvo; relações externas = 55.320 e cobertura = 523, com hashes pré/pós idênticos. O default QA continuou `ca-297c7ec9ab33fcaae579`; não houve alteração de `latest.json` ou promoção. O gate da publicação ativa é outro snapshot: `ca-7d302a9c674a97b83278`, 0/27 e 310 erros ING-03 após a atualização local dos pins AP/AC; os documentos-base oficiais AP e AC seguem sem alvo/hash e não são tratados como resolvidos.

Auditoria de branches sem fetch: remoto tem apenas `main` em `9ffddef0ac74666842d7a66db9cb5e4fd4756d85` (`public-main`/`origin/main`). `main` local em `84de9d9` e checkpoint `6f93ed1` não têm ancestral comum com o remoto; portanto, 3/8 commits locais alcançáveis não são contagem válida de ahead/behind. O checkpoint contém a `main` local e está 5 commits à frente/0 atrás dela. Nenhuma atualização de ref remota foi feita.

## Atualização de dez fontes — 2026-10-31

Candidata privada e não promovida `ca-update-b87d8c766eb2124135e9a008088cdb76`, manifesto SHA `ddad19382fcb18b4b215a69e843a1537a7fb8860eb5f1532a75c0d632ac0f169`, foi composta sobre a base ativa com dez alvos AC/ES/PI/SP. Resultado: 207.284 itens, 57.423 relações e 303 fontes. A prova global preservou 293 fontes externas ao alvo, 55.065 relações externas e 520 linhas de cobertura; hashes antes/depois iguais. Default QA manteve `ca-297c7ec9ab33fcaae579`; `latest.json` e `docs/evidence/data-release-check.json` continuam vinculados à base `ca-7d302a9c674a97b83278`.

O gate do candidato, calculado com o Python fixado de `var/venv-pipeline`, continua **FAIL, 0/27 UFs**, ING-03=269. Os erros restantes incluem 257 recibos ausentes, seis SourceWhole V2 recusados, três dependências sem alvo/hash, dois denominadores documentais e a verificação runtime V2 ausente para MS; cobertura tem 51 escopos sem inventário e 89 sem aprendizagem estruturada. J03: 5.701 amostras, 122 falhas literais, 90 estratos sem amostra, zero erros de âncora. A correção técnica AC reduziu uma falha literal e a cobertura continua sem recortes ausentes (0/565). A receipt ES 5.190 passa SourceWhole V2, mas a regra de evidência de parte ainda falha porque os registros não têm `section` ou `verification`; requer reemissão com novo hash antes de nova composição. AC EM ainda não tem reconciliação whole-source, pois o documento curricular obrigatório relacionado não foi obtido. Evidências: `docs/evidence/source-audit-northeast/sp-ac-es-pi190-acem-ten-current-receipts-composition-qa.json` e `sp-ac-es-pi190-acem-ten-current-receipts-release-check-20261031.json`.

Branches rechecadas via `git ls-remote` sem atualizar refs: `origin` só anuncia `main` em `9ffddef0ac74666842d7a66db9cb5e4fd4756d85`, igual a `public-main`. Branch atual `checkpoint/2026-10-29-j11-diagnostic` está em `6f93ed1`; contém a `main` local `84de9d9` e está cinco commits à frente/zero atrás dela. `main` e checkpoint não têm merge-base com o remoto, portanto as contagens reachability `3/1` e `8/1` não são ahead/behind válidos. Worktree preservada: 28 caminhos rastreados modificados e 176 não rastreados. Não houve fetch, limpeza, promoção ou deploy.

## Reemissão ES e candidata privada mais recente — 2026-10-31

Reemiti o recibo SourceWhole V2 de ES Resolução CEE nº 5.190/2018, acrescentando contexto `section` para as mesmas 13 páginas/IDs, sem mudar texto/classificação. A verificação permanece 13/13 páginas, 127 fragmentos documentais vinculados e zero problemas; novo SHA `e897a4373ae25ec7d824949f7497c7959a3190589f2ac438f70e21442421e6f5`. O RAW de dez fontes foi regenerado com esse recibo e a correção técnica AC já documentada. A candidata `ca-update-ad940b94fa9214ecf6b3d9cbc2abf46f` (SHA `df486de8d957917bb288555f917a3e2b376a7bd8f1f745e00821c83ee302be1f`) tem 207.284 itens, 57.423 relações e 303 fontes.

A prova integral de preservação passou no banco `curriculos_qa`: 293 fontes e 192.378 itens fora do alvo, 55.065 relações e 520 linhas de cobertura, hashes pré/pós iguais e igualdade JSONB canônica aprovada. O candidato foi importado sem promoção; default QA permaneceu `ca-297c7ec9ab33fcaae579`. O gate correto, executado pelo Python `var/venv-pipeline` (3.11.15, PyMuPDF 1.26.7), continua **FAIL, 0/27 UFs**, com ING-03 reduzido de 269 para 267: a reemissão ES retirou um erro e o pin runtime V2 MS revalidado retirou outro. Restam 257 recibos ausentes, seis recusas SourceWhole V2, três dependências documentais AP/AC/RN sem alvo/hash e o denominador narrativo MS. J03 = 5.701 amostras, 122 falhas literais, 90 estratos ausentes e zero erros de âncora. Coverage: 0/565 recortes ausentes, zero partes mapeadas pendentes, 51 escopos sem inventário, 89 sem aprendizagem estruturada e 17 projeções de dependência.

A verificação de igualdade canônica revelou e corrigiu um plano aninhado quadrático, causado por estatísticas antigas que estimavam o candidato em uma linha. `enable_nestloop=off` fica restrito à seção dessa transação, e o `EXPLAIN` mostrou merge join pelos índices `(publication_id,id)`. A tentativa privada anterior foi interrompida; a prova integral com a alteração passou no candidato já importado. O runtime V2 da fonte MS foi revalidado contra cache, parser, configuração, runtime, OCR, 127 páginas e adapter; o campo foi adicionado sem alterar o resultado SourceWhole nem fechar seu denominador. Evidências de composição/preservação e gate em `docs/evidence/source-audit-northeast/sp-ac-es-pi190-acem-ten-current-receipts-reissue-*`; recibos em `docs/evidence/source-audit-southeast-uncoded/complements/` e `docs/evidence/source-audit-central-south/ms-pv-runtime-pin-verification-20261031.json`. `latest.json`, publicação ativa e deploy não foram alterados.

Rechecagem de branch após a execução: `git ls-remote --heads origin` continua retornando apenas `main` em `9ffddef0ac74666842d7a66db9cb5e4fd4756d85`. A branch local está em `checkpoint/2026-10-29-j11-diagnostic` (`6f93ed1`); `main` local (`84de9d9`) e checkpoint continuam sem ancestral comum com `origin/main`, então as contagens de commits alcançáveis não são medidas válidas de ahead/behind. A árvore de trabalho foi preservada e agora tem 29 caminhos rastreados modificados e 194 não rastreados.

## Atualização privada com RJ e delta do gate — 2026-10-31

O item RJ `EM13LGG701` foi corrigido no RAW sem trocar seu ID, usando o sidecar literal existente, as supersessões de extração registradas e a validação dos 890 itens codificados. O RAW de 11 fontes `ca-fa1a7788438fd48b1234` tem 20.628 itens e 2.534 relações; a avaliação técnica confirmou 14 supersessões RJ e a correção same-ID AC.

A candidata QA `ca-update-a5299305c188bec5ace5e0b4e20db16c` (bundle SHA `e69c960d8ca1c3c19ca46c34cb98b04fa80b059e6d6ab926c7e80b821521213a`) foi importada privada com 207.416 itens, 57.439 relações e 303 fontes. Preservação QA: 292 fontes/191.343 itens fora do alvo, 54.905 relações e 515 linhas de cobertura; hashes antes/depois iguais. Default QA permaneceu `ca-297c7ec9ab33fcaae579`.

O gate não passou: **0/27 UFs**, ING-03=267. Contra a candidata de dez fontes, J03 melhorou de 122 para 91 falhas literais (−31), com amostras de 5.701 para 5.715; seguem 90 estratos sem amostra e zero erros de âncora. O erro total ING-03 não mudou: 257 reconciliações ausentes, seis SourceWhole V2 recusados, três dependências sem alvo/hash e um denominador MS. Coverage continua 0/565 recortes faltantes, zero partes mapeadas sem reconciliação, 51 escopos sem inventário, 89 sem aprendizagem estruturada e 17 projeções de dependência.

Evidências: `docs/evidence/source-audit-northeast/sp-ac-es-pi190-acem-rj-eleven-source-current-reissue-composition-qa.json` e `sp-ac-es-pi190-acem-rj-eleven-source-current-reissue-release-check-20261031.json`. A leitura paginada e a prova de preservação no banco QA levaram cerca de 54 minutos, concluindo sem divergência. `latest.json`, publicação ativa e deploy não mudaram.

Branch rechecada sem fetch: `origin` anuncia somente `main` em `9ffddef0ac74666842d7a66db9cb5e4fd4756d85`. O checkpoint local `6f93ed1` está cinco commits à frente da `main` local `84de9d9`, mas os dois não têm merge-base com `origin/main`; portanto, não cabe um ahead/behind por commits alcançáveis contra a branch remota. Worktree preservada: 29 caminhos rastreados modificados e 205 entradas não rastreadas.

Triagem complementar das 91 falhas J03 não encontrou outra correção textual de alta confiança: nenhuma pertence a RJ, AC, ES, PI 190 ou SP; permanecem distribuídas em 39 fontes fora do lote. Sidecars encontrados para SC são de hierarquia e não provam literalidade dos itens em falha. A triagem read-only das seis fontes com recusa SourceWhole também não encontrou correção de runtime pendente: AP/AC/BA/RN/MA já têm pins V2 correntes, mas faltam identidades ou hashes de documentos obrigatórios; para MS, o denominador narrativo segue aberto.

Nota para futura reemissão: o `source_reconciliation` embutido no manifesto desta candidata conserva o hash anterior do recibo MS (`c490c68a…`), enquanto o recibo corrente instalado está em `4070a4aa…`. A candidata não foi alterada após importação para preservar o hash do artefato e seu vínculo no QA. O gate lido contra as evidências atuais continua reprovando SourceWhole/denominador MS; um próximo artefato de release deve incorporar metadata reconciliado.

Distinção de ponteiro: `data/bundles/latest.json` ainda aponta para a base ativa `ca-7d302a9c674a97b83278`, enquanto `docs/evidence/data-release-check.json` está vinculado à candidata privada de 11 fontes. Esse relatório genérico não significa mudança do default QA nem publicação ativa.


## RN Trilhas — correção local de atribuição de módulo — 2026-10-31

O adaptador deixava segmentos verticais sem rótulo herdarem o escopo do traço anterior na ordenação de leitura, inclusive ao atravessar para a outra coluna. Revisão visual dos nove casos manteve oito como geometria não classificada; um caso na p.369 é redundante por estar contido em barra rotulada. O builder foi reexecutado: 3.851 nós/IDs/textos preservados; 24 registros tiveram contexto geométrico regenerado, com uma alteração efetiva de pai: `uc-p468:field:p468:c1:raw77` saiu de `uc-p468:module-printed-1` para `uc-p468`. Sidecar SHA atual `269729c19ae872c599586306f84c6f229612d427ccd387d570e580590504028c`.

O manifesto registra esse hash como revisão posterior, mas marca a validação integral do importador/parser como pendente. O recibo SourceWhole de RN não foi emitido: p.23 e p.25 ainda contêm defeitos nos contextos genéricos e o inventário das páginas iniciais 1–30 não está reconciliado. A candidata QA de 11 fontes e a publicação ativa `ca-7d302a9c674a97b83278` não incorporam esta correção; `latest.json` não mudou.

## Revalidação corrente do mapa de escopo — 2026-10-31

A evidência `release-coverage-source-part-map/1.1` separa partes normativas de fonte inteira das três projeções documentais EI/EF/EM para Computação no currículo SP. O verificador fixa cada projeção a hash, páginas, excerto e nota exatos em `stage_component_inventory_evidence`. Executado com `var/venv-pipeline` (Python 3.11.15/PyMuPDF 1.26.7), o candidato privado de 11 fontes `ca-update-a5299305c188bec5ace5e0b4e20db16c` passa a ter 0 recortes ausentes e 0 partes mapeadas sem reconciliação, mas o release permanece FAIL/0 de 27 UFs por 51 inventários incompletos, 89 escopos sem aprendizagem estruturada e 266 erros ING-03. J03: 5.715 amostras, 91 falhas literais e 90 estratos sem amostra.

A evidência canônica `docs/evidence/data-release-check.json` corresponde novamente ao `latest.json` ativo `ca-7d302a9c674a97b83278` / SHA `be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d`: FAIL/0 de 27, 3 recortes SP ausentes, 10 partes AC não reconciliadas, 51 inventários incompletos, 90 escopos sem aprendizagem e 307 erros ING-03. J03: 5.609 amostras, 125 falhas literais e 90 estratos ausentes. Candidato, `latest.json` e default QA `ca-297c7ec9ab33fcaae579` permanecem separados; não houve promoção.

## Inventário de cobertura vigente — 2026-10-31

`pipeline/build_coverage_manifest.py` atualizou `data/coverage-manifest.json` usando o `latest` ativo, o inventário atual e a evidência de escopo v1.1. O manifesto diferencia 565 recortes esperados de 564 linhas embutidas no bundle: 562 linhas alinham-se ao inventário, três recortes SP–Computação estão ausentes e duas linhas antigas sem componente são explicitadas como extras fora do inventário atual. Os recortes SP ausentes têm registros no bundle, mas não cobertura/publicação para o componente; permanecem `ready=false`. A geração não altera o artefato, `latest.json` ou default QA.

## Instalação QA e gates de produto — 2026-10-31

Uma imagem isolada de produção (`curriculos-abertos:goal-20261031`, SHA `dfc564471b9ab8dee3baf523cdd02a6cbcb19946f9e4f5d91fdbecd05de5fbd0`) foi instalada em QA limpa sem substituir o serviço local existente. A instalação diagnóstica passou com 11 migrações idempotentes, 75 shards, 200.724 itens, 57.425 relações e 303 fontes; bootstrap, admin/login, API/MCP, amostra real, reinícios e persistência passaram. O registro `docs/evidence/production-install.json` é diagnóstico (`diagnostic_only=true`), não aceite nem registro da suíte de produção.

Jornadas Playwright: 10/10 desktop e mobile. MCP HTTP/stdio passou com cliente SDK real e 10 ferramentas; smoke operacional passou health/readiness, 401 em admin/métricas anônimos e heartbeat do worker. A integração `docs/evidence/release-check.json` agora mostra 8/20 gates aprovados e 4/55 requisitos verificados (`FUN-12`, `MCP-01..03`).

API: 170 checks HTTP passaram, porém a suíte falhou na confirmação do primeiro export nacional porque seu polling termina em 120 s e o job ainda estava `running`. A consulta posterior mostrou o mesmo job `succeeded` às 21:16:00Z; o JSON produzido ocupou 1,4 GB no volume isolado. Portanto, o worker concluiu, mas o limite de tempo/perfil de exportação atual não passa a suíte. Os outros quatro exports não foram iniciados após a falha. Não houve repetição por demanda de espaço; há cerca de 15 GiB livres e arquivos QA existentes.

Backup/restore não passou: o script encerrou antes de criar recursos porque exigia 17,31 GiB livres e mediu 16,04 GiB (`docs/evidence/backup-restore.json`). Gate de dados permanece FAIL/0 de 27 UFs. `latest.json` continua em `ca-7d302a9c674a97b83278` e o default QA em `ca-297c7ec9ab33fcaae579`; nenhuma promoção ou deploy ocorreu. O aceite ACE-01/ACE-02 segue aberto.

## Auditoria integral e desempenho — 2026-10-31

A auditoria independente contra a QA passou em 128/128 verificações, cobrindo as 75 partes do artefato e comparações com API por amostragem estratificada, matrizes, detalhes, hierarquia, autenticação e rejeição de origens não confiáveis. Integridade técnica passou; a própria evidência ressalva que isso não equivale à reconciliação documental/visual nem revisão pedagógica.

O benchmark real (200 requisições, concorrência 10) teve zero erros HTTP, mas não cumpriu as metas de busca: código p95 2.683 ms (meta 500 ms) e texto p95 2.723 ms (meta 1.500 ms). ID, panorama e comparação passaram (246, 413 e 412 ms, respectivamente). Um `EXPLAIN ANALYZE` da consulta de contagem para `q=1.1` revelou 36.381 candidatos trigram com 34.946 rejeitados no recheck e 11.340 blocos de heap tocados; isso aponta seletividade baixa para termo numérico curto como hipótese parcial, sem concluir causa de todo o tempo do endpoint. Nenhuma otimização foi aplicada; guardar a semântica de código/texto exige análise antes de mudança. Detalhe: `docs/evidence/search-performance-diagnostic-20261031.md`.

`release-check.json` agora mostra 9/20 gates e 10/55 critérios verificados. O gate de dados continua 0/27 UFs; API excedeu seu limite de exportação e desempenho falhou; demais pendências operacionais continuam explícitas em `docs/verification.md`. ACE-01/ACE-02 não concluídos.


## Atualização de gates e branches — 2026-10-31

O hash atual `1adccfce223012ece60522b8a67439ef9ee03791ac1af54660064e34696f9b04` tem typecheck, build, lint e suíte completa (122/122) aprovados. O relatório integrado recalculado apresenta 5/20 gates aprovados e 0/55 critérios completos: API/MCP/browser/operations/audit têm provas com outro hash ou reprovação anterior, a busca textual p95 ficou em 2.594 ms para meta de 1.500 ms e o gate documental continua em 0/27 UFs. A busca por código BNCC agora usa `EF01CI01` como amostra contratual; `1.1` fica como diagnóstico isolado. O tuning temporário foi revertido no DB QA e a consulta alternativa mais lenta foi descartada. Mais detalhes em `docs/evidence/search-performance-diagnostic-20261031.md`.

Auditoria Git: a branch ativa `checkpoint/2026-10-29-j11-diagnostic` está 5 commits à frente de `main`; `public-main` é igual a `origin/main`. `main` tem 3 commits locais e `origin/main` tem 1 commit remoto, sem ancestral comum entre as duas histórias; counts ahead/behind convencionais não se aplicam. Worktree segue com 270 mudanças locais preservadas. Nenhum merge, push, deploy ou promoção.


## Atualização de aceite técnico — 2026-10-31 22:10 UTC

A matriz atual (`docs/evidence/release-check.json`, hash `1adccfce223012ece60522b8a67439ef9ee03791ac1af54660064e34696f9b04`) registra **10/20 gates aprovados** e **6/55 critérios integralmente verificados**: `FUN-12`, `MCP-01..03`, `ARQ-02`, `OPS-03`. Passaram sob o hash corrente typecheck, build, lint, 122 testes, MCP HTTP/stdio, navegador (10/10), instalação QA diagnóstica, backup/restore e smoke operacional. O restore verificou 3.517 arquivos de dados, o banco restaurado e 75 partes; limpou só o banco/diretório temporários e preservou o backup privado e volumes QA. QA corrente `curriculos-abertos-clean-20261031214824-a1f735` ficou parada após as provas; seus volumes foram mantidos.

Pendências de aceite: gate documental continua **0/27 UFs**; API mantém a reprovação de exportação acima do timeout, a busca textual falha (p95 2.594 ms/meta 1.500) e o gate de performance não passa. Containers, admin, admin-browser, ingestion, reimport e sources não têm execução atual; auditoria integral é de hash anterior. As jornadas nacionais de navegador passaram, mas cada percurso das 27 UFs levou 2,2–2,4 minutos em desktop/mobile, reforçando a pendência de latência. `latest.json` (`ca-7d302a9c674a97b83278`) e os bancos principais não foram alterados. Sem promoção, deploy, merge ou push.


Contagem ao fechar esta etapa: `git status --short` lista 271 entradas modificadas/não rastreadas, incluindo os relatórios e provas QA recém-gerados; todas foram preservadas.


## Estado integrado — 2026-10-31 23:25 UTC

Hash de código `dcd608a432ac8be0dee87e3a77629b0186e6125acf5cbd198834c46d388f68a8`; matriz gerada às 23:23 UTC: **15/20 gates** e **27/55 requisitos** verificados. A API exportou JSON/CSV nacionais íntegros, e typecheck, build, lint, 122 testes, MCP, navegador, recovery, operações, admin, admin-browser e auditoria passaram. O gate técnico de ingestion continua marcado como falho porque o harness esperava uma etapa de pausa que o worker não publica; entretanto, o job real em QA concluiu a composição do candidato privado e seu recibo verificou a preservação integral das 302 fontes não alvo, relações e cobertura. O candidato está preparado, sem publicação e sem alteração do default. Detalhes: `docs/evidence/ingestion-direct-outcome-20261031.json`.

O release **não está aprovado**: cobertura documental 0/27 UFs, ING-03 com 307 erros, busca textual p95 1.645 ms/meta 1.500 ms, reimport interrompido pelo limite de 600 s e monitor de fontes pausado após 57/303. Os artefatos parciais de reimport e o QA volume foram preservados. Não houve merge, push, deploy ou promoção.

Git: checkpoint 5 commits à frente e 0 atrás de `main`; `public-main` = `origin/main`. `main` (3 commits) e `origin/main` (1 commit) não têm ancestral comum. Há três branches locais, um worktree e 288 entradas de worktree modificadas/não rastreadas preservadas; `git diff --check` passa.


## Estado integrado após auditoria e build de containers — 2026-10-31 22:17 UTC

A matriz corrente (`docs/evidence/release-check.json`) está vinculada ao hash `1adccfce223012ece60522b8a67439ef9ee03791ac1af54660064e34696f9b04`: **12/20 gates passaram e 13/55 critérios estão verificados** (`ESC-04`, `ORQ-01/02`, `FUN-12`, `MCP-01/02/03`, `ARQ-01/02`, `OPS-03`, `QA-05`, `ACE-03/04`). Passaram containers, tipos, build, lint, testes, MCP HTTP/stdio, navegador 10/10, instalação QA diagnóstica, backup/restore, smoke operacional e auditoria 128/128. Restore validou 3.517 arquivos e todas as 75 partes; o backup `var/backups/20261031T215349Z-DBrZqv` e volumes QA foram preservados. A QA limpa foi parada depois das provas.

O lançamento segue **não aprovado**: dados 0/27 UFs; API falha no timeout do export; performance falha porque busca textual p95=2.594 ms supera meta 1.500 ms. Admin, admin-browser, ingestion, reimport e sources não têm prova atual. A busca nacional no E2E levou 2,2–2,4 min por execução nas 27 UFs. `latest.json` continua em `ca-7d302a9c674a97b83278` / SHA `be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d`; ponteiro de banco principal/QA não foi promovido. Sem commit, merge, push ou deploy.

Git permanece: checkpoint 5 commits à frente do `main` local; `public-main` igual ao único remoto `origin/main`; `main` contém 3 commits locais e o remoto 1 commit, em históricos sem ancestral comum. `git status --short` lista 271 entradas locais preservadas; `git diff --check` passa. Há 48 GiB livres após a construção; não foi feita limpeza/prune global.


## Correção do registro de QA e cache PE — 2026-10-31 23:34 UTC

A base QA do job era isolada, mas o Compose montava `./data` do workspace com escrita. O worker QA (Python 3.11.2) sobrescreveu o cache `data/extracted/1b7b6c325b74b580697325f1c7af59780799fbdb9582fe98a0dab63a9203a832-page-cell-v1.5.0.json`: o hash esperado pelo recibo era `ac299e3e…`, e o arquivo atual ficou `05ae8002…`. A evidência direta foi corrigida para não chamar o filesystem inteiro de isolado. O gate ING-03 corrente registra **308 erros**; o novo erro é a divergência deste cache/runtime.

Foi preservada em `var/qa-cache-rebuild-20261031/` uma reconstrução de trabalho com Python 3.11.15 e a configuração de extração atual: SHA `fdc5802d2890ecd1124ad84eb8873309452573e38ec19c9eaec82648de627a49`, 8 itens em 8 páginas. Comparada semanticamente à cópia diagnóstica disponível, IDs, páginas e textos coincidem após normalizar timestamps/runtime/configuração. Ela **não** restaura o hash original nem substitui um recibo: não foi instalada em `data/extracted`, nem alterou recibo, manifesto ou publicação. É necessária nova prova formal de extração/recibo e candidato imutável. Detalhes em `docs/evidence/pe-cache-rebuild-candidate-20261031.json`.

A medição adicional do plano exato de busca `matemática` + EF confirmou 1.200 IDs nos dois desenhos avaliados. A consulta `UNION` existente ficou em 408–411 ms aquecida, com cerca de 63,7 mil buffers hit e 24,1 mil lidos; uma alternativa com `OR` custou 3.414–3.452 ms, cerca de 187,7 mil hits e 78,3 mil leituras. A alternativa `OR` foi descartada. Ramo trigram de texto normalizado dominou o plano (283 ms; 30.467 hits/12.298 leituras); trigram de texto PDF unido levou 165 ms (16.310 hits/3.279 leituras). Isso orienta investigação adicional, mas não prova sozinho o p95 sob concorrência. Nenhuma alteração de busca foi feita.

A matriz de release precisa ser lida com o gate documental atualizado para 308, e a QA não deve voltar a montar `./data` com escrita para extrações.

Verificação final às 23:35 UTC: a árvore de código segue `dcd608a432ac8be0dee87e3a77629b0186e6125acf5cbd198834c46d388f68a8`; a matriz regenerada continua em 15/20 gates e 27/55 requisitos. A árvore local registra 289 caminhos modificados/não rastreados e `git diff --check` passa. A branch ativa continua 5 commits acima de `main` local; `origin` anuncia apenas `main` em `9ffddef0ac74666842d7a66db9cb5e4fd4756d85`, sem ancestral comum com esta branch. Três heads locais, um worktree.


## PE: reconstrução formal do receipt em scratch — 2026-10-31 23:39 UTC

A extração foi refeita num root scratch com `var/venv-pipeline` (CPython 3.11.15, PyMuPDF 1.26.7), cópias dos módulos/fonte/adapter/schema/recibo e sem escrita em `data/` ativo. Cache SHA `cf66adc484e9f3865ba967d0e943e1f20d87882f74aa80d02068eec998885ba4`, configuração `717d5a6d…`, fingerprint `a2188a0e…`. O replay real genérico + adaptador/finalizer confirmou os 93 IDs do inventário independente, 94 fragmentos literais no PDF, schema para todos os registros, 90 relações parentais sem órfãos, 8 páginas sem OCR pendente e gate V2 whole-source sem issues. Seis probes negativos foram rejeitados.

O recibo candidato tem SHA `13f9ac118cf1d61bc8cdf7fe876169295d1d11bf1f77b310d3ede3bcea4c28b0`. A prova completa e o recibo estão em `docs/evidence/pe-runtime-refresh-candidate-20261031.json` e `docs/evidence/source-audit-northeast/pe-runtime-refresh-candidate/`. **Ainda não instalei cache/recibo no workspace ativo**: o par está associado a um hash de árvore que inclui `data/manifests`, e integrá-lo muda esse hash e exige renovar as evidências dependentes. A release-check ativa segue 308 erros e 0/27 UFs; o candidato não reduz o gate corrente até instalação controlada e revalidação. Nenhuma publicação foi alterada.

## Revalidação — 2026-10-31 23:49 UTC

Instalado e registrado o par de cache e recibo PE, sem alterar `latest.json`; cache SHA `cf66adc484e9f3865ba967d0e943e1f20d87882f74aa80d02068eec998885ba4`, recibo SHA `13f9ac118cf1d61bc8cdf7fe876169295d1d11bf1f77b310d3ede3bcea4c28b0`. Ajustado o harness de ingestion para registrar a asserção de pausa que a matriz requer. Ambos exigem prova runtime atual ainda não executada.

No hash `0a75b73e4868b1eacb6e8a10369b44591e835769ba8099806149182c98ef7e9f`, typecheck, lint e build passaram. `npm test` não alcançou os testes: faltava `TEST_DATABASE_ADMIN_URL` e Docker respondeu HTTP 500 em `/_ping`; `docker info` também excedeu 15 s. Build de containers anterior encerrou com RPC/EOF, sob hash precedente. Sem reiniciar Docker Desktop, pois há serviços locais ativos. A matriz atual tem 4/20 gates e 0/55 requisitos aprovados; dados nacionais 0/27 UFs, 307 falhas documentais. Lançamento não aprovado, sem promoção.

## Pré-filtro de busca e infraestrutura de testes — 2026-10-31 23:55 UTC

Busca por etapa agora usa contenção JSONB indexável antes do `EXISTS` exato, apenas quando posições desconhecidas não são incluídas. O GIN de `positions` existe. Typecheck, lint, build e contrato SQL focado passaram; neste último, 3 testes PostgreSQL foram pulados. Falta executar comparação completa de IDs e benchmark 200 requisições/concorrrência 10 contra publicação atual.

A suíte completa corrente falhou antes de iniciar porque o Docker Engine está encerrado: o log da VM confirma panic fatal em `HistoryQueue.Listen` / `filterHistoryEvents` do BuildKit e `reboot: Power down`; o backend falha ao alcançar `192.168.65.7:2376`. Matriz `cbc8e5c4…`: 4/20 gates, 0/55 requisitos; dados 0/27 UFs e 307 erros. Docker não foi reiniciado nem novo container build iniciado. `latest.json` permanece intacto. Um recibo whole-source de ES cobre 8 unidades, mas a incorporação à publicação ativa ainda não foi comprovada.

## Recibo ES preparado contra base fixada — 2026-10-31 23:59 UTC

Gerado sem Docker um `source_update_receipt` isolado para a Resolução CEE-ES nº 5.777/2020, fixado ao bundle `ca-7d302a9c674a97b83278` e SHA `be442730…`. O artefato `ca-dd4d6ac7f763f39d62b9` (`6ecd396f…`) passou validação independente de integridade; contém os oito IDs/textos exatamente como o recibo whole-source verificado e preserva os 4.555 itens nacionais de contexto. A evidência registra `national_release_ready=false`; nada foi mesclado, importado ou publicado, e `latest.json` permaneceu inalterado. Esse recibo aumenta a prontidão para a etapa de importação; não muda o resultado nacional 0/27 UFs, 307 erros.

## Revalidação do filtro de etapa — 2026-11-01 00:05 UTC

O teste de integração de busca agora fixa a igualdade dos IDs e o fallback de posições desconhecidas para quando o PostgreSQL voltar. Contrato SQL focal passou; 4 verificações PostgreSQL ficaram puladas. Typecheck, lint e build passaram no hash `7a72ab90…`; `npm test` falha antes do banco por daemon Docker indisponível. `docker desktop restart --timeout 120` não conseguiu encerrar os processos do Desktop, e não houve kill forçado. Matriz: 4/20 gates, 0/55 requisitos; nacional 0/27 UFs e 307 erros. Sem nova publicação; o candidato ES permanece receipt privado.

## Estado corrente — 2026-11-01 01:08 UTC

Matriz/hash: `59a6f71ac74a249546c0de2bec36153bb2266c2c465f8c8a166e82d2643c2c8e`, 7/20 gates, 0/55 requisitos. Passam negative, containers, types, build, lint, tests e ingestion; a API, MCP, browser/admin e auditoria ainda têm evidência vinculada ao hash anterior. Performance tem 0 erros HTTP, mas o p95 end-to-end de ID foi 540 ms frente à meta de 500; busca por estágio passou com 1.346 ms frente à meta de 1.500.

O gate de ingestão real passou no QA isolado, com restart/resume idempotente, comparação SQL de preservação e rollback final. O bundle/default ativo não mudou. `npm test`: 123/123, sem skips. Docker Desktop 4.97.0 / Engine 29.9.2; build de imagens passou.

**Não aprovado para lançamento:** dados em 0/27 UFs, 307 erros ING-03 e lacunas de cobertura/reconciliação. O bundle ativo é `ca-7d302a9c674a97b83278`; candidatos privados ES/SP permanecem sem promoção. Branch ativa está 5 commits à frente de `main` local; remoto só tem `main`, sem ancestral comum com o `main` local. 299 caminhos locais permanecem preservados. Sem merge, push ou deploy.


## Continuação — 2026-11-01 01:31 UTC

**Estado não pronto para lançamento.** A matriz no hash ade55087b3dce259e1b5fdb2257cbb7f6330ed5ee6970a704a674b710d8ed412 verifica 3/20 gates e 0/55 requisitos. O gate de dados ainda reprova com 0/27 UFs e 307 erros ING-03. O candidato privado de 11 fontes não foi promovido.

API, MCP (HTTP e stdio), browser (10/10), operations e audit passaram no QA antes da correção de src/domain/revisions.ts; essa evidência agora é stale por hash. Typecheck, lint e suíte completa (123/123, 0 skips) passaram depois da correção. A reconstrução da imagem QA não chegou ao runtime: Docker BuildKit retornou erro de filesystem somente leitura, Docker Desktop está stopping, Docker API responde 500 e o disco host tem menos de 1 GiB livre. Assim, o fix de timeout ainda não tem prova no runtime, gates atuais do hash nem confirmação administrativa.

O ambiente ativo e os demais serviços não foram reiniciados. Nenhuma publicação, merge, push ou deploy foi realizado.


## Empacotamento reversível e ambiente Docker — 2026-11-01 01:34 UTC

Para restaurar espaço após a falha EROFS, os dois exports completos do último gate API foram compactados com gzip e verificados por descompressão/hash. O relatório preserva SHA e bytes originais, agora registra também caminho, tamanho/hash compactado e o manifest `docs/evidence/api-download-compression-20261101.json`. Foram recuperados 2,44 GB; restam cerca de 3,9 GiB livres. Docker Desktop está parado e a chamada `docker info` informa que não consegue iniciar. Não invoquei restart/start, pois isso reativaria serviços Docker compartilhados de outros projetos. A matriz corrente permanece 3/20 gates, 0/55 requisitos; sem promoção ou deploy.


## Estado revalidado — 2026-11-01 01:37 UTC

O host recuperou espaço (5,8 GiB disponíveis), mas Docker Desktop segue `stopped` e o daemon não inicia; o BuildKit havia encerrado após panic fatal. O patch `src/domain/revisions.ts` passou typecheck, lint e suíte no hash corrente, mas a imagem atualizada e a prova de execução administrativa ainda não foram validadas. A pergunta de coordenação para reiniciar o Desktop está pendente.

A release-check do hash corrente continua em 3/20 gates e 0/55 requisitos. Dados permanecem 0/27 UFs e 307 erros ING-03. A árvore possui 303 caminhos alterados/não rastreados preservados; branch local está +5/0 frente a `main`, enquanto `origin/main` é uma história sem ancestral comum (1 commit exclusivo remoto e 8 exclusivos na linha atual), e continua sendo a única branch remota.


## Correção de concorrência em revisão relacional — 2026-11-01 01:42 UTC

Movi o lock global da preparação de revisão para antes do `BEGIN REPEATABLE READ`, para que uma chamada em espera só crie seu snapshot após adquirir o lock. O lock é de sessão, limitado a 120 s, restaurando o timeout anterior e liberando/destruindo a conexão com segurança no cleanup. Adicionei uma regressão de duas preparações idênticas atrás de um lock de teste. Typecheck e lint passaram; os testes de banco não foram executados porque o Docker permanece parado.

Hash de código `f8e19a6905b206724dd5c15f3b746bdcabf5a94927c62f4f718ebb2a5f2b047f`; matriz recém-gerada: 3/20 gates e 0/55 requisitos. Passam `negative`, `types`, `lint`. Os 17 demais gates, incluindo dados, runtime, admin, performance e auditoria, permanecem falhos ou stale.


## Build e suíte integral no hash atual — 2026-11-01 01:50 UTC

Hash `d34a924c456d436c2c731749811ea8aacc7d72ea48241c4ee4bb357dc2ac4435`: typecheck, lint e build Next passam; a suíte passou 124/124, 0 falhas/0 skips no PostgreSQL 15.15 local com `C.UTF-8`. `scripts/test-all.ts` agora registra versão e locale efetivos no log de testes. A regressão de concorrência de preparação relacional passou. Esta execução não prova compatibilidade com o Postgres 17.11 pinado no Compose.

Matriz atual: 5/20 gates e 0/55 requisitos. Permanecem os bloqueios nacionais (0/27 UFs, 307 ING-03) e os gates de runtime/API/MCP/browser/admin/recovery/operations/performance/containers stale ou ainda não executados. Docker Desktop está parado e o APFS tem só 7,1 GiB disponíveis; o preflight de full import/runtime exige cerca de 14,3 GiB, por isso o fluxo não foi contornado com carga parcial.
## Revalidação após o fingerprint do log — 2026-11-01 01:58 UTC

Fingerprint corrente: `b359a7fbe9b1a695d5caa2d5f0055c43252cdc1ad4e9c1184c18eeac6151f7ed`. A suíte completa é 124/124, zero falhas/zero skips, em Node 22.23.2 e PostgreSQL temporário 15.15 com `C.UTF-8`; typecheck, lint e build Next também passaram nesse hash. A execução não valida o runtime com PostgreSQL 17.11 do Compose.

A matriz corrente registra 5/20 gates e 0/55 requisitos verificados. Dados: publicação ativa `ca-7d302a9c674a97b83278`, 0/27 UFs prontas e 307 falhas ING-03. O candidato parcial ES prova identidade para oito itens e limpa o alvo ES, mas o recibo global segue falho (361 ING-03); a publicação ativa não mudou. Worktree: 305 caminhos modificados/não rastreados; `git diff --check` passou.

Ambiente: Docker Desktop não inicia; há 6,4 GiB livres no volume APFS (99% ocupado), ante guard de ~14,3 GiB para importação/gates runtime. A linha local está cinco commits à frente de `main`; remoto observado: uma branch `main`. Não há ancestral comum entre a linha ativa e `origin/main` (1 commit exclusivo remoto, 8 exclusivos ativos), portanto isso não é uma promoção convencional por fast-forward. Nenhum push, merge, deploy, reinício de Docker ou promoção foi feito.
## Refresh documental PE; Docker autorizado não subiu — 2026-11-01 02:05 UTC

O usuário autorizou reiniciar Docker Desktop. `open -a Docker` foi executado, mas o daemon não iniciou; o log reporta falta de espaço ao escrever `Data/log/vm/init.log`. APFS mostra cerca de 4,9 GiB disponíveis e 99% de uso. Nenhum volume foi removido nem houve limpeza destrutiva.

O cache/recibo PE foi gerado e verificado em scratch: fonte, manifesto, sidecar, parser e configuração fixados; 93/93 registros conciliados, V2 integral aprovado e seis probes negativos rejeitados. O ativo PE já passava nesse gate e o release check com CPython 3.11.15/PyMuPDF 1.26.7/Pillow 13.0.0 não reduziu os 307 ING-03 nem elevou as UFs prontas (0/27). Restaurei o cache e recibo ativos aos hashes anteriores, mantendo a prova como candidato isolado em `docs/evidence/source-audit-northeast/pe-current-runtime-refresh-20261101/`; `latest` não mudou. Fingerprint restaurado `b359a7f…`, matriz 5/20 e requisitos 0/55.
## Aquisição documental AP/AC e auditoria limitada TO — 2026-11-01 02:14 UTC

O snapshot oficial segue em `ca-7d302a9c674a97b83278`; matriz 5/20, requisitos 0/55, cobertura 0/27 UFs e 307 ING-03. A branch ativa está cinco commits à frente do `main` local; `origin` anuncia só `main`, com 1 commit remoto exclusivo e 8 na linha ativa, sem ancestral comum.

AP: os Diários Oficiais 8.564 e 8.571 foram verificados por página/hash. A Resolução 133/2025 homologa o Referencial de Educação Digital; a Resolução 001/2026 aprova o Plano da SEED. Nenhum desses atos inclui o documento integral correspondente. AC: o DOE 14.191 e cadernos A/B foram verificados; o ato 667/2025 está nas páginas 39–40, mas o CEDMAC não está anexado. Dependências permanecem pendentes, sem alteração de pins.

TO: os 65 erros são recibos ausentes, não cache vencido. Prova independente nova para `to-dct-ei` confirma 359/359 vínculos e cinco probes negativos, mas está explicitamente limitada ao conteúdo enumerado e citado, sem SourceWhole/UF-ready. Inventário detalhado em `docs/evidence/source-audit-to/`; o inventário das páginas EI restantes está em andamento. Não houve importação ou promoção.

## Continuação TO-EI e recuperação do Docker — 2026-11-01 02:39 UTC

Docker Desktop reiniciado a pedido do usuário: `running`, daemon 29.9.2, 19 containers; volume com 25 GiB disponíveis (95% usado). O cache de extração TO-EI foi atualizado com OCR concluído (110 páginas; aviso de orientação/transcrição ainda pendente na p.1).

Recibo candidato WholeSource V2 de TO-EI validado: 459 itens/459, 500 fragmentos, oito partes, 18 unidades, nenhum erro literal/schema/pai e seis probes negativos rejeitados. SHA `ddbc706a…`; permanece não instalado. O manifesto norte agora divide corretamente o documento em oito partes; o mapa adiciona cinco associações de escopo ao Capítulo V, todas campo-específicas. Revisão independente confirmou os 93 códigos e limites, e o loader do mapa passa sem erros.

A publicação ativa `ca-7d302a9c674a97b83278` (`be442730…`) permanece imutável e desatualizada em relação à declaração atual de TO: o bundle ainda guarda a parte genérica e suas cinco linhas de cobertura. Release-check documental corrente: 307 ING-03, 0/27 UFs; o mapa é válido, mas cobertura reporta 5 partes inventariadas ausentes, 15 associações não reconciliadas, 6 partes antigas não declaradas e 3 recortes ausentes. Relatório completo fixado em `docs/evidence/source-audit-to/release-check-20261101-after-scope-map.json` (`bb71474d…`). Sem promoção.

Incidente de emissão: a primeira execução passou o receipt para o helper sem `install=False`, cujo default instalou o arquivo em rota ativa. Verifiquei igualdade por SHA, preservei a cópia em `/tmp`, removi o receipt e alterei o gerador para passar `install=False` e afirmar que não houve instalação; a última geração confirmou rota ativa ausente. `latest.json` permaneceu inalterado. Sem commit, merge, push ou deploy.

A Resolução CEE/TO 024/2019 documenta a aprovação original; Nota Técnica 001/2024 informa prazo de revisão vencido e revisão pendente. A aplicabilidade presente continua não verificada. Branch ativa +5 sobre `main` local; `origin/main` tem 1 commit exclusivo remoto e 8 exclusivos ativos, sem merge-base. Worktree preservada, 317 caminhos modificados/não rastreados, `git diff --check` aprovado.

## Correção de projeção TO-EI e avaliação isolada — 2026-11-01 03:29 UTC

Docker Desktop foi reiniciado e o daemon responde em 29.9.2; 17 containers estão ativos. A stack QA isolada `curriculos-abertos-clean-toei-20261101` mantém app, worker e PostgreSQL saudáveis; há 36 GiB livres. Nenhum volume foi podado ou removido.

Corrigi `coverage_for()` em `pipeline/ingest.py` para projetar somente as associações explícitas e validadas do mapa de partes para etapa/componente, validando o mapa contra o inventário completo mesmo na ingestão incremental. O comentário obsoleto em `pipeline/release_check.py` foi atualizado. A imagem QA v2 e a ingestão final candidata já haviam sido executadas; o candidato permanece privado/prepared e `latest`/publicação ativa não mudaram.

A emissão final tem 459/459 itens, oito partes de fonte e cinco linhas de cobertura TO-EI com uma associação explícita cada. As cinco linhas permanecem `ready=false` e `reconciled=false`, aguardando reconciliação documental. Ao reavaliar a cópia QA, alinhei o cache no clone com o hash registrado, preservando os bytes substituídos em `/tmp/curriculo-toei-cache-before-sync-20261101`. O gate ainda falha: no relatório de avaliação host, a configuração de extração do cache diverge do runtime atual; as oito partes também falham no denominador documentado, incluindo 392 evidências para 414 itens do Capítulo V. O worker QA não contém PyMuPDF, portanto a avaliação de runtime dentro desse container não é prova de aprovação. Não alterei recibos para contornar esses bloqueios.

Relatório candidato (não é o gate ativo): `docs/evidence/source-audit-to/to-dct-ei-candidate-release-check-20261101.json`, SHA `4e1d6f231d0a5d0aa487fefcc99914970b492173614469be7ed18d6b88cd95e4`. Gate geral permanece reprovado, 0/27 UFs prontas; não houve importação/promoção, merge, push ou deploy. Branch `checkpoint/2026-10-29-j11-diagnostic`, HEAD `6f93ed1`; 5 commits à frente do `main` local. `origin` anuncia apenas `main` (`9ffddef…`), sem ancestral comum com a branch ativa. Worktree preservada, 319 caminhos modificados/não rastreados.

## Retomada após reinício do Docker e atualização do gate — 2026-11-01 03:54 UTC

Docker Desktop voltou ao estado `running` após a segunda inicialização: engine 29.9.2, 22 containers conhecidos e 17 em execução. A primeira tentativa levantou o VM por alguns segundos e terminou com `the Docker Desktop VM stopped unexpectedly: the virtualization process exited without being asked to`; a segunda relançou o engine. Nenhum volume foi removido ou podado.

Foram atualizados, somente no working tree, 13 caches e recibos após comparar payload semântico (ignorando timestamps de evento de revisão), texto de páginas e gate `own_source_reconciled`. Relatório: `docs/evidence/source-audit-to/active-runtime-cache-refresh-20261101.json` (SHA `9c59e03a20a7b29884200f35fe4ac616c9a66afc33863ddfd3a676a95cdb6b95`). O gate ativo em `docs/evidence/data-release-check.json` (SHA `5ad3e0bf52d1f73975e891772846723c07691b1f0ad01ab1a5d000e9182f6e29`) caiu de 334 para 321 erros ING-03, mas continua reprovado, 0/27 UFs: 256 recibos ausentes, 42 denominadores de partes, 14 caches/runtime desatualizados, 6 gates SourceWhole V2 e 3 dependências alvo/hash. Persistem 3 recortes SP Computação ausentes, 2.509 obrigações de fontes sem mapeamento, 90 escopos sem aprendizagem estruturada e 51 sem inventário.

A avaliação isolada do bundle candidato completo tem 319 erros ING-03 e zero erro TO-EI específico; continua não promovida. A cache TO-EI foi recomposta no clone QA sob o runtime Docker correto e o recibo cobre 459/459 itens em oito partes, com evidências estruturais válidas; a projeção atual contém cinco linhas de cobertura explicitamente mapeadas, ainda não reconciliadas e `ready=false`. Evidência: `docs/evidence/source-audit-to/to-dct-ei-candidate-release-check-20261101.json` (SHA `dfb28749e006fd2c8d9f3dcf2479886e8da3b2279bc80d5e15e3425ceabd53dc`).

Correção do diagnóstico anterior: PyMuPDF está presente em `/opt/venv/bin/python` na imagem worker; o comando com `sh -lc` usou `/usr/bin/python3`, que não o tem. A proporção 392 evidências/414 IDs não era, por si só, a condição reprovada; o gate verifica a estrutura mínima da evidência, atendida agora nas oito partes. Não afirmar que a reconciliação documental TO está concluída.

`data/bundles/latest.json` permanece em `ca-7d302a9c674a97b83278` (SHA `dfc9e7b208d2dc0a814d3484900baf6b3f7937ffe514539c9370fb52be1881bd`). Branch `checkpoint/2026-10-29-j11-diagnostic`, HEAD `6f93ed1`, +5 commits sobre `main` local; `origin` só anuncia `main` e não há merge-base com a branch ativa. Sem promoção, merge, push, PR ou deploy; alterações locais preservadas.


## Recibo TO-EI aplicado localmente e gate atualizado — 2026-11-01 04:09 UTC

Instalei `data/manifests/reconciliation/to-dct-ei.json` a partir do candidato host-runtime verificado (SHA `19a3ce06dc99b4f39c1ebe0594284603c4fa9fc69db251473120f2ed3f684d68`). O V2 contabiliza 459/459 itens em 8 partes, sem issues ou falhas literais; o cache fixado (`320685b9…`) corresponde ao runtime/configuração atuais. Reavaliei o bundle ativo pelo `release_check.evaluate`: ING-03 caiu de 321 para 320, os erros TO-EI passaram a zero e a falta de recibos caiu de 256 para 255. A publicação permanece `ca-7d302a9c674a97b83278` / `be442730…`, `latest.json` não mudou, e ACE-01 segue 0/27 UFs.
Branch revalidada: `checkpoint/2026-10-29-j11-diagnostic` em `6f93ed1`, cinco commits à frente da `main` local (`84de9d9`); `origin` anuncia somente `main` (`9ffddef`) e não há ancestral comum. Há 334 caminhos alterados/não rastreados preservados.

Evidência antes/depois e hash-pins: `docs/evidence/source-audit-to/whole-source-candidate-host-runtime-20261101/receipt-installation-report.json`, `data-release-check-before-toei-install.json` e `data-release-check-after-toei-install.json`. As lacunas de cobertura não mudaram: 3 recortes SP Computação ausentes, 5 partes sem inventário, 15 não reconciliadas, 51 escopos sem inventário, 90 sem aprendizagem estruturada e 2.509 obrigações fonte-level sem mapeamento. Este recibo prova reconciliação documental da fonte TO-EI, não aplicabilidade vigente, prontidão da UF ou prontidão nacional. A cópia anterior do relatório de gate foi preservada; nenhum bundle foi promovido.


## Vínculo do recibo ao bundle reforçado — 2026-11-01 04:20 UTC

Corrigi `pipeline/release_check.py` para comparar os hashes textuais dos `item_checks` com cada item efetivamente publicado, exigir cobertura integral dos itens pelas unidades documentais e validar o hash do escopo/partes e os contadores V2 contra o bundle. O valor `v2_gate_result` persistido, sozinho, não prova que o recibo descreve o texto atualmente publicado. Dez testes unitários focados passaram; `git diff --check` também passou.

Reavaliei a publicação ativa com a nova regra: `docs/evidence/data-release-check.json` SHA `8c72202549e6ef59e29926db7f7c5c2da2fd7673f625e68ed7585e4a95daa93e`, `ca-7d302a9c674a97b83278` / `be442730…`, **330 erros ING-03**, 0/27 UFs. O aumento sobre 320 decorre de 10 vínculos de recibos que o gate anterior não conferia, nos fontes SP/ES/MS/AC/AM/PI; o recibo TO-EI permanece sem erros e reduz uma ausência de recibo (256→255). `latest.json` permanece SHA `dfc9e7b…`. Relatório completo e resumo em `docs/evidence/source-audit-am-aprovacao-20261101/`.

Ao tentar atualizar o cache AM no clone COW, a extração OCR em português reproduziu os itens e textos de página, mas a reavaliação SourceWhole encontrou checks textuais diferentes dos dois registros do bundle. A tentativa foi descartada; hashes ativos do cache/recibo permaneceram iguais aos preimages. Ver `am-cache-refresh-rejected-by-sourcewhole.json`. Não há promoção: a prontidão nacional continua reprovada.

## Matriz de aceite revalidada no checkout atual — 2026-11-01 04:28 UTC

Revalidei branch e worktree: `checkpoint/2026-10-29-j11-diagnostic` em `6f93ed1`, 5 commits exclusivos frente à `main` local (`84de9d9`), sem ancestral comum com `origin/main` (`9ffddef`). O servidor anuncia apenas `main`; há 336 caminhos modificados/não rastreados preservados. Docker Desktop voltou a `running` (29.9.2); os 17 containers estão ativos e saudáveis.

Rodei `npx tsx scripts/release-check.ts --output docs/evidence/release-check-current-20261101.json`. A matriz [verification.md](../verification.md) agora aponta para o hash atual `8e8bab81279c77230bacd6cc923bef262ebedb78ebfdae626d54847ddea1233f`; ainda são **0/55 requisitos verificados**. Refiz `typecheck`, `lint` e `build` nesse hash e os três passaram; os demais gates seguem sem evidência compatível ou reprovados. O self-test documental positivo/negativo passou. A publicação continua reprovada em **0/27 UFs**, com 330 ING-03. O gate ativo foi regravado no mesmo conteúdo semântico (novo SHA `b39a65e0…`); a cópia prévia está em `docs/evidence/source-audit-am-aprovacao-20261101/data-release-check-current-binding-final.json` (SHA `8c722025…`). `latest.json` manteve o SHA `dfc9e7b…`.

Também avaliei isoladamente, sem importar/promover, o candidato AM `ca-update-d64b2929d1b171072e807a601c8000be` (SHA `6a5efdaa…`). O gate atual dá 329 ING-03, 0/27, e mantém AM bloqueado por cache/runtime stale; 9 outros bindings seguem inválidos. Relatório: `docs/evidence/source-audit-am-85-2021/am85-qa-release-check-current-20261101.json`. As transcrições corrigidas eliminam os 4 erros de vínculo textual AM, mas não substituem runtime atual nem reconciliação completa. Nenhum bundle/default foi promovido.

Próximo trabalho: gerar evidências atuais por gate (e corrigir funcionalidades/performance quando as medições reproduzirem falhas), enquanto os bloqueios nacionais continuam exigindo fontes oficiais integrais e reconciliação documental. Não reemitir recibos apenas para alinhar hashes.

A reavaliação atual do candidato privado de dez fontes SP/AC/ES/PI confirmou 281 erros ING-03 (vs. 330 no ativo), 0/27 UFs e zero recortes ausentes; ainda há 5 partes sem inventário, 5 não reconciliadas, 5 partes não declaradas, 51 escopos sem inventário, 14 caches stale, 255 recibos ausentes e outras falhas. A prova anterior indicava 280, mas foi superada pela regra atual de vínculos. Evidência atual: `docs/evidence/source-audit-northeast/sp-ac-es-pi190-acem-ten-current-receipts-reissue-release-check-current-binding-20261101.json`.

## Overlay de recibos para candidato QA e aceitação técnica atual — 2026-11-01 04:47 UTC

Adicionei a avaliação de overlays privados de recibos em `pipeline/release_check.py`: arquivos presentes no overlay substituem a versão ativa apenas para aquela avaliação; fontes sem override continuam herdando o recibo ativo. A CLI agora aceita `--reconciliation-root` com `--bundle --output` e recusa gravar uma avaliação de candidato sobre o gate ativo. Três testes focados do overlay passaram.

Para o candidato privado `ca-update-ad940b94fa9214ecf6b3d9cbc2abf46f` (manifesto SHA `df486de8…`), gerei cache isolado ES 5.777 sob runtime/parser atuais. O texto extraído e as páginas são semanticamente iguais, desconsiderando apenas metadados de runtime e horários de eventos de revisão. O SourceWhole V2 foi reexecutado com 8 itens do candidato: 8/8 vinculados, 2 páginas cobertas, 1 parte verificada, zero issues. O recibo correspondente existe apenas em `var/qa-es5777-candidate-data-20261101/data/manifests/reconciliation/`; o active receipt e o bundle ativo não mudaram.

A avaliação do candidato com overlay em `docs/evidence/source-audit-northeast/sp-ac-es-es5777-current-receipt-overlay-release-check-20261101.json` caiu de 281 para **280 erros ING-03**; o erro de runtime ES 5.777 foi removido. O candidato permanece 0/27 UFs, com 255 recibos ausentes, 13 caches stale, 6 gates V2, 3 dependências, 2 bindings e 1 denominador de parte; cobertura ainda tem 5 partes sem inventário, 5 não reconciliadas, 5 não declaradas, 51 escopos sem inventário e 89 sem aprendizagem estruturada. Não foi promovido.

Corrigi `scripts/test-all.ts`: PostgreSQL 17 não expõe `lc_collate`/`lc_ctype` como parâmetros `current_setting`; o runner agora lê esses valores de `pg_database` e inclui logs do container quando a prontidão falha. Suite completa passou no banco descartável PostgreSQL 17.11: **124/124 testes, zero falhas ou skips**. No hash `69bd27cacd8dbfc6c3608506ba045fa2783fb5a5ad33b375e236625ff154936c`, typecheck, lint e build também passaram. A matriz foi regenerada em `docs/evidence/release-check-current-20261101-69bd27cacd8d.json`; segue 0/55 requisitos verificados, pois os outros gates e a cobertura nacional continuam pendentes.

Estado nacional ativo preservado: `ca-7d302a9c674a97b83278` / SHA `be442730…`, `latest.json` SHA `dfc9e7b…`, gate 0/27 e 330 ING-03. Branch `checkpoint/2026-10-29-j11-diagnostic` em `6f93ed1`, +5 frente à `main` local; `origin` anuncia somente `main` (`9ffddef`) e não há ancestral comum. A worktree permanece local e não publicada.
## Atualização corrente — 2026-11-01 05:29 UTC

A matriz técnica foi reavaliada depois da execução administrativa em navegador: **22/55 requisitos verificados** no source hash `a75918654551061846286a8bd0ba980d7ad9d8462bc1c9f2ffa1df7d536f4090`. A execução passou em desktop e mobile, preservou a publicação/texto de origem, validou um rascunho sem preparar ou publicar e removeu a conta automatizada. Os novos resultados e checksums estão em `docs/evidence/release-check-after-admin-browser-20261101.json` e `docs/evidence/admin-browser-verification.json`.

O resultado nacional continua **não aprovado**: publicação ativa `ca-7d302a9c674a97b83278`, manifesto SHA `be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d`, 0/27 UFs, 330 erros ING-03. O detalhamento é: 255 recibos ausentes, 42 denominadores de parte, 14 caches/runtime desatualizados, 10 vínculos textuais/inventariais inválidos, seis gates SourceWhole recusados e três dependências obrigatórias sem alvo/hash atual. `latest.json` não mudou (`dfc9e7b…`).

O gate técnico de containers está pendente porque a evidência atual de build não foi vinculada à publicação alvo; produção, recovery, ingestão e reimport têm evidências ausentes ou incompatíveis com o hash corrente. O portal de fontes AP/AC foi rechecado e não forneceu os documentos integrais; os links da consulta pública do CEDMAC são vídeos. A evidência foi registrada sem reclassificar essas fontes nem alterar pins. Worktree e branch foram preservadas; nenhum artefato foi promovido ou implantado.

## Revalidação parcial — 2026-11-01 06:07 UTC

A publicação padrão continua `ca-7d302a9c674a97b83278` (manifesto SHA-256 `be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d`) e o código local está no hash `be983996a13b633a05bf7ae9aff7f67eb0b727c51c3031b0eb28b1b90cfcb0ed`. Resultado do gate documental: **0/27 UFs prontas, 8/567 recortes prontos e 330 erros ING-03**. A página 474 do PDF oficial de RO confirma um identificador local (`EF01GE11 - 3RO`) que o bundle ativo fragmentou; um candidato corrigido já existe, mas não está integrado. Detalhes e limites em `docs/evidence/source-audit-ro/ef-physical-review-followup-20261101.json`.

Docker Desktop/Engine 29.9.2 está operacional e a QA existente em `localhost:3107` responde readiness 200. A imagem atual passou verificação isolada. O gate `containers` segue falho porque o `docker compose build` foi interrompido por consumo de espaço; havia 9,4 GiB livres após a interrupção. Não houve instalação limpa, publicação nacional aprovada ou deploy remoto. Esta nota é uma atualização do diagnóstico, não aceite final.


## Atualização operacional e comparação de candidato RO-EF — 2026-11-01 06:13 UTC

O Docker Desktop foi recuperado pelo comando oficial `docker desktop restart` após a VM encerrar na primeira tentativa manual. A engine 29.9.2 está `running`, com 20 containers; readiness da QA existente em `localhost:3107` retornou HTTP 200 com banco, publicação e worker prontos. Não foram apagados dados do Docker.

A comparação somente leitura do cache RO-EF com o candidato privado v11 encontrou 1.176 pares únicos exatos de código+texto e 1.315 ocorrências em comum. O v11 preserva as 2.179 identidades do v10 e acrescenta 394 habilidades LP (393 códigos distintos, páginas 149–231), 11 seções normativas e seis registros estruturais; 330 das novas habilidades LP têm par exato no cache ativo. Das 64 restantes, 21 códigos ausentes do inventário de itens ativos foram confirmados visualmente nas células oficiais (páginas 204–217, 229 e 231); as outras 43 ainda aguardam readback físico. Evidência direcionada: `docs/evidence/source-audit-ro/ro-ef-portugues-v11-21-uncached-code-visual-readback-20261101.json` (SHA-256 `813c9c553f7025470cd6b3e60e78880c3c03fe3cc86468470c2496709a2fb5f6`). `actor_id` e `expected_inventory` permanecem os da auditoria v10 de Educação Física (78 códigos nas páginas 366–384), apesar do método do v11 descrever a adição LP: a proveniência está inconsistente e a leitura independente continua pendente. O resultado e a regra de comparação estão registrados em `docs/evidence/source-audit-ro/ro-ef-portugues-v11-cache-comparison-20261101.json`; a comparação não substitui o inventário integral nem autoriza merge/recibo. A publicação ativa segue inalterada e o gate nacional continua 0/27 UFs, 330 ING-03.

## Reinício do Docker e revisão anual RO-EF LP — 2026-11-01 06:29 UTC

Docker Desktop foi reiniciado a pedido do usuário e confirmado em `running`; Engine 29.9.2 respondeu e a rota QA `localhost:3107/api/ready` retornou HTTP 200. Nenhum dado/volume Docker foi removido.

Concluí a leitura visual independente dos 137 códigos EF01–EF05 LP que no v11 herdavam posição ampla `[1,2]` ou `[3,4,5]`. Todos aparecem na coluna física correspondente ao ano codificado; não houve exceção. Criei o candidato privado `data/manifests/uncoded/ro-ef-with-portugues-v12.json` (SHA-256 `ab1075de25bf10289367b9b592067a7793141a125ed807781600b6f80f0e7688`), preservando os 2.590 registros do v11 e estreitando as 137 posições para o ano verificado. O v11 permaneceu inalterado (SHA `050d0a4d296d7a930b6892be1335f0cd8097191f6f75f532708eab1bf71bd1e4`). Evidência por registro: `docs/evidence/source-audit-ro/ro-ef-portugues-v12-year-column-readback-20261101.json` (SHA `c2bdaf2e8a3cf6f28e3651ffd94bf83b73ee620e2352fbed21709c3383f29720`); gerador reprodutível: `docs/evidence/source-audit-ro/correct_ef_lp_year_mapping_v12.py`.

O loader/finalizer do pipeline aceitou 2.590/2.590 itens; validação literal não teve erros, a hierarquia não teve pendências e o schema 1.1.0 não teve erros. A quebra de página de `EF05LP27` foi unida em `informatividade`; a sugestão de unir `-\nagem`/`-\neza` em `EF04LP08` foi registrada mas não aplicada ao texto canônico, pois o normalizador de fidelidade do loader não considera esse padrão equivalente. Assim o texto e a evidência permanecem literais. A revisão visual conferiu a distribuição anual, mas não reconcilia o documento RO-EF inteiro (591 páginas), seus denominadores/inventário integral ou os 43 pares de texto do cache ainda em aberto. O v12 é privado: não foi ligado ao manifesto ativo, importado, reconciliado, aceito como WholeSource, nem publicado.

A última matriz integral continua sendo a avaliação amarrada ao hash de código `be983996…`: 0/55 requisitos técnicos verificados; gate nacional 0/27 UFs, 330 ING-03; 8/567 recortes prontos. O sidecar privado não alterou o bundle, a publicação, `latest.json` nem o gate ativo. Branch e alterações preexistentes seguem preservadas; sem merge, push, PR ou deploy.


## Reinício solicitado do Docker e delta runtime privado — 2026-11-01 06:41 UTC

Executei `docker desktop restart` a pedido do usuário. Estado confirmado: Desktop `running`, engine 29.9.2; `http://localhost:3107/api/ready` retornou `status=ready`, `database=ok`, publicação `ca-7d302a9c674a97b83278` e `worker=ok`. O host tem 13 GiB livres. Não foram removidos containers, imagens, caches ou volumes.

Retomei a avaliação do overlay privado de runtime ING-03 criado nesta sessão. A comparação com o gate ativo (330 erros) removeu exatamente os três erros de cache/runtime de DF Vol2, DF Vol3 e SC Língua Inglesa EF. No relatório candidato há 327 erros ING-03; as contagens restantes são 255 recibos ausentes, 42 denominadores, 11 caches/runtime stale, 10 vínculos inválidos, 6 gates V2 reprovados e 3 dependências. Três recortes adicionais ficam prontos (DF Competências Digitais EI/EF e SC Língua Inglesa EF): 11/567 no overlay contra 8/567 no gate ativo; continuam 0/27 UFs.

Relatório candidato: `docs/evidence/source-audit-ing03-runtime-refresh-20261101/candidate-release-check.json` (SHA-256 `bc3be4309483684742bae872af8e634c6257c49f9f76e8368d96f1cb1aa4f8dd`). É uma avaliação privada sobre overlay de recibos; recibos ativos, bundle, `latest.json` e publicação não foram alterados. O gate nacional continua reprovado.


## Candidato QA: cobertura TO-EI derivada do pipeline — 2026-11-01 06:53 UTC

A partir da candidata privada de dez fontes `ca-update-ad940b94fa9214ecf6b3d9cbc2abf46f` (SHA `df486de8…`), gerei a candidata imutável `ca-8c034fb288e05d37f57f` (manifesto SHA `d01916e83ea4f4a0389ba3031b5473d8cf567d3efb6319c2f9a82c05fc2bf715`). O gerador `docs/evidence/source-audit-ing03-runtime-refresh-20261101/materialize_to_ei_scope_coverage_candidate.py` reconstitui as cinco linhas TO-EI usando `coverage_for`, o mapa de projeções explicitamente auditado, o recibo SourceWhole ativo (459/459 itens) e o cache/runtime atual. Em cada linha, a única parte esperada é o Capítulo V; `processed_parts` e `reconciled_parts` coincidem, sem pendências nem erros. A parte continua sendo uma projeção de escopo, não uma alegação de que o capítulo inteiro pertence a um único componente.

O `release_check.py` validou a integridade do artefato e apontou **16/567 recortes prontos**, contra 8/567 na publicação ativa; os cinco recortes TO-EI ficaram prontos, e os bloqueios TO-EI de parte ausente, não reconciliada e placeholder foram a zero. O candidato ainda falha o gate nacional: 0/27 UFs, 278 erros ING-03 (255 recibos ausentes, 11 caches/runtime desatualizados, 6 gates V2 reprovados, 2 vínculos inválidos, 1 denominador e 3 dependências) e ainda 51 escopos sem inventário / 89 sem aprendizagem estruturada.

Relatório completo: `docs/evidence/source-audit-ing03-runtime-refresh-20261101/ten-source-to-ei-coverage-runtime-candidate-release-check-20261101.json` (SHA `bee61917f008c6ecc4f0b286266be3ff1dfb30e0b7e7571b6b10793bb8fb40b1`). Construção: `docs/evidence/source-audit-ing03-runtime-refresh-20261101/to-ei-scope-coverage-candidate-build.json`. Comparação anterior, antes das cinco linhas TO-EI: 11/567 recortes prontos e os mesmos 278 erros ING-03. A candidata não foi anunciada nem promovida; `latest.json` continua em `ca-7d302a9c674a97b83278` / SHA `be442730…`.

Branch revalidada em `checkpoint/2026-10-29-j11-diagnostic`, HEAD `6f93ed1`; está cinco commits à frente da `main` local (`84de9d9`). O remoto só anuncia `main` (`9ffddef`) e não há ancestral comum. Mantive o histórico divergente e as alterações preexistentes sem merge, push, PR ou deploy. `git diff --check` passou.

## Composição AM visual e refresh runtime privado — 2026-11-01 07:17 UTC

A candidata imutável `ca-bb729ac2709455545430` parte de `ca-8c034fb288e05d37f57f` e substitui somente os dois registros normativos da Resolução AM 085 pelos textos conferidos visualmente nas páginas 1–2. O recibo SourceWhole liga ambos (4/4 checks) e a reextração do runtime atual preservou páginas, OCR pinado e conteúdo estrutural; os hashes dos textos foram atualizados pelo adapter visual. Os 13 overlays de runtime são privados e correspondem a AM, DF Vol2/Vol3, SC-LI, cinco fontes SP, ES 5.777, AC CRU EI/EF e PI Resolução 188/Parecer 190.

O release-check vinculado ao manifesto SHA `69cdc6498ea01476fd3b7db216554f97b9af29d31c7007119c7860e0db7b8238` passou DAT-01/02/05 (207.284 itens, zero duplicidade) e reportou 19/567 recortes prontos, 0/27 UFs e 267 erros ING-03. Delta contra a candidata com TO-EI: menos nove erros de cache/runtime, um runtime AM e um vínculo AM; a prontidão subiu em três recortes além dos 16 já aprovados. Os erros restantes são 255 recibos ausentes, seis gates V2, runtime stale de MS, vínculo e denominador MS e três dependências. O critério nacional segue reprovado.

Relatório completo: `docs/evidence/source-audit-am-85-2021/ten-source-to-ei-current-runtime-release-check-20261101.json` (SHA `1c4c363aef2a0454c200d1db098e952068f16399bed742ac2dcdda13587f4a61`). Build: `ten-source-to-ei-am-visual-candidate-build-20261101.json`; relatório dos nove refreshes: `residual-current-runtime-refresh-report-20261101.json`. Nenhum artefato foi anunciado: bundle e recibos ativos, caches ativos, publicação e ponteiro `latest.json` permaneceram intactos.

## Candidato RO-EF p.474 e gate vigente — 2026-11-01 07:35 UTC

A auditoria visual da página 474 confirmou a habilidade local `EF01GE11 - 3RO`, omitida como identificador no texto canônico do item ativo. Um overlay privado de substituição 1:1 preserva o código literal, separa o texto da habilidade e o associa ao 1º ano pelo cabeçalho físico da página 473. Evidências: `docs/evidence/source-audit-ro-geography-p474/ro-ef-p474-ef01ge11-3ro-replacement-candidate.json` e `ro-ef-p474-correction-evidence.json`; a captura tem hash fixado. O overlay não está integrado porque a fonte ainda não tem reconciliação integral: o manifesto seleciona outro sidecar e não existe receipt WholeSource de RO-EF. Nenhum bundle, receipt, cache, banco, ponteiro ou publicação foi modificado por essa correção.

O gate nacional ativo segue reprovado: `ca-7d302a9c674a97b83278` / SHA `be442730…`, 8/567 recortes e 0/27 UFs, 330 erros ING-03. A avaliação da candidata privada `ca-bb729ac2709455545430` indica 19/567 recortes e 267 erros, DAT-01/02/05 aprovados; ela não foi promovida. A branch local está 5 commits à frente de `main`; `origin` anuncia apenas `main`, os históricos locais `main` e `public-main` divergem e não há ancestral comum com o checkpoint. Sem merge, push, PR ou deploy.

## Atualização da fonte RJ Laboratório de Linguagens — 2026-11-01 07:47 UTC

O bundle público local permanece `ca-7d302a9c674a97b83278`, 8/567 recortes, 0/27 UFs e 330 erros ING-03. A avaliação completa corrente está em `docs/evidence/source-audit-rj-linguagens-20261101/active-release-check-current.json` (SHA `4f1d4271f710ed9bed047d4d37dd64fab591795f26b31640e2368e7a0a6e5188`).

A fonte RJ tem correção sidecar local, extração íntegra (8/8) e receipt SourceWhole V2 candidato aprovado (8/8; zero falhas literais; seis negativos rejeitados). O candidate bundle incremental `ca-74023377e85aae4b8b4a` passou DAT-01/02/05 e não teve erro ING-03 para o RJ sob o overlay do receipt. A avaliação desse `source_update_receipt` é parcial e não serve como gate de lançamento. Não instalei o receipt: a publicação ativa ainda vincula os textos/posições antigos, e a verificação de prontidão nacional segue pendente. `latest.json` continuou byte a byte inalterado.

## Reconciliação RJ Laboratório de Humanas e gate da candidata privada — 2026-11-01 08:02 UTC

A revisão visual do PDF oficial de RJ Humanas, hash `47fef969a965f6f22ecacf308cdd41ddbd590698be8b5b6f73f0d60939fd8eb0`, encontrou oito páginas e 12 células curriculares (8 da 1ª série, 4 da 2ª). O sidecar literal recompõe três habilidades que cruzam páginas, remove um duplicado fragmentário de `EM13CHS101`, preserva a grafia impressa “comparando as a narrativas” e registra a quebra tipográfica de `ético-políticos`. Cache local: 8 seções de página + 12 habilidades; zero falhas de schema/evidência/pais. O receipt V2 candidato fecha 20/20 itens, uma parte, sem issues, com seis probes negativos rejeitados; revisão pedagógica e vigência seguem não verificadas.

Delta `ca-3d0a6456792bc046900e` foi composto privadamente na candidata integral `ca-b57fa07a470476258cad`. A mudança retém 20 IDs, remove exatamente um ID duplicado, substitui 10 relações de RJ e preserva o bundle ativo e `latest.json`. O gate completo passa integridade DAT-01/02/05 e falha nacionalmente: 19/567 recortes, 0/27 UFs, 265 erros ING-03; RJ Humanas não tem erro residual na candidata. Artefatos e hashes estão em `docs/evidence/source-audit-rj-humanas-20261101/full-candidate-composition-v2.json`, `full-candidate-release-check.json` (SHA `dc447fce271f4712cc20dce37387ddc4fe284654c5efe4906779ee5c4a2890a1`) e `full-candidate-receipt-overlays-v2/overlay-inventory.json`. O gate ativo e a publicação padrão não foram alterados; a candidata não foi anunciada.

A revisão de branches confirma cinco commits do checkpoint além da `main` local e somente `origin/main` publicado. A história privada e `public-main` são unrelated (raízes distintas e sem merge-base); não se deve interpretar a contagem como avanço linear. Worktree preservada e sem merge, push, PR, deploy ou promoção.

## Atualização de runtime MS — overlay privado, sem reconciliação integral — 2026-11-01 08:12 UTC

Regerei o cache MS com o modelo português local hash-pinado e runtime atual: 127 páginas, `ocr_pending=false`, cache SHA `d6b730abd507a197c7083ec7f2bf02a627110f718dea77f45591b80d34b596cd`, config `cd2d5a9b…51ef0cb`, parser `a76cef2d…5f42c4`. A validação literal/esquema/pais não encontrou falhas. Os 681 checks textuais das três partes curriculares existentes continuam idênticos, mas o parser atual regenerou cinco referências externas ao organizador; a candidata ainda não tem inventário V2 cobrindo todos os itens.

O overlay atualiza exclusivamente o pin runtime do recibo MS e preserva `reconciliation_scope=parts`, sem `v2_gate_result` nem declaração de reconciliação integral. Reavaliação do candidato `ca-b57fa07a470476258cad`: DAT-01/02/05 passou, 19/567 recortes, 0/27 UFs e 264 erros ING-03 (uma redução, exclusivamente o cache stale MS). Permanecem o gate V2, binding e denominador da quarta parte, além de 253 recibos ausentes, seis fontes V2 recusadas e três dependências sem alvo/hash. Evidência de overlay em `docs/evidence/source-audit-rj-humanas-20261101/full-candidate-receipt-overlays-ms-runtime-v1/`; gate `full-candidate-release-check-ms-runtime-v1.json`, SHA `82c17b0fd3b10ca05c887ba89b99e8e23e9e86ed210e0d74c471f9e0f7c743c9`. Receipt ativo, bundle e `latest.json` permaneceram inalterados. A parte narrativa e os 54 registros sem vínculo ainda precisam de denominador e inventário independentes.
