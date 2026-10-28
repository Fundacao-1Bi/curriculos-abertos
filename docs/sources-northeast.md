# Fontes Nordeste — inventário e checkpoint

Inspeção automatizada por `codex:data_northeast`; atualização 2026-10-28T04:54:51.969642+00:00. Nenhuma revisão pedagógica humana foi realizada.

Estado: em execução. 64 entradas, 62 artefatos PDF adquiridos, 16099 páginas físicas de fonte, 624789948 bytes. **0 UFs reconciliadas/ACE-01 prontas** neste lote. Uma cópia de pesquisa AL Computação é privada e explicitamente não publicável enquanto sua procedência integral não for confirmada. Esses totais são de documentos, não de aprendizagens nem prova de completude.

## Cobertura de aquisição

| UF | PDFs adquiridos | Etapas com artefatos | Pendência obrigatória conhecida |
|---|---:|---|---|
| AL | 20 | EF, EI, EM | ReCAL Computação: cópia privada adquirida, cadeia de distribuição primária pendente; atos DOE exigem recorte; 15 complementos EM integrados; reconciliação documental pendente |
| BA | 5 | EF, EI, EM | DCRB-EM2026 aprovado para implementação2027 ainda não localizado; edição2022 preservada como distinta; ato249/2026 reconciliado |
| CE | 5 | EF, EI, EM | Reconciliação de partes/etapas e tabelas giradas; catálogo de trilhas requer OCR |
| MA | 2 | EF, EI, EM | Organizador EM requer correção de tipologia; verificação de complementos/vigência e reconciliação |
| PB | 1 | EF, EI | Ensino Médio: fonte oficial retorna CAPTCHA/JavaScript; parser de objetivos/referências requer correção |
| PE | 5 | EF, EI, EM | Reconciliação de CEDIM e referências/itinerários; cadeia oficial da EI pendente; 8 habilidades História EM verificadas, demais estruturas pendentes |
| PI | 4 | EF, EI, EM | Caderno2 declara versão preliminar; confirmar edição final e Computação EM; corrigir colunas EI e reconciliar |
| RN | 10 | EF, EI, EM | DCEC Computação2026 agora adquirido819p, cadeia oficial confirmada; ato de homologação reconciliado; currículo, estruturas2026, trilhas e IFA ainda em reconciliação |
| SE | 10 | EF, EI, EM | Tabelas de itinerários com fronteiras incorretas; reconciliar Computação e eletivas; distinguir atualização da página e edição |

## Catálogo de artefatos

Os metadados, URLs primárias, tentativas, hashes SHA-256, páginas e caminhos privados estão em `data/manifests/northeast.json`. Os PDFs de terceiros ficam em `data/raw/{UF}/`, ignorados no Git; não são relicenciados. A instalação usa o bundle estruturado produzido pelo pipeline, não downloads externos a cada requisição.

