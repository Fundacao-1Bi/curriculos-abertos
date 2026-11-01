# Política de disco e ciclo de vida dos experimentos

Esta política deve ser lida antes de criar candidatos, executar testes com
banco, build, extração, composição, exportação, reimportação ou restauração.
Aplica-se também a subagentes e sessões simultâneas no mesmo workspace.
O objetivo é impedir crescimento sem orçamento e recursos sem responsável.

## Estado de implementação

As regras operacionais abaixo são obrigatórias para os agentes. O executor
comum está implementado em `scripts/qa-executor.ts` e é chamado pelas entradas
de QA listadas a seguir. Ele não é um coletor global de lixo: recursos únicos
ou preexistentes continuam protegidos e interrupções exigem revisão explícita.

| Controle | O que existe | O que falta automatizar |
| --- | --- | --- |
| Inventário | Inventário seguro por execução, recursos declarados antes da alocação e recibos por ID | Classificação do passivo legado sem registro continua explícita |
| Capacidade | Reserva host/Docker, checks entre etapas e monitor independente de comandos longos | Comandos manuais externos ao executor não são interceptados |
| Exclusão mútua | Lease exclusiva por caminho real do workspace, identidade do processo e bloqueio de sessões concorrentes | Builds e extrações fora das entradas de QA precisam de coordenação explícita |
| Propriedade e retenção | `var/jobs/qa-<tipo>-<uuid>/retention.json`, eventos e relatórios imutáveis | IDs retornados por APIs deduplicadas não provam autoria |
| Limpeza | Guardas novas de uso/montagens, provas específicas e fechamento dos recursos próprios | Não há descarte automático de backups, dados únicos ou recursos alheios |
| Limites de crescimento | Um QA de integração, três publicações, limites de exports/fixtures e revisão de backup retido | Retenção deliberada exige revisão; não equivale a liberar espaço |

Entradas integradas: `qa-production.ts`, `qa-reimport.ts`, `qa-recovery.ts`,
`qa-ingestion-admin.ts`, `ops-verify.ts`, `api-verify.ts`,
`qa-admin-browser.ts`, `qa-performance.ts` e `test-all.ts` em `scripts/`.
Invocar essas CLIs diretamente também passa pelo executor; `--help` e a
enumeração `qa-admin-browser.ts --list` não alocam recursos pesados. O worker
de reimportação é uma delegação autenticada, não uma entrada alternativa.

Builds, extrações Python, comandos Docker/SQL manuais e outros scripts não
listados não são automaticamente interceptados. Neles, o agente deve cumprir
esta política explicitamente. Não usar essas rotas para contornar uma recusa.

## Antes de criar recursos

1. Consultar o ponto de continuação em
   [experiment-consolidation-20261101.md](experiment-consolidation-20261101.md).
   Identificar base publicada, candidato de continuação e escopo do delta.
   Não inferir sucessor apenas por data, quantidade de itens ou nome.
2. Inventariar disco, processos, arquivos abertos, containers e montagens.
   Identificar outras operações pesadas e QAs do projeto ainda sem decisão de
   retenção. Resolver esse passivo antes de abrir outro QA nacional.
3. Calcular o pico real da próxima etapa, incluindo arquivos simultâneos,
   índices, banco, WAL, cópias de conversão e reserva. Verificar espaço no host
   e no Docker; considerar a capacidade já reservada para trabalho em curso.
   Não somar tamanhos APFS/Docker sobrepostos como espaço recuperável.
4. Registrar a execução **antes** de criar banco, volume, export ou árvore de
   dados. Não usar apenas o ponteiro mutável `qa-clean-state.json`.
5. Designar um responsável pela integração. Manter no máximo uma operação
   pesada por vez no workspace, inclusive entre subagentes e sessões.

O preflight de build mantém a guarda de 15 GiB. Para QA nacional, 40 GiB é
referência de planejamento, não autorização nem garantia de capacidade.
Não reduzir limites para fazer uma execução passar.

O registro `var/jobs/<run-id>/retention.json` deve conter:

- ID, responsável, propósito, início, estado e última atualização;
- hashes de código, inputs e base; fonte-alvo e resultado esperado;
- caminhos e IDs exatos de recursos, distinguindo próprios de preexistentes;
- orçamento de pico, reserva e limites de crescimento da execução;
- dependências, sucessor designado e evidências que precisam sobreviver;
- resultado, decisão de retenção/limpeza e evento de revisão previsto.

Não armazenar senhas, tokens ou variáveis de ambiente completas nesse registro.
Relatórios e recibos finais devem ser imutáveis por execução; ponteiros para o
último resultado são apenas índices. Registrar transições de estado sem apagar
o histórico, incluindo falha e interrupção.

