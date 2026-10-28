# Auditoria independente automatizada

## Identidade, escopo e método

Auditor: subagente real `/root/auditor`, distinto dos autores de domínio, portal, API/MCP, administração/operação e pipeline. Tipo de ator: **automatizado**. Data de início: 2026-10-28. Não houve revisão pedagógica humana nem homologação institucional.

A especificação vinculante é docs/requirements.md (55 IDs obrigatórios). A auditoria confronta o código integrado, dados, manifestos e execuções das jornadas J01–J12. Não considera cadastro de siglas, fontes ligadas ou extração parcial como UF pronta. Uma limitação de tempo não é bloqueio externo.

## Estado inicial, ainda durante implementação

- Não existe publicação nacional reconciliada nesta inspeção inicial.
- Os módulos e fontes estão em construção paralela. A existência de arquivos não foi aceita como comprovação das jornadas.
- O gate `npx tsx scripts/release-check.ts` foi executado e recusou o lançamento: 0/55 requisitos verificados, exit 1. O relatório corrente está em docs/evidence/release-check.json.
- Os dois testes isolados de integridade de evidências passaram (`npx tsx --test tests/release-check.test.ts`): versão/código incorreto, execução falha, checksum alterado e flag manual `ready` não satisfazem o contrato.

## Contrato de evidências

`npx tsx scripts/release-check.ts record --kind types --publication PUBLICACAO -- npm run typecheck` executa o comando, registra início/fim, exit code, SHA-256 da árvore de código, publicação e log com checksum em docs/evidence/executions/. Os kinds são containers, types, build, lint, tests, api, mcp, browser, operations, admin, production, recovery, performance, sources e audit. Browser e npm test exigem execução integral sem filtros. MCP exige cliente HTTP e stdio, pois ambos são oferecidos. Os relatórios reais são verificados e a publicação observada precisa coincidir com a declarada; o argumento --publication não substitui uma resposta do serviço. Cada tipo tem prefixo de comando obrigatório; não aceita `true` como substituto.

O gate compara os hashes de artefatos, o código e a publicação do resultado com o estado final. Os testes precisam conter asserções relevantes; o auditor deve inspecioná-las. O gate documental é delegado ao pipeline/release_check.py e seu resultado é integrado ao relatório por requisito. O caso negativo documental será executado de forma isolada, sem alterar o bundle de produção.

`docs/verification.md` é gerado a partir do gate e mantém uma linha por ID, implementação, teste, recorte, evidência, código, publicação, resultado e pendência. Evidências ausentes ou não executadas permanecem não verificadas.

## Próxima inspeção integrada

Conferir jornadas reais e ataques à falsa conclusão especificados em ACE-03. Verificar autorização diretamente nas rotas, handshake MCP por cliente real, isolamento dos snapshots, filtros por blocos, panorama inconclusivo, exports sem perda, fontes/localizadores, worker/restore e responsividade. Registrar achados com arquivo/linha, reprodução, impacto e correção. Nenhum aceite foi emitido nesta etapa.

## Achados da inspeção de código e correções solicitadas

| Severidade | Achado | Requisito | Encaminhamento/estado |
| --- | --- | --- | --- |
| P1 | Panorama tratava qualquer item da UF como recorte processado e podia converter desconhecido em nenhuma correspondência. | DAT-03, FUN-05 | Domínio corrigiu herança da etapa do item nacional e exige cobertura reconciliada; aguarda reexecução integrada final. |
| P1 | Prontidão de UF aceitava flags em uma linha de cobertura sem exigir EI/EF/EM e denominador. | ACE-01, ING-05 | Domínio exige etapas e partes positivas esperadas/processadas/reconciliadas. Gate documental independente confere provas; aguarda publicação final. |
| P1 | Validação não confrontava UF/etapa do item com fonte, permitindo atribuição inconsistente. | DAT-01, DAT-05 | Validação de importação corrigida pelo domínio; testes de integração precisam ser reexecutados no estado final. |
| P1 | Decisão de publicação por ator humano criava automaticamente revisão pedagógica humana. | DAT-02, ADM-02 | Administração separou review_type explícito; publicação conserva revisão pedagógica. Método e evidência são obrigatórios para revisão pedagógica. |
| P2 | Corrida entre edição de rascunho e preparação podia promover snapshot anterior às alterações. | ADM-02, DAT-04 | Administração adicionou revision/CAS em migration003 e transições concorrentes. Aplicar migration e reconstruir imagem. |
| P2 | Curador podia retomar/repetir job de ingestão reservado a administrador. | ADM-01, SEG-01 | Administração restringiu controles de ingestão por papel. |
| P1 | Lote com ID vazio era recusado inteiro pelo schema, em vez de devolver invalid por entrada. | API-02, MCP-03 | API/MCP passou a validar limite/corpo do lote e classificar cada entrada no domínio; testes contrato 6/6 relatados pelo autor, execução final HTTP pendente. |
| P2 | Bootstrap não conferia sidecar de bytes e podia selecionar latest.json como bundle. | OPS-02, ING-04 | Operação passou a conferir checksum e excluir ponteiro do seletor; execução limpa pendente. |
| P2 | Backup com nome apenas até segundos permitia colisão e sobrescrita. | OPS-04 | Operação passou a criar diretório com mktemp; teste de restore usa caminho exato retornado. |

