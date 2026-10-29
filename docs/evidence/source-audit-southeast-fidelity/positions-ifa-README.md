# Posições explícitas — IFA Linguagens/CHSA do Espírito Santo

Fonte única `es-ifa-lingchsa-6-1`, SHA-256 `d5ac69230fe71ac97de5c6fe0953a6a627da35bb3348fe1738c907c4ed3161cf`, com **265 páginas**. Esta frente leu somente o PDF, os inventários do adaptador e candidatos privados; não editou manifesto, core, caches ou publicação.

## Implementado, executado e verificado

- **30 formulários detalhados** declaram os rótulos originais `Módulo`, `Componente`, `Série` e **`Trimestre`**, além de eixos e competências. Não se converte Trimestre em semestre.
- **90 ocorrências positivas** receberam componente, série e trimestre desses campos. O código não escolhe a posição: por exemplo, a página 40 declara Língua Portuguesa/2ª série/Primeiro para `EMIFALGG603`, enquanto a página 90 declara Língua Espanhola/2ª série/Primeiro para `EMIFALGG601`.
- As **41 definições das seis páginas iniciais** de matrizes gerais continuam com série, componente e trimestre nulos. A etapa EM e a área vêm dos títulos explícitos do próprio documento:20 ocorrências de Ciências Humanas e Sociais Aplicadas e 21 de Linguagens e suas Tecnologias. Os títulos de competência são preservados como enumeração original, sem códigos oficiais inventados.
- São **129 contexts página+código para 131 ocorrências positivas**. O PDF imprime `EMIFALGG501` três vezes na página 32; as três caixas e definições são preservadas, compartilhando a mesma posição geral, sem correção para 501/502/503.
- **819 fragments únicos** passaram literalmente no native rawdict e no glyph trace visível, sem substituição lexical. Incluem todos os campos, códigos positivos, continuações e 259 números de página impressos. As seis páginas de abertura sem número impresso ficam nulas; não se deriva paginação por deslocamento.
- **26 recortes reais do PDF** foram inspecionados pelo modelo, cobrindo todos os nove componentes, ambas as séries, os três trimestres, formulários entre páginas e quatro continuações estratificadas. Atores `automated`; não houve revisão humana.
- O finalizador real, carregado novamente com hash de módulo conferido antes/depois, aplicou a proposta às **131 ocorrências positivas**, com zero diferenças de posição. IDs, códigos, texto, kind, evidências e `source_context` das folhas permaneceram exatamente iguais.

## Denominador por campo explícito

| Componente impresso | Série | Primeiro | Segundo | Terceiro | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Língua Portuguesa | 2ª | 1 | 2 | 7 | 10 |
| Língua Portuguesa | 3ª | 1 | 3 | 3 | 7 |
| Língua Inglesa | 3ª | 1 | 1 | 2 | 4 |
| Língua Espanhola | 2ª | 1 | 1 | 3 | 5 |
| Arte | 2ª | 2 | 3 | 3 | 8 |
| Educação Física | 3ª | 2 | 2 | 3 | 7 |
| Filosofia | 3ª | 5 | 4 | 5 | 14 |
| Geografia | 2ª | 4 | 4 | 5 | 13 |
| História | 3ª | 5 | 5 | 4 | 14 |
| Sociologia | 2ª | 3 | 3 | 2 | 8 |

Os 30 formulários são ocorrências de módulo/componente/série/trimestre; nomes e eixos permanecem como metadata da fonte. Os cabeçalhos dos formulários detalhados nomeiam duas áreas integradas. A proposta mantém essa designação literal e deixa `area:null` no posicionamento singular, sem deduzir uma associação exclusiva pelo componente ou código.

## Continuidade e escopo

Os **12 vínculos físicos** passaram uma verificação independente: páginas consecutivas, mesma coluna corporal original (diferença máxima 0,571pt), campo esquerdo vazio, prefixo literal exato antes do próximo código e limites do mesmo formulário Módulo. Apenas o fragmento registrado herda a posição do item inicial.

Não são criados contexts genéricos nos destinos de continuação. Isso evita atribuir a hierarquia de `EMIFALGG604` 70→71 e `EMIFALGG103` 104→105 às citações dos mesmos códigos em Objetos de Conhecimento.

Há três seletores de página+código que também aparecem como referência contextual no mesmo formulário:`EMIFALGG503` nas páginas 54/127 e `EMIFALGG201` na página 115. O finalizador preserva o tipo `referencia_no_documento`; esses registros recebem apenas o contexto documental do formulário compartilhado, sem promoção a aprendizagem. As 21 referências do inventário original não entram no denominador de 131 definições.

## Proposta congelada e pendência

`positions-ifa-metadata-proposal.json` está congelado como proposta reviewável, **não integrada por esta frente**. O guard é o par source_id/artefato SHA.

- `position_contexts`: 129 seletores pela página inicial e pelo código literal.
- `continuation_scopes`: 12 vínculos de item/célula, separados dos seletores genéricos.
- `source_context`: mantém cabeçalho do aprofundamento, label/título do Módulo, campos Componente/Série/Trimestre, eixos, competências e caixas originais. O `position_evidence` também preserva os fragments verificáveis.

Pendente: incorporação pelo owner do manifesto e repetição dos gates no candidato integrado. A prova trata posições documentais desse PDF e não declara completude editorial da UF, equivalência BNCC, revisão pedagógica ou prontidão nacional.

## Reprodução

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-fidelity/positions-ifa-audit.py
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-fidelity/positions-ifa-continuity-verify.py
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-fidelity/positions-ifa-finalizer-verify.py
```

A primeira etapa relê os campos de todas as 265 páginas e valida todos os fragments. A segunda testa os 12 vínculos físicos. A terceira usa o candidato atual se disponível ou o candidato privado imutável anteriormente verificado enquanto um novo probe está em execução, registrando caminho/hash e o finalizador carregado. `positions-ifa-render.py` gera os recortes somente em `var/private-evidence/`; geração não substitui inspeção visual.

## Hashes de entrega

- `positions-ifa-metadata-proposal.json` — SHA-256 `be5a94cba74df08d7d4e70b96009fe10d90356e231b46b15f5592e22beba9411`.
- `positions-ifa-verification.json` — SHA-256 `c9ef0f79438bf77b8e5a999ae6a067736d67a11cdaa100399bc8e029b88db128`.
- `positions-ifa-continuity-verification.json` — SHA-256 `2773a7e93ba08126674e070633f8831e4950e2974eb2ab5008717c5e7e8d345a`.
- `positions-ifa-finalizer-verification.json` — SHA-256 `af9ea18d64b8b19e1468cb8513725c69789e89097288cf1481a79b0beb12433c`.
- `positions-ifa-visual-review.json` — SHA-256 `16fad62f427c9a9747dbdd20ca2e73d1daa94aaec80341a17e7c9f19a530a0e4`.
