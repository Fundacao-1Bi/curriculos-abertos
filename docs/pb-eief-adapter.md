# Paraíba — adaptador documental EI/EF

Fonte `pb-proposta-ei-ef`, PDF oficial de 635 páginas: <https://basenacionalcomum.mec.gov.br/images/implementacao/curriculos_estados/documento_curricular_pb.pdf>. Original privado em `data/raw/PB/pb-proposta-ei-ef.pdf`, SHA-256 `b55786376874ab6a46064c44726d578d37f550a99a702069fe7065946ce26383`. O adaptador verifica esse hash antes de executar; não modifica o original nem usa modelos para completar texto.

## Escopo e limites semânticos

`data/manifests/uncoded/pb-eief-items.json` contém 2.008 registros documentais. Inclui 103 objetivos nos 15 quadros da Educação Infantil; colunas de objetivos do EF regular nos nove componentes; Matemática com 234 códigos literais e dois objetivos cujo original não apresenta código; Ensino Religioso na EI e na EJA; princípios/direitos de Educação Física, direitos das linguagens de Arte e objetivos gerais explícitos dos ciclos da EJA. Integra ainda os 180 registros indígenas descritos em `docs/evidence/source-audit-pb/pb-indigenous-adapter.md` (42 nós estruturais e 138 folhas).

A distribuição é 1.620 objetivos de aprendizagem, 234 habilidades com código literal, 54 competências, 42 seções normativas, 28 direitos de aprendizagem, 21 critérios de avaliação, seis princípios curriculares e três objetivos gerais. Tipos distintos não são contados automaticamente como habilidades.

A coluna externa BNCC é referência documental da linha física, sem equivalência automática e sem transformar seu código no identificador do objetivo local. Células mescladas e continuações mantêm a relação de muitos objetivos com um conjunto de referências. Tokens anômalos, como `EF67PB01`, `EF697P06/07`, e tokens partidos no original são preservados, sem correção silenciosa. O código final de Matemática identifica a prosa que o antecede; `EF06MA07` na página 310 não usa o conteúdo vizinho “Frações.” como texto da habilidade.

Marcadores de listas são guardados em `source_number`, `source_context.raw_text` e/ou `evidence.source_original_excerpt`; o trecho semântico `evidence.excerpt` corresponde ao texto publicado do item. O código literal possui localização de evidência com papel `code_locator`. Esse tratamento não altera palavras, ortografia, pontuação ou formulações da fonte. Expressões matemáticas bidimensionais conservam glifos e caixas, sem inventar barras de fração.

A segunda tabela de LP na página 104 e suas continuações não declaram 7º ano: a posição permanece desconhecida. EJA mantém ciclo/modalidade, sem equivalência inferida a anos do EF. Os objetivos indígenas sem atribuição explícita de etapa/ano mantêm `positions: []`. ER na EI conserva o componente e o campo/idade declarados, sem equipará-lo a um campo nacional por suposição.

O texto de introdução, competências gerais e contextos pedagógicos permanece nas seções documentais da extração central. Quadros de conteúdo, vivências, metodologia, avaliação, radares e exemplos explicitamente ilustrativos não se tornam aprendizagens adicionais. As modalidades posteriores à página 484 foram examinadas; não foram excluídas apenas por sua posição no arquivo. O relatório indígena documenta as seleções e exclusões das páginas 538–631.

## Reprodução

Executar a partir da raiz, com Python seguro/PyMuPDF 1.26.7 ou superior:

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/pb-eief-extract.py --layout
var/venv-pipeline/bin/python data/manifests/uncoded/pb-eief-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/pb-eief-selfcheck.py
var/venv-pipeline/bin/python data/manifests/uncoded/pb-eief-verify.py
var/venv-pipeline/bin/python data/manifests/uncoded/pb-eief-integration-check.py --require-binding
```

O inventário de geometria usa `lines_strict` para tabelas; os quadros preenchidos da EI usam cabeçalho/retângulo de fundo e intervalos de parágrafos. Referências usam palavras nativas dentro da célula, pois algumas linhas do PDF atravessam conteúdo e referência na mesma baseline. O censo independente não importa o extrator como denominador.

## Evidências e integração

- Inventário independente: 291 tabelas físicas em 230 páginas, 15 quadros EI/103 objetivos e 1.157 células locais com aprendizagem; seis falsos candidatos de radar permanecem registrados como exclusões explícitas do inventário físico original de 1.163.
- Evidências de leitura visual principal em `pb-visual-samples.json`: 43 páginas efetivamente renderizadas e vistas, incluindo todos os 15 quadros EI, todos os componentes, exceções de ano/código, direitos de Arte e ciclos EJA. Auditorias indígena e independente conservam suas próprias amostras.
- `pb-selfcheck-all-fragments.json`: 2.287 fragmentos nativos, zero falhas, zero diferenças de ordem literal e zero pais ausentes; reconstrução semântica e IDs únicos verificados.
- `pb-independent-verification-summary.json`: PASS no SHA final `b64de254205f8d9700baafa3c7efde58808fff6da01398e6c5e7e652f882a514`, zero erros e zero células descobertas; 3.532 fragmentos nativos (incluindo 1.245 referências), 2.008 textos, 397 cabeçalhos nativos, 103 posições EI, 1.560 controles de ano, 1.452 conjuntos de referências e 823 âncoras independentes. Todos os denominadores foram encontrados integralmente.
- `pb-integration-check.json`: PASS, 2.008 registros carregados, 234 códigos Matemática, 2.758 registros finais da fonte e zero definições genéricas duplicadas. Comprova o carregador `source_uncoded_items` e o finalizador reais, preservação de texto/tipo/posição/contexto/hierarquia e ausência de definições genéricas duplicadas. A execução final com `--require-binding` exigiu e verificou a ligação efetivamente publicada em `northeast.json`; não modificou o manifesto. O corpus consolidado é produzido pelo responsável do pipeline.
- `pb-reproducibility.json`: PASS, duas gerações com bytes idênticos. `pb-checkpoint.json` mantém hashes e caminhos para retomada.

Contrato de ligação acordado com o pipeline: `uncoded_items_path: data/manifests/uncoded/pb-eief-items.json`, `adapter_authority.generic_coded_reference_pages: [1,635]`, `adapter_authority.coded_learning_pages: [259,325]`. Os códigos genéricos fora da autoridade matemática permanecem como referências documentais; as ocorrências genéricas de Matemática são substituídas pelas ocorrências do adaptador. Seções documentais são conservadas. `source_order`, chaves estruturais e `parent_key` preservam a hierarquia literal.

Esta entrega não afirma vigência editorial atual, reconciliação normativa global da UF, revisão pedagógica humana ou aceite nacional. O Ensino Médio da PB continua com bloqueio externo CAPTCHA registrado pelo responsável da fonte; isso não é usado para ocultar pendências de processamento do PDF EI/EF acessível.