## Primeira auditoria HTTP integrada executada

Comando: `npx tsx scripts/audit-verify.ts`. Ambiente: processo local acessível em http://localhost:3000, publicação piloto `ca-64e60bb2c92be368dcd7` (2.108 itens de SP; 131 fontes inventariadas). Resultado: **exit 1**, sem aceite nacional. Evidência: docs/evidence/audit-integrated.json, com hash da árvore e do bundle.

Foram conferidos os textos, códigos, IDs, fontes e evidências de oito amostras (documento/etapa, códigos com sufixo e textos longos), contagens das 27 UFs e recusa direta de administração sem sessão/origens não autorizadas na API e no MCP. Nenhuma UF foi anunciada como pronta apenas por estar cadastrada. Dependências essenciais estavam fixadas, segredos locais ignorados e não foram encontradas chamadas .skip/.todo/.fixme incondicionais nos arquivos de teste. As opções condicionais de integração exigem execução com ambiente isolado; o gate de execução exige relatório com zero skips.

Falhas observadas: v1.1 do extrator deixou 584 itens sem posicionamento (450 habilidades locais com sufixo e 134 seções normativas), e a publicação piloto ainda não continha BNCC para o panorama. O pipeline recebeu os IDs e deve reprocessar o conjunto afetado na revisão v1.2, preservando razões explícitas quando o contexto não estiver disponível. Não basta corrigir as amostras. A ausência da BNCC no piloto bloqueou as jornadas correspondentes; os clientes reais não substituíram esse passo por mock.

## Operação de produção e recuperação

Os scripts `scripts/qa-production.ts` e `scripts/qa-recovery.ts` foram escritos para executar uma instalação limpa isolada, com projeto Compose único e portas 3001/55438. Geram segredos aleatórios privados em var/, verificam banco vazio, migrations e importação idempotentes, CLI do primeiro administrador, login, API, cliente MCP real, heartbeat do worker e persistência de checksums após reinício. A recuperação chama os comandos de backup e restore entregues, usa banco descartável e compara dados e arquivos. Esses scripts **ainda não haviam sido executados ao registrar este checkpoint**; a imagem precisa conter a árvore final, conferida pelo próprio teste.

## Segunda inspeção de confiabilidade e semântica (ainda em integração)

- **P1, ING-02/SEG-02:** finalização de job filtrava apenas ID, sem fencing de proprietário/tentativa do lease. Um worker antigo poderia sobrescrever o resultado depois de outro reclamar o lease. Encaminhado a administração/operação para comparar lease_owner/attempt e tratar perda de lease.
- **P1, ADM-03/SEG-02:** monitor de fontes não interrompia a iteração ao receber STOP, e o worker lia latest.json sem vincular o relatório ao job. Pedi checkpoint/relatório por job_id, parada antes da próxima fonte e escalada limitada de sinal para parser não responsivo. Não confundir cancelamento com indisponibilidade de fonte.
- **P1, ING-03/ACE-01:** o gate documental inicial precisava recusar inventário sem organização/componentes identificados, exigir hash não nulo e incluir falhas de reconciliação/amostragem na prontidão individual por UF. Encaminhado ao pipeline. Comparar listas esperado/obtido não prova que o denominador veio da fonte; o registro deve conter índice/localizador/método/ator e evidência independente.
- **P2, FUN-03:** a opção de incluir posicionamento desconhecido não alcançava positions=[] por estar dentro de EXISTS sobre a própria lista. Encaminhado ao domínio para política explícita e teste de interseção/ausência, sem inventar ano.
- **P1, DAT-01/FUN-03:** derivar posicionamento local por convenção de código requer regra e evidência de aplicabilidade. O rótulo de método sozinho não torna uma inferência um posicionamento documentado. Encaminhado ao pipeline para preservar desconhecido quando cabeçalho/regra local não estiver conferido.
- **P2, QA-04:** o ensaio de desempenho omitia panorama condicionalmente quando faltava BNCC. Pedi asserção de operações obrigatórias presentes e resultado não aprovado se uma medição estiver ausente. Não alterar metas nem silenciar operação faltante.

