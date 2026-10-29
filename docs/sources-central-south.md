# Fontes oficiais — Centro-Oeste e Sul

Responsável: subagente real `data_central_south`, ator automatizado. Data da pesquisa e aquisição: 28/10/2026. Requisitos: ESC-01/02, DAT-05, ING-01/03/05. Este relatório registra pesquisa documental e obtenção; **não certifica reconciliação integral nem prontidão de uma UF**.

O manifesto `data/manifests/central-south.json` contém o inventário descoberto, partes normativas esperadas, componentes identificados, fontes primárias, artefatos alternativos, hashes, páginas, tentativas e evidências de sumário. Os PDFs reais ficam em `data/raw/{UF}/`, cache local ignorado pelo Git. Não foi atribuída licença nova aos materiais oficiais. Textos canônicos devem manter a redação e o contexto; os arquivos privados do cache não são o bundle distribuído.

## Conjunto documental selecionado

- **DF**: Currículo em Movimento EI (2ª edição/2018), EF (2ª edição/2018), Novo EM (2021) e Pressupostos Teóricos; catálogo IFA2026, orientação IF2025 e Percursos Educacionais Estruturados; Competências Digitais volumes I–IV. O volume V é específico de EJA (sumário p5), mantido apenas como metadado fora do corpus comum conforme ESC-02.
- **GO**: DC-GO Ampliado volumes I/EI, II/Anos Iniciais, III/Anos Finais; DC-GOEM2021 integral (1397 páginas), com introdução, FGB, itinerários e EPT. A cópia vinculada na página atual Ensino Médio Goiano tem **texto normalizado integralmente idêntico** à cópia do catálogo anterior, apesar de PDFs/checksums de arquivo distintos. Não é edição oficial2025 por estar em pasta2025. Incluídos a matriz/orientação2026 e catálogos de eletivas2026/FIC por sua indicação no conjunto pedagógico oficial, com vigência/aplicabilidade a confirmar documentalmente.
- **MT**: quatro cadernos homologados vinculados pela equipe BNCC/MT (Concepções, EI, EF-AI e EF-AF) e DRC-EM2021 completo, obtido no MEC. A página estadual do edital público2025 remete ao site BNCC/MT. Duas cópias municipais de Pedra Preta são alternativas verificadas: a suposta publicação EF é **somente Anos Iniciais**, e Anos Finais têm documento próprio obrigatório. Os hashes de texto integral comprovam igualdade das cópias EI/AI com as primárias, sem duplicar corpus.
- **MS**: Currículo EI/EF V1.10, EM/Novo EM V1.1 integral, Núcleo Integrador e Currículo da Educação Digital, Midiática e Computacional V1.3, além das Orientações de Projeto de Vida2024 (127p), que complementam o currículo e não substituem a ementa2023. **A publicação oficial Núcleo Integrador2023 permanece indisponível como PDF**, embora o catálogo e a API pública de mídia oficial confirmem o anexo. Não foi substituída por transcrição do Scribd, snippet ou texto de IA.
- **PR**: a fonte2021 EM retornou404, mas a pesquisa primária confirmou atualização pela Deliberação CEE/PR03/2025, aprovada30/07/2025. Foram obtidos o ato, seu anexo integral digitalizado924p e os três volumes textuais oficiais2025 (105/676/142p), indicados como vigentes no portal Seed. A representação textual dos três volumes é a selecionada para processamento; o anexo digitalizado é evidência normativa. EI/EF também recebeu atualização2025 (Deliberação07/2025), com anexo integral de1028p e Computação/Educação Digital. A edição2018 foi preservada como metadado histórico, sem misturar seus itens com2025.
- **RS**: RCG-EI2018 V1 (142p), RCG-EF2018 compilado (1379p) e RCG-EM2021 (287p). A varredura integral do compilado EF não encontrou objetivos EI, por isso EI foi obtida em fonte própria. O PDF público EI usa AES com senha vazia; a biblioteca `cryptography` existente na `.venv` permite a leitura normal, sem credencial extra. O artefato EM de julho2022 é alternativo:13p exibem diferenças de texto/ordenação na extração e uma linha da p113; não foi inventada revisão oficial com base nisso.
- **SC**: CBTC-EI/EF2019 integral, cadernos EM1–6 (incluindo EPT824p e Magistério638p), Currículo de Educação Digital2026 (484p), Língua Inglesa-AI (31p) e normativos CEE/SC070/2025 e parecer446/2025. Caderno5 está indicado como preliminar/em revisão, embora a SED o descreva como parte integrante: permanece explicitamente no inventário, sem esconder a situação editorial. A URL antiga `www2.sed.sc.gov.br` apresentou falha TLS por hostname; as páginas atuais da SED e Google Drive público por elas vinculado forneceram cópias oficiais legítimas.

