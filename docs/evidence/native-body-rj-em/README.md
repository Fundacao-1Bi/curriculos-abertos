# RJ EM — recuperação técnica de corpos nativos

Ator automatizado, revisão técnica. Nenhuma aprovação humana, alteração do currículo oficial, reconciliação SourceWhole ou prontidão de UF é declarada.

## Entrega e escopo

Source `rj-em-curriculo-referencial`, PDF original de 337 páginas, SHA256 `d5b0700da3a2ef3ca10ab46ec4e69691968f1b00b377ce7d12e8d83683fd38b8`. O censo nativo independente percorreu todas as páginas e encontrou **890 ocorrências de identificadores EM em 238 páginas**. O escopo é o corpo dos parágrafos codificados, não os capítulos, competências, objetos de conhecimento, anexos sem código ou a totalidade documental da Source.

O candidato contém 884 parágrafos explicitamente rotulados como habilidade e seis referências sob o rótulo literal `Unidade temática:`. Estas seis não são contadas como novas definições de habilidade. As três grafias atípicas `EMLGG303` (p45), `EM1313CNT305.RJ02` (p84) e `EM13CNT0101.RJ02` (p85) permanecem literais, sem correção ortográfica, equivalência BNCC ou alias inventado.

Dos 758 registros codificados do cache1.5, 744 IDs válidos, códigos, localizadores, pais e posições aplicáveis foram preservados. 572 corpos foram corrigidos e 172 já estavam iguais. Foram recuperadas 146 ocorrências não representadas. Quatorze registros extras eram duplicatas técnicas: um código local era produzido duas vezes, uma no anchor de outro código e outra no seu identificador físico correto. O candidato conserva o ID da ocorrência física correta; `recovery-report.json` enumera os 14 IDs técnicos a superseder, seus IDs retidos, evidências antigas e geometrias. **O coordenador `/root` autorizou tecnicamente as 14 supersessões documentadas, preservando IDs válidos, registros antigos e provas. A revisão independente do auditor é obrigatória antes do vínculo; o candidato não foi vinculado ao MF. Esse aceite técnico automatizado não é aprovação humana.**

## Método e diagnóstico

O censo foi lido do PDF original antes de comparar os corpos de saída. Não se executou ingestão nem parser completo. As rotações foram normalizadas exclusivamente em memória pelo helper de geometria; o hash do arquivo original é conferido.

As páginas 12, 32 e 168 foram inspecionadas visualmente em pequenas renderizações privadas. `three-page-diagnosis.json` documenta cada código e corpo. Não há tabela estrita nessas páginas (`lines_strict`: zero). A fonte apresenta faixas sombreadas com parágrafos em coluna única e rótulos em negrito. Nas páginas12/168, o fallback genérico começava a seleção no x do identificador, perdendo o começo das linhas seguintes e incorporando rótulos posteriores. A página32 é controle positivo: o fallback de parágrafo rotulado já preservava os quatro corpos, que não foram alterados.

A recuperação usa todas as ocorrências primárias, não somente os anchors conhecidos pelo cache, e os rótulos literais `Habilidade`, `Habilidade específica`, `Competência específica`, `Objetos de conhecimento`, `Campos de Atuação Social` e `Unidade temática`, inclusive quando aparecem na mesma linha. Cada fragmento físico é transcrito por palavras e conferido caractere por caractere com um leitor independente de clusters de glifos. Normalizam-se apenas as quebras de linha conforme `clean_text` existente; grafia, pontuação e variantes impressas são conservadas. O limite não depende de verbo, infinitivo, heurística morfológica, bbox do extrator ou texto de outra fonte.

Todos os parágrafos codificados terminam antes de outro campo explicitamente rotulado na mesma página. A ausência de ponto final em `EM13CHS101` p295 foi mantida, pois o próximo rótulo delimita fisicamente seu término. Não se acrescentou pontuação nem continuação externa. Os três `EM13MAT106` impressos na p168 permanecem três ocorrências distintas.

## Verificação executada

`runtime-verification.json`: loader real `source_uncoded_items`, `finalize_items`, schema Learning e checker literal de produção passaram **890/890**, com 890 IDs únicos e zero erros de schema, evidência e conservação dos identificadores válidos. Não se afrouxou o checker.

Controles negativos executados contra a fonte física:

1. Prefixo estrito do corpo.
2. Corpo de outro identificador impresso.
3. Troca de um caractere acentuado.
4. Incorporação do campo seguinte no corpo.
5. Prefixo com evidência também truncada: o checker literal atual aceita esse caso, mas a comparação do corpo completo com a fonte o rejeita. Este controle reproduz a insuficiência que motivou a auditoria.

Controles positivos: corpo íntegro, término sem pontuação seguido de cabeçalho real, três ocorrências legítimas do mesmo código, seis rótulos `Unidade temática` conservados como referência e ausência apenas dos 14 IDs técnicos falsos. O denominador inteiro dos códigos em cada página proposta foi reemitido; não há páginas bloqueadas no candidato.

## Reprodução e integração

Da raiz do repositório:

```sh
var/venv-pipeline/bin/python docs/evidence/native-body-rj-em/prepare.py
var/venv-pipeline/bin/python docs/evidence/native-body-rj-em/census.py
var/venv-pipeline/bin/python docs/evidence/native-body-rj-em/recover.py
var/venv-pipeline/bin/python docs/evidence/native-body-rj-em/verify.py
```

`prepare.py` lê o Source pin e projeta os registros codificados do cache por streaming, verificando SHA do cache e sidecar SHA. Dados intermediários e imagens ficam em `var/native-body-rj-em/`, sem persistir dumps de rawdict ou de todas as páginas. `source-pin.json` conserva o contrato usado para as posições válidas.

`binding-proposal.json` contém os hashes, ranges explícitos das 238 páginas e guardas de integração. O MF consultado não tinha `uncoded_items_path` para esta Source. Se outro adaptador sem código tiver sido acrescentado antes do vínculo, é obrigatório compor aditivamente os objetos e repetir o loader/finalizador; não substituir esse trabalho pelo candidato de corpos. A autoridade proposta é somente `coded_learning_ranges`, sem suprimir capítulos ou seções não codificados. MF, parser, core e caches1.5 permaneceram intactos.

## Proveniência da próxima extração

`technical-supersessions.json` registra os 14 pares `invalid_duplicate_id → superseded_by_id`, cada hash de prova, o pin do peer e a instrução de transportar essa linhagem para o changelog/proveniência da próxima extração. Publicações anteriores permanecem imutáveis. O censo tem 238 páginas codificadas: a p195 contém identificadores nativos ausentes do cache, que só representava 237. Os ranges, os 890 corpos e o SHA do candidato não mudaram com essa correção de metadado.

`integration-verification.json` executou a combinação real de 1.035 registros genéricos com os 890 registros do adaptador: 1.167 registros finais únicos, preservando os 277 registros sem código integralmente, sem genérico codificado remanescente ou erro literal/schema. Esse resultado não substitui o binding e a importação de produção.