| ID | Etapas | Edição editorial consultada | Estado aquisição | Páginas PDF |
|---|---|---|---|---:|
| `ce-dcrc-ei-ef-2019` | EI, EF | 2019 | acquired | 618 |
| `ce-dcrc-em-2021` | EM | 2021 | acquired | 411 |
| `ce-trilhas-aprofundamento-2023` | EM | 2023 | acquired | 16 |
| `ba-dcrb-ei-ef` | EI, EF | 2020 | acquired | 482 |
| `ba-dcrb-em-vol2-2022` | EM | 2022 | acquired | 563 |
| `pb-pcem` | EM | Não confirmada | unavailable | — |
| `pe-curriculo-em-2021` | EM | 2021 | acquired | 709 |
| `pe-curriculo-ef` | EF | Não confirmada | acquired | 612 |
| `pi-curriculo-ei-ef` | EI, EF | 2020 | acquired | 313 |
| `pi-curriculo-em-caderno1-2021` | EM | 2021 | acquired | 344 |
| `ma-dctm-em-vol2` | EM | 2022 | acquired | 254 |
| `al-recal-ei-2019` | EI | 2019 | acquired | 144 |
| `al-recal-ef` | EF | 2019 | acquired | 738 |
| `al-recal-em` | EM | Não confirmada | acquired | 539 |
| `rn-referencial-em` | EM | 2021 | acquired | 570 |
| `rn-documento-ei-2018` | EI | 2018 | acquired | 177 |
| `pb-proposta-ei-ef` | EI, EF | Não confirmada | acquired | 635 |
| `ma-dctm-ei-ef` | EI, EF | 1ª edição, 2019 | acquired | 482 |
| `rn-documento-ef-2018` | EF | 2018 | acquired | 1103 |
| `pi-curriculo-em-caderno2-2021` | EM | 2021 | acquired | 434 |
| `pi-computacao-ei-ef` | EI, EF | Não confirmada | acquired | 147 |
| `se-curriculo-ei-ef` | EI, EF | 2018 | acquired | 666 |
| `se-curriculo-em` | EM | Não confirmada | acquired | 571 |
| `se-computacao-2026` | EI, EF, EM | 2026 | acquired | 54 |
| `se-bncc-computacao-2025` | EI, EF, EM | 2025 | acquired | 218 |
| `se-natureza-vol2` | EM | Não confirmada | acquired | 90 |
| `se-humanas-vol2` | EM | Não confirmada | acquired | 79 |
| `se-matematica-vol2` | EM | Não confirmada | acquired | 66 |
| `se-linguagens-vol2` | EM | Não confirmada | acquired | 82 |
| `se-linguagens-parte2-vol2` | EM | Não confirmada | acquired | 83 |
| `se-projeto-vida` | EM | Não confirmada | acquired | 21 |
| `ba-matrizes-em-2025` | EM | Não confirmada | acquired | 20 |
| `ba-ementas-itinerarios` | EM | Não confirmada | acquired | 13 |
| `ba-resolucao-249-2026` | EM | 2026 | acquired | 7 |
| `ba-dcrb-em-2026` | EM | 2026 | research_pending | — |
| `pe-curriculo-ei` | EI | 2019 | acquired | 134 |
| `pe-cedim-2026` | EI, EF, EM | 2026 | acquired | 682 |
| `pe-historia-pernambuco-2026` | EM | 2026 | acquired | 8 |
| `ce-dcrc-computacao` | EI, EF, EM | 2026 | acquired | 247 |
| `ce-resolucao-526-2026` | EI, EF, EM | 2026 | acquired | 4 |
| `al-parecer-27-2026-doe` | EI, EF, EM | 2026 | acquired | 152 |
| `al-recal-computacao` | EI, EF, EM | 2025 | acquired / pesquisa privada | 89 |
| `rn-diretrizes-ifa` | EM | Não confirmada | acquired | 167 |
| `rn-trilhas-aprofundamento` | EM | 1ª versão | acquired | 485 |
| `rn-dcec-computacao` | EI, EF, EM | 2026 | acquired | 819 |
| `rn-estrutura-em-2026-diurno` | EM | 2026 | acquired | 15 |
| `rn-estrutura-em-2026-noturno` | EM | 2026 | acquired | 17 |
| `rn-estrutura-em-2026-em_tempo_integral` | EM | 2026 | acquired | 26 |
| `al-matrizes-em-2026` | EM | 2026 | acquired | 44 |
| `al-organizador-fgb-2025` | EM | 2025 | acquired | 125 |
| `al-ifa-pit-1-2026` | EM | 2026 | acquired | 82 |
| `al-ifa-tac-1-2026` | EM | 2026 | acquired | 124 |
| `al-ifa-praticas-lgg-chs-2-2026` | EM | 2026 | acquired | 75 |
| `al-ifa-temas-lgg-chs-2-2026` | EM | 2026 | acquired | 129 |
| `al-ifa-praticas-mat-cnt-2-2026` | EM | 2026 | acquired | 117 |
| `al-ifa-temas-mat-cnt-2-2026` | EM | 2026 | acquired | 122 |
| `al-ifa-praticas-lgg-chs-3-2026` | EM | 2026 | acquired | 56 |
| `al-ifa-temas-lgg-chs-3-2026` | EM | 2026 | acquired | 133 |
| `al-ifa-praticas-mat-cnt-3-2026` | EM | 2026 | acquired | 56 |
| `al-ifa-temas-mat-cnt-3-2026` | EM | 2026 | acquired | 162 |
| `al-projeto-vida-guia-1` | EM | Não confirmada | acquired | 243 |
| `al-projeto-vida-guia-2` | EM | Não confirmada | acquired | 240 |
| `al-projeto-vida-guia-3` | EM | Não confirmada | acquired | 228 |
| `rn-portaria-11123-2025` | EI, EF, EM | 2025 | acquired | 57 |

