# PB CEDOC de 392 páginas — adaptador integral próprio

Fonte `pb-proposta-ei-ef-cedoc`, SHA-256 `af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453`. Original privado: `data/raw/PB/pb-proposta-ei-ef-cedoc.pdf`. Asset exato com `?download=0`, catálogo/autoria/origem/data separados e validação HTTP/assinatura/parser estão no README desta pasta e nos relatórios de aquisição. O processamento desta fonte é obrigatório e solicitado pelo usuário; vigência normativa desconhecida não foi usada para impedir sua extração.

## Resultado

O sidecar próprio `data/manifests/uncoded/pb-cedoc-392-items.json` contém **1.946 registros**:

| Tipo documental | Registros |
| --- | ---: |
| Objetivos de aprendizagem sem código próprio | 1.554 |
| Habilidades de Matemática com código literal | 234 |
| Direitos de aprendizagem | 111 |
| Princípios curriculares | 15 |
| Nós de seção/hierarquia | 32 |

O SHA final do sidecar é `4336a71d0676c2b48f1e363e06f4ef0368c0eba9e2980ff3fc3c79f2865f998b`. Contagens de tipos não equivalem a equivalência nacional ou vigência. Os 32 nós compreendem três cabeçalhos etários e 15 campos/organizadores EI, mais os cabeçalhos das listas EF. As seis subseções de direitos EI conservam integralmente título, prosa e citações como unidades documentais de direitos; seus parágrafos docentes não foram convertidos em habilidades.

## Contrato semântico e evidências

Todos os textos, cabeçalhos, caixas, anos, grupos e códigos vêm deste PDF de 392 páginas. Reutilizou-se lógica de geração do adaptador anterior, sem copiar seus textos, coordenadas, posições, modalidades ou dados. O PDF de 635 páginas e seu sidecar de 2.008 registros mantêm seus hashes anteriores. Os blocos de ER EI/EJA e modalidades finais que não constam no novo artefato não foram inseridos nele. Nenhuma etapa EM foi atribuída.

Na EI há 15 quadros/99 objetivos, com suas próprias faixas e campos e pais estruturais. Não se reaproveitaram os 103 objetivos anteriores por troca de páginas: somente 64 ocorrências antigas coincidem no mesmo campo/faixa, e nenhuma das 33 ocorrências antigas de crianças pequenas coincide nesse contexto. A nova versão declara literalmente o 7º Ano em LP110; esse dado não foi retroatribuído ao bloco sem ano da versão anterior.

No EF, objetivos locais de colunas à esquerda permanecem `code:null`; códigos na coluna BNCC tornam-se referências documentais de linha/grupo, nunca identificadores inventados do objetivo nem equivalência pedagógica. A relação admite vários objetivos para um conjunto de referências. Conteúdos, metodologia, radares e gráficos nominais ficam fora do conjunto de objetivos, preservados nas seções documentais centrais.

A unidade documental não é reduzida à célula. Listas explícitas de Inglês/História/ER são separadas por seus marcadores; Matemática é delimitada pelo próprio código terminal. Nos demais componentes, um novo infinitivo no começo de linha física delimita expectativa quando a frase anterior termina em ponto/ponto e vírgula ou quando há separação de parágrafo maior que cinco pontos. Essa regra recupera 60 metas LP e 38 Ciências que compartilhavam células, sem cortar palavras em meio de linha. Metas nominais originalmente declaradas, como “Produção de roteiros...”, também são preservadas. Cinco fragmentos nominais Geo em células adjacentes foram reunidos visualmente porque completam a mesma frase (Andina, Chile, Europa, Colonial e Oceania); não foram apresentados como novas metas.

