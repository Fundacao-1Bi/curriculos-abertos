# Completude documental SP / MG / RJ — censo e partes estruturadas

O censo percorreu as camadas nativas das **6.494 páginas físicas de16fontes** dos três estados, conferindo os SHA256 dos PDFs originais. Esse percurso não equivale a conferência literal ou semântica de todas as páginas: o P1 documentado ao final identifica, por exemplo,13páginas MG cuja camada nativa é ilegível e requer recuperação. ES é responsabilidade de outra frente e BR está fora deste escopo. `source-census.json` e `heading-candidates.json` são inventários compactos da fonte, anteriores às novas saídas; ocorrências de palavras/códigos e páginas com pouco texto são diagnósticos, não denominadores de aprendizagens, páginas em branco ou provas de prontidão.

## Implementado, executado e verificado

| Fonte / parte delimitada | Denominador documental | Nós para integração |
|---|---|---:|
| SP EI/EF: listas gerais/específicas e direitos gerais EI | 12 listas, 96 parágrafos de competências; painel com 6 direitos | 115 |
| MG EI/EF: listas gerais/específicas e direitos gerais EI | 12 listas, 94 parágrafos de competências; painel com 6 direitos | 113 |
| RJ EI/EF: listas gerais/específicas, preservando direitos anteriores | 12 listas, 94 competências; os 30 direitos diferenciados já existentes são mantidos | 136 |
| MG EM: Quadro37, Educação Profissional e Técnica, PDF348–349 | 4 competências locais e 19 habilidades `C1.H1` etc., mais o quadro pai | 24 |
| RJ EM itinerários: PDF1679p, metadados e finalidades rotuladas | 54 cabeçalhos de componente, 54 ofertas/séries e 54 blocos explícitos de finalidades | 182 |
| **Total aditivo** | **540 nós novos +30 preexistentes preservados** | **570** |

570 nós não significam 570 habilidades. O conjunto inclui competências, direitos, finalidades, grupos e hierarquia documental. Somente as 19 habilidades locais do Quadro37 são novos nós com esse tipo; os demais tipos preservam seu papel documental. Não foram criados códigos oficiais para listas numeradas, direitos ou finalidades.

As listas têm censo independente de âncoras físicas por `get_texttrace` antes da construção dos itens. Cada fragmento novo foi cotejado por Unicode NFC/espaço contra texto nativo e leitura de glifos no bbox original. Os importadores reais `source_uncoded_items` e `finalize_items` executaram com clones de Source somente em memória e páginas originais de evidência: todos os cinco conjuntos passaram contagem, IDs únicos, esquema1.1.0, pais, ciclos e idempotência, com fingerprint do parser igual antes/depois. A prova é delimitada ao importador e aos fragmentos; **não foi executada aqui uma nova extração FULL nacional**.

`source-bindings-proposal.json` contém os cinco caminhos/PINs, SHAs das fontes e paths anteriores esperados. Somente o owner coordenado deve aplicar esses vínculos ao manifesto compartilhado. Não há proposta de `adapter_authority`: as páginas contêm outros contextos e os genéricos/codificados não podem ser suprimidos por conveniência. Esta frente não modificou manifesto/core/cache de produção nem marcou fonte/UF pronta.

## Decisões documentais importantes

- SP História tem **9** competências impressas, não7; Ensino Religioso tem6. O denominador não foi copiado da BNCC. Em Arte, a definição em negrito fica separada do comentário pedagógico regular; o comentário permanece contexto da fonte.
- MG EPT conserva os identificadores locais e até o ponto literal de `C.4.`; não há transformação para `EM13...`. A competência C2/H4 continua entre as páginas348/349. O Quadro38 cita uma comparação do Fórum Econômico Mundial de2015/2020, distinta de novas aprendizagens locais e de anos escolares.
- RJ EI/EF imprime `8. Selecionar...` dentro da linha da competência7, na página133. A competência8 foi separada pelo número/glifos explícitos, com caixas próprias; a7 não absorve seu texto. As10 competências gerais usam coluna numérica própria, recuperada pelos retângulos físicos do quadro.
- RJ itinerários aceita as variantes originais `Objetivo do Componente Curricular`, `Objetivos do Componente Curricular` e `Objetivos do Componente`. Os textos integrais são **finalidades em prosa**, `objetivo_curricular`, `learning_objective_claim:false`; não foram divididos por sentença/verbo para criar expectativas individuais.
- Os seis rótulos literais de área e13 de trilha do RJ conservam variantes como `TECNOLOGIAS:`/`TECNOLOGIAS` e `LINGUAGEM`/`LINGUAGENS`. Não se declara equivalência semântica pela similaridade. Há54 ocorrências de oferta e54 componentes, com série2/3 apenas de cabeçalhos explícitos. A reconstrução física das linhas evita que o título desenhado tardiamente na página309 vire nome de componente.
- A primeira versão do adaptador SP atribuía incorretamente o deslocamento de página impressa de MG. A correção deriva cada folio do próprio PDF e usa `null` quando não há número legível. Textos, páginas físicas e bboxes ficaram preservados. Os PINs de integração são os finais no JSON de bindings; versões SP anteriores não devem ser usadas.
- Os30 direitos EI/RJ preexistentes são copiados integralmente ao agregado, sem editar `rj-ei-rights.json`. `rj-existing-rights-preservation.json` verifica IDs/textos/tipos/posições/evidências/pais/rótulos após os dois importadores reais; recibos originais do wrapper ficam retidos no agregado.