## Evidências e decisões materiais

- **PB EM — bloqueio externo real:** o portal `paraiba.pb.gov.br` devolve HTTP200 `text/html` com desafio de CAPTCHA/JavaScript em lugar do PDF. Foram tentadas as publicações original, `www`, `copy_of` e `@@download`; o portal MEC alternativo também devolveu desafio. Nenhum controle foi contornado. Snippets de busca não foram usados para preencher aprendizagens. O exemplar do Instituto Unibanco foi usado apenas para descoberta, pois a página informa restrições de download/reprodução. Intervenção mínima: fonte primária alternativa acessível ou arquivo oficial obtido legitimamente com proveniência.
- **BA EM — divergência de edição:** a Resolução CEE249/2026, página1 do PDF adquirido, confirma revisão DCRB-EM2026. O art16, na PDF p7, determina implementação a partir do ano letivo2027; o art22 dá vigência ao ato na publicação. Esses marcos não foram equiparados. O catálogo SEC `https://www.ba.gov.br/educacao/coordenacao-do-ensino-medio` entrega PDF cujo CIP/capa diz2022. O host legado `dcrb.educacao.ba.gov.br` deu timeout TLS; o arquivo2022 foi adquirido legitimamente no novo domínio, preservando essa diferença. A revisão2026 permanece como fonte aprovada pendente com início de aplicação2027; isso não comprova que a edição2022 seja inaplicável em todo o ano2026. Não se excluiu a edição2022 sem esclarecer o escalonamento.
- **CE EI/EF — alternativa oficial resolvida:** o host antigo `www.seduc.ce.gov.br` falhou validação TLS. A publicação oficial movida para `www.ce.gov.br/seduc/wp-content/uploads/sites/63/2020/02/DCRC_2019_OFICIAL.pdf` foi adquirida sem desabilitar verificação de certificado.
- **PI — substituição de caminho resolvida:** `/arquivos/diretrizes/` retornou404; `/download/diretrizes/` entregou PDFs oficiais EI/EF e EM. O caderno2 adquirido traz “VERSÃO PRELIMINAR” na capa; sua homologação não foi presumida.
- **SE — WPDM público:** PDFs adquiridos pelo link público `data-downloadurl` do próprio portal. No manifesto preserva-se URL estável `?wpdmdl=ID`, sem depender do parâmetro efêmero `refresh`; downloads não exigiram autenticação. Datas de atualização da página2026 não foram tomadas como edição dos PDFs.
- **RN — extensão do referencial:** o catálogo oficial contém RCEMP2021, trilhas e diretrizes IFA; página de estruturas acrescenta diurno/noturno/integral2026. Os três documentos2026 foram adquiridos. O DCEC/RN Computação inicialmente retornou403; nova requisição pública às04:44UTC retornou200/PDF e permitiu adquirir819 páginas físicas. A cadeia oficial municipal.gov→SIGEduc→PDF foi confirmada; isto resolve acesso, não reconciliação. O ato estadual de homologação foi adquirido e sua região curricular integral reconciliada, preservando matérias alheias fora do recorte.
- **AL — escopo do Diário Oficial:** o PDF de152p contém matérias não curriculares. Somente parecer27/2026 p34-35 e Resolução10/2026 p36-37 pertencem ao recorte. P37 contém duas colunas: a esquerda segue curricular até o rodapé e a direita encerra a resolução antes da SEFAZ. Cortar a sequência global pelo marcador apagaria os artigos11/12 à esquerda. `page_regions` registra a união ordenada de duas regiões curriculares; até existir implementação e prova de recorte seguro, `include_in_corpus:false` preserva metadados e bloqueia processamento completo do ato. Isso é pendência técnica, não exclusão do conjunto obrigatório.
- **Direitos MA EI/EF:** o próprio PDF declara reprodução permitida com citação da fonte e distribuição gratuita. Demais permissões de redistribuição de PDFs permanecem não estabelecidas, salvo indicação específica em fonte; direitos sobre texto oficial, diagramação e fotos não foram misturados à licença MIT do código.

## Inventário e verificação

`stages`, `components`, `normative_parts`, `index_entries` e `inventory_evidence` registram expectativas observadas em fontes/capas/sumários. Com exceção da fonte específica PE História já reconciliada, os estados de inventário e reconciliação permanecem pendentes: o denominador não foi substituído pelos registros que o parser conseguiu extrair. A leitura inicial não comprova extração integral, associação código/texto em todas as tabelas, OCR ou revisão humana. As partes internas das modalidades que integram o documento principal permanecem dentro do PDF processado; materiais didáticos, cadernos trimestrais e documentos específicos de modalidade fora do referencial principal devem ser classificados separadamente, com justificativa, antes de excluir.

