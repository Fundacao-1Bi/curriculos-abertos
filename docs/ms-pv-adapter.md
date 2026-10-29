# Mato Grosso do Sul — Projeto de Vida 2024

Frente executada para ING-03, DAT-01, DAT-05 e ESC-02. Autor: `agent:rs_adapter:ms-pv`. Auditor independente: `agent:ms-independent-auditor`, subagente distinto do autor. Ambos são **atores automatizados**; nenhuma revisão pedagógica humana ou homologação institucional foi atribuída.

## Fonte e abrangência

Fonte oficial `ms-projeto-vida-orientacoes-2024`, **Orientações Pedagógicas — Projeto de Vida**, SED/MS, edição 2024, 127 páginas. Arquivo local: `data/raw/MS/ms-orientacoes-projeto-vida-2024.pdf`; SHA-256 `eff8fcd19d69b1f5d614cbb2ca1599d98e11c697772084b56694a142fecf7048`.

O documento se declara complementar ao Currículo de Referência, detalhando objetos de conhecimento. Não foi usado como substituto fictício da ementa de 2023 indisponível. Esta entrega atesta o processamento deste complemento; não declara isoladamente a UF pronta nem comprova publicação nacional ou jornada API/MCP.

O adaptador processou integralmente os **73 quadros curriculares**, páginas 51–125, excluídas as divisórias 78 e 99. Contém Ensino Fundamental do 1º ao 9º ano e Ensino Médio do 1º ao 3º ano, com os **48 contextos explícitos de ano × bimestre**. As seções introdutórias, concepção e orientações permanecem no processamento documental compartilhado; as páginas divisórias e a estrutura curricular real são ligadas pelos nós do adaptador.

## Resultado estruturado

| Tipo | Registros |
| --- | ---: |
| Divisórias de etapa | 3 |
| Anos escolares | 12 |
| Quadros curriculares | 73 |
| Habilidades com códigos originais | 141 |
| Ocorrências documentadas de pilares | 226 |
| Grupos de objetos associados aos pilares | 226 |
| **Total** | **681** |

As linhas físicas determinam a associação **código → habilidade → pilar → objetos**. Os códigos são verticalmente centralizados e sua altura não delimita o início da redação. O adaptador usa as células obtidas por `find_tables(strategy='lines')`, com caixas completas; todos os fragmentos permanecem localizáveis. Uma ocorrência repetida conserva ID próprio e contexto: não se deduplicam linhas ou pilares por mera igualdade textual.

Cada quadro é filho do ano escolar correspondente; cada habilidade é filha do quadro, cada ocorrência de pilar é filha da habilidade daquela linha física e os objetos são filhos do pilar. Há `key`/`parent_key` estáveis, códigos originais, evidência de código separada, caixas das três células, posição e título literal do pilar. `MS.EM13LP12325`, `MS.EM13LP2740` e as redações visivelmente impressas como `colhimento` permanecem preservados. Os códigos longos não foram convertidos automaticamente em códigos BNCC.

Ano e bimestre vêm de cabeçalhos **visíveis**, acompanhados de evidência. Continuação sem novo cabeçalho carrega a última declaração visível do mesmo percurso documental. Não se infere período pela ordem de tabelas ou pelo código. Os nós de ano têm período nulo; nenhum contexto global restringe o ano inteiro ao primeiro bimestre.

## Correção da camada textual e visibilidade

O PDF apresenta corrupção sistemática em `/ActualText`: palavras são fragmentadas e glifos finais aparecem duplicados na extração semântica, embora o documento seja visualmente legível. Exemplo na página 100: a redação visível contém `vulnerabilidades vinculadas` e `bem-estar.`, enquanto a camada semântica pode produzir separações internas e `bbem-estar.`.

O helper compartilhado `pipeline/ms_glyphs.py`, implementado mediante coordenação com a frente pipeline, lê os glifos efetivamente desenhados por `get_texttrace()`, agrupados pela origem real da linha de base. A transcrição não aplica autocorreção ortográfica. A camada semântica original fica separada em `source_context.native_text_original`.

`get_texttrace()` sozinho também não comprova visibilidade. A auditoria identificou 16 rótulos fantasmas `1º Bimestre` em páginas de continuação: 14 são sobrepintados por células opacas posteriores e dois são brancos sobre branco. Eles não aparecem na renderização. O helper aplica duas regras verificáveis:

- Remove um glifo integralmente coberto por **subcaminho retangular fechado opaco posterior**, usando `seqno`. A caixa geral de uma grade aberta não é tratada como área preenchida.
- Nos corpos dos quadros aplica a política explícita `black_curricular_table_body`: a auditoria independente conferiu os glifos de todas as 423 células e confirmou que o conteúdo curricular real é preto. Os 176 glifos brancos pertencem aos 16 rótulos fantasmas. Essa política não se aplica aos cabeçalhos brancos sobre fundo colorido.

A evidência usa `method: pymupdf-rendered-glyph-trace-v1`, coordenadas de exibição do PDF e, para corpos de tabela, `glyph_color_policy: black_curricular_table_body`. O carregador central deve conferir esses fragmentos pelo mesmo helper e política; a camada semântica corrompida não pode substituir a prova visual dos glifos.

