# Auditoria de retenção e consolidação dos ambientes QA

**Atualização final:** após autorização explícita do usuário, os cinco QAs
`f517a7`, `b6fa71`, `a1f735`, `a65573` e `toei` foram aposentados: 15 containers
e dez volumes removidos, pacotes privados de metadados únicos preservados.
Principal e QA `a3f8cd` permanecem saudáveis. O snapshot histórico abaixo
explica a decisão; não representa mais o inventário ativo. Resultado, limites
dos arquivos retidos e recibos em [storage-consolidation-20261101.md](storage-consolidation-20261101.md).

Levantamento em 2026-11-01, aproximadamente 12:15–12:22 UTC. Auditoria somente leitura de Docker/PostgreSQL; nenhum serviço iniciado, parado, reiniciado, removido ou alterado. Este documento registra propostas, não recibos de execução de limpeza.

## Conclusão comprovada

Há seis projetos QA e o projeto principal. Cinco QAs estavam ativos e um parado. A multiplicação ocorre também **dentro** dos bancos: o QA diagnóstico `f517a7` mantém 24 publicações nacionais completas, com aproximadamente 200–219 mil itens cada. Seu banco mede 45.926.094.515 bytes; a tabela `items`, incluindo índices/TOAST, mede 40.485.142.528 bytes. Portanto, apagar apenas caches do host não resolve o crescimento estrutural.

O QA `a65573` mantém seis publicações de 200.724 itens e ainda um banco de reimportação residual. O QA `toei` mantém três publicações; o QA `a3f8cd`, duas. Os nomes/contagens não provam equivalência entre versões nem autorização para apagar seus dados administrativos e provas.

`df -k .` às 12:21:54 UTC: **1.663.368 KiB disponíveis**, aproximadamente 1,59 GiB. Não executar build, extração, exportação, reimportação, restauração, `VACUUM FULL`, cópia nacional ou **novo backup nacional** neste estado. Os 15 GiB do build e os orçamentos calculados de QA continuam obrigatórios.

## Inventário Docker

`docker system df`: imagens 46,65 GB; volumes 104,5 GB; build cache 55,49 GB. São métricas sobrepostas, com camadas compartilhadas. Não somar nem anunciar esses números como espaço recuperável. A listagem de imagens apresentou inclusive tamanho único negativo para `local`; usar os números como inventário, não medição física confiável de economia.

Na tabela, DB/storage são tamanhos arredondados de `docker system df -v`, em GB decimais. O tamanho SQL é `pg_database_size`, não o volume completo, e não deve ser somado ao volume.

| Projeto Compose | Estado | Containers app / worker / DB | DB / storage | Banco SQL e publicações |
|---|---|---|---|---|
| `curriculos-abertos-clean-20261028205403-f517a7` | ativos | `ee88fb967f98` / `0fc642a0a890` / `1c6e8b09218b` | 47,02 GB / 8,226 GB | `curriculos_qa`: 45.926.094.515 bytes; 24 publicações; default `ca-297c7ec9ab33fcaae579` |
| `curriculos-abertos-clean-20261031210426-b6fa71` | ativos | `10da46d334f7` / `c0000b7e74ee` / `24dc02bff2c2` | 3,041 GB / 1,451 GB | `curriculos_qa`: 1.961.146.035 bytes |
| `curriculos-abertos-clean-20261031214824-a1f735` | parados | `fd0a2eecd01f` / `eec5b64b70bf` / `a2419de51b5c` | 3,058 GB / 94 bytes | Banco parado não foi iniciado para inspeção. Estado arquivado identifica `ca-7d302a9c674a97b83278`. |
| `curriculos-abertos-clean-20261031222510-a65573` | ativos | `d9a55798066d` / `34e5af37b8fa` / `daffd2220708` | 16,17 GB / 3,343 GB | `curriculos_qa`: 12.920.231.603 bytes, 6 publicações; `curriculum_reimport_be0f5dd53b57`: 2.172.412.431 bytes |
| `curriculos-abertos-clean-20261101045455-a3f8cd` | ativos | `9f5173cb5bac` / `4d030b0d4972` / `64030ec0d900` | 4,988 GB / 3,097 GB | `curriculos_qa`: 3.890.771.635 bytes, 2 publicações |
| `curriculos-abertos-clean-toei-20261101` | ativos | `1e07bccec84f` / `5722ca2a07c6` / `bba62b20125e` | 6,901 GB / 516,6 kB | `curriculos_qa`: 5.803.792.051 bytes, 3 publicações |
| `curriculos-abertos` | ativos | `8e80c95a4956` / `7f65f3764b1e` / `783ff1bcba3e` | 2,446 GB / 534,5 MB | `curriculos`: 1.549.997.747 bytes; volume DB efetivo é o de migração `pg1711`, abaixo |

