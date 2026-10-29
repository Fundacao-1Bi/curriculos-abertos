# Norte: estado documental e integração

As revisões são automatizadas, com autoria e evidências identificadas. Aquisição, extração, reconciliação por parte, aceite de UF e incorporação em produção são estados distintos.

O quadro atual reproduzível está em `docs/evidence/north-current-source-state.json`: 16 sidecars vinculados, 12.910 registros documentais. Esse número inclui estruturas e contextos; não é uma contagem de aprendizagens nem comprovação de cobertura nacional.

## Reconciliação integral do artefato

`ro-rcro-ei`: OwnSourceV2 e fechamento de dependências declaradas passaram no gate real. Foram conferidos 773 registros, 173 páginas, 18 partes, 3.747 blocos, 246.117 caracteres curriculares/contextuais e 4.251 fragmentos. Doze blocos de créditos/overlays/footer da página5 têm exclusão não curricular explícita; a abertura normativa permanece integral. O receipt está em `data/manifests/reconciliation/ro-rcro-ei.json`.

Os atos `ac-computacao-667-2025` e `ap-plano-em-001-2026` passaram OwnSourceV2 nos recortes próprios, com 12 e16 registros. O fechamento das dependências permanece pendente: o ato não substitui o currículo digital do Acre nem o corpo/tabelas do Plano de Ação do Amapá. A aprovação em2026 não foi transformada em edição2026 do Plano. Receipts e gate atual: `docs/evidence/north-current-own-source-v2-verification.json`.

## Partes verificadas e vinculadas

| Fonte/parte | Registros e escopo |
|---|---|
| AC EI/EF | 2.191 registros do adapter previamente verificado; não declarar UF por esse recorte |
| AC EM PV/Pós-Médio | 158:146objetivos sem código,6competências próprias e6seções; corpo/anexo preservados por ocorrência |
| AP614 | 2.441:93objetivosEI,465experiências,1.633habilidadesEF e direitos/competências/estrutura; microfaixas documentais preservadas |
| PA361 | 4.027:base1.972 preservada e2.055definições próprias de HabilidadesEF; autoridade disjunta EI73–88/EF112–323 |
| RR EI | 346:90objetivos,60experiências,90abordagens,90orientações,15campos/faixas e1legenda documental |
| TO EI | 359:93objetivos,93detalhamentos,93sugestões,30direitos completos,30rótulos de contexto,5campos e15faixas |
| RO EF | 429:149Espanhol preservados,100competências e organizadoresER; outras partes continuam pendentes |
| RO EM | 620 registros do recorte120–236 e156relações documentais internas; sem equivalência/pré-requisito |
| RO Eletivas | 915 registros de campos/objetivos/habilidades/competências; objetos/eixos/rubricas restantes pendentes |
| RO Educação Digital EI | 168 registros; escopo correto EI/EF, com clipping/XObjects e outras partes explicitamente pendentes |
| RO atos | 42/32/381 registros nativos; matrizes/regiões raster11/1/12 ainda não reconciliadas |

Os registros de direitos/rótulos, competências, objetos, detalhamentos, orientações, finalidades e normas mantêm seus papéis. Não se transformam todos em habilidades. Códigos originais irregulares permanecem literais, inclusive `E103ET04`, `EI01ET01` no contexto diverso e variantes `LE`/`C1`; não foram criados aliases nacionais por suposição.

Os snapshots RR/TO anteriores foram preservados. TOv3 documenta30correções de tipo rótulo e30novas definições, com IDs/textos/códigos/pais anteriores mantidos. As posições mensais desses recortes vêm de cabeçalhos físicos e incluem Evidence[]. PB635/PB392 congelados permanecem intactos; seus refreshes de idade são assunto separado.

## Reprodução e integração

Use `var/venv-pipeline/bin/python`. Os originais privados são necessários.

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/ac-em-pv-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/rr-ei-organizers-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/to-ei-rights-v3-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/north-normative-acts-extract.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/reconcile_ei_whole_source.py
var/venv-pipeline/bin/python docs/evidence/source-audit-north-norms/write-current-whole-source-receipts.py
```

O aplicador `docs/evidence/north-apply-proposal.py` valida hash do PDF/sidecar, loader/finalizer/schema, hierarquia, texto/código/posições/ordem e parser estável antes da gravação serial. Recusa propostas `binding_ready:false` e regressões silenciosas de identidades. Não executa o parser global. Os receipts só podem ser produzidos contra cache/config/runtime atuais; não se reescrevem fingerprints para aparentar compatibilidade.

AM permanece com provas próprias de posição/capítulos, não de corpo textual integral. O peer de corpo é uma frente separada. Os92PNGs primários AM e79PNGs CEDOC foram movidos sem perda para `var/private-evidence`, com inventários old/new/SHA. Os dois crops ligados ao snapshot PB continuam no lugar por decisão do coordenador. AP também possui inventário próprio de imagens privadas.

Nenhum resultado desta página comprova vigência atual, revisão pedagógica humana, UF integral ou produção. O quadro de pendências distingue trabalho interno, refresh técnico e falhas externas concretamente observadas.
