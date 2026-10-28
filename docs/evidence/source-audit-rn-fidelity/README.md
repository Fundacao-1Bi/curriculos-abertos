# RN — fidelidade literal e papel documental

Auditoria automatizada das fontes completas, sem alterar PDFs, manifestos, caches de produção ou arquivos centrais. A proposta permanece isolada neste diretório até integração pelo proprietário do pipeline.

| Fonte | Páginas físicas | SHA-256 | Menções de códigos no original |
|---|---:|---|---:|
| rn-trilhas-aprofundamento | 485 | fac7333112fcfaac3d99d74f72f206bea8e9a4b256e770a9ea0f2eace99b027a | 2.930 |
| rn-dcec-computacao | 819 | 886cdd02d96a63c50be00e93faf0fe5a9f7f305a959bd9920bcbdd429be134bd | 1.392 |

## Denominador independente

`rn-full-fidelity-audit.py` percorreu as 1.304 páginas, 765 tabelas físicas detectadas, 8.639 células não vazias, os 741 cartões vetoriais de referência e todos os 1.881 fragmentos codificados anteriores. O cache anterior foi arquivado privadamente, com hash em `baseline-cache-provenance.json`, para permitir reprodução após o rebuild. Foram localizados os 479 IDs da regressão, inclusive os casos negativos anteriormente aprovados. `rn-reconcile-audit-roles.py` localiza cada ocorrência por seus glifos reais no stream, incluindo códigos repetidos, e associa cabeçalhos por geometria horizontal. Não usa o primeiro resultado de `search_for`, nem presume que índices de células mescladas sejam colunas documentais.

O relatório geométrico é a reconciliação posterior e mais precisa dos papéis; os campos iniciais `source_column_role` do primeiro inventário são preservados para auditoria. A coluna `geometric_source_role` e `geometric-role-reconciliation.json` substituem essa classificação inicial. A conferência de papel não equivale à reconciliação de completude curricular.

## Trilhas

As quatro folhas iniciais `HABILIDADES — ...`, páginas físicas 16–19, contêm **48 definições** (12 por folha). O cache anterior tinha 27. Os **741 cartões** das unidades contêm **2.882 referências**, com os rótulos expressos Investigação Científica, Processos Criativos, Mediação e Intervenção Sociocultural e Empreendedorismo. Esses cartões não repetem a redação da habilidade.

Todos os **365 casos de falha literal** anteriores estão nos cartões. A recuperação genérica de tabelas sem grade tomava um código e buscava prosa até uma coordenada inferior, misturando Ementa, Objetos do Conhecimento e Sugestões Didático-Metodológicas de colunas vizinhas. Até 103 cartões que passavam no teste literal anterior continuavam sendo referências; passar na substring não prova associação código–redação.

A proposta exige ID e hash exatos, contorno vetorial retangular e resíduo textual igual a um dos quatro rótulos. Não descarta páginas. Retém cada código como `referencia_no_documento`, com o texto integral do cartão em `source_context`, e conserva as seções normativas existentes. Nas quatro folhas de definições, exige cabeçalho `HABILIDADES —`, caixas grandes e prosa, extrai cada definição sem concatenar cartões, sem inventar ano, alias ou código. Os 48 códigos são os literais da fonte, inclusive `EMIFCHSA...`.

## Computação

O PDF contém spreads: **página física não é página impressa**. O inventário registra os números de rodapé por metade do spread, quando legíveis. As 1.392 menções se distribuem em:

- 773 na coluna HABILIDADE;
- 593 na EXPLICAÇÃO DA HABILIDADE;
- 11 em OBJETO DE CONHECIMENTO, 7 em EXEMPLOS e 6 em SUGESTÕES DIDÁTICAS;
- 2 exemplos narrativos de leitura de códigos, fora das tabelas, nas páginas físicas 61 e 574.

Os 114 casos anteriores se distribuem em **49 na coluna HABILIDADE** e **65 nas colunas de contexto**. Estes últimos não são automaticamente novas habilidades. A proposta mantém os primários e os casos desconhecidos; substitui somente candidatos cuja ocorrência literal está geometricamente dentro de uma coluna secundária identificada. O registro de referência contém o código original e conserva toda a prosa da célula e seu cabeçalho no contexto documental. Os dois exemplos narrativos continuam no texto da seção; nenhum posicionamento é inferido.