Cada projeto QA usa os volumes exatos `<projeto>_database` e `<projeto>_storage`. Todos os volumes QA têm labels `com.docker.compose.project` correspondentes. Principal usa `curriculos-abertos_database_pg1711_20261028044133-f64587bb` e `curriculos-abertos_storage`. O volume antigo `curriculos-abertos_database` tem 1,829 GB, zero links, mas é recurso de rollback até prova/decisão específica. Zero links não autoriza remoção.

Recursos externos ao escopo: `contentizap_pgdata`, `contentizap_node_modules`, containers `contentizap-*`, imagens e caches sem ownership demonstrado; preservar. Há volumes anônimos sem vínculo demonstrado; não removê-los por nome ou ausência de links.

### Identidade das imagens

| Projeto | Imagem efetivamente executada (SHA-256) | Referência usada ao criar container |
|---|---|---|
| principal | `c2eb90fd88ac746bc8839cdcecae574101ef99c245a3a5abb257c8fdde8758b0` | `curriculos-abertos:local` |
| f517a7 | `9ea498032eabfae9f1b4ec49a6645cf5ec8bd6616f28c5a83f71c02d1cf8336c` | `curriculos-abertos:diag-base-20261028t195651-4a29dd` |
| b6fa71 | `dfc564471b9ab8dee3baf523cdd02a6cbcb19946f9e4f5d91fdbecd05de5fbd0` | `curriculos-abertos:goal-20261031` |
| a1f735 | `fd85675e3d704f614bf71be2ed6dc886ae811a68d8590f2ca6288fef5e4ec82d` | `curriculos-abertos:goal-20261031-current` |
| a65573 | `432163b205ad5da5e68c1138fcaa62c246b621f65dd34936d2ce5f1b46781216` | `curriculos-abertos:goal-20261031-api-gate` |
| toei | `0206bea8a6c5b7a724f20aafec85e1881dc61429d05dbabc0520ac6e913f277d` | `curriculos-abertos:goal-20261101-toei-scope-v2` |
| a3f8cd | `b59080d5ff491b94ee9c5b9a02cb9302c91fa3c1caca3b035e47d08e2dc8809a` | `curriculos-abertos:qa-20261101-a7591865` |

As tags foram movidas: no levantamento `local` aponta para `912ea5ba6ace` e `qa-20261101-a7591865` aponta para `8496095768cd`, diferentes dos containers existentes. Para reutilização ou recuperação, conferir **image ID efetivo**, código, publicação, manifest SHA, migrations, configuração e mounts. Tags e healthcheck não bastam.

Imagens históricas identificadas, sem containers na listagem: `c8c96262fd97` (before-slice-fix), `96488dffdc72` (before-domain-fix), `e14d8dfeb847` (before-contract-fix), `4dfd9268ed48` (before-probe-fix), todas da família diagnóstica `diag-base-20261028t195651-4a29dd`, ~3,69 GB nominais cada. São propostas de revisão de retenção; verificar necessidade de rollback e ownership dos caches antes de aprovar remoção. Não somar tamanhos de imagens e caches associados.

## Montagens dos diretórios grandes do host

Prefixo do projeto: `/Users/otacilio.maia/Desktop/AprendiZAP/Curriculo-Aprendizap`. Docker Desktop apresenta fontes ativas sob `/host_mnt` + esse caminho. A equivalência abaixo foi conferida em `docker inspect` de **todos os 23 containers**, inclusive parados.

