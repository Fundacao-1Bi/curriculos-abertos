# CEDOC AP/PB — aquisição, identidade e confronto documental

Capturas em 28/10/2026. Os dois endpoints foram solicitados com o parâmetro literal `?download=0`, sem alteração. Os originais permanecem privados em `data/raw/{UF}/`, ignorados pelo Git. Nenhum arquivo EI/EF foi classificado como EM.

## Aquisição e validação antes da extração

| Artefato | HTTP / Content-Type / assinatura | Páginas | Bytes | SHA-256 |
| --- | --- | ---: | ---: | --- |
| AP CEDOC | 200 / application/pdf / `%PDF-` | 614 | 4.199.170 | `bcf0aa03705580d2f92c7471a68ddf71121748d3407928840f0c9bba402e5c7e` |
| PB CEDOC | 200 / application/pdf / `%PDF-` | 392 | 7.115.062 | `af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453` |

Os seis valores esperados (páginas, bytes e hash de cada arquivo) coincidiram exatamente. PyMuPDF 1.26.7 abriu e percorreu todas as páginas dos dois PDFs, sem erro de página nem reparação automática. Isso comprova aquisição/legibilidade técnica, sem equivaler a cobertura curricular, reconciliação normativa ou vigência.

Os relatórios `ap-rca-ei-ef-cedoc-validation.json` e `pb-proposta-ei-ef-cedoc-validation.json` preservam autoria catalográfica, `catalogPage`, `originalSource` indicada, URL efetiva, data de captura, headers, hash, metadados técnicos do PDF e validação por página em campos separados. As páginas de catálogo também foram capturadas, com HTTP e hash; os HTMLs integrais permanecem privados. O ano 2020 e a licença “Domínio Público” são afirmações do catálogo, sem serem promovidos automaticamente a edição/vigência ou autorização jurídica verificada.

