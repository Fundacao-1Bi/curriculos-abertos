# Fontes Nordeste — inventário e checkpoint

Inspeção automatizada por `codex:data_northeast`; atualização 2026-10-28T17:41:09.134217+00:00. Nenhuma revisão pedagógica humana foi realizada.

Estado: em execução. 90 entradas, 86 artefatos PDF adquiridos, 17486 páginas físicas de fonte, 667622099 bytes. **0 UFs reconciliadas/ACE-01 prontas** neste lote. Oito artefatos têm prova própria V2 no cache atual1.5,423registros/465fragmentos; quatro fecham também suas dependências declaradas(PEHistória,MA181,BA125,BA266). A incorporação em candidato e produção é verificação distinta. Uma cópia de pesquisa AL Computação é privada e não publicável enquanto sua procedência integral não for confirmada. Esses totais são de documentos, não de aprendizagens nem prova de completude.

## Cobertura de aquisição

| UF | PDFs adquiridos | Etapas com artefatos | Pendência obrigatória conhecida |
|---|---:|---|---|
| AL | 20 | EF, EI, EM | Computação cadeia primária; estruturas/DesDP/IFA e atos em reconciliação |
| BA | 7 | EF, EI, EM | DCRB2026 integral não localizado; implementação2027;249 reconciliada, referenciais pendentes |
| CE | 7 | EF, EI, EM | Matrizes2026 adquiridas100p eRes52126p digitalizadas; OCR/reconciliação internos pendentes |
| MA | 4 | EF, EI, EM | 211/181 reconciliados; complemento digital integral faltante; referenciais e GPD/SUGEDA pendentes |
| PB | 3 | EF, EI, EM | 635 e392 sidecars2008/1946 verificados; EM867p adquirido 2026-10-29 (download humano pós-CAPTCHA, SHA d31b7a84…), adaptador próprio 6750 registros ligado com peer PASS; refresh seletivo feito e recibo delta `ca-ce95aa72…` verificado (não promovido); V2 integral pendente |
| PE | 19 | EF, EI, EM | 14partes atuais563p adquiridas; EI cadeia primária; IN03/2026 faltante; CEDIM/hierarquia pendentes |
| PI | 7 | EF, EI, EM | ComputaçãoEM137p e atos8p adquiridos; Res18814nós/peerPASS ligado, refresh/V2 e Parecer190 integral pendentes |
| RN | 10 | EF, EI, EM | Trilhas3851nós sem código/hierarquia e2930links verificados e ligados; FULL/V2 e DCEC completo pendentes |
| SE | 10 | EF, EI, EM | Geometria/glifos corrigidos em recortes provados; FULL e reconciliação pendentes |

## Catálogo de artefatos

Os metadados, URLs primárias, tentativas, hashes SHA-256, páginas e caminhos privados estão em `data/manifests/northeast.json`. Os PDFs de terceiros ficam em `data/raw/{UF}/`, ignorados no Git; não são relicenciados. A instalação usa o bundle estruturado produzido pelo pipeline, não downloads externos a cada requisição.

