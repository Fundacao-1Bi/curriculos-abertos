# Consolidação dos experimentos — 01/11/2026

Inventário documental de retomada, sem extração, build, exportação, alteração de
ponteiros ou promoção. Esta designação organiza o trabalho futuro; não concede
aceite nacional nem autoriza remover os artefatos relacionados.

Atualização operacional: a aposentadoria dos cinco QAs históricos foi depois
autorizada e executada, preservando os artefatos do host e pequenos pacotes de
curadoria/jobs/históricos. Permanecem principal e QA `a3f8cd`; não recriar os
QAs aposentados só para continuar as frentes. Ver
[storage-consolidation-20261101.md](storage-consolidation-20261101.md) para
identidades, recibos, capacidade e limites de retomada. As referências a bancos
históricos abaixo são contexto, não promessa de bancos ainda disponíveis.

## Estado que deve orientar a retomada

| Papel | Identidade e prova | Decisão de retenção |
| --- | --- | --- |
| Base publicada no filesystem | `data/bundles/latest.json` aponta para `ca-7d302a9c674a97b83278`; manifesto SHA `be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d`; 303 fontes, 200.724 itens, 57.425 relações, 75 shards | Preservar ponteiro, manifesto, checksum e todos os shards |
| Candidato de continuação designado | `data/bundles/ca-41c0553542d47d558786.manifest.json`, SHA `23e96c1871d109c424a1f279ad30ad465bce82a6bcf0d9e1ae85d3e77ffff850`; 303 fontes, 207.285 itens, 57.423 relações, 75 shards | Preservar como candidato privado; concentrar a próxima integração nesta identidade |
| QA registrado | `var/qa-clean-state.json`: projeto `curriculos-abertos-clean-20261101045455-a3f8cd`, publicação `ca-7d302a9c674a97b83278` | Preservar até correlacionar containers, montagens, fingerprint, banco e evidências atuais |
| Publicações históricas/runtime | Checkpoint registra `ca-77fb8076598b567e1ba3` e `ca-297c7ec9ab33fcaae579` em ambientes anteriores | Não presumir que ficaram dispensáveis porque o `latest` é outro; conferir diretamente os bancos e leitores |

Os bytes de `latest.json` foram conferidos nesta auditoria: SHA
`dfc9e7b208d2dc0a814d3484900baf6b3f7937ffe514539c9370fb52be1881bd`.
O candidato designado tem 192.194.416 bytes comprimidos de shards e manifesto
de 17.256.945 bytes; os shards decodificados representam 1.418.763.143 bytes.
Esses tamanhos lógicos não representam espaço físico recuperável em APFS.

O gate ativo em `docs/evidence/data-release-check.json`, SHA
`d55223c9aa845fce84c10c678d9c4ea06aa48126be8bbd68a5e7bae309855301`,
registra 11/567 escopos, 0/27 UFs e 326 erros ING-03. A avaliação persistida do
candidato após RR, em
`docs/evidence/source-audit-rr-integral-38-2025/candidate-release-check-installed.json`,
registra 19/567 escopos, 0/27 UFs e 264 erros ING-03. Esta última avaliação
antecede a instalação dos três recibos DF/SC; não inferir seu resultado atual
por subtração. Nenhum dos dois artefatos está aprovado nacionalmente.

## Linhagem operacional comprovada

Os dez alvos da composição SP/AC/ES/PI são `ac-cru-ei-ef`, `ac-cru-em`,
`es-resolucao-cee-es-no-5-190-2018-ei-e-ef`,
`es-resolucao-cee-es-no-5-777-2020-ensino-medio`, `pi-parecer-190-2025`,
`sp-curriculo-eief-isbn`, `sp-curriculo-em-isbn`,
`sp-educacao-digital-midiatica-2026`, `sp-seduc156-anexos-matrizes-2026` e
`sp-seduc156-corpo-2026`. O candidato designado conserva essa composição,
a correção visual AM e a incorporação RJ com remoção de uma célula duplicada.
O manifesto contém a proveniência dos dez alvos e o recibo adicional RJ
`ca-3d0a6456792bc046900e`; o changelog identifica a correção de dois itens AM.

