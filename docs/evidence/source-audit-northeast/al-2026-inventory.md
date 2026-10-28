# Alagoas — complementos de Ensino Médio encontrados no catálogo atual

Revisão automatizada por `codex:al_current_materials`. Requisitos atendidos parcialmente: ESC-02, ING-01, ING-03 e DAT-05. Não houve revisão pedagógica humana, reconciliação integral nem declaração de UF pronta.

## Aquisição e cadeia oficial

O catálogo público da Secretaria de Estado da Educação está em <https://escolaweb.educacao.al.gov.br/>. A página publicada com slug `ensino-medio-3` é obtida pelo endpoint público <https://escolaweb.educacao.al.gov.br/api/17/pages/ensino-medio-3>. O corpo da página liga os arquivos Drive e as pastas públicas que sustentam este inventário. Não foram usados endpoints autenticados.

O snapshot HTML de catálogo foi preservado em `data/raw/AL/ensino-medio-3-catalog.html`, privado/ignorado no Git. Seu hash, os nomes e URLs obtidos das 13 listagens públicas estão em `al-public-folder-inventory.json`. Os downloads usaram HTTPS com verificação de certificado, timeout de45 segundos, no máximo duas tentativas, concorrência4, limite80MiB por resposta e validação de assinatura PDF; todos os15 arquivos abaixo foram abertos com PyMuPDF e tiveram SHA-256 revalidado. Não houve bypass de autenticação, CAPTCHA ou desafio de acesso.

As entradas Source para integração sequencial estão em `al-complements.json`, deliberadamente fora de `data/manifests/` para evitar dupla ingestão. São15 documentos,1936 páginas PDF e186.185.453 bytes; **esses números não representam aprendizagens nem completude**. Todos usam `inventory_complete:false`, `inventory_status:in_progress`, `reconciliation_status:pending` e `mandatory:true`.

| ID da fonte | Páginas PDF | Edição da capa | SHA-256 abreviado |
|---|---:|---|---|
| `al-matrizes-em-2026` | 44 | 2026 | fba1e33e135dcb52… |
| `al-organizador-fgb-2025` | 125 | 2025 | 1f9b076cee0ad6db… |
| `al-ifa-pit-1-2026` | 82 | 2026 | 96ff789382e1a45f… |
| `al-ifa-tac-1-2026` | 124 | 2026 | aeb77519094233a1… |
| `al-ifa-praticas-lgg-chs-2-2026` | 75 | 2026 | db735911a11f7ce6… |
| `al-ifa-temas-lgg-chs-2-2026` | 129 | 2026 | 2620cfe459ac4f16… |
| `al-ifa-praticas-mat-cnt-2-2026` | 117 | 2026 | 2ef7e9596968f44a… |
| `al-ifa-temas-mat-cnt-2-2026` | 122 | 2026 | 96bcf67a8edca7c3… |
| `al-ifa-praticas-lgg-chs-3-2026` | 56 | 2026 | 00b393d6c12dd774… |
| `al-ifa-temas-lgg-chs-3-2026` | 133 | 2026 | 6c82596e88f2d627… |
| `al-ifa-praticas-mat-cnt-3-2026` | 56 | 2026 | b69a103a264fc00a… |
| `al-ifa-temas-mat-cnt-3-2026` | 162 | 2026 | 977387a01d70a8ad… |
| `al-projeto-vida-guia-1` | 243 | não confirmada | f0914a20b70f6368… |
| `al-projeto-vida-guia-2` | 240 | não confirmada | 92bd054cdcc91cc5… |
| `al-projeto-vida-guia-3` | 228 | não confirmada | 3730f12237b589ee… |

## Organização e decisões

- As dez fontes IFA2026 incluem PIT e TAC da1ª série, Práticas e Temas LGG/CHS e MAT/CNT da2ª e da3ª séries. Capas, séries e índices foram lidos diretamente dos PDFs. Evidências em `al-complement-cover-index-evidence.json`.
- O Organizador FGB tem125 páginas e capa **2025**. Sua presença no catálogo2026 não foi tratada como nova edição2026. O documento detalha habilidades por série, componente e bimestre; as relações e posicionamentos devem ser extraídos dos cabeçalhos efetivos, sem inferir bimestre pela ordem.
- Os dois iframes de Temas da3ª série na página apontam para arquivos antigos indisponíveis. As pastas públicas oficiais LGG/CHS e MAT/CNT apontam para arquivos atualizados, adquiridos legitimamente, com capas IFA2026. As tentativas originais e os novos artefatos estão registrados em `al-acquisition-attempts.json` e `al-public-folder-inventory.json`.
- Os três Guias do Educador de Projeto de Vida não foram excluídos só por se intitularem materiais didáticos: p4 os descreve assim, mas p8 de cada ano traz quadro explícito de competências BNCC, **Habilidades de Projeto de Vida** e objetos. O1º ano, por exemplo, traz “Identificar e relacionar conteúdos e aprendizados associados ao projeto de vida e elaborar uma síntese que o auxilie na sua construção.” Três redações amostradas não foram localizadas literalmente no texto nativo do ReCAL539p; a comparação não comprova exclusividade de todos os itens. Como há conteúdo curricular próprio, os guias permanecem obrigatórios pendentes até reconciliação.
- Os guias PV têm25 quadros identificados por ano, total75, correspondentes às24 aulas e ao projeto interdisciplinar. **Quadros não são habilidades individuais**: cada quadro pode reunir várias redações. Páginas e texto-fonte estão em `al-projeto-vida-structural-inventory.json`. O guia1º ano ligado na pasta atual é byte-idêntico ao arquivo ligado diretamente na página, portanto não gera outra fonte.
- As três edições de PV não têm data editorial completa confirmada; menção na apresentação a trabalho realizado em2020 não foi convertida em data de publicação, homologação ou vigência. Esses campos permanecem nulos.
- Materiais do Estudante, Revistas da Família, a apresentação21p e o Plano de Ação33p foram obtidos e registrados separadamente em `al-auxiliary-materials.json`. Não são automaticamente adicionados ao referencial obrigatório. A classificação/exclusividade integral desses materiais continua aberta; isso não autoriza declarar inventário completo nem esconder objetivos exclusivos que venham a ser encontrados.
- A pasta oficial Legislação liga os parâmetros nacionais de IFA e seu anexo. A frente nacional confirmou `br-ifa-parametros-2025`, PDF24p com anexo17–24, já adquirido. As fontes IFA locais apontam essa referência nacional sem replicá-la como currículo alagoano. A estruturação do anexo é responsabilidade da frente nacional.
- Direitos de redistribuição dos PDFs não foram estabelecidos. Os arquivos ficam em `data/raw/AL/` privado/ignorado; o produto deve publicar metadados, evidências e dados estruturados com proveniência, sem relicenciar ou redistribuir automaticamente os PDFs.

