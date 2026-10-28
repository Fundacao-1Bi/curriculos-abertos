# Revisão independente — Tocantins, Educação Infantil

Revisor: `codex:api_mcp:independent-to-peer`, tipo **automated**. Esta revisão não é aprovação humana ou pedagógica e não declara UF pronta.

O original privado `data/raw/TO/to-dct-ei.pdf` tem 110 páginas e SHA256 `42b3e65fce43bf993518bb6e0426d90ab8069c5ec319906b1ffcdbc87d35d3bc`. O censo foi levantado diretamente do PDF e persistido antes da abertura do candidato. O script lê todas as páginas nativas com `sort=True`; as células são inventariadas independentemente pelos limites vetoriais e centros das palavras, sem usar o adaptador do autor para gerar o denominador.

O censo confirmou 93 linhas de objetivos, 93 células completas de detalhamento e 93 de experiências sugeridas; cinco campos explicitamente nomeados; 15 cabeçalhos etários e 30 definições de direitos específicas dos campos. Objetivos por campo: EO20, CG15, TS9, EF27 e ET22. Não se adotou a contagem proposta como critério de sucesso: a detecção inicial por tabelas automáticas perdeu linhas neste PDF e foi substituída pelo censo independente dos limites vetoriais, que recuperou os 93 códigos distintos.

## Candidato age-v2 executado

Arquivo: `data/manifests/uncoded/to-ei-organizers-age-v2-items.json`; SHA256 `fbb08f66d3c681db8d842dc60d5c88fbb2ff74d2c2dad46283ac6717026841bd`.

- 279 células confrontadas com seu texto completo, coluna física, código quando presente, campo, cabeçalho etário e vínculos: nenhuma divergência.
- 15 nós etários conferidos com os cabeçalhos literais e suas unidades; limites 0–18, 19–47 e 48–71 meses. Nenhuma idade foi inferida dos códigos EI.
- Cinco campos, pais e posicionamentos conferidos. A ordem dos 93 códigos coincide com o documento; `source_order` é único e sequencial.
- Loader e finalizer de produção executados apenas em memória: 329 entradas, 329 registros finais e IDs únicos; texto/código/pai/ordem preservados. Schema `Learning` e `evidence_check` de produção com páginas `sort=True`: 329/329, sem erro.
- Quatro controles negativos sobre cópias dos registros reais foram bloqueados: texto e rótulo etário iguais com evidência emprestada de outro campo; texto e excerpt truncados juntos; duplicação; atribuição de um filho a outro objetivo existente.

Os 30 registros de direitos do age-v2 são **somente rótulos**, como `brincar`, declarados como `explicit_right_label_only`. Eles não contêm as 30 definições completas nas páginas 53, 64–65, 72, 77 e 92. Além disso, os rótulos estão em ordem alfabética em cada campo; o cabeçalho literal usa conviver, brincar, participar, explorar, expressar e conhecer-se. Esses achados foram enviados ao autor para um novo snapshot técnico, preservando o age-v2 e distinguindo rótulo de definição. O relatório conserva ambos como pendências.

## Arquivos e reprodução

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-to-peer/verify.py --census-only
var/venv-pipeline/bin/python docs/evidence/source-audit-to-peer/verify.py
```

`verify.py` aceita `--candidate` e `--proposed` para uma versão posterior, exigindo correspondência com o SHA do candidato fixado pela proposta. Não escreve nos manifestos, adaptadores, PDF, caches ou banco. Somente os relatórios deste diretório são gerados. `independent-census.json` contém localizadores, hashes e comprimentos dos textos, sem redistribuir o PDF ou o texto integral das células. `candidate-fbb08f66d3c6-verification.json` registra as verificações e os controles negativos executados.

## Limites

Os capítulos, orientações e referências fora dos organizadores foram lidos no censo nativo, mas não estão reconciliados registro a registro por este candidato de organizadores. Páginas sem texto nativo não foram renderizadas nesta frente leve. Por isso não se emite comprovante SourceWholeV2, aprovação do documento integral, prova de importação/publicação ou UF pronta. A execução usou apenas o runtime Python local, sem parser completo duplicado, Docker, SQL ou renderização pesada.


## Rechecagem v3 — executada

Candidato `data/manifests/uncoded/to-ei-rights-v3-items.json`, SHA256 `3e15a87ca5489c9afd5b6aca6e9aa2970e0ff6fe391d32fe168534ac9e1beeab`. A rechecagem confirmou as 30 definições completas com confronto independente do texto de cada campo; os 30 rótulos foram separados em `rotulo_direito`, com caixas individuais e ordem literal. O denominador passa a distinguir 329 unidades anteriores e 30 definições acrescentadas: 359 registros, sem duplicar rótulos como direitos completos.

As 329 chaves anteriores e seus textos/códigos/posições/pais foram preservados exatamente. A alteração de tipo dos 30 rótulos foi explícita. Produção loader/finalizer/schema/evidence passou 359/359 e os quatro controles negativos continuaram bloqueados. `candidate-3e15a87ca548-verification.json` não tem divergência nas células nem pendência na parte dos direitos; `v2-v3-preservation.json` registra a preservação. O censo independente exclui também a linha de citação da página 72, cuja grafia difere das demais páginas; ela não foi incorporada ao último direito.

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-to-peer/verify.py \
  --candidate data/manifests/uncoded/to-ei-rights-v3-items.json \
  --proposed docs/evidence/source-audit-to/ei-rights-v3-proposed-source-fields.json
```

A aprovação desta parte documental não altera os limites anteriores: nenhuma declaração SourceWholeV2, revisão humana, importação/publicação ou UF pronta foi emitida.