| ID | Etapas | Edição editorial consultada | Estado aquisição | Páginas PDF |
|---|---|---|---|---:|
| `ce-dcrc-ei-ef-2019` | EI, EF | 2019 | acquired | 618 |
| `ce-dcrc-em-2021` | EM | 2021 | acquired | 411 |
| `ce-trilhas-aprofundamento-2023` | EM | 2023 | acquired | 16 |
| `ba-dcrb-ei-ef` | EI, EF | 2020 | acquired | 482 |
| `ba-dcrb-em-vol2-2022` | EM | 2022 | acquired | 563 |
| `pb-pcem` | EM | Não confirmada | acquired | 867 |
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
| `pe-fgb-trimestral-matematica-c6335b8d` | EM | Não confirmada | acquired | 55 |
| `pe-fgb-trimestral-arte-cb58c164` | EM | Não confirmada | acquired | 37 |
| `pe-fgb-trimestral-educacao-fisica-d997d37c` | EM | Não confirmada | acquired | 59 |
| `pe-fgb-trimestral-lingua-inglesa-360febf4` | EM | Não confirmada | acquired | 32 |
| `pe-fgb-trimestral-lingua-portuguesa-f9f839b5` | EM | Não confirmada | acquired | 103 |
| `pe-fgb-trimestral-filosofia-d3d771c6` | EM | Não confirmada | acquired | 20 |
| `pe-fgb-trimestral-geografia-916f592c` | EM | Não confirmada | acquired | 37 |
| `pe-fgb-trimestral-historia-d8799974` | EM | Não confirmada | acquired | 35 |
| `pe-fgb-trimestral-sociologia-7acc310e` | EM | Não confirmada | acquired | 17 |
| `pe-fgb-trimestral-biologia-7f902274` | EM | Não confirmada | acquired | 32 |
| `pe-fgb-trimestral-fisica-cd2ccadd` | EM | Não confirmada | acquired | 30 |
| `pe-fgb-trimestral-quimica-007bc04c` | EM | Não confirmada | acquired | 24 |
| `pe-ifa-matriz-anexo-i-c4ba842e` | EM | Não confirmada | acquired | 37 |
| `pe-ifa-matriz-anexo-ii-c6f9ef30` | EM | Não confirmada | acquired | 45 |
| `pi-computacao-em-2025` | EM | 2025 | acquired | 137 |
| `ce-matrizes-2026` | EM | 2026 (arquivoV2) | acquired | 100 |
| `ce-resolucao-521-2025` | EM | Resolução nº521/2025 | acquired | 26 |
| `pe-instrucao-normativa-03-2026` | EM | Não confirmada | research_pending | — |
| `pi-resolucao-188-2025` | EI, EF, EM | 2025 | acquired | 2 |
| `pi-parecer-190-2025` | EI, EF, EM | 2025 | acquired | 6 |
| `pb-proposta-ei-ef-cedoc` | EI, EF | Não confirmada | acquired | 392 |
| `ma-resolucao-211-2026-doe` | EI, EF, EM | 2026 (numeração do ato) | acquired | 38 |
| `ma-portaria-181-2026-recomposicao-doe` | EM | 2026 (numeração do ato) | acquired | 100 |
| `ma-dctma-educacao-digital-midiatica` | EI, EF, EM | Não confirmada | research_pending | — |
| `ba-resolucao-266-2025-computacao` | EI, EF, EM | 2025 | acquired | 21 |
| `ba-resolucao-125-2024-historia` | EI, EF, EM | 2024 | acquired | 2 |

## Evidências e decisões materiais

