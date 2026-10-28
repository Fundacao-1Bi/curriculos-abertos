# Fontes BNCC e Sudeste — execução e conferência documental

Checkpoint 2026-10-28T04:58:13.362695+00:00. Responsável: agente `data_bncc_southeast`, ator automatizado. Propriedade: manifesto bncc-southeast, snapshots BR/ES/MG/RJ/SP e este relatório.

Foram adquiridos 54 PDFs reais, 11.499 páginas e 167.375.665 bytes. Hashes SHA-256 e URLs efetivas estão em `data/manifests/bncc-southeast.json`. Essa aquisição não declara UFs prontas nem substitui estruturação/reconciliação integral.

| Jurisdição | Fontes adquiridas | Páginas | Etapas no inventário | Estado |
|---|---:|---:|---|---|
| BR | 5 | 734 | EF, EI, EM | adquirido; extração e reconciliação em andamento |
| ES | 33 | 4271 | EF, EI, EM | adquirido; extração e reconciliação em andamento |
| MG | 5 | 1436 | EF, EI, EM | adquirido; extração e reconciliação em andamento |
| RJ | 6 | 4266 | EF, EI, EM | adquirido; extração e reconciliação em andamento |
| SP | 5 | 792 | EF, EI, EM | adquirido; extração e reconciliação em andamento |

## Inventário e escolhas documentais

- **São Paulo:** volumes ISBN da EI/EF e EM, publicados no índice oficial, mais Educação Digital e Midiática disponibilizada em 2026. Os volumes completos foram preservados; inclui FGB, itinerários e formação técnica/profissional presentes no EM. Homologações 2019/2020 são informadas pelo portal; o upload de 2023 não é tratado como nova vigência.
- **Espírito Santo:** nove volumes EI/EF (EI revisado em 2026 conforme título), FGB EM separada em seis documentos, temas integradores, IFAs disponibilizados em 2025, aprofundamentos anteriores, EPT integrado e normas de aprovação. Transição/vigência entre aprofundamentos anteriores e IFAs precisa de reconciliação; não foi inventada substituição automática.
- **Minas Gerais:** EI/EF versão atualizada, EM completo em publicação atual do Portal Pedagógico, complemento Computação (primeira versão), documento orientador EM2026 e resolução de matrizes2026. O orientador não substitui o currículo. Os documentos selecionados são integrais, inclusive seções normativas sem código, modalidades e anexos incorporados.
- **Rio de Janeiro:** DOC2019 EI/EF (508 páginas), referencial EM, itinerários (1679 páginas), regular integral/técnico (1729 páginas) e laboratórios de Linguagens/CHSA publicados pela fonte institucional. O referencial EM incorpora seções EJA/privação/socioeducação e anexos Ensino Religioso: mantidos no inventário, sem apagar partes integradas por conveniência. O índice detalhado dos anexos do arquivo1729p permanece pendente.
- **BNCC:** cópia de 600 páginas e anexo Computação de75 páginas do snapshot `bncc-dev/bncc-dados` commit `9c268978efa2aa250834c6a9edb6074432752838`. Os hashes conferem com o manifesto de fontes daquele projeto. Também foram obtidas DCNEM2024 e parâmetros IFA2025, cópias normativas oficiais republicadas pela SEE-MG. Revisões posteriores e vigência integral precisam continuar verificadas; data de upload não basta.

## Obtenção, alternativas e direitos

A página inicial MEC retornou403 na pesquisa; URLs antigas de BNCC em gov.br devolveram HTML/404. O PDF RJ EI/EF no domínio MEC foi acessível diretamente. A BNCC completa/anexo foram obtidos de cópia procedente fixada por commit e checksum; a URL primária e o impedimento original permanecem no manifesto. O espelho UFES consultado tem versão EI/EF anterior, sem EM, por isso não substituiu o PDF nacional completo.

