# Aceite técnico independente da extração PB CEDOC392

**Passou:** o sidecar de **1.946 registros** foi confrontado com o PDF392 e com denominadores fonte-only, sem divergências ou palavras de células descobertas. Não houve aprovação pedagógica humana nem declaração de vigência, completude da UF ou distribuição de produção.

## Identidade do resultado

- Fonte: `pb-proposta-ei-ef-cedoc`, `data/raw/PB/pb-proposta-ei-ef-cedoc.pdf`,392 páginas.
- SHA-256 PDF: `af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453`.
- Sidecar: `data/manifests/uncoded/pb-cedoc-392-items.json`.
- SHA-256 sidecar: `4336a71d0676c2b48f1e363e06f4ef0368c0eba9e2980ff3fc3c79f2865f998b`.
- Execução final: `2026-10-28T15:03:55.320178+00:00`, PyMuPDF1.26.7, agente independente `/root/data_north/pb_independent`.
- [Resumo completo](pb-independent-392-verification-summary.json) e[confrontos por fragmento/célula/unidade/referência](pb-independent-392-verification-details.json).

## Denominadores e grãos

A leitura nativa percorreu todas as 392 páginas. O inventário geométrico encontrou224 tabelas estritas em178 páginas, sem falhas. A seleção documental exclui os quadros nominais de conteúdos/ciclos(EFi173), exemplos metodológicos(Arte143), rubricas de avaliação(ER380), cabeçalhos e a coluna de vivências EI. A ausência de tabela em páginas introdutórias135/197/233/297–298/351 não foi tratada como ausência curricular.

**1.055 células físicas** contêm palavras de aprendizagem e foram integralmente cobertas. Esse denominador não é a quantidade de metas: uma célula pode conter várias metas, e uma meta pode continuar entre células.

O denominador de **1.689 unidades EF** tem correspondência individual, sem unidade colapsada e sem registro EF extra sem âncora:

| Componente/linguagem | Unidades |
| --- | ---: |
| Língua Portuguesa | 308 |
| Artes Visuais | 94 |
| Dança | 40 |
| Música | 26 |
| Teatro | 28 |
| Educação Física | 45 |
| Língua Inglesa | 284 |
| Matemática | 236(234 com código literal+2 sem código) |
| Ciências | 289 |
| Geografia | 128 |
| História | 177 |
| Ensino Religioso | 34 |

A EI tem **99 objetivos** em15 organizadores de campo/idade, ligados a3 cabeçalhos etários explícitos. As6 subseções de direitos EI foram preservadas integralmente, com títulos, prosa e citações, sem transformar parágrafos docentes em habilidades. Há ainda **120 direitos/princípios EF**, incluindo listas externas aos quadros: LP15, Inglês13, Matemática9, Ciências9 princípios+14 direitos, Geografia10, História10, ER6, Arte22 e EFi12. Os32 nós estruturais preservam a hierarquia.

Assim,1.689 EF+99 EI+120 listas+6 subseçõesEI+32 nós=1.946 registros. Não se somam as1.055 células físicas ou os localizadores de código a esse total.

## Independência e verificação

Os inventários físicos,99 EI, células, marcadores explícitos e listas foram formados a partir do PDF, antes do confronto dos respectivos módulos do produtor. Após um protótipo ter exposto o risco de grão, foram acrescentadas958 âncoras de parágrafos infinitivos/nominais e2 expectativas matemáticas sem código por algoritmos que leem exclusivamente a fonte. Essa complementação não foi cega ao fato de existir um protótipo, mas não importou o extrator nem usou seus textos/contagens como valores esperados.

O verificador executou:

- 3477 confrontos nativos por caixa/página, incluindo1284 fragmentos de referência;
- 1946 textos conferidos contra fragmentos semânticos e contra originais, permitindo somente espaços, normalização Unicode, marcadores declarados e remoção do código delimitado;
- 234 códigos próprios conferidos na grafia original, dos quais37têm formatação/quebras preservadas em `code_original`;
- 445 cabeçalhos distintos confrontados com a fonte e1704 posições anuais com prova literal anterior à aprendizagem;
- 1453 conjuntos de referências confrontados com células físicas independentes; códigos da coluna BNCC não viraram identidade local nem equivalência automática;
- todas as1.689 âncoras EF,99 objetivos EI,120 listas e6 subseções EI correspondentes, com chaves únicas e pais resolvidos.

O snapshot é lido no início e comparado novamente ao fim; uma alteração durante o confronto causa falha. O mesmo SHA passou nas execuções15:01 e 15:03 UTC. A geração determinística do sidecar pertence à frente produtora; esta auditoria confirma estabilidade do artefato entre leituras e verificações.

As[40 imagens examinadas](pb-independent-392-visual-samples.json) cobrem39 páginas únicas, todos os15 organizadores EI, todos os componentes EF, listas fora de quadros, duas geometrias de Matemática, mesclas e continuações, grafia de códigos e a lacunaπ. O revisor foi um agente automatizado.

## Correções materiais resultantes do confronto

- Recuperadas as4 linhas de Música159, continuação do quadro8º/9ºano.
- Eliminada a herança indevida de prosa130 como eixo de Arte136.
- Separadas as metas de Inglês com marcador `·`, além de `•`, preservando284 ocorrências.
- As5continuações nominais de Geografia(Andina/Chile/Europa/Colonial/Oceania) foram ligadas aos respectivos objetivos; não viraram novas metas.
- Separadas metas em uma mesma célula quando uma nova linha física começa por infinitivo após sentença concluída ou por parágrafo espacial distinto. As5 metas sem pontuação final anterior em Ciências304/307/308 foram confirmadas visualmente e recuperadas.
- Preservadas a gramática `(Re)produzir`, as2 metas `Compor…` e a expectativa nominal `Produção de roteiros…` na coluna de objetivos, sem copiá-las de conteúdos vizinhos.
- LP110tem7ºano explícito na nova fonte; não houve retroatribuição ao635, cujo bloco correspondente continua sem ano.
- Matemática EF07MA27 mantém a lacuna deπ do392. Os códigos partidos são preservados, sem preenchimento do glifo ausente por inferência.

## Reprodução e limites

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/pb-cedoc-392-verify.py
```

O comando retorna 0 somente se os confrontos e os denominadores passarem. Os scripts `pb-independent-392-*` nesta pasta regeneram inventário/células/listas/âncoras/subseções diretamente da fonte. O[confronto de todas as unidades produzidas](pb-independent-392-produced-unit-reconciliation.json) confirma1.689 unidades EF esperadas e produzidas, sem extras. O[controle de preservação](pb-independent-392-preservation-check.json) confirma que o 635 e seu sidecar 2008permanecem byte-idênticos.

Não há pendência técnica de extração no snapshot auditado. Edição/vigência continuam desconhecidas; isso não foi usado para interromper a implementação solicitada. A fonte392 é EI/EF e não contém os blocos adicionais de modalidades do635. Revisão pedagógica humana, escolha de versão padrão, incorporação pública, API/portal e distribuição exigem evidências próprias e não são afirmadas por este aceite. Nenhum manifesto/pipeline/original foi alterado por esta frente, e não houve commit ou ação remota.