## Métodos e limites

Aquisição com HTTP(S), timeouts, duas tentativas limitadas por artefato e conferência do magic header `%PDF`, tamanho e parsing; hashes SHA256 do arquivo, datas de obtenção e quantidade real de páginas. O catálogo IFA/DF2026 contém173.444.102 bytes e552p: o limite inicial160MiB o rejeitou; o HEAD oficial confirmou o tamanho, e uma transferência em blocos limitada a200MiB foi executada. Isso é configuração explícita de recursos, sem contorno de acesso.

Identificação de título/sumário/partes via pypdf e PyMuPDF. `inventory_evidence` preserva página e trecho das primeiras seções de sumário. `components` não constitui número de aprendizagens esperado; a reconciliação ainda precisa contar independentemente as linhas/seções do material integral. Nenhuma fonte deste lote recebe `reconciled:true` por mera aquisição ou coincidência de códigos.

Campos `mandatory:false` e `include_in_corpus:false` são usados somente com justificativa: cópia alternativa do mesmo documento, edição histórica substituída por ato primário conhecido, representação digitalizada cujo texto é fornecido em todos os volumes oficiais, ou modalidade EJA expressamente identificada. O `replacement_source_id` e a justificativa estão no manifesto. Nenhuma parte curricular obrigatória foi omitida por conveniência.

Datas de documento/homologação não comprovadas permanecem nulas. Edição consultada e situação de vigência são separadas; data de upload, pasta de URL e checksum nunca são tratados como homologação. Os vínculos encontrados em fontes externas não são relações pedagógicas verificadas automaticamente.

## Diagnóstico de layouts para extração

Amostras automatizadas de layout, **não reconciliação nem revisão pedagógica humana**:

| Documento | Página PDF | Característica observada |
| --- | ---: | --- |
| GO EI |99| Sufixo local `EI01EO01-A`; colunas por grupo etário |
| GO EF-AI |80| `EF01GE01-A` e `EF01GE01-B` |
| GO EM |602| `EMIFCG04`/`EMIFCG05`; muitos objetivos locais adicionais fora do padrão BNCC |
| DF EI |67| Objetivos sem código oficial; ID técnico necessário |
| DF EF |documento inteiro| Não localizado padrão de código BNCC pela varredura; objetivos textuais não podem ser descartados |
| DF EM |39| Objetivos próprios de Projeto de Vida com códigos `PV01` etc.; preservar código local, sem criar código nacional |
| MS EI/EF |80| Prefixo estadual `MS.EI01EO01.`; pontuação/sufixo requerem conferência |
| MS EM |85| `MS.EM13LGG101` |
| MT EI |30| Objetivos EI em colunas por grupo etário |
| MT EF-AF |29| `EF06LP01` e `EF06LP02` |
| MT EM |46| Código local `EM13CNT105.1.PDCMT` |
| PR EI/EF2025 |244| `EF15AR05`/`EF15AR06`; referência preservada no quadro |
| PR EM volume2 |57| `EM13LGG104`/`EM13LGG105` |
| RS EI |88| Objetivo nacional e desdobramento `EI01EO01RS-01` |
| RS EF |57| Objetivo nacional e código local `EF15AR01RS12` |
| RS EM |105| `EM13CNT103`/`EM13CNT104` |
| SC EI/EF |127| EI em colunas; código separado de campos de experiência |
| SC EM caderno2 |30| Códigos nacionais citados em tabela; não presumir equivalência |

