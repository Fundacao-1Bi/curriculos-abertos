# Hierarquias documentais SC — cinco fontes

Enriquecimento local executado por agente automatizado. Os arquivos de entrada e o manifesto não foram alterados por esta frente. EPT/Magistério C5/C6 ficam fora deste escopo. Não há revisão humana, commit, publicação remota ou declaração de UF pronta.

Foram preservadas **2.906 folhas**, com apenas `parent_key` acrescentado, e criados **1.498 nós estruturais** com `key`/`parent_key`. Todos os nós novos usam `kind:secao_normativa`: conteúdos, campos, temas, anos, cursos e linhas de quadros não se tornam objetivos novos. Os rótulos vêm das fontes, com página, caixa e texto verificáveis. Nenhum título oficial, código, numeração macro, ano ou bimestre foi inventado.

| Fonte | Folhas preservadas | Nós novos | Organização |
| --- | ---: | ---: | --- |
| `sc-cb-eief-2019-atual` | 1.202 | 912 | 10 capítulos, 67 anos/blocos e 835 contextos nominais de linha |
| `sc-lingua-inglesa-ai` | 143 | 141 | capítulo, cinco anos e 135 contextos de linha |
| `sc-cb-em-caderno-2` | 4 | 2 | Formação Geral Básica → Matemática |
| `sc-cb-em-caderno-3` | 1.157 | 273 | seção documental, 53 títulos de seção/trilha, 19 quadros, unidades e contextos de linha |
| `sc-cb-em-caderno-4` | 400 | 170 | 25 grupos, 25 cursos e 120 unidades |

Os contextos de linha são agrupamentos geométricos documentados. Não afirmam equivalência entre aprendizagens, ordem de pré-requisito ou que uma célula de conteúdo seja uma aprendizagem. Textos extensos e células adjacentes de habilidades permanecem nas folhas originais; somente rótulos nominais curtos e verificáveis à esquerda alimentam esses nós. Etapa, componentes, anos/blocos e faixas etárias já declarados na entrada são preservados; valores ausentes não são preenchidos por suposição.

## Entradas fixadas

- `sc-eief-items.json`: `7aae29168b5d76834987b2fc3bdc8a38c9c9d82ef5c669a0da2e436d6e23ed6e`.
- `sc-em-items.json`: `65ab8b27fb841dac96680bd860126d01d0a8d42d4761dbfcbf08d714d815bfcd`.
- `sc-trilhas-all-items.json`: `eb4abf0c3d9889ed79c17619329681bd62d848bfc25ab8facfcf805efcbb093f`.

A implementação rejeita mudanças dos arquivos durante a execução. Esses hashes são de entradas finais do produtor, não dos PDFs; os hashes dos artefatos originais também são conferidos e preservados nos relatórios por fonte.

A conferência de contagens expôs quatro capas de cursos do Caderno 4 cujo resumo começava em outra página. O produtor corrigiu o contexto de 21 para os 25 cursos documentados, sem alterar textos, evidências ou localizadores das folhas. A busca de títulos deste enriquecedor lê fluxos alinhados por coluna/fonte para evitar misturar os dois campos de título nas capas.

O produtor também corrigiu os caminhos de seções do Caderno 3: a raiz integrada da página 163 é conservada literalmente sem número inventado, seguida pela trilha 5.1 da página 164 para as células da página 170. Contextos antigos de unidade anteriores à nova trilha não são usados como pais. A revisão final fixada não tem esses achados pendentes.

A unidade “As Diferentes Moedas no Brasil” que inicia na página 303 do Caderno 4 aponta para o título explicitamente legível na primeira linha continuada da página 304. A evidência original dessa associação foi conservada. Isso não transforma a página seguinte em ano/período nem altera o texto da aprendizagem.

## Execução e prova

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-sc-hierarchy/enrich_sc_hierarchy.py --include-c3
var/venv-pipeline/bin/python docs/evidence/source-audit-sc-hierarchy/verify_sc_hierarchy.py
```

Usa o ambiente com PyMuPDF corrigido. As saídas ficam em `data/manifests/uncoded/sc-hierarchy-{source_id}.json`, como wrappers de uma fonte com `items` contendo nós e folhas. Cada arquivo já passou pelo importador real `pipeline.ingest.source_uncoded_items`.

`verify_sc_hierarchy.py` é uma etapa separada: importa e finaliza tanto a entrada original quanto a saída enriquecida com as funções reais `source_uncoded_items` e `finalize_items`. Compara por ID canônico os campos ID, fonte, currículo, código, texto, texto normalizado, tipo, posições, evidências e contexto. Todas as 2.906 folhas permanecem idênticas nesses campos. Os 1.498 nós e todos os fragmentos passam pelo verificador literal do importador, os 2.906 pais das folhas resolvem e não há ciclos.

`actual-importer-finalizer-verification.json` guarda essa prova. `hierarchy-report.json` e os relatórios por fonte registram os hashes de entrada/saída, os papéis dos nós, rótulos não localizados e achados. Na execução final não há rótulo obrigatório sem evidência nem pai pendente. `reproducibility.json` registra a repetição e compara os bytes das cinco saídas.

A inspeção visual dirigida conferiu dez páginas: raiz/trilha/unidade do Caderno 3; as quatro capas corrigidas do Caderno 4; o título continuado na página 304; e a ligação de ano/quadro em Alfabetização e Língua Inglesa. `visual-selection.json` registra o escopo. A conferência visual não é uma leitura pedagógica humana de todas as folhas.

## Integração

O responsável pelo manifesto deve trocar `uncoded_items_path` das cinco fontes pelos wrappers correspondentes após conferir os hashes no relatório final. A integração global, publicação, navegação do portal/API/MCP e o aceite da UF são etapas separadas. Esta frente não modifica o manifesto nem os dados-fonte dos adaptadores.
