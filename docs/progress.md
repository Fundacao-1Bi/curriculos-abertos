# Progresso e checkpoint

2026-10-28: especificação integral lida e copiada sem alteração para requirements.md. Diretório inicialmente vazio; Git inicializado. Node v25.2.1, npm 11.6.2, Docker Engine 29.1.3 disponíveis. Sem alvo remoto autorizado. Pesquisa BNCC/MEC teve HTTP 403 na ferramenta web; alternativas oficiais serão investigadas. Não é bloqueio nacional comprovado ainda.

Estado geral: em execução. Nenhum requisito de lançamento declarado verificado nesta etapa. Contratos estabelecidos em architecture.md e src/shared/contracts.ts. Frentes com propriedade exclusiva de caminhos.

## Checkpoint de integração — 2026-10-28 00:44 BRT

- Contratos e frentes reais: domain, portal, api_mcp, admin_ops, pipeline, data_north, data_northeast, data_central_south, data_bncc_southeast e auditor independente.
- 227 fontes no inventário em crescimento, 27 UFs presentes; aquisição não equivale a cobertura reconciliada. PDFs/cache locais em data/raw e data/extracted (fora do Git, direitos não globalmente relicenciados).
- PostgreSQL principal dedicado localhost55437, container curriculos-abertos-db-1; banco alheio ContentiZAP na5432 preservado. .env0600 gerada sem exibir segredos.
- Piloto real ca-64e60bb2c92be368dcd7 importado,2108 itens SP; candidato, zero UFs prontas. Pipeline v1.2 reprocessa códigos LP/sufixos/itinerários e ingestão nacional, checkpoint var/jobs/national-extraction.json.
- Dois builds de produção locais executados; typecheck passa. npm test real12/12, zero skips, PostgreSQL descartável removido. Audit npm zero vulnerabilidades.
- API e MCP HTTP SDK testados parcialmente; gate exigindo BNCC/referências bloqueia êxito final. Browser E2E detectou encoded IDs e brand aria; corrigidos pelos autores, reteste após segundo build.
- Docker Engine operacional. Pulls DockerHub iniciais silenciosos foram encerrados pelo coordenador; DB usa digest oficial cached17.7. Node24 mirror ECR sendo testado por ops com fallback suportado Node22.23.3 cached. Nenhuma implantação remota autorizada/executada.
- Próximo: concluir ingestão+BNCC, importar snapshot nacional candidato, corrigir qualidade/reconciliação e partes obrigatórias; retestar jornadas reais. Depois build Compose limpo, restart, backup/restore isolado, performance10x200, revisão final e release-check bloqueante.

## Checkpoint de escala e qualidade — 2026-10-28 01:18 BRT

- Native batch v1.3 concluído231/231 fontes:55.948p,139.546 registros candidatos,1falha documentada. Esses números não comprovam completude/reconciliação. Pipelinev1.4 integra correções de orientação, células/continuação, códigos, OCRTSV e adaptadores reais semcódigo.
- Revisores documentais descobriram dados que não podem ser substituídos pelaBNCC: DF2.659 objetivos semcódigo, PR/SC/AC objetivos locais, RJ30direitosEI, PE8habilidadesIFA e BNCC>1.000nós de hierarquia/competências. Adaptadores em execução e autoriaautomatizada identificada.
- Publicação PostgreSQL principal atual ca-77fb8076598b567e1ba3:38.322itens,13.007relações,247fontes. Artefato gzip24.253.561B comSHA e decodedSHA237.695.811B validado; não é cobertura nacional pronta. Piloto anterior preservado.
- API e MCP completos sobre essa candidata passaram, incluindo HTTP+stdio e cincoexports integrais emstream; admin20checks passou com publicação temporária/revisãoautomatizada/rollback. Performance diagnóstica10clientes/200requests passou targets comzeroerros, corpus38k/hostNode25; final será repetido no ambiente produzido comcorpusfinal.
- Sharding obrigatório por escala: manifest pequeno+JSONL.gz partes comhash, DBrelacionalmetadataonly e exportstream; domain/pipeline/admin integram. Migrations001–005 já aplicadas no banco principal,006 pendente quando pronta.
- Novosruntimes oficiais ATUAIS arm64 Node22.23.4 ePostgres17.11 foram obtidos/verificadosSHAe dockerload/run pelo agente runtime_images, contornando somente endpointbuild/pull que não respondia por alternativaRegistrypública normal; semalterar daemon/contêineresalheios. Banco principal aindaPG17.7 atébackup/cutoverlocal.
- SegurançaPython encontrou CVEs reais em pinsantigos; runtime dispensará pypdf/pdfplumber e fixaPyMuPDF1.26.7 comPython3.11. Venvantigo não será tratado como distribuiçãosegura.
- Locknpm regenerado emcontextolimpo para depsopcionaisLinux; adicionarqualquerdependência pede regenerarsemnode_modules. packageManager11.6.2fixado. ÚltimoparserQA stream-json3.7.0 já incluído.
- FontesALComputação de blog comprocedênciapendente permanecem pesquisa privada/nãopublicáveis, requisito continua no denominador. CAPTCHA/artefatocorrompido/HTTPHTML/lacunasnormativas estãoem sourcesreports; parser/estrutura incompletos são trabalho interno, nãobloqueioexterno.
- Próximo: concluir v1.4+shards/import, consolidarestruturaportal, rebuildimagemcódigofinal, produçãoComposeisolada/restart/backuprestore, QA integral e auditor/gatebloqueante.

## Checkpoint operacional — 2026-10-28 02:06 BRT

