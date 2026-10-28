# Adaptador SC — Educação Profissional e Magistério

Esta frente implementa e executa a extração dos cadernos 5 e 6 do Currículo Base do Ensino Médio do Território Catarinense, para DAT-01/DAT-02/DAT-05, ING-02/ING-03 e ESC-02. A revisão é automatizada, por agente; não houve revisão humana, commit ou ação remota. A situação de vigência/edição continua sendo a registrada no manifesto oficial, sem alegação adicional de homologação pelo projeto.

## Fontes e alcance

| Fonte | PDF | SHA-256 |
| --- | --- | --- |
| `sc-cb-em-caderno-5` | 824 páginas; 28 cursos técnicos do índice | `cc9d7f60be1588334b1a3a5542f6517a079e23b3e55159e331b63b546cb41934` |
| `sc-cb-em-caderno-6` | 638 páginas; formação geral, unidades, componentes, eletivos, Magistério Indígena, Educação Especial e anexos | `1fa4e94263494ce01f76f30d87d6cc41c71dd8d61e9569e9dc2907a746f5ad78` |

Os caminhos e URLs são resolvidos em `data/manifests/central-south.json`; os bytes originais são verificados antes da extração. Os PDFs não foram republicados. O índice do Caderno 5 fornece 28 cursos; o do Caderno 6 fornece 58 entradas, incluindo partes, componentes e anexos. Entradas de organização, políticas, avaliação e metodologia não são automaticamente aprendizagens.

O resultado integrado está em `data/manifests/uncoded/sc-em-ept-items.json`: **6.314 registros**, sendo **4.549 do Caderno 5** e **1.765 do Caderno 6**. Há 6.157 registros de objetivos/competências/habilidades e 157 de contexto normativo. Os tipos distinguem objetivo geral de curso, específico de curso, objetivo de trilha, objetivo de aprendizagem, competência profissional, habilidade do eixo, habilidade do componente e seção normativa. As 10 competências gerais docentes são preservadas individualmente. Contagens detalhadas estão em `output-summary.json`.

São 807 registros com identificadores decimais originais, conservados sem conversão para códigos da BNCC. Enumerações simples como o número 7, impresso sem ponto na competência geral docente, permanecem `source_number`, com `code:null`. Códigos alfanuméricos já extraídos pelo pipeline central não são duplicados como objetivos sem código; suas células permanecem no inventário e no arquivo `coded-cell-contexts.json`.

## Extração e hierarquia

O adaptador lê todas as páginas e usa linhas estritas da grade para localizar colunas de habilidades/competências. Isso evita tratar fundos de texto do editor de origem como novas linhas de tabela. Objetivos gerais, específicos, de trilha e de unidade são delimitados por seus cabeçalhos explícitos. Marcadores e quebras de linha após pontuação terminal separam os itens; agrupamentos sem código não recebem numeração oficial inventada.

As evidências usam palavras completas selecionadas pelo centro geométrico. Palavras, numeradores, marcadores e trechos em fontes diferentes podem aparecer em linhas técnicas separadas no PDF; são reunidos pelo mesmo alinhamento físico antes da segmentação. O primeiro processamento revelou perda do verbo em listas como “Compreender a importância...”; a regra foi corrigida e o conjunto inteiro reprocessado.

O posicionamento conserva etapa EM, curso, unidade/componente, trilha e parte documental. I/II de componentes e números de trilha não são convertidos em anos escolares ou períodos letivos. Anos/séries são preenchidos somente quando explícitos no título da tabela, como Matemática — 3ª série. O título original que fundamenta isso fica em `position_header`.

Há **330 itens com evidências em várias páginas** e **6.674 fragmentos**. O adaptador mantém uma evidência por fragmento e concatena o texto na ordem documental. A revisão visual identificou que objetivos específicos de Edificações atravessavam as páginas 344–345; a retomada das regiões de objetivos e perfis foi corrigida para todas as páginas. O verificador passou a ter um denominador separado para esses prefixos de continuação, pois conferir apenas cabeçalhos não detectava essa omissão.

Relações de equivalência pedagógica não são inferidas por proximidade, repetição de código ou semelhança textual. Os identificadores e redações próprias permanecem vinculados à fonte selecionada. Dimensões como “Conhecimento Profissional” são contexto normativo, não habilidades novas.

## Anexos digitalizados

O Caderno 6 contém 64 páginas com imagem e pouco/nenhum texto nativo entre as páginas 573–638. Todas foram processadas com Tesseract em português, incluindo capas. O resultado tem palavras, caixas em pontos PDF e confiança por palavra. O corpo de 62 páginas foi preservado em `sc-em-ept-annex-items.json`, também incluído no resultado integrado, com `kind:secao_normativa`. Capa e contracapa ficam como metadados; as páginas 590 e 637 são vazias no artefato.