Os trechos de diagnóstico completos estão no cache `data/raw/central-south-layout-samples.json`. A equipe de pipeline recebeu diretamente esses achados para evitar perdas sistemáticas de DF, sufixos e relações muitos-para-muitos.

## Bloqueio externo específico

`ms-if-projeto-vida-2023`: link público da SED e registro público WordPress de mídia80798 apontam para o PDF, mas a requisição de obtenção retorna HTML com `common.js?matcher` em vez de `%PDF`. Tentativas e tamanho/hash da resposta limitada estão registrados. Página de origem: https://www.sed.ms.gov.br/programas-e-projetos/novo-ensino-medio/ . URL de artefato: https://www.sed.ms.gov.br/wp-content/uploads/2025/10/PROJETO-DE-VIDA-Ementa-Nucleo-Integrador-2023.v.1.0.pdf . Alternativas primárias pesquisadas não localizaram cópia legível equivalente. Nenhum controle foi contornado. Intervenção mínima: arquivo público corrigido no emissor ou cópia oficial verificável do mesmo documento. Enquanto faltar essa parte ou sua reconciliação, MS não pode satisfazer ACE-01.

## Estado de aceite

**Executado:** pesquisa nacional deste lote, obtenção real de fontes e complementos, hashes, leitura de sumários, descoberta de atualizações normativas2025/2026, diagnóstico de layouts e comparação de cópias alternativas.

**Verificado:** arquivos adquiridos são PDFs parseáveis, checksums conferíveis, origem rastreável; igualdade textual integral das cópias GOEM e MT-EI/AI; distinção documental EJA/regular e anos iniciais/finais.

**Pendente:** reconciliação integral independente das partes/componentes ainda abertos, revisão documental estratificada dos registros produzidos pelo pipeline, resolução da fonte MS2023 e confirmação de aplicabilidade/vigência de complementos nos recortes. Não se declara nenhuma UF pronta a partir deste relatório. O lançamento depende também das jornadas integradas e do release-check.

## Inventário material obtido

| UF | Fontes cadastradas | PDFs adquiridos | Partes/documentos obrigatórios selecionados | Obrigatórios indisponíveis |
| --- | ---: | ---: | ---: | ---: |
| DF | 12 | 12 | 11 | 0 |
| GO | 8 | 8 | 7 | 0 |
| MT | 7 | 7 | 5 | 0 |
| MS | 5 | 4 | 5 | 1 |
| PR | 9 | 8 | 6 | 0 |
| RS | 4 | 4 | 3 | 0 |
| SC | 12 | 11 | 11 | 0 |

Estas contagens são de artefatos documentais, não de cobertura de aprendizagens nem qualidade curricular.