- **PB EM — aquisição ainda pendente:** o PDF oficial abriu normalmente no Chrome com867p e a ficha `/view` declara `application/pdf`,7.6MB e modificação25/04/2023 (esta não é data editorial). O botão Download próprio do viewer e o link de download da ficha abrem diálogoSave comSave desabilitado emDownloads/nomeASCIIválido e outros destinos, sem mensagem de erro; nenhuma cópia local foi obtida. A prova está em `pb-em-official-acquisition.json`. Em requisições HTTP padrão sem sessão, o portal `paraiba.pb.gov.br` devolve HTTP200 `text/html` com desafio de CAPTCHA/JavaScript em lugar do PDF. Foram tentadas as publicações original, `www`, `copy_of` e `@@download`; o portal MEC alternativo também devolveu desafio. Nenhum controle foi contornado. Snippets de busca não foram usados para preencher aprendizagens. O exemplar do Instituto Unibanco foi usado apenas para descoberta, pois a página informa restrições de download/reprodução. Intervenção mínima: fonte primária alternativa acessível ou arquivo oficial obtido legitimamente com proveniência.
- **PB EM — adquirido em 2026-10-29:** o usuário obteve o PDF pessoalmente no navegador, no portal oficial, após resolver o CAPTCHA, e o entregou ao projeto. Nenhuma automação resolveu ou contornou o desafio. Validação local: PDF1.5, 7.918.257B, 867 páginas (igual à renderização anterior), sem criptografia, CreationDate/ModDate 25/04/2023, coerentes com a ficha `/view` (7.6MB, 25/04/2023). SHA-256 `d31b7a843ecef96921434877db1bf3955b6942a3125747b11059dc3765fe5db8`, snapshot privado `data/raw/PB/pb-pcem.pdf`. A igualdade com o binário servido não tem prova por hash independente porque o GET anônimo segue retornando HTML. Edição/vigência continuam não confirmadas. A extração v1.5.0 com parser congelado gerou 1.884 candidatos (1.018 com código, 165 códigos distintos, 866 seções). Há defeitos: o parser genérico corta na vírgula os códigos locais legítimos do modelo PB (p.53: `EM13LP51/1,2` = habilidade 51 relacionada às competências 1 e 2), produzindo 25 tokens `EM13LP51/1` com texto `,2)`; há também 298 textos sem fecho e repetições de tabelas de progressão. O próximo passo é um adaptador PB EM independente, com peer e binding, antes de qualquer delta. Nada disso torna PB pronta.
- **PB EM — adaptador documental (2026-10-29):** sidecar `data/manifests/uncoded/pb-pcem-items.json` com 6.750 registros em quatro partes: FGB Linguagens, FGB Matemática/Ciências da Natureza/Ciências Humanas, itinerário de Linguagens e itinerários Exatas/CHS/Vasto Mundo. Gerado por `pb-pcem-part-*.py` sobre `pb_pcem_common.py`, com células delimitadas pelas réguas vetoriais do PDF. Os códigos locais do modelo PB (p.53, habilidade/competências) são tokens literais. Os objetivos são separados em ponto ou ponto e vírgula de fim de linha seguidos de maiúscula, e os objetos ficam como contêineres por célula. Posições vêm só de cabeçalhos explícitos de série, componente e área; nenhum ano é derivado de código. O caminho real `source_uncoded_items` dá 6.715/6.715 sem erro, e o replay de binding (`scripts/verify-source-bindings.py`) também dá 6.715/6.715, com o parser congelado inalterado. A revisão independente source-first passou na 4ª rodada: 2.916 códigos impressos (único sem código afirmado: `EM13LP 8/1,6`), 0 palavra perdida em 153.817 e 0 duplicação. As rodadas 1–3 corrigiram Quadro 5, códigos IFA engolidos, quebras de página, séries e linhas. Resíduos documentados estão em `adapter_peer_review` no manifesto. Projeto de Vida, Eletivas e EPT seguem como seções genéricas. Depois da revisão foram acrescentados a p.53 (prosa literal e o exemplo do Quadro 4) e o Quadro 18 (p.91–93, 18 habilidades de LP com texto integral), que substituem registros genéricos truncados. Refresh seletivo e recibo delta `source-delta-pb-pcem-20261029b` → `ca-ce95aa72db0a5084067e` sobre o BASE `ca-7d302a…`: integridade verificada, 6.750/6.750 do sidecar presentes e 0 item genérico codificado restante (`docs/evidence/source-audit-pb-pcem/post-delta-verification.json`). O recibo não foi promovido. PB continua não pronta.
- **BA EM — divergência de edição:** a Resolução CEE249/2026, página1 do PDF adquirido, confirma revisão DCRB-EM2026. O art16, na PDF p7, determina implementação a partir do ano letivo2027; o art22 dá vigência ao ato na publicação. Esses marcos não foram equiparados. O catálogo SEC `https://www.ba.gov.br/educacao/coordenacao-do-ensino-medio` entrega PDF cujo CIP/capa diz2022. O host legado `dcrb.educacao.ba.gov.br` deu timeout TLS; o arquivo2022 foi adquirido legitimamente no novo domínio, preservando essa diferença. A revisão2026 permanece como fonte aprovada pendente com início de aplicação2027; isso não comprova que a edição2022 seja inaplicável em todo o ano2026. Não se excluiu a edição2022 sem esclarecer o escalonamento.
- **CE EI/EF — alternativa oficial resolvida:** o host antigo `www.seduc.ce.gov.br` falhou validação TLS. A publicação oficial movida para `www.ce.gov.br/seduc/wp-content/uploads/sites/63/2020/02/DCRC_2019_OFICIAL.pdf` foi adquirida sem desabilitar verificação de certificado.
- **PI — substituição de caminho resolvida:** `/arquivos/diretrizes/` retornou404; `/download/diretrizes/` entregou PDFs oficiais EI/EF e EM. O caderno2 adquirido traz “VERSÃO PRELIMINAR” na capa; sua homologação não foi presumida.
- **SE — WPDM público:** PDFs adquiridos pelo link público `data-downloadurl` do próprio portal. No manifesto preserva-se URL estável `?wpdmdl=ID`, sem depender do parâmetro efêmero `refresh`; downloads não exigiram autenticação. Datas de atualização da página2026 não foram tomadas como edição dos PDFs.
- **RN — extensão do referencial:** o catálogo oficial contém RCEMP2021, trilhas e diretrizes IFA; página de estruturas acrescenta diurno/noturno/integral2026. Os três documentos2026 foram adquiridos. O DCEC/RN Computação inicialmente retornou403; nova requisição pública às04:44UTC retornou200/PDF e permitiu adquirir819 páginas físicas. A cadeia oficial municipal.gov→SIGEduc→PDF foi confirmada; isto resolve acesso, não reconciliação. O ato estadual de homologação foi adquirido; sua região curricular tem gate próprioV2, preservando matérias alheias fora do recorte. A identidade do Parecer160/2025 e do texto DCEC aprovado não foi inferida por semelhança de título ou pelo PDF2026 disponível.
- **AL — escopo do Diário Oficial:** o PDF de152p contém matérias não curriculares. Somente parecer27/2026 p34-35 e Resolução10/2026 p36-37 pertencem ao recorte. P37 contém duas colunas: a esquerda segue curricular até o rodapé e a direita encerra a resolução antes da SEFAZ. Cortar a sequência global pelo marcador apagaria os artigos11/12 à esquerda. `page_regions` registra a união ordenada de duas regiões curriculares; a implementação v1.4 e a conferência do recorte passaram nas quatro páginas, preservando artigos11–17 e excluindo SEFAZ/CNPJ/matérias tributárias. `include_in_corpus:true` está habilitado apenas para essas regiões. A estrutura normativa e a fidelidade dos glifos ainda exigem reconciliação documental; o conjunto permanece obrigatório.
- **Direitos MA EI/EF:** o próprio PDF declara reprodução permitida com citação da fonte e distribuição gratuita. Demais permissões de redistribuição de PDFs permanecem não estabelecidas, salvo indicação específica em fonte; direitos sobre texto oficial, diagramação e fotos não foram misturados à licença MIT do código.

