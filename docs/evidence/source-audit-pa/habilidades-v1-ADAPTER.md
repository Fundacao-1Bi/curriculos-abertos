# Pará EF — reconciliação da coluna Habilidades

Incremento versionado para `pa-dcepa-ei-ef`, páginas físicas 112–323 da edição 2019. Fonte imutável: 361 páginas, SHA256 `6b101a029e7fc40b10feb79969309251337eb01fc2491c9e0b38563094fa8ec5`.

O pacote anterior de 1.972 registros não foi reescrito. Seu arquivo `data/manifests/uncoded/pa-dcepa-items.json` continua com SHA256 `946e4f16523b127bbbf35e15947655bd52a6d890920cc3e7cce49753b35c424b`, e seus 1.972 valores aparecem como prefixo idêntico no agregado novo.

| Artefato novo | Registros | SHA256 |
|---|---:|---|
| `data/manifests/uncoded/pa-dcepa-habilidades-v1-items.json` |2055 habilidades próprias|`2ecc8449b8723bbc56264aa3eda770f8924bea778e79e2a9cbe762e6d06667ca`|
| `data/manifests/uncoded/pa-dcepa-habilidades-v1-combined-items.json` |4027 totais|`7294cebd0c8cd3008c7f9498312cd66268843aeabcbd94c4a158651cd7de9ed6`|

## Denominador primário antes do cache

As 2.117 células não vazias da coluna física Habilidades contêm 2.055 ocorrências de definições codificadas, com 1.543 códigos literais distintos. São 64 quadros de 10 componentes. O censo foi contado em separado por marcadores no texto de célula e por tokens nativos do PDF, com multiconjuntos idênticos. Nenhum output genérico foi usado como quantidade esperada.

Há 68 células sem código no topo de páginas: todas continuam o parágrafo codificado anterior, dentro do mesmo quadro físico. Não foram encontradas habilidades autônomas sem código nessa coluna e nesse recorte. Seis células contêm duas definições:122,213,214,215,216 e310. Todas são particionadas pelo token literal de código; caixas por linha isolam o caso inline da122.

| Componente declarado no cabeçalho | Ocorrências |
|---|---:|
| Língua Portuguesa |787|
| Educação Física |119|
| Arte |79|
| Língua Inglesa |129|
| História |162|
| Geografia |123|
| Estudos Amazônicos |108|
| Ciências |147|
| Matemática |264|
| Ensino Religioso |137|
| Total |2055|

1543 códigos distintos não equivalem a2055 habilidades nacionais únicas. As ocorrências repetidas em quadros/linhas diferentes permanecem separadas, com código e redação próprios da fonte. Nenhum código, sufixo, texto nacional, equivalência ou edição foi inventado.

## Confronto com o snapshot genérico

Depois de fixar o denominador, foi lido o cache existente `page-cell-v1.5.0`, com checksum e fingerprint do parser conferidos. Seu configSHA não coincide com a Source atual; portanto, o relatório o identifica como snapshot observado, não como extração recém-executada da configuração vigente.

O snapshot contém2054 itens codificadosEF no recorte, uma ocorrência a menos, nove diferenças literais e1173 diferenças de componente/anos em relação aos cabeçalhos físicos. A comparação confronta código, página e âncora geométrica, evitando confundir duas ocorrências idênticas na mesma página.

- Na122, `EF04LP27` aparece duas vezes: uma ocorrência inline na célula de `EF04LP26` e outra na linha seguinte. O genérico conserva a linha própria, mas mistura a ocorrência inline ao texto de `EF04LP26`. O incremento conserva ambas como ocorrências documentais separadas, sem inferir intenção editorial.
- Três continuaçõesLP estavam truncadas no snapshot: `EF67LP08`134→135, `EF69LP50`135→136 e `EF69LP23`154→155.
- Três definições iniciais de Estudos Amazônicos264 estavam truncadas: `EF06GE01`, `EF06GE02` e `EF06EA01PA`.
- `(_ed)`225 perde o underscore no genérico; o símbolo original foi confirmado em crop4x e trace de glifo pretoU+005F. O hífen original após `EF06HI01`244 também foi mantido.
- Os anos/blocos vêm exclusivamente do quadro local. Por exemplo, `EF01LP04` está no quadro1º–3º, e as letrasGE/HI não mudam o componente local Estudos Amazônicos para Geografia/História.