| ID | Etapas | Edição consultada | Páginas PDF | Estado | Fonte primária |
| --- | --- | --- | ---: | --- | --- |
| `go-dcgo-ei` | EI | não confirmada | 174 | acquired | [Emissor](https://goias.gov.br/educacao/documentos-curriculares/) |
| `go-dcgo-ef-ai` | EF | não confirmada | 437 | acquired | [Emissor](https://goias.gov.br/educacao/documentos-curriculares/) |
| `go-dcgo-ef-af` | EF | não confirmada | 434 | acquired | [Emissor](https://goias.gov.br/educacao/documentos-curriculares/) |
| `go-dcgoem-2021` | EM | 2021 | 1397 | acquired | [Emissor](https://goias.gov.br/educacao/documentos-curriculares/) |
| `go-dcgoem-portal-atual` | EM | 2021 | 1397 | acquired | [Emissor](https://goias.gov.br/educacao/ensino-medio-goiano/) |
| `df-cm-ei-2018` | EI | 2ª edição (2018) | 106 | acquired | [Emissor](https://www.educacao.df.gov.br/pedagogico-curriculo-em-movimento/) |
| `df-cm-ef-2018` | EF | 2ª edição (2018) | 312 | acquired | [Emissor](https://www.educacao.df.gov.br/pedagogico-curriculo-em-movimento/) |
| `df-cm-em` | EM | 2021 | 208 | acquired | [Emissor](https://www.educacao.df.gov.br/pedagogico-curriculo-em-movimento/) |
| `df-cm-pressupostos` | EI, EF, EM | não confirmada | 92 | acquired | [Emissor](https://www.educacao.df.gov.br/pedagogico-curriculo-em-movimento/) |
| `ms-cr-eief-v110` | EI, EF | V.1.10 | 821 | acquired | [Emissor](https://www.sed.ms.gov.br/informativos/guias-e-manuais/) |
| `ms-cr-em-v11` | EM | V.1.1 | 357 | acquired | [Emissor](https://www.sed.ms.gov.br/programas-e-projetos/novo-ensino-medio/) |
| `ms-if-nucleo-integrador` | EM | não confirmada | 134 | acquired | [Emissor](https://www.sed.ms.gov.br/programas-e-projetos/novo-ensino-medio/) |
| `ms-if-projeto-vida-2023` | EM | 2023 V.1.0 | — | unavailable | [Emissor](https://www.sed.ms.gov.br/programas-e-projetos/novo-ensino-medio/) |
| `pr-referencial-em-2021` | EM | 2021 | — | unavailable | [Emissor](https://www.educacao.pr.gov.br/Noticia/Educacao-aprova-referencial-curricular-e-diretrizes-complementares-do-Novo-Ensino-Medio) |
| `pr-referencial-eief-2018` | EI, EF | 2018 | 901 | acquired | [Emissor](https://www.referencialcurriculardoparana.pr.gov.br/) |
| `rs-rcg-ef` | EF | não confirmada | 1379 | acquired | [Emissor](https://educacao.rs.gov.br/) |
| `rs-rcg-em` | EM | 2021 | 287 | acquired | [Emissor](https://www.ceed.rs.gov.br/resolucao-0361) |
| `rs-rcg-em-jul22` | EM | não confirmada | 287 | acquired | [Emissor](https://www.ceed.rs.gov.br/resolucao-0361) |
| `sc-cb-eief-2019` | EI, EF | 2019 | — | unavailable | [Emissor](https://www.sed.sc.gov.br/professores-e-gestores/bncc-e-curriculo-base-da-educacao-infantil-e-do-ensino-fundamental-do-territorio-catarinense/) |
| `mt-drc-ei-2018` | EI | 2018 | 76 | acquired | [Emissor](https://www.pedrapreta.mt.gov.br/Portal-Educacao/Documentos-curriculares-24) |
| `sc-cb-em-caderno-1` | EM | não confirmada | 124 | acquired | [Emissor](https://www.sed.sc.gov.br/professores-e-gestores/propostas-curriculares-de-sc-e-curriculo-base/) |
| `sc-cb-em-caderno-2` | EM | não confirmada | 212 | acquired | [Emissor](https://www.sed.sc.gov.br/professores-e-gestores/propostas-curriculares-de-sc-e-curriculo-base/) |
| `sc-cb-em-caderno-3` | EM | não confirmada | 344 | acquired | [Emissor](https://www.sed.sc.gov.br/professores-e-gestores/propostas-curriculares-de-sc-e-curriculo-base/) |
| `sc-cb-em-caderno-4` | EM | não confirmada | 360 | acquired | [Emissor](https://www.sed.sc.gov.br/professores-e-gestores/propostas-curriculares-de-sc-e-curriculo-base/) |
| `sc-cb-eief-2019-atual` | EI, EF | 2019 | 492 | acquired | [Emissor](https://www.sed.sc.gov.br/professores-e-gestores/propostas-curriculares-de-sc-e-curriculo-base/) |
| `sc-lingua-inglesa-ai` | EF | 2026 (capa conferida) | 31 | acquired | [Emissor](https://www.sed.sc.gov.br/professores-e-gestores/propostas-curriculares-de-sc-e-curriculo-base/) |
| `sc-resolucao-070-2025` | EM | 2025 | 18 | acquired | [Emissor](https://www.cee.sc.gov.br/index.php/downloads/documentos-diversos/curriculo-base-do-territorio-catarinense/) |
| `sc-parecer-446-2025` | EM | 2025 | 5 | acquired | [Emissor](https://www.cee.sc.gov.br/index.php/downloads/documentos-diversos/curriculo-base-do-territorio-catarinense/) |
| `ms-educacao-digital-v13` | EI, EF, EM | V1.3 | 611 | acquired | [Emissor](https://www.sed.ms.gov.br/informativos/guias-e-manuais/) |
| `mt-drc-ef-2018` | EF | 2018 | 151 | acquired | [Emissor](https://www.pedrapreta.mt.gov.br/Portal-Educacao/Documentos-curriculares-24) |
| `mt-drc-em-2021` | EM | 2021 | 771 | acquired | [Emissor](https://sites.google.com/view/novo-ensino-medio-mt/drcmt-em-documento-homologado) |
| `pr-deliberacao-0325` | EM | 2025 | 81 | acquired | [Emissor](https://www.cee.pr.gov.br/Pagina/2025-Deliberacoes) |
| `pr-referencial-em-2025` | EM | 2025 | 924 | acquired | [Emissor](https://www.cee.pr.gov.br/Pagina/2025-Deliberacoes) |
| `pr-referencial-eief-2025` | EI, EF | 2025 | 1028 | acquired | [Emissor](https://www.cee.pr.gov.br/Pagina/2025-Deliberacoes) |
| `pr-deliberacao-0725` | EI, EF | 2025 | 8 | acquired | [Emissor](https://www.cee.pr.gov.br/Pagina/2025-Deliberacoes) |
| `pr-referencial-em-volume1-atual` | EM | 2025 | 105 | acquired | [Emissor](https://professor.escoladigital.pr.gov.br/ensino-medio-paranaense) |
| `pr-referencial-em-volume2-atual` | EM | 2025 | 676 | acquired | [Emissor](https://professor.escoladigital.pr.gov.br/ensino-medio-paranaense) |
| `pr-referencial-em-volume3-atual` | EM | 2025 | 142 | acquired | [Emissor](https://professor.escoladigital.pr.gov.br/ensino-medio-paranaense) |
| `df-catalogo-ifa-2026` | EM | 2026 | 552 | acquired | [Emissor](https://www.educacao.df.gov.br/ensino-medio-2) |
| `df-orientador-if-2025` | EM | 2025 | 65 | acquired | [Emissor](https://www.educacao.df.gov.br/ensino-medio-2) |
| `df-catalogo-pee` | EM | não confirmada | 272 | acquired | [Emissor](https://www.educacao.df.gov.br/ensino-medio-2) |
| `df-competencias-digitais-vol1` | EI, EF, EM | não confirmada | 64 | acquired | [Emissor](https://www.educacao.df.gov.br/pedagogico-curriculo-em-movimento/) |
| `df-competencias-digitais-vol2` | EI | não confirmada | 77 | acquired | [Emissor](https://www.educacao.df.gov.br/pedagogico-curriculo-em-movimento/) |
| `df-competencias-digitais-vol3` | EF | não confirmada | 140 | acquired | [Emissor](https://www.educacao.df.gov.br/pedagogico-curriculo-em-movimento/) |
| `df-competencias-digitais-vol4` | EM | não confirmada | 91 | acquired | [Emissor](https://www.educacao.df.gov.br/pedagogico-curriculo-em-movimento/) |
| `df-competencias-digitais-vol5` | EF, EM | não confirmada | 46 | acquired | [Emissor](https://www.educacao.df.gov.br/pedagogico-curriculo-em-movimento/) |
| `rs-rcg-ei-2018` | EI | 2018 V1 | 142 | acquired | [Emissor](https://www.ceed.rs.gov.br/resolucao-n-0345-2018) |
| `sc-cb-em-caderno-5` | EM | Versão preliminar 2022 (portal indica em revisão) | 824 | acquired | [Emissor](https://www.sed.sc.gov.br/etapas-e-modalidades-de-ensino/novo-ensino-medio/) |
| `sc-cb-em-caderno-6` | EM | não confirmada | 638 | acquired | [Emissor](https://www.sed.sc.gov.br/etapas-e-modalidades-de-ensino/novo-ensino-medio/) |
| `sc-educacao-digital` | EI, EF, EM | 2026 | 484 | acquired | [Emissor](https://www.sed.sc.gov.br/programas-e-projetos/curriculo-de-educacao-digital-de-santa-catarina/) |
| `mt-drc-concepcoes-2018` | EI, EF | 2018 | 138 | acquired | [Emissor](https://sites.google.com/view/bnccmt/educa%C3%A7%C3%A3o-infantil-e-ensino-fundamental/documento-de-refer%C3%AAncia-curricular-para-mato-grosso) |
| `mt-drc-ei-primario-2018` | EI | 2018 | 76 | acquired | [Emissor](https://sites.google.com/view/bnccmt/educa%C3%A7%C3%A3o-infantil-e-ensino-fundamental/documento-de-refer%C3%AAncia-curricular-para-mato-grosso) |
| `mt-drc-ef-ai-primario-2018` | EF | 2018 | 151 | acquired | [Emissor](https://sites.google.com/view/bnccmt/educa%C3%A7%C3%A3o-infantil-e-ensino-fundamental/documento-de-refer%C3%AAncia-curricular-para-mato-grosso) |
| `mt-drc-ef-af-2018` | EF | 2018 | 319 | acquired | [Emissor](https://sites.google.com/view/bnccmt/educa%C3%A7%C3%A3o-infantil-e-ensino-fundamental/documento-de-refer%C3%AAncia-curricular-para-mato-grosso) |
| `go-matriz-orientador-2026` | EI, EF, EM | 2026 retificado | 115 | acquired | [Emissor](https://goias.gov.br/educacao/ensino-medio-goiano/) |
| `go-eletivas-2026` | EM | 2026 | 127 | acquired | [Emissor](https://goias.gov.br/educacao/ensino-medio-goiano/) |
| `go-eletivas-fic-2026` | EM | 2026 | 35 | acquired | [Emissor](https://goias.gov.br/educacao/ensino-medio-goiano/) |

| `ms-projeto-vida-orientacoes-2024` | EF, EM | 2024 | 127 | acquired | [Emissor](https://www.sed.ms.gov.br/programas-e-projetos/novo-ensino-medio/) |

## Evidência de integridade executada

Conferência do cache em 28/10/2026, evidência `source-audit-central-south/source-integrity.json`: 58 fontes cadastradas, 55 PDFs adquiridos e parseáveis, 49 documentos/partes obrigatórios, 48 obrigatórios adquiridos. SHA256 dos 55 arquivos: **zero divergências e zero arquivos ausentes**. Volume total de 659.023.349 bytes e 19.365 páginas físicas (inclui representações alternativas preservadas). Reconciliação documental integral concluída em **5 fontes**: `sc-parecer-446-2025` (cinco páginas/seis seções), `sc-lingua-inglesa-ai` (31 páginas, 362 registros esperados e verificados), `sc-resolucao-070-2025` (18 páginas/27 artigos/cinco capítulos, 53 registros) e os volumes digitais DF EI/EF (77/140 páginas, 626/1.321 registros). Todas passaram no gate V2 da revisão1.5, com união exata e hashes de texto primário conferido antes da extração. Autoria de verificação automatizada explícita; não representa revisão pedagógica humana nem prontidão de SC. Em MS Projeto de Vida 2024, os três organizadores completos (AI/AF/EM) estão reconciliados: 245+207+229=681 registros; fundamentos e fechamento continuam pendentes reais. Um obrigatório permanece sem artefato PDF legível (`ms-if-projeto-vida-2023`).

## Adaptadores documentais e integração verificada

DF: 2.659 objetivos das colunas originais EI/EF e 406 nós de cabeçalhos literais foram importados pelo pipeline real (3.065 IDs únicos, zero pais ausentes, zero alteração de texto/evidência/posição das folhas). SC: 2.906 registros em cinco fontes foram conferidos fragmento a fragmento com os PDFs; o Caderno 3 inclui 1.157 registros, e os 400 objetivos do Caderno 4 estão vinculados aos 25 roteiros efetivamente declarados. Os tipos distinguem aprendizagem, palavra-chave, estrutura e fragmentos incompletos originais. Os cinco wrappers de hierarquia de SC passaram pelo importador/finalizador real: 2.906 folhas preservadas e 1.498 nós adicionais, sem pais ausentes, ciclos ou alteração dos IDs, textos, evidências, posições e contextos das folhas. A fonte complementar de Língua Inglesa foi posteriormente ampliada e reconciliada integralmente, conforme abaixo.

Os adaptadores independentes de PR (3.971 registros), RS EM (121), SC EPT/Magistério (6.314), GO EM (443) e MS Projeto de Vida 2024 (681) estão referenciados no manifesto. Suas provas e limites estão nos relatórios próprios; a incorporação ao bundle nacional final e a reconciliação de todas as partes permanecem etapas distintas. O novo complemento MS 2024 não substitui a ementa obrigatória de 2023 ainda inacessível. A versão de MS 2024 usa somente cabeçalhos visíveis: texto nativo oculto sob preenchimentos posteriores foi excluído do posicionamento.

## Fechamentos documentais de partes acessíveis

Língua Inglesa dos Anos Iniciais de SC: inventário independente das 31 páginas, 78 células de aprendizagem/143 parágrafos originais, seis competências específicas numeradas, cinco definições de eixos e 25 ocorrências de organizadores. O wrapper final contém 338 registros próprios; 24 seções de página geradas pelo pipeline completam 362/362 registros esperados. As 143 habilidades mantêm seus IDs, texto, evidências e posições. A capa teve sua camada textual truncada confrontada com OCR real do raster, página de rosto e render original; a edição visível é 2026. As páginas 2, 8, 10 e 30 são brancas; 31 contém somente grafismo, conferido por render e OCR. A varredura integral de blocos nativos confirmou zero palavras omitidas e zero texto invisível nos 143 parágrafos. Provas em `docs/evidence/source-audit-sc-li-complete/`; reconciliação em `data/manifests/reconciliation/sc-lingua-inglesa-ai.json`.

MS Projeto de Vida 2024: o denominador independente construído antes da leitura do adaptador identifica 73 quadros, 141 habilidades físicas e 226 pilares/objetos nos três organizadores completos. Os 681 IDs foram derivados da gramática pública de chaves e importados/finalizados sem pais ausentes; 508 verificações independentes passaram. As páginas substantivas 1–49 e referências/fechamento 126–127 ainda exigem conferência integral própria. Prova em `docs/evidence/source-audit-central-south/ms-pv-organizer-reconciliation-verification.json`; o documento inteiro permanece pendente, sem substituir a ementa obrigatória de 2023 indisponível.

O helper geométrico RS EI/MS EF está congelado no SHA256 `f85f208c88957570f85fc6802745fff53b358f58c3c2c46a99e5aec1bee16e4e`: 340/340 âncoras RS e 1.737/1.737 MS, todos os 2.162 fragmentos literais/ordenação de glifos conferidos, mais auditoria independente dos 2.077 posicionamentos e 25 verificações abrangentes. O finalizador real preserva todas as posições explícitas. Isso fecha a extração dos escopos tabulares comprovados; não declara os fundamentos narrativos das fontes nem uma UF pronta.

Resolução SC070/2025: os 27 artigos sequenciais, cinco capítulos, preâmbulo, identificação e encerramento foram inventariados no original antes da importação. O texto de todas as 18 páginas foi cotejado integralmente; os renders Poppler das 18 páginas foram inspecionados, inclusive a continuação de artigos e o bloco nativo que mescla o título do capítulo IV ao artigo16. São 35 nós normativos mais 18 páginas documentais, 53/53 verificados no gateV2. A data do ato é 25/11/2025; o artigo24 estabelece implementação a partir do ano letivo de2026, e o artigo27 vincula vigência à publicação cuja data não foi comprovada. Fonte emissora corrigida para Conselho Estadual de Educação de SC. Provas: `docs/evidence/source-audit-sc/sc-res070-*`.

DF digital EI/EF: após revisão independente das fronteiras, o adaptador corrigido tem 1.189 objetivos e 375 nós, mais 172 contextos de fundamentos, créditos, referências, premissas e capas: 1.736 registros. Com as 211 seções documentais de página, o core1.5 produz 1.947 registros, todos com evidência literal e pais resolvidos. Cada uma das 211 páginas nativas teve ID e texto exato derivados do original antes da extração. O censo independente conservador1175 recebeu14 fronteiras físicas revisadas, resultando1189; o falso split “Localizar o Sistema” / “Solar na nossa galáxia.” foi rejeitado. A regra morfológica isolada foi removida; a versão1.2 usa terminal/espaçamento tipográfico e somente três quebras de página documentadas. Todos1563 objetos não afetados permanecem idênticos, incluindo IDs/locators/textos/evidências/posições/contexto. O primeiroID da frase mesclada foi preservado, o falso segundo supersedido, sem renumerar os objetivos posteriores. Isso corrige a extração, não a edição normativa.

As capas gráficas p2 contêm texto: cinco recortes reais de OCR preservam quatro linhas do título e a marca vertical de volume; uma transcrição visual I/l de “III” está explicitada com OCR bruto e confronto da primeira capa nativa. As páginas6 são somente padrão decorativo. Os quatro itens declarados “premissas” e guias à prática do professor permanecem orientações metodológicas, com papel literal registrado. Todas as1.189 fronteiras, cadeias de pais, colunas, eixos, componentes, temas e ordem passaram em auditoria independente; testes negativos de join/split que conservavam todas as palavras e de pai existente errado foram rejeitados. Ambos os volumes passaram no gate de fonte inteira V2 (626/626EI e1.321/1.321EF), com375 chaves estruturais derivadas dos cabeçalhos originais e hashes de texto primário. Recibos ativos em `data/manifests/reconciliation/df-competencias-digitais-vol2.json` e `...vol3.json`; prova, comandos, pins anteriores e fusão em `docs/evidence/source-audit-df-digital-candidate-v1.2/`. A incorporação ao corpus nacional atualizado e verificação de runtime permanecem distintas; nenhuma UF foi declarada pronta.

Os três organizadores de MS2024 passaram também no gateV2/1.5 com681 hashes UTF-8 construídos do modelo primário independente antes da leitura do adaptador,827 evidências vinculadas, e rejeição de mutações de palavra/diacrítico. As partes narrativas continuam pendentes reais. A nova tentativa ordinária de MS2023 às17:31UTC manteve o bloqueio: URL direta e download=1 retornaram HTML após redirecionamento; o REST oficial ainda declara o PDF63.530.818bytes. Evidência `source-audit-central-south/ms2023-latest-ordinary-retry.json`.

Renders dos documentos originais permanecem privados e ignorados por Git/Docker; seus hashes, dimensões e caminhos locais constam em `source-audit-central-south/private-primary-image-inventory.json`. Não foram redistribuídos como capturas públicas do produto.
