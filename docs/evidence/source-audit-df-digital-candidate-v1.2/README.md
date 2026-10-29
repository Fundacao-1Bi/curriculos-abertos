# DF digital EI/EF — correção e reconciliação integral V2

Os dois volumes passaram no gate `reconciliation-gate/2.0`, revisão `page-cell-v1.5.0`, com autoria automatizada explícita e revisão independente dos quadros. A palavra `candidate` nos nomes preserva a identidade dos arquivos testados; o manifesto foi atualizado após o encerramento do FULL4. Isso não promove um corpus nem declara DF pronto.

| Fonte | Objetivos | Estrutura | Contextos | Páginas documentais | Total verificado |
| --- | ---: | ---: | ---: | ---: | ---: |
| DF digital EI, 77 páginas | 395 | 76 | 81 | 74 | 626 |
| DF digital EF, 140 páginas | 794 | 299 | 91 | 137 | 1.321 |

O peer independente começou pelos PDFs e produziu um censo conservador de 1.175 unidades. Revisou fisicamente 15 divergências: 14 eram fronteiras válidas, e uma era erro do extrator. A expressão “Localizar o Sistema Solar na nossa galáxia.” havia sido dividida porque o heurístico tratava qualquer palavra terminada em `-ar` como infinitivo. A revisão 1.2 remove essa regra; usa terminal e espaçamento tipográfico, mais três quebras de página comprovadas individualmente. Os três casos têm texto, caixas e hash da fonte em `data/manifests/uncoded/proofs/df-digital-paragraph-boundaries.json`.

Todos os 1.563 objetos não afetados permaneceram idênticos. A frase mesclada preserva o primeiro ID; o falso segundo ID é supersedido, sem renumerar os locators posteriores. `granularity-correction.json` registra a linhagem. É uma correção de extração, sem mudança da edição normativa ou equivalência curricular automática. Rótulos históricos de fronteira nos objetos preservados descrevem a proveniência do heurístico 1.1; a aceitação atual usa a revisão física independente, sem classificar enunciados nominais como verbos.

A auditoria independente verificou todas as 1.189 fronteiras e seus pais, eixos, componentes, temas, colunas, organizadores e ordem. Rejeitou controles que juntavam ou dividiam objetivos mantendo todas as palavras e um controle com pai existente incorreto. Os textos primários foram reconstruídos das linhas originais antes de receber os hashes; a igualdade UTF-8 com a candidata e o finalizador real foi exigida. O diretório `../source-audit-df-digital-peer/` conserva censo, decisões e testes. O pin do mapa primário é `725e978aa482f13acf22466acccd594294cc1f243a7559381a13fd3d5a03310f`.

Os 375 nós foram derivados dos títulos de volume, legendas de quadro e cabeçalhos de idade/ano, eixo, componente e tema presentes no original, com a gramática pública de chaves técnicas. Os 172 contextos preservam fundamentos, créditos, referências, premissas e capas. Todas as 211 páginas nativas tiveram IDs e textos exatos fixados antes da extração. As capas gráficas têm prova de cinco regiões de OCR real; o texto bruto defeituoso das páginas inteiras fica como diagnóstico privado. As páginas 6 contêm apenas padrão decorativo. Renders primários ficam privados, com inventário de hash, sem redistribuição.

Pins ativos após a integração:

- EI: `data/manifests/uncoded/df-digital-complete-context-df-competencias-digitais-vol2.json`, SHA256 `f40c428c23f93e11b386524b64e14ca05657647744889505157d6f623caae04a`.
- EF: `data/manifests/uncoded/df-digital-complete-context-v1.2-candidate-df-competencias-digitais-vol3.json`, SHA256 `e6a42d4cea4be93a3cff2469f5055c8881272411f45daa258916d57a4e0c2845`.
- Base corrigida dos quadros: `data/manifests/uncoded/df-digital-items-v1.2-candidate.json`, SHA256 `81cfbd6afc943c48bbb5472a949c531be6c9858a17ab0ab7b084f28e50180257`.

Os arquivos antigos e seus pins continuam preservados. Os recibos ativos estão em `data/manifests/reconciliation/df-competencias-digitais-vol{2,3}.json`. `input-integration.json` registra os campos antes/depois, hashes e a janela de integração liberada pelo responsável do FULL.

Comandos a partir da raiz:

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/df-digital-extract-v1.2-candidate.py
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python data/manifests/uncoded/df-digital-context-v1.2-candidate.py
var/venv-pipeline/bin/python docs/evidence/source-audit-df-digital-peer/verify.py --candidate data/manifests/uncoded/df-digital-items-v1.2-candidate.json --sha256 81cfbd6afc943c48bbb5472a949c531be6c9858a17ab0ab7b084f28e50180257
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python docs/evidence/source-audit-df-digital-candidate-v1.2/reconcile_whole_sources.py
```

Os probes interceptam tanto `write_json` quanto `write_extraction_cache`. O core e o helper RS/MS congelado não foram alterados. O refresh seletivo nacional e a conferência dos shards/runtime publicados permanecem etapas separadas sob responsabilidade da integração final.
