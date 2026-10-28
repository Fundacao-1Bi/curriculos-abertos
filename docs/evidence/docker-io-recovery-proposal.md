# Recuperação proposta após esgotamento de espaço

Estado observado em 2026-10-28, 16:01 UTC. Não foi executado reinício global.

## Fatos

- O host chegou a aproximadamente 140 MiB livres durante exportação/descompactação da imagem técnica. O build encerrou, mas a subida/verificação da imagem falhou.
- Foram recuperados aproximadamente 1,6 GiB com ações restritas ao projeto: cache gerado Next, arquivamento gzip reversível de 229 caches obsoletos v1.3 e remoção da cópia JSON redundante de ca77 após verificar gzip e SHA de descompressão. Um cache v1.3 com leitor ativo foi preservado. PDFs originais, caches atuais, volumes e backup de rollback não foram removidos.
- Mesmo após recuperar espaço, o Docker continua retornando `input/output error` em blobs antigos do content store, logs de containers, `/var/lib/docker/buildkit/containerd-overlayfs/metadata_v2.db` e `/var/lib/desktop-containerd/daemon/io.containerd.metadata.v1.bolt/meta.db`.
- `docker exec` do app falhou antes do comando com `openat etc/passwd: input/output error`; não foi possível consultar `/proc/mounts`. Não há evidência suficiente para afirmar filesystem somente leitura ou corrupção permanente; o erro explícito é EIO, não EROFS.
- O banco do projeto saiu com código 1, sem OOM, às 15:32:16 UTC. O erro registrado aponta para leitura de `.../containers/783ff.../hosts` com EIO.
- App e worker foram parados via Docker, conforme autorização da coordenação. A remoção apenas desses containers parados, sem `-v`, foi recusada pelo daemon com EIO no `meta.db`. Nenhum volume foi removido.
- O container PostgreSQL de ContentiZAP foi observado como `running`. Não foi reiniciado ou alterado por esta frente.

## Próximo passo que depende de autorização

Reiniciar normalmente o Docker Desktop, o que interrompe temporariamente também os containers de ContentiZAP e outros serviços no mesmo daemon. O escopo do projeto não autoriza fazer isso silenciosamente.

Não executar factory reset, apagar `Docker.raw`, apagar volumes, reparar dados do PostgreSQL manualmente ou fazer prune global. Se o reinício não resolver EIO, parar e reavaliar o armazenamento; não repetir reinícios indefinidamente.

Os 1,6 GiB recuperados, com 200 MiB reservados para a aquisição oficial PB já autorizada, parecem suficientes para uma inicialização sem build ou exportações, mas não garantem reparo. Nenhum novo build, FULL ou teste com gravações grandes deve ocorrer antes de recuperar margem adicional e validar o daemon.

## Verificação depois de um reinício autorizado

1. Conferir Docker API, leitura de metadados/content store e status dos containers de ContentiZAP, sem alterar sua configuração/imagem/volumes.
2. Conferir o volume dedicado PostgreSQL 17.11 do projeto e seu log de recuperação WAL. O volume anterior 17.7 e o backup privado devem permanecer intactos.
3. Subir somente o banco dedicado do projeto se necessário; ler `pg_is_in_recovery()`, publicação padrão, SHA de ca77, contagens e ledger de migrations. Última publicação padrão confirmada antes da falha: ca77, SHA `da8fb61ce80b2aec4a83d4f0e9cdeb306505c384315af59a76b0fc9fabc03eb0`.
4. Obter novo backup privado quando houver espaço suficiente.
5. Recuperar espaço com GC somente de IDs de cache/imagens técnicas próprias, provadamente sem uso; nunca prune global.
6. Validar imagem técnica e source fingerprint antes de recriar app/worker. Não usar tag cujo blob esteja faltando ou ilegível. Sem nova construção até haver margem para o pico medido de export/unpack.
7. Só então repetir readiness, API/MCP e J11 completo. O candidato global 030922 continuava privado; a jornada completa ainda não está aprovada.