O confronto independente da primeira candidata encontrou ainda uma definição ausente que a checagem de substring não captou: `EF15CI06`, página 177, está impresso após `resultados.` na mesma linha, seguido de travessão. A página original foi visualizada. A varredura integral das 773 menções primárias encontrou exatamente uma fronteira desse tipo (`inline-definition-full-scan.json`). A proposta só a separa dentro da coluna HABILIDADE e conserva cada palavra original. O proprietário do pipeline também corrigiu o reconhecimento central com controles positivos/negativos. A localização técnica dessa definição passa de um recorte de recuperação por palavras para a célula física documentada; o código e a página permanecem literais. `inline-idempotence.json` verifica que reaplicar o helper não duplica o registro.

A proposta habilita `native_text_order: "glyph_cluster_stream"` apenas na fonte Computação. A leitura nativa já implementada no core conserva o stream e associa a letra expandida de ligadura ao glifo físico de base. Não usa dicionário, não elimina letras de largura zero e não altera o PDF.

## Testemunho independente de glifos

`rn-glyph-witness-verification.py` percorreu todas as páginas e células com `get_texttrace`, por fonte tipográfica e origem física. Todas as **6.528 expansões** da Computação tiveram testemunho independente. As 20 células das Trilhas e 8.598 das 8.619 células da Computação coincidiram integralmente.

Há **21 células** da Computação com diferenças entre ActualText e Unicode nominal ou caixas de glifos: marcadores numéricos com pontos, seletor de emoji, zero-width U+200B e geometria de uma seção introdutória. Elas permanecem explicitamente registradas em `physical-glyph-cell-verification.json`; não foram apagadas por normalização global. Somente uma dessas células contém uma citação de código, p409/EXEMPLOS, cuja diferença é U+200B dentro de “material/​tecnologia”; o código `EF07CI06` coincide. O texto proposto conserva o Unicode original. O testemunho de ligaduras não autoriza declarar todas as células, toda a tipologia ou a fonte reconciliada.

## Execução e limites

A primeira tentativa executou o parser real com o helper injetado somente em memória e escritor privado. Trilhas concluiu; a extração das 819 páginas da Computação foi corretamente barrada ao final pelo runtime guard quando outro agente alterou arquivos centrais. Os caches anteriores ficaram preservados. Essa tentativa não é apresentada como teste integrado aprovado. A execução seguinte usa snapshot privado imutável de todos os módulos Python: apenas `ingest.ROOT` aponta para os PDFs reais, enquanto `runtime.ROOT` e o guard permanecem no snapshot. Hashes antes/depois, versões e fingerprint estão em `immutable-parser-snapshot.json`. Uma primeira candidata completa passou na checagem literal, mas faltou a definição inline acima; ela foi corrigida e o conjunto integral foi reexecutado. O resultado final está no resumo do probe e no confronto independente, sem atribuir esse resultado ao futuro core do rebuild nacional.

A execução final do snapshot `a3b51fb66cc94d19ff570968883c06042c4ae7328b23236a8e8032e95034d39e` passou em **4.320/4.320 fragmentos literais**. O confronto independente de **4.322 menções** aprovou os papéis de 4.320 registros, sem faltas nem extras; os dois exemplos narrativos continuaram nas seções. Todos os **1.881 casos anteriores** foram confrontados — 479 falhas e 1.402 controles negativos. Na Computação, as 773 definições foram preservadas, com 49 redações ajustadas por leitura de glifos ou delimitação explícita, sem paráfrase; 772 locadores físicos ficaram iguais e a definição inline teve uma relocação documentada para sua célula. Há 48 definições e 2.882 referências nas Trilhas, e 773 definições e 617 referências na Computação. Os hashes dos caches de produção e dos arquivos do snapshot antes/depois coincidiram.

A proposta de produção está em `rn-document-roles-integration.patch`; ela omite a coleção global de debug usada apenas pelo probe (`probe-snapshot-integration.patch`). `git apply --check` passou. O helper é idempotente para a recuperação inline. `current-core-p177-peer.json` verificou o ajuste central posterior do proprietário: o core atual já separa os dois códigos e o helper não duplica a definição. Esse teste pontual não substitui o novo FULL após integração/freeze.

O probe nativo pula OCR explicitamente. As páginas digitalizadas e a tipologia/hierarquia sem códigos das unidades exigem reconciliação própria; preservar seções e referências não equivale a extrair todos os objetivos locais. Nenhuma fonte foi marcada `ready`, nenhuma revisão humana foi alegada e nenhum lançamento foi aprovado por esta frente. Não houve bloqueio externo de acesso aos PDFs. A licença da fonte Computação e sua procedência permanecem no inventário do Nordeste; renders completos ficam privados em `var/private-evidence/source-audit-rn-fidelity/`.