## Pendências de integração e aceite

1. Integrar as15 entradas em `data/manifests/northeast.json`, mantendo IDs únicos e sem copiar este arquivo auxiliar para um segundo manifesto carregado automaticamente.
2. Processar os arquivos com o pipeline compartilhado, preservando habilidades sem código, competências, séries e bimestres declarados, referências muitos-para-muitos e estrutura das partes.
3. Reconciliar índices, tabelas, competências e objetivos com denominador independente; o contador de códigos nativos em evidência é apenas diagnóstico.
4. Classificar os materiais auxiliares e comparar as habilidades de PV com o ReCAL e outros complementos, evitando duplicação semântica e exclusões indevidas.
5. Confirmar a cadeia oficial do ReCAL Computação, em pesquisa paralela pelo responsável Nordeste. Esta aquisição de Ensino Médio não remove aquele bloqueio.
6. Não declarar AL pronta enquanto houver documento obrigatório sem processamento e reconciliação ou erro crítico conhecido.

## Evidências executadas

- 15 fontes adquiridas, abertas e com hash revalidado;1936 páginas e186.185.453 bytes.
- IDs das15 fontes são únicos.
- 13 listagens Drive públicas inspecionadas; não houve acesso autenticado.
- 75 quadros de Habilidades de Projeto de Vida localizados em inventário estrutural independente.
- 0 partes reconciliadas e0 UFs aceitas nesta subfrente.

## Adaptador executado de Projeto de Vida

Foi acrescentado `data/manifests/uncoded/al-pv-items.json`, lista filtrável por `source_id`, para as três fontes `al-projeto-vida-guia-{1,2,3}`. Configure o mesmo caminho em `uncoded_items_path` de cada fonte; a função compartilhada filtra o arquivo por fonte e valida hash, localização e texto.

O adaptador independente `al-pv-extract.py` recuperou as 75 células da coluna **Habilidades de Projeto de Vida** e segmentou seus parágrafos pelo espaçamento nativo explícito do PDF. São 182 ocorrências documentais: 59, 58 e 65 nos guias de 1º, 2º e 3º ano. Há repetições entre aulas: as quantidades de redações exatamente distintas por fonte são 34, 21 e 23, respectivamente. Esses números não representam objetivos pedagógicos únicos ou competências diferentes. Nenhuma pontuação ausente na fonte foi acrescentada.

Cada ocorrência mantém `code:null`, tipo `habilidade_projeto_vida`, ano explícito, bloco/tema/aula ou projeto interdisciplinar, página e bbox do parágrafo. Bimestre não foi inferido de bloco ou número de aula. IDs esperados são derivados do contrato canônico `source|page|locator|uncoded|occurrence:0`; não foram copiados dos resultados do pipeline. O identificador inicial do adaptador também foi preservado para rastreabilidade.

Foram executadas as funções reais `source_uncoded_items` e `finalize_items` da revisão compartilhada `page-cell-v1.4.0`: 182 entradas passaram a conferência literal de evidências, os IDs finais corresponderam aos IDs previstos, e as 75 páginas de quadros apresentaram ano consistente com seu documento. O teste utilizou os PDFs reais e seus textos/bboxes, sem depender de outputs anteriores como denominador. O relatório está em `al-pv-verification.json`.

A revisão visual automatizada conferiu as células PDF 8/128/233 do 1º ano, 8/120/231 do 2º e 8/118/220 do 3º. As três imagens `al-projeto-vida-guia-{1,2,3}-sample-cells.png` preservam os recortes conferidos. São nove células amostradas, não uma inspeção visual de todos os parágrafos. Há inventário independente de todas as tabelas e parágrafos em `al-pv-table-paragraph-inventory.json`.

Reconciliação integral e aceite de UF permanecem pendentes: as referências a competências BNCC, outros elementos estruturais e a integração do bundle nacional precisam ser verificadas no conjunto. Nenhum teste isolado do adaptador foi apresentado como publicação nacional ou jornada completa.

Comandos de retomada executados:

```sh
.venv/bin/python docs/evidence/source-audit-northeast/al-pv-extract.py
.venv/bin/python docs/evidence/source-audit-northeast/al-pv-verify.py
```