## Reprodução

Usar o Python seguro já instalado:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-completeness/census_sources.py
var/venv-pipeline/bin/python data/manifests/uncoded/sp-eief-competencies-adapter.py
var/venv-pipeline/bin/python data/manifests/uncoded/mg-eief-competencies-adapter.py
var/venv-pipeline/bin/python data/manifests/uncoded/rj-eief-competencies-adapter.py
var/venv-pipeline/bin/python data/manifests/uncoded/sp-mg-ei-rights-adapter.py
var/venv-pipeline/bin/python data/manifests/uncoded/mg-ept-quadro37-adapter.py
var/venv-pipeline/bin/python data/manifests/uncoded/rj-itinerarios-objectives-adapter.py
var/venv-pipeline/bin/python data/manifests/uncoded/sp-mg-rj-compose-structured.py
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-completeness/verify_new_adapters.py data/manifests/uncoded/sp-eief-structured-items.json data/manifests/uncoded/mg-eief-structured-items.json data/manifests/uncoded/rj-eief-structured-items.json data/manifests/uncoded/mg-ept-quadro37-items.json data/manifests/uncoded/rj-itinerarios-objectives-items.json
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-completeness/verify_rj_existing_rights_preservation.py
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-completeness/verify_semantic_boundaries.py
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-completeness/write_checkpoint.py
```

Os geradores preservam o instante inicial dos sidecars já existentes para permitir reexecução determinística. Os logs de execução e recibos `*-real-importer-proof.json` registram os resultados reais, não uma promessa de execução. `semantic-boundary-checks.json` contém16 negativos/limites documentais; esses testes complementam os denominadores, sem substituí-los.

## Pendente, sem bloqueio externo novo

A completude global de SP/MG/RJ **permanece pendente**. `remaining-completeness-inventory.json` preserva todas as partes declaradas das16fontes e os candidatos da fonte, inclusive: direitos MG diferenciados por campo/faixa etária e orientações didáticas; demais contextos e organização EI/SP; competências e estrutura sem código dos volumes EM; os programas/cursos/objetos e finalidades do volume RJ integral/técnico de1.729p; conteúdos programáticos, atividades e referências de competências no volume itinerários de1.679p. Nenhum anexo foi descartado, nem a disponibilidade do PDF contada como reconciliação.

Ainda faltam o vínculo coordenado dos sidecars, a extração nacional com parser congelado e o cotejo integral dos resultados atuais. Para RN, o peer independente de3851nós sem código já passou em pasta própria; o cotejo final dos leitores codificados após o FULL nacional ainda aguarda esse FULL.

Não houve novo bloqueio de acesso a fontes nesta frente. O limite de disco foi respeitado: sem novas cópias de PDFs ou renders completos, e inventários públicos compactos. Não há revisão pedagógica humana ou prontidão nacional certificada neste relatório.

## Incremento MG EM versionado, posterior ao marco570

Os cinco PINs do marco570 foram vinculados pelo root. O recibo `bindings-observed-after-root.json` é histórico desse marco; os incrementos versionados abaixo substituem somente o vínculo correspondente, preservando os arquivos anteriores. O novo agregado **`mg-em-structured-v2-items.json`** tem95nós: os24do Q37 originais,9capacidades de Filosofia+10finalidades do ensino de Geografia+2cabeçalhos, e42parágrafos de competências em8listas+8cabeçalhos. São **71nós novos**; nenhum kind novo foi introduzido.

As9capacidades de Filosofia estão expressamente introduzidas por “estudantes ... necessita para ser capaz de”, nas páginas231–232. As10finalidades de Geografia vêm de “espera-se que o ensino da Geografia se baseie”, páginas234–235; mantêm `objetivo_curricular`, sem alegação de expectativa individual codificada. Os42parágrafos de competências são21na sinopse inicial, páginas48–50, e21nos capítulos da FGB. Há variações reais de texto entre as apresentações; nenhuma identidade ou equivalência foi inferida do número. Na Natureza/FGB, os blocos citados foram separados dos comentários pedagógicos adjacentes.

Os95nós passaram no importador/finalizador real, esquema1.1.0, IDs/pais/ciclos, idempotência e guard de imutabilidade do sidecar. O corpo novo foi cotejado em240fragmentos originais (54listas locais+186competências). `mg-em-v2-semantic-boundary-checks.json` contém11limites/negativos adicionais. O agregado não altera Q37 nem o agregado v1. A proposta de binding está em `mg-em-v2-bindings-proposal.json`; aguarda composição coordenada com a recuperação dos corpos codificados pelo agente API. Nenhum manifesto foi alterado por esta frente, e nenhum genérico/codificado foi suprimido.

Comandos incrementais:

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/mg-em-local-objectives-v1-adapter.py
var/venv-pipeline/bin/python data/manifests/uncoded/mg-em-competencies-v1-adapter.py
var/venv-pipeline/bin/python data/manifests/uncoded/mg-em-compose-v1.py
var/venv-pipeline/bin/python data/manifests/uncoded/mg-em-compose-v2.py
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-completeness/verify_new_adapters.py data/manifests/uncoded/mg-em-structured-v2-items.json
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-completeness/verify_mg_em_v2_boundaries.py
```

