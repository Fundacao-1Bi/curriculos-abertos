# Contraprova independente — Roraima, quadros de Educação Infantil

**PASS no recorte28–99**, para o candidato `rr-ei-organizers-age-v2-items.json`, SHA-256 `98992856b485be462bac63fdaaf071c8c375d7584f8a01cadab70bedcc60a206`. O PDF original634páginas tem SHA `e95761f67d1733660b9b9bd2acee10707ed07301249c322cbf39fd86a3453112`. Esta auditoria não altera o candidato, o manifesto, o pipeline, o banco ou a publicação, nem declara RR pronto.

## Fonte antes do candidato

O censo próprio foi produzido antes de abrir o candidato ou ler seu gerador. Seu hash congelado é `52e215f3e67ead3c6e2aba1da1c28e88a981312d745d8491b134301f4c9205d0`, registrado em `independent-denominator-pin.json`. Ele usa palavras nativas e os cabeçalhos físicos dos seis papéis: direitos, faixa etária, objetivo, experiências, abordagens e orientação. Códigos não determinam campo nem idade.

Foram encontrados15organizadores e109faixas horizontais definidas pela coluna de objetivos:90começam uma definição e19continuam unidades anteriores. A projeção dos seis papéis gera654regiões de comparação, **não654células físicas únicas**: existem células mescladas, pequenas fendas geométricas e continuações. Há90âncoras de definição,89códigos distintos,60células de experiências não vazias,109fragmentos de abordagens e90orientações não vazias. Direitos e faixa têm89ocorrências próprias não vazias; os vazios não viraram conteúdo inventado. O exemplo EI02TS01 da28 é referência documental, sem posição de aprendizagem.

O primeiro confronto mostrou uma diferença no meu censo, não no candidato: a borda de experiências é317,28na abertura34, mas310,28na continuação35. Herdar a largura do cabeçalho capturava o vocábulo “se” da coluna de abordagens também em experiências. Mantive o censo cego original byte a byte e gerei `independent-source-census-page-grid.json` usando as bordas locais de cada página e intervalos semiabertos de propriedade das palavras. Esse segundo script não importa nem lê o candidato. A correção e seu motivo permanecem explícitos; não se mudou o adapter para fazer o teste passar.

## Conferência integral e invariantes

`independent-verification.json` registra3595verificações e zero falhas. Cada definição foi associada à sua âncora física e ao organizador efetivamente declarado. Para cada objetivo, a união inteira de cada papel foi comparada com a fonte, preservando palavras, acentos, pontuação e hífens; apenas compatibilidade explícita de ligaturas nativas foi admitida. Experiência, abordagem e orientação não foram misturadas. A fragmentação106/212do parser do candidato não foi contada como novas unidades: as uniões se reconciliam com os90objetivos e90abordagens do denominador independente.

Todos os346registros e484fragmentos passaram no checker comum com a ordenação real de produção `get_text(sort=True)`, no loader, no finalizador e no JSON Schema. Texto, código, posições, pais e evidências permaneceram iguais após o finalizador. O pin de helper/schema/candidato não sofreu mutação durante a execução.

As345posições dos objetivos, experiências, abordagens, orientações e nós de campo/faixa foram confrontadas com letras, números e unidades das legendas físicas. Os limites0–18,19–47e48–71meses têm Evidence[]; não foram deduzidos de BEBÊS ou do código. A faixa vazia da segunda unidade na90 usa uma legenda real do mesmo organizador, com caixa e página verdadeiras. Direitos e demais provas secundárias também foram conferidos no **próprio bbox**, evitando o atalho de aceitar uma frase repetida em qualquer lugar da página.

O original `rr-ei-organizers-items.json` continua SHA `f8a5d668ced4ab21e2223d8fb4e73926968806d1c23142e4f220f63d681ace84`. Todos os campos de registro que existiam antes, exceto a ampliação autorizada de posição, permanecem iguais. O grupo etário antigo continha a legenda completa; em345posições essa legenda foi conservada em `age_label`, enquanto `age_group` passou ao nome do grupo. Todos os demais campos antigos de posição foram preservados. A quebra tipográfica da67 conserva as mesmas letras em `Crianç/as` e `pequen/as`; a imagem confirma o grupo e os números, e a legenda literal quebrada permanece disponível.

## Anomalias do documento e amostras visuais

Foram vistos os15inícios de organizador e25páginas completas, além do recorte de borda da35 e dos códigos78/95. As imagens ficam apenas em `var/private-evidence/source-audit-rr/independent-*`; hashes e regiões examinadas estão em `independent-visual-review.json`.

O original78 imprime `EI01ET01` no campo Corpo, Gestos e Movimentos, grupo de crianças pequenas. O original95 imprime `E103ET04`, com dígito1. Recortes próprios e trace de glifos confirmam ambos em `independent-code-anomalies.json`. Essas grafias são dados da fonte, não correções a fazer por memória da BNCC. Passar na fidelidade literal não estabelece equivalência nacional nem sana a inconsistência entre código, campo e faixa.

As continuações91/94/97/98 foram vistas e conferidas integralmente. Na97, a parte superior conclui uma abordagem; a parte inferior inicia EI03ET07, que continua na98. A continuação objetiva78→79 pertence a CG02. A62 foi examinada para confirmar que as subcélulas artificiais do parser não criam nem perdem objetivos.

## Controles negativos

`independent-negative-verification.json` bloqueia9corrupções controladas: correção editorial de E103ET04; idade e campo inferidos do código78; troca de pai com árvore internamente consistente; duplicação que conserva a contagem60; troca entre orientação e experiência; continuação truncada com texto/evidência alterados juntos; legenda promovida a definição mantendo código/contagem; e citação real na página com bbox apontando a célula vazia. O checker literal isolado aceita8desses casos, demonstrando por que a prova física e o denominador são necessários.

## Reprodução e limites

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-rr/independent-source-census.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rr/independent-source-census-page-grid.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rr/independent-verify.py
var/venv-pipeline/bin/python docs/evidence/source-audit-rr/independent-negative-check.py
```

O fecho e hashes estão em `independent-final-summary.json`; invariantes da versão em `independent-v2-invariants.json`. A validação é automatizada e não houve revisão pedagógica humana. O restante do documento, Ensino Fundamental, demais partes normativas e fontes de RR não são aceitos por este resultado. Não há bloqueio externo neste recorte; ele está pronto para o proprietário integrar e verificar na Source real.
