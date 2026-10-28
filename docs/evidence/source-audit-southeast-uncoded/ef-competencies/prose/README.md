# ES EF: competências gerais e objetivos curriculares em figuras sem identificador

Implementado, executado e verificado localmente, com ator `automated`. Os PDFs originais, manifesto, caches de produção e pipeline foram usados somente para leitura.

O censo nativo independente percorreu as 1.956 páginas dos oito volumes EF02–09 antes da geração dos registros. Guardou texto, cabeçalhos, caixas, fontes e candidatos numerados por página (`inventory-<sourcehash>.json`). O inventário físico posterior (`physical-prose-inventory.json`) contou as linhas/cartões e fixou IDs esperados antes da extração. Não há denominador derivado dos outputs.

| Parte física | Ocorrências preservadas | Tipo do registro |
|---|---:|---|
| Figura3, p27 de cada um dos8 volumes;10 linhas ×3 colunas |80|`competencia`|
| Figura25, vol03 p195 e vol07 p251;4 cartões em cada|8|`objetivo_curricular`|
| Legendas originais das10 figuras|10|`secao_normativa`|
| Total|98| |

As figuras gerais não imprimem códigos nem números oficiais1–10. Cada competência conserva os três fragmentos correspondentes a Dimensão/O que?/Para que?; `source_order` é apenas ordem física e `code` é nulo. Não são fabricados CG01, CE01 ou equivalências BNCC. A figura do volume05 tem cabeçalhos fora da malha: são10 linhas de dados, enquanto as outras sete malhas incluem uma linha de cabeçalho. O adaptador preserva ambas as geometrias documentadas.

Os quatro cartões de Ensino Religioso são intitulados pela fonte “Objetivos do Componente Curricular Ensino Religioso a partir da BNCC”. São objetivos/finalidades curriculares explícitos, sem convertê-los automaticamente em habilidades ou competências de estudantes. Foram preservados com tipo distinto e enquadramento original.

Posições registram somente EF comprovado pela capa do volume e, nos cartões, Ensino Religioso comprovado pelo cabeçalho da própria página. Não se deduz série/ano pela sigla, área do volume ou adjacência. As hierarquias são as dez legendas reais das figuras, com chaves técnicas e pais resolvidos.

Tabelas introdutórias e colunas com identificadores alfanuméricos de competência (CE, CEAR, CELI, LPEF e outros literais) pertencem ao adaptador do agente pai e não são duplicadas neste sidecar. Menções narrativas às dez competências não geram listas artificiais. P26 traz a definição contextual; p35–37, Matriz de Saberes/Delors; os candidatos “10.” em p55 pertencem a referências; a lista de espaços culturais do vol04 p132 é contexto de ensino de Arte. `census-closure.json` registra os candidatos e o fechamento; não restaram candidatos numerados sem classificação nem páginas com grande imagem e texto nativo insuficiente segundo a triagem documentada.

A verificação real chamou `ingest.source_uncoded_items` e `ingest.finalize_items` com extratos construídos em RAM a partir do censo independente. Foram98/98 IDs, zero faltas/extras, todos os pais resolvidos e identidade exata de texto/código/tipo/posições após finalização. Todos os258 fragmentos canônicos e36 fragmentos de metadados foram confrontados com glifos nativos e o fluxo de renderização do PDF, sem normalização além de whitespace; zero falhas. O relatório registra hashes das fontes e fingerprint do parser. Reexecutar a extração produziu bytes idênticos.

As dez figuras foram renderizadas e vistas pelo agente (`visual-review.json`), cobrindo todos os volumes e os dois tipos documentais. Imagens permanecem apenas em `var/private-evidence/es-ef-competencies-prose/`. Isso é revisão automatizada; revisão humana não foi realizada. O censo completo é nativo/geométrico e não uma revisão visual humana das1.956 páginas.

Comandos reproduzíveis, a partir da raiz:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-uncoded/ef-competencies/prose/inventory.py
var/venv-pipeline/bin/python data/manifests/uncoded/es-ef-competencies-prose-extract.py inventory
var/venv-pipeline/bin/python data/manifests/uncoded/es-ef-competencies-prose-extract.py extract
var/venv-pipeline/bin/python data/manifests/uncoded/es-ef-competencies-prose-extract.py verify
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-uncoded/ef-competencies/prose/census-check.py
```

Entregável: `data/manifests/uncoded/es-ef-competencies-prose-items.json`, SHA256 `fa99f01571389a5efdfdc68836f8f1c3c71736ace534a62698b6356bae8990e6`.

Pendente: o agente pai deve consolidar estes98 registros com as competências identificadas e respectivas ocorrências de colunas antes de propor o único `uncoded_items_path` de cada fonte. O caminho deste sidecar foi usado apenas no fixture de verificação em RAM; não substituir o manifesto diretamente e omitir a frente identificada. Nenhuma revisão humana, prontidão da UF ou publicação é declarada.