Correção do inventário pendente: a hipótese inicial de uma “síntese de aprendizagens” EI/SP não foi comprovada; a busca lexical negativa não atesta ausência. O processamento seguinte identificou de fato30direitos diferenciados por campo naspáginas47–52, já recuperados em35nós separados. Páginas com pouco/nenhum texto nativo continuam exigindo disposição documental específica.


## Incrementos SP EI/EF e MG EI, após integração do marco inicial

O agregado SP **`sp-eief-structured-v2-items.json`** foi vinculado pelo coordenador e passou em seu replay real **154/154**. Seu PIN é `70b258fda07c4fe56fdecfc1dfc4effda05788b57dbc7844e4bb7e0cac9b46fe`: os115 nós anteriores permanecem intactos, somados a30direitos diferenciados por cinco campos EI+5cabeçalhos, e três definições com códigos literais não usuais+1cabeçalho Arte. `sp115-final-record-preservation.json` prova preservação integral dos115 registros e todos os seus IDs/textos/evidências/posições/pais após importação; somente o instante do novo recibo automático difere. As três definições são `EIO2TS04`, `EIO3TS04` e `EF069AR16`, confirmadas em recortes mínimos originais privados, sem transformar O em zero ou corrigir069. Um censo lexical completo das401p identificou1983ocorrências entre parênteses/1946códigos distintos, e exatamente essas três formas fora da gramática geral. Idades EI vêm das colunas impressas; o6ºano de Arte vem da célula explícita, nunca dos dígitos do código. Os direitos de campo continuam separados dos seis direitos gerais, com faixa etária nula.

O novo candidato **`mg-ei-organizers-v1-items.json`** contém268nós, PIN `c956fbcf53322b2b40d274758d05b1bc09e44a6bdcaa28d64ffd2fb744f7d395`, e passou no importador/finalizador real268/268, esquema, pais/ciclos e idempotência. O mapa geométrico independente cobre as75páginas68–142, cinco campos×três faixas, com as quatro colunas literais. Foram preservados5campos,15grupos etários,99direitos distintos dentro de campo/faixa (438ocorrências físicas retidas),75colunas/página de orientação didática e74de experiências sugeridas. As11.358linhas de origem foram verificadas;248regiões comprimidas só foram aceitas quando continham exatamente os mesmos glifos. As colunas de Objetivos estão deliberadamente fora desse sidecar, pois o agente de recuperação codificada trata seus códigos/corpos e continuações. Orientações são contexto docente; experiências propostas são experiência, sem atomização em aprendizagens individuais. O candidato aguarda composição coordenada com113nós estruturais anteriores e os corpos codificados.

## Incremento delimitado SP EM

**`sp-em-basic-competencies-v1-items.json`** tem15nós, PIN `f0146a69531c66d41568d46818a927d26b268ce5c9604c6d3c1f391975101041`:10competências gerais nas páginas24–26, três competências de Natureza na152 e dois cabeçalhos. O denominador independente usa âncoras nativas de `get_texttrace`; todos os fragmentos e o importador/finalizador real15/15 passaram com fingerprint estável e sem escrever cache. As competências das demais áreas presentes nas colunas de organizadores continuam em censo; não se declara completude do EM a partir dessas duas listas.

Os novos candidatos não estabelecem autoridade de página nem removem registros genéricos ou codificados. Nenhuma fonte/UF foi marcada pronta. O vínculo nacional, a composição com corpos codificados e o cotejo do FULL atual são fatos separados das verificações delimitadas acima.


## RJ integral/técnico: contextos docentes integrais

A fonte de1.729p foi percorrida integralmente antes de gerar o candidato **`rj-integral-teaching-contexts-v1-items.json`** (PIN `3fe072fd7606d6e5b8ee70a082aa21cc5fd4d2711f6b6a6777b804cdb9a87d7f`,4.289.354bytes). O denominador independente de caracteres em `get_texttrace` confirmou269cabeçalhos de Perfil do professor,269de Abordagem metodológica e269de Abordagem avaliativa. O censo físico da fonte confirmou os mesmos807cabeçalhos e269ocorrências de componente. São1.076nós, com311campos continuados entre páginas e2.495fragmentos primários verificados. O importador/finalizador real passou1.076/1.076, sem falhas literais, esquema, órfãos ou ciclos e com idempotência. Onze controles semânticos adicionais passaram.