- [Catálogo AP](https://observatoriodeeducacao.institutounibanco.org.br/cedoc/detalhe/tf-referencial-curricular-amapaense-educacao-infantil-e-ensino-fundamental,01847f46-8b77-4a4d-96bb-72eae9fcf44f): autora Secretaria de Estado da Educação do Amapá; fonte indicada MEC; acesso catalográfico em 17/08/2023.
- [Catálogo PB](https://observatoriodeeducacao.institutounibanco.org.br/cedoc/detalhe/tf-proposta-curricular-do-estado-da-paraiba-educacao-infantil-e-ensino-fundamental,39027aab-c324-4c7e-bb44-0cc164c79a01): autora Secretaria da Educação do Estado da Paraíba; fonte indicada Google Drive; acesso catalográfico em 28/08/2023. A página Drive não foi acessível por `web.open`; isso não impediu adquirir e validar o asset CEDOC.

## AP: conteúdo idêntico ao documento MEC de 614 páginas

O PDF MEC já adquirido possui 4.199.175 bytes e hash `23c42348e0b0e00d4135a108366141a257bec54b7b1bff79e521c822d9903f89`. O confronto binário identifica somente cinco letras `s` presentes em namespaces XML `https://` no XMP do MEC e ausentes nos namespaces `http://` do CEDOC. Nenhum outro byte diverge. O arquivo MEC é aberto com `is_repaired=true`; o CEDOC, com `false`; ambos os originais foram preservados.

O confronto percorreu as 614 páginas e encontrou igualdade literal do texto, das palavras e coordenadas, das dimensões e dos streams de conteúdo de cada página. Dez pares de renderizações têm pixels idênticos. Seis imagens foram efetivamente vistas pelo agente (1, 6, 80, 240, 500 e 614), incluindo capa, índice, EI, organizador LP, código local de Ciências e página final. Isso estabelece identidade de conteúdo entre os dois artefatos de 614 páginas; não estabelece equivalência com o livro AP de 339 páginas aprovado em 2019.

`ap-rca-ei-ef-cedoc` está registrado em `north.json` como snapshot alternativo, `include_in_corpus=false`, para não duplicar o mesmo documento. Autoria institucional do catálogo e autor técnico dos metadados Word permanecem separados. Edição/vigência permanecem desconhecidas. O sumário do arquivo abrange introdução, modalidades (Especial/Campo/Quilombola/Indígena/EJA), EI, nove componentes EF, trabalho pedagógico e referências.

Uma extração genérica direta percorreu as 614 páginas, mas o controle de fingerprint rejeitou corretamente a escrita porque os arquivos do parser mudaram durante a execução. Não foi aceito cache de parser misto. O responsável do pipeline recomendou adiar a repetição desse snapshot duplicado até estabilizar o processamento consolidado. A identidade integral por página e o vínculo ao conteúdo MEC já processado estão preservados em `ap-614-mec-cedoc-comparison.json`; não foram fabricados itens com novo hash a partir do cache anterior.

## PB: versão de 392 páginas não substitui automaticamente a de 635

O PDF anterior de 635 páginas e seu adaptador de 2.008 registros permanecem byte a byte intactos. A nova versão possui outra diagramação e ficha institucional: aparecem João Azevêdo e a Secretaria de Educação e Ciência e Tecnologia, enquanto o arquivo anterior cita Ricardo Coutinho. Metadados técnicos indicam Word/dezembro de 2018 no anterior e InDesign/fevereiro de 2019 no CEDOC; essas datas técnicas não são prova de vigência.

O escopo editorial também mudou. O índice CEDOC encerra Ensino Religioso EF e referências, sem os blocos ER na EI/EJA e as modalidades finais que constam no arquivo anterior (Especial, EJA, Campo, Quilombola e Indígena). Isso não autoriza chamar o download de truncado: o arquivo coincide com os 392 fólios anunciados pelo catálogo e precisa ser tratado como artefato editorial distinto.

A auditoria independente identificou alterações reais na EI: 15 caixas contêm 99 objetivos no CEDOC, contra 103 no anterior. Somente 64 ocorrências antigas apresentam texto idêntico no mesmo campo/faixa; nenhuma das 33 ocorrências antigas de crianças pequenas permanece idêntica nesse contexto. A nova faixa apresenta 32 objetivos. A nova versão também apresenta cabeçalho literal de 7º Ano em LP110; ele não autoriza retroatribuir ano ao bloco sem cabeçalho em LP104–106 da versão anterior. Buscar os mesmos textos globalmente é insuficiente, pois expectativas reaparecem em faixas diferentes. Não se pode reutilizar o sidecar apenas trocando números de página.

O conjunto de 1.231 códigos regulares coincide após reconhecer quebras tipográficas documentadas, inclusive U+00AD. Uma comparação ingênua indicava 35 códigos de Matemática ausentes, mas eles existem partidos por quebra de linha. Essa verificação não afirma igualdade de prosa ou de posicionamento nem autoriza corrigir códigos anômalos. Depois de separar problemas de leitura que intercalavam colunas, o confronto identificou 12 diferenças textuais reais entre objetivos regulares comparados: 11 redações de Ensino Religioso e a lacuna de π em Matemática. Direitos de Arte e a EI são examinados separadamente. A auditoria também confirmou uma lacuna visual material em `EF07MA27`: o CEDOC, página 280, omite o símbolo π que aparece no anterior, página 315. O espaço deve ser preservado e sinalizado; não completado por inferência.

O pipeline executou uma extração técnica com 392 páginas, 746 registros candidatos (381 seções documentais e 365 candidatos codificados), 198 tabelas e 2.568 menções a códigos. Esses números não são cobertura de aprendizagens: referências de colunas e objetivos sem código exigem adaptador específico para esta edição/layout. Os dois warnings iniciais são da tentativa de OCR sem caminho do modelo nas capas. OCR direcionado com modelo português explícito foi executado depois: a primeira capa contém título EI/EF e a última apenas arte geométrica, ambas conferidas visualmente. O cache genérico conserva seu histórico `ocr_pending=true`; a evidência complementar está separada, sem alegar reconciliação concluída.

O processamento obrigatório solicitado foi concluído com adaptador próprio de 1.946 registros e auditoria independente sem divergências. O proprietário ligou o novo sidecar em `northeast.json`, com etapas EI/EF e flags de incorporação do snapshot ativadas. A antiga proposta `pb-source-registration-proposal.json` agora espelha o registro efetivo e assinala que foi superada pelo manifesto obrigatório; não mantém a hipótese inicial de fonte opcional. Ver [relatório do adaptador392](pb-cedoc-392-adapter.md), [aceite independente](pb-independent-392-acceptance.md) e [checkpoint](pb-cedoc-392-checkpoint.json). O relatório independente, os mapas por página/contexto, códigos partidos e crops comparativos são arquivos `pb-independent-*` nesta pasta.

## Estado e retomada

- Implementado/executado/verificado: aquisição exata, hashes, headers, assinatura, leitura técnica integral, captura de catálogo, confronto AP por página e confronto PB independente; originais privados e versões anteriores preservadas.
- AP: snapshot alternativo registrado; repetição da extração direta pode ocorrer quando o parser estabilizar, sem duplicar o corpus.
- PB: adaptador próprio de 392 páginas concluído, auditado e ligado ao manifesto real. São 1.946 itens, todas as 1.055 células e 1.689 unidades EF, 99 objetivos EI e suas listas/hierarquia reconciliados. Loader/finalizer reais: 2.478 registros finais da fonte, zero definições genéricas duplicadas e zero posições EM. Reprodução byte a byte aprovada. O corpus consolidado é executado pelo responsável do pipeline; atualidade normativa e cadeia primária permanecem desconhecidas, separadamente do processamento concluído.
- EM: o CAPTCHA da fonte governamental PB e o PDF AP com árvore de páginas danificada permanecem exatamente nas fontes EM anteriores. Nenhum dos dois novos arquivos resolve esses bloqueios.

Comandos executados:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-cedoc-ap-pb/acquire_validate.py
var/venv-pipeline/bin/python docs/evidence/source-audit-cedoc-ap-pb/catalog_capture.py
var/venv-pipeline/bin/python docs/evidence/source-audit-cedoc-ap-pb/ap_compare.py
```

Para o confronto PB, ver os scripts independentes `pb-independent-compare.py`, `pb-independent-ei-scope.py` e `pb-independent-code-typography.py`. `extraction-traceability.json` contém o caminho/hash do cache, revisão/fingerprint/runtime do parser e rastreabilidade dos 746 fragmentos por fonte/página. `preservation-and-stage-checks.json` comprova que o PDF PB635, seu sidecar e o PDF AP EM não foram sobrescritos e que os novos endpoints continuam com `download=0` e etapas EI/EF.
