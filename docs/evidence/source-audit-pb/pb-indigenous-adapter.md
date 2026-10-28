# PB: objetivos da Educação Escolar Indígena

O adaptador `data/manifests/uncoded/pb-eief-indigenous.py` lê o original imutável `pb-proposta-ei-ef`, SHA-256 `b55786376874ab6a46064c44726d578d37f550a99a702069fe7065946ce26383`, conforme o manifesto Nordeste. Percorre textualmente todas as páginas físicas 538–631 e identifica os objetivos explicitamente apresentados nas listas e nos dois parágrafos que a própria fonte chama de objetivo. Não acessa rede nem modelos.

A saída `pb-eief-indigenous.json` contém 180 registros: 42 nós estruturais, 63 objetivos, 54 competências e 21 critérios avaliativos. Os títulos mistos “Sugestões de competências e conteúdos” permanecem como contexto original; seus tópicos nominais são nós de estrutura, e os enunciados verbais são conservados como competências. Os critérios de avaliação de História, Arte e Educação Física conservam seu tipo. A Matemática e a Educação Física também apresentam um objetivo em parágrafo narrativo, preservado integralmente com a introdução contextual.

Todos os registros têm código nulo. As etapas, os anos regulares e as faixas etárias não são atribuídos aos resultados indígenas quando o próprio trecho não os declara: `positions:[]`, com modalidade, componente, motivo de posição desconhecida, hierarquia, `parent_key` e ordem física em metadados. Não se estabelece equivalência com a BNCC ou com as etapas regulares.

Os 168 marcadores de lista encontrados na seção foram confrontados com as decisões de escopo: 136 inícios de resultados/critérios foram selecionados, e 32 marcadores de normas, orientações ou conteúdos foram excluídos com motivo. Os dois objetivos narrativos completam os 138 resultados e critérios. As listas “Conteúdos” de Arte, as unidades de medidas sugeridas na Matemática e os temas/conteúdos de Educação Física não viraram aprendizagens. O inventário das páginas e o registro de exclusões estão nos arquivos `pb-indigenous-page-inventory.json` e `pb-indigenous-excluded-lists.json`.

A verificação integral reextraiu cada um dos 180 fragmentos pelas caixas do PDF: zero divergências. Também verificou união dos fragmentos, chaves únicas, pais existentes, código nulo e ausência de posição regular inferida. Não há item individual partido entre duas páginas neste conjunto; há listas e seus agrupamentos que continuam nas páginas seguintes, cujos pais são mantidos.

Foram renderizadas e efetivamente inspecionadas 21 páginas, cobrindo Línguas, História, Matemática, Geografia, Saúde, Arte e Educação Física, todos os tipos de registro e os limites entre objetivos, conteúdos e avaliação. A seleção, os hashes e o resultado da revisão automatizada estão em `pb-indigenous-visual-samples.json`. Isso não é revisão pedagógica humana.

Comando de reprodução:

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/pb-eief-indigenous.py
```

A função `extract(write=True)` retorna um dicionário com `source_id`, `artifact_sha256`, metadados e `items`; o adaptador PB principal pode incorporar esse conjunto. Reexecução integral produziu bytes idênticos: SHA-256 `98022b5d4795ac6da5fcf67f4a5a09df41552c184f40b0dd9a5973ab1a161dd9`.

Pendentes fora desta frente: comparação pelo verificador independente, integração no sidecar PB principal, importação/publicação central e aceite da fonte/UF. Nenhum manifesto central, pipeline, commit ou recurso remoto foi modificado por esta frente.
