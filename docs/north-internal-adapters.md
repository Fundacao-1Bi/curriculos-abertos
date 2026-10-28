# Norte: partes documentais e integração

Todas as revisões descritas aqui são automáticas, executadas por agentes e verificadores identificados. Não são revisão pedagógica humana nem declaração de vigência. Aquisição, extração técnica, reconciliação por parte e aceite da UF são estados distintos.

## Partes ligadas ao manifesto

- AC EM: `ac-em-pv-items.json`, 158 registros. Os seis quadros do corpo/anexo têm 146 objetivos locais sem código, seis competências próprias e seis seções. A revisão independente conferiu todos os textos, 161 excertos e 2.335 palavras. Os 11 pares de objetivos que diferem entre corpo e anexo continuam distintos. A extração não cobre as outras partes do currículo. O artefato termina no título Anexo 2; não foi presumida uma falha de rede.
- RO EI: 773 registros, com 497 definições, uma referência de legenda e 64 unidades sem código, além da hierarquia documental. Créditos sobrepostos e reconciliação editorial das outras seções permanecem separados.
- RO EM: o pacote atual de 620 registros substitui o pacote inicial de 159 referências. Contém 133 definições por ano explícito, 262 objetivos locais e referências/estrutura. O gerador relacional efetivamente produziu 156 ligações documentais entre índice e definições da mesma fonte, sem órfãos. Não são equivalências ou pré-requisitos.
- RO atos: 42, 32 e 381 registros nativos das portarias/matrizes. Os 11/1/12 recortes raster ainda não estão reconciliados. Artigos e células da matriz não foram classificados como aprendizagens.

Os quatro contextos de posição com formato antes ignorado foram corrigidos. PA112 e AP240 usam cabeçalhos literais e geometria da fonte. O quadro RO120–122 mantém posições individuais por célula, inclusive a coluna de índice sem ano.

## Candidatos ainda sem vínculo

- RR EI: 346 registros dos organizadores físicos 29–99 e legenda 28. São 90 objetivos literalmente codificados, 60 experiências locais sem código, 90 abordagens, 90 orientações, 15 campos/faixas e uma referência de legenda. Os identificadores impressos `E103ET04` e `EI01ET01` sob outra faixa/campo foram preservados. Nenhum texto ausente foi completado com a BNCC. Revisão independente pendente.
- TO EI: 329 registros dos organizadores 54–103. São 93 objetivos, 93 detalhamentos, 93 sugestões de experiências, 30 rótulos de direitos, cinco campos e 15 faixas. Os rótulos de direitos não foram apresentados como definições expandidas. Revisão independente pendente.
- PA EI/EF e AP614 estão sob extração/revisão própria. As propostas somente devem ser vinculadas depois dos respectivos pacotes finais e seus hashes.

## Reprodução

Use `var/venv-pipeline/bin/python`; os originais privados em `data/raw` são necessários.

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/ac-em-pv-extract.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ac-em/pv-integrate.py
var/venv-pipeline/bin/python data/manifests/uncoded/rr-ei-organizers-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/to-ei-organizers-extract.py
var/venv-pipeline/bin/python docs/evidence/north-apply-proposal.py docs/evidence/source-audit-ro/ro-rcem-lgg-proposed-source-fields.json
```

Os candidatos RR/TO reconstruíram os mesmos bytes. O aplicador serial recusa propostas marcadas `binding_ready:false`, valida hashes e executa o loader/finalizer/schema antes de alterar o manifesto. Lê novamente o manifesto antes da gravação para preservar os campos de outras frentes.

Os PNGs primários AM foram transferidos sem perda para `var/private-evidence`; o inventário old/new/SHA está em `source-audit-am-sections/primary-assets-relocation.json`. AP tem inventário equivalente. Imagens e PDFs não foram presumidos redistribuíveis.