## Durante os experimentos

Usar recibos e deltas por fonte para as tentativas. Alteração de recibo ou
diagnóstico deve gerar relatório pequeno contra o mesmo artefato imutável,
sem outro corpus, export ou banco nacional apenas para renovar a avaliação.
Acumular os deltas validados antes de uma composição nacional por rodada.

Manter um ambiente de integração do projeto; instalações vazias adicionais
devem ter finalidade de aceite explícita, isolamento, capacidade e decisão de
encerramento próprios. Reutilizar um QA somente com image ID, código, inputs,
publicação, migrations e configuração compatíveis. Não apresentar um ambiente
reutilizado como prova de instalação limpa.

O QA deve ter limites registrados de bytes e publicações completas, com base,
candidato e rollback necessário identificados. Não manter indefinidamente
uma publicação nacional por tentativa ou teste administrativo. Se o limite
for atingido, impedir novas alocações e consolidar/encerrar o ensaio antes de
continuar. Essa regra de QA não autoriza apagar histórico do produto principal.

Acompanhar crescimento e folga durante operações longas. Ao atingir a guarda,
impedir a próxima etapa ou suspender somente o batch identificado pelo monitor
adequado, preservando checkpoint. Não interromper serviços alheios. Retomada
exige conferir PIDs, identidade da execução e capacidade novamente.

## Encerramento e retenção

| Resultado | Ação exigida |
| --- | --- |
| Sucesso | Guardar provas compactas, hashes, deltas incorporados e sucessor; executar a limpeza própria dos recursos descartáveis autorizados, depois das verificações |
| Falha | Guardar erro, inputs, checkpoint e material necessário ao diagnóstico; registrar tamanho, responsável e motivo de cada retenção |
| Interrupção | Marcar execução interrompida e reconciliar o registro com os recursos reais antes de retomar ou abrir nova operação |
| Recurso sem registro | Classificar propriedade, uso e dependências; ausência de dono não é permissão para excluir |

Um `finally` não resolve encerramento forçado, crash ou reinício do host.
O executor detecta execuções incompletas na inicialização e bloqueia a próxima
alocação até a reconciliação aplicável.
PID inexistente, lock antigo, idade ou prazo vencido disparam revisão; não
autorizam apagar recursos ou assumir um lock sem conferir sua identidade.

Separar evidência histórica de cópias completas do corpus: preservar manifestos,
diferenças, resultados e proveniência quando bastarem para o propósito de
retomada. Antes de descartar estado único, identificar curadoria, drafts,
contribuições, jobs pausados e eventos. Pacote seletivo de metadados não equivale
a backup integral nem prova de restauração; registrar esse limite.

Limpeza automática só pode alcançar recursos próprios, registrados como
descartáveis e cobertos pela autorização aplicável, depois de verificar
evidências, hashes, referências, processos, arquivos abertos e montagens.
Falha em qualquer verificação bloqueia a exclusão. Dados únicos, originais,
backups, rollback e recursos de outro projeto continuam protegidos pelo
`AGENTS.md`. Nunca usar `docker system prune` global nem apagar `Docker.raw`.

Não apagar por idade. Toda retenção precisa de um responsável e de um evento
de revisão, como o fechamento da rodada, validação do sucessor ou resolução
da falha. A revisão decide conservar, consolidar ou propor descarte concreto.

`DELETE` não garante devolver espaço PostgreSQL ao filesystem. Para QA
descartável, planejar encerramento do banco/volume conforme autorização e
preservação exigidas. Não executar `VACUUM FULL` como solução automática:
ele requer capacidade adicional e planejamento de locks.

## Operação do executor

Executar os QAs no host, no workspace canônico, com Python 3, `ps`, `lsof`,
Docker e as dependências Node disponíveis. Um lock criado somente dentro de
um container não protegeria as outras sessões; o executor recusa esse modo.
O Docker precisa estar acessível para os fluxos que o utilizam. As medições
leem containers existentes; a admissão não inicia Docker nem cria um ambiente
apenas para medir sua capacidade.

```sh
node --import tsx scripts/qa-executor.ts list
node --import tsx scripts/qa-executor.ts reconcile qa-TIPO-UUID 'Motivo concreto da retenção e próxima revisão'
```

Substituir o ID pelo retornado por `list`. A reconciliação aceita somente a
decisão explícita de conservar os recursos: confere identidade do dono e dos
filhos, uso e montagens; para projeto QA identificado, exige ausência de jobs
`queued/running`. Ela não apaga dados, cancela jobs, reinicia serviços ou retoma
trabalho. Um processo vivo ou uso não verificável bloqueia a liberação da lease.
Lease interrompida antes de gravar o registro inicial também é identificada e
pode receber registro mínimo na revisão explícita. Uma revisão que seja ela
própria interrompida pode deixar `reconciliation.lock.json`; não remover esse
arquivo por idade, sem conferir dono e os efeitos já registrados.

