# Adaptador de colunas físicas — RS EI e MS EF

Ator automatizado `agent:data_central_south`, com auditoria independente por `agent:df_digital`. Esta frente não declara UF pronta nem reconcilia as partes narrativas das fontes.

`pipeline/rs_ms_geometry.py` trata duas falhas sistemáticas: o reconhecedor de tabelas fragmentava células mescladas RS em linhas repetidas e reconhecia somente o cabeçalho de muitos quadros MS. As ocorrências de identificadores físicos, nas colunas explicitamente intituladas BNCC/RS ou Habilidade(s), dão origem às aprendizagens. Uma cópia artificial de linha não cria nova ocorrência.

O helper conserva os textos e códigos impressos, inclusive as grafias `EI01E003RS-01/02/03`, `MS.EF67EF19.s.1)8`, `MS.EF06LE.00.n.01`, `MS.EF07HI.00.n.04`, o sufixo separado `MS.EF15AR14 .s.14` e os espaços internos de códigos LE. Essas grafias não são reparadas nem transformadas em vínculos BNCC presumidos. O componente e o ano/bloco MS provêm do cabeçalho do quadro; transições dentro da página têm escopos geométricos próprios. Espanhol é o décimo componente EF explicitamente presente na fonte, com cabeçalho singular e códigos LE.

Os campos/idades RS e os quadros MS preservam continuações da coluna antes da próxima âncora. Uma página com quadro de habilidades sem nova âncora ainda pertence ao esquema: citações em Ações Didáticas não se tornam novas definições. Linhas coloridas que atravessam o quadro, como `CAMPO DA VIDA COTIDIANA`, permanecem no contexto. O rodapé é limitado pela caixa do número físico da página; números das aprendizagens não são apagados do texto.

A leitura canônica usa `NativeGlyphText` em ordem do fluxo nativo, com agrupamento de ligaturas e seleção por identidade de bloco/linha mais coordenadas. Isso evita reordenar letras `fi/fl`. Palavras que ultrapassam ligeiramente a borda usam o bloco/linha original. O contexto registra essa condição, pois a fonte pode cortar visualmente uma letra na borda: por exemplo, RS126 imprime `de se`; não se reconstrói `seu` nem se afirma correspondência visual perfeita de glifos ocultos. A seleção não toma a palavra da célula vizinha.

## Contrato de integração

```python
from rs_ms_geometry import handles_source_page, extract_source_cells
if handles_source_page(source, page, physical_page):
    coded_items = extract_source_cells(source, page, physical_page, CODE_ANY, make_item, clean_text)
```

Nessas páginas os registros genéricos codificados são substituídos pelo resultado do helper, mantendo seções documentais e fontes originais. `handles_source_page` pode retornar verdadeiro e a extração retornar zero: trata-se de continuação sem nova definição. O helper não escreve caches nem modifica bytes dos PDFs. A integração ao núcleo pertence à frente de pipeline.

## Provas e reprodução

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-central-south/audit_rs_ms_helper_full.py
```

O script constrói primeiro o censo de identificadores do PDF, sem copiar IDs extraídos. Os denominadores independentes são 340 ocorrências RS (93 BNCC e247 RS) e1.737 MS. Compara ocorrência/página/código/caixa, verifica cada fragmento literalmente e também sua ordem contra o fluxo nativo integral. Os arquivos `*-helper-items.json` são resultados de auditoria; o marcador `rs-ms-helper-full-verification.json` fixa o hash do código efetivamente executado. Não se devem misturar resultados produzidos por revisões diferentes.

A auditoria independente em `../source-audit-rs-ms-independent/` abrange15 estratos RS (cinco campos × três faixas),92 estratos MS (dez componentes e todos os anos/blocos), todas as famílias de código anômalo e casos negativos de citações. A varredura MS de713 regiões de cabeçalho encontrou apenas dois prefixos não vazios sem âncora própria (441 e522), sem uma segunda página de prosa sem âncora. O confronto final deve provar que os dois prefixos foram conservados nas evidências anteriores.

Consulte o marcador final e a auditoria independente para o estado efetivamente verificado. Contagem de âncoras e amostragem visual, isoladamente, não provam completude de todas as partes normativas.

## Verificação integral concluída no candidato congelado

A execução com SHA `f85f208c88957570f85fc6802745fff53b358f58c3c2c46a99e5aec1bee16e4e` produziu340/340ocorrênciasRS e1.737/1.737MS: zero falta/extra, zero falha literal e zero divergência contra a ordem do fluxo nativo em todos os fragmentos. O denominador MS inclui as três definições adicionais `MS. EF69AR24.s.27`, `MS. EF69AR25.s.28` e `MS.F07GE05.s.06`, verificadas nos originais. Esse resultado técnico não equivale à reconciliação de fundamentos, direitos e demais partes narrativas. A incorporação ao núcleo e o confronto final independente são etapas separadas.