Esses anexos incluem legislação, pareceres e a reprodução da BNC-Formação já estruturada no corpo nativo. Seu OCR não é apresentado como nova aprendizagem local nem como transcrição humana. A confiança e a origem OCR permanecem explícitas. As referências `ocr_reference_path` e `ocr_reference_sha256` permitem verificar o cache de palavras usado para cada evidência. O importador central precisa respeitar essa origem ao verificar a prova; exigir correspondência no texto nativo das páginas digitalizadas rejeitaria evidências reais de OCR.

O cache OCR é local em `data/raw/SC/sc-ept-ocr-cache/`. Pode ser reconstruído pelas fontes e pelo script entregue; não substitui os PDFs originais.

## Verificação e denominadores

`sc-em-ept-verify.py` não importa a função extratora. Reconstrói expectativas a partir das palavras/cabeçalhos e tabelas da fonte, usando o cache nativo identificado pelo hash do PDF. O denominador contém:

- 28 cursos técnicos e as 58 entradas do índice do Magistério, preservados em `source-index-inventory.json`;
- 843 cabeçalhos explícitos de objetivos, 678 declarações de unidade e 1.484 células de habilidades/competências;
- 4.486 IDs canônicos reconstruídos independentemente dos inícios de listas das células e das competências gerais docentes, todos encontrados e verificados;
- as regiões de prefixo de objetivos que continuam na página seguinte, verificadas em `independent-objective-continuations.json`;
- 64 páginas OCR processadas, 62 contextos normativos e os respectivos hashes de prova.

Os 4.486 IDs independentes são um subconjunto explicitamente delimitado; não são uma cópia dos 6.314 IDs produzidos. Os demais objetivos são reconciliados pelos cabeçalhos/unidades/regiões e pela validação integral dos fragmentos. Todas as 6.314 entradas e seus 6.674 fragmentos passam pela conferência de conteúdo e caixa; não há colisão, texto fora da evidência, cabeçalho de objetivo sem região, célula sem código não contemplada ou ID esperado independente faltante no resultado final. O relatório diferencia esses critérios em vez de anunciar uma reconciliação pedagógica humana.

Amostragem visual: 72 páginas, em nove folhas de contato, cobrindo os 28 cursos EPT, componentes do Magistério com itens locais e casos dirigidos de anexos, códigos decimais, marcadores e continuações. A inspeção de contato confere organização, cabeçalhos e colunas. Casos dirigidos foram lidos em resolução integral. A seleção, escopo e IDs das amostras ficam em `visual-sample-selection.json`; isso não é leitura humana nem conferência visual linha a linha das 1.462 páginas.

## Comandos reproduzíveis

```sh
# Python 3.11 e PyMuPDF corrigido 1.26.7 ou posterior
var/venv-pipeline/bin/python data/manifests/uncoded/sc-em-ept-ocr.py
var/venv-pipeline/bin/python data/manifests/uncoded/sc-em-ept-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/sc-em-ept-verify.py
# Apenas material de inspeção; requer Pillow 12.1.1
var/venv-pipeline/bin/python data/manifests/uncoded/sc-em-ept-render.py
```

O OCR usa `tesseract` com `var/tessdata/por.traineddata`, `--psm 3` e `-c tessedit_create_tsv=1`. O parâmetro explícito evita depender de um arquivo de configuração TSV ausente no diretório de idioma. A escala raster é 2,5, com caixas reconvertidas a pontos PDF. Três processos isolados podem pré-computar o cache nativo com `sc-em-ept-cache.py`; PyMuPDF não é compartilhado entre threads. O cache nativo fica em `data/raw/SC/sc-ept-native-cache/` e não altera o cache central.

`reproducibility.json` registra a reexecução integral e o hash do resultado. O verificador e seus inventários não marcam homologação ou publicação apenas por existir um teste. O estado local efetivo fica em `checkpoint.json`.

## Integração pendente

O responsável pelo manifesto deve associar `data/manifests/uncoded/sc-em-ept-items.json` aos dois sources. O contrato permite array de múltiplas fontes e código original opcional. O agente de pipeline foi avisado sobre identificadores decimais e provas OCR.

Esta entrega não declara Santa Catarina pronta. Permanecem sob responsabilidade da coordenação: importação/publicação central, tratamento das provas OCR na integração, reconciliação dos itens codificados e dos outros cadernos, auditoria independente de agente e jornadas do produto. Não houve alvo remoto autorizado.
