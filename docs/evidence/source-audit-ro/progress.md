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

## Checkpoint posterior: Eletivas, Digital e fechamento documental de EI

Este checkpoint atualiza os estados parciais acima. O manifesto atual e `data_north` confirmam os vínculos EM620, Espanhol149 e Eletivas915.

- Eletivas v3: `ro-eletivas-competency-fields-v3.json`, SHA `6feac57d112b6ee10ab26eb26533728c9d95b29cd95055b9f62a6da35d5e8a95`,915 registros. Preserva809 anteriores exatamente. Todos caracteres dos43campos de habilidades e43campos de competências foram relidos. Totais274enunciados codificados locais,40habilidades sem código,9capacidades,80competências gerais,2específicas,157objetivos,85finalidades e66referências, além de contextos. O43ºcampo de competência, MAT10p70, imprime `COMPETENCIA GERAL` sem acento: a afirmação anterior de ausência foi retratada em `eletivas-field-census-correction.json`, sem alterar os artefatos históricos. Objetos/eixos/rubricas/contexto integral e normativa introdutória continuam pendentes.
- Digital: escopo EI/EF corrigido na fonte após conferência da capa1 e dos parágrafos7/14. Diagnósticos XObject delimitados em39/267p, causa externa não confirmada. `ro-digital-ei-primary-organizer.json`, SHA `244252c9163f77d1665718b0a1e4af1a9d3516428b7ef2d7443d03c43e4772af`,168registros e7relações documentais passaram loader/finalizer/schema e releitura integral. Todos131códigos físicos70–101 estão contabilizados:11objetivos dos alunos,1finalidade literal “Ensinar”,32células de experiências e119referências. Três corpos transversais p74 são fisicamente cortados na MediaBox, confirmado em recorte privado28KB; ficam SOMENTECÓDIGO canônico e fragmentos candidatos explicitamente incompletos em metadata, sem recompor palavras.112outros corpos de referência são literais. Completude visual/EF/outroscontextos permanecem pendentes.
- EI: `verify_ei_whole_primary.py` derivou773chaves/páginas diretamente da fonte ANTES de ler o adapter, confrontando TODOS173p,3.747blocos e246.117caracteres não brancos curriculares/contextuais. As48entradas do índice e17capítulos estão contabilizados. Somente12blocos de créditos/overlays/footer p5 são exclusões explícitas não curriculares; a abertura normativa de8blocos está integralmente preservada. Prova `ei-whole-primary-inventory.json`, SHA `9d6d9d942a64a65b64434bd92c418ed48d0c55aef7a9f1a5faf1de45ecca3339`. As18partes reais propostas em `ro-ei-whole-source-parts-proposal.json` já foram aplicadas serialmente por `data_north` (prova `ro-ei-whole-parts-actual-binding.json`). Aguarda refresh seletivo do cache1.5 coordenado com FULL antes de executar `reconcile_ei_whole_source.py`. O writer exige cache/config/parser/runtime atuais e valida773registros/fragments/pais/schema, além de cinco mutações negativas. Nenhum receipt ou OwnSourceV2 foi presumido; vigência/dependências/UF/produção seguem separados.

Comandos adicionais:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_eletivas_skills.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_eletivas_skills.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_eletivas_competencies.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_eletivas_competencies.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/census_digital_resources.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_digital_ei.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_digital_ei.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ei_whole_primary.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/reconcile_ei_whole_source.py
```

## Incremento EF: competências completas e teste contra primeira linha

`ro-ef-spanish-and-competencies-v2.json`, SHA `a8cc77cdd1570d1578f6d8d17840dc20f25d8347197022f619398120b2d8d487`,262registros: preserva os149de Espanhol exatamente e acrescenta13grupos/100competências completas (10gerais e90específicas). O censo fonte-primeiro cobre as tabelas de competências de Linguagens, LP, LI, Espanhol, Arte, Educação Física, Matemática, Ciências, Humanas, Geografia, História, Ensino Religioso e as gerais. Todos os números/corpos foram confrontados com células completas, réguas físicas pretas desenhadas no PDF e intervalo até próximo número na mesma coluna; nenhuma primeira linha foi aceita como corpo inteiro. O rótulo impresso `09` de Educação Física é preservado em metadata; nenhum código oficial ou ano foi criado.

O loader/finalizador/schema real passou262, assim como a releitura literal e pais acíclicos. O teste negativo REAL reduz texto canônico e evidência à primeira linha: o `evidence_check` genérico ainda passa por substring, mas a conferência integral rejeita a cópia alterada. Prova `ef-competencies-negative-first-line.json`. A cópia privada temporária foi removida; originais e adapter não foram alterados pelo teste. Proposta serial `ro-ef-competencies-proposed-source-fields.json`; nenhum cache, DB ou extrator global foi usado. Continua sem `ready/reconciled`; demais organizadores/objetos/contextos do EF ainda pendentes. A reconciliaçãoEI fica com North após refresh coordenado; esta frente segue os demais recortesRO conforme orientação do coordenador.

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_competencies.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ef_competencies.py
```

