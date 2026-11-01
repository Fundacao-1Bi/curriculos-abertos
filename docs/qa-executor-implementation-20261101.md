# Executor comum de QA — implementação e validação

Implementado em 01/11/2026. Política operacional:
[storage-policy.md](storage-policy.md). Esta entrega protege o ciclo de vida
dos ensaios; não promove publicação curricular nem comprova aceite nacional.

## Entradas protegidas

`scripts/qa-executor.ts` é obrigatório nas CLIs de instalação limpa,
reimportação, recuperação, ingestão administrativa, verificação administrativa,
verificação de API, browser administrativo, desempenho e suíte de testes.
As entradas continuam utilizáveis diretamente; a proteção está dentro delas.
O modo `--import-worker` de reimportação exige capacidade delegada, pai vivo,
PID registrado, task/diretório/banco próprios criados e fingerprint compatível.

O executor usa caminho real do workspace e arquivo criado exclusivamente para
serializar sessões. Registra propriedade antes de alocar, reserva capacidade
host/Docker, guarda relatórios imutáveis e não registra credenciais. Falha de
admissão não cria banco, export ou ambiente de QA. `process.exitCode` não zero
e recursos descartáveis sem encerramento impedem registrar sucesso.

Antes de usar um QA mutante, confere banco `curriculos_qa`, endpoint local,
cluster PostgreSQL, ausência de jobs ativos, fingerprints de app/worker,
image IDs e hashes das migrations. O ambiente principal não atende esse
contrato. Imagens preservadas de uma revisão anterior precisam de atualização
compatível antes de executar esses ensaios contra o código novo.

## Contenção e fechamento

- `qa-command-watchdog.py` monitora comandos longos independentemente do Node,
  incluindo durante `spawnSync`. Recebe controle privado e registra identidade
  do supervisor/filho antes do monitoramento. Não grava argv, env ou stdout
  como metadados. Só contém seu grupo de processos e one-off rotulado próprio.
- Restore usa cliente PostgreSQL isolado sem montar o volume do servidor.
  Cancelamento/terminação SQL exige ID/labels do servidor QA, nome do banco
  temporário, usuário e `application_name` exatos. Não para o servidor nem
  executa `DROP` como resposta automática a uma guarda.
- `qa-parent-guard.ts` acompanha o pai do worker de reimportação. Perda da
  identidade impede novas queries e contém somente backends da operação própria.
- `qa-executor-job-guard.ts` solicita pausa de uma ingestão cujo UUID/tipo/ator
  próprio sejam comprovados. Espera quiescência por prazo limitado; se não
  houver prova, preserva identidade e diagnóstico e deixa a execução bloqueada.
- Cleanup exige recursos próprios, criados e descartáveis, guardas atuais de
  processos/arquivos abertos/montagens/Docker e as provas específicas do fluxo.
  Inventário exato e hashes impedem remover arquivos extras de uma árvore QA.
- `npm test` cria container e volume nomeados, registra ambos antes da criação,
  fixa a imagem local por ID e usa orçamento de 5 GiB. Após sucesso, confere
  identidade, ausência de referências e remoção. Falha preserva os recursos.

Os limites de um QA de integração, três publicações, exports e fixtures impedem
repetição sem limite. Backup completo retido de uma recuperação exige revisão
explícita antes de outra recuperação. A revisão conserva o material; não é uma
autorização genérica para apagar dados ou para reutilizar fingerprints diferentes.

## Interrupção e uso

```sh
node --import tsx scripts/qa-executor.ts list
node --import tsx scripts/qa-executor.ts reconcile qa-TIPO-UUID 'Motivo concreto de retenção e próxima revisão'
```

`list` é somente leitura. `reconcile` confere que dono e filhos não continuam
ativos, examina uso/montagens e exige quiescência dos jobs do QA identificado.
Grava revisão e libera somente a lease correspondente; não apaga dados, retoma
jobs ou inicia Docker. Lease sem registro após crash na admissão também é
detectada. Uma revisão interrompida pode precisar de inspeção explícita do seu
próprio lock de revisão; não há expiração automática que roube locks por idade.

Para QAs mutantes, usar arquivo de ambiente e endpoint do QA compatível. O
`make verify` passou a executar testes com banco e verificação de API no host,
compartilhando a lease; configurar `VERIFY_ENV_FILE` e `COMPOSE` para o projeto
pretendido. As verificações somente leitura de tipo/MCP/smoke no container
continuam separadas. A política descreve as fronteiras de cada comando.

## Validação executada

- `npm test`: **165/165 testes passaram**, 30 arquivos, zero skips, PostgreSQL
  **17.11** temporário. A execução usou a entrada real do novo executor.
- Conferência posterior: todos os 16 recursos próprios descartáveis registrados
  ficaram `cleaned`; container e volume de testes ausentes; lease ausente.
- `npx tsc --noEmit --incremental false`: passou.
- ESLint dos arquivos TypeScript alterados e testes associados: passou.
- `python3 -m unittest discover -s tests -p test_qa_command_watchdog.py -v`:
  **23/23 testes passaram**, com comandos sintéticos e Docker/SQL simulados.
- `git diff --check`: passou. Sintaxe Bash dos fluxos de backup/restore validada.

A suíte inclui disputa real entre processos e alias de caminho, `SIGKILL`,
lease órfã antes do registro, filho ainda ativo, delegação falsa, insuficiência
de capacidade, limites, fingerprints divergentes e recusa de limpeza com
prova incompleta. Os testes do monitor incluem timeout, crescimento, perda do
pai, descendentes, container estrangeiro e cancelamento SQL com escopo restrito.

Execução completa:
`var/jobs/qa-tests-8a20cfb2-304b-428d-b89f-556f21a39c2d/retention.json`.
Recibo resumido versionável:
`docs/evidence/qa-executor-verification-20261101.json`.

## Limites da prova

Não foram executados build ou importação/exportação/restore do corpus nacional
para esta mudança. O cancelamento de backends do restore foi validado com
Docker/SQL simulados; não declarar por isso uma recuperação nacional aprovada.
Principal, QA existente, dados canônicos, backups e imagens permaneceram
preservados; o ponteiro `latest.json` manteve seu SHA.

Exports públicos são deduplicados sem prova de autoria. Seus jobs/arquivos no
servidor ficam retidos sob teto; abortar o cliente não prova cancelar esse
trabalho compartilhado. A pausa de ingestão é cooperativa e depende de
heartbeat/cancelamento. Orçamento e monitoramento não são quota rígida do
filesystem nem proteção contra consumidores externos.

Builds, extrações Python e comandos Docker/SQL fora das entradas integradas
ainda exigem coordenação e inventário explícitos. A autorização anterior de
aposentadoria de cinco QAs não se estende a novos volumes ou dados únicos.
