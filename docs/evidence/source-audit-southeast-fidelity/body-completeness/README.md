# Integridade dos corpos codificados — quatro complementos de Ensino Médio do ES

A entrega utilizável é **V3**: `v3/integration-proposal.json`, os quatro `data/manifests/uncoded/es-complement-coded-v3-*.json` e o gerador `es-complement-coded-v3-extract.py`. V1 e V2 permanecem como checkpoints históricos: V1 omitia identificadores literais fora da gramática; V2 ainda incluía alguns rótulos do eixo seguinte no corpo anterior. Não integrar os checkpoints como entrega completa.

Foram censadas todas as **561 páginas originais** das quatro fontes, antes da comparação dos corpos com candidatos anteriores. O inventário físico deriva dos glifos nativos, posições de linha, caminhos/regras originais e colunas, sem executar o detector de tabelas/parser completo nem usar as caixas de células esperadas como limites. O confronto posterior usa os registros anteriores apenas para preservar IDs e metadados documentais.

| Fonte | Páginas | Definições de aprendizagem | Referências documentais | Registros finais |
| --- | ---: | ---: | ---: | ---: |
| IFA Linguagens/CHSA | 265 | 131 | 18 | 149 |
| Aprofundamento CHSA | 98 | 260 | 0 | 260 |
| Energias | 102 | 462 | 0 | 462 |
| CHSA + Ciências da Natureza | 96 | 328 | 0 | 328 |
| Total | 561 | 1181 | 18 | 1199 |

As 18 referências IFA contêm **21 menções físicas**: três códigos aparecem duas vezes dentro da mesma célula de Objetos de Conhecimento. São preservadas todas as ocorrências; isso não cria três aprendizagens ou registros duplicados. Os 1.160 IDs codificados anteriores permanecem. Os 39 novos IDs decorrem de âncoras impressas antes não reconhecidas: `EMFICG03` (12), `EMCHSA04` (15), `EMFICHSA09` (11) e `EMIF CG01` (1). A última grafia tem espaço original e partes em dois objetos de texto na mesma linha. Não se corrigem códigos, nem se afirma equivalência com variantes EMIF/BNCC. Identificadores temáticos TI são contexto, não novas habilidades.

O censo genérico independente examinou 1.202 menções físicas de identificadores EM, além de 892 tokens opacos adicionais: temas integradores, referências bibliográficas/URLs e falsos cortes dentro de palavras Unicode. Não restam tokens sem classificação ou identificadores desconhecidos dentro dos campos de aprendizagem. Os detalhes e linhas originais estão em `identifier-syntax-census.json` e `v2/identifier-syntax-closure.json`.

Há 374 diferenças de corpo em relação ao congelado: **39 novos registros e 335 corpos existentes alterados**. Em Energias, 292 corpos diferem: 289 completudes materiais e três diferenças apenas de espaços/glifos da fonte. As páginas com corpos anteriormente truncados são 10, 16, 18, 20, 22, 24, 26, 45, 47, 51, 53, 55, 57, 59, 61, 63, 67, 69, 71, 73, 75 e 77. Outros corpos antigos misturavam identificadores fora da gramática com a habilidade anterior. A V3 separa ainda **21 rótulos de eixo seguintes** (20 em CHSA+CN e um `Eixo IV` na IFA127): cada corte exige que o sufixo removido seja exatamente o cabeçalho fonte comprovado, sem remover prosa.

Na IFA, a revisão prospectiva das 131 âncoras, independente da antiga lista de continuações, prova **11 continuações reais** e rejeita cinco casos de novo cabeçalho. O título `IV. Mundo do Trabalho e Transformação Social` na página149 não continua a habilidade501 da página148. Os doze candidatos históricos foram vistos em renderizações do PDF original. O censo separado das 1.050 âncoras das outras três fontes lê a coluna além do fim dos preenchimentos originais, até a próxima âncora/rodapé: 23 resíduos são números impressos de página; nenhum é prosa de aprendizagem omitida.