## Fechamento EI e próximos organizadores EF

- EI OwnSourceV2 foi executado por North contra cache/config/parser/runtime atuais:773/773registros,18partes e4.251fragmentos. Receipt instalado em `data/manifests/reconciliation/ro-rcro-ei.json`, SHA `d8450d857c31cf2501518caefc9b39c333948b719befe886107bd08ebbac8c83`; `ingest.source_reconciliation_reports` real também passou. `WholeSource=true` refere-se à fonte própria sob o inventário declarado; não comprova vigência/UF/produção/revisão pedagógica humana. O primeiro writer falhou por acessar página top-level ausente no canônico; corrigido para `evidence[0].page` antes de emitir o receipt. Nenhum recibo foi emitido naquela tentativa falha.
- ER: `ro-ef-spanish-competencies-er-v3.json`,429registros, SHA `29242fcafeae43b526a4a40978829f0cae1fd065d4a67caf93e4a971692281f7`,preserva262. São63habilidades,9cabeçalhos de ano,30células de objetos e63temáticas, todos corpos/réguas conferidos. EF09ER04 tem continuação550→551 antes de EF09ER05;145caracteres completos. O teste negativo remove continuação do texto e da evidência: o prefixo62passa no checker genérico, mas falha no verificador integral. O cache1.5 já tinha145; não se alegou bug de API/produção. Pacote entregue para BASE429.
- Geo, dados novos sem MF/cache: `ro-ef-with-geografia-v4.json`,694registros, SHA `c5ddcaba1cadb7c0f62160d20fb6a03541d6416b0dcb1f9af8d6f93bea37073c`,preserva429. São127habilidades,9cabeçalhos reais de ano,7continuações,45células temáticas e82objetos. As123habilidades de código nacional literal e4locais são separadas sem alias: `EF01GEO3. 1RO`, `EF01GE05.2RO`, `EF01GE11   -  3RO`, `EF03GE05 – 4RO`. O O, espaços/hífens e ausência de parêntese em EF08GE05 são preservados. Domínio confirmou code raw arbitrário; IDs são ASCII por Fonte/locator. Censo de TODOS caracteres e loader/finalizer/schema PASS694.
- História, dados novos sem MF/cache: `ro-ef-with-historia-v5.json`,1.003registros, SHA `7d1739d8eefba5aadabc0e19de65851248c21067c652dd0792e1602bc4493eb8`,preserva694. São156habilidades (151códigos nacionais literais e5locais RO),9cabeçalhos e11continuações, além dos objetos/temas físicos. Releitura de todos os corpos/células por próximo código, réguas preenchidas/traçadas e loader/finalizer/schema PASS1.003. Cinco sufixos RO permanecem brutos; EF06HI14 sem parêntese de abertura é preservado. Não inclui a menção de legenda p41 como aprendizagem.