| Caminho relativo exato | `du -sk` (KiB) | Montagem atual |
|---|---:|---|
| `var/qa-es-source-update-candidate-20261031` | 10.260.220 | Nenhuma montagem identificada |
| `var/qa-ingestion-data-20261031` | 10.465.184 | `/app/data` do app a65573 RO e worker a65573 **RW** |
| `var/qa-toei-candidate-data-20261101` | 11.061.084 | `/app/data` do app toei RO e worker toei **RW** |
| `var/qa-toei-eval-root-20261101` | 10.923.776 | Nenhuma montagem identificada |
| `var/diagnostic-context-20261028195651-4a29dd` | 7.276.820 | Subdiretório `data` montado em `/app/data` do app f517a7 RO e worker f517a7 **RW** |

Sem mount não significa descartável: antes de qualquer limpeza conferir processos, `lsof`, hashes, evidências únicas, referência em checkpoint e linhagem do candidato. Não reclassificar uma cópia inteira como duplicada sem inspecionar seus arquivos exclusivos. Diretórios montados RW precisam de encerramento específico do escritor antes de consolidar hashes ou remover.

## Evidências de publicações e banco residual

`f517a7` contém a base `ca-7d302a9c674a97b83278`, revisão administrativa `ca-7d302a9c674a97b83278.r-e6de9f90-4221-4d3c-a940-d88b2a3fd095`, default `ca-297c7ec9ab33fcaae579` e 21 publicações `ca-update-*`. Não são cópias byte a byte: manifests diferentes e contagens entre 200.724 e 219.673. As tabelas `relations` e `relation_members` medem 3.153.190.912 e 2.101.207.040 bytes. Consolidar este ambiente exige decidir destino de cada ramo e preservar revisões/eventos/jobs, não só escolher a publicação de maior contagem.

`a65573` contém base, revisão `ca-7d302a9c674a97b83278.r-32d35ecf-d4cd-4d75-8357-df7b71e28d91` e candidatos `ca-update-0b5c2dcc958a706e67be02e478801718`, `ca-update-a4154f6d78c03749cce960d59366a75d`, `ca-update-21d893c0fec0b7ed51cc33c9440c52f6`, `ca-update-0989f21280a76cb4493fc1f3a4cf1423`. Todos declaram 200.724 itens; hashes diferentes.

`a3f8cd` contém base e revisão `ca-7d302a9c674a97b83278.r-d779c8ea-c3b7-4d2f-be74-6f8aa614919e`. `toei` contém base e candidatos `ca-update-e61e73b620fed8731aeaca01cfa362b3` e `ca-update-dbf6556acff2b15ed3f88b29fdae821e`. Nesses três QAs o default permanece `ca-7d302a9c674a97b83278`, manifest `be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d`.

O banco residual `curriculum_reimport_be0f5dd53b57` está ligado diretamente a `var/qa-reimport/2565d9825a04/task.json`, fingerprint de código `dcd608a432ac8be0dee87e3a77629b0186e6125acf5cbd198834c46d388f68a8`. Não havia conexões nele no snapshot de `pg_stat_activity`. Isso prova associação e ausência momentânea de uso, não conclusão/sucesso do ensaio.

O diretório residual mede 1.885.168 KiB e inclui downloads e shards. O task declara:

| Download | Bytes | SHA-256 | Job / ownership |
|---|---:|---|---|
| `national.json` | 1.451.121.538 | `1f9afaebe64ed6a72600c37ba10abdf47ce82624c5bc8c39f0ed60617f0f0b1a` | `16912f30-1bad-4667-9152-10077c1af07e`, **preexistente**, não remover no cleanup da execução |
| `slice.json` | 245.144.027 | `b116a9abcf41701f88d3c89612079cff5c92120ddcb8bd4999fca34caab3b5c7` | `19a67223-6062-4064-867c-4317b0880d67`, criado pela execução |

Esses hashes são recibos existentes, não novos hashes calculados nesta auditoria. O relatório corrente `docs/evidence/reimport.json` falhou antes de iniciar uma nova reimportação porque encontrou duas publicações/401.448 itens onde o snapshot esperava uma/200.724. Não usar esse relatório como prova de sucesso do banco residual.

## Backups e retenção

`var/backups` mede 8.464.136 KiB. Subdiretórios/arquivos:

