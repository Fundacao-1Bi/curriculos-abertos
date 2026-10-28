# Amazonas — revisão documental de posições e capítulos

Revisões automatizadas, sem alegação de revisão pedagógica humana ou completude das aprendizagens. O objetivo deste recorte é sustentar componente/área/idade/ano local onde o título ou a seção do próprio documento os declara; não inferir por código ou prosa incidental.

## Vínculos executados em north.json

| Fonte | Prova ligada | Escopo efetivamente verificado |
| --- | --- | --- |
| AM EI226p | position_review_path/sha0717… | 96 regiões de cabeçalho etário em35páginas; replay do autor aplica153/153faixas reproduzindo pixels |
| AM EF-AI670p | title packet71e1… +13structure_sections | 49títulos primários;10capítulos/546páginas com20fronteiras vistas, duas áreas comuns e referências; físico=impresso+2 conferido porabertura/fecho |
| AM EF-AF604p | title packet5dc365… +12structure_sections | 5títulos primários adicionais;10capítulos e duas áreas comuns;31páginas de fronteira+sumário16/tabela20 vistas; folios dos capítulos iguais aos físicos |
| AM EM292p | 5structure_sections FGB/revisão541330… | Seis aberturas/limites27/116/137/157/186/229; áreas e LP dentroFGB; IF229+ fora desses intervalos |

Integridade de arquivos/SourceSHAs e vínculos: `primary-position-packets-integration.json`, `ai-source-section-integration.json`, `em-source-section-integration.json` e propostas AI/AF. O pipeline deve reprocessar ou invalidar seus caches de configuração após esses vínculos; não foi aceito cache com metadados anteriores como prova da configuração nova.

Os capítulos não atribuem anos. Não foram adicionados contextos amplos em `position_contexts`, pois o finalizador recompõe todos os campos e isso apagaria anos de cabeçalhos de tabelas mais específicos. O contexto preciso jáexistente AF106/6ºano foi preservado. `am_positions` utiliza somente componente/área do capítulo, mantendo os anos físicos detectados/revistos separadamente.

A tabela de áreas/componentes AF20 declara dezcomponentes, incluindo Língua Espanhola. Define Ciências—CI na área Ciências da Natureza: o rótulo do capítulo permanece “Ciências da Natureza”, e o componente é “Ciências”. Páginas473–474 são competências comuns de Ciências Humanas e separador, não continuação de Ciências/Geografia. O sumário AF16 situa competências de Linguagens na99, mas o título real está na100; a99continua competências gerais. O corpo conferido prevalece sobre a indicação inexata do índice.

Os separadores AF274/316/408/446/474/522/590 e a contracapa604 não receberam folio impresso por suposição; carimbos do protocolo não são numeração do livro. Os intervalos de componentes terminam na última página substantiva vista. Na AI, a orientação OCR da488 está incorreta e foi documentada pelo revisor a partir da imagem original; o cacheOCRnão foi reescrito para esconder a divergência.

O ensaio real `chapter-integration-probe.json` executou `am_positions.positions_for_page` com as seções desligadas/ligadas em seis páginas, preservando todos os anos físicos, preenchendo somente escopos declarados e garantindo que IF230 não herdasse áreaFGB. Nenhum módulo/core foi alterado por esta frente.

## Limites restantes

OCR integral e posição correta não demonstram texto/código/unidade curricular corretos. Continuam separadas: reconciliação integral de linhas/células/continuações, definição versus referência, código original versus erroOCR, listas normativas semcódigo e completude de cada parte do índice. O EM tinha contaminação de coluna em saída preliminar; metadados de área não a corrigem. Os novos vínculos não aprovam nenhum livro nem aUF como completos.

A revisão de seções foi feita por `agent:data_north` (AF e integraçãoEM) e `agent:pb_independent` (AI); os packets de título/idade foram produzidos por `codex:am_ocr_grid` e vinculados após confirmar arquivos, hashes e SourceSHAs. Evidências visuais permanecem nos caminhos registrados; as leituras automatizadas e limites de validade são explícitos nos JSONs.
