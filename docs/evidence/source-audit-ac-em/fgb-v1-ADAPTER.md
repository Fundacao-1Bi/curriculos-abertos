# Acre EM — aditivo dos quadros de áreas do conhecimento

Pacote local pronto para integração serial, após os gates descritos abaixo. A Source não foi vinculada por este agente. A publicação BASE em consolidação permanece separada deste candidato.

Fonte original: `data/raw/AC/ac-cru-em.pdf`, 459 páginas físicas, SHA256 `9ff75d1d5d9397aa145dccedd8023a01ed3b862692f58bb7d2cb2c84fc7602ad`.

## Pacotes e preservação

| Pacote | Registros documentais | SHA256 |
|---|---:|---|
| PV anterior, intacto | 158 | `535611af0023abffda03e3b4cc899e5a4b02b286a224303d99f8cfde26114909` |
| `data/manifests/uncoded/ac-em-fgb-v1-items.json` | 1.134 | `ca0432b91b599e06c767732913364d71cb1bd2307886e7926d6f63f8b40e1a22` |
| `data/manifests/uncoded/ac-em-fgb-v1-combined-items.json` | 1.292 | `e8d40d8a44d5971cc5e01301698e20c403f954de0dc7165f9bf0a2894eea44a2` |

Os 158 valores anteriores aparecem como prefixo idêntico no agregado. O arquivo anterior não foi reescrito. Esses totais incluem contexto e estrutura; não são contagem de aprendizagens nacionais únicas.

| Tipo do aditivo | Registros |
|---|---:|
| `habilidade` | 240 |
| `competencia_especifica` | 60 |
| `objeto_conhecimento` | 447 |
| `experiencia_sugerida` | 240 |
| `orientacao_didatica` | 1 |
| `secao_normativa` | 146 |

Objetos e propostas são containers completos da fonte, ligados à ocorrência de habilidade e ao componente explícito. Não foram divididos artificialmente em atividades atômicas nem promovidos a habilidades.

## Inventário primário e recortes

Uma passagem leve de texto e palavras nativas percorreu as 459 páginas, sem OCR, parser global ou consulta ao cache/outputs de aprendizagem. A geometria de bordas do censo anterior foi reutilizada de forma declarada; a classificação de papéis e as palavras foram relidas da fonte. Não se apresenta essa reutilização como detecção independente de tabelas.

O corpo físico dos quadros começa em `30. ÁREAS DO CONHECIMENTO`, na página 112, abaixo de uma continuação de Formação Técnica e Profissional. Termina antes de `ITINERÁRIOS FORMATIVOS`, na página 385, que ainda contém propostas de CHS acima desse título. O sumário das páginas 5–8 contradiz a organização do corpo e não foi usado para offsets.

Títulos de série físicos:

- LGG: páginas 121, 183 e 232, respectivamente 1ª, 2ª e 3ª séries.
- Matemática: páginas 256, 264 e 272, respectivamente 1ª, 2ª e 3ª séries.
- CNT: páginas 286 e 299, respectivamente 1ª e 2ª séries.
- CHS: páginas 330 e 365, respectivamente 1ª e 2ª séries.

Um título pode abrir no meio ou no pé da página. As ocorrências acima dele conservam o quadro anterior. Nenhuma 3ª série de CNT/CHS foi inferida por código `EM13` ou por expectativa externa.

O denominador foi fixado antes do aditivo: 240 definições codificadas e 52 continuações, 447 containers de objetos em 556 fragmentos, 240 containers de propostas em 331 fragmentos, 86 cabeçalhos estruturais, 45 rótulos matemáticos numéricos sem definição própria e 60 ocorrências de competências específicas completas. São 44 definições plenas nos quadros e 16 nas listas introdutórias (7 LGG, 3 CNT e 6 CHS). Os 45 rótulos isolados continuam como estrutura de referência, sem corpo copiado de outra posição.

A geometria reutilizada contém 245 segmentos de tabelas nesse recorte, 2.598 células físicas e 2.293 células não vazias. A classificação de todos os papéis terminou sem células pendentes. Os 579 cabeçalhos de coluna e 330 rótulos de componente são preservados nas provas/metadados de posição, sem inflar o número de habilidades.

A revisão nativa e visual acrescentou uma nota explícita fora das bordas de tabela, na página 210. Essa extensão primária foi registrada separadamente em `fgb-native-code-note-inventory.json`; os denominadores 240/60/447/240 permaneceram. O aditivo inclui essa nota como `orientacao_didatica`.

## Casos que exigem preservação literal

