# AM — peer visual dos códigos primários

Frente automatizada `agent:rs_adapter:visual-primary-code-peer`, autorizada pelo root. Não é revisão humana ou pedagógica. O escopo inicial contém exatamente **2.629 slots conhecidos em 1.038 páginas**: 1.202 EF-AF, 1.017 EF-AI, 153 EI e 257 EM. Esse universo vem dos crops inventariados anteriormente; não prova que o OCR encontrou todos os códigos impressos nem todas as habilidades da fonte.

`am-code-slot-ledger.json` guarda fonte/SHA/página/slot, coordenadas, matriz, hashes e hipóteses dos reconhecedores. O ledger começa pendente e só muda com uma leitura visual explicitamente registrada. Tesseract/Vision/regex e consenso não são aceitos como confirmação primária.

## Pixels e proveniência

Os antigos crops tinham descritores e hashes, mas não PNGs persistidos. Os PDFs AM têm, nas páginas inspecionadas, uma imagem raster incorporada por página. `build-contact-sheets.py` verifica o SHA original por streaming, extrai os bytes dessa imagem por xref, recorta os pixels nativos e aplica apenas rotação ortogonal sem perda para leitura. Cada recorte registra bytes da imagem, dimensões, crop, matriz PDF, hashes dos pixels nativos/orientados e PNG privado. A folha amplia por Lanczos e mostra somente localizador; oculta hipóteses OCR.

Um diagnóstico de reconstrução verificou que a renderização recortada do MuPDF muda pixels de reamostragem em relação ao crop de uma página inteira. Um único controle em RAM reproduziu o hash legado e confirmou o mapeamento. Não se afirma igualdade entre samplers diferentes. A revisão usa os pixels originais incorporados, sem renderizar ou persistir páginas completas e sem OCR adicional.

Todos os recortes/folhas permanecem em `var/private-evidence/source-audit-am-code-peer/`. Evidência commitável contém hashes, locadores e leituras necessárias.

## Leituras e propostas

`record-visual-review.py` recebe leituras explícitas feitas na folha e grava ator automatizado, data, código literal, rótulo observado, notas e prova visual. Delimitadores não são afirmados quando ficam fora do recorte. A ordem/repetição dos códigos é preservada; não se completa sequência por código nacional ou vizinhança. Dúvida de glifo ou recorte insuficiente resulta em código nulo no ledger e não produz referência. Uma releitura conserva o histórico anterior, inclusive correções de leitura.

`build-reference-proposal.py` emite apenas `referencia_no_documento`, `code=text=literal confirmado`, sem posições inferidas, equivalência ou corpo de habilidade validado. Esses arquivos `data/manifests/uncoded/am-primary-code-references-*.json` são **propostas data-only não ingeridas**. Nenhum Source está ligado a eles. O core1.5 ainda não possui verificador de revisão raster; não se usa `ocr_reference_path` para contornar o contrato. Definições antigas e seus status/textos não são alterados.

Estados admissíveis: `confirmed_primary_code_only`, `ambiguous_primary_glyphs`, `crop_insufficient`, `not_a_code_in_this_crop`. Mesmo o último não prova ausência de habilidade no documento. O progresso atualizado está no ledger e em `am-code-visual-reviews.json`; a revisão do conjunto continua enquanto houver slots pendentes.

## Comandos

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-am-code-peer/build-inventory.py
var/venv-pipeline/bin/python docs/evidence/source-audit-am-code-peer/build-contact-sheets.py --pilot
var/venv-pipeline/bin/python docs/evidence/source-audit-am-code-peer/build-contact-sheets.py --start 12 --count 60
var/venv-pipeline/bin/python docs/evidence/source-audit-am-code-peer/record-visual-review.py --manifest docs/evidence/source-audit-am-code-peer/slots-0013-0072-manifest.json --readings docs/evidence/source-audit-am-code-peer/slots-0013-0072-visual-readings.json
var/venv-pipeline/bin/python docs/evidence/source-audit-am-code-peer/build-reference-proposal.py
var/venv-pipeline/bin/python docs/evidence/source-audit-am-code-peer/verify-primary-code-review.py --replay-primary
```

Reexecução do inventário reaplica os registros visuais já salvos por slot/SHA, preservando o progresso. O censo e os caches antigos não são modificados. Não há commit, ação remota ou afirmação de prontidão de UF/fonte.

## Fechamento dos slots conhecidos

Todos os **2.629 slots / 1.038 páginas** foram lidos em folhas sem hipóteses OCR. Resultado: **2.628 códigos confirmados**, **1 localização sem código no recorte**, **0 não revisados** e **0 ambiguidades ativas**. Os 48 registros com histórico incluem releituras e sobreposição do piloto; o histórico não é apagado.

| Fonte | Slots revisados | Referências code-only propostas | Localização rejeitada |
|---|---:|---:|---:|
| EF anos finais | 1.202 | 1.202 | 0 |
| EF anos iniciais | 1.017 | 1.017 | 0 |
| Educação Infantil | 153 | 152 | 1 |
| Ensino Médio | 257 | 257 | 0 |

O slot `am-rca-ei:p114:slot001` (índice global 2309) contém literalmente **“e folhear livros.”** no recorte ampliado. Permanece com `code=null`, status `not_a_code_in_this_crop` e fora das propostas. Isso rejeita somente a localização do candidato e não demonstra ausência de habilidade na página.

Anomalias impressas foram preservadas: `EF09LE9AM` (AF p407), `EF06AM01AM` (AF p418), `EF08HI11` em quadro de Geografia (AF p500), `EF35LP08 AM` com separação antes de AM (AI p210/255/303), `EF06CI05` no conjunto de anos iniciais (AI p585) e `EI02EO4` com um único dígito final (EI p77). São leituras documentais; não se afirma adequação do código. A primeira leitura de AI p210 foi corrigida após reabrir o recorte e visualizar o sufixo AM; os eventos anteriores ficam registrados.

`verify-primary-code-review.py --replay-primary` verificou hashes das quatro fontes, dos insumos e das 55 folhas/manifests atualmente usados pelos registros; refez **2.629/2.629** crops diretamente dos bytes da imagem incorporada, comparou pixels RGB nativos e orientados, PNGs e transformação para bbox PDF. Decodificou uma imagem por vez em RAM, sem renderização ou OCR. Os cinco controles negativos rejeitam literal alterado, afirmação de corpo validado, posição inferida, emissão de slot não confirmado e crop primário deslocado. Esse replay verifica a proveniência mecânica, não constitui uma segunda leitura dos códigos.

As quatro propostas foram regeneradas com bytes idênticos. `am-code-primary-versus-OCR-differences.json` registra uma comparação secundária feita **depois** da leitura primária: 311 diferenças, sendo 68 contra candidatos não nulos e 243 contra candidatos nulos. Nenhum valor foi trocado automaticamente com base nessa comparação. Ela não é prova de leitura.

Pins e resultados finais: `am-code-review-verification.json`, `am-code-proposal-idempotence.json` e `am-code-review-handoff.json`. O status permanece **proposta data-only não ingerida**: o core1.5 não possui verificador raster dessa modalidade, os textos das definições não foram revistos e o universo dos slots conhecidos não é um censo independente de todos os códigos/objetivos impressos.
