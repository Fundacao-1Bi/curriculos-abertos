# Pará EI/EF — adaptador documental da edição2019

Pacote de1972 registros estabilizado para a fonte `pa-dcepa-ei-ef` (361 páginas físicas, SHA256 `6b101a029e7fc40b10feb79969309251337eb01fc2491c9e0b38563094fa8ec5`). A página7 declara2ªedição revisada/publicada2019 e aprovação pela Resolução769/2018. Isso não comprova vigência atual, completude de complementos posteriores ou equivalência com outra edição/arquivo.

Arquivo para vinculação pelo proprietário do manifesto: `data/manifests/uncoded/pa-dcepa-items.json`, SHA256 `946e4f16523b127bbbf35e15947655bd52a6d890920cc3e7cce49753b35c424b`. Este agente não alterou manifesto, pipeline, banco ou publicação.

## Denominadores anteriores à saída

O censo próprio percorreu todas361 páginas do PDF imutável:175 segmentos físicos de tabela,4945 células. A detecção usa traços estritos, sem confundir preenchimentos coloridos com bordas. A seleção do texto usa centros de palavras nativas, evitando vazamento para células vizinhas quando a caixa de um glifo cruza a borda. O inventário de objetivosEF foi contado tanto por inícios nas células da terceira coluna quanto por marcadores na lista nativa de palavras do PDF, com multiconjuntos iguais.

| Parte | Denominador e produto |
|---|---|
| EF local,112–323 |64 quadros de10componentes;676 objetivos;700 fragmentos não vazios na coluna própria;41 células de continuação sem marcador;15 células com múltiplos objetivos |
| HierarquiaEF |64 cabeçalhos de ano/bloco,256 eixos literais e411 células/grupos de subeixos; três objetivos com subeixo vazio explicitamente conservado |
| EI,73–88 |3grupos de idade,15ocorrências de campos,93objetivos codificados próprios(29+32+32) |
| EI adicional na coluna própria |2parágrafos sem código,77/78; mantidos como filhos distintos, sem herdar código |
| EI experiências |403fragmentos de célula →401aprendizagens, com duas continuações comprovadas74→75 e87→88 |
| Competências gerais,23–24 |10linhas completas, preservando papéis de Competência/Oque/Para/Resultado; linha6 continua24 |
| Linguagens,105–106 |6citações explícitas de competências |
| EducaçãoFísica,184–186 |10ocorrências citadas, preservando agrupamentos numéricos e repetição da própria fonte |
| Inglês,222–223 |6competências citadas; uma continua entre páginas |
| EnsinoReligioso,314–315 |6competências e4objetivos explícitos(a..d) |
| Matemática,293–295 |3citações explícitas; uma continua293→294; fonte295 atribui formulação composta à “quinta competência geral”, preservada sem corrigir/desmembrar por template |
| DireitosEI,67 |6nomes literais; nenhuma definição copiada de outro documento |

Produto:749 nós estruturais,1176 objetivos/aprendizagens,41competências e6direitos. Os1176 objetivos são676EF locais+93EI codificados+2EI adicionais sem código+401experiênciasEI+4objetivos narrativosER. Os números decimais dos objetivosEF são `source_number`, com `code:null`; nunca são transformados em IDs oficiais nacionais/estaduais inventados.

## Associação e hierarquia

Eixo→Subeixo→Objetivo segue células e cabeçalhos físicos. Células mescladas com vários subeixos/objetivos conservam o agrupamento literal. Anos/blocos vêm dos cabeçalhos de cada quadro, inclusive os que abrem no meio de uma página; códigos vizinhos não restringem um objetivo de1º–3º a um único ano. EI usa cabeçalhos físicos de faixa etária e campo, sem inferência exclusiva pelo código.

As2117 células de HabilidadesEF ficam no inventário de referências auditadas. A associação usa sobreposição vertical positiva com células de objetivos, com relações compartilhadas quando necessário. `source_context.reference_codes` contém apenas códigos literais dessas células adjacentes, com texto/caixa/linha de auditoria em `adjacent-reference-row-audit.json`. Isso não afirma equivalência semântica. As definições codificadas verdadeiras da coluna Habilidades continuam a cargo do pipeline genérico; não devem ser reclassificadas em massa como simples referência documental.

