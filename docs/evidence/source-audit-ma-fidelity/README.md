# Maranhão — fidelidade de glifos e células

Frente documental automatizada concluída sobre as duas fontes MA. A proposta foi inspecionada e aplicada pelo proprietário do pipeline; este subagente não editou arquivos centrais. A integração foi executada em ambiente isolado, sem escrever os caches de produção ou publicar candidatos.

| Fonte | SHA-256 | Páginas | Tabelas físicas | Células não vazias | Itens codificados verificados |
|---|---|---:|---:|---:|---:|
| ma-dctm-em-vol2 | ca271258eccee9bf73682267ec680e32ec7fa43bc12216e7c30ea50c77a9dcd9 | 254 | 91 | 1.526 | 49 |
| ma-dctm-ei-ef | 8a1203d9794205738dfaf7ad2b34719d76b21b8559ca042fb498082bdea9af9a | 482 | 293 | 6.152 | 1.883 |

O inventário independente percorreu **736 páginas, 384 tabelas, 7.678 células, 12.803 expansões de ligaduras e 12.912 caracteres com largura zero**. As ocorrências foram enumeradas integralmente, sem usar a lista de registros extraídos como denominador de completude curricular.

## Causa e correção

`table.extract()` ordena caracteres pela geometria. Em ligaduras, PyMuPDF pode apresentar a segunda letra com caixa de largura zero, depois do início da letra seguinte. Na página 157 do volume EM, o `i` expandido da ligadura `fi` fica em x448,91, enquanto o `c` começa em x448,75: a ordenação produz `Identifci ar`, embora o texto nativo e a página exibam `Identificar`.

Um recorte simples de `get_text('text', clip=..., sort=False)` também não é suficiente: no EI/EF ele pode vazar letras sintéticas de uma coluna vizinha, por exemplo `Crianças bem pequenasií`. A solução lê o `rawdict` da **página inteira**, mantém a ordem nativa e vincula os caracteres de avanço zero ao glifo físico anterior. O recorte da célula usa o centro desse glifo base e conserva todos os caracteres do grupo. Nenhuma letra é excluída por ter largura zero; não há dicionário, correção de ortografia, código atribuído ou alias nacional.

API promovida pelo proprietário: `pipeline/native_glyphs.py`, `source_cell_text(source, page, bbox=None)`. A rotação deve ser normalizada antes da leitura. A fonte precisa declarar `native_text_order: "glyph_cluster_stream"`; o pipeline também admite `native_text_order_pages` para escopo documental restrito. `source-metadata-proposal.json` contém as duas fontes, hashes e provas. A configuração e o fingerprint do parser invalidam caches anteriores.

## Verificações executadas

- `ma-full-fidelity-audit.py`: inventário integral das páginas, células, letras expandidas, fontes e caixas; comparação de todos os fragmentos codificados do cache anterior. A análise inicial identificou 907 divergências literais nesses registros.
- `ma-glyph-witness-verification.py`: **7.678/7.678 células concordaram com `get_texttrace()` independente**, sem falhas. As equivalências usadas somente na conferência são ligaduras Unicode e soft hyphen/traço/espaço nominal quando pertencem ao mesmo glifo, font e origem. O texto proposto não é alterado por essa conferência.
- O levantamento completo reteve 1.804 diferenças entre ActualText e Unicode nominal do glifo — pequenas capitais, marcadores e acentos de cabeçalhos, rodapés ou prosa — todas fora das células inventariadas. Também reteve 110 grupos expandidos sem testemunho nominal individual, todos fora das células. Não foi criado mapa global para tentar reescrevê-los; ver `outside-table-actualtext-limitations.json`.
- `ma-isolated-pipeline-probe.py`: executou o **`extract_pdf` real**, com o runtime guard ativo e o escritor redirecionado a artefatos privados. Os **1.932 itens/fragmentos codificados passaram**, sem divergência literal. Códigos, páginas, locadores e caixas permaneceram exatamente iguais ao cache anterior (`code-locator-stability.json`). Os hashes dos caches de produção antes/depois coincidiram. Os nove casos MA indicados pelo responsável do Nordeste passaram.
- Os 11 estratos por combinação de fontes tipográficas e as nove regressões foram visualizados no PDF original. Os PNGs são recortes privados em `var/private-evidence/source-audit-ma-fidelity/`, não páginas redistribuídas.
- Peer check SE: duas células da página 235, verificadas independentemente no PDF, confirmaram `filosófica`, `Identificar` e `con-/flitos`. A prova está em `se235-peer-check.json`; não foram copiados expectedIDs. O trace sem filtro de SE contém texto invisível de template, portanto não foi apresentado como prova de visibilidade integral dessa fonte. O responsável do Nordeste controlou a habilitação nas páginas da grade revisada.

## Limites precisos

O teste isolado pulou OCR explicitamente; ambos os candidatos conservaram `ocr_pending=true`. Isso não bloqueia o resultado de fidelidade das células nativas, mas impede chamar o teste de distribuição completa ou lançamento pronto. Tipologia normativa, referências sem prosa, hierarquia, posicionamento, cobertura de competências, atualidade das fontes e revisão pedagógica continuam sujeitos às respectivas reconciliações. Nenhuma fonte foi marcada pronta por esse subagente. Não houve bloqueio externo de acesso aos PDFs auditados.

Goiás e o portal permaneceram intocados nesta frente. O proprietário do pipeline informou a conclusão posterior do segundo patch GO: 1.454 códigos e 1.458 fragmentos, sem ausências, extras ou falhas literais. Essa integração continua registrada na frente GO original.

## Reprodução

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ma-fidelity/ma-full-fidelity-audit.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ma-fidelity/ma-glyph-witness-verification.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ma-fidelity/ma-isolated-pipeline-probe.py
```

Runtime usado: Python 3.11.15 e PyMuPDF 1.26.7, em `var/venv-pipeline`. O probe lê o código central já aplicado e deve respeitar seu runtime guard; se outro agente editar o parser durante a execução, reinicie após o freeze. Capturas e caches candidatos ficam privados, enquanto hashes, locadores, resultados e trechos necessários permanecem neste diretório.
