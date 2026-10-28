# Rondônia: processamento documental em andamento

Esta frente possui somente os novos sidecars `data/manifests/uncoded/ro-*` e as evidências deste diretório. O manifesto `north.json` é integrado serialmente por `data_north`; não foi editado por esta frente. Nenhum banco ou contêiner foi usado. Runtime: `var/venv-pipeline/bin/python`, Python 3.11.15 / PyMuPDF 1.26.7; contratos reais `source_uncoded_items`, `finalize_items` e schema 1.1.0.

## Escopo e censo

`physical-census.json` abre integralmente as oito fontes, verifica os hashes e enumera 2.060 páginas: EI173, EF591, EM860, Eletivas119, Educação Digital267 e atos de matrizes/itinerários11+13+26. Aquisição, menção de código e seção de página não são usados como prova de currículo completo. Todos os estados de conclusão continuam `ready:false` / `reconciled:false`.

## Entregas verificadas

- EI: `ro-ei-complete-primary.json`, SHA `614d26c2a9ef233ad290d0b879a934954a7eaa9be0eca209c31177b539e9d8a7`; 773 registros, todos verificados literalmente e após finalização/schema. Denominadores: 497 definições codificadas +1 exemplo da legenda, 10 competências gerais, 35 direitos (6 gerais +29 por campo), 19 objetivos de síntese, 17 capítulos, 5 campos e 15 grupos etários. As variantes de códigos impressas são preservadas; a página85 realmente imprime cinco direitos para Traços/Sons/Cores/Formas. A página5 preserva o parágrafo normativo completo; os créditos não curriculares com sobreposições/artefatos nativos continuam separados como pendência.
- Portaria246/2026: `ro-matrizes-2026-native-structure.json`, SHA `04788ff9cba9478e3adf1c1f573b89d6321f5acad932c31d027779938455c7e2`; 42 registros, 20 artigos literais e 10 células nativas. A fonte trata de EF Anos Finais, não EI/EM; data do ato06/01/2026. A numeração salta12/13/15/16; artigos inexistentes não foram fabricados. Onze matrizes rasterizadas continuam pendentes.
- Portaria12518: `ro-itinerarios-2026-native-structure.json`, SHA `ba08814d55062873d00d470ff7f85fe945cb0ccd4435c3a35e67b3041cd2620d`; 32 registros, 18 artigos; ato29/12/2025, publicado08/01/2026. Uma região rasterizada permanece pendente.
- Portaria1328/2025: `ro-matrizes-2025-native-structure.json`, SHA `546b2190502a5eacbb3940792239e9eb8afb05b66d721190714c7bfb0a5b0589`; 381 registros, 24 artigos e 330 células nativas. Doze regiões rasterizadas permanecem pendentes.
- Progressão EM, páginas120–122: `ro-rcem-progressions.json`, SHA `faffba4c01ca9e85a2edf4201dc6bf96474e8deee7b441f38e63e3e161b2ae2c`; 159 registros. As156 referências documentais incluem128 células com ano explícito e28 entradas da coluna-índice sem ano. Os91 agrupamentos page/code são prova técnica, não sobrepõem as posições por ocorrência. Nenhuma referência foi promovida a definição de aprendizagem; não há propagação de anos para todo o livro.
- Incremento EM LGG/LP: `ro-rcem-lgg-organizer.json`, SHA `a6ae34de74db85aac316c6568f4c1f3c6cf5bd41483a6ae5a05435af6d5be6a4`; 620 registros, preservando os159 anteriores. Inclui133 definições completas com cabeçalhos de ano (47/47/39),31 fragmentos de continuação entre páginas,262 objetivos locais sem código do Quadro5,27 referências documentais e hierarquia. O censo bruto fecha todos os316 códigos primários no recorte120–236. A releitura cobre todos os caracteres de todas as células de aprendizagem, sem truncamento. Há156 associações documentais índice→definição local da mesma Source/edição e ano compatível, sem equivalência ou pré-requisito. A proposta serial está em `ro-rcem-lgg-proposed-source-fields.json`.

Os cinco primeiros vínculos de fonte foram confirmados por `data_north` em `docs/evidence/north-source-bindings-verification.json` (1.387 registros). A integração do incremento620 deve ser confirmada separadamente; não é presumida por este documento.

## Trabalho atual e pendências

- EF Espanhol: `ro-ef-spanish-complete.json`, SHA `38a049fbe79b2a6a588fc1ac352d953ca16c6a85ddc147aab177ef017838fba4`;149 registros,144 definições locais `LE`,142 códigos distintos e10 continuações. Todas as evidências e todos os caracteres das colunas258–278 foram conferidos, além do finalizador/schema reais. Não há alias para `LI`. Os códigos EF07LE24(p273) e EF09LE28(p274) aparecem sob o cabeçalho explícito8º ano: o conflito é preservado, sem inferência pelos dígitos. Integração serial solicitada. Outros componentes, competências/eixos/objetos permanecem pendentes.
- EM: outras áreas da formação geral, competências/objetos, itinerários, projeto de vida e modalidades ainda exigem censo/extração completos. O incremento LGG/LP não equivale à conclusão das860 páginas.
- Eletivas2026: primeiro incremento `ro-eletivas-objectives-primary.json`, SHA `30f45aa4bc9ed3d3ad7f925cf1d5aa65d0be73b905bc2a4a56e846558f766bf2`,415 registros após finalizador/schema e releitura integral:43 projetos,126 campos físicos preservados,157 objetivos de aprendizagem,75 finalidades organizacionais,2 competências e contexto. Denominadores físicos41 campos de objetivos,42 cabeçalhos acentuados de competências e43 habilidades; MAT8/MAT9 não imprimem campo de objetivos. O censo ampliado encontrou o43º campo de competência em MAT10 p70, grafado sem acento (`COMPETENCIA GERAL`): a afirmação anterior de ausência foi explicitamente retratada em `eletivas-field-census-correction.json`; os artefatos históricos permanecem íntegros e o novo campo entra no próximo incremento. Todos caracteres dos41 campos conferidos; teste negativo de truncamento de um caractere é rejeitado. Integração serial solicitada. Incremento de274 enunciados codificados e58 referências sem enunciado está em verificação; não usar antes do gate. Competências/objetos/rubricas/contexto completo continuam pendentes; nenhum código de projeto vira código oficial e nenhuma equivalência pedagógica é presumida.
- Educação Digital: texto nativo disponível nas267 páginas, mas há avisos de recursos XObject ausentes em algumas páginas. Tratar como integridade visual em investigação, não causa externa confirmada; delimitação por página e confirmação por outro parser/aquisição ainda pendentes. Não foi feito novo download grande durante a recuperação de disco.
- Matrizes rasterizadas: OCR legível e conferência primária pendentes; os artigos/células nativas já extraídos não encerram o escopo dos anexos.
- Imagens de conferência ficam em `var/private-evidence/source-audit-ro/`, fora do Git, com caminhos/hashes em `private-evidence-inventory.json`. Nenhuma imagem-fonte é distribuída neste diretório.

## Reprodução

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ei_sidecar.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_normative_sidecars.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_em_progression_positions.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_em_lgg_organizer.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_em_lgg_organizer.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_spanish.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ef_spanish.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/census_eletivas_fields.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_eletivas_objectives.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_eletivas_objectives.py
```

Os dois passos geométricos compartilham PyMuPDF; não se afirma independência absoluta de engine. Censos brutos, comparação exata de fragmentos e cobertura de caracteres de células são verificações adicionais. Nunca publicar uma proposta cujo gate ainda não passou.