Esses apontamentos são revisão automatizada de código. Correção relatada pelo autor é separada da reexecução do teste no produto integrado.

## Checkpoint de estabilização do auditor

- `scripts/release-check.ts` soma o gate documental, caso negativo e evidências de execução, gerando 55 linhas em docs/verification.md. O caso negativo foi executado pelo auditor: baseline isolado passou, remoção de AC/EI/componente obrigatório passou a falhar, com hashes distintos e sem alterar publicação.
- A árvore de código inclui src/, scripts/, pipeline/, tests/, configurações de lint/browser/Docker e docs/requirements.md. Alterar filtros, ignorar arquivos ou mudar o mandato invalida evidências anteriores. Logs e progresso não entram no hash para evitar ciclos.
- `record` confere relatórios gerados nesta execução e a publicação efetivamente consultada. O argumento --publication não vale como prova do corpus servido. API, MCP, browser, administração, desempenho, auditoria, produção e recuperação registram seus relatórios reais com checksum. MCP oferecido exige HTTP e stdio testados. Navegador exige desktop/mobile e anotações data-publication, sem grep/projeto/shard; testes exigem zero skips.
- Tipos, lint, build Next e testes unitários/de domínio isolados têm escopo code_only: precisam do código idêntico, mas não fingem usar o corpus nacional. A troca apenas da publicação não exige recompilar código sem mudança. Container build e jornadas de dados permanecem separados.
- Três testes próprios do gate passaram, zero skips. Typecheck e lint dos arquivos do auditor foram executados durante integração; a rodada final ainda deve usar a árvore estabilizada.
- Autores relataram correções de fencing/lease, TERM→KILL limitado, monitor por job_id, inventário/reconciliação mais forte, texto multipágina e opção de posicionamento desconhecido. Ainda exigem reexecução integrada; não foram convertidas em aceite pelo relato.
- A instalação QA e restauração não foram executadas pelo auditor neste checkpoint. O coordenador preparará a imagem final e executará os scripts isolados. O build Docker tem evidência própria e não é substituído por um processo de desenvolvimento ou pela existência de uma tag.

Próxima retomada: conferir pub/manifesto final, imagem e hash da árvore; executar os wrappers de evidência para API, MCP --stdio, navegador completo, admin, operations, production, recovery, performance e audit; revisar resultados e corrigir causas. Só depois regenerar o gate transversal. Se corpus normativo ou reconciliação faltarem, manter lançamento nacional recusado e registrar bloqueio externo específico separado de trabalho ainda executável.

## Retomada de escala — distribuição sharded-v1

O coordenador identificou que o corpus ultrapassou o tamanho adequado a uma string JSON nacional. A auditoria foi adaptada ao contrato `curriculos-abertos/sharded-v1`, sem aumentar o limite de JSON/string para contornar o problema.

`scripts/audit-artifact.ts` abre somente o manifesto pequeno e percorre todas as partes JSONL.gz. Confere hashes compactados/decodificados, bytes e contagens pelo leitor compartilhado; aplica schemas dos registros e invariantes independentes de fonte/UF/etapa, evidência, hierarquia, direção/revisão e referências. Mantém apenas IDs, contagens e referências compactas de amostra (SHA-256 do texto, evidências e posições), sem reter os textos de todas as UFs na memória do Node. Suporte legado permanece limitado a 64 MiB decodificados e não é usado como caminho nacional escalável.

A auditoria HTTP confronta as amostras estratificadas com a API em lotes pequenos, fixando a publicação. As respostas de detalhe incluem uma amostra por UF e os textos mais longos. Manifesto presente não basta: a inspeção exige esgotar todas as partes antes de considerar sua integridade demonstrada.

A instalação limpa também percorre o artefato antes da importação e compara as contagens carregadas. Para sharded-v1, exige persistência relacional e ausência de arrays items/relations no JSONB de metadados da publicação. As consultas de persistência retornam somente contagens e hashes SQL, sem transferir o JSON nacional ao processo de teste.

A recuperação calcula hashes de dumps/arquivos por stream, confere a árvore recursiva e relê integralmente as partes restauradas em raiz isolada. A mesma inspeção de schemas/referências é executada sobre a árvore restaurada; não se aceita apenas o manifesto ou a existência do arquivo tar.

Três novos testes isolados foram executados: leitura integral e correspondência sem depender da ordem de chaves JSONB; erro semântico na última parte; corrupção do gzip/checksum decodificado e caminho fora da raiz. Todos passaram, zero skips. As fixtures ficaram somente em diretórios temporários e foram removidas. A execução contra o artefato nacional sharded real ainda aguarda a publicação efetiva e o runtime integrado; estes testes não a substituem.