Outra diferença real da fonte ocorre na página 59: uma aspa de fechamento do título do pilar está em fonte regular, embora o restante seja negrito. Ela permanece no título. Iniciar a caixa dos objetos nessa aspa repetiria o título na redação dos objetos; a regra foi corrigida para o conjunto antes da verificação final. As duas ocorrências visíveis de Cidadania e Compromisso Ético naquela célula foram preservadas.

## Execução e conferência

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/ms-pv-2024-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/ms-pv-2024-verify.py
```

Runtime: Python 3.11 / PyMuPDF 1.26.7. Saída: `data/manifests/uncoded/ms-pv-2024-items.json`, objeto com fonte, hash e itens. A frente `data_central_south` integrou `uncoded_items_path` e a autoridade do adaptador para as linhas codificadas 51–125. A fonte e os PDFs não são modificados; não houve commit ou ação remota.

O auditor produziu seu denominador **antes de ler o sidecar**, usando exclusivamente o PDF, seus limites de células, códigos, títulos de pilar e cabeçalhos visíveis. Não importou o algoritmo do adaptador nem o helper compartilhado. Resultado do confronto independente final: **508 verificações, zero falhas**; 73/73 quadros, 141/141 linhas, 226/226 pilares e 226/226 grupos de objetos. Os 681 IDs/keys têm pais resolvidos e os objetos permanecem dentro da linha física correta.

A verificação técnica do autor também foi executada integralmente: **827 fragmentos literais**, **282 células completas de habilidades/objetos** e **80.693 glifos reais**, sem perda, inclusão externa ou duplicação. O carregador e o finalizador compartilhados aceitaram **681/681 registros**, preservando todos os pais e as posições explícitas de Projeto de Vida. O teste negativo central rejeitou `1º Bimestre` invisível mesmo quando a mesma string existe na camada semântica da página. Reexecução produziu bytes e IDs ordenados idênticos; SHA-256 final do sidecar: `77eb9feaa003382a73741f36f3379d83aa945debae1cd128b7ad95513e781f08`.

A inspeção visual independente atravessou todos os 12 anos e os quatro bimestres: **48 páginas com cabeçalhos explícitos**, organizadas em 12 folhas de contato, além das páginas de risco 103, 111 e 114. A página 103 também foi renderizada por Poppler para confirmação por um segundo renderizador. A conferência visual é amostral; o confronto determinístico dos textos, códigos, posições e relações físicas abrange todas as linhas.

Evidências em `docs/evidence/source-audit-ms-pv/`:

- `independent-denominator.json`: inventário documental independente.
- `independent-adapter-comparison.json` e `independent-adapter-cell-checks.json`: confronto integral e identificação do hash conferido.
- `independent-visual-review.json`, folhas de contato e PNGs: seleção, revisor automatizado e achados visuais.
- `ms-pv-2024-table-inventory.json` / `ms-pv-2024-row-inventory.json`: 73 quadros, 141 linhas e seus limites reais.
- `ms-pv-2024-extraction-report.json`: contagens e hash atual do sidecar.
- `ms-pv-2024-shared-helper-tests.json`: casos positivos e negativos de transcrição, oclusão e texto branco invisível.
- `ms-pv-2024-verification.json`, `ms-pv-2024-all-literal-fragments.json` e `ms-pv-2024-full-cell-accounting.json`: conferência literal, contabilidade de glifos e integração executada com o carregador/finalizador reais.
- `ms-pv-2024-idempotence.json`: reexecução e comparação integral dos bytes e IDs.

Prontidão desta extração, integração com o pipeline, publicação nacional e consulta no produto são fatos distintos. As evidências nomeadas registram o que foi efetivamente executado, sem transformar revisão técnica automatizada em revisão pedagógica humana.

## Recibo de texto primário para o gate V2

`ms-pv-2024-primary-text-checks.py` constrói os 681 textos esperados e seus IDs **antes de abrir o sidecar**, usando o inventário primário independente e seu leitor de glifos. Reconfere as 423 células do PDF atual, os 12 cabeçalhos de ano, os 73 cabeçalhos triplos e os três divisores de etapa. As 226 porções de objetos são delimitadas pelos títulos de pilar inequívocos do modelo documental, com contagem de ocorrências validada; nenhum limite vem do texto extraído do adapter.

Depois desse cotejo, calcula SHA-256 dos bytes UTF-8 exatos, sem normalizar acentos ou grafia para o hash. O recibo `data/manifests/uncoded/ms-pv-2024-primary-text-checks.json` contém `expected_item_text_sha256`, 681 `item_checks` e 827 evidências localizáveis. O gate `reconciliation-gate/2.0` aceitou 681/681 e rejeitou tanto uma alteração de palavra quanto uma alteração só de diacrítico. Os grupos documentais são 245 EF-AI, 207 EF-AF e 229 EM. SHA do recibo: `e8a0b14c448fd2e08bc58f5be10c6b883ebdf9ce7c0e874ecdfbc9c36bfd1c9d`.

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/ms-pv-2024-verify.py --primary-text-checks
```

A execução também repetiu os 827 fragmentos, 282 células completas, 80.693 glifos e importador/finalizador 681/681. O sidecar original não mudou. O modelo esperado e a prova V2 estão em `ms-pv-2024-primary-text-model.json` e `ms-pv-2024-primary-text-v2-verification.json`. A frente responsável pelo manifesto integra o recibo somente nos três organizadores; as orientações 1–49/126–127 permanecem pendentes. A comparação no futuro artefato nacional sharded continua aguardando caminho e SHA imutáveis.
