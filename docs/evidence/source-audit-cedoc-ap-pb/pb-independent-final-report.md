# Paraíba: comparação independente CEDOC392 × fonte validada635

**Conclusão:** os PDFs compartilham o núcleo regular EI/EF, mas **não são documentos equivalentes nem apenas o mesmo conteúdo reformatado**. O CEDOC392 tem escopo menor, revisões substantivas nos objetivos da EI, alterações editoriais e uma perda visual do símbolo π. Recomenda-se preservar ambos como fontes/versionamentos separados, mantendo intactos o PDF635 e seu sidecar validado de2.008 registros. Não há evidência aqui de vigência ou substituição normativa oficial.

## Execução e identidade

Leitura nativa de todas as635+392 páginas com PyMuPDF1.26.7, mapa lexical bidirecional por página, confronto dos2.008 textos antigos, censo contextual das 15 caixas EI e26 imagens/crops efetivamente examinados pelo agente. Outras10 imagens foram renderizadas e não são declaradas revisadas. O confronto é independente: não importa o extrator principal, não modifica manifestos/pipeline e não utiliza o título ou a contagem de páginas como prova de equivalência.

| Artefato | SHA-256 |
| --- | --- |
| PDF635 validado | `b55786376874ab6a46064c44726d578d37f550a99a702069fe7065946ce26383` |
| CEDOC392 | `af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453` |
| Sidecar2008 preservado | `b64de254205f8d9700baafa3c7efde58808fff6da01398e6c5e7e652f882a514` |

Os três hashes foram novamente conferidos ao fechar a comparação. O [veredito estruturado](pb-independent-final-verdict.json) registra a identidade e os limites.

## Relação de escopo e edição

A capa392 diz expressamente **Educação Infantil e Ensino Fundamental**. As referências a transição para o Ensino Médio no corpo não constituem currículo de EM.

O [mapa documental de seções](pb-independent-scope-crosswalk.json) confronta os sumários e os cabeçalhos físicos. A fonte635 inclui ER EI447–454, ER EJA455–468, Educação Especial484–511, EJA512–525, Campo526–530, Quilombola531–537 e Indígena538–631, além das referências de modalidades632–635. O CEDOC392 termina Ensino Religioso regular365–380 e referências381–390, seguido de páginas sem texto curricular. Esses blocos adicionais não têm seção correspondente na nova cópia. Menções genéricas a diversidade/modalidades ou coincidências de títulos curtos não comprovam cobertura dessas modalidades.

O expediente635p2 nomeia Ricardo Vieira Coutinho e a Secretaria de Estado da Educação;392p3 nomeia João Azevêdo e a Secretaria de Estado da Educação e da Ciência e Tecnologia. Os metadados técnicos são Word04/12/2018 no635 e InDesign01/02/2019 no392. O ano2020 é uma afirmação do catálogo registrada na aquisição; não determina a edição ou vigência do conteúdo. Não foi localizada nesta comparação uma declaração que permita afirmar substituição oficial do635 pelo392.

## Mudanças verificadas nos objetivos e contextos

O [confronto EI por campo e faixa](pb-independent-ei-context-comparison.json) identifica **103 ocorrências antigas e99 novas**, distribuídas em15 caixas em cada documento. Apenas64/103 ocorrências antigas têm texto idêntico no mesmo campo/faixa:

| Faixa explicitada na fonte | Ocorrências635 | Texto idêntico no mesmo contexto392 |
| --- | ---: | ---: |
| Bebês | 31 | 29 |
| Crianças bem pequenas | 39 | 35 |
| Crianças pequenas | 33 | 0 |

A faixa “crianças pequenas” passa a32 objetivos no392:7EO,5CG,3TS,9EF e8ET. O635 repetia nessa faixa diversos textos que também aparecem em faixas anteriores. Isso foi fielmente preservado pelo sidecar antigo e **não deve ser corrigido retroativamente com o novo PDF**.

Exemplos confirmados visualmente:

- EO:635p60 começa “Demonstrar atitudes de cuidado e solidariedade…”;392p61 começa “Demonstrar empatia pelos outros…”, ambos sob cabeçalho de4anos a5anos11meses.
- CG:635p61 traz “Apropriar-se de gestos e movimentos…”;392p63 traz “Criar com o corpo formas diversificadas…”.
- TS:635p62 traz “Criar sons com materiais…”;392p64 traz “Utilizar sons produzidos por materiais…”.
- ET:635p65 traz “Explorar e descrever semelhanças…”;392p66 traz “Estabelecer relações de comparação…”.

Há ainda redações alteradas em direitos de Arte e princípios/direitos de Educação Física. No núcleo das1.594 expectativas EF do sidecar antigo,1.582 textos foram localizados no novo PDF após tratar a intercalação das colunas;12 diferenças textuais foram trianguladas:11 redações de ER e1 lacuna matemática. Essa contagem é de presença textual no componente correspondente; não é aprovação integral de seus posicionamentos anuais.

O392p110 contém cabeçalho literal **“7º Ano”** para LP. O bloco correspondente no635p104(segunda tabela)–106 não tinha cabeçalho legível/nativo e permaneceu com ano desconhecido. A nova evidência serve à nova fonte; não autoriza preencher o ano desconhecido da antiga.

