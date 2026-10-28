# ES Ensino Médio: competências sem código e estrutura dos seis volumes-base

Frente exclusiva do auditor, autorizada pelo coordenador: Texto Introdutório, Linguagens, Língua Portuguesa, Ciências da Natureza, Ciências Humanas e Sociais Aplicadas e Matemática. Não altera manifesto Source, núcleo congelado, helpers existentes ou habilidades codificadas conferidas por outra frente. Sem banco, Docker, OCR em massa ou rasterização em massa. Imagens de conferência ficam privadas.

O censo físico foi concluído antes de gerar qualquer sidecar: 417 páginas, com todas as linhas, palavras, caixas e tipografia nativas. `physical-census.json` registra SHA dos seis PDFs, hashes por página e inventários de candidatos a cabeçalho/número. As representações completas das linhas/palavras ficam compactadas em `var/private-evidence/es-em-core/` (3,9MiB no primeiro censo), sem duplicar os PDFs. `table-census.json` fixa a grade física, células únicas, índices de palavras e todo o texto de cada campo. O censo não usa presença de código ou substring como prova de campo inteiro.

Há duas formas documentais relevantes: quadros iniciais de competências e ocorrências repetidas em organizadores, sob contextos próprios. As repetições não serão eliminadas por semelhança de redação. Objetos, campos/categorias, unidades, temas, finalidades de eixos, referências e orientações terão papéis distintos de competências/aprendizagens. Séries só serão atribuídas quando declaradas por cabeçalho primário; nenhuma é deduzida da ordem de páginas ou do código nacional.

O ledger readonly `docs/evidence/source-audit-southeast-fidelity/coded-em-core-identity-ledger.json` cobre457 identidades apenas de LP, Ciências da Natureza e CHSA. Introdução/Linguagens/Matemática não estavam nesse baseline: o censo literal encontra códigos nos outros volumes, sem afirmar que foram previamente aprovados. O novo adapter não recria essas habilidades; vínculos `item_parent_links` usarão ID exato ou seletor Source+página+locator+código unívoco, com cabeçalhos reais.

Particularidade preservada: Matemática p4 imprime a legenda “Competências Específicas de Matemática para o Ensino Fundamental” dentro do volume que se apresenta como Ensino Médio. Os identificadores da tabela são CE01–CE05; a prosa também menciona C04/C05. Não haverá correção silenciosa por memória da BNCC. O escopo documental e a legenda literal contraditória serão documentados separadamente; qualquer posicionamento será fundamentado em evidência explícita.

Comandos do censo (não geram ou publicam corpus):

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-uncoded/em-core/inventory.py
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-uncoded/em-core/inventory_tables.py
```

A geração, o oráculo de completude de campos, os casos negativos, loader/finalizer/schema e as propostas de Sourcefields ainda estão em implementação. O censo não declara conclusão dos seis documentos, da UF ou do release nacional, nem revisão pedagógica humana.