## Inventário e verificação

`stages`, `components`, `normative_parts`, `index_entries` e `inventory_evidence` registram expectativas observadas em fontes/capas/sumários. O gateV2 atual verificou oito artefatos próprios; quatro fecham também as dependências declaradas. PEHistória93,PI18814,BA12523eBA266141já passaram após refresh seletivo1.5. Os demais estados de inventário e reconciliação permanecem pendentes: o denominador não foi substituído pelos registros que o parser conseguiu extrair. A leitura inicial não comprova extração integral, associação código/texto em todas as tabelas, OCR ou revisão humana. As partes internas das modalidades que integram o documento principal permanecem dentro do PDF processado; materiais didáticos, cadernos trimestrais e documentos específicos de modalidade fora do referencial principal devem ser classificados separadamente, com justificativa, antes de excluir.

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

A aquisição dos arquivos não conclui a reconciliação. O quadro de amostragem em `docs/evidence/source-audit-northeast/audit-report.json` foi construído diretamente de ocorrências nativas dos PDFs, por UF, etapa e componente, antes de consultar os IDs extraídos. Abrange 159 pontos de amostragem em 157 combinações distintas de UF, etapa e componente, nas nove UFs. Ocorrência de código inclui exemplos e referências e **não é o denominador de aprendizagens**.

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