Os tipos são `formacao_docente`, `orientacao_metodologica` e `orientacao_avaliacao`: perfis de professor e orientações não se tornam expectativas dos estudantes. Cada campo rotulado é mantido inteiro, sem divisão em verbos, sentenças ou itens de lista. O último componente, PROJETO DE INTERVENÇÃO na página1710, possui título original sem o rótulo usual e recebe nó próprio: não herda MÍDIAS E COMUNICAÇÃO da unidade anterior. A variante nativa `Perfil do professo` é mantida sem correção automática nem alegação de erro impresso visualmente confirmado.

A primeira tentativa do importador rejeitou268cabeçalhos porque os trechos primários incluíam o rótulo enquanto o texto canônico continha só o valor. A correção localiza os glifos do valor após o separador original e conserva o rótulo no contexto; a redação não mudou. O recibo final é `rj-integral-teaching-contexts-v1-items-real-importer-proof.json`.

Anos escolares e área/eixo permanecem nulos nesses registros: as matrizes de carga horária podem conter0h/a, e seus rótulos de eixo tecnológico não devem ser convertidos automaticamente em áreas BNCC. Programas/cursos, matrizes, objetos, referências e corpos codificados continuam sujeitos a reconciliação própria. O adaptador não propõe autoridade de página; nenhum desses conteúdos foi retirado. A proposta de vínculo coordenado está em `rj-integral-teaching-contexts-v1-binding-proposal.json`.

```sh
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B data/manifests/uncoded/rj-integral-teaching-contexts-v1-adapter.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/verify_new_adapters.py data/manifests/uncoded/rj-integral-teaching-contexts-v1-items.json
```


### SP EM: composição das quatro áreas concluída neste recorte

A composição preferencial agora é **`sp-em-structured-v1-items.json`**, com40nós: os15acima preservados integralmente+21parágrafos literais dos quatro organizadores+4cabeçalhos. O censo das83páginas dos organizadores encontrou64ocorrências numeradas;21redações distintas dentro de área/número foram retidas, com todas as reiterações guardadas como localizações secundárias verificadas. Os34parágrafos de competências nas seis listas/apresentações não equivalem a34novas habilidades estaduais. As três competências de Natureza da lista e sua apresentação na matriz permanecem como apresentações documentais distintas, sem identidade automática pelo número.

A recuperação usa somente a primeira coluna delimitada por réguas vetoriais originais. Todo o fluxo não branco da coluna, não apenas seus números, coincide com uma leitura independente de caracteres `get_texttrace`. Foram verificados913fragmentos, inclusive os quatro títulos originais de área que justificam o posicionamento. A revisão do censo encontrou continuações de Linguagens até a111 e de Natureza até a167, além do marcador literal `3-`; nenhuma delas foi truncada nem corrigida para `3.`. A evidência primária contém cada parágrafo uma vez; reiterações ficam documentadas no contexto com caixas e texto literal, para não duplicar o texto canônico na validação.

O importador/finalizador real passou40/40, esquema, pais/ciclos, idempotência e fingerprint estável. Oito negativos/limites passaram em `sp-em-v1-semantic-boundary-checks.json`. A proposta **`sp-em-v1-binding-proposal.json`** substitui a proposta ainda não vinculada dos15nós, sem mudar o arquivo de15 nem remover genéricos, codificados, objetos, anexos ou demais partes. O FULL nacional atual continua pendente.

```sh
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B data/manifests/uncoded/sp-em-organizer-competencies-v1-adapter.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B data/manifests/uncoded/sp-em-compose-v1.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/verify_new_adapters.py data/manifests/uncoded/sp-em-structured-v1-items.json
```


### RJ integral/técnico v2: correção geométrica e continuação omitida

A composição preferencial é agora **`rj-integral-structured-v2-items.json`**, com1.080registros: os1.076anteriores literalmente preservados e quatro definições com âncora na página669. O importador/finalizador existente passou1.080/1.080, esquema1.1.0, pais/ciclos e idempotência, sem alteração de parser. A proposta de vínculo e autoridade delimitada está em **`rj-integral-v2-binding-proposal.json`**.

Na célula de Habilidades da669, palavras inteiras da coluna vizinha começam antes da régua: `Tecnologias` e `C):`. A extração por caractere introduzia seus glifos `T`/`C` no texto de EM13LGG204. O recorte mínimo original privado (7.017bytes; hash/bbox em `rj-integral-p669-minimal-glyph-crop.json`) e duas leituras independentes de geometria confirmam a origem. O corpo agora usa palavras inteiras da coluna, com evidência de cada palavra e sem correção ortográfica. A grafia original `remidiação` em EM13LGG105 permanece intacta. A regra não foi promovida a helper global.