A reconstrução conserva `source_original_excerpt`, texto semântico, número/marcador da fonte, caixas e ordem. Somente espaços e soft-hyphens discricionários de quebra são tratados como formatação. Nas 37 ocorrências de códigos partidos, `code_original` conserva U+00AD/espaços e `code_formatting_equivalence.method=source_code_soft_hyphen_and_line_wrap` contém a prova. O código normalizado corresponde estritamente a remover U+00AD e whitespace; hard-hyphens e trocas 0/O não são corrigidos. O localizador do código conserva a forma original.

A ausência de π no próprio render de `EF07MA27`, página 280, fica registrada em `documented_source_anomaly`; o símbolo presente na versão de 635 páginas não foi preenchido por inferência. Códigos anômalos e redações da fonte permanecem literais.

## Reconciliação executada

O auditor independente gerou seus denominadores diretamente do original antes do output correspondente e não importou o extrator. No SHA final, passou com zero erros e zero palavras descobertas:

- 1.055/1.055 células físicas, reunidas em 1.050 linhas/grupos após as cinco continuações Geo;
- 1.689/1.689 âncoras individuais EF, incluindo os dois objetivos sem código de Matemática;
- 99 objetivos EI, 15 campos, três cabeçalhos etários e seis seções integrais de direitos EI;
- 120/120 entradas das listas de direitos/princípios EF;
- 3.477 fragmentos nativos, incluindo 1.284 referências; 1.946 textos; 445 cabeçalhos, 1.704 verificações de ano e 1.453 conjuntos de referências.

O selfcheck adicional verificou 2.193 fragmentos nativos, zero falhas, zero diferenças de ordem de palavras e zero pais ausentes. Duas gerações sucessivas produziram bytes idênticos. Amostras visuais estratificadas do auditor estão registradas em seus arquivos; houve revisão automatizada das páginas originais, sem alegação de revisão pedagógica humana.

## Integração e reprodução

Contrato acordado e ligado pelo proprietário de `northeast.json`:

```json
{
  "uncoded_items_path": "data/manifests/uncoded/pb-cedoc-392-items.json",
  "adapter_authority": {
    "generic_coded_reference_pages": [1, 392],
    "coded_learning_pages": [234, 284]
  },
  "include_in_corpus": true,
  "publication_eligible": true
}
```

As flags autorizam incorporar o snapshot processado solicitado; não declaram adoção normativa atual, edição equivalente à anterior, fonte EM ou UF pronta. O carregador/finalizador reais aprovam os 1.946 itens e produzem 2.478 registros finais da fonte, conservando texto/tipo/posição/hierarquia/ordem e prova de código: zero definições genéricas duplicadas e zero posições EM. O teste final `--require-binding` exige a ligação efetiva e não altera o manifesto.

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/pb-cedoc-392-extract.py --layout
var/venv-pipeline/bin/python data/manifests/uncoded/pb-cedoc-392-extract.py
var/venv-pipeline/bin/python data/manifests/uncoded/pb-cedoc-392-selfcheck.py
var/venv-pipeline/bin/python data/manifests/uncoded/pb-cedoc-392-verify.py
var/venv-pipeline/bin/python data/manifests/uncoded/pb-cedoc-392-integration-check.py --require-binding
var/venv-pipeline/bin/python data/manifests/uncoded/pb-cedoc-392-reproduce.py
```

Runtime executado: Python 3.11.15/PyMuPDF 1.26.7. Cache geométrico privado `data/raw/PB/pb-cedoc-392-layout-cache.json`, derivado de tabelas `lines_strict`, palavras e linhas do original. O novo sidecar não depende de arquivos de texto/dados do adaptador635.

Evidências principais nesta pasta: `pb-independent-392-verification-summary.json`, verificador/detalhes independentes, `pb-cedoc-392-selfcheck.json`, `pb-cedoc-392-integration-check.json`, `pb-cedoc-392-reproducibility.json` e checkpoint. A consolidação do corpus pelo pipeline, importação, API/portal e distribuição de produção possuem suas próprias provas. O bloqueio externo do EM PB e o EM AP corrompido continuam em fontes separadas; nenhum novo asset EI/EF os substitui.
