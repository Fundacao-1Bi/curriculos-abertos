# Acre — extração integral de objetivos e capacidades (EI/EF)

Responsável: subagente real `portal`, atuando nesta frente documental. Todo o trabalho de revisão descrito aqui é automatizado por IA e por verificações determinísticas; não constitui revisão pedagógica humana nem homologação institucional. O passe de inventário independente usa outro caminho de código e a fonte original antes de ler o sidecar. Ele foi executado pelo mesmo agente; a auditoria final distinta continua a cargo da coordenação.

## Fonte e escopo

Fonte `ac-cru-ei-ef`, PDF real de 1.714 páginas, SHA-256 `cbcd7249582d043ad893416c3c2fc0c8cb5056aee6f0e89eceb212aed680bf33`. Emissor e URLs estão em `data/manifests/north.json`. A condição de redistribuição do PDF não foi estabelecida: as imagens nesta pasta são evidências locais de conferência; direitos de terceiros permanecem próprios, separados da licença do código.

O adaptador percorre a fonte integral e estrutura: objetivos codificados da EI; direitos por campo e grupo; aprendizagens específicas locais sob os respectivos objetivos; primeira coluna Objetivos/Capacidades dos quadros do EF; direitos/objetivos organizados por ano ou bloco nas aberturas dos componentes. Conteúdos, sugestões de experiências, propostas de atividades e avaliação não são concatenados à redação de capacidades. Essas partes continuam preservadas no texto documental do pipeline central e exigem reconciliação própria conforme sua tipologia.

## Resultado executado

| Tipo | Itens reais |
| --- | ---: |
| Objetivos de aprendizagem e desenvolvimento da EI, com código original | 93 |
| Aprendizagens específicas da EI, sem código oficial | 548 |
| Direitos de aprendizagem da EI (5 campos × 3 grupos × 6 direitos) | 90 |
| Capacidades na coluna Objetivos do EF | 825 |
| Direitos/objetivos do EF por ano ou bloco, incluindo 13 parágrafos sem marcador | 635 |
| Total de ocorrências documentais estruturadas | 2.191 |

O total descreve ocorrências da fonte, não aprendizagens semanticamente únicas ou qualidade curricular. Há 2.373 fragmentos de evidência e 548 vínculos hierárquicos locais entre aprendizagens específicas e seus objetivos da EI. Os 93 objetivos são os efetivamente presentes nesta edição consultada; não foi adicionada uma lista nacional para completar uma quantidade presumida.

Os seis códigos nativos `EIO2EF03`, `EIO2EF04`, `EIO2EF08`, `EIO3EF03`, `EIO3EF04` e `EIO3EF08` conservam a letra O que consta da extração da fonte. Nenhuma substituição automática por zero nem equivalência nacional foi declarada. Filhos locais continuam com `code: null`; os IDs são técnicos e escopados.

## Denominador independente e verificações

- O sumário das primeiras 17 páginas define **148 quadros**: Arte 35; Ciências 9; Educação Física 51; Ensino Religioso 9; Espanhol 4; Geografia 9; História 9; Inglês 4; Matemática 9; Português 9. Todas as 148 aberturas foram localizadas na página física correspondente. Nenhuma abertura faltando ou excedente.
- Uma segunda leitura de marcadores nativos e bordas de coluna constrói as âncoras esperadas antes de abrir o sidecar: 2.098 inícios sem código e 93 objetivos codificados. Os 17 parágrafos sem marcador foram inventariados por prefixos literais e localização próprios: quatro na EI, quatro em Inglês 8º, oito em Português 3º/5º e um em Geografia 5º.
- Resultado: **2.191 âncoras esperadas e 2.191 correspondentes**, zero omissões, zero itens excedentes. A estratificação por parte, componente/campo, ano ou grupo é salva em `independent-reconciliation.json` e nos inventários de âncoras/contextos.
- **2.373/2.373 fragmentos** conferidos contra palavras nativas inteiramente contidas em seus retângulos, nos dois sentidos, preservando pontuação e grafia. A comparação usa palavras inteiras: recortes de glyphs de descendentes de uma linha vizinha podem aparecer em `get_text(clip=...)` e não representam palavras não atribuídas.
- **951/951 páginas de evidência** tiveram a numeração impressa conferida literalmente na região do rodapé. Nenhum número impresso foi deduzido apenas por uma fórmula sem conferência.
- Nenhuma palavra da coluna Objetivos foi encontrada além do limite inferior de corte utilizado. As duas páginas em que o título de um novo quadro inicia ao fim da página foram tratadas como intervalos separados: finais do quadro anterior preservados e cabeçalho continuado na página seguinte.
- Reexecução completa preservou todos os payloads e IDs; quando o conteúdo não muda, `generated_at` é preservado para manter o checksum do sidecar e evitar invalidação artificial do cache.
- O contrato real do pipeline `page-cell-v1.4.0` recebeu os 2.191 itens, executou `source_uncoded_items`/`evidence_check`/`finalize_items` e confirmou 548 pais resolvidos, zero pais inexistentes e IDs únicos. Não foram usadas fixtures.
- Conferência visual de **25 amostras**: 15 estratos da EI (cinco campos nos três grupos etários) e dez componentes do EF. As imagens, IDs selecionados, redações e verificações estão em `visual-samples.json`. A conferência de amostras não foi apresentada como revisão visual de todas as páginas.

