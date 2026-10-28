# Modelo, publicações e consulta

## Persistência e identidades

PostgreSQL é a fonte de verdade. As migrations em `src/db/migrations/` são versionadas, transacionais, ordenadas e protegidas por advisory lock. Uma migration já aplicada com conteúdo alterado é recusada. `src/db/schema.ts` representa as tabelas por Drizzle; resolução de publicação usa consultas tipadas. Consultas nacionais e agregações usam SQL parametrizado pelos serviços compartilhados.

`publications` contém o snapshot JSONB canônico e contagens. `publication_metadata` e `publication_coverage` materializam metadados pequenos para evitar descomprimir o JSONB nacional em cada leitura pública. `sources`, `items`, `relations` e `relation_members` materializam a consulta indexada. Triggers recusam UPDATE/DELETE de snapshots e registros públicos; correções criam outro snapshot. A transação só disponibiliza o conjunto completo. `current_publication` é um apontador alterável com eventos em `publication_events`; rollback muda o apontador sem apagar o histórico.

IDs de aprendizagem são escopados à fonte e localização. Código oficial é um atributo, pode repetir entre documentos e manter sufixos/asteriscos. Um registro sem código recebe ID técnico, nunca código oficial inventado. `text` é redação canônica extraída, `normalized_text` é auxiliar, `editorial_note` é comentário do projeto. O índice de busca deriva sua própria normalização sem modificar o payload canônico entregue.

`positions` preserva etapa, componente/área, anos documentados, rótulo do bloco, faixa etária e período. Arrays de anos representam a interseção documentada de um bloco. Campos desconhecidos são nulos; um documento que menciona um código de outra etapa não deve inventar posicionamento local nessa etapa.

## Validação e publicação

`validateBundle` verifica estrutura, IDs únicos e escopados, datas de criação, UFs, fonte/UF e etapa compatíveis, códigos nulos ou textuais, localizadores e trechos, referências de parentes e relações, dimensões separadas de relações e identidade/tipo de atores de revisão. Uma alegação de revisão humana exige evento com ator humano identificado. Isso valida o registro de autoria, sem certificar que uma pessoa examinou pedagogicamente o conteúdo. Verificação automatizada não vira homologação institucional.

`importBundle` executa transação, valida o grafo, recusa reutilizar um ID com conteúdo diferente e permite reimportar JSON semanticamente igual mesmo após reordenação de chaves por JSONB. O SHA guardado na publicação identifica a serialização importada; o sidecar `.json.sha256` verifica os bytes do arquivo distribuído antes de importar. Uma atualização da publicação padrão produz evento com ator `automated` em importação por comando.

Versões separadas: documento/edição oficial por fonte; `extraction_revision`; `mapping_revision`; `id` da publicação; `schema_version`; caminho `/api/v1`. A resolução do padrão acontece uma vez por operação. Links de próxima página e jobs de exportação fixam esse ID.

## Busca e recortes

A busca normaliza acentos, caixa e espaços somente para comparação. Códigos exatos recebem prioridade 100; prefixos, 80; fragmentos textuais, 20; busca lexical portuguesa, 1. Desempate por código e ID. `plainto_tsquery('portuguese', ...)`, índice GIN lexical e índices trigramas de código/texto permitem pesquisa lexical e por fragmentos sem provedor pago. Não existe anúncio de busca semântica por embeddings.

Filtros combinam UF, currículo, edição, etapa, componente/área, tipo, faixa, período e dimensões de relação/revisão. Ano individual ou faixa inclui blocos cuja lista documentada de anos intersecta a consulta. Itens sem ano ficam fora, salvo `include_unknown_positions=true`. Isso não atribui um ano ao item. Registros com `positions: []` também podem ser incluídos explicitamente: a etapa precisa constar da fonte, e o fallback de componente só se aplica quando a fonte declara um único componente compatível. Filtros de área/faixa/período não são inferidos para um item sem posicionamento. Limite de página: 100; lote: 100; comparação: duas ou três UFs distintas. Comparações podem selecionar currículo e edição individualmente por UF.

## Relações e disponibilidade