North pediu segurar novas propostas/bindings ROEF enquanto fecha BASE429. Geo/História foram produzidos em arquivos novos, sem mutação de MF/cache/DB nem extrator global; os relatórios ficam `binding_ready:false` somente pelo checkpoint, com `independent_readback_passed:true`. Demais organizadores, rubricas/contextos/atos rasterizados continuam em execução. Isso é trabalho interno pendente, não bloqueio externo.

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_religioso.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ef_religioso.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_geografia.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ef_geografia.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_historia.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ro/verify_ef_historia.py
```


### Ciências1190 e Matemática1725 — candidatos data-only, sem binding

`build_ef_ciencias.py` e `verify_ef_ciencias.py` passaram1190 registros no loader/finalizer/schema1.1.0, preservando exatamente os1003 anteriores. Foram confrontados120 identificadores únicos (111 nacionais na forma e9 locais literais), todos os corpos/objetos/unidades por célula e5 continuações. Os9 anos usam cabeçalhos físicos; os de4º/9º estão fora das tabelas no rodapé447/454, e o cabeçalho de colunas450/451 é dividido entre páginas. A área é Ciências da Natureza. SHA89edb5cdf279236cbebbb8203a781466fc7ddfb3a12aff33155ff6343d4265ae.

`build_ef_matematica.py` e `verify_ef_matematica.py` passaram1725 registros no loader/finalizer/schema1.1.0, preservando exatamente os1190 anteriores. Censo247 definições,9 anos explícitos,5 continuações; EF03MA13 sem parêntese inicial é preservado. Cabeçalhos literais “TEMÁTICA –1º ANO” e “MATEMÁTICA –2º AN0” não foram corrigidos. As quatro linhas verticais de cada quadro são verificadas nos desenhos físicos do PDF; as pequenas bordas internas não são promovidas a colunas. O cotejo integral do corpo verifica também que os espaços de até8pt entre a caixa interna e a régua externa não escondem caracteres. A bibliografia fora do quadro final433 não foi incorporada à habilidade. SHA03030e29c47eb7c129690c2473092b2ef66cea4f50edb7794eab5250f0a7374a.

Comandos: `var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_ciencias.py`, `.../verify_ef_ciencias.py`, `.../build_ef_matematica.py`, `.../verify_ef_matematica.py`. Relatórios ef-ci-readback.json/ef-ma-readback.json e censos ef-ci-primary-census.json/ef-ma-primary-census.json. Reader de novos campos utiliza os centros dos clusters de glifos nativos, preservando o texto canônico sem correção ortográfica. É o mesmo motor PyMuPDF, não um segundo motor independente.

Nenhum manifesto/cache/DB foi alterado e nenhuma nova proposta/binding foi escrita durante o checkpoint429 do proprietário North. São incrementos do organizador; EF591p e as8 fontes RO não estão declarados completos. WholeSourceEI está reconciliado separadamente; vigência, adoção, dependências, UF e produção permanecem dimensões distintas.


### Língua Inglesa1818 — censo e readback integrais do quadro238–251

`build_ef_ingles.py` e `verify_ef_ingles.py` passaram1818 registros no loader/finalizer/schema, preservando1725 anteriores. Todas88 ocorrências/88códigos distintos do quadro local e10 fragmentos de continuação foram cotejados; distribuição por cabeçalho explícito6º26/7º23/8º20/9º19, sem conflito de código/ano. Cada caractere não branco das colunas de habilidades está coberto por identificador ou corpo canônico, com evidências página/bbox e fontes originais intactas. Sidecar ro-ef-with-ingles-v8.json SHA41aaec0ea6c0082604cdedd30e12dea3a469c929fd4414bbf099ac1b3dd18cb3; relatório ef-english-readback.json. Colunas de eixos/objetos/unidades e contextos conceituais ainda exigem tipagem própria; esta entrega não declara a fonte inteira reconciliada.

Comandos: `var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_ingles.py` e `.../verify_ef_ingles.py`. Nenhum manifesto/cache/proposta/DB foi alterado durante o checkpoint do proprietário.


### Arte2096 —268 ocorrências completas sob9 anos explícitos

`build_ef_arte.py` e `verify_ef_arte.py` passaram2096 registros no loader/finalizer/schema, preservando1818 anteriores. O quadro291–339 possui268 ocorrências e61 códigos distintos. As redações/posições repetidas são ocorrências locais preservadas, sem dedução por código ou equivalência nacional; há26/26/25/26/25/36/35/35/34 definições nos anos1–9 conforme os títulos reais.3º/5º têm títulos no rodapé298/307 e colunas na página seguinte;8º aparece literalmente8ºANO. Foram cotejados todos os caracteres das colunas e19 continuações. Dois identificadores sem parêntese inicial (EF15AR18/EF69AR27) e o espaço antes do fechamento emEF69AR24 permanecem documentados como impressos. Sidecar ro-ef-with-arte-v9.json SHA76cc0d609243bc711e9f7c3b6a452d6da142c4ad7c1d7a9fa79df04f897b07d2. Provas ef-art-readback.json e ef-art-negative-first-line.json (primeira linha literal passa substring, mas falha completude).

Os campos de linguagens artísticas/objetos e capítulos contextuais ainda exigem tipagem integral; as9competências específicas de Arte já estão na base262 preservada. Não houve manifesto/cache/proposta/DB alterado. Comandos runtime fixado: `var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_arte.py` e `.../verify_ef_arte.py`.


### Educação Física2179 —78 definições,69 prefixos nacionais e9 códigos locais

`build_ef_fisica.py` e `verify_ef_fisica.py` passaram2179 registros no loader/finalizer/schema, preservando2096 anteriores. Todas78 definições/códigos completos do quadro366–384 foram conferidas por caractere da coluna, com2 continuações. O censo inicial de69 únicos era apenas de prefixos de formato nacional: existem9 códigos locais sufixo.1RO, incluindo o literal EF67EF11. 1RO. Não foram suprimidos como duplicatas nem normalizados para códigos nacionais. Os títulos documentam4blocos:1º/2º12definições,3º–5º15,6º/7º28,8º/9º23; os blocos são preservados como arrays, sem repartição anual. Sidecar ro-ef-with-fisica-v10.json SHA500edf5d813830feeb1e6586a8579de172c476cfb09f9efd808f50a9f8e52aa7. Prova ef-fisica-readback.json; nunca foi executado import para produção deste candidato.

Comandos runtime fixado: `var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_fisica.py` e `.../verify_ef_fisica.py`. Eixos/objetos e capítulos contextuais/EJA ainda não estão integralmente tipados. Dez competências específicas de Educação Física já constam da base262 preservada. MF/cache/proposta/DB intactos; North confirmou que429permanece pinado até checkpointRoot/pipeline.