Problemas encontrados e corrigidos sistematicamente: menções em prosa a Quadro Organizador confundidas com títulos; cabeçalhos na página seguinte; continuações acima de um novo título na mesma página; sugestões de experiências no singular; 17 parágrafos normativos sem bullet; e o título `4.2 Anos finais` sem ponto final, que poderia anexar narrativa ao objetivo anterior. O diagnóstico de parágrafos remanescentes e os resultados de borda estão preservados junto às evidências.

## Contexto documental adicional e composição atual

O sidecar de aprendizagem continua com 2.191 itens, SHA-256 `6309ec0a74b6b8ddb63b6c07ec59ad15f165bd0c7f07e19067ff2a075def3886`. O manifesto agora aponta `uncoded_items_path` para o composto `data/manifests/uncoded/ac-source-items.json`, SHA-256 `7d81517fc115dc60deb667fdf8f9ec5650f39afd8b041598bf8d3d7b17d502c7`: os 2.191 itens originais, byte a byte, mais dois fragmentos contextuais curtos das pp.625 e 830. Eles estão em `kind=secao_normativa`, sem código, ano ou tipagem de aprendizagem; qualquer etapa/componente finalizado vem apenas da faixa de seção já mapeada no manifesto.

- p.625: continuação de uma célula de avaliação do quadro de Ginásticas, 8º ano de Educação Física: `identificá-los no contexto em que os alunos vivem, dentro e fora da escola.`
- p.830: bullet na coluna de conteúdos da tabela de Espanhol, continuação de p.829–831: `Respeito às diferenças.` A ocorrência da p.830 foi mantida mesmo com repetição literal na página anterior porque é uma localização física distinta.

O gerador `data/manifests/uncoded/ac-compose-source-items.py` valida o SHA do PDF, o SHA do sidecar-base e a literalidade de ambos os fragmentos antes de escrever o composto. A cache v1.5 foi reextraída após a troca do `uncoded_items_path`; a auditoria atual conta 3.885 itens finais com zero falhas literais. Isso preserva contexto curto, mas não substitui o inventário documental integral nem torna a fonte pronta.

## Arquivos e reprodução

Sidecar-base de aprendizagem: `data/manifests/uncoded/ac-objectives-items.json` (2.191 itens). SHA-256: `6309ec0a74b6b8ddb63b6c07ec59ad15f165bd0c7f07e19067ff2a075def3886`. O consumidor do pipeline usa o sidecar composto `ac-source-items.json` descrito acima.

```sh
# Python 3.11.15 e PyMuPDF 1.26.7 preparados no ambiente
var/venv-pipeline/bin/python data/manifests/uncoded/ac-extract-objectives.py --render-samples
var/venv-pipeline/bin/python data/manifests/uncoded/ac-independent-inventory.py
# Após regenerar a sidecar-base, compor e validar os fragmentos contextuais.
var/venv-pipeline/bin/python data/manifests/uncoded/ac-compose-source-items.py
# Apenas repetir conferência de fragmentos já extraídos
var/venv-pipeline/bin/python data/manifests/uncoded/ac-extract-objectives.py --validate-only
```

Os comandos retornam código diferente de zero quando as suas verificações falham. A geração não modifica o manifesto North nem o pipeline central. O responsável North vinculou `uncoded_items_path`; a coordenação/pipeline trata a autoridade do sidecar sobre os pais codificados da EI para não duplicar a extração genérica.

## Situação e retomada

**Implementado, executado e verificado:** a extração integral das colunas de objetivos/capacidades e dos recortes normativos acima, com proveniência, hierarquia, denominador independente e conferência técnica. Não há bloqueio externo nesta frente.

**Não equivale a fonte ou UF pronta:** o recibo SourceWhole V2 instalado localmente reconcilia o documento fixado, incluindo páginas preliminares agrupadas sob `Texto introdutório` somente como contexto documental, sem alegar pertencimento curricular. Edição, vigência, aplicabilidade atual, aprovação pedagógica e prontidão da UF continuam sem comprovação. `source_ready` permanece falso no relatório independente de âncoras; o passe de aprendizagem e o recibo técnico não substituem aprovação atual da fonte inteira. A publicação nacional e as jornadas API/MCP/portal do snapshot integrado devem ser verificadas pela coordenação após a carga deste sidecar.

Checkpoint: não reimplementar este adaptador nem substituir os registros por páginas genéricas. Reutilizar os arquivos, checksums e inventários existentes; alterações de fonte devem gerar reprocessamento identificável. O portal não foi alterado durante esta frente.