- A fonte imprime `(EM13LGG40)*Fazer` na página 209. O código curto `EM13LGG40`, o asterisco e a redação permanecem intactos. Não foi corrigido silenciosamente para outro código.
- A nota da página 210 declara que a habilidade é própria da Língua Inglesa e deve ser adaptada para Língua Espanhola. Ela foi preservada, ligada à chamada por asterisco. Essa orientação não foi convertida em equivalência nacional presumida.
- Língua Espanhola é declarada como parte do itinerário na página 112, embora seus objetos apareçam no quadro compartilhado de LGG da 2ª série. As posições desse componente conservam `curricular_track: itinerario_formativo` e evidência literal. A localização física no quadro não torna automaticamente todo o conteúdo FGB.
- Na página 266, o título isolado `PROPOSTAS DE ATIVIDADES` introduz o corpo da página 267. Ele não foi tratado como um cabeçalho de coluna sem continuação.
- Cabeçalhos quebrados como `OBJETOS DECONHECIMENT O` (232) e `OBJETOS DE` (237/251) continuam cabeçalhos, sem correção literal nem promoção a objetos.
- Rodapés numéricos não são conteúdo de competência. Hífens, acentos e pontuação nativos são preservados; a normalização limita-se a espaços entre palavras.

As 240 ocorrências usam 184 códigos literais distintos. Repetições em séries/componentes são ocorrências documentais próprias, não duplicações descartáveis. A hierarquia conserva organizador, competência/rótulo numérico, componente/campo e definição; objetos/propostas ficam ligados à definição correspondente.

## Verificação executada

- 1.392/1.392 fragmentos relidos do PDF, com 54.002 palavras nativas conferidas.
- 1.179/1.179 células de dados particionadas integralmente, sem perda ou duplicação de palavras.
- Multiconjunto de 240 âncoras literais idêntico entre fonte e aditivo.
- Anos, componentes múltiplos e evidências dos cabeçalhos conferidos; nenhum ano derivado do código.
- Carregador real: 1.292 registros, zero erros.
- Finalizador e hierarquia reais: 1.292 registros; texto, tipo, código, posições e vínculos de pai preservados.
- Schema `Learning` atual: 1.292 válidos, zero erros.
- Prova sintética declarada de supressão de duplicatas: 240 cópias genéricas fornecidas ao finalizador, 1.292 registros finais. Nenhum cache genérico foi lido ou alterado para essa prova.
- 20/20 controles positivos/negativos passaram, incluindo continuações, contaminação da coluna vizinha, ano aplicado à página inteira, perda de componentes, propostas promovidas a habilidade, rótulos promovidos a competência, correção indevida do código curto, nota descartada, alteração do PV e autoridade ampla indevida.
- Nove páginas completas leves e dois crops foram efetivamente vistos. A prova visual é amostral; a prova de palavras/células é integral no recorte.
- Repetição completa dos oito scripts produziu bytes idênticos dos dois sidecars e dos inventários primários de unidades; PDF, PV158, manifesto e fingerprints de runtime permaneceram intactos.

Provas: `fgb-primary-unit-inventory.json`, `fgb-source-role-inventory.json`, `fgb-source-specific-competences.json`, `fgb-native-code-note-inventory.json`, `fgb-v1-all-gates.json`, `fgb-v1-negative-controls.json`, `fgb-v1-visual-review.json` e `fgb-v1-reproducibility.json`.

## Execução e proposta

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ac-em/fgb-native-checkpoint.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ac-em/fgb-source-roles.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ac-em/fgb-source-competences.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ac-em/fgb-source-code-notes.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ac-em/fgb-source-units.py
var/venv-pipeline/bin/python data/manifests/uncoded/ac-em-fgb-v1-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/ac-em-fgb-v1-verify.py
var/venv-pipeline/bin/python data/manifests/uncoded/ac-em-fgb-v1-negative-controls.py
```

A proposta `fgb-v1-source-binding-proposal.json` aponta para o agregado 1.292 e acrescenta autoridade **somente para definições codificadas nas páginas 122–384**. As fronteiras 121 e 385 permanecem fora da supressão de códigos. Competências/contextos nessas páginas são carregados pelo sidecar sem suprimir seções documentais genéricas. Campos atuais da Source devem ser preservados na vinculação serial posterior à consolidação BASE.

Este trabalho não executou binding, ingestão global, alteração de cache, banco, core, publicação ou produção. A conferência pedagógica humana não foi realizada. A introdução normativa da FGB nas páginas 49–52, competências gerais anteriores, demais partes de IF/FTP, anexos, vigência atual e aceite integral da Source/UF permanecem fora deste recorte. Não há bloqueio externo constatado para este aditivo local.
