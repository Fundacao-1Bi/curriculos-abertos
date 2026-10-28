# Goiás — auditoria e adaptador documental do Ensino Médio

Auditoria integral executada sobre o PDF oficial `go-dcgoem-portal-atual`, de 1.397 páginas. O passe produziu inventários independentes, provas de decodificação tipográfica, OCR das páginas raster e um adaptador das colunas de aprendizagem sem código. Revisão automatizada explícita; não houve revisão pedagógica humana. A fonte e a UF continuam com reconciliação pendente.

SHA-256 do PDF: `2b350b8a53e5072ba915489c749f55b91284f4d23531a08faf5ea7fed89ae1a9`. Edição consultada: 2021. Upload em 2025 não foi convertido em edição nova. O alternativo `go-dcgoem-2021` tem outro hash binário, mas texto integral normalizado idêntico conforme conferência do responsável da fonte; não foi duplicado como outra parte curricular.

## Executado sobre o conjunto

`docs/evidence/source-audit-go-em/` contém o inventário das 1.397 páginas, 790 tabelas nativas em 789 páginas, 89 entradas do sumário e os 20 quadros listados pelo documento. Foram localizadas 1.454 ocorrências de códigos, com 923 valores distintos: 597 locais GO, 120 de Projeto de Vida, 575 EMIF e 162 referências nacionais/outras. Menções repetidas, exemplos e referências não são denominador de habilidades completas.

As partes físicas foram conferidas pela abertura efetiva, sem recortar pelo número incorreto do sumário:

| Parte | Páginas físicas | Tabelas nativas |
|---|---:|---:|
| Elementos iniciais e texto introdutório | 1–140 | 8 |
| Formação Geral Básica | 141–496 | 248 |
| Itinerários Formativos | 497–1302 | 528 |
| Referências DC-GOEM | 1303–1390 | 0 |
| Anexos | 1391–1397 | 6 |

O sumário indica Referências em 1299, porém a abertura real é 1303. Há deslocamentos variáveis: Administração abre em 692; Linguagens em 740; Matemática em 799; Ciências da Natureza em 899; Ciências Humanas em 1002; Integrados em 1051. Cinesfera abre em 1099, Comer Bem em 1129, Incertezas em 1177, Matematicidades em 1234 e Mama Gaia em 1274. `page-inventory.json` preserva cabeçalhos, texto inicial/final, geometria e hashes de cada página.

## Fontes Type3 e códigos originais

Foram inventariadas todas as ocorrências de sete controles provenientes de fontes Type3 sem ToUnicode. Todos os 28 pares observados de font/xref/controle tiveram prova visual automatizada e métricas do charproc. `font-glyph-decoding-proposal.json`, `glyph-visual-samples.json` e `font-charproc-metrics.json` registram as provas. O responsável da fonte aplicou os mapas apenas ao artefato exato:

| Controle | Glyph exibido | Ocorrências |
|---|---|---:|
| U+001C | fi | 4.822 |
| U+001D | fl | 613 |
| U+001B | ff | 7 |
| U+0010 / U+0011 | “ / ” | 330 / 331 |
| U+0015 | – | 1 |
| U+0001 | ´ | 2 |

U+0001 é acento agudo isolado em `TIC´s`, não apóstrofo. U+0015 é o traço exibido em um URL; o adaptador não o transforma em hífen ASCII para tentar consertar o endereço. Original e SHA do PDF permanecem intactos.

O uso de `table.extract()`, `get_text('words')` ou `get_text('text', sort=True)` elimina essas ligaduras antes da substituição, gerando exemplos errados como `Identi car` e `Per l`. A solução usa o texto nativo **sem sort**, recortado pela caixa da célula, aplica os mapas documentados e só então normaliza quebras de linha. Essa correção sistemática foi repassada ao pipeline central, inclusive ao verificador de evidências.

Os prefixos/sufixos locais são preservados. `GO-EMLGG101A` não vira `EM13LGG101` por aritmética. Códigos quebrados como `GO-` + nova linha + `EMMAT103B` conservam o prefixo. Há grafias reais que não podem ser corrigidas silenciosamente: `GO-EMLP26-B`, `GO-EMLP31-A`, `GO-EMLP31-B`, `GO-EMCH605D`, `EMIFCHSO2` e variantes `GO EMCHS102B` e `GO EMCHS202D` sem hífen. As cinco primeiras têm recortes visuais em `code-anomalies-visual.json`; as duas últimas têm recortes visuais nas páginas 465/471 e foram encaminhadas ao parser.

