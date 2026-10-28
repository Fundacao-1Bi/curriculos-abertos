# Adaptador do Referencial Curricular Gaúcho – Ensino Médio

Requisitos atendidos nesta frente: ING-03, DAT-01, DAT-02, DAT-05 e ESC-02. Autoria e conferência técnica: `agent:rs_adapter`, ator **automatizado**. Não houve revisão pedagógica humana, homologação institucional, commit ou ação remota.

## Fonte e delimitação

O manifesto seleciona `rs-rcg-em`, documento oficial de 2021 com 287 páginas, SHA-256 `01478f372c7d4d77002c68877f1b6018535218d419b1efd5583cb739825daaf7`. O arquivo `rs-rcg-em-jul22`, indicado inicialmente na delegação, está registrado como apresentação alternativa excluída para evitar duplicação do mesmo referencial. A comparação de **todos os 122 fragmentos entregues** com as mesmas regiões do PDF de julho de 2022 encontrou 122 textos idênticos. Isso confirma somente esses fragmentos; não atribui equivalência normativa, vigência ou identidade integral das edições.

O adaptador complementa a extração compartilhada dos itens com códigos e das seções documentais. Não substitui o restante da extração do referencial e não declara a UF pronta isoladamente. Usa `pipeline.geometry` para normalização da página e leitura/recorte de palavras; o código específico resolve as diferenças reais deste documento: três colunas, células mescladas e listas H./H.E.

## Registros entregues

| Parte documental | Páginas PDF | Tipo | Quantidade |
| --- | --- | --- | ---: |
| Quadro 1, coluna Habilidades RS | 104–110 | `habilidade`, código nulo | 51 |
| Quadros 12–15, Objetivos | 265–268 | `objetivo_aprendizagem`, código nulo | 12 |
| Quadros 12–15, Habilidades | 265–268 | `habilidade`, código original H.1–H.12 / H.E.1–H.E.12 | 24 |
| Quadro 11, Saúde I | 223–240 | `unidade_curricular` | 11 |
| Quadro 11, Sugestões de Objetos do Conhecimento | 223–240 | `objeto_conhecimento`, uma lista por unidade com conteúdo | 10 |
| Quadros 12–15 | 265–268 | `eixo_estruturante` | 4 |
| Quadros 12–15 | 265–268 | `orientacao_metodologica` | 4 |
| Formação geral / Natureza / Itinerários / Saúde I / EPT | 91, 92, 204, 219, 241 | `secao_normativa` | 5 |
| **Total** | | | **121** |

As 51 habilidades locais estão distribuídas nas 26 linhas lógicas EM13CNT101–107, EM13CNT201–209 e EM13CNT301–310. O código da coluna BNCC **não** foi transferido ao campo `code` do objetivo local: permanece uma referência com sua caixa, trecho e página em `source_context.reference_evidence`, de escopo `same_logical_grid_row_not_equivalence`. As relações resultantes só podem expressar referência documentada, sem equivalência automática.

Os anos vêm da coluna explícita `Ano(s)`. Preservam-se rótulos como `1º e/ou 2º`, `1º e/ou 3º` e `1º, 2º e/ou 3º`, além dos anos estruturados. A atribuição considera a **linha lógica inteira**, inclusive continuações entre páginas: os dois últimos rótulos de CNT102 aparecem na página 104 enquanto os parágrafos correspondentes estão na 105; a habilidade local sob CNT106 continua da página 105 para a 106; o terceiro parágrafo sob CNT308 aparece na 110 e seu ano está na 109. Usar o ano mais próximo na mesma página causaria perda ou troca.

No modelo Saúde I, `2/CNT` e `3/MAT` pertencem a `Horas Aula/Área`: **não são séries escolares**. Permanecem no contexto original e os anos são nulos. A unidade `BIO TECNOLOGIAS` possui célula vazia na coluna de sugestões; a hierarquia foi mantida e nenhum conteúdo foi criado para preencher o vazio. Os títulos dos componentes são verticalmente centralizados; as fronteiras vêm das células físicas, nunca da altura do título.

Os quatro textos de Foco Pedagógico/Pressupostos Metodológicos e as dez listas de conteúdo têm tipos próprios. Não são contabilizados como objetivos ou habilidades. A numeração H./H.E. permanece original e escopada ao documento, sem conversão em EMIF.

Cada registro tem ID estável, hierarquia por `key`/`parent_key`, posição, código quando efetivamente presente, trecho literal e região de cada fragmento. Quebras de linha são normalizadas; grafia e pontuação da extração nativa permanecem preservadas. `printed_page` só é preenchida quando o número foi lido no cabeçalho: as aberturas das partes nas páginas 91 e 241 não imprimem número e recebem nulo.

## Execução reproduzível

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/rs-em-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/rs-em-verify.py
```

Runtime executado: Python 3.11 com PyMuPDF 1.26.7, no ambiente local `var/venv-pipeline`. Os PDFs originais não são modificados. Saída: `data/manifests/uncoded/rs-em-items.json`, objeto com `source_id`, hash da fonte e `items`. A frente `data_central_south` integrou `uncoded_items_path` no manifesto da fonte; a referência foi conferida após a alteração.

## Evidências e limites

O verificador constrói o denominador **antes de ler o sidecar**: varre as 287 páginas, consulta a lista documental dos 15 quadros, conta rótulos da coluna Ano(s), identifica os 11 componentes na primeira coluna do Quadro 11 e conta os marcadores de objetivo e os códigos H./H.E. nos quatro quadros finais. Não importa nem invoca o algoritmo de extração.

Resultados executados: 51/51 habilidades locais; 26/26 linhas de referência; 11/11 unidades; 12/12 objetivos; 24/24 códigos originais; 122/122 fragmentos literais; 121/121 registros aceitos pelo carregador real `source_uncoded_items`. A comparação por coordenadas de **todas as 4.095 palavras em 37 regiões** das colunas locais 104–110, das colunas de objetos 223–240 e das três regiões curriculares dos quatro quadros EPT não encontrou perda, inclusão externa nem duplicação. IDs e referências de hierarquia são únicos/resolvidos. Reexecução com a mesma fonte produz bytes e IDs idênticos.

Foram renderizadas e inspecionadas visualmente por agente as 15 páginas 104–110, 223, 224, 234, 235 e 265–268. Isso cobre todos os quadros com objetivos sem código, a quebra de linha lógica, o cabeçalho horas-aula e a célula vazia. A inspeção visual é amostral quanto às demais unidades Saúde I; a contabilidade de palavras é integral nas 18 páginas desse quadro.

Evidências locais em `docs/evidence/source-audit-rs-em/`:

- `rs-em-independent-denominator.json`: inventário independente e âncoras documentais.
- `rs-em-layout-inventory.json` e `rs-em-fragments.json`: linhas lógicas, colunas, unidades, regiões e continuações.
- `rs-em-verification.json` e `rs-em-literal-checks.json`: resultados determinísticos e exercício do carregador compartilhado.
- `rs-em-alternate-comparison.json`: comparação dos fragmentos com julho de 2022.
- `rs-em-idempotence.json`: hashes e igualdade dos IDs na reexecução.
- `rs-em-visual-samples.json` e imagens `rs-em-p*.png`: seleção, tipo real de revisor e achados visuais.
- `rs-em-extraction-report.json`: contagens e hash da saída atual.

Publicação nacional, carregamento no banco, consulta em API/MCP e reconciliação dos demais itens codificados pertencem à integração geral e não são atestados apenas por este relatório. Nenhuma ausência de conteúdo em uma célula foi interpretada como ausência pedagógica da UF.