O corpo curricular das páginas PDF3–8 foi inventariado por títulos, subdivisões e bullets, independentemente dos itens codificados do parser. Esse corpo contém91 registros tipados: oito habilidades, 13 temáticas, 11 desdobramentos, dez eixos, dez temas transversais, seis produções sugeridas, apresentação, orientações e títulos. Há 90 vínculos hierárquicos e 92 fragmentos de evidência. As habilidades se distribuem em três, duas e três por trimestre; uma continua da PDF p.5 à p.6. Todos os códigos permanecem nulos.

`data/manifests/uncoded/pe-historia-items.json` preserva os textos, série, período e hierarquia. Os IDs foram derivados do inventário documental e do contrato canônico do finalizador. `build-pe-structure.py` permite reconstruir o inventário, e `verify-pe-structure.py` confronta importação, IDs e parentesco com a expectativa independente.

A execução com PyMuPDF1.26.7 e pipelinev1.4 verificou os 91 registros, 92 fragmentos e 90 pais, sem órfãos, warnings ou OCR pendente. As evidências estão em `pe-complete-structure-inventory.json` e `pe-complete-structure-import-check.json`. Esse teste antigo validava o corpo curricular. A revisão posterior preserva também a capa e os créditos PDF1–2: a fonte integral tem93registros(91corpo+2contextos),94fragmentos e90pais. O binding corrigido passou no refresh seletivo1.5 e reciboV2 atual; não há completude PE/EM ou revisão pedagógica humana.

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

O cache de sete páginas foi produzido pelo pipelinev1.4/PyMuPDF1.26.7, sem warnings ou OCR pendente. Importação, finalização e evidências passaram para os 45 nós, sem órfãos ou ciclos. O gateV2 em cache atual1.5 verificou o ato próprio45/45,49fragmentos. A dependência DCRB-EM2026 continua faltante e impede fechamento documental conjunto. Comandos e evidências estão em `ba-resolucao249.md`, `ba-resolucao249-inventory.json` e `ba-resolucao249-verification.json`.

O ato é de 07/07/2026, foi homologado em 26/08/2026 e publicado em 27/08/2026. O art22 estabelece vigência na publicação; o art16 determina implementação da organização curricular a partir do ano letivo2027. A edição DCRB2022 não foi descartada com base apenas na data do ato.


## RN: acesso resolvido, procedência e direitos documentados

