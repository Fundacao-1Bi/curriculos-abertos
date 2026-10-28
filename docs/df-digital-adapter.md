# DF: objetivos dos volumes digitais II e III

Ator `agent:df_digital`, tipo `automated`. Esta é uma extração documental com conferência automatizada e visual por agente. Não houve revisão pedagógica humana.

O adaptador `data/manifests/uncoded/df-digital-items.json` contém **1.565 registros**: **1.190 objetivos** e **375 nós estruturais**. São 471 registros do Volume II (395 objetivos) e 1.094 do Volume III (795 objetivos). Os dois PDFs oficiais permanecem byte a byte no cache privado original.

Para integrar, associe o mesmo `uncoded_items_path` a `df-competencias-digitais-vol2` e `df-competencias-digitais-vol3`. O importador filtra o array por `source_id`. Não é necessário alterar o pipeline. SHA256 final do array:

```text
eaf5647402002573828836e30af8cd68db419586f3eaba391f0278b9199b58f8
```

## Estrutura preservada

Os quadros imprimem os eixos Pensamento Computacional, Mundo Digital e Cultura Digital. Os objetivos ficam sob o eixo e campo/componente efetivamente impressos. Um mesmo texto em duas colunas continua como duas ocorrências documentais. Essa disposição declara uma relação com o eixo digital; não produz equivalência automática com uma aprendizagem nacional.

Códigos oficiais permanecem nulos. As chaves `key`/`parent_key` são técnicas, escopadas por fonte e localização. A hierarquia inclui volume, quadro quando a legenda existe, faixa ou ano, eixo, campo/componente e unidade temática quando presente. Anos são lidos do cabeçalho `ANO`; ciclo, bloco, faixa e edição não são confundidos. Períodos não declarados ficam nulos.

O Volume II tem quatro aberturas físicas de organizador: páginas 17, 27, 38 e 57. A página 38 repete literalmente a faixa de crianças bem pequenas e não possui legenda `QUADRO`. Essa ocorrência foi preservada com nota de anomalia; não foi inventado Quadro 3 ou outra faixa. No organizador Bebês, páginas 17–26, a fonte imprime quatro campos em cada eixo, sem cabeçalho `Corpo, gestos e movimentos`. A extração não completa um quinto campo por expectativa.

O Volume III tem nove quadros, do 1º ao 9º ano, iniciados nas páginas 19, 31, 41, 50, 67, 82, 100, 113 e 123. Algumas páginas encerram um quadro acima e iniciam outro abaixo: o escopo segue a região geométrica, sem sobrescrever o ano de toda a página. Vinte e cinco rótulos matemáticos nominais, como `Geometria`, `Números` e `Sistemas de numeração`, são nós temáticos e não objetivos fictícios. Células vazias continuam documentadas como vazias.

## Método e evidências

O inventário independente é calculado antes da itemização: quadros e linhas são reconhecidos pela geometria original; as palavras nativas são enumeradas por centro dentro das células. Ele fixa **783 células e 23.977 palavras**. Um segundo verificador lê as coordenadas salvas e exige que cada palavra seja atribuída exatamente uma vez a fragmento de objetivo ou cabeçalho literal. Não utiliza a lista de IDs extraídos como denominador.

Os textos seguem parágrafos impressos, pontuação terminal e início de infinitivo em linha, mantendo cláusulas compostas e listas subordinadas. Isso não cria uma numeração oficial de objetivos. Um objetivo que cruza página tem fragmentos de evidência separados; nenhuma frase é completada editorialmente. Todas as 194 fronteiras foram renderizadas e inspecionadas em dez folhas de contato. As 13 aberturas e os 25 rótulos matemáticos também foram inspecionados.

A normalização canônica preserva todos os hífens visíveis e a pontuação; somente espaços/quebras de linha e o hífen discricionário U+00AD são normalizados. Isso evita transformar `utilizá- lo` e `compreendê- los` em palavras sem o hífen impresso. As evidências conservam cada trecho e sua caixa. A capa rotacionada `VOLUME II/III` usa fragmentos individuais das palavras, preservando sua ordem de leitura apesar da inversão no cache `pdftotext`.

Evidências principais em `docs/evidence/source-audit-df-digital/`:

- `df-digital-independent-inventory.json`: denominador original, cabeçalhos, palavras e caixas.
- `df-digital-whole-word-checks.json`: cobertura exaustiva, sem perda ou dupla atribuição de palavra.
- `df-digital-pipeline-import-verification.json`: importador e finalizador reais, 1.565/1.565 registros e IDs únicos; zero falhas literais, de pontuação, de pais ou de identidade das folhas.
- `df-digital-render-review.json`: autoria, hashes e resultado da inspeção das imagens reais.
- `df-digital-visible-hyphen-preservation.json`: correção transparente de 54 textos canônicos, sem modificar contagens, localizadores, evidências ou posições.
- `df-digital-idempotency.json`: duas extrações completas produziram bytes idênticos.
- `checkpoint.json`: estado, runtime, hashes e próximos passos.

## Reprodução

```sh
.venv/bin/python data/manifests/uncoded/df-digital-extract.py
.venv/bin/python data/manifests/uncoded/df-digital-verify.py
.venv/bin/python data/manifests/uncoded/df-digital-render-review.py
```

O renderizador regenera imagens e marca a inspeção visual como pendente. Ver as imagens e registrar o ator é uma etapa distinta de criá-las. O runtime efetivamente utilizado foi Python 3.9.6 / PyMuPDF 1.26.5, registrado no checkpoint. O módulo real `pipeline/ingest.py` foi utilizado na verificação.

## Escopo restante

A incorporação ao bundle nacional pertence à integração central. Fundamentos, introdução, referências e outras partes fora dos quadros explícitos precisam de reconciliação própria; este adaptador não marca as fontes inteiras nem DF como prontos. Não há bloqueio externo nesta frente. Os comandos, dados e evidências foram entregues, sem editar manifestos centrais, pipeline ou fazer commit.
