# Peer PE EI — fidelidade do organizador, procedência não aprovada

**PASS técnico no recorte declarado**, ator automatizado, sem revisão humana, sem aprovação de procedência, vigência, adoção, redistribuição ou publicação. Os recibos foram produzidos temporariamente em `var/pe-ei-peer-freeze/` durante freeze operacional e copiados para este diretório depois da liberação explícita de operações, com igualdade de bytes/SHA registrada.

PDF: `data/raw/PE/pe-curriculo-ei.pdf`, SHA256 `a54f4801045b826ef20700074495ebea9b4b145bcabbdb24bd217845914a64d3`,2.505.568B/134p. Sidecar congelado `data/manifests/uncoded/pe-ei-objectives-items.json`, SHA256 `3325af8e84729ac9791208a5953cb9cbc2aee9dbe343f5221dd6863ef7e2ddd5`,525.303B. A cadeia GoogleSites→Drive→emissor permanece `pending_primary_distribution_chain`; a fidelidade de um arquivo não resolve sua origem institucional.

## Censo anterior aos candidatos

O peer leu a introdução2.12/legenda83–86 e os115objetivos originais das31tabelas87–117, escrevendo `docs/evidence/source-audit-pe-ei-organizer-peer/primary-census.json` antes de abrir o output/ledger autoral. Expectativas da tarefa eram conhecidas; o recount é independente, não cego. São36bebês/39criançasbempequenas/40criançaspequenas;21EO/17CG/16TS/34EF/27ET, total115. Um somatório inicial por grupo estava errado e foi corrigido pelo recount físico, sem alterar fonte/sidecar.

O denominador vem dos identificadores localizados fisicamente nas colunas, não de regex nacional: existem115, não113. O código `EI02S 06PE` na101não temT; `EI003EF11PE` na117temzeroextra; `EI02EO01PE)` na96não temparêntese inicial. Os recortes próprios inspecionados mostram exatamente isso. O código compacto elimina somente whitespace de agrupamento, segundo a legenda85–86; `code_original` conserva a representação recebida e não fabrica envelope. Não se cria alias ou equivalência nacional pela remoção dePE.

## Escopo e posicionamento

A fonte descreve6colunas. Este peer aprova apenas as5colunas textuais de objetivos, intro/legenda e cabeçalhos de grupos/campos:115objetivos+3grupos+15campos+organizador+legenda=135nós,134pais,252fragmentos. A primeira coluna contém a espiral gráfica dos direitos, **não transcrita/aprovada por este adapter**; nem todas as134páginas estão reconciliadas. Não se afirma SourceWhole, UFpronta ou completude de toda a imagem/organizador por causa do número135.

Os grupos são derivados da sequência/cabeçalhos físicos e legenda:0–18,19–47,48–71meses, sem inferir pelo código malformado. Os rótulos e os campos foram conferidos em todos115registros. Nomes canônicos de componente/campo usam a legenda, enquanto os cabeçalhos impressos permanecem preservados como texto/evidência; não viram disciplinas. O exemplo da legenda é metadado, não um116ºobjetivo. As considerações da introdução preservam flexibilidade dos objetivos e que não os alcançar não implica problema de aprendizagem.

**Pendência de melhoria de posicionamento:** os115objetivos ainda não possuem `age_min_months`/`age_max_months`+`age_evidence` estruturados, apesar da faixa textual explícita. O peer não alterou esse conteúdo congelado. Para servir interseção seletiva em `age_months`, é necessário enriquecer esses limites a partir da legenda/cabeçalhos com o contrato já existente, mantendo literalidade e sem estender a aprovação de procedência.

## Verificação real

`audit.py` escreve somente no diretório onde está salvo; o primeiro replay usouvar durante o freeze. Conferiu os pares código/texto/pai/campo/faixa de cada objetivo contra reconstrução independente por geometria; preservou caixa/pontuação/acentos, normalizando só whitespace. Usou páginas primárias `sort=True`, leitor nativo por glifos, loader/finalizer efetivos e schema1.1.0 para Source/135Learning. Resultado final245registros no replay global desse Source, sendo135específicos; os demais são contextos genéricos, não245objetivos. Preservados79registros externos à faixa alterada; autoridade remove apenas códigos genéricos87–117 e contêineres genéricos84–86. A presença dos demais contextos não comprova sua fidelidade/editorialidade.

Source clonado, nunca Source real:

```json
{"coded_learning_pages":[87,117],"uncoded_page_sections_pages":[84,86]}
```

Seis negativos recusados:inventarT;retirarzero;mapearocódigoanômaloparaocampoerrado;alterarotextodaúltimapágina;trocaridadepelo código;texto inventado submetido ao checker de produção. IDsesperados/verificados135constam de `verification.json`, junto aos hashes/runtime, estado do cache, limites e recibo visual automatizado. Cache/raw/MF/core/sidecar/banco não foram alterados; não houve OCR, extração, builder ou publicação.

O replay utiliza Source clonado e não substitui a verificação pós-binding da configuração real. A cópia final após liberação de operações está registrada em `relocation.json`; os hashes do relatório foram preservados. A aprovação limitada não foi reinterpretada como procedência oficial.
