# Revisão independente do adaptador de competências ES EF

Revisão automatizada, somente leitura de fontes, inventários e código. Nenhum sidecar, manifesto, PDF, cache ou pipeline foi alterado.

Os quatro casos solicitados foram confrontados com o PDF original, glifos nativos, glifos de renderização e recortes efetivamente vistos em memória, sem persistir imagens:

| Código literal | Volume | PDF/impresso | Resultado |
|---|---:|---:|---|
| CElI01 |08|251|grafia original; coluna de competências|
| CIEF03 |06|93|grafia original; coluna de competências|
| LPEFO9 |05|103|letra O preservada; coluna de competências|
| CIEF04 |02|83|grafia original; coluna de competências|

CIEF03 e CIEF04 não estão nos volumes inicialmente sugeridos05 e09. Todos os quatro identificadores e textos integrais delimitados passaram native/trace com comparação limitada a whitespace. O código separado deve conservar exatamente a grafia impressa; não há fundamento documental para corrigi-lo ou atribuir equivalência BNCC. Os textos observados são competências de aprendizagem, não trechos de metodologia docente. A parte metodológica acima do quadro de Inglês p246 permanece fora da seleção por campo físico.

Uma busca lexical mais ampla nos campos originais de competência/descrição dos oito inventários encontrou4.591 linhas com identificadores alfanuméricos iniciais. Nenhum token ficou fora da expressão atual. Isso é um confronto independente do alfabeto e não substitui o denominador por âncoras de glifos: o censo do responsável registrava4.603 âncoras no checkpoint revisado. Foram preservadas também grafias como CEF03, CE1 e LPEF010, sem padronização corretiva.

Achados:

1. **Denominador estrutural:** o primeiro código revisado derivava IDs esperados de nós a partir dos outputs. A correção já foi constatada: `census_structure.py` utiliza inventário físico/censo de campos, e `verify` lê `structural-denominator.json`. O novo denominador deve continuar vinculado ao hash do censo efetivamente utilizado.
2. **Conflito de legenda na continuação:** vol08 p246 imprime “Competências Específicas de Artes”, embora o capítulo e a página seguinte comprovem Língua Inglesa. A p247 contém CELI02–06 no mesmo quadro continuado. Ambas foram vistas. O responsável reconheceu e está preservando prova da legenda p246, contexto de capítulo/banner e conflito nas duas páginas; escolheu `component:null` conservador, sem apagar o capítulo comprovado. Revalidar os outputs finais após essa alteração.

Não foram encontrados títulos de capítulo abaixo das âncoras na própria página sendo utilizados como contexto. Os anos permanecem nulos; o identificador não determina seriação. A separação entre código/descrição introdutórios e marcadores inline é adequada: o texto inline conserva o marcador; o código tem prova separada `code_locator`. Textos nacionais EF contidos no campo são contexto/referência, sem promoção automática a competência nova.

Provas detalhadas, caixas, excertos, hashes das fontes/scripts e hash dos recortes em memória constam em `ce-review-report.json`. Pendente: execução integral e aceite do novo output pelo importador/finalizador do responsável. Esta revisão não afirma aceite de outputs ainda não examinados, revisão humana ou prontidão da UF.
