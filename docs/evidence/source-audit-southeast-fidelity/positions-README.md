# Posições documentais ES — proposta independente

Implementado e executado: releitura dos cabeçalhos de **677 páginas**, em **11 fontes oficiais**, vinculados aos **2513 objetivos** do inventário físico de coluna Código da Habilidade + Habilidade. Os componentes vieram do próprio cabeçalho ou do último título literal de componente no banner/capa do capítulo, com página e bbox. Código BNCC não foi usado para escolher ano local ou componente.

| Fonte | Páginas com objetivos | Objetivos |
| --- | ---: | ---: |
| Área de Ciências da Natureza e Matemática – Volume 2 | 56 | 196 |
| Área de Ciências Humanas e Ensino Religioso – Volume 3 | 59 | 160 |
| Área de Linguagens, Arte e Educação Física – Volume 4 | 63 | 202 |
| Área de Linguagem, Língua Portuguesa – Volume 5 | 49 | 366 |
| Área de Ciências da Natureza e Matemática – Volume 6 | 55 | 191 |
| Área de Ciências Humanas e Ensino Religioso – Volume 7 | 85 | 199 |
| Área de Linguagens, Arte, Ed. Física e Língua Inglesa – Volume 8 | 102 | 314 |
| Área de Linguagens – Volume 9 | 103 | 428 |
| Ciências da Natureza — Ensino Médio — Currículo do Espírito Santo | 23 | 130 |
| Ciências Humanas — Ensino Médio — Currículo do Espírito Santo | 30 | 148 |
| Língua Portuguesa — Ensino Médio — Currículo do Espírito Santo | 52 | 179 |

## Resultado verificado

- Os **1036 fragments únicos** de metadata passaram literalmente no texto nativo do PDF e no glyph trace visível; zero falhas.
- O ensaio com o `ingest.finalize_items` real, em memória, preservou todos os IDs, códigos, textos, tipos, evidências e `source_context` das folhas. As **2513 posições** ficaram compatíveis com a proposta, sem gravar manifestos, caches ou publicação.
- No candidato anterior à proposta, **2330 objetivos** não preservavam o ano/série local explícito; **278** de EM Ciências da Natureza/Humanas também não preservavam o componente. Os 179 objetivos de EM Língua Portuguesa já coincidiam. Os 4 objetivos conflitantes já mantinham ano nulo.
- Um diagnóstico secundário comparou os componentes documentados com as convenções dos códigos e encontrou zero contradições; essa convenção não participou da atribuição.

## Conflito da fonte preservado

No volume 6, página PDF 132, o original imprime “Matemática – 1º Ano do Ensino Fundamental (Continuação)”. As páginas adjacentes e os identificadores EF06 apontam para 6º ano. O raster original confirma o 1º impresso. Não há correção silenciosa: os 4 objetivos ficam com `years:null` e `year_label:null`. O `position_evidence` contém o caption, os 4 code-cell fragments, os 2 captions vizinhos e `position_conflict` com ambas as leituras. O contexto adicional guarda o caption literal e os candidatos de convenção, sem escolhê-los.

## Aplicação proposta

`positions-metadata-proposal.json` é uma proposta congelada, ainda **não integrada**. Cada fonte tem guard `source_id` + `artifact_sha256`, seguido de contextos por página. Acrescentar esses contextos às metadata da mesma fonte mantém o escopo documental explícito. No ensaio, o campo de conflito dentro de `position_evidence` sobrevive ao finalizador; o contexto adicional da proposta deve ser mantido na origem para auditoria.

O escopo limita-se às 11 fontes com colunas próprias e aos 2513 objetivos do inventário independente. Não atribui série aos 4 documentos de matrizes com códigos prefixados, nem resolve competências sem código, a completude editorial total da UF ou revisão pedagógica. Todos os atores são `automated`; não houve revisão humana nem alteração do estado de publicação.

## Reprodução

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-fidelity/positions-audit.py
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-fidelity/positions-verify.py
```

A primeira etapa relê os PDFs e compara os finalized paths atuais de `probe-ef/em-summary.json`; a segunda valida todos os fragments e aplica a proposta em memória. O relatório de verificação fixa os hashes dos candidatos, a versão do PyMuPDF e o fingerprint/hash do finalizador usado, exigindo estabilidade durante o ensaio.

## Artefatos congelados

- `positions-metadata-proposal.json` — SHA-256 `b87217abe8cc1429a0d1f05c7f39325650d5e3da32f4661c67fe4c99eff34a29`.
- `positions-audit-report.json` — SHA-256 `24d62637751cc26107872edebb9cbb351cdb871ff01b7586e76dd65fdae2ae3f`.
- `positions-verification.json` — SHA-256 `ae8cf51f466a77e9e210e72432c9ab912f4c5f375252ff17679b01a5a8da9f33`.