| Origem | Sucessor | Evidência da transformação |
| --- | --- | --- |
| `ca-44350ccb5a3d8b75f72d` | `ca-b57fa07a470476258cad` | `docs/evidence/source-audit-rj-humanas-20261101/full-candidate-composition-v2.json`: recibo RJ, 21→20 itens da fonte e substituição de 10 relações; `latest` preservado |
| `ca-b57fa07a470476258cad` | `ca-8fe878d6db7c6c13b0b0` | `docs/evidence/source-audit-ms-pv/corrected-stage-banner-candidate-20261101.json`: correção MS e recomposição pelo finalizador |
| `ca-8fe878d6db7c6c13b0b0` | `ca-f77d4a0ed3e79d81af09` | `docs/evidence/source-audit-ms-pv/page38-39-candidate-bundle-20261101.json`: callout p.38 e texto p.39 |
| `ca-f77d4a0ed3e79d81af09` | `ca-093f46c859f50bddff90` | `docs/evidence/source-audit-ms-pv/page15-candidate-bundle-20261101.json`: registro da figura p.15 |
| `ca-093f46c859f50bddff90` | `ca-4af153161499294faa75` | `docs/evidence/source-audit-ms-pv/page24-reuse-candidate-20261101.json`: contexto do reuso da figura p.24 |
| `ca-4af153161499294faa75` | `ca-41c0553542d47d558786` | `docs/evidence/source-audit-ms-pv/page41-candidate-20261101.json`: substituição da seção genérica p.41, contexto da figura e autoridade de extração |

Os predecessores da cadeia estão superados como ponto de continuação desta
frente. Isso não prova que os arquivos físicos possam ser apagados: scripts,
recibos, bancos e falhas preservadas podem apontar para suas identidades.

**Não reconstruir essa cadeia apenas por `parent_publication`.** Os manifests
MS examinados mantêm `parent_publication=ca-8c034fb288e05d37f57f` mesmo quando
os relatórios `base_candidate` mostram derivações sucessivas. A linhagem acima
usa os relatórios específicos. Há ainda tentativas fora da cadeia: por exemplo,
`full-candidate-composition.json` registra `ca-8b69d435711e540da86b` com o recibo
RJ anterior `ca-b9669ecc15effa2e5b31`, enquanto a versão v2 registra `ca-b57…`.
Não tratar essas identidades como equivalentes sem comparar conteúdo.

## O que falta consolidar no candidato designado

| Frente | Fato verificado | Próxima ação limitada |
| --- | --- | --- |
| TO-EI | O recibo instalado em `data/manifests/reconciliation/to-dct-ei.json` foi validado para 459 itens/8 partes; a prova está em `docs/evidence/source-audit-to/whole-source-candidate-host-runtime-20261101/receipt-installation-report.json`. O candidato já contém cinco coberturas TO-EI com `ready/reconciled=true`, mas seu `source_reconciliation` embutido ainda registra `receipt_source_artifact_or_revision_mismatch` | Reavaliar recibo, cache e todos os IDs/campos do candidato. Distinguir metadados embutidos históricos do gate externo atual; não reextrair ou gerar outro FULL para atualizar só o relatório |
| RR 38/2025 | Recibo `data/manifests/reconciliation/rr-integral-38-2025.json` instalado para 9 itens/9 páginas. `docs/evidence/source-audit-rr-integral-38-2025/installation-report.json` e `candidate-release-check-installed.json` comprovam instalação e avaliação. O manifesto imutável conserva um relatório anterior de mismatch | Herdar o recibo ativo na próxima avaliação do candidato, sem reescrever o manifesto. Não confundir resolução normativa com cobertura curricular ou vigência atual |
| DF vol.2/3 e SC Inglês AI | `docs/evidence/source-audit-rr-integral-38-2025/next-receipt-installation-report.json` comprova recibos atuais instalados, caches/sidecars conferidos, SourceWhole, controles negativos e binding documental ao **bundle ativo** | Revalidar binding no candidato designado, preservando resultados ativos; não instalar indiscriminadamente um overlay completo. Os 74/137/24 `parent_id` divergentes foram expressamente excluídos do escopo documental e exigem gate de hierarquia separado |
| MS Projeto de Vida | O candidato p.41 incorpora os avanços das pp.15/24/38/39/41 e título p.50. `ms2024-p30-infographic-role-proof-20261101.json` classifica a infografia externa, sem transcrever microtexto ilegível | Fechar inventário independente e reconciliação integral. O piso 737 segue provisório; o recibo anterior de 681 registros não prova a fonte completa. Não reemitir pins só para reduzir erros |
| PI 188/190, AP e AC | Checkpoint e `active-with-candidate-overlay-diagnostic.json` documentam dependência PI sem prova atual e bindings inválidos RJ/MS quando se tenta instalar o overlay completo. Inventário oficial AP/AC está em `docs/evidence/source-audit-northeast/ap-ac-dependency-official-web-inventory-20261101.md` | Resolver dependências/documentos específicos. Não transformar ausência de arquivo oficial em prontidão ou remover a obrigação |