Cada relação contém membros com papel/direção e alcance. `relation_type`, `origin`, `technical_validation_status`, `pedagogical_review_status` e `publication_status` são dimensões independentes. O pipeline inicial captura referência literal de código nacional, sem inferir equivalência textual integral. Relação entre dois itens locais não é consequência automática de uma referência nacional comum.

Panorama e matriz mostram as 27 UFs. Vínculos explícitos aparecem como documentados; interpretações editoriais e candidatos mantêm seus estados. Sem vínculo, o sistema só informa nenhuma correspondência localizada quando a cobertura do recorte estiver reconciliada; caso contrário informa dados insuficientes. A etapa nacional é usada no panorama quando inequívoca. Nenhum estado é conclusão sobre o ensino ou aprendizagem dos estudantes.

A prontidão de UF exige EI/EF/EM e todas as linhas esperadas do inventário com partes processadas/reconciliadas equivalentes ao denominador positivo e sem erros críticos. O release gate independente verifica as evidências documentais; flags de interface não aprovam o lançamento.

Análises contam itens únicos, ocorrências por posicionamento e relações separadamente. Grupos por componente podem se sobrepor se a fonte documentar múltiplos posicionamentos. A matriz é paginada por aprendizagem nacional; a cardinalidade de desdobramentos locais não infla seu denominador nacional. Todas as contagens oferecem os filtros e identificação da publicação.

## Downloads e reimportação

A base nacional JSON reproduz o snapshot integral e pode ser reimportada idempotentemente. Recortes JSON preservam os IDs originais, adicionam membros de vínculos diretos e ancestrais como suporte explícito e recebem ID derivado determinístico: `parent_publication`/`export_manifest.publication` identificam a publicação consultada. `matched_item_count` conta o filtro; `support_item_ids` distingue suporte. A cobertura nacional de origem não certifica esse subconjunto. A distribuição também suporta `.json.gz` determinístico. O loader verifica o SHA-256 do gzip antes de descomprimir com limite de saída, depois confere SHA-256 e tamanho do JSON decodificado. `latest.json` identifica ambos os conjuntos de bytes. O JSON original permanece imutável localmente; o gzip e os sidecars bastam para distribuição/reinstalação. Limites padrão: 256 MiB comprimidos e 512 MiB decodificados, configuráveis por `DATA_MAX_FILE_BYTES` e `DATA_MAX_DECODED_BYTES`.

O importador valida o grafo autocontido e recusa substituir a publicação de origem por um recorte.

CSV da base/recorte usa cabeçalho `record_type,id,payload_json`. Há linhas `manifest`, `source`, `item`, `relation` e `coverage`; os payloads JSON conservam campos, hierarquia, relações e localizadores. Assim não há achate silencioso de estruturas muitos-para-muitos. Células potencialmente executáveis em planilhas são prefixadas com apóstrofo; o texto original é conservado em JSON/banco.

Exports de panorama, comparação e análises retornam relatórios completos em JSON, sem limitar ao tamanho da página da interface. CSV de relatórios usa uma célula `json_report` com o relatório estruturado integral. O manifesto informa esse formato. A impressão HTML do portal é o relatório legível. Exports grandes são jobs persistentes do worker.

## Correspondência conceitual CASE / 1EdTech

Esta é uma orientação de interoperabilidade; o produto não declara certificação nem implementa integralmente a API CASE.

| Modelo local | Conceito CASE | Limite |
|---|---|---|
| Currículo/documento edição | CFDocument | A publicação de dados é distinta da edição oficial. |
| Aprendizagem e ID canônico | CFItem / identifier / uri | Código oficial não é a chave global. |
| Relação com membros | CFAssociation | Grupos muitos-para-muitos exigem representar os membros e seu alcance; não condensar em equivalência. |
| Hierarquia parent_id | isChildOf | Somente hierarquia documentada, sem inferir pré-requisito. |
| Fonte/evidência | notas/metadados de proveniência | Localização, hash, origem e revisão permanecem metadados explícitos do projeto. |
| Posicionamento | educationLevel / metadata | Blocos, EI e períodos preservam os rótulos próprios da fonte. |

Referência consultável: https://www.imsglobal.org/spec/CASE/v1p1/impl . O mapeamento é de conceitos; não promete endpoints CASE.
