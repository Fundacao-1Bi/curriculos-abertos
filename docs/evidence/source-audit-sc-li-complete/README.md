# Língua Inglesa dos Anos Iniciais de Santa Catarina — conferência integral

Verificação documental automatizada por `agent:data_central_south`, com inspeção dos renders reais. Fonte original de 31 páginas: SHA256 `3d9c5785a8ab77e944d4ceb3377a0465978d8e92a42bcaa06ea3cd47dfbad2c0`. A capa confirma edição 2026; nenhuma vigência foi inventada.

O inventário das páginas e células originais precedeu a leitura dos adaptadores e caches: 78 células, 143 parágrafos de habilidades, seis competências específicas numeradas, cinco definições de eixos, 25 ocorrências de eixos e 141 chaves estruturais derivadas dos cabeçalhos/células e da gramática pública das chaves. Os IDs esperados não foram copiados da extração para declarar cobertura.

O adaptador final `data/manifests/uncoded/sc-li-ai-complete-items.json` contém 338 registros, SHA256 `c5174064be009c797ec13334ff07894b552eac421f89184c7df9ff851701f904`. Com as 24 seções de página do extrator real, são **362 registros esperados, importados, finalizados e verificados**, sem pais ausentes ou IDs extras. Todas as 143 folhas anteriores preservam ID, texto, código ausente, posições, evidências e contexto. Novos vínculos de hierarquia usam apenas capítulos, anos e eixos impressos.

Todas as páginas de texto integral tiveram contagem de palavras e ordem literal confrontadas com a fonte. Uma segunda varredura, sem recorte horizontal das células, conferiu os blocos nativos completos dos 143 parágrafos: nenhuma palavra omitida, nenhum texto invisível e nenhum `/ActualText` no corpo. As imagens ocorrem somente na capa, página de rosto e contracapa, inspecionadas por render. As páginas 2, 8, 10 e 30 são brancas; 31 tem apenas grafismo e recebeu OCR efetivo, sem aprendizagem textual.

A camada textual da capa termina incorretamente em “Anos Inici”. OCR real do raster recuperou o título completo visível, confrontado com o render e a página de rosto. O arquivo `data/manifests/uncoded/proofs/sc-li-cover-ocr.json` vincula raster, configuração, versão, resultado e artefato original. O texto nativo defeituoso foi preservado no contexto da fonte; não se completou a palavra por dicionário.

Evidências principais:

- `independent-source-inventory.json`: inventário anterior à importação.
- `full-verification.json`: 362/362 e provas por página/campo.
- `full-block-and-visibility-verification.json`: segundo censo integral dos blocos e visibilidade.
- `idempotence.json`: reexecução com bytes idênticos.
- `native-empty-pages-render.png` e `../source-audit-sc/li-ai-whole-document-preamble.png`: renders conferidos.
- `../../../data/manifests/reconciliation/sc-lingua-inglesa-ai.json`: sidecar de reconciliação da parte documental inteira.

Reproduzir a partir da raiz do repositório, com os PDFs oficiais já adquiridos:

```sh
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python docs/evidence/source-audit-sc-li-complete/complete_sc_li.py
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python docs/evidence/source-audit-sc-li-complete/verify_reconcile_sc_li.py
```

Os verificadores interceptam as escritas do cache de extração nacional para não substituí-lo por um probe. A incorporação ao cache/bundle nacional final cabe à execução integrada do pipeline. O fechamento é documental e automatizado: não equivale a revisão pedagógica humana nem prontidão da UF inteira.

O gate `reconciliation-gate/2.0` também passou na revisão `page-cell-v1.5.0`: 362/362 registros contabilizados pela união exata de quatro unidades (143 habilidades, seis competências específicas, 172 estruturas e 41 contextos). Cada hash UTF-8 corresponde a texto esperado construído diretamente dos blocos/células/páginas nativas ou do OCR primário, antes da extração. A igualdade exata é exigida antes de vincular o hash; hashear a saída extraída por si não serve como prova. O recibo e relatório antigos1.4 foram preservados em `../source-audit-central-south/legacy-reconciliation-v1.4/`.

Refresh do recibo ativo em 2026-10-31: `verify_reconcile_sc_li.py` foi reexecutado com a revisão corrente; passou 362/362, 31/31 páginas, `findings=[]`, sem falhas literais nem pais não resolvidos. O writer do cache foi interceptado e a SHA da cache permaneceu `15fbded49c600467990dff6a34964fac0c786de83f135dabb508158e1c650c34`. O recibo ativo agora inclui `v2_gate_result` e pins atuais da cache, configuração, fingerprint, runtime e adapter; a validação do pin no release checker passou. O recibo e relatórios substituídos estão preservados em `prior-active-refresh-20261031/`; o resumo da instalação está em `receipt-refresh-installation.json`. Isso prova reconciliação documental automatizada da fonte, não prontidão da UF nem incorporação em produção.