## Reprodução

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fidelity/rn-full-fidelity-audit.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fidelity/rn-reconcile-audit-roles.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fidelity/rn-glyph-witness-verification.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fidelity/rn-isolated-pipeline-probe.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fidelity/rn-confront-candidate.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rn-fidelity/rn-negative-controls.py
```

Python 3.11.15 / PyMuPDF 1.26.7. A proposta não deve ser aplicada simultaneamente por múltiplos agentes; o proprietário do pipeline controla integração, fingerprint e reprocessamento nacional.


## Peer independente para a hierarquia sem códigos

A frente `rs_adapter` recebeu os censos, caixas, papéis e a separação entre definições e cartões. `trilhas-toc-peer-denominator.json` registra uma leitura independente do sumário original (p11–12), conferida com o quadro sinóptico p21: **33 trilhas em sete grupos**, com 4/4/4/6/5/5/5 entradas. As três páginas foram visualizadas; não houve nova extração integral das 485 páginas nem leitura do output do adaptador sem códigos.

As declarações da fonte p24 (seis UC por trilha) e p29 (dois módulos por UC) dão expectativa nominal de 198 UC/396 módulos. Isso serve para procurar exceções e reconciliar o corpo; não certifica essas contagens. O censo prévio de rodapés prova igualdade impresso/físico para as 474 páginas 11–484 desta fonte. O sumário contém identificadores repetidos, títulos truncados e grafias distintas do quadro: o peer preserva cada campo literal e usa chave técnica própria, sem criar código oficial corrigido.


## Peer integral do adaptador sem códigos — PIN 551f90cc…4602

`verify-rn-uncoded-peer.py` confrontou o pacote congelado do outro responsável (`data/manifests/uncoded/rn-trilhas-items.json`, SHA-256 `551f90cca125541f09975b3d62f8457695a4cdc7a742f096360f609854749602`) com os denominadores já produzidos **antes do output autoral**. O peer não editou o extrator, Source, cache ou sidecar.

- **3.851 nós, 21.423 evidências:** todas as redações são a junção integral das evidências; zero mudanças de texto, caixa ou pais sem prova. A conferência independente usa o trace físico. Em 855 linhas de cartões, a ordem física esquerda→direita difere da ordem dos objetos PDF. Três controles de formatação preservados da fonte (p187/346) têm testemunho explícito; nenhum texto é corrigido silenciosamente.
- **1.875 cabeçalhos, 2.050 fragmentos e 175 continuações:** todos os cabeçalhos impressos têm exatamente um campo do tipo correto; nenhum campo ficou sem cabeçalho independente, nenhuma continuação atravessa a UC errada.
- **198 UCs/395 pares UC–número de módulo:** 617 rótulos impressos de módulo, oito barras de continuação sem rótulo, 329 barras de UC e um traço redundante na p369 foram conferidos. Os 1.479 escopos dos novos cabeçalhos coincidem com as barras originais e a leitura física, incluindo legendas acima de barras curtas. Não foi inventado Módulo2 na UC403 nem reparada a sequência contraditória 1→2→1 da UC436.
- **774.445 glifos de corpo elegíveis, todos cobertos** por redação efetivamente demonstrada, não apenas por retângulo sobreposto. Paratexto repetido e etiquetas de escopo foram classificados separadamente; os 33 cabeçalhos de grupo das capas permanecem em contexto e também foram conferidos.
- Os 33 textos gerais e as 33 regiões completas de específicos coincidem integralmente com a leitura independente. Uma segunda conferência independente dos operadores vetoriais nos 33 recortes encontrou 152 marcadores pretos originais, cada um ligado a exatamente um específico. Não houve numeração oficial inventada; ponto e vírgula não é denominador de objetivo. Os 20 posicionamentos de quadros/eixos16–19 coincidem com seus cabeçalhos originais de área.
- Os 741 cartões e os **2.930 seletores de pais dos registros codificados existentes** conferem, sem trocar código, locator ou identidade. Os dois cabeçalhos reiterados de Avaliação326/327 e Fontes346/347 são ocorrências reais; preservá-los separados não é duplicação inventada. Vínculos documentais complementares podem ser registrados sem apagar os nós.

Resultado detalhado: `rn-uncoded-peer-summary.json`, `rn-uncoded-peer-*-checks.json`, `rn-uncoded-peer-native-body-coverage.json`. O proprietário executou separadamente o importador, schema, idempotência, OCR da contracapa485 e autoridade disjunta dos genéricos. Este peer aprova o recorte de texto/geometria/hierarquia conferido; não a prontidão integral da UF, uma revisão humana ou a futura distribuição nacional.