## Retomada executável

1. Usar o manifesto atual, preservando os PDFs já adquiridos por checksum. Não repetir a pesquisa concluída.
2. Executar pipeline para fontes novas e conferir warnings/OCR:

```sh
scripts/data-ingest.sh --source ce-dcrc-computacao --job-id nordeste-computacao
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python pipeline/batch.py --workers 4 --skip-ocr
scripts/data-ingest.sh --cached-only --job-id nacional-nordeste-checkpoint
```

`--skip-ocr` é apenas para extração inicial de PDFs textuais: páginas digitalizadas continuam pendentes e requerem execução posterior com OCR. A reconciliação deve seguir `docs/data-reconciliation.md`, confrontando o inventário independente e preservando o tipo real do revisor.

3. Resolver as fontes obrigatórias pendentes acima; não liberar o gate nacional enquanto houver parte sem processamento/reconciliação.
4. Validar metadados de edição contra capas e atos, amostrar tabelas de todas etapas/componentes, e registrar reprocessamento sistemático quando houver troca de código/texto.

## Auditoria independente de estrutura, código e posição

A aquisição dos arquivos não conclui a reconciliação. O quadro de amostragem em `docs/evidence/source-audit-northeast/audit-report.json` foi construído diretamente de ocorrências nativas dos PDFs, por UF, etapa e componente, antes de consultar os IDs extraídos. Abrange 159 estratos das nove UFs. Ocorrência de código inclui exemplos e referências e **não é o denominador de aprendizagens**.

A primeira execução preservada encontrou muitos caches ainda ausentes. `recheck.py` reaplica os mesmos 159 pontos aos caches atuais, sem selecionar novos exemplos a partir do resultado. A execução v1.3 preservada em `audit-recheck-v1.3.json` inspecionou 110 estratos, encontrou 30 ocorrências ainda sem item codificado correspondente e 19 estratos sem cache. `audit-recheck.json` acompanha separadamente o reprocessamento v1.4; um cache ainda ausente nessa rodada não significa perda confirmada de conteúdo. Entre os itens comparados, 78 passaram na conferência literal de célula; isso não atesta semântica ou completude. Os resultados de candidatos e a disposição histórica individual estão preservados em `finding-dispositions-v1.3.json`. Correções do v1.4 exigem nova conferência; não são consideradas resolvidas apenas por alteração de código.

Foram confirmados os seguintes problemas sistemáticos, encaminhados ao responsável pelo pipeline:

| Fonte e exemplo | Evidência observada | Tratamento necessário |
| --- | --- | --- |
| CE EI/EF, PDF p.344 | Tabela fisicamente girada, com metadado de rotação zero. `find_tables` devolve a coluna lógica HABILIDADES como linha física. EF67EF06 pertence a uma relação, mas recebeu texto `(EF67EF07)`. | Selecionar células pelo papel semântico mesmo com orientação girada; registrar relações separadamente. As aprendizagens reais da linha são EF89EF05 a EF89EF08. |
| CE EM, PDF p.373 | EMIFCG12 recebeu “Meio Ambiente Saúde”, que são temas da coluna seguinte. | Não transformar código de referência e tema vizinho em habilidade. Preservar a organização do itinerário. |
| MA EM vol.II, PDF p.199/204/216 | Coluna HABILIDADES contém códigos de referência; coluna seguinte traz unidade temática. EM13CNT306 recebeu “VIDA, TERRA E COSMOS.” e outros rótulos. | Estruturar o organizador, os conteúdos e suas referências. O cabeçalho HABILIDADES isolado não autoriza usar o texto da coluna seguinte como habilidade nacional. |
| PB EI/EF, PDF p.310 | Código EF06MA07 termina o objetivo na célula esquerda; a célula vizinha contém “Frações.”. | Extrair o trecho anterior ao código dentro da célula de objetivo, preservando continuações e objetivos sem código. |
| PB EI/EF, PDF p.95/139/344 | Objetivos próprios à esquerda e conjuntos de referências BNCC à direita, em relações de vários para vários. | Objetivo local sem código deve manter `code:null`; relações documentadas não são equivalência nem atribuição artificial de um código nacional ao objetivo local. |
| PI EI/EF, PDF p.58 | Limite de célula inclui fragmentos “a/e/es” da coluna de faixa etária. | Separar coluna do objetivo e posição etária explícita; corrigir o conjunto afetado. |
| SE EM, PDF p.327 | Detecção de linhas cria limite vertical dentro da coluna contínua e corta parte do texto de EMIFCG04. | Reconstruir as colunas semânticas das tabelas de itinerários e verificar todas as páginas afetadas. |

