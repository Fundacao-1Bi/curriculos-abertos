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