Os dois parágrafos sem código na coluna própria deEI são “Participar...”77 e “Atentar...”78. O censo de todas as células/continuações encontrou apenas esses dois intervalos de25pt entre parágrafos. Os paisEI02EO01/EI02EO06 conservam somente o parágrafo codificado. Os filhos permanecem sem código; as experiências da célula compartilhada não recebem uma alocação semântica exclusiva inventada para um dos parágrafos.

Anomalias próprias: eixo impresso `INGUAGEM E SUAS FORMAS COMUNICATIVAS`280 permanece literal; Sub-eixo de Valores em Matemática9º311–312 está vazio e não recebe o texto do8º; a repetição sobre preconceitos em EducaçãoFísica186 é preservada em seus dois grupos declarados. Não se corrigem grafia, gramática, atribuições ou numeração silenciosamente.

## Verificação executada

- 2189/2189 fragmentos relidos do PDF original,27514 palavras conferidas.
- 700/700 partições completas das células de objetivosEF e102/102 células próprias de objetivosEI, sem perda/duplicação de palavras.
- 403/403 fragmentos de experiênciasEI particionados em401itens, com os dois vínculos de continuação explícitos.
- Inventários:676âncorasEF,93códigosEI,64quadros/10componentes e51unidades narrativas reconcilidados com os denominadores feitos antes da saída.
- Cabeçalhos físicos de posição relidos e anos/faixas confrontados; hierarquia ancestral de ano também conferida.
- 52 páginas efetivamente vistas em imagem:EI73–88 integral,21páginasEF estratificadas de todos os10componentes e15páginas de competências/direitos/narrativas. Evidências/hashes em `visual-review.json`; imagens privadas em `var/private-evidence/source-audit-pa/pa-adapter-*.png`.
- Carregador real `ingest.source_uncoded_items`/`evidence_check`:1972/1972 registros aceitos, zero erros, sem alterar manifesto/bundle/cache/banco. Evidência em `actual-loader-probe.json`.
- 10/10 controles positivos/negativos passaram, incluindo texto fabricado, troca de coluna de evidência, código adjacente atribuído como ID local, ano/faixa indevidos, perda de continuação, empréstimo de subeixo do ano anterior e checksum divergente. A geometria é conferida pelo gate independente, pois coincidência de texto na página não prova a caixa correta.
- Execuções completas repetidas geram bytes idênticos, com SHA do PDF original inalterado; `reproducibility.json` registra os hashes.

Comandos:

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/pa-dcepa-census.py
var/venv-pipeline/bin/python data/manifests/uncoded/pa-dcepa-inventory.py
var/venv-pipeline/bin/python data/manifests/uncoded/pa-dcepa-narrative.py
var/venv-pipeline/bin/python data/manifests/uncoded/pa-dcepa-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/pa-dcepa-verify.py
var/venv-pipeline/bin/python data/manifests/uncoded/pa-dcepa-negative-controls.py
var/venv-pipeline/bin/python data/manifests/uncoded/pa-dcepa-loader-probe.py
```

## Integração e limites

`source-binding-proposal.json` propõe a vinculação serial pelo dono do manifesto e autoridade somente para códigosEI nas páginas físicas73–88, suprimindo duplicação dos93pais. Não propõe suprimir ou reclassificar as definições codificadasEF112–323. A estrutura normativa em prosa continua preservada pelos segmentos documentais do pipeline, sem converter metodologia, conceitos ou perguntas em aprendizagens só por estarem no currículo.

Esta verificação é documental e automatizada. Revisão pedagógica humana não foi realizada. A reconciliação global da fonte, as definiçõesEF do parser genérico, a situação temporal/normativa de complementos e a comparação da alternativaPA620 permanecem separados; nenhuma evidência daqui autoriza marcar UF/sourceReady integralmente. O pacote local não encontrou bloqueio de rede: não usou rede ou novo modelo e o PDF disponível abriu sem necessidade de OCR.
