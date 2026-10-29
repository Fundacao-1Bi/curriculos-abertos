# Revisão de aceite — estado observado, não release final

Revisão automatizada de domínio em 28/10/2026. Evidência reproduzível e somente leitura: `docs/evidence/domain-acceptance-review/inspect.py` e `observed-state.json` (18:32 UTC). A revisão não executou novamente release-check, extração, build, benchmark, Docker ou mutações no banco. Fonte normativa dos critérios: `docs/requirements.md`; há 55 IDs, preservados no relatório estruturado complementar. Esta revisão não substitui o auditor final nem promove a matriz oficial a verde.

## Resultado

**ACE-01/ACE-02 continuam não satisfeitos.** O serviço público está saudável, mas não entrega ainda a publicação nacional consolidada/reconciliada. Não há motivo para parar o trabalho independente: há fontes acessíveis com extração concluída, recibos de pares a integrar, inventários a fechar e preparação de verificações finais que podem avançar em paralelo.

| Observação diretamente conferida | Consequência de aceite |
| --- | --- |
| `/api/ready`200, banco/worker OK e padrão ca77; catálogo público com 38.322 itens, 13.007 relações, 247 fontes | Funcionamento do runtime e preservação da versão anterior comprovados nessa consulta; não comprova cobertura, código final servido ou instalação final. |
| `/api/v1/ufs`: 27 entradas, **zero ready**, AM/MA/PB/RR sem itens nessa publicação | O catálogo não equivale a cobertura nacional. Dados novos dessas frentes podem existir fora da publicação; não se deve recoletar trabalho já concluído só porque ainda não foi integrado. |
| `latest.json` aponta ca09, 20.612 itens/2.851 relações, `national_release_ready=false`; coverage-manifest também é antigo/ca09 | Artefato de instalação e padrão HTTP são candidatos parciais distintos, explicitamente conhecidos. A entrega final deve selecionar uma publicação consolidada e conferir o mesmo ID/SHA em bootstrap, runtime e evidências. Nenhuma promoção foi feita nesta auditoria. |
| Catálogo atual:303 fontes,295 `acquired`,5 `unavailable`,3 `research_pending` | Status de obtenção não prova processamento, completude nem obrigatoriedade. A contagem197 de flags obrigatórias explícitas não substitui o inventário curricular esperado. |
| FULL1.5:286 resultados,285 extraídos/1 falha AP EM; refresh29/29 concluído | Execução real avançou. Os155.620 candidatos FULL e26.357 do refresh **não são aditivos** nem denominador de completude; o refresh substitui resultados. Falta verificar deriva posterior da configuração e consolidar o artefato atual. |
| Há12 arquivos em `data/manifests/reconciliation/`, incluindo partes e revisões antigas | Não são12 fontes prontas. Cada recibo precisa corresponder a Source, hash/configuração/runtime atuais, fechar partes obrigatórias e demonstrar inventário original; pares completos em docs ainda precisam de vinculação verificável. |
| `docs/evidence/executions/` não existe; relatórios oficiais de release disponíveis são antigos e reprovados | Não há registro dos wrappers finais com código/publicação atuais. Diagnósticos91/91 ou puros9/9 não aprovam J01–J12, performance, produção/reimport/restore ou lançamento nacional. |

A API foi consultada sem conta. As observações de HTTP e filesystem têm horário/hash próprios no JSON. Não se inferiu que a árvore atual está servida pela imagem antiga nem que todas as implementações em arquivo foram verificadas nesta rodada.

## Critérios e estado

| IDs | Estado que a evidência permite afirmar | Falta determinante |
| --- | --- | --- |
| ESC-01/02, ING-01..05, ACE-01/02 | Em execução; nacional não aprovado | Conjunto obrigatório integral por UF/etapa/componente/edição, reconciliação documental e publicação integrada. |
| DAT-01..05, ARQ-01..03 | Modelo/serviços/contratos presentes e verificações diagnósticas registradas | Repetir no código/dados finais; conferir coerência Source/posições/hierarquia/relações/versões nos registros reais e transportes. |
| FUN-01..12, API-01/02, MCP-01..03 | Implementações e ensaios anteriores existem; runtime responde | Jornadas integrais sobre publicação consolidada e código/imagem observados, sem filtros/skips e sem tratar amostra como cobertura. |
| ADM-01..03, SEG-01/02 | Controles e ensaios anteriores presentes | Novo J11 HTTP/worker com base pinada, pausa/restart/replay idempotente, preservação global, CAS negativo, publicação/rollback e privacidade de preparados; ensaios finais de acesso/abuso. |
| OPS-01..04 | Distribuição e recuperação anteriores executadas; runtime atual saudável | Instalação limpa, validação da imagem real, publicação nacional importada, reinício e recuperação do estado final, artefatos preservados. Remoto não foi autorizado; isso não impede a distribuição local de produção. |
| QA-01..05, ACE-03/04 | Testes/gates existem e falsos verdes foram bloqueados | Executar wrappers finais e gerar matriz de evidências atual; conservar bloqueios externos distintos de trabalho interno. |
| ESC-03/04/05, ORQ-01/02 | Funcionalidades/escopo aberto e coordenação real documentados | Integração final e documentação correspondente ao estado entregue; não reintroduzir diagnóstico de acervo, requisitos opcionais ou identidade institucional inventada. |