O censo adicional de escopo percorreu todos os tokens de código das páginas 112–323: os 2.055 estão dentro das células primárias da coluna Habilidades; nenhuma ocorrência de código EF ficou fora desse inventário (`habilidades-v1-scope-code-census.json`).

A coluna Habilidades possui definições válidas próprias. O fato de seus códigos aparecerem como referências nos objetivos locais da coluna anterior não autoriza reclassificá-las como `referencia_no_documento`.

## Implementação e provas

O incremento tem2055 registros `kind:habilidade`, com texto nativo completo, código literal, evidência localizada, quadro/ano/componentes explícitos e vínculos documentais com os objetivos locais por célula. O pai estrutural é o quadro físico já presente entre os1972 registros congelados. Associações a objetivos locais são mantidas como contexto, sem equivalência semântica presumida.

- 2141/2141 fragmentos relidos do PDF original,66088 palavras conferidas.
- 2117/2117 células de Habilidades particionadas integralmente, sem perda/duplicação de palavras.
- 2055 ocorrências de código e68 continuações reconciliadas com o censo primário.
- Carregador real:4027/4027 registros, zero erros.
- Finalizador e hierarquia reais:4027 registros; as2055 habilidades mantêm tipo, texto, código e posições.
- SchemaLearning atual:4027/4027 válidos.
- Prova de autoridade disjunta em memória:2147 itens genéricos codificados do snapshot fornecidos junto ao agregado; zero duplicações genéricas restantes nas faixas revistas e4027 registros finais.
- Fronteiras verificadas:73/88 e112/323 cobertas;72,89,111 e324 não cobertas.
- 13/13 controles positivos/negativos passaram: perda de ocorrência repetida, concatenação de códigos, retângulo contaminado, continuação perdida, remoção de pontuação/sufixo, posição por código, rebaixamento indevido para referência, alteração do prefixo1972 e supressão ampla de intervalo não revisto.
- Fingerprint de pipeline/runtime/contrato/schema estável durante as provas.
- Sete páginas novas renderizadas e vistas(122,134,135,154,225,244,310), um crop de glifo e13 páginas visuais anteriores reutilizadas do mesmo PDF/checksum, cobrindo todos os dez componentes. A prova visual é amostral; a partição de palavras/células é integral.
- Reexecução completa: bytes idênticos dos dois sidecars novos e PDF/base1972 inalterados.

Evidências principais: `habilidades-primary-denominator.json`, `habilidades-primary-definition-stream.json`, `habilidades-generic-comparison.json`, `habilidades-v1-all-gates.json`, `habilidades-v1-negative-controls.json`, `habilidades-v1-visual-review.json` e `habilidades-v1-reproducibility.json`.

Comandos:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-pa/habilidades-source-census.py
var/venv-pipeline/bin/python docs/evidence/source-audit-pa/habilidades-compare-generic.py
var/venv-pipeline/bin/python data/manifests/uncoded/pa-dcepa-habilidades-v1-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/pa-dcepa-habilidades-v1-verify.py
var/venv-pipeline/bin/python data/manifests/uncoded/pa-dcepa-habilidades-v1-negative-controls.py
```

## Vinculação proposta e limites

`habilidades-v1-source-binding-proposal.json` propõe ao proprietário do manifesto a troca do caminho para o agregado4027 e autoridade explícita em duas faixas disjuntas:73–88(códigosEI já cobertos) e112–323(definiçõesEF deste incremento). O campo atual suportado pelo core é `coded_learning_ranges`, complementando `coded_learning_pages`. Não usar um único intervalo73–323, nem `generic_coded_reference_pages` para esta coluna.

Este agente não alterou Source/manifesto, core, bundle, banco ou publicação. A revisão pedagógica humana não foi realizada. Esta prova fecha o inventário estruturado dessa coluna no arquivo2019; a reconciliação normativa global, complementos posteriores, vigência atual, alternativaPA620 e aceitação integral da UF continuam separados.