## OCR e orientação

As 36 páginas com menos de 30 caracteres nativos foram classificadas integralmente: 6 títulos nativos completos, 5 páginas em branco contendo apenas rodapé, 5 diagramas curriculares EPT, 18 páginas de rubricas em imagem, capa e prosa introdutória ilustrada (página 29).

OCR português real foi executado nas 25 páginas raster: **5.774 palavras**. A segunda execução reutilizou os mesmos 25 caches. Engine, modelo, versões, geometria, hashes, palavras, confiança e avisos estão nos arquivos `ocr-p*.json` e `short-pages-ocr-audit.json`. Baixa confiança permanece explícita. As 18 rubricas reutilizam duas imagens exatamente iguais, nove vezes cada, com rodapés próprios; não foram tratadas como páginas vazias ou como códigos novos.

A auditoria encontrou um erro de orientação: um rodapé de quatro caracteres fazia o normalizador girar o corpo de diagramas e páginas em branco. As imagens original/normalizada documentam o problema. O responsável pelo pipeline adicionou o mínimo de 128 caracteres para rotação por direção nativa. O inventário final registra 607 páginas com rotação original zero e 790 com rotação declarada de 90°, sem rotação indevida adicional. Todos os cinco diagramas foram inspecionados na orientação corrigida.

## Adaptador sem códigos executado

`data/manifests/uncoded/go-em-uncoded-items.json` contém **443 registros**:

- 281 habilidades EPT: 50 de Informática, 151 de Química e 80 de Administração;
- 92 objetivos locais IF: 25 de Energia, 24 de Micromundo, 19 de Comer Bem e 24 de Incertezas;
- 63 unidades curriculares, 3 cursos técnicos e 4 itinerários como nós de hierarquia.

O inventário independente identificou **382 fragmentos físicos** nas colunas Habilidade EPT e Objetivo(s) de Aprendizagem. A grafia fonte `Objetivos de apredizagem` foi reconhecida explicitamente e preservada no contexto. Nove continuações foram unidas, incluindo a sequência 984–986, em que o texto do objetivo continua enquanto a referência EMIF de outra coluna muda. As nove ligações foram conferidas visualmente, além da conferência determinística de todos os 382 fragmentos. Os 443 registros têm 452 evidências, caixas, páginas impressas, texto fonte e hierarquia resolvida. Os rodapés literais das 206 páginas distintas de evidência foram verificados nas margens do PDF (`printed-page-verification.json`). Objetos de conhecimento, práticas e referências paralelas permanecem em `source_context`; não entram no texto da aprendizagem local.

Os cinco diagramas EPT têm nove grupos de série e 64 menções a unidades. As posições de ano foram atribuídas somente quando o nome literal da unidade coincide com o diagrama conferido: 286 registros, dos quais 244 aprendizagens, recebem 305 ocorrências de posição explícita. Divergências de redação entre diagrama e título, eletivas e unidades não localizadas permanecem com ano desconhecido. Os códigos `EM1PV`/`EM2PV`/`EM3PV` não foram usados para presumir série; as tabelas de Projeto de Vida identificam módulos e competências, sem legenda de série nesses cabeçalhos.

Repetição integral produziu bytes idênticos. SHA-256 final do sidecar: `dbc441a6e756f0e31c9010ec83fe37d7c472616f3565324b70fc954729144135`. `idempotency-verification.json` comprova a igualdade. `adapter-summary.json`, `adapter-cell-verification.json`, `explicit-position-inventory.json` e `visual-verification.json` delimitam o que foi efetivamente conferido.

## Confronto com extração central e limites

A primeira versão 1.4 observada tinha 1.279 itens codificados, zero dos 120 objetivos PV, prefixos GO danificados e configuração anterior aos mapas de glyph. O confronto integral identificou 208 ocorrências ainda não representadas e 33 itens com código extra/prefixo danificado. O confronto literal estrito com texto nativo decodificado encontrou 853 achados em 1.281 fragmentos; o diagnóstico anterior baseado em texto ordenado havia subestimado a perda de ligaduras. Esses números são evidência de falha do cache anterior, não avaliação da versão corrigida. Os arquivos `baseline-*` preservam o primeiro diagnóstico; `extraction-comparison-summary.json` identifica hash/configuração/data do cache efetivamente confrontado.