O DCEC/RN foi adquirido integralmente após nova requisição pública, sem resolver desafios ou usar autenticação. A [Secretaria municipal oficial](https://antoniomartins.rn.gov.br/secretarias/secretaria-de-educacao/) liga seu Portal SIGEduc; o catálogo público noticia o documento e liga o PDF adquirido. O livro tem edição2026, 819 folhas físicas e 714 pranchas duplas; o sumário usa paginação editorial até1528. Não se tratam de 819 aprendizagens nem de uma reconciliação concluída.

A apresentação declara que o documento complementa os referenciais EI/EF2018 e EM2021 e remete à Portaria-SEI11123/2025. O PDF declara **CC BY-NC-ND**, sem especificar versão, na página física6. As condições de atribuição, não comercialização e ausência de adaptações estão registradas no manifesto; imagens não foram incluídas nos dados estruturados. O original não é relicenciado pela licença MIT do software ou pela licença dos metadados do projeto. Alteração editorial de texto e mera mudança técnica de formato são fatos distintos.

O [DOE13/12/2025](https://webdisk.diariooficial.rn.gov.br/Jornal/12025-12-13.pdf) contém a Portaria-SEI11123/2025 na páginaPDF21. O diário completo fica privado. Somente a região do ato `[28,560,395,800]` entra no corpus: a portaria anterior trata de questão disciplinar e a seguinte de outro órgão. Inspeção visual, inventário de 24 linhas, extração e importação v1.4 verificaram as 12 partes normativas do ato, sem referências a essas matérias vizinhas, órfãos, warnings ou OCR pendente. O gateV2 próprio em cache atual1.5 passou12/12; a dependência Parecer160/DCEC aprovado tem identidade integral não confrontada. O currículo de819páginas permanece em processamento/reconciliação.

Evidências: `rn-dcec-acquisition-and-provenance.json`, `rn-portaria11123-inventory.json` e `rn-portaria11123-verification.json`. As limitações de acesso anteriores são preservadas no histórico de tentativas; não se mantêm como bloqueio atual após a aquisição bem-sucedida. PBEM continua respondendoHTML com desafio na verificação mais recente.


Atualização de auditoria v1.4 e propostas de correção

A reaplicação atual dos159 pontos inspecionou126 pontos com registros e encontrou33 ocorrências ainda sem item codificado. As comparações de célula deram108 passes literais,15 divergências e4 casos multipágina. Os quatro casos multipágina foram depois conferidos em todos os8 fragmentos: caixas físicas, redação concatenada e sequência de páginas passaram4/4 (`multipage-anchor-verification.json`). Esses resultados não concluem a reconciliação de uma UF.

As33 ocorrências sem item não foram reclassificadas em bloco como referências. Nove pontos BA EI/EF têm habilidades próprias ausentes: o desenho do documento deixa aberta a borda direita da tabela e o detector omitia toda a coluna. Uma varredura das482 páginas encontrou243 páginas com fechamento dedutível dos finais repetidos das linhas horizontais, recuperando2161 células codificadas antes ausentes do detector; os9 pontos independentes passaram no teste de recuperação. Isso é proposta de correção de extração, ainda dependente de integração e reprocessamento, e não denominador final de aprendizagens.

As propostas isoladas em `proposals/geometry_proposal.py` também tratam a recuperação indevida de texto posterior a listas de códigos no CE,14 células PE com dois prefixos literais para uma redação compartilhada e as grades artificiais formadas por decoração oculta no SE. Todos os códigos conjuntos PE permanecem literais do documento; não estabelecem equivalência nacional. A auditoria MA de glifos foi entregue à frente `source-audit-ma-fidelity`. O achado NUL do RN EF está somente no contexto secundário de um diagrama da página743, não no texto da habilidade EF01MA09: fonte LOVEAMY e ToUnicode inválido foram registrados em `rn-nul-secondary-context-evidence.json`; a correção autorizada é serialização reversível de metadado, sem descarte ou troca global de glifos.

Os33 pontos sem item codificado têm disposição individual em `unrepresented-anchor-dispositions-v1.4.json`:9 lacunas BA por geometria,1 erro do rótulo de amostragem AL (o documento e o registro usam literalmente AL.EF05LI16),7 menções CE em colunas de relações,6 listas em organizadores MA sem redação própria naquela célula,9 pontos PB aguardando adaptador integral e1 citação explicativa PI. Classificar uma menção como referência não remove a estrutura ou parte normativa do escopo.


Foram integradas14 partes oficiais PE atuais:12 organizadores FGB por componente e2 cadernos IFA (matrizes anexosI/II),563 páginas físicas. Os hashes, páginas, bytes, links exatos no painel oficial e inventário de partes foram revalidados. As fontes permanecem sem edição/data/aplicação inferidas; o rótulo do portal2026 está em campo separado. A extração e reconciliação desses novos documentos estão pendentes. O Caderno de Atividades Complementares42p também foi adquirido, mas sua tipologia/obrigatoriedade segue aberta no suplemento, sem exclusão silenciosa. O ato integral IN SEE/PE03/2026 e matrizes ainda não foi adquirido; há citações nos dois cadernos IFA.

O adaptador PB2008 foi ligado ao manifesto após conferência do SHA final e da revisão independente:1157/1157 células físicas,103/103 objetivos EI,138/138 folhas indígenas,34/34 direitos/princípios e823/823 âncoras, sem erros. A autoridade distingue234 habilidades matemáticas com códigos literais de referências de códigos nas demais colunas. A ligação não substitui reprocessamento do cache, hierarquia documental integral ou confirmação do Ensino Médio indisponível; não há declaração de UF pronta.


Atualização adicional de fontes: PI Computação EM137p tem edição2025 declarada na ficha catalográfica (136p impressas,137p físicas). O sumário identifica o organizador transversal por quatro áreas; a ResoluçãoCEE/PI188/2025(2p) e o Parecer190/2025(6p) foram adquiridos. Res188tem14nós públicos com OCRreal/peer visual integral e binding ativo; refresh seletivo1.5/V2 e Parecer190integral seguem pendentes. CE Matrizes2026 V2,100p, está diretamente ligada na notícia oficial preservada e declara transição escalonada por série; não substitui automaticamente o referencial anterior. Resolução CEE521/2025,26p escaneadas, foi adquirida do portal legislativo oficial e requer OCR e inventário de artigos/anexos. Nenhuma data legal foi inferida dos metadados de criação do PDF. O ato PE IN03/2026 está agora no denominador como research_pending obrigatório; a URL do artefato original é desconhecida/null, com landing separada e tentativas403 registradas.

A prova MA cobre736p e1932 fragmentos codificados no extrator real:zero falhas literais e9 regressões corrigidas; isso habilitou `native_text_order=glyph_cluster_stream` nas duas fontes. No SE, o mesmo modo está restrito às21 páginas de grade revisadas e tem peer check das duas células235. Os caches produtivos integrais ainda devem ser reprocessados sob o fingerprint congelado; os testes isolados não foram publicados como cache nacional.

## Quadro factual de reconciliação atualizado

O [quadro por fonte e parte](evidence/source-audit-northeast/factual-coverage-current.md) distingue provas próprias V2, fechamento das dependências, sidecars auditados, fidelidade e processamento interno pendente. Os oito recibos V2 contêm423registros/465fragmentos derivados de estrutura documental independente e conferidos contra o cache real1.5. PEHistória93(91corpo+2contextos),MA18176,BA12523eBA266141fecham suas dependências declaradas; BA249,RN11123,MA211ePI18814mantêm documentos relacionados pendentes. Nenhuma revisão automatizada é apresentada como revisão pedagógica humana. PB392 permanece entrega de processamento solicitada pelo usuário; edição/vigência desconhecidas e635p preservado.

RNTrilhas recebeu o sidecar completo3851nós,185objetivos locais,198UC,395módulos,741cartões,2930links codificados; o peer conferiu21423fragmentos e774445glifos. O finalizador real retorna6807registros, incluindo26contextos legítimos. A autoridade disjunta suprime somente contêineres redundantes16–19e31–485, com prova de cobertura dos12375glifos16–19. O binding já entrou no FULL1.5; V2integral seguependente.

PE12FGB usa o handler confiável `pe-fgb-document-roles-v1`, congelado no runtime1.5: habilidades nacionais da área e específicas preservadas, somente menções em colunas contextuais de Computação/objetos/eixos reclassificadas como referências com redação integral em contexto. O censo de481p verificou526referências literais,457menções específicas,445nacionais e60desconhecidas preservadas. Esses números são ocorrências diagnósticas, não denominador de aprendizagens.

Dois atos BA adicionais foram adquiridos oficialmente e incluídos no snapshot global303: Res266/2025Computação(21p,comParecer365/2025integral) eRes125/2024HistóriaBahia(2p). Os dois atos têm partição integral ativa e V2atual próprio: BA266141nós/155fragmentos,BA12523nós/23fragmentos, com pares independentes. Isso não reconcilia os referenciais BA ou o DCRB2026 faltante. A publicação daRes266em26/03/2026 e o prazo deumano doArt20 são fatos distintos; Res125exigeHistóriaBahiaEF/EM,sem transformá-la automaticamente em componenteEI.


PE EI possui candidato de reparo do organizador completo:115objetivos codificados e20nós de grupo/campo/introdução/legenda,31tabelas,252fragmentos físicos. O importador/finalizador real, schema e135IDs passaram em Sourceclone; o candidato ainda não foi ligado e aguarda peer. Dois identificadores fora do padrão foram conferidos em imagens originais e preservados: `EI02S 06PE` e `EI003EF11PE`, sem inventarT ou retirarzero. A cadeia GoogleSites→Drive é uma distribuição candidata; elo ao emissor permanece `pending_primary_distribution_chain`, visível no portal. Nenhuma elegibilidade foi alterada nesta investigação.