| Caminho | KiB | Decisão atual |
|---|---:|---|
| `var/backups/20261031T215349Z-DBrZqv` | 3.563.244 | Preservar; precisa comparar manifestos/escopo privado antes de classificar redundância |
| `var/backups/20261031T223935Z-lsFfGH` | 3.962.256 | Preservar; restauração comprovada em `docs/evidence/backup-restore.json` |
| `var/backups/pg1711-20261028044133-f64587bb` | 114.456 | Preservar rollback de migração PostgreSQL |
| `var/backups/pi-parecer190-20261031` | 756 | Preservar evidência específica |
| `var/backups/runtime-rollback-c2eb-20261028.tar.gz` | 823.424 | Preservar imagem do runtime principal efetivo |

O restore de `20261031T223935Z-lsFfGH` passou em a65573 e removeu somente o banco temporário `curriculos_restore_qa_20261031224234_5ae6e83d` e seu diretório extraído. Preservou backup privado e volumes, conforme desenho. Não existe autorização implícita para remover os backups porque o restore já passou.

## Falhas de gestão no fluxo atual

1. `scripts/qa-production.ts:37` sempre cria identidade/projeto novos; `:53` exige volumes novos. Não há registro central de lifecycle/retenção nem limite para o número de QAs simultâneos. Isso é correto para provar instalação vazia, mas não deve ser usado para toda validação incremental.
2. `scripts/qa-production.ts:96` só grava `var/qa-clean-state.json` depois do sucesso e sobrescreve esse ponteiro; `:98-99` sobrescreve `production-install.json`. Falhas posteriores podem esconder a última prova bem-sucedida, enquanto recursos antigos continuam existindo. O relatório atual falha por capacidade e não identifica um projeto novo, pois falhou antes da criação.
3. `scripts/qa-ingestion-admin.ts:102` preserva deliberadamente publicação/histórico após rollback; o `finally` remove conta e job técnico, sem política de encerramento das publicações. Cada ensaio pode deixar mais uma cópia nacional no banco.
4. `cleanupVerifiedReimport` faz boas verificações de namespace, hash, ownership, status, publicação e recibos por job, porém só cuida do próprio download/export. Não consolida bancos históricos, volumes, cópias nacionais ou imagens.
5. `scripts/qa-own-cleanup.ts:15` sobrescreve o intent global; os recibos por job ficam dentro do volume. O `rm(root)` em `:25` pressupõe conteúdo exclusivamente próprio sem manifestar todos os arquivos locais. Acrescentar inventário por execução e validação de arquivos extras antes da remoção futura.
6. `scripts/qa-reimport.ts:84` tenta descartar o banco descartável também em falha; se houver kill/crash isso não ocorre, como demonstra o residual. Gravar ownership antes de criar recursos e ter reconciliação idempotente depois de interrupção é necessário. Falha com banco único exige preservar o diagnóstico antes de descartar.
7. `scripts/ops-resource-inventory.py:40-52` mede diretórios grandes e Docker agregado, mas não mede `tmp`, processos, mounts, bancos ou ownership. O AGENTS exige conferir esses sinais separadamente; só executar esse script não cumpre a auditoria completa.

## Escopos de limpeza propostos, ainda não executados

| Prioridade | Escopo concreto | Prova necessária / dependências | Impacto |
|---|---|---|---|
| 1 | Arquivos duplicados comprovados dentro de `var/qa-es-source-update-candidate-20261031` e `var/qa-toei-eval-root-20261101` | Nenhum mount atual; ainda conferir `lsof`, processos e igualdade de hash; preservar arquivos únicos, patches e recibos num índice compacto | Recuperação depende das cópias preservadas; não remover diretório inteiro por nome |
| 2 | Banco residual `curriculum_reimport_be0f5dd53b57` e execução `var/qa-reimport/2565d9825a04` | Encerrar/reter diagnóstico com status explícito, prova de reconstrução dos downloads/canônico, ownership e nova checagem de conexões; autorização específica de descarte do banco | Perde retomada direta do banco parcial; nacional preexistente/job de terceiros ficam preservados |
| 3 | QA parado `curriculos-abertos-clean-20261031214824-a1f735`, volumes exatos `<projeto>_database` e `<projeto>_storage` | Provas históricas/checkpoint, dados administrativos e rollback preservados; decisão explícita de aposentadoria; autorização específica de volumes | Reexecutar exige imagem imutável/artefato e bootstrap; parada não prova redundância |
| 4 | Publicações históricas / encerramento dos QAs f517a7, a65573, b6fa71 e toei | Linhagem, promoção/rejeição de cada candidato, provas únicas compactas e política de rollback; autorização específica antes de parar serviços ou remover volume | Maior potencial nominal, mas maior risco de perder trabalho não consolidado |
| 5 | Imagens diagnósticas sem containers e seus caches específicos | Lista exata image/cache IDs, dependências, proteção de runtime principal/rollback e ownership | Não usar prune global; liberação física pode ser menor que os tamanhos exibidos |