- Build PADRÃO Docker Compose executado com sucesso, imagem técnica curriculos-abertos:local SHA69060a8a...; runtimearm64Node22.23.4/npm11.6.2/Python3.11.2/PyMuPDF1.26.7 verificado. EndpointsDockerbuild/pull deixaram de impedir execução após obtençãoRegistrypúblicoSHA+loadlocal. Imagemtécnica não é o código final.
- Backup lógico privado112MiB e restauração em volumeNOVO verificados com21tabelasduráveis+digests iguais. Cutoverprincipal dedicado55437 paraPG17.11Bookwormconcluído: collation2.36=actual, zeroíndicesinválidos. Oldvolumecurriculos-abertos_database e envrollback preservados. ContentiZAP5432 intacto.
- App/workerHOST foram parados comSIGTERM para cutover e continuamPARADOS aguardando buildcom008/009+adminingest. Não apresentar localhost3000 como ativo neste intervalo.
- Migrações001..009 aplicadas no principal.008corrige exposição de preparação: lifecycleprivado/público fora snapshotimutável, serviços públicos404para prepared, publicação atomizada/históricoretido.39/39testes reais/contratos passaram antesaplicação.009normaliza espaços nos códigos sópara busca.
- Nova integração obrigatória identificada: jobingest deve importar candidatoPREPARED do seucheckpoint específico e permitirinspeção/validação/publicaçãoadmin semcorreçãofictícia; opsimplementa. Rollback deve apenas alternarversõesjápublicadas.
- ArtefatoSHARDED técnico ca-9d9b45e82947bd8fe35c entregue e inspecionadointegralmente:20.612itens/2.851relações/7partes,117.288.380Bdecoded, zeroerros/hashesconferidos; candidatoPARCIAL. DefaultDB permanececa-77fb...38.322itenspara evitar regressãodecobertura.
- Nativev1.4+OCR/layoutfixes seguem em var/pipeline-national-v14.log e docs/data-progress.md. OCRNorte2.157páginas executado; transcrição/colunasAM ainda sendo corrigidas, semconfundirzeroerrodeexecuçãocomreconciliação.
- Sidecars integrais reais:AC2.191;PR3.971;DF2.659;RSEM121;BR1.186nós+1.721skills;SC EPT/Magistério6.314 emintegração, SC C3 emextração. FonteSPII2026anexos eRN DCEC819padquiridosnovamentecomproveniênciaprimária.
- Git checkpoint4f7056ca581b03dfd91bd8e0ca817f4196f5553e. Alteraçõesposteriores permanecem naárvore; arquivosgeradospycache removidos apenasdoíndice e agoraignorados, originais/cacheslocais preservados.
- Próximo: fecharadminingest e correçõesv1.4; importar artefatofinalpreparado; buildincremental exato; iniciarapp/worker; executar QAprivacidade/API/MCP/browseradmin/public, instalaçãoComposeisolada+persistência+backuprestore+desempenho; auditar/gate. MVPnacionalcontinua não concluído.

## Retomada e integração — 2026-10-28 10:47 BRT

O limite de uso interrompeu os agentes; o usuário informou o reset e autorizou a continuação. Todas as frentes essenciais foram reativadas com seus contratos e arquivos existentes. Não foi reiniciado o projeto nem descartado trabalho.

- Serviços Compose permaneceram ativos: app/worker saudáveis em localhost:3000, banco principal PG17.11 em55437, default `ca-77fb8076598b567e1ba3`. Serviço ContentiZAP5432 preservado.
- Nova imagem técnica `sha256:acd1b70caff6453a0f5ba465ac97a9fcca29a73c1a90746a69409ede8adbb335` construída normalmente. Fingerprint da imagem e host coincidiu no build; pipeline ainda receberá correções, logo a imagem não é a distribuição final.
- Administração em navegador real PASSOU desktop/mobile após corrigir foco das regiões roláveis. AXE sem violações; login/erro/logout, fonte/registro com publicação fixa, rascunho de redação idêntica validado uma vez, contribuição e autoria automatizada conferidos. Conta temporária e sessões removidas. Evidências: `admin-browser-verification.json`, `admin-browser-scroll-fix.log`. Execução final via wrapper do gate ainda pendente.
- Domínio concluiu48/48 testes reais sem skips; migração010 de busca por palavras quebradas aplicada ao principal. Textos originais e compostos legítimos preservados. Latência transitória de14s em consulta individual está em investigação, sem atribuição causal não provada.
- Ops26checks de autenticação/autorização e lifecycle privado/público passaram. Fluxo J11 real foi interrompido pelo verificador de evidência PR; reparo preserva3971 IDs/textos e troca somente uma evidência ampla por7spans originais. Reteste do job em execução, com pausa/restart/retomada/publish/rollback.
- UI agora preserva parent_id ao reaplicar filtros e exportar; área é filtro explícito. Suíte pública inclui navegação nas27UFs e hierarquia sem código, sem skips. Publicação antiga ainda falha por AM sem registros e BR sem hierarquia; não remover esses critérios para obter verde.
- Pipeline consolida artefato sharded integral após GO/MT/AM/PR e sidecars. PB1983registros, DF3065 e SC novas hierarquias/objetivos em verificação/incorporação; complementos PE atuais estão em aquisição/inventário legítimos. Nada disso é automaticamente UF pronta.
- Auditor exige schema_path+schema_sha256 e provas finais de18tipos. Sequência de distribuição isolada: qa-production → qa-reimport (downloads reais+DB descartável) → qa-recovery. Nenhuma dessas provas finais foi substituída por descrição ou existência de script.
- Dados obrigatórios ausentes e reconciliações internas continuam impedindo ACE-01/02. Gate anterior reprovou corretamente e caso negativo controlado passou. Próximo: artefato consolidado, inspeção integral, publicação administrativa e todas as jornadas/gates sobre a mesma versão e código.