O quarto código, EM13LGG304, está no fim da669 e seu corpo integral continua na670; estava ausente do cache anterior. Foram preservados os três IDs canônicos existentes, seus códigos, posições, tipos e pais; somente o texto de204 perdeu os dois fragmentos espúrios. A definição304 possui novo ID, âncora669 e evidências670. O cabeçalho explícito3ªSÉRIE/Habilidades da668 é retido separadamente; posições válidas anteriores foram preservadas neste delta de fidelidade, sem enriquecimento posicional silencioso.

O replay do cache integral desta fonte no finalizador real, com a proposta de autoridade somente para aprendizagens codificadas da669, passou **2.851→2.852registros**: todos os2.848registros externos aos três substituídos ficaram idênticos. Passaram15controles, inclusive negativos para668,670, outra Source, contextos genéricos e referências. O cache original ficou byte a byte inalterado. Não se propõe autoridade para a670, e seus outros códigos permanecem intactos. A checagem cobre todos os quatro códigos da669, não somente o erro conhecido. Demais partes da fonte e o FULL nacional continuam pendentes.

```sh
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B data/manifests/uncoded/rj-integral-p669-coded-body-v1-adapter.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B data/manifests/uncoded/rj-integral-compose-v2.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/verify_new_adapters.py data/manifests/uncoded/rj-integral-structured-v2-items.json
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/verify_rj_integral_v2_scope.py
```


A correção do texto de EM13LGG204 também possui ledger próprio **`data/manifests/uncoded/rj-integral-p669-text-corrections-v1.json`** (SHA `193c0b309fd880c07760776e646a93d5b1719c9f7677b305ed53dbb8485f8153`), no formato `record_text_corrections_v1`. Contém exatamente uma alteração com mesmo ID, textos anterior/posterior e hashes UTF8, motivo e quatro provas com hashes. Declara publicações anteriores imutáveis e nenhuma mudança da edição oficial. A definição304 foi registrada separadamente como inclusão, não como alteração de texto anterior; o recibo do ledger registra essa distinção. A proposta de Source passou a incluir `technical_extraction_corrections`, sem aplicar o vínculo nesta frente.

## SP: corpo integral da Resolução SEDUC156/2025

**`sp-seduc156-act-v1-items.json`** tem87nós normativos, PIN `f12a91f1980b92bd1793aebdde13becfb07bd4f7d114c5f17f9cfd5e7627301e`. A fonte é uma página do DOE, impressa21/139, com três colunas e fragmentos de outros atos ao redor. O recorte integral desta resolução começa no título156 da coluna esquerda, continua por toda a coluna central e termina na indicação do anexo da direita, antes do título158. Há16artigos,6capítulos,20parágrafos,34incisos,3alíneas,3considerandos, título, ementa, preâmbulo, comando e referência de anexo. Os caputs não absorvem os filhos; a hierarquia segue os rótulos impressos e conserva as continuações entre colunas.

O censo da fonte tem255linhas e12.257caracteres não brancos representados exatamente uma vez. O fluxo inteiro coincide com uma leitura independente `get_texttrace`, com uma equivalência tipográfica explícita apenas na comparação:30glifosﬁ de trace correspondem aos dois caracteres fi que RAWDICT já fornece. Não há substituição ortográfica, de códigos ou de bytes do PDF. O recorte mínimo privado do título também confirma o limite com o anexo do ato PEP anterior e os espaços originais da ementa, que a saída ordenada padrão do MuPDF perde.

Os87nós passaram no importador/finalizador real, esquema, pais/ciclos, idempotência e fingerprint estável, além de10limites/negativos. A proposta `sp-seduc156-act-v1-binding-proposal.json` é aditiva, sem autoridade de página. A referência ao arquivo de matrizes não se apresenta como seu conteúdo: os anexos têm Source própria. O contexto genérico da página permanece, e o ato PEP anterior/158 posterior não foram transformados em dispositivos da156. Nenhuma fonte/UF pronta foi declarada.

```sh
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B data/manifests/uncoded/sp-seduc156-act-v1-adapter.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/verify_new_adapters.py data/manifests/uncoded/sp-seduc156-act-v1-items.json
```


## SP SEDUC156: todos os anexos e disposições de páginas vazias

O candidato **`sp-seduc156-annexes-v1-items.json`** contém26registros, PIN `0863a97a14b68b88916872df860f029b918a36dbe810264a47e4dbb54fd3208a`:9títulos de anexo,15fragmentos físicos de quadro,1bloco complementar de anexo e1nota documental de pontuação solta original. As1.804linhas das12páginas com texto foram representadas exatamente uma vez, com inventário independente de todos os caracteres nativos, inclusive textos rotacionados. As células originais, suas caixas e índices de grade estão retidas no contexto; a grade técnica do detector não se apresenta como denominador de disciplinas, aprendizagens ou linhas pedagógicas.