O portal antigo Novo Ensino Médio RJ falhou na validação TLS por certificado expirado. A validação não foi desativada. A alternativa legítima foi o Google Sites em domínio institucional `educa.rj.gov.br`, que publica os links dos PDFs no Drive; downloads e hashes foram registrados. O endpoint legado MG EM devolveu HTML; o PDF foi recuperado no atual Portal Pedagógico da SEE-MG. Todos os 54 arquivos deste inventário foram adquiridos; não há fonte deste lote marcada indisponível, embora validação de abrangência/vigência continue aberta.

Os PDFs são de terceiros e permanecem em `data/raw/` ignorado no Git; o manifesto não concede nova licença sobre eles. Dados estruturados reutilizados de **bncc.dev (mantido pela Profy)** são CC BY4.0, conforme `dados/LICENSE.md` daquele projeto; código upstream MIT. Atribuir o repositório e preservar a licença da compilação. Não apresentar os PDFs sob uma licença global do projeto.

## Evidência independente e adapter sem códigos

- `data/manifests/southeast-code-inventory.json`: índice independente de todas as menções de códigos por página em49 documentos curriculares, preservando códigos locais, EM13LP de dois dígitos, EMIF e sufixos. Inclui referências e exemplos; **não é contagem de aprendizagens nem denominador de completude**. Cinco documentos normativos adicionais não têm índice curricular de códigos.
- `inventory_evidence` em cada fonte contém localizadores de sumários/índices, número de páginas e método de conferência. `stage_component_inventory` separa campos EI de componentes EF.
- `docs/evidence/source-audit-southeast/expected.json`:16 amostras dirigidas com código completo, texto lido visualmente da página rasterizada, posicionamento explícito quando há, checksum e captura. Tipo de revisor: automatizado. Não há revisão pedagógica humana.
- `docs/evidence/source-audit-southeast/extraction-audit-v13.json`: confronto executado contra cachesv1.3; SP EM13LP02A/B confirmadas, inclusive continuação75→76. O relatório distingue falha de extração de cache ainda não produzido. Reexecutar contra a revisão final após correções.
- `data/manifests/uncoded/rj-ei-rights.json`:30 direitos reais sem código, seis direitos nomeados em cada um dos cinco campos EI. Script reprodutível `data/manifests/uncoded/extract_rj_ei_rights.py`. Execução conferiu30/30 textos literais na página oficial. Nenhum código BNCC foi inventado; anos/grupos etários não declarados permanecem nulos. Esses30 direitos não representam a totalidade da EI do documento.

Comando executado:

```sh
.venv/bin/python data/manifests/uncoded/extract_rj_ei_rights.py
```

Resultado: `items=30`, `literal_checks_passed=30`.

## Problemas sistemáticos encontrados e encaminhados à integração

| Problema | Evidência | Encaminhamento |
|---|---|---|
| LP EM tem código com2 dígitos, não3 | EM13LP01 no ES p3 e RJ p32 | Regex e reprocessamento integral corrigidos pelo pipeline; conferir revisão final. |
| Sufixos canônicos truncados | ES EM13LGG101ARTa/ES p9; MG EM13LGG106MG p118 | Preservar caixa, letras, /ES, MG e asteriscos. |
| Itinerários não usam apenas padrão BNCC | ES EMIFACNT201 p26, MG EMIFCG01 | Adicionar padrões reais EMIF e contexto EM sem inferir ano. |
| Exemplos de códigos viravam habilidades | SP30/SP EM49;MG45–46/153–154;ES69 | `non_curricular_code_pages` preserva seções explicativas e exclui como novas habilidades. |
| Heurística de mínimo5 palavras perdia habilidade curta | SP EF01LP06 p85: Segmentar oralmente as palavras. | Remover o corte em célula curricular comprovada. |
| Habilidade atravessa páginas | SP EM13LP02B p75–76 | Costura por coluna/célula; confirmação visual e teste textualv1.3 passaram. Ponto após contribuam. é da edição, mantido. |
| Colunas de explicação contaminavam texto | MG Computação EM13CO01 p118 | `layout_rules` isola primeira coluna no anexo EM118–125. Auditoria v1.3 detectou falha; reprocessamento posterior necessário. |
| Detector de tabela fragmenta coluna em linhas falsas | ES EM p9, só uma de sete habilidades virava item | `layout_rules` com geometria das colunas; âncoras de todasp9–101 medidas. Reprocessar e conferir. |
| Texto rotacionado embaralhado | RJ EM p32, rotation90 | `remove_rotation()` em memória mantém aspecto visual e recupera ordem textual; fallback precisa reconhecer códigos prefixados por rótulos. |
| EI sem códigos desaparecia das consultas | RJ EI35–110, nenhuma ocorrência EI no texto | Adapter de30 direitos reais + `structure_sections`; restante da estrutura/orientações deve ser reconciliado. |
| Correspondências por regra precisam origem explícita | SP30/SP EM49;MG45–46/153–154 |7 `code_rules` com origem regra_explicada_fonte, evidências e escopo; nunca equivalência automática. |