As linhas individuais dos55requisitos, evidências e próximos testes estão em `docs/evidence/domain-acceptance-review/requirements.json`. São uma revisão complementar, não resultados fabricados de execução.

## Frentes independentes prioritárias

| Ordem | Frente e responsável sugerido | Trabalho independente concreto | Critério objetivo de fechamento |
| --- | --- | --- | --- |
| 1 | Reconciliação por fonte — auditor/pares distintos dos autores, com donos regionais | Criar um ledger por Source/parte/edição que una inventário original, IDs esperados/verificados, hashes de fonte/configuração, runtime e recibos existentes. Começar pelos peers completos já executados; não aguardar todas as extrações nem derivar denominador dos candidatos. | Cada parte obrigatória tem prova original e hashes compatíveis; partes não fechadas permanecem abertas. SourceWhole só quando todas estão fechadas. Isso reduz a principal lacuna ACE-01. |
| 2 | Atualização incremental e empacotamento — pipeline, integração sequencial | Confrontar o FULL+refresh com todos os bindings/sidecars posteriores, reprocessar só configurações divergentes e gerar manifesto global sharded com validação de todas as partes/schema/referências. Não somar FULL+refresh nem sobrescrever artefatos antigos. | Snapshot identificado e verificável; nenhuma fonte-alvo/publicação parcial substitui o conjunto; instalador aponta o mesmo artefato entregue. Reconciliação editorial segue separada. |
| 3 | Fontes ainda indisponíveis — pesquisa oficial por donos regionais | Continuar obtenção legítima de AP EM íntegro/PB EM e localizar documentos integrais explicitamente aprovados (MA digital, MS2023, BA2026/PE ato), preservando a incerteza de edição/vigência e a tipologia. Distinguir alternativas já adquiridas de links históricos opcionais. | Artefato íntegro com procedência e escopo comprovados, ou tentativa/alternativa/bloqueio/intervenção mínima documentados. Não travar fontes acessíveis por esses casos. |
| 4 | Recuperação/capacidade de build — operações, sem reinício global adicional | Preparar espaço para guard de15GiB usando somente derivados próprios sem escritores, compressão/GC dirigido reversível e inventário. Verificar imagem pós-build antes de up; preservar volumes, raw, rollback e outros projetos. | Guard e verificação da imagem passam sobre imagem íntegra; nenhuma exclusão de original/volume nem falso sucesso de build. A tarefa pode avançar enquanto pares documentais trabalham. |
| 5 | QA integrado — API/MCP/portal/admin/auditor, em instalação descartável | Preparar seleção estratificada de registros reais por27UF/etapa/componente e cenários many-to-many, idades/blocos, códigos sem normalização canônica, fontes distintas, preparado privado, contribuição e J11. Fixar um único publication/code/image. | J01–J12, API+MCPclienteHTTP/stdio, browser integral desktop/mobile, admin, exports/reimport e oracle independente com resultados/artefatos reais e zero skips. Execução final depende da candidata, a preparação não. |
| 6 | Sequência operacional final — operações/auditor | Executar `qa-production`→`qa-reimport`→`qa-recovery`; repetir persistência/backup/restore/publicação/rollback. Depois benchmark10clientes/200requisições sobre corpus real sem OCR simultâneo, incluindo ID/código, busca/panorama e comparação3UF. | Mesmo código/imagem/publicação nas provas; metas originais preservadas, warm/cold separados, zero erros válidos. Não usar resultado de38khostcomo aceite final. |
| 7 | Matriz e pacote final — coordenador/auditor | Gerar wrappers de execução e novo release-check com negativo controlado; atualizar coverage/report/README com o estado efetivamente entregue. | As55linhas obrigatórias têm evidência atual; gate aprova somente quando27UF satisfazem ACE-01. Se não, registrar requisitos abertos sem renomeá-los como opcionais. |

Frentes1/3/4 e preparação5 são paralelas;2 precisa de integração sequencial dos bindings;6/7 dependem da publicação/código congelados. Não criar nova plataforma de IA, diagnósticos de acervo, Kubernetes ou certificação CASE: nada disso resolve os bloqueios atuais de aceite.

## Bloqueio externo versus trabalho interno

O PDF AP EM tem falha real de árvore de páginas no ensaio atual; o catálogo PB EM registra dificuldade de aquisição apesar de renderização no navegador. Outros documentos integrais explicitamente aprovados continuam por localizar. Já extração de fontes acessíveis, fechamento de inventário, reconciliação, binding, tipo documental, publicação, build e ensaios finais são tarefas internas; não devem ser apresentados como impedimento externo. Fontes históricas opcionais com404/TLS não substituem a avaliação da fonte obrigatória atual.

A fila de trabalho não é condição de encerramento do produto. A coordenação deve continuar distribuindo pares e fechando os contratos acima enquanto cada frente puder avançar.