As páginas9,14e15 não foram chamadas vazias por falta de texto: não têm imagens nem caminhos de desenho e todos os pixels RGB da rasterização original de página inteira são brancos. Dimensões, hashes do raster e estatísticas constam em `sp-seduc156-annexes-v1-source-denominator.json`. Não se criaram capturas completas em disco. A vírgula isolada existente no intervalo entre anexosIII/IV foi preservada como nota documental sem pai, com flag explícita; não virou seção normativa ou expectativa de aprendizagem.

Os anexosI–VIII contêm matrizes de carga horária;IX indica formação docente para componentes. Os valores/células permanecem literais, sem converter formação docente em habilidade estudantil nem atribuir séries a um bloco inteiro por seus numerais. O importador/finalizador real passou26/26, esquema, pais/ciclos, idempotência e fingerprint estável, além de10controles semânticos. A proposta de vínculo é `sp-seduc156-annexes-v1-binding-proposal.json`, aditiva e sem autoridade de página. Reconciliação nacional e Source/UFpronta continuam distintas desse processamento.

```sh
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B data/manifests/uncoded/sp-seduc156-annexes-v1-adapter.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/verify_new_adapters.py data/manifests/uncoded/sp-seduc156-annexes-v1-items.json
```


## SP EI: cinco descrições dos campos, distintas de sínteses individuais

**`sp-eief-structured-v3-items.json`**,159nós, PIN `a9fa43bc464021b5c9f6e7ed497a44ae083d9660f5f942eb7e4c6cca91a7261a`, preserva literalmente todos os154registros anteriores e acrescenta as cinco descrições em prosa dos Campos de Experiências nas páginas45–46. O censo independente confirmou cinco marcadores e todo o fluxo de caracteres das regiões. A descrição Corpo/gestos continua na página46; Escuta/fala também atravessa a coluna. Os parágrafos completos foram mantidos, sem dividir verbos ou criar objetivos.

O tipo `descricao_campo_experiencias` é contexto documental, não síntese de aprendizagem individual. Os nomes de campo da posição vêm do próprio rótulo; a única normalização declarada é desfazer a quebra tipográfica de fim de linha no rótulo, preservado integralmente no contexto. Não se ligou automaticamente o título com pontuação variante da lista posterior. Não se afirma presença/ausência global de sínteses a partir de uma busca lexical. Os159nós passaram no importador/finalizador real e seis limites/negativos; a proposta aditiva está em `sp-eief-v3-binding-proposal.json`, para substituir o vínculo154 mediante guarda de PIN. Nenhuma fonte/UF pronta foi marcada.


## MG orientador2026: projetos com campos explicitamente rotulados

**`mg-orientador2026-projects-v1-items.json`** contém21registros, PIN `508c963903cdb4a349303855594c7ac49045b1b50f70e7aebdd125f712e9a031`, e passou no importador/finalizador real21/21, esquema, pais/ciclos, idempotência e nove controles documentais. O censo integral das46páginas encontra sete títulos Projeto Integrador: três exemplos nas13–14 e quatro detalhamentos nas16–19. O candidato cobre estes quatro detalhamentos, com anos2/3 de cabeçalhos expressos, sínteses pedagógicas integrais, listas literais de eixos e referências de material sugerido. Inclui também três cabeçalhos de ano e a finalidade/implementação geral do1ºano.

Síntese pedagógica de projeto fica como `objetivo_curricular`/finalidade, não como síntese de aprendizagem individual. Nenhum verbo ou sentença virou nova habilidade; nenhuma competência do anexo nacional CNE4/2025 foi reescrita como criação mineira. Os materiais indicados são suporte auxiliar, expressamente descritos assim pela2.6.4. Os URLs incorporados no PDF ficam no contexto, sem alegar aquisição desses materiais. As grafias originais, inclusive `económicos`, permanecem. Os exemplos anteriores e os quadros EJA31–33 continuam no inventário para processamento separado. A proposta foi preparada após aviso ao coordenador e está explicitamente destinada ao período posterior ao refresh atual dos16Sources.

```sh
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B data/manifests/uncoded/mg-orientador2026-projects-v1-adapter.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/verify_new_adapters.py data/manifests/uncoded/mg-orientador2026-projects-v1-items.json
```


### MG orientador2026 v2: EJA e oferta prisional

**`mg-orientador2026-structured-v2-items.json`**,64nós, PIN `3d953ba2f7fb73d9d9b18bfa68d517ece0172d760cad1c6db81ea721dfae6e1c`, preserva os21anteriores e acrescenta43registros dos três quadros EJA31–33:3períodos literais,12componentes e suas referências/resumos, além da oferta para unidades prisionais e seus dois componentes explícitos. Os12resumos coincidem integralmente com leitura independente por palavras nativas; a leitura correta preserva `definida`, cuja ligadura o `table.extract` reordenava. Títulos abreviados/reticências do acesso a material não foram completados por invenção.