As evidências PNG são renderizações dos originais privados, não currículos recriados. Ficam em `var/private-evidence/source-audit-northeast/`, ignoradas no Git; `private-render-inventory.json` conserva seus hashes e caminhos para conferência local. O arquivo `layout-observations.json` registra páginas, geometrias e limites da inferência. A varredura identificou 359 páginas do CE EI/EF com texto girado, código EF e cabeçalho HABILIDADES; não se presume que uma única coordenada resolva todos os componentes.

Também há defeitos de tratamento de hifenização suave e ordem de glifos. A fonte original permanece preservada; não foi feita correção ortográfica por dicionário. O parser deve tratar quebras de linha sem corromper palavras e continuar distinguindo a transcrição literal da normalização usada na busca.

## Convenções da fonte e conflitos documentais

O manifesto registra regras com evidência de página para CE, BA, AL e SE. Regras que apenas explicam códigos locais marcados com sufixo estadual usam `mapping_allowed:false`: numeração local não prova correspondência nacional de mesmo número. A regra baiana de asterisco identifica contextualização declarada pela própria fonte. Figuras ilustrativas de convenções não são inventário de habilidades e estão tipologicamente sinalizadas.

A figura original do CE EI/EF, PDF p.25, contém conflito verificável: repete a sigla EF no campo de espaços/tempos e traz faixas etárias divergentes da convenção nacional. Isso está registrado em `code_convention_conflicts`. Não se corrige silenciosamente o original nem se usa essa figura para declarar todas as posições etárias documentadas; os cabeçalhos efetivos das tabelas precisam ser conferidos.

## Pernambuco: estrutura integral de uma fonte sem códigos

O PDF oficial `pe-historia-pernambuco-2026` tem oito páginas e se refere especificamente ao **IFA de História de Pernambuco do 2º ano do Ensino Médio**. O escopo do manifesto foi corrigido para esse artefato. O componente integra a área de Ciências Humanas e Sociais Aplicadas; a apresentação pede contribuição de História, Geografia, Sociologia e Filosofia.

A fonte foi integralmente inventariada por títulos, subdivisões e bullets, independentemente dos itens codificados do parser. O resultado contém 91 registros tipados: oito habilidades, 13 temáticas, 11 desdobramentos, dez eixos, dez temas transversais, seis produções sugeridas, apresentação, orientações e títulos. Há 90 vínculos hierárquicos e 92 fragmentos de evidência. As habilidades se distribuem em três, duas e três por trimestre; uma continua da PDF p.5 à p.6. Todos os códigos permanecem nulos.

`data/manifests/uncoded/pe-historia-items.json` preserva os textos, série, período e hierarquia. Os IDs foram derivados do inventário documental e do contrato canônico do finalizador. `build-pe-structure.py` permite reconstruir o inventário, e `verify-pe-structure.py` confronta importação, IDs e parentesco com a expectativa independente.

A execução com PyMuPDF1.26.7 e pipelinev1.4 verificou os 91 registros, 92 fragmentos e 90 pais, sem órfãos, warnings ou OCR pendente. As evidências estão em `pe-complete-structure-inventory.json` e `pe-complete-structure-import-check.json`. A reconciliação documental **desta fonte específica** foi concluída por agente automatizado. Isso não atesta completude de PE/EM, do conjunto estadual ou revisão pedagógica humana.

## Alagoas: complementos e apoio didático

As 15 fontes adicionais ligadas ao catálogo oficial foram integradas e tiveram hashes, bytes e páginas revalidados. As dez fontes de IFAs2026 estão ligadas aos componentes TAC/PIT/Temas/Práticas declarados na organização curricular por série. O Organizador FGB tem edição2025 preservada e é explicitamente apresentado como complemento ao ReCAL.