Volumes, backups, publicações únicas, rascunhos e evidências únicas exigem autorização específica para esse escopo. Este documento não a substitui. O usuário autorizou investigar/consolidar; as decisões concretas de descarte devem continuar revisáveis e amparadas nas instruções de preservação do repositório.

`DELETE` de linhas antigas pode liberar espaço reutilizável **dentro** do PostgreSQL, sem diminuir os arquivos. `VACUUM` comum não devolve automaticamente esse espaço ao filesystem. `VACUUM FULL` reescreve tabelas, exige folga, lock e planejamento; não executar com o disco atual. Não usar compressão, backup ou export nacional extra para criar uma aparente solução que precise de mais pico de disco que a folga disponível.

## Operação futura proposta

- Manter principal e **um ambiente de integração** por fingerprint congelado; reutilizar apenas se image ID, source tree hash, manifest SHA, migrations, mounts e snapshot baterem. Não declarar instalação vazia a partir de ambiente reutilizado.
- Usar testes de fonte/delta para experimentos; promover em sequência os deltas aceitos para uma composição única. Executar instalação nacional vazia apenas no checkpoint de release que exigir essa prova.
- Adicionar registro persistido antes da primeira criação de recurso: run ID, proprietário, propósito, hashes de código/inputs/base, recursos exatos, orçamento/pico, estado (`running`, `passed`, `failed`, `interrupted`, `retained`, `retired`) e dependências/decisão de retenção.
- Relatórios imutáveis por run; ponteiro `latest` separado. Lock de integração/QA pesado para impedir novas cópias nacionais concorrentes. Lock deve recuperar interrupções por PID/identidade verificáveis, sem tratar timeout como autorização para apagar.
- Em sucesso, guardar provas compactas e executar cleanup apenas de recursos próprios já aprovados. Em falha, reter material diagnosticável com dono e decisão de reavaliação; não reter automaticamente toda árvore nacional para sempre.
- Antes de cada limpeza: lista exata e hash de plano, novas leituras de processos/`lsof`/mounts/Docker/conexões, verificação de duplicatas, impacto em retomada/rollback e `df` antes/depois. Se qualquer verificação falhar, não excluir.

## Comandos somente leitura usados

Foram usados `cat`/`sed`/`rg`/`nl` para scripts e evidências; `du -sk var/*`, `du -sk var/backups/* var/qa-reimport/* var/qa-downloads/*`; `df -k .`; `docker system df`, `docker system df -v`, `docker ps -a`, `docker image ls`, `docker volume ls`, `docker volume inspect` e `docker inspect` de todos os containers. JSON completo de `docker inspect` foi processado em memória e **apenas** nomes, IDs, estados e mounts foram exibidos; env/credenciais não foram registrados.

As leituras SQL foram realizadas com `docker exec <db-container> psql ... -At -v ON_ERROR_STOP=1 -c <SELECT>`, consultando `pg_database`/`pg_database_size`, `pg_stat_activity` agregado, `current_publication`, metadados limitados de `publications` e tamanhos de `pg_stat_user_tables`. Não foram lidos usuários/senhas/sessões, nem executados `INSERT`, `UPDATE`, `DELETE`, `DROP`, `VACUUM`, backup ou export.

Os valores são um snapshot. Novas execuções ou serviços ativos podem alterar tamanhos e referências. Qualquer economia final deve ser o delta observado em `df`, com ressalva de atividade concorrente e compartilhamento APFS/Docker.