`retention.json` informa `admitting`, `running`, `passed`, `failed`,
`interrupted` ou `retained`. Os recibos de resultado e eventos ficam no mesmo
diretório. Sucesso não pode deixar recursos próprios declarados descartáveis
sem fechamento verificado; `exitCode` não zero também produz falha. Em falha,
os dados de diagnóstico ficam retidos, e recursos pendentes bloqueiam outra
execução até a revisão. Diretórios/bancos próprios de reimportação e restore
são limpos somente depois da prova integral; seus backups ficam preservados.

Os controles atuais de admissão são:

- Bloquear instalação de outro QA nacional enquanto houver um QA de integração
  existente. Reutilização não constitui prova de instalação vazia.
- Exigir banco `curriculos_qa`, endpoint local e cluster correspondentes;
  conferir fingerprints de código, image IDs de app/worker e migrations antes
  dos ensaios mutantes. Não apontar esses ensaios para o principal.
- Limitar a três publicações completas no QA antes de preparar mais uma;
  limitar exports a 15 jobs no QA, cinco pedidos por verificação de API e dois
  por reimportação.
- Bloquear novo fixture de testes se restar container ou volume de um fixture
  anterior. `npm test` usa orçamento explícito de 5 GiB para dados sintéticos,
  container/volume nomeados e cleanup de identidade comprovada no sucesso.
- Exigir revisão do backup completo retido de uma recuperação anterior antes
  de gerar outro. A revisão conserva o backup e não prova restore integral.

O `make verify` roda os testes com banco e a verificação de API no host para
compartilhar a lease. Selecionar `VERIFY_ENV_FILE` com o ambiente QA apropriado
e configurar `COMPOSE` para o projeto correspondente quando usar esse alvo.
O arquivo principal `.env` não se transforma em ambiente QA por ser usado no
comando: a verificação mutante recusa o principal. URLs administrativas para
fixtures de testes precisam ser locais e corresponder ao cluster Docker
inspecionado; servidores remotos/nativos sem orçamento verificável são recusados.

## Monitoramento e limites de contenção

Comandos síncronos longos usam `qa-command-watchdog.py`, que acompanha disco,
prazo e identidade do pai em processo independente do event loop do Node.
Ele registra identidades do supervisor/filho e pode interromper somente seu
grupo de processos e o one-off com nome, ID e label próprios comprovados.
No restore, o cliente PostgreSQL não monta o volume do servidor; cancelamento
de backend é restrito ao banco temporário e `application_name` da operação.
Reimportação valida task/banco/diretório contra o registro do pai e mantém
guarda contínua da identidade desse pai.

Na ingestão, a guarda solicita pausa somente do job com ator automatizado
próprio comprovado e espera quiescência com prazo limitado. Se não puder provar
o encerramento, preserva diagnóstico/identidade e bloqueia continuidade; não
para o worker compartilhado. A pausa é cooperativa, sujeita ao heartbeat e à
latência de cancelamento. Reservas são margens operacionais, não quotas rígidas
do filesystem ou garantia contra consumo externo ao executor.

Exports públicos são deduplicados pela API e não informam autoria de criação.
Por isso os arquivos/jobs do servidor ficam retidos sob limite; não são
apagados ou pausados por terem sido observados pelo QA. Somente os downloads
locais próprios, conferidos por inventário exato e hashes, são limpos. Abortar
o request local não prova cancelamento do trabalho compartilhado no servidor.

Os testes do executor usam fixtures pequenas para concorrência real entre
processos, crash, capacidade, isolamento, filhos e fechamento. Os testes do
watchdog usam comandos sintéticos e Docker simulado; não substituem uma prova
nacional de importação/restore. Ver o recibo de implementação e validação em
[qa-executor-implementation-20261101.md](qa-executor-implementation-20261101.md).

## Evidências e retomada

- [AGENTS.md](../AGENTS.md): regras de preservação e autorização.
- [storage-consolidation-20261101.md](storage-consolidation-20261101.md):
  intervenção de disco concluída e recibos; capacidade é um snapshot histórico.
- [qa-retention-audit-20261101.md](qa-retention-audit-20261101.md): causas do
  acúmulo e limitações dos fluxos auditados.
- [experiment-consolidation-20261101.md](experiment-consolidation-20261101.md):
  linhagem e ponto de continuação; verificar sucessores posteriores antes de usar.
