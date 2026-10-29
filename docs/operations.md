# Operação autogerida

## Contrato operacional

PostgreSQL mantém publicação, autenticação, fila e auditoria. App é Next.js em `next start` de produção; worker Node executa parsing Python por subprocesso, fora das requisições. Leitura pública não exige conta ou chave de modelo. O projeto não seleciona uma conta externa nem cria recursos pagos.

Requisitos: Docker Engine + Compose v2, Node 22 LTS+ e npm para a primeira configuração, espaço suficiente para banco, fontes e backups. A imagem contém Python, Poppler, Tesseract português e PyMuPDF fixado em pipeline/requirements.txt. Node 22.23.4 e PostgreSQL 17.11 são os defaults documentados; `POSTGRES_IMAGE` permite selecionar imagem compatível explicitamente. O lockfile fixa dependências JavaScript; instalação e operação na imagem usam npm 11.6.2, igual ao packageManager declarado. As versões padrão foram conferidas nas fontes oficiais de [Node LTS](https://nodejs.org/en/about/previous-releases) e [PostgreSQL](https://www.postgresql.org/support/versioning/); o relatório de execução identifica os digests efetivamente usados. Fontes PDF não são redistribuídas automaticamente: o diretório `data/raw` é cache de coleta, fora do Git.

`make preflight` antecede `image` e `bootstrap`. O guard exige por padrão 15 GiB livres no filesystem do projeto (`BUILD_MIN_FREE_BYTES`), verifica configuração e Docker/Compose e, quando a imagem Node já está local, confere também espaço no filesystem Docker com um probe descartável sem rede. A margem considera o pico de exportação/unpack observado neste projeto. Esse guard não garante integridade do daemon nem substitui monitorar espaço de volumes e do disco virtual do Docker Desktop. Sem imagem base local, o espaço interno ainda não pode ser medido e isso fica explícito no resultado; o preflight não faz pull. `node --import tsx scripts/ops-preflight.ts --disk-only` permite conferir apenas o espaço do host sem acessar o Docker.

Depois de construir, `make image` executa `scripts/ops-image-verify.ts` antes de qualquer recriação de serviços. Um container descartável, sem rede, somente leitura e sem segredos verifica JSONs críticos, BUILD_ID, UID e o fingerprint dos arquivos efetivamente exportados na imagem, comparando-o ao repositório. A verificação falha diante de arquivo vazio, imagem incompleta ou edição concorrente durante o build. O resultado fica em `docs/evidence/image-files-verification.json`. Para conferir uma tag específica: `node --import tsx scripts/ops-image-verify.ts --image curriculos-abertos:TAG`. Um build com exit0 ou um processo Node funcional, isoladamente, não comprova a integridade da imagem.

`make up` também verifica a imagem e seu fingerprint antes de executar `docker compose up`; se a verificação falhar, não recria serviços. Esse caminho não constrói nem baixa imagens e não exige os 15 GiB reservados para build. Se o repositório ou os manifests mudaram desde a construção, a divergência exige congelar as entradas e executar `make image` antes de `make up`. A configuração `RELEASE_TAG` seleciona a tag verificada e usada pelo Compose; não use `docker compose up` diretamente para contornar essa conferência.

`data/bundles` fica fora do contexto Docker, assim como raw e extrações. Os artefatos entregues permanecem no host e são montados pelo `./data:/app/data` do Compose; app recebe leitura e worker recebe escrita. Manifests, schemas e provas documentais usadas pelo parser continuam na imagem. O fallback aplica a mesma exclusão. Executar a imagem sem o mount de dados não corresponde à distribuição Compose documentada.

QA de instalação, reimportação e recuperação verifica a imagem antes de criar ambiente ou recursos. A reserva de build de 15 GiB continua independente. `qa-capacity.ts` calcula espaço incremental por etapa: antes da instalação usa o artefato verificado; depois mede `pg_database_size`, bytes SQL completos e a maior UF. O orçamento inclui export no servidor, download no cliente, conversão em shards, cópias SQL, WAL, índices e reserva. Vínculos podem trazer membros de outras UFs, portanto o suporte do recorte recebe um limite conservador do grafo nacional inteiro. Host e filesystem Docker precisam comportar o orçamento; não se reutiliza o antigo limiar fixo de 3 GiB para FULL.

A ordem é instalação limpa → reimportação nacional e maior UF → backup/restore. Após prova completa, a reimportação revalida os SHAs e remove somente seu diretório aleatório, banco descartável e exports criados nesta rodada no projeto QA isolado; jobs preexistentes são preservados. A recuperação remove apenas o banco restaurado com nome aleatório e suas cópias extraídas, depois de comparar registros e arquivos. Backups privados, volumes QA e artefatos canônicos permanecem. Falhas preservam os arquivos para diagnóstico. Essas rotinas não removem volumes nem dados do projeto principal.

## Instalação limpa e início

```
npm ci
make configure
make bootstrap
```

`configure` cria `.env` com permissão 0600, senha PostgreSQL e segredo Better Auth aleatórios. Nunca imprime segredos. Se `.env` já existe, preserva o arquivo. `bootstrap` constrói imagens, inicia banco, executa migrations, importa um bundle pronto em `data/bundles` apenas quando ainda não existe publicação, e inicia app/worker. Verifica checksum sidecar e integridade do bundle antes de promover. O loader aceita JSON ou JSON gzip, com limite padrão de 256 MiB do arquivo compactado e 512 MiB do JSON decodificado (`DATA_MAX_FILE_BYTES`/`DATA_MAX_DECODED_BYTES`); confere checksums de ambos quando compactado. Publicações maiores usam manifesto JSON com shards JSONL.gz verificados. JSON/JSON.gz grandes de exportação também são reimportados incrementalmente por conversão para shards; `DATA_MAX_STREAM_BYTES` limita a 10 GiB de fluxo por padrão, sem aumentar o limite de string nem o heap. O import verifica todas as referências antes de promover e preserva IDs/relações. Não coleta a internet a cada boot. O estado real de cobertura vem do manifesto: subir uma publicação parcial não libera lançamento nacional.

Para escolher outro bundle entregue, use `make bootstrap DATA_BUNDLE=data/bundles/ID.json`. Se houver dados existentes, `bootstrap` não os substitui. Nova publicação é importação explícita: `make data-import DATA_BUNDLE=data/bundles/ID.json`. Publicações com o mesmo ID e conteúdo diferente são rejeitadas.

Para obter localmente as imagens oficiais atuais ARM64 quando o daemon não consegue baixar mas o host tem acesso HTTPS, `make runtime-images` usa Registryv2 anônimo, valida digests do index/manifest/config e de cada layer compactado/descompactado e executa `docker load`. O helper é específico para linux/arm64 nesta entrega; o Dockerfile padrão permanece multi-arquitetura. Tokens e URLs assinadas não são registrados. `docs/evidence/runtime-images.json` comprova os digests e as verificações reais de Node22.23.4 e PostgreSQL17.11. Ele não troca o banco em execução: atualize `POSTGRES_IMAGE` e reinicie somente o projeto após backup.

Se o endpoint de build/pull do Docker ficar indisponível mas o ciclo normal de containers funcionar, o fallback explícito é `make bootstrap IMAGE_BUILD_METHOD=lifecycle`. Ele exige uma imagem oficial de runtime já presente, selecionada por `NODE_IMAGE`, e produz a aplicação por create/cp/exec/commit isolados, com npm ci e build de produção reais. Não reinicia daemon nem acessa serviços alheios. O contexto exclui .env, PDFs brutos, caches, Git e diretórios privados; o fingerprint interno confere o código antes do commit. O relatório `docs/evidence/docker-build.json` registra runtime/digest/plataforma/comandos/resultado. O fallback foi implementado durante a indisponibilidade inicial; sua execução integral não foi aprovada naquela etapa. Após carregar os runtimes oficiais, o build padrão Compose foi executado com sucesso e permanece o caminho verificado de distribuição. A imagem cache de ferramentas contém somente runtime, ferramentas públicas e package files, sem configurações privadas.

O endereço local padrão é `http://localhost:3000`; API `/api/v1`, MCP `/mcp`, administração `/admin`, saúde `/api/health`, prontidão `/api/ready`. O PostgreSQL é acessível somente no loopback `127.0.0.1:55437` para ferramentas locais; app e worker usam a rede interna do Compose. App se mantém em loopback e deve ser publicado por proxy TLS no servidor remoto.

## Primeiro administrador, curador e recuperação

```
make admin-create EMAIL=administrador@seu-dominio NAME='Responsável' ACTOR_TYPE=human
make admin-create EMAIL=curadoria@seu-dominio ROLE=curator ACTOR_TYPE=human
make admin-reset EMAIL=administrador@seu-dominio
```

Cada comando solicita senha de 14 a 128 caracteres por stdin, sem colocá-la em argumento ou log. Em terminal interativo a entrada fica oculta; para execução automatizada encaminhe um segredo de seu gerenciador para stdin. Não há senha padrão, registro público de usuários nem e-mail pago obrigatório. A recuperação exige acesso administrativo local ao ambiente e revoga todas as sessões da conta. O comando recusa conta inexistente ou e-mail duplicado.

O padrão `ACTOR_TYPE=automated` previne atribuição indevida de humanidade ao uso por agentes. `human` deve ser escolhido somente para a conta de uma pessoa. Administradores podem publicar/reverter e iniciar ingestão; curadores podem revisar, preparar rascunhos, tratar contribuições e monitorar. Toda rota de mutação verifica sessão, papel, Host/Origin e validação no servidor. Contas automatizadas continuam registradas como automatizadas, independentemente do papel.

As tabelas Better Auth são migradas pelo projeto. Sessões duram oito horas, com renovação e cookies HttpOnly; HTTPS ativa cookies Secure. O cadastro web está desativado. Para rodar atrás de proxy, configure `PUBLIC_URL` com o endereço externo real e encaminhe corretamente Host/Origin. Não desative a proteção para contornar erro de configuração.

## Curadoria e publicação

Na administração: consulte a fonte, confira o ID e os localizadores; crie rascunho a partir de snapshot; registre correção de transcrição ou aceite/rejeição/contestação de relação com justificativa; valide tecnicamente; prepare snapshot imutável; publique como padrão. É possível reverter o padrão para um snapshot já publicado sem apagar histórico. A reversão rejeita candidatos preparados. Correções não fingem que a secretaria mudou o currículo. A origem das relações não muda com a aceitação. Validação técnica e revisão automatizada não constituem homologação pedagógica humana.

Para uma nova ingestão, o administrador inicia o job em **Trabalhos de processamento** e acompanha o resultado persistente. O worker confere o checkpoint e o SHA do artefato daquele mesmo job e importa o candidato em estado preparado, sem mudar o padrão. Em **Candidatos de ingestão**, selecione a edição, confira metadados, fontes, itens e evidências na prévia autenticada; registre justificativa e use **Validar candidato**, seguido de **Publicar candidato**. Esse fluxo não exige inventar uma correção de texto. Antes da publicação explícita, API pública, MCP e downloads não revelam o candidato. A validação técnica verifica integridade e referências; a prontidão nacional exige o gate documental separado.

Contribuições públicas entram em fila privada persistente e não alteram dados públicos diretamente. Uma decisão de contribuição não publica texto; o responsável deve preparar uma nova revisão. Contatos não são coletados nesse formulário. Eventos de auditoria mostram ator, tipo real, data, antes/depois e justificativa.

## Worker e fontes

```
make data-ingest
make data-ingest SOURCE=ID_DA_FONTE
make sources-check
make sources-check SOURCE=ID_DA_FONTE
make logs
```

A fila em PostgreSQL usa `FOR UPDATE SKIP LOCKED`, lease de 45 segundos e heartbeat de 10 segundos. Tentativas têm backoff, máximo três; a administração permite pausar, retomar e repetir. Reinício reaproveita checkpoints do mesmo job. Jobs pausados não publicam nada. Um lease expirado é retomável; atingir tentativas sem sucesso torna o erro explícito. SIGTERM encerra o subprocesso, devolve trabalho interrompido à fila e preserva progresso.

A aquisição tem limites configuráveis por documento (`SOURCE_MAX_BYTES=209715200`, 200 MiB; `SOURCE_MAX_PAGES=2500`; `SOURCE_TIMEOUT_SECONDS=90`). O limite de 200 MiB inclui referenciais oficiais extensos sem permitir downloads ilimitados. O parsing roda fora do processo web, em worker sem capabilities adicionais e com `no-new-privileges`, memória padrão 4 GiB, 2 CPUs, limite 256 processos e temporários limitados a 512 MiB. `WORKER_MEMORY_LIMIT` e `WORKER_CPUS` permitem ajustar a instalação. OCR limita threads a duas e instala os modelos português/osd. No host o worker respeita PIPELINE_PYTHON/PYTHON_BIN e prefere var/venv-pipeline/bin/python antes do Python de sistema; na imagem usa /opt/venv/bin/python.

O monitor executa `pipeline/ingest.py sources-check`, registra hashes/metadados e abre avaliação. Não promove edição automaticamente. Configure `SOURCE_CHECK_ENABLED=true` e `SOURCE_CHECK_INTERVAL_SECONDS` (mínimo 60; padrão 86400) para agendar jobs internos. O monitor distingue os estados produzidos pelo pipeline; nova edição exige confirmação documental e revisão. Nenhuma mensagem externa é enviada.

Exports grandes são jobs persistentes com publicação fixada. Arquivos ficam em `STORAGE_DIR/exports`, escritos primeiro em temporário e renomeados atomicamente. UUID e extensão são validados antes de resolver caminhos. Exports públicos não incluem usuários, contribuições ou auditoria. Não se anuncia validade temporária: arquivos são mantidos até política de retenção explicitamente configurada pelo operador.

## Verificações

```
make verify
make release-check
```

`verify` executa tipos, testes, cliente MCP real, checks HTTP e API. `release-check` executa o gate transversal baseado em inventário, dados publicados e evidências reais; retorna não zero enquanto obrigatório estiver pendente. Usa o runtime da imagem em um container descartável com `docs` do repositório montado, para conferir os relatórios atuais e salvar a matriz no repositório. A pasta deve permitir escrita pelo UID 1000 usado na imagem. A área `/api/metrics` exige administrador e mostra agregados de contagem/latência e jobs. `/api/ready` requer banco, publicação carregada e worker recente; `/api/health` responde pelo processo. Logs são JSON com IDs de requisição/job. A existência desses comandos não é evidência de que passaram: consulte `docs/evidence` e o relatório final.

## Backup e restauração exercitável

```
make backup
make restore BACKUP=var/backups/AAAAmmddTHHMMSSZ RESTORE_DB=curriculos_restore_test
```

Backup é privado: contém usuários/sessões/auditoria e deve ser criptografado e guardado com acesso restrito pelo operador. Inclui `pg_dump` custom, manifestos/bundles, schemas JSON referenciados pelos artefatos (`data/schema`), exports/checkpoints/monitor e manifesto com SHA-256. Não inclui `.env` nem segredos de configuração; preserve-os em gerenciador seguro. Fontes brutas não redistribuíveis devem ser preservadas à parte se a política do órgão permitir; a instalação de leitura depende do bundle pronto, não da disponibilidade do PDF remoto.

Restore valida checksums e nomes de membros tar e exige um banco novo com prefixo `curriculos_restore_`; nunca sobrescreve a produção. Restaura banco e arquivos em `var/restore/DB`, imprime contagens, permitindo compará-las às originais. Um restore de desastre para produção exige parada planejada, restauração em volume/banco novo, verificação e troca explícita de `DATABASE_URL`; preserve o banco anterior para rollback. O relatório de verificação deve registrar execução real, contagens, restart e isolamento. A documentação isoladamente não atesta recuperação.

## Produção Linux, domínio e TLS

1. Instale Docker/Compose no servidor autorizado; copie este repositório, bundles e `.env` seguro. Use volumes com backup e espaço monitorado.
2. Configure `PUBLIC_URL=https://curriculos.seu-dominio`, `MCP_ALLOWED_HOSTS=curriculos.seu-dominio` e as credenciais geradas; ajuste `PORT` se necessário.
3. Execute bootstrap e crie a conta administrativa. Verifique `/api/ready`, API e cliente MCP pela origem externa.
4. Configure DNS no provedor autorizado para o servidor; coloque Nginx/Caddy existente como proxy para `127.0.0.1:3000`, com certificado TLS válido, preservando Host, Origin, `X-Forwarded-Proto` e suporte a streaming do MCP. Não bufferize SSE. Exemplo Caddy: `curriculos.seu-dominio { reverse_proxy 127.0.0.1:3000 }`.
5. Mantenha banco sem exposição pública, discos/volumes persistentes, logs rotacionados e backup fora da máquina. Configurar DNS/certificado exige domínio e alvo remoto reais; nenhum foi inventado pelo projeto.

Atualizar: faça backup, registre tag/imagem anterior, execute build, migrations, importe nova publicação apenas explicitamente, `make up`, smoke/MCP/gate. Rollback de código usa imagem anterior por `RELEASE_TAG`, sem apagar volumes; não reverta schema destrutivamente. Rollback dos dados usa a administração e mantém snapshots. Rode `make down` para parar preservando volumes; não use `down -v` como operação cotidiana. Rotação do segredo Better Auth exige gerar novo segredo local e reiniciar app; revogue sessões se houver incidente. Rotação PostgreSQL exige ALTER ROLE autorizado e atualização coerente da configuração, nunca logar a senha.

## Migração local verificada de PostgreSQL e collation

A distribuição foi construída pelo fluxo padrão `docker compose build app` com Node22.23.4 ARM64, npm11.6.2, Python3.11.2 e PyMuPDF1.26.7. O fluxo padrão voltou a funcionar depois de carregar as imagens oficiais verificadas; o fallback permanece como alternativa documentada. A imagem técnica e sua identificação estão em `docs/evidence/docker-compose-build-current.json`. A coordenação executa um novo build depois de estabilizar o código para verificar a correspondência final.

O banco dedicado local foi migrado de PostgreSQL17.7/Trixie (libc/collation2.41) para PostgreSQL17.11/Bookworm (2.36) por restauração lógica em **novo volume**, com reconstrução dos índices. O diretório físico antigo foi preservado. A migração verificou o dump SHA-256, os registros das 23 tabelas no snapshot restaurado e, no cutover, as 21 tabelas duráveis (heartbeat e métricas são transitórios), além de índices válidos e versão de collation registrada igual à biblioteca efetiva. As evidências estão em `postgres-upgrade-prepared.json` e `postgres-upgrade-cutover.json` sob `docs/evidence`.

Os helpers são específicos para o banco dedicado `curriculos-abertos` em `127.0.0.1:55437`, com imagem ARM64 atual já disponível:

```
docker compose stop app worker
node --env-file=.env --import tsx scripts/ops-pg-upgrade.ts
node --env-file=.env --import tsx scripts/ops-pg-promote.ts --promote
docker compose up -d --wait app worker
```

O primeiro comando de migração gera um dump consistente com `pg_export_snapshot`, restaura em container/volume isolados na porta55439, confere os registros e a collation e mantém o resultado pronto. A promoção compara novamente o estado durável, encerra o container isolado, atualiza `.env` para o volume novo e inicia somente o serviço `db` do projeto. `DATABASE_VOLUME` seleciona explicitamente o volume e `DATABASE_VOLUME_EXTERNAL=true` preserva esse volume de restauração como recurso externo do Compose. A configuração anterior fica com permissão0600 junto do backup privado em `.env.before-cutover`; os segredos permanecem fora dos relatórios.

Para rollback ao estado anterior, primeiro preserve o estado atual com novo backup. Restaure a configuração privada anterior e execute `docker compose up -d --no-deps --wait db`. O volume antigo e sua imagem original mantêm a combinação de libc/collation com a qual os índices foram construídos. Esse rollback retorna ao ponto anterior ao cutover; alterações posteriores exigem plano próprio de restauração. Os helpers recusam promoção se os dados duráveis mudaram após o backup. Para atualizar um banco com alteração de libc, use restauração lógica em volume novo ou um procedimento explícito de REINDEX/REFRESH; um aviso de collation não é uma validação de compatibilidade.