O importador real central (`source_uncoded_items` e `finalize_items`) passou com 443 itens/IDs únicos, 436 vínculos e nenhum pai ausente. Todas as 452 evidências foram aceitas; `pipeline-import-verification.json` registra o hash do código central e do sidecar. O teste usou caminho do sidecar em uma cópia da fonte em memória, sem alterar o manifesto. Não há supressão de códigos genéricos: este adaptador contém apenas aprendizados sem código e seus nós.

Um reprocessamento real posterior, com fonte já vinculada ao sidecar, leu novamente as 1.397 páginas: 1.454 itens codificados, 624 tabelas, 24 páginas OCR utilizadas pelo pipeline e `ocr_pending=false`. A capa, coberta pelo OCR separado da auditoria, não dispara a regra de área raster central. Os 120 objetivos PV foram recuperados e os controles residuais no texto ficaram em zero. A configuração atual é `5efc1390dc3146e2ff5ef59acc75033e46e6777593fd1dabfecf88f3dc2cb79e`.

O novo confronto estrito verificou 1.458 fragmentos codificados: 1.374 passaram e 84 produziram achados, todos provenientes de `ruled-column-continuation-recovery`. A causa restante foi identificada: códigos locais adicionais entre parênteses no mesmo parágrafo são rejeitados pelo segmentador de células; a recuperação por x da palavra recorta textos em colunas inexistentes. Há também 33 prefixos GO ainda danificados (31 quebras após `GO-` e duas variantes com espaço). `go-inline-prefix-proposal.patch` e seu teste em memória documentam uma correção restrita para revisão do responsável pelo pipeline. O teste integral das tabelas FGB recuperou as 597 âncoras locais independentes com 597 registros, nenhum ausente/extra e nenhuma falha literal; o responsável inspecionou e aplicou o hunk de segmentação inline e uma gramática de prefixo restrita às UFs. Reprocessamento forçado posterior está sendo verificado, sem reaproveitar o cache do parser anterior.

Após a primeira correção inline aplicada, o reprocessamento forçado passou a representar todas as âncoras fonte: zero ausências. O passo de recuperação, porém, reintroduziu 33 códigos sem prefixo como duplicatas, elevando o cache a 1.487 itens codificados; 25 de 1.491 fragmentos ainda falharam no confronto literal. Foram isoladas mais seis células EMIF, visualmente confirmadas como definições adicionais na mesma coluna Habilidade/Habilidades, e a comparação da recuperação que não reconhecia o prefixo GO quebrado.

`go-emif-recovery-position-proposal.patch` resolve esses pontos e corrige LP como componente, com Linguagens como área. O teste da proposta em memória passou nas seis células EMIF e em todas as 31 páginas afetadas pelos 33 códigos duplicados, sem produzir nova recuperação duplicada; a posição LP ficou correta e sem série inferida. `emif-recovery-position-proposal-summary.json` registra o resultado. Esse segundo patch está sob responsabilidade do proprietário do pipeline; ainda não foi apresentado como aplicado em produção nesta fotografia.

A prontidão da fonte exige integrar e reprocessar sistematicamente essa última correção, repetir o confronto dos códigos/textos e reconciliar as partes completas, incluindo competências e contextos normativos sem código. O adaptador não fabrica uma lista de todos os IDs extraídos para declarar completude nacional. Nenhum bloqueio externo de acesso foi identificado nesta fonte; eventual processamento/importação central pendente é trabalho interno da integração e está explicitado nos arquivos de verificação.

## Comandos reproduzíveis

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-go-em/go-em-independent-audit.py --tables
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python docs/evidence/source-audit-go-em/go-em-ocr-audit.py
var/venv-pipeline/bin/python docs/evidence/source-audit-go-em/go-em-uncoded-cell-inventory.py
var/venv-pipeline/bin/python data/manifests/uncoded/go-em-extract-uncoded.py
var/venv-pipeline/bin/python docs/evidence/source-audit-go-em/go-em-extraction-compare.py
var/venv-pipeline/bin/python docs/evidence/source-audit-go-em/go-em-validate-adapter.py
# Após o responsável aplicar correções no parser: force invalida cache da mesma configuração.
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python docs/evidence/source-audit-go-em/go-em-reprocess.py --force
```

Runtime executado: Python 3.11.15 e PyMuPDF 1.26.7 em `var/venv-pipeline`. Os scripts preservam o PDF original e não modificam o manifesto central unilateralmente. O portal estável permaneceu intocado nesta frente. Nenhum commit foi criado pelo subagente.
