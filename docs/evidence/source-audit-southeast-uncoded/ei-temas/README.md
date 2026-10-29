# ES: EI e Temas Integradores — extração documental sem código

Ator automatizado; revisão humana e pedagógica pendentes. Nenhuma declaração de UF pronta, equivalência entre currículos ou pré-requisito de escolarização.

## Escopo físico e denominadores

O censo percorreu as 140 páginas do volume EI e as 15 páginas de Temas Integradores antes da construção dos sidecars. `physical-census.json` registra cada página, texto nativo SHA, quadros e cabeçalhos; `raster-image-inventory.json` enumera os objetos de imagem. Índices, créditos, referências e governança foram inspecionados e não transformados em aprendizagens.

A EI apresenta 105 objetivos com código em 21 quadros físicos. Eles permanecem no adaptador codificado existente: este pacote propõe somente seus 105 vínculos hierárquicos, conferidos contra `es_ei_rows.extract_rows` real, sem duplicar objetivos ou declarar equivalência com os itens das colunas adjacentes.

O censo independente de marcadores e rótulos no PDF encontrou:

- 36 direitos: seis gerais e seis aplicações em cada um dos cinco campos;
- 42 colunas em 21 pares físicos:210 marcadores docentes e 259 indicadores de observação;
- três princípios, com três descrições de valores e 11 ações docentes;
- cinco campos, quinze grupos etários explícitos e quatro pilares da Matriz de Saberes;
- 19 sínteses de aprendizagem em tabelas raster nas páginas 132–133: EF4, ET5, EO3, CG4 e TS3.

`expected-target-ids.json` deriva 505 IDs diretamente dos marcadores/rótulos e das caixas originais. `hierarchy-and-target-id-verification.json` confronta esses 505 IDs com o importador final, mais os 19 IDs da síntese derivados das caixas e parágrafos OCR registrados. Os denominadores por campo/faixa/coluna estão em `by_field_age_column`; não foram obtidos contando o sidecar.

O documento de Temas contém19 definições TI físicas nas páginas 6–14, inclusive continuações nas páginas 7,8,9,11,13 e14. Foram preservadas a grafia `TI I0 /ES.` e a notação irregular `TI 13. /ES`, sem correção ou alias inventado. Os números declarados nas páginas 4–5 são internamente diferentes: a prosa menciona 12/15 temas da BNCC; o censo das definições locais continua 19. O denominador deste pacote é a lista efetivamente impressa, sem harmonizar essas declarações.

## Tipagem, posições e hierarquia

Os itens de `Dicas para o Planejamento` são ações/contextos docentes. Os de `Vale Observar Se` são indicadores/contextos de observação. Nenhum dos dois tipos foi promovido a objetivo codificado da criança. A síntese foi tipada `sintese_aprendizagem` e mantém o aviso da página 132: é elemento balizador e indicativo, **não condição ou pré-requisito de acesso ao Ensino Fundamental**.

Os títulos de capítulos/seções, campos, grupos e cabeçalhos de quadro são rótulos reais do corpo do documento, com caixas próprias. Os quinze grupos usam as faixas escritas nos quadros; meses 0–18,19–47 e48–71 são somente a conversão das unidades explicitadas. Direitos e síntese não receberam faixa etária presumida. Campos mantêm a grafia original de cada parte, inclusive diferenças na ordem “Formas/Cores”; não foi criada equivalência entre variantes.

A capa de Temas nomeia “FUNDAMENTAL E MÉDIO”, embora o manifesto também liste EI e o corpo mencione diferentes etapas. As posições do adaptador conservam EF/EM, explicitamente documentadas pela capa, e registram a divergência. Os 19 temas são conteúdos/temas curriculares, sem alegar que suas descrições são objetivos individuais dos estudantes.

## Provas e limites

`full-verification.json`: importação real por `source_uncoded_items`, `finalize_items` e `attach_hierarchy`; 1.439 registros, 5.402 fragmentos nativos e 25 fragmentos OCR. Todos os fragmentos nativos foram confrontados com rawdict e glifos visíveis. Espaços sintéticos do PDF e sobrescritos são registrados separadamente: cada caractere não branco também é conferido por código Unicode e origem geométrica, sem relaxar o importador.

A síntese raster usa Tesseract 5.5.2, modelo português SHA registrado, renderização4x do PDF real e inversão da origem inteira do pixmap para as coordenadas do PDF. Os 11 arquivos `synthesis-ocr-*.json` preservam transcrição integral, palavras, confiança, caixas, fonte/hash/página, engine/modelo e SHA do render privado. Os 19 enunciados foram inspecionados integralmente nas duas tabelas renderizadas pelo ator automatizado. A prova técnica é **correspondência com a transcrição OCR registrada**; não é prova nativa nem revisão humana. Não houve correção manual dos textos OCR.

Os diagramas raster de organização/matriz (figuras 5–10 e 20) permanecem identificados no inventário e nas amostras privadas. Seus conceitos/pilares/direitos também aparecem na prosa e nos quadros nativos extraídos; o pacote não certifica por glifos nativos cada palavra interna dessas imagens. A tabela raster de síntese foi tratada separadamente e integralmente, pois contém enunciados adicionais. O organograma 68 inclui uma variante textual de campo (“imagens”) que não foi usada para renomear os capítulos.

`visual-inspection.json` registra os renders realmente vistos, separados dos renders apenas gerados; todos ficam em `var/private-evidence/es-ei-temas`, com SHA. A inspeção cobre os cinco campos, os três grupos, direitos, princípios, matriz, todos os temas físicos e ambas as tabelas de síntese. Nenhuma imagem de fonte foi gravada em docs.

## Reprodução

Executar a partir da raiz, sem escrever em `data/extracted`:

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/es-ei-physical-census.py
var/venv-pipeline/bin/python data/manifests/uncoded/es-ei-target-census.py
var/venv-pipeline/bin/python data/manifests/uncoded/es-ei-temas-adapter.py
var/venv-pipeline/bin/python data/manifests/uncoded/es-ei-synthesis-ocr.py
var/venv-pipeline/bin/python data/manifests/uncoded/es-ei-temas-verify.py
var/venv-pipeline/bin/python data/manifests/uncoded/es-ei-hierarchy-verify.py
```

`determinism.json` compara os bytes completos dos dois wrappers após a repetição nativa + OCR; o instante de referência registrado no wrapper é fixo para permitir essa prova. PDF, manifesto e core não são modificados. `source-binding-proposals.json` é proposta para o agente responsável, ainda não aplicada. Os 105 vínculos para objetivos já codificados estão separados em `coded-parent-proposals.json`; a resolução foi provada em RAM, mas os vínculos não foram inseridos no wrapper para exigir integração explícita com os itens codificados.