O gate externo deve ser executado contra o mesmo hash do candidato e um conjunto
de recibos explicitamente identificado. Aprovação documental da fonte,
integridade do bundle, aceitação de software, revisão pedagógica e promoção
continuam sendo fatos separados.

## Preservação necessária antes de reduzir experimentos

Preservar `data/raw`, os manifests e sidecars em `data/manifests`, esquemas
pinados em `data/schema`, os caches referidos pelos recibos e os binários
originais/evidências visuais. Muitos desses caminhos estão fora do Git.
`data/extracted` histórico não é descartável só por carregar versão antiga:
primeiro resolver leitores, fingerprints e dependências por hash.

Preservar os dois bundles designados completos, manifests/checksums de todos
os predecessores, relatórios da cadeia e os recibos/provas/overlays relevantes
em `docs/evidence/source-audit-ms-pv`,
`docs/evidence/source-audit-rj-humanas-20261101`,
`docs/evidence/source-audit-am-85-2021`,
`docs/evidence/source-audit-to`,
`docs/evidence/source-audit-rr-integral-38-2025` e
`docs/evidence/source-audit-ing03-runtime-refresh-20261101`.

Preservar proveniência referenciada no próprio candidato, especialmente
`var/jobs/sp-ac-es-pi190-acem-10-source-current-reissue-20261031/technical-evaluation.json`
e seu diretório `receipts`. Preservar o recibo bruto
`data/bundles/ca-e30b13fd827f056f79a0.manifest.json` e seus shards enquanto
a proveniência depender dele. Scripts de reprodução também fixam predecessores:
`docs/evidence/source-audit-rj-humanas-20261101/compose_full_candidate.py`,
`build_ms_runtime_overlay.py` e
`docs/evidence/source-audit-am-85-2021/compose_ten_source_to_ei_am_visual_candidate.py`.
Remover o artefato pinado sem adaptar/registrar o fluxo quebra reprodução.

Backups em `var/backups`, evidências de restore, export de rollback mencionado
no checkpoint, imagens e volumes Docker ficam retidos até avaliação específica.
Também há preimages fora do repositório em
`/var/folders/f5/wl08x13j71g9fwy5tgshcdwh0000gp/T/curriculos-receipts-preimage-91nbomdh`;
o relatório de instalação identifica seu papel. Esta auditoria não atesta a
integridade nem o uso corrente desses recursos e não autoriza removê-los.

## Regra para as próximas iterações

1. Usar a base ativa e o candidato designado como referências explícitas;
   registrar responsável, hash de código/inputs, fonte-alvo e resultado esperado
   antes de abrir uma experiência.
2. Alterações de recibo/gate devem produzir relatórios pequenos contra artefatos
   imutáveis existentes. Não gerar corpus, exportação ou banco integral para
   atualizar apenas avaliação documental.
3. Validar alteração de fonte em um recibo/delta limitado, com schema, IDs,
   texto, evidência, hierarquia e controles negativos apropriados. Usar os
   parâmetros incrementais existentes de `pipeline/ingest.py`; preservar pins
   de base e fonte-alvo.
4. Acumular deltas validados e realizar uma única composição global por rodada.
   Registrar a lista completa de deltas incorporados, diferenças fora do alvo,
   sucessor designado e quais predecessores perderam utilidade operacional.
5. Manter um QA nacional por rodada. Reuso exige fingerprint e isolamento
   compatíveis; uma falha tem dono e retenção explícitos. Antes de build,
   extração, exportação ou restore, cumprir inventário/preflight/capacidade do
   `AGENTS.md` e estimar arquivos simultâneos, banco e WAL.
6. Encerrar cada rodada com recibo de retenção/limpeza. Em sucesso, usar a
   limpeza própria da execução. Para recursos antigos, listar paths/IDs,
   tamanhos, hashes duplicados ou reprodução comprovada e impacto sobre retomada,
   rollback e evidência; conferir processos, `lsof`, Docker e montagens
   imediatamente antes de qualquer remoção. Falha em uma conferência retém o
   recurso.

Esta consolidação documental não executou nova publicação, comparação completa
dos 207 mil registros, QA nacional ou remoção. A cadeia está comprovada pelos
relatórios versionados e hashes de manifestos; a autorização de limpeza física
depende do inventário operacional e da lista exata apresentada pelo integrador.