Os **46 cabeçalhos literais mistos** e seus **120 vínculos a IDs codificados** estão em `v2/mixed-coded-field-headings.json`; todos passaram também pelo importador real na prova `v3/mixed-heading-import-verification.json`. A proposta inclui III/IV da IFA148/149, Eixo III/IV da IFA127, os dois cabeçalhos completos de Investigação Científica em Energias12/14 e 40 rótulos de eixo CHSA+CN. É proposta de hierarquia para o proprietário consolidar/deduplicar com curso/unidade/ano. Os 16 candidatos restantes são dez cabeçalhos Habilidades e seis trechos de corpo em negrito; as provas e vínculos dos seis corpos estão em `v3/remaining-heading-candidate-classification.json`. Não são novos objetivos.

A prova literal integral usa `source_uncoded_items` e `finalize_items` reais, em RAM e contra o hash dos PDFs originais. A autoridade proposta substitui registros genéricos apenas nas páginas completas enumeradas e inclui todas as referências honestas dessas páginas. Como existe um único `uncoded_items_path` por fonte, **o proprietário deve mesclar estes registros com o seu adaptador de objetivos sem código e hierarquia antes de integrar o manifesto**. Os novos 39 registros não coincidiram com folhas sem código nos dois sidecars do proprietário confrontados (`v2/owner-uncoded-overlap-review.json`, hashes dos snapshots registrados).

As caixas/páginas/excertos são prova técnica automatizada. A ordenação dos glifos por posição preserva a grafia/Unicode original; seis divergências da ordem de pintura nativa permanecem registradas. Na página77 de Energias, sobreposição de tinta entre colunas exige prova por linha física para LGG01. As amostras mostram também cortes/overflow presentes no próprio PDF: não houve reparo por dicionário nem alegação de que todos os glifos embutidos estejam integralmente visíveis como pixels. Os rasters ficam somente em `var/private-evidence/es-coded-body-review/` e a revisão é do agente, sem revisão humana.

Etapas, anos e componentes documentais anteriores são preservados com as suas provas. Para os novos 39, a etapa EM tem declaração explícita da própria fonte; não se deduz série/componente do código. A consolidação de curso, unidade e posição é feita pelo proprietário com as evidências de campos originais. Nenhuma equivalência curricular ou estado readyUF é afirmado.

Comandos principais (a partir da raiz):

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-fidelity/body-completeness/audit_columns.py scan
var/venv-pipeline/bin/python data/manifests/uncoded/es-complement-coded-v3-extract.py build
var/venv-pipeline/bin/python data/manifests/uncoded/es-complement-coded-v3-extract.py verify
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-fidelity/body-completeness/verify_v3_contract.py deterministic
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-fidelity/body-completeness/verify_v3_contract.py authority
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-fidelity/body-completeness/verify_v3_metadata.py
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-fidelity/body-completeness/verify_v3_assignment.py
var/venv-pipeline/bin/python docs/evidence/source-audit-southeast-fidelity/body-completeness/verify_mixed_heading_import.py
```

O gerador V3 consome também o censo de cabeçalhos literal V2, preservado com hash no contrato. O replay determinístico intercepta a gravação em RAM e compara bytes, sem regravar os sidecars. Nenhum PDF, extração de produção, manifesto ou arquivo core foi modificado nesta frente. A adição concorrente de `pipeline/raster_review_scoped.py`, fora dos arquivos carregados no fingerprint do parser, é explicitada no contrato; não se confunde estabilidade da execução comprovada com igualdade global posterior.

**Pendente de integração:** composição dos quatro sidecars com a hierarquia/objetivos sem código do proprietário e pins no manifesto. A auditoria atual cobre os quatro complementos acima. Os outros onze PDFs do baseline ES não receberam nova auditoria integral de corpo nesta subfrente; o antigo fechamento 3655/3655 por fragmentos não basta para afirmar essa completude global.