Os seis resumos de atividades complementares são experiências/propostas, e os demais são contexto. O campo heterogêneo Objetivos específicos de Soluções Matemáticas mantém os três bullets juntos como `objetivo_curricular`/finalidade: contribuir para educação financeira, contextualizar geometria e compreender pesquisas amostrais. O parecer independente de domain, lido no original e imagem da página33/impressa32, está em `mg-orientador2026-eja-objectives-semantic-peer.json`; não se isolou o último verbo discente para criar uma habilidade. A granularidade é `source_material_summary_objectives_block`, com `learning_objective_claim:false`.

Período1/2/3 não se tornou ano/série ou idade. A oferta prisional posterior ao quadro não herda automaticamente seu3ºPeríodo. Passaram o importador/finalizador real64/64, esquema, pais/ciclos, idempotência e11controles semânticos. A proposta `mg-orientador2026-v2-binding-proposal.json` substitui somente a proposta21ainda não ligada; o manifesto continuou intacto nesta frente. Nenhuma autoridade de página ou Source/UFpronta foi proposta.

```sh
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B data/manifests/uncoded/mg-orientador2026-eja-v1-adapter.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B data/manifests/uncoded/mg-orientador2026-compose-v2.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/verify_new_adapters.py data/manifests/uncoded/mg-orientador2026-structured-v2-items.json
```


## P1 novo: MG Resolução SEE5212/2025, corpo1–13 com codificação ilegível

O censo original das163páginas encontrou91anexos numeradosI–XCI, com continuações, a partir da14. As primeiras13páginas são o corpo normativo; sua camada nativa está corrompida. Os programas Type0 dos corpos têm contornos de glifos, mas não têm ToUnicode, cmap ou post com mapeamento Unicode; os glifos de trace voltam como U+FFFD e RAWDICT usa índices/controles em lugar de letras. Nenhum decoder de português foi inventado a partir disso. O rodapé SEI de outra fonte tipográfica permanece legível e não prova que o corpo esteja correto.

O cache1.5 atual tem163seções e conserva esses símbolos, embora marque `ocr_required:false`, `ocr_completed:false`, `ocr_pending:false` nas13páginas. Portanto zero falhas de códigos não certifica esse texto documental. `mg-matrizes2026-original-header-census.json` é somente diagnóstico: suas163linhas de heading são majoritariamente rodapés, não denominador de artigos. Root e pipeline receberam o P1; nenhuma página foi marcada concluída.

Foi executado **OCR real das13páginas completas**, usando o engine existente, Português, rasterizadorPyMuPDF1.26.7 e modelo/binary fingerprintados. Todos os arquivos ficaram em `var/private-evidence/source-audit-southeast-completeness/mg-matrizes2026-ocr13/`; `ocr.ROOT` foi redirecionado só no processo. Foram6.355palavras,94com confiança abaixo de60, em11,26segundos com dois trabalhadores. Os13rasters originais, camadas nativas e resultados OCR permanecem privados. O PDF, cache de produção e fingerprint do parser foram idênticos antes/depois. Não houve `requires_ocr_pages` inventado, alteração de Source ou escrita no cache OCR de produção.

As páginas1/7/13 foram inspecionadas visualmente: imagens legíveis, estrutura de capítulos/artigos, término nos artigos54/55 e assinatura confirmam que a falha está na codificação. Isso é diagnóstico, **não conferência integral de transcrição**. Todas as6.355palavras continuam candidatas pendentes;94tokens de baixa confiança são prioridade, não os únicos que precisam de conferência. Há confusões de OCR entre incisos romanos e letras, além de marcadores§; nenhuma correção textual foi aplicada automaticamente.

Provas: `mg-matrizes2026-font-and-ocr13-probe.json` e `mg-matrizes2026-ocr13-visual-diagnostic.json`. Não há sidecar de texto aprovado nem proposta de binding. Após conferência primária integral, a via prevista é um adaptador documental com provas reais do OCR/imagens e autoridade delimitada ao corpo, preservando os anexos legíveis. A alternativa opt-in `requires_ocr:true` do core vale para todas as163páginas; não foi ativada por conveniência ou sem medir o custo/escopo. Esta falha é recuperável localmente, não bloqueio externo de acesso.

```sh
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/mg-matrizes2026-font-and-ocr13-probe.py
```

### MG corpo 1–13: candidato documental após revisão primária integral do autor