## Continuidade e pendências

A aquisição e os inventários preliminares estão executados. A reconciliação de cada documento/parte/componente permanece aberta até corrigir o conjunto e confrontar todas as partes esperadas. Não foram fabricados `expected_item_ids` a partir do que o parser conseguiu extrair. As16 amostras não cobrem por si só todos os componentes deste lote e não aprovam uma UF.

Próximo passo: pipeline reprocessar fontes afetadas com rules/adapter/rotação, importar os30 direitos, confrontar expectativas visuais contra o cache final, conferir todos os componentes e registrar reconciliações independentes por parte com hash/revisão. Avaliar edições e alterações normativas posteriores nos índices oficiais.

## Fontes adquiridas

| ID | Etapas | Páginas | Título e fonte oficial |
|---|---|---:|---|
| `sp-curriculo-eief-isbn` | EI,EF | 401 | [Currículo Paulista — Educação Infantil e Ensino Fundamental](https://efape.educacao.sp.gov.br/curriculopaulista/) |
| `sp-curriculo-em-isbn` | EM | 301 | [Currículo Paulista — Etapa Ensino Médio](https://efape.educacao.sp.gov.br/curriculopaulista/) |
| `sp-educacao-digital-midiatica-2026` | EI,EF,EM | 74 | [Educação digital e midiática — Currículo Paulista](https://efape.educacao.sp.gov.br/curriculopaulista/) |
| `mg-crmg-eief-atualizada` | EI,EF | 603 | [Currículo Referência de Minas Gerais — Educação Infantil e Ensino Fundamental — versão atualizada](https://portalpedagogico.educacao.mg.gov.br/estrutura-curricular-e-ensino/curriculo-referencia-de-minas-gerais/) |
| `mg-crmg-em` | EM | 496 | [Currículo Referência de Minas Gerais — Ensino Médio](https://portalpedagogico.educacao.mg.gov.br/estrutura-curricular-e-ensino/ensino-medio/principais-legislacoes-ensino-medio/) |
| `es-resolucao-cee-es-no-5-190-2018-ei-e-ef` | EI,EF | 13 | [RESOLUÇÃO CEE-ES Nº 5.190-2018 EI e EF](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-resolucao-cee-es-no-5-777-2020-ensino-medio` | EM | 2 | [RESOLUÇÃO CEE-ES Nº. 5.777-2020 Ensino Médio](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curriculo-es-2020-vol-01-educacao-infantil-rev2026` | EI | 140 | [Educação Infantil – Volume 1](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-tema-integrador-final-24-10` | EI,EF,EM | 15 | [Tema Integrador](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curr-culo-es-2019-vol-02-ensino-fundamental-anos-iniciais-rea-de-ci-ncias-da-natureza-e-matem-tica-m` | EF | 210 | [Área de Ciências da Natureza e Matemática – Volume 2](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curr-culo-es-2019-vol-03-ensino-fundamental-anos-iniciais-rea-de-ci-ncias-humanas-e-ensino-religioso` | EF | 226 | [Área de Ciências Humanas e Ensino Religioso – Volume 3](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curr-culo-es-2019-vol-04-ensino-fundamental-anos-iniciais-rea-de-linguagens-arte-e-educa-o-f-sica-mi` | EF | 226 | [Área de Linguagens, Arte e Educação Física – Volume 4](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curr-culo-es-2019-vol-05-ensino-fundamental-anos-iniciais-rea-de-linguagens-l-ngua-portuguesa-miolo` | EF | 190 | [Área de Linguagem, Língua Portuguesa – Volume 5](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curr-culo-es-2020-vol-06-ensino-fundamental-anos-finais-rea-de-ci-ncias-da-natureza-e-matem-tica-mio` | EF | 208 | [Área de Ciências da Natureza e Matemática – Volume 6](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curr-culo-es-2020-vol-07-ensino-fundamental-anos-finais-rea-de-ci-ncias-humanas-e-ensino-religioso-m` | EF | 280 | [Área de Ciências Humanas e Ensino Religioso – Volume 7](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curr-culo-es-2020-vol-08-ensino-fundamental-anos-finais-rea-de-linguagens-arte-educa-o-f-sica-e-l-ng` | EF | 318 | [Área de Linguagens, Arte, Ed. Física e Língua Inglesa – Volume 8](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curr-culo-es-2020-vol-09-ensino-fundamental-anos-finais-rea-de-linguagens-l-ngua-portuguesa-miolo` | EF | 298 | [Área de Linguagens – Volume 9](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-em-texto-introdut-rio` | EM | 38 | [Texto Introdutório — Ensino Médio — Currículo do Espírito Santo](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-em-linguagens` | EM | 109 | [Linguagens — Ensino Médio — Currículo do Espírito Santo](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-em-l-ngua-portuguesa` | EM | 107 | [Língua Portuguesa — Ensino Médio — Currículo do Espírito Santo](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-em-ci-ncias-da-natureza` | EM | 58 | [Ciências da Natureza — Ensino Médio — Currículo do Espírito Santo](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-em-ci-ncias-humanas` | EM | 75 | [Ciências Humanas — Ensino Médio — Currículo do Espírito Santo](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-em-matem-tica` | EM | 30 | [Matemática — Ensino Médio — Currículo do Espírito Santo](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-orientacoes-para-elaboracao-dos-projetos-integradores-3` | EM | 13 | [ORIENTAÇÕES PARA ELABORAÇÃO DOS PROJETOS INTEGRADORES DOS IFAS](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-ifa-das-quatro-areas-do-conhecimento-finalizado` | EM | 275 | [LINGUAGENS E SUAS TECNOLOGIAS, CIÊNCIAS HUMANAS E SOCIAIS APLICADAS, CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS, MATEMÁTICA E SUAS TECNOLOGIAS](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-ifa-lingchsa-6-1` | EM | 265 | [LINGUAGENS E SUAS TECNOLOGIAS, CIÊNCIAS HUMANAS E SOCIAIS APLICADAS](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-ifa-cntmat` | EM | 173 | [MATEMÁTICA E SUAS TECNOLOGIAS E CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curriculo-em-aprofundamento-da-area-matematica-alterado-15-09-23` | EM | 60 | [Documento Curricular “EDUCAÇÃO FINANCEIRA E FISCAL (Matemática)”](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-referenciais-curriculares-para-elaboracao-de-itinerarios-formativos-1-1` | EM | 14 | [REFERENCIAIS CURRICULARES PARA A ELABORAÇÃO DE ITINERÁRIOS FORMATIVOS](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curriculo-em-aprofundamento-da-area-cn-alterado-20-04-22` | EM | 120 | [Documento Curricular “ TERRA, VIDA E COSMO (Ciências da Natureza) “](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curriculo-em-aprofundamento-da-area-linguagens-alterado-19-04` | EM | 108 | [Documento Curricular “ MÍDIAS DIGITAIS: LINGUAGENS EM AÇÃO (Linguagens) “](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curriculoem-aprofundamento-da-area-de-chsa` | EM | 98 | [“ MODERNIZAÇÃO, TRANSFORMAÇÃO SOCIAL E MEIO AMBIENTE (Ciências Humanas) “](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curriculo-em-aprofundamento-entreareas-cn-e-linguagens-alterado-20-04-22` | EM | 107 | [Documento Curricular “ O ESPORTE, A CIÊNCIA E SUAS LINGUAGENS (Ciências da Natureza e Linguagens) “](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curriculo-em-aprofundamento-entreareas-cn-chsa-mat-e-linguagens-alterado-20-04-22` | EM | 102 | [Documento Curricular “ ENERGIAS RENOVÁVEIS E EFICIÊNCIA ENERGÉTICA (Ciências da Natureza, Ciências Humanas, Matemática e Linguagens) “](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curriculo-em-aprofundamento-entreareas-chsa-e-linguagens-alterado-20-04-22` | EM | 90 | [Documento Curricular “ NARRATIVAS SOCIOLITERÁRIAS: LITERATURA, ARTE E CIÊNCIAS HUMANAS ESCREVEM O MUNDO (Linguagens e Ciências Humanas) “](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-curriculo-em-aprofundamento-entreareas-chsa-e-cn-alterado-20-04-22` | EM | 96 | [Documento Curricular “HUMANIDADES E RELAÇÕES SOCIOAMBIENTAIS (Ciências da Natureza e Ciências Humanas)“](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-aspiracoes-docentes-versao-revisada` | EM | 143 | [Documento Curricular “ASPIRAÇÕES DOCENTES (Linguagens, Matemática, Ciências da Natureza e Ciências Humanas)“](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `es-em-ept-integrado` | EM | 64 | [EPT Integrado — Ensino Médio — Currículo do Espírito Santo](https://curriculo.sedu.es.gov.br/curriculo/documentos/) |
| `br-bncc-2018` | EI,EF,EM | 600 | [Base Nacional Comum Curricular — Educação Básica](https://basenacionalcomum.mec.gov.br/) |
| `br-bncc-computacao-2022` | EI,EF,EM | 75 | [Computação — Complemento à BNCC](https://basenacionalcomum.mec.gov.br/historico/) |
| `rj-doc-eief-2019` | EI,EF | 508 | [Documento de Orientação Curricular do Estado do Rio de Janeiro — Educação Infantil e Ensino Fundamental](https://basenacionalcomum.mec.gov.br/implementacao/) |
| `mg-crmg-computacao-2025` | EI,EF,EM | 128 | [Referencial Curricular Computação na Educação Básica de Minas Gerais — Primeira Versão](https://portalpedagogico.educacao.mg.gov.br/estrutura-curricular-e-ensino/ensino-fundamental/programas-de-fortalecimento-curricular/) |
| `mg-em-documento-orientador-2026` | EM | 46 | [Documento Orientador do Ensino Médio — 2026](https://portalpedagogico.educacao.mg.gov.br/estrutura-curricular-e-ensino/ensino-medio/principais-legislacoes-ensino-medio/) |
| `mg-matrizes-2026` | EI,EF,EM | 163 | [Resolução SEE nº 5.212 de 19 de novembro de 2025 — Matrizes Curriculares 2026](https://portalpedagogico.educacao.mg.gov.br/estrutura-curricular-e-ensino/ensino-medio/principais-legislacoes-ensino-medio/) |
| `rj-em-curriculo-referencial` | EM | 337 | [Currículo Referencial do Estado do Rio de Janeiro — Ensino Médio](https://sites.google.com/educa.rj.gov.br/ementas2024/orienta%C3%A7%C3%B5es-curriculares/ementas-2025) |
| `rj-em-itinerarios` | EM | 1679 | [Referencial do Ensino Médio para o Estado do Rio de Janeiro — Itinerários Formativos](https://sites.google.com/educa.rj.gov.br/ementas2024/orienta%C3%A7%C3%B5es-curriculares/ementas-2025) |
| `rj-em-integral-tecnico` | EM | 1729 | [Referencial Curricular para o Ensino Médio do Estado do Rio de Janeiro — Regular em Tempo Integral e Cursos Técnicos](https://sites.google.com/educa.rj.gov.br/ementas2024/orienta%C3%A7%C3%B5es-curriculares/ementas-2025) |
| `rj-em-lab-linguagens-2025` | EM | 5 | [Ementas — Laboratório de Linguagens e suas Tecnologias](https://sites.google.com/educa.rj.gov.br/ementas2024/orienta%C3%A7%C3%B5es-curriculares/ementas-2025) |
| `rj-em-lab-humanas-2025` | EM | 8 | [Ementas — Laboratório de Ciências Humanas e Sociais Aplicadas](https://sites.google.com/educa.rj.gov.br/ementas2024/orienta%C3%A7%C3%B5es-curriculares/ementas-2025) |
| `br-dcn-em-2024` | EM | 22 | [Resolução CNE/CEB nº 2, de 13 de novembro de 2024 — Diretrizes Curriculares Nacionais para o Ensino Médio](https://portalpedagogico.educacao.mg.gov.br/estrutura-curricular-e-ensino/ensino-medio/principais-legislacoes-ensino-medio/) |
| `br-ifa-parametros-2025` | EM | 24 | [Resolução CNE/CEB nº 4, de 12 de maio de 2025 — Parâmetros Nacionais para os Itinerários Formativos de Aprofundamento](https://portalpedagogico.educacao.mg.gov.br/estrutura-curricular-e-ensino/ensino-medio/principais-legislacoes-ensino-medio/) |

## Continuação nacional — estrutura tipada além das habilidades codificadas

Os extratores nacionais preservam a organização real dos documentos com `code:null`, número original separado em `source_number`, chaves técnicas e `parent_key`. Cada texto emitido tem página e regiões conferidas no PDF primário.

| Sidecar | Nós sem código | Conteúdo e vínculos |
| --- | ---: | --- |
| `br-bncc-structure.json` | 1.048 | Dez competências gerais, 105 específicas, seis direitos EI, cinco campos com definições completas, nove áreas, 21 componentes, três grupos etários e 879 contextos organizadores: 775 objetos, 77 unidades temáticas, 13 campos de atuação, nove práticas e cinco eixos. Há 1.580 vínculos de habilidades a pais e contextos documentados. |
| `br-computacao-structure.json` | 80 | Sete competências da seção EF e sete específicas EM, três eixos, 59 objetos, etapas e raiz, com 141 vínculos estruturais. As sete competências EF não foram automaticamente atribuídas à EI ou ao EM. |
| `br-ifa-2025-annex.json` | 58 | Anexo curricular completo das páginas PDF 17–24 da Resolução CNE/CEB 4/2025: dez competências comuns, 21 objetivos específicos (seis de Linguagens e cinco de cada outra área), 21 grupos completos de capacidades e seus agrupamentos. |

A compilação de entrada do **bncc.dev (mantido pela Profy)**, CC BY 4.0, permanece com commit, checksums e atribuição em `br-structure-input.json`. Seus rótulos foram conferidos contra texto primário. O campo jornalístico-midiático usa hífen no PDF e barra na planilha reutilizada; a diferença está registrada. Cinco competências exigiram conferência tipográfica dirigida: ligaturas, barra com quebra e hífens lexicais em fim de linha. As páginas PDF 200, 359, 368 e 572 foram rasterizadas e inspecionadas pelo agente. A redação e a pontuação canônicas foram preservadas. Caracteres de controle não imprimíveis da extração são retirados do canônico, mantendo o trecho bruto para auditoria.

O verificador independente passou com 1.128 nós e zero erros: hashes, fragmentos brutos, bbox, texto integral por sequência de glifos, chaves únicas, hierarquia acíclica e pais existentes. O denominador das 115 competências foi conferido contra os numerais físicos das listas no PDF; os seis direitos contra seis bullets; e os 1.721 vínculos contra os códigos curriculares das fontes. Os 879 contextos são o universo do inventário independente das planilhas compiladas, com todos os rótulos localizados no PDF. Isso não comprova, isoladamente, a estruturação de cada parágrafo introdutório.

A auditoria preservou uma diferença editorial relevante: o anexo Computação imprime **EF05CO011** na página PDF 36, enquanto o upstream canonizou `EF05CO11`. O produto mantém o primeiro como código original, o segundo como alias e uma nota editorial, com ID técnico estável. A referência `EM13MAT315`, página 67, aparece numa explicação de relação e não é uma nova habilidade de Computação; está fora do denominador 141.

Comandos executados:

```sh
.venv/bin/python data/manifests/uncoded/extract_br_structure.py
.venv/bin/python data/manifests/uncoded/verify_br_structure.py
.venv/bin/python data/manifests/uncoded/extract_br_ifa_2025.py
.venv/bin/python data/manifests/uncoded/reconcile_br_ifa_2025.py
```

O teste real do pipeline (`extract_bncc_dataset`, `source_uncoded_items`, `finalize_items` e `attach_hierarchy`) passou com **2.907 IDs únicos: 1.721 habilidades e 1.186 nós sem código**. As 1.721 habilidades têm pai resolvido; não há referências de pais ausentes. A reconstrução dos três sidecars foi repetida e manteve os hashes integrais. Isso comprova o contrato de importação com fontes reais; publicação no banco e jornadas do portal são verificações distintas.

Há reconciliação parcial formal das cinco partes do anexo IFA, em `data/manifests/reconciliation/br-ifa-parametros-2025.json`, com denominador físico independente e todos os 58 itens. Os artigos normativos das páginas 1–16 permanecem pendentes. Nenhum código alfanumérico IFA nacional ou equivalência BNCC foi inventado, e a fonte inteira não foi declarada pronta.

As evidências ficam em `docs/evidence/source-audit-southeast/`: `br-structure-reconciliation.json`, `br-ifa-2025-reconciliation.json`, `br-uncoded-loader-test.json`, `br-hierarchy-integration-test.json` e `br-reconstruction-determinism.json`. A conferência das 16 amostras estaduais exige caches da revisão final; a execução inicial v1.4 registrou os 16 como pendentes de cache, sem reaproveitar aprovação de revisão anterior.

### Conferência dirigida da revisão v1.4

`var/venv-pipeline/bin/python docs/evidence/source-audit-southeast/probe_final_revision.py` executa as 16 expectativas visuais independentes contra páginas oficiais reais, usando caches temporários e o finalizador do pipeline. Não substitui os caches integrais nem modifica a publicação. Na última execução, **14 amostras passaram**. A continuação de SP EM13LP02B entre as páginas 75–76 e a separação das colunas de exemplos em MG Computação passaram.

As quatro pendências iniciais de posição foram resolvidas por inventário de cabeçalhos ao longo dos documentos completos: 44 contextos explícitos em ES Linguagens, 52 em ES Língua Portuguesa, 170 em RJ FGB e duas seções de área em ES IFA. O script `enrich_southeast_document_context.py` reconstrói essas declarações com trechos primários. Série EM vem dos cabeçalhos; não foi inferida do código. As seções de área do IFA não recebem série.

A execução inicial mantinha duas pendências: MG EI01EO07MG conserva a quebra física como `progres- sivamente`, e ES EI precisava combinar a célula de código com a célula de objetivo na mesma linha. No documento ES, todos os 105 códigos curriculares das páginas 72–128 foram localizados na coluna física 168–233,5; o texto fica na coluna 233,5–493. Códigos estão centralizados verticalmente na linha, por isso cortar o texto no topo do código perde conteúdo. A regra documental `separate_ruled_row` está registrada para integração do adaptador, com evidência da linha real. Essas pendências impedem declarar a conferência amostral integral aprovada.

Foi também preservada uma relação nacional expressa no anexo Computação: a linha de EM13CO05 contém, na coluna de exemplos da página PDF 67, “Possui relação direta com (EM13MAT315).” As duas páginas espelhadas 66–67 foram inspecionadas visualmente; a evidência em `br-computacao-explicit-reference.json` não a transforma em equivalência ou pré-requisito. Sua publicação aguarda suporte explícito no pipeline.

O adaptador `pipeline/es_ei_rows.py` foi implementado em coordenação com o responsável pelo pipeline. A conferência independente de **todas as 105 ocorrências primárias** passou: 105 objetivos extraídos, zero códigos perdidos, extras ou duplicados e zero divergências de texto contra o recorte completo da célula. A prova contém os 105 registros em `es-ei-physical-rows-check.json`; o comando reproduzível é `var/venv-pipeline/bin/python docs/evidence/source-audit-southeast/verify_es_ei_physical_rows.py`. Essa verificação cobre as tabelas codificadas, sem afirmar a estruturação integral dos parágrafos introdutórios e explicativos. O adaptador foi integrado ao caller compartilhado e a amostra ES passou. A reexecução das 16 amostras registrou 14 aprovadas, mas detectou regressão em RJ: um candidato geométrico truncado passou a impedir o leitor de parágrafos rotulados. A pendência MG de hifenização permanece; o responsável pelo pipeline recebeu o diagnóstico. O resultado atual segue sem aprovação integral da amostra.

### Atualização normativa e matrizes paulistas de 2026

O inventário atual totaliza **54 PDFs, 11.499 páginas e 167.375.665 bytes**, com todos os hashes novamente conferidos. Foi acrescentado o original MEC da Resolução CNE/CEB nº 2, de 21 de março de 2025, sobre educação digital e midiática: 13 páginas, com os artigos 1–42 em sequência. Não substitui o complemento BNCC Computação de 2022 e permanece com reconciliação normativa pendente. Fonte primária: [MEC](https://www.gov.br/mec/pt-br/cne/2025/marco/rceb002_25.pdf).

Em São Paulo, a [Resolução SEDUC nº 156/2025](https://doe.sp.gov.br/executivo/secretaria-da-educacao/resolucao-seduc-n-156-de-28-de-novembro-de-2025-20251129112312201498325) explicita a organização do ano letivo de 2026. O fac-símile oficial CPS contém o corpo completo de 16 artigos na página 21 do DOE, junto de trechos de atos vizinhos, sem os anexos. Os **nove anexos originais** foram obtidos separadamente no PDF de 15 páginas do próprio DOE: matrizes diurno, noturno, PEI de sete e nove horas para MAT/CNT e LGG/CHS, além de formação docente. Alguns títulos ficam no fim da página anterior à tabela, o que exige preservar sua continuidade. As páginas 9, 14 e 15 são realmente brancas: renderização integral com valores 255, sem imagens ou comandos de desenho.

O navegador local estava desabilitado. A alternativa legítima foi a API pública anônima utilizada pelo leitor oficial do DOE: endpoint e ID do anexo foram localizados nos arquivos JavaScript públicos e no JSON público da publicação. O download respondeu PDF sem tokens, cookies, login ou bypass. Os metadados, o fac-símile e o anexo originais estão preservados em `data/raw/SP/`, e as fontes `sp-seduc156-corpo-2026` e `sp-seduc156-anexos-matrizes-2026` estão no manifesto.

A [Resolução SEDUC nº 103, publicada em outubro de 2026](https://doe.sp.gov.br/executivo/secretaria-da-educacao/resolucao-seduc-n-103-de-16-de-outubro-de-2026-20261016112412202211650), prevê adoção das novas matrizes no ano letivo de **2027**, quando determina a revogação da Resolução 156/2025. Não foi aplicada retroativamente a 2026. Esse registro de atualização não constitui revisão jurídica integral de vigência.