## Códigos e diferenças de diagramação

A [comparação inicial bruta](pb-independent-comparison-summary.json) foi marcada como **superada pela triagem documental**. Os1.701 textos globalmente encontrados não provam igualdade contextual: por exemplo, textos antigos da EI podem reaparecer em outra faixa. Resultados negativos da busca de página inteira não provam remoção.

As35 ausências aparentes de códigos de Matemática eram quebras tipográficas, como `EF­` seguido de `01MA08`. A [verificação tipográfica](pb-independent-code-typography-check.json) encontra o mesmo conjunto de1.231 códigos com formato regular nos dois PDFs, sem diferença de conjunto. Esse procedimento é exploratório: não atribui validade a um código nem repara texto de produção. As três referências de Geografia partidas no635 aparecem inteiras no392. Cada ingestão deve preservar sua grafia, geometria e prova próprias.

Oito ausências aparentes de textos EF (3Ciências e5Geografia) eram intercalações de conteúdos/referências entre partes do objetivo. A [triagem pela primeira coluna física](pb-independent-table-search-triage.json) recuperou todos os oito. Exemplos:392p314 separa duas frases de objetivo em células físicas com referência mesclada;338/339/340 quebram alguns objetivos entre linhas após “Comunidade”, “Sistema” ou “da”. Tais fragmentos não devem virar habilidades autônomas só por haver uma borda horizontal.

**Lacuna material confirmada:**392p280, EF07MA27, imprime “Estabelecer o número” seguido de linha vazia e “como a razão…”. O símboloπ aparece no635p315 e está ausente tanto na extração quanto na renderização do392. Os crops [392](pb-independent-cedoc392-pi-crop.png) e[635](pb-independent-validated635-pi-crop.png) comprovam a diferença. Uma futura extração precisa sinalizar essa lacuna; não deve preencherπ por suposição.

## Recomendação de processamento

1. Registrar CEDOC392 como fonte distinta, somente EI/EF, com SHA e proveniência próprios. Manter o635 e o sidecar 2008 intactos e acessíveis como versão documental separada.
2. Manter o392 fora do aceite de publicação até adaptar suas99 expectativas EI e sua geometria de quadros. Não reutilizar os103 registros EI antigos apenas trocando os localizadores.
3. Recriar evidências de página/caixa, contexto de campo/faixa/ano e código para a nova fonte. Os textos comuns podem apoiar reconciliação rastreável, sem copiar posições ou códigos por similaridade.
4. Preservar as modalidades e ER EI/EJA do635 como partes daquele documento; não contabilizá-las como presentes no392. Qualquer composição de versões no portal deve ser explícita.
5. Tratar códigos partidos, continuações entre células e o glifoπ ausente como regras/alertas documentados. Atribuir o7ºano apenas onde o novo cabeçalho o explicita.
6. Não declarar o392 vigente, sucessor oficial, completo para a UF ou fonte de EM com base nesta comparação. A homologação/edição e a escolha de versão padrão exigem evidência normativa própria.

## Reprodução e evidências

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-cedoc-ap-pb/pb-independent-compare.py
var/venv-pipeline/bin/python docs/evidence/source-audit-cedoc-ap-pb/pb-independent-ei-scope.py
var/venv-pipeline/bin/python docs/evidence/source-audit-cedoc-ap-pb/pb-independent-code-typography.py
var/venv-pipeline/bin/python docs/evidence/source-audit-cedoc-ap-pb/pb-independent-table-triage.py
```

- [Mapa lexical bidirecional de todas as páginas](pb-independent-page-map.json): candidatos localizáveis por cobertura de shingles, sem equivalência semântica automática.
- [Inventário635](pb-independent-validated635-inventory.json) e[inventário392](pb-independent-cedoc392-inventory.json): textos, linhas, caixas, hashes e metadados por página.
- [Concordância dos2008 registros](pb-independent-sidecar-concordance.json): ocorrências exatas globais e candidatos não resolvidos.
- [Amostras visuais, hashes e registro explícito de revisão](pb-independent-visual-comparisons.json).
- [Aquisição/proveniência CEDOC](pb-proposta-ei-ef-cedoc-validation.json), produzida pela frente de aquisição.

**Entregue:** comparação implementada, executada e documentada; arquivos originais preservados. **Pendente fora deste escopo:** adapter/ingestão específica392, reconciliação normativa de edição/vigência, revisão pedagógica humana e eventual publicação. Não houve commit ou alteração de manifesto/pipeline.

## Atualização posterior: extração estruturada executada

O adapter 392foi implementado e auditado em `2026-10-28T15:03:55.320178+00:00`:1.946 registros, zero divergências, SHA`4336a71d0676c2b48f1e363e06f4ef0368c0eba9e2980ff3fc3c79f2865f998b`. Veja o[aceite independente da extração](pb-independent-392-acceptance.md). A pendência de adapter mencionada acima descrevia o momento da comparação inicial; as restrições sobre vigência/versões e a necessidade de evidências de publicação continuam distintas.