O checkpoint acima era diagnóstico. O candidato posterior **`mg-matrizes2026-body13-candidate-v1-items.json`**, PIN `d79aec0b269bf438745e229047912f9addfd24eb082e4bf2e114cdc93b2402a5`, contém 265 nós documentais. Foram conferidos os 55 artigos e seus caputs, parágrafos, incisos, alíneas, títulos e continuações. Rodapés, metadados e assinatura permanecem distintos da prosa legal. Não se criaram habilidades, códigos oficiais ou anos escolares a partir dos números dos artigos. Os três elementos gráficos — brasão, logotipo de assinatura e QR — estão inventariados como paratexto do original, sem inserir palavras espúrias de OCR no corpo legal nem alegar transcrição de suas letras internas.

A conferência não se limitou aos 94 tokens de confiança baixa. O inventário físico integral tem **41.912 ocorrências de glifo em 598 baselines**, sendo **558 linhas com texto e 40 linhas formadas somente por glifos vazios/espaços**. Foram lidas as 176 formas desconhecidas dos programas de fonte, em cinco atlas de recortes primários, e todas as regiões das 13 páginas completas. O mapeamento é uma transcrição visual do autor, identificada por SHA do programa da fonte/GID; **não é um cmap ou Unicode nativo recuperado**. Pontuação e grafias originais permanecem, inclusive capítulos IV/V repetidos, § 4º repetido no art. 44, `que altera o Lei`, `Lei no`, referências incomuns a anexos e distinções entre hífen, travessões e ordinal/grau.

As 13 transcrições públicas por linha guardam caixas, baseline, origem dos glifos, hashes do raster original e do OCR bruto privado. O único espaço acrescentado para separar regiões físicas é explicitado: na página 13, processo à esquerda e número SEI à direita ocupam a mesma baseline, com grande intervalo sem glifo entre os objetos. Nenhuma letra foi acrescentada. As linhas foram atribuídas uma vez, sem faltas ou duplicações; continuações atravessam os rodapés e mantêm o proprietário documental anterior.

`mg-matrizes2026-body13-candidate-v1-controls-and-real-import.json` registra recontagem direta dos glifos no PDF, identidade de pixels das 13 páginas, conferência estrita dos caracteres e dos 558 textos de linha, além de 12 controles negativos. O importador e o finalizador reais passaram **265/265**, esquema, pais e idempotência. Parser, manifesto, cache de produção e sidecar foram idênticos antes/depois. Os dois fragmentos de fim de linha `módulos-` exigiram apenas agrupar a evidência do parágrafo completo para o checker existente; texto e checker permaneceram intactos.

**Revisão independente ainda pendente; binding não permitido neste candidato.** North recebeu primeiro apenas PDF/SHA/páginas/rasters e fixou inventários visuais independentes antes de receber qualquer transcrição. O importador existente confere o arquivo de transcrição referenciado e atribui seu padrão `source_attributed`; esse padrão não comprova leitura do original nem revisão independente. O estado técnico de todos os registros e do wrapper continua `author_primary_raster_review_complete_independent_peer_pending`. Nenhuma Source/UF foi declarada pronta, nenhum campo do manifesto foi alterado e os anexos 14–163 continuam fora deste candidato.

```sh
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/mg-matrizes2026-build-body13-candidate-v1.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/mg-matrizes2026-verify-body13-candidate-v1.py
```

O peer independente confirmou as **545 linhas do corpo mais 13 rodapés**, mas pediu dois ajustes antes da disposição final. Foram aplicados em **novo arquivo v2**, PIN `e3a5340bf06d803d5ef1e104f99049546d7450f21211daa92976621d81d486f6`: art. 1º passa a filho de “DISPOSIÇÕES PRELIMINARES”; nove caixas de cabeçalho ganham 1,5 ponto para cima, incluindo os acentos pintados acima da métrica tipográfica. Cada caixa conserva `source_metric_bbox` e o motivo/hash da prova. As três supostas intrusões de logotipo da página 13 eram artefatos do diagnóstico de máscara e não foram aplicadas. V1 e as treze transcrições continuam intactas; todos os textos, chaves, tipos, códigos, posições e ordens foram preservados.

O replay do finalizador com **Source clonada somente em memória** demonstrou a substituição declarada de exatamente 13 seções genéricas corrompidas por 265 nós, sem retirar conteúdo para melhorar uma métrica: **163 → 415 registros**. Todos os **150 containers dos anexos 14–163 ficaram idênticos em todos os campos**. A autoridade proposta cobre somente `uncoded_page_sections_ranges:[[1,13]]`, sem autoridade sobre códigos. Os 13 registros antigos foram arquivados privadamente com hashes/IDs no recibo. Isso não afirma que os 150 containers de anexos sejam uma estrutura curricular integral. A proposta continua `DRAFT-pending-peer`, sem execução de vínculo; o estado só poderá mudar após o parecer final sobre a v2.

```sh
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/mg-matrizes2026-compose-body13-candidate-v2.py
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/verify_new_adapters.py data/manifests/uncoded/mg-matrizes2026-body13-candidate-v2-items.json
PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -B docs/evidence/source-audit-southeast-completeness/mg-matrizes2026-verify-body13-replacement-v2.py
```
