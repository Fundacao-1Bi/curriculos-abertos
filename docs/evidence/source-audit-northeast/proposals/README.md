# Propostas NE de geometria — 28/10/2026

Autor automatizado: `codex:data_northeast`. Nenhum PDF original foi modificado. As propostas foram promovidas para o módulo `pipeline/ne_geometry.py`, com guardas de hash para os adaptadores BA/SE; a integração no núcleo pertence à frente pipeline.

- CE EM: varredura411p/103p com códigos,187 células físicas contendo somente códigos e delimitadores. Elas são menções de referência sem redação própria naquele local. A recuperação antiga ignorava o fim da célula e tomava prosa de linhas posteriores. `cell_recovery_is_reference` limita a classificação ao próprio bbox. O placeholder EI no fim de tabela de objetivos exige exceção explícita e não se aplica aos casos CE.
- PE EM: varredura709p/496p com códigos,14 células com28 prefixos literais conjuntos em10páginas. `joint_prefix` preserva uma redação por célula e todos os identificadores em `source_context.joint_source_codes`; não os declara equivalentes à BNCC nem os transforma em28 aprendizagens distintas. A leitura/continuação multipágina permanece responsabilidade do núcleo.
- BA EI/EF: varredura482p/249p com códigos,243 páginas com borda direita aberta dedutível dos finais repetidos das linhas reais. O detector anterior fechava só as três colunas à esquerda, omitindo a quarta de habilidades. A linha de extração adicionada é registrada como intervenção, sem alterar o documento. Recuperadas2161 células codificadas adicionais e os9 pontos independentes BA da amostra,9/9. Isso não é inventário semântico completo da fonte.
- SE EM: varredura571p/174p com códigos,21 páginas com título explícito de habilidades IFA e grade final em retângulos alinhados. O detector antigo tomava desenhos decorativos ocultos por bordas e criava60 colunas na p327. O adaptador usa retângulos finais compostos e preenchimentos simples com as mesmas bordas de coluna.109 células codificadas;107 passes literais nativos,2 divergências de ordem de ligadura na p235 entregues à frente MA. A geometria p327 de EMIFCG04 foi corrigida no teste isolado.

Reprodução:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-northeast/verify-ne-proposals.py
var/venv-pipeline/bin/python docs/evidence/source-audit-northeast/verify-ba-open-edge.py
var/venv-pipeline/bin/python docs/evidence/source-audit-northeast/verify-multipage-anchors.py
```

`geometry-scan.json` e `ba-open-edge-scan.json` derivam caixas e prefixos diretamente dos PDFs, não dos IDs extraídos. Os9 pontos BA vêm do quadro independente prévio. Nenhuma dessas provas conclui uma UF, revisão pedagógica ou integralidade normativa. Os4 casos multipágina da amostra passaram nos8 fragmentos originais, com concatenação e páginas consecutivas; a prova está em `../multipage-anchor-verification.json`.

Probes após integração no núcleo:27/27 checks passaram nas23 páginas selecionadas (CE3,PE14,SE1,BA9), sem escrita de caches integrais. `integrated-core-probes.json` registra os textos/caixas/identificadores observados; a etapa seguinte é reprocessar as fontes completas após congelar o leitor de glifos e o fingerprint do algoritmo.

Verificação adicional do leitor de clusters MA em SE:105/109 células coincidem com a leitura nativa recortada;4 diferenças são i/l espúrios anexados por `get_text(clip)`, ausentes nos4 recortes de fonte visualmente conferidos. As duas ordens de ligadura da p235 ficam corretas. A comparação independente com `get_texttrace` sem controle de visibilidade passa apenas21/109: o trace inclui texto oculto/clipped do template, então essa comparação foi preservada como limitação e não apresentada como aprovação integral. `se-glyph-trace-verification.json` mantém todas as duas leituras e disposições.