Os três Guias do Educador de Projeto de Vida são **apoio didático opcional**, não partes normativas obrigatórias demonstradas. A própria p.4 os descreve como materiais didáticos, e o catálogo não foi tomado como ato de incorporação normativa. A presença de habilidades próprias não basta para alterar essa tipologia. `mandatory:false`, `document_type:material_didatico_com_objetivos` e a justificativa documental preservam essa distinção; não se exclui o componente Projeto de Vida do currículo obrigatório.

O sidecar opcional conserva 182 ocorrências de habilidades em 75 quadros: 59/58/65 ocorrências por guia, 34/21/23 textos literais distintos por guia e **61 textos literais distintos no conjunto dos três**. Essas contagens não afirmam equivalência semântica nem 182 objetivos únicos. O importador/finalizador verificou as 182 entradas. Fontes, tipologia, inventários e execução estão em `al-2026-inventory.md`, `al-typology-review.json` e `al-pv-verification.json`.

Para repetir a auditoria sem refazer o quadro de amostragem:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-northeast/recheck.py
```

Para reconstruir o quadro a partir dos documentos (execução mais longa):

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-northeast/audit.py
```


## Bahia: ato normativo integral e marco de implementação

A Resolução CEE249/2026 foi estruturada integralmente em 45 partes: 22 artigos, oito capítulos, nove considerandos e demais elementos do ato. O inventário independente atribuiu as 237 linhas originais não vazias exatamente uma vez. Quatro artigos atravessam páginas; seus fragmentos foram preservados. Os registros são normativos, **não habilidades de aprendizagem**.

O cache de sete páginas foi produzido pelo pipelinev1.4/PyMuPDF1.26.7, sem warnings ou OCR pendente. Importação, finalização e evidências passaram para os 45 nós, sem órfãos ou ciclos. A reconciliação documental desse ato específico foi concluída, sem substituir a revisão curricular DCRB-EM2026 que continua pendente de aquisição. Comandos e evidências estão em `ba-resolucao249.md`, `ba-resolucao249-inventory.json` e `ba-resolucao249-verification.json`.

O ato é de 07/07/2026, foi homologado em 26/08/2026 e publicado em 27/08/2026. O art22 estabelece vigência na publicação; o art16 determina implementação da organização curricular a partir do ano letivo2027. A edição DCRB2022 não foi descartada com base apenas na data do ato.


## RN: acesso resolvido, procedência e direitos documentados

O DCEC/RN foi adquirido integralmente após nova requisição pública, sem resolver desafios ou usar autenticação. A [Secretaria municipal oficial](https://antoniomartins.rn.gov.br/secretarias/secretaria-de-educacao/) liga seu Portal SIGEduc; o catálogo público noticia o documento e liga o PDF adquirido. O livro tem edição2026, 819 folhas físicas e 714 pranchas duplas; o sumário usa paginação editorial até1528. Não se tratam de 819 aprendizagens nem de uma reconciliação concluída.

A apresentação declara que o documento complementa os referenciais EI/EF2018 e EM2021 e remete à Portaria-SEI11123/2025. O PDF declara **CC BY-NC-ND**, sem especificar versão, na página física6. As condições de atribuição, não comercialização e ausência de adaptações estão registradas no manifesto; imagens não foram incluídas nos dados estruturados. O original não é relicenciado pela licença MIT do software ou pela licença dos metadados do projeto. Alteração editorial de texto e mera mudança técnica de formato são fatos distintos.

O [DOE13/12/2025](https://webdisk.diariooficial.rn.gov.br/Jornal/12025-12-13.pdf) contém a Portaria-SEI11123/2025 na páginaPDF21. O diário completo fica privado. Somente a região do ato `[28,560,395,800]` entra no corpus: a portaria anterior trata de questão disciplinar e a seguinte de outro órgão. Inspeção visual, inventário de 24 linhas, extração e importação v1.4 verificaram as 12 partes normativas do ato, sem referências a essas matérias vizinhas, órfãos, warnings ou OCR pendente. Este ato foi reconciliado; o currículo de819 páginas permanece em processamento/reconciliação.

Evidências: `rn-dcec-acquisition-and-provenance.json`, `rn-portaria11123-inventory.json` e `rn-portaria11123-verification.json`. As limitações de acesso anteriores são preservadas no histórico de tentativas; não se mantêm como bloqueio atual após a aquisição bem-sucedida. PBEM continua respondendoHTML com desafio na verificação mais recente.
