# Modelo, publicações e consulta

## Persistência e identidades

PostgreSQL é a fonte de verdade. As migrations em `src/db/migrations/` são versionadas, transacionais, ordenadas e protegidas por advisory lock. Uma migration já aplicada com conteúdo alterado é recusada. `src/db/schema.ts` representa as tabelas por Drizzle; resolução de publicação usa consultas tipadas. Consultas nacionais e agregações usam SQL parametrizado pelos serviços compartilhados.

`publications` contém contagens e metadados imutáveis. Snapshots legados `embedded-v1` conservam o JSONB integral; publicações novas `relational-v1` guardam somente o manifesto e os metadados, com registros canônicos nas tabelas de itens/relações/membros. `publication_metadata` e `publication_coverage` materializam metadados pequenos para evitar descomprimir o JSONB nacional em cada leitura pública. `sources`, `items`, `relations` e `relation_members` materializam a consulta indexada. Triggers recusam UPDATE/DELETE de snapshots e registros públicos; correções criam outro snapshot. A transação só disponibiliza o conjunto completo. `current_publication` é um apontador alterável com eventos em `publication_events`; rollback muda o apontador sem apagar o histórico.

IDs de aprendizagem são escopados à fonte e localização. Código oficial é um atributo, pode repetir entre documentos e manter sufixos/asteriscos. Um registro sem código recebe ID técnico, nunca código oficial inventado. `text` é redação canônica extraída, `normalized_text` é auxiliar, `editorial_note` é comentário do projeto. O índice de busca deriva sua própria normalização sem modificar o payload canônico entregue.

`positions` preserva etapa, componente/área, anos documentados, rótulo do bloco, faixa etária e período. Arrays de anos representam a interseção documentada de um bloco. Campos desconhecidos são nulos; um documento que menciona um código de outra etapa não deve inventar posicionamento local nessa etapa.

## Validação e publicação

`validateBundle` verifica estrutura, IDs únicos e escopados, datas de criação, UFs, fonte/UF e etapa compatíveis, códigos nulos ou textuais, localizadores e trechos, referências de parentes e relações, dimensões separadas de relações e identidade/tipo de atores de revisão. Uma alegação de revisão humana exige evento com ator humano identificado. Isso valida o registro de autoria, sem certificar que uma pessoa examinou pedagogicamente o conteúdo. Verificação automatizada não vira homologação institucional.

`importBundle` executa transação, valida o grafo, recusa reutilizar um ID com conteúdo diferente e permite reimportar JSON semanticamente igual mesmo após reordenação de chaves por JSONB. O SHA guardado na publicação identifica a serialização importada; o sidecar `.json.sha256` verifica os bytes do arquivo distribuído antes de importar. Uma atualização da publicação padrão produz evento com ator `automated` em importação por comando.

Versões separadas: documento/edição oficial por fonte; `extraction_revision`; `mapping_revision`; `id` da publicação; `schema_version`; caminho `/api/v1`. A resolução do padrão acontece uma vez por operação. Links de próxima página e jobs de exportação fixam esse ID.

## Busca e recortes

A busca normaliza acentos, caixa e espaços somente para comparação. Códigos exatos recebem prioridade 100; aliases documentados, 90; prefixos, 80; fragmentos textuais, 20; busca lexical portuguesa, 1. Desempate por código e ID. `plainto_tsquery('portuguese', ...)`, índice GIN lexical e índices trigramas de código/texto permitem pesquisa lexical e por fragmentos sem provedor pago. Não existe anúncio de busca semântica por embeddings.

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


## Distribuição em partes e memória limitada

A instalação preferida recebe manifesto `curriculos-abertos/sharded-v1`, com metadados, fontes, cobertura, versões, contagens e partes JSONL/gzip. Cada parte declara SHA/tamanho comprimido e decodificado, tipo e quantidade. Limites: 20 MiB decodificados por parte, 5000 registros e 8 MiB por registro. O importador verifica cada checksum antes de descomprimir e todos os schemas/referências/ciclos antes de publicar. Uma segunda leitura dentro da transação evita promover arquivos alterados durante o processo. Falhas preservam o padrão anterior.

Downloads nacionais JSON/CSV são escritos em fluxo pelo worker com consultas keyset à publicação fixada. A seleção em recortes mantém membros e ancestrais necessários, identificados como suporte. Arquivos são persistidos com checksum e nunca cortados ao tamanho de uma página.

Snapshots JSON completos grandes podem ser reimportados: `stream-json` descarta as coleções em memória após cada registro e produz um cache de partes verificado. O caminho de fluxo tem limite total configurável `DATA_MAX_STREAM_BYTES` (padrão 10 GiB), além dos limites menores de string/registro/parte/metadados; ele não eleva o limite de buffers do loader legado. O original não é modificado. Hashes físicos podem mudar entre representações sem mudar o conteúdo: reaproveitar um ID só é aceito após comparar todos os registros e metadados semânticos.

JSONL usa exclusivamente LF como delimitador. U+2028 e U+2029 literais dentro de strings são preservados, e UTF-8 inválido é rejeitado. Isso foi exercitado no corpus real, não apenas em fixtures.

O campo `checksum_kind` nas publicações distingue SHA de serialização JSON legada, SHA do manifesto de instalação e hash lógico base+patch em revisões de curadoria. O checksum do arquivo de download é calculado sobre os bytes entregues e exposto separadamente. Nenhum desses hashes afirma revisão pedagógica ou vigência oficial.

Aliases são auxiliares de busca e não alteram o código exibido nem estabelecem equivalência. Origens legadas com nomes equivalentes (por exemplo regra_explicada_fonte/regra_fonte) são aceitas na filtragem e classificadas como documentadas, preservando o valor canônico de cada registro.
