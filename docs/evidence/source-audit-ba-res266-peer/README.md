# Peer independente — Resolução CEE/BA 266/2025 e Parecer 365/2025

Revisão automatizada do artefato primário selecionado, não revisão pedagógica humana nem verificação jurídica externa de vigência. Nenhum Source, sidecar, parser, schema imutável ou banco foi alterado pelo peer. As alterações de classificação documental foram autorizadas separadamente por Root e estão em `policy-v5-decisions.json`.

## Pins e execução

- PDF primário: `data/raw/BA/ba-resolucao-266-2025-computacao.pdf`, SHA256 `dae336de6d45da873386a66f01de53a483c790b502254c5faef3def5d5f00e17`, 856.939 bytes, 21 páginas.
- Sidecar final: `data/manifests/uncoded/ba-resolucao-266-items.json`, SHA256 `3f9ec0e5bd173ec311bf576116a6b1a645c085a3a5803f53d75dc83c50f25f12`, 668.003 bytes.
- Censo anterior do produtor: `docs/evidence/source-audit-northeast/ba-res266-source-only-inventory.json`, SHA256 `b36d6db94578e9477ca3a7ac979b56a37b6e360e8a811a59d319e54d629feb27`.
- Censo próprio: `primary-census.json`, escrito antes de abrir os registros candidatos dentro do verificador; `primary-lines.json` guarda texto e caixas das linhas nativas. O pacote/denominador do produtor já era conhecido: a conferência é independente, não cega.

Reexecução técnica (sem extração, OCR, escrita de Source/sidecar ou banco):

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ba-res266-peer/audit.py --skip-render --visual-reviewed
```

`--visual-reviewed` registra a revisão visual **já executada pelo peer** nas quatro imagens de página e no recorte da tabela. Não substitui essa inspeção para um novo artefato. `verification.json` contém o resultado, os controles negativos, hashes de runtime e limites; `execution.log` preserva a execução final. O verificador usa cache nativo existente, substitui em memória seus textos de página pelos `get_text(sort=True)` primários, chama o loader/finalizer de produção e valida Source/141 Learning contra o schema 1.1.0 fixado.

## Denominadores e papéis

Foram confrontadas todas as 688 linhas não vazias do corpo, exatamente uma vez, e os 21 numerais físicos de rodapé. São 123 nós da resolução e 18 do Parecer, total 141, com 155 fragmentos: 21 artigos, 17 parágrafos, 57 incisos (49 `inciso_normativo` e oito `postulacao_curricular` do art. 10), quatro capítulos, duas seções, quatro subseções, onze referências preambulares; Parecer completo, sete campos de cabeçalho, três seções, notas nas páginas 15/16, tabela de duas linhas por duas colunas, legenda Fonte, data e assinatura. A comparação geométrica própria não usa os `source_native_line_refs` do candidato como oráculo.

A ordem é confrontada com a primeira ocorrência nativa de cada unidade; pais, ciclos, tipos documentais e etapas são verificados contra a estrutura primária. EI: arts. 9–10; EF: 11–12, com rótulos Anos Iniciais/Finais preservados; EM: 13–14. Nos demais nós, o contexto de etapas do documento não é alegação de aplicabilidade de cada cláusula a toda etapa. Não se inventam anos/idades/códigos.

As oito postulações do art. 10 são disposições jurídico-curriculares para a proposta pedagógica EI, não automaticamente oito resultados individuais ou códigos BNCC. As citações nacionais/acadêmicas do Parecer não viram definições locais. A tabela p. 16 é ilustração histórica do Programa Mais Educação: **não tem cabeçalhos impressos das colunas**; “Fonte” fica abaixo, não é cabeçalho. As descrições de colunas agora são explicitamente editoriais (`table_columns_descriptive_not_printed`, `printed_table_column_headers_present=false`).

O ato é datado/aprovado em 21/10/2025; a homologação impressa é 24/03/2026 e a publicação 26/03/2026. O art. 21 remete a vigência à publicação; o art. 20 fixa prazo de um ano para inserção curricular/plano de formação. São papéis diferentes. Erros bibliográficos impressos, como Lei 14.553 no relatório, “13 de janeiro” e 14.533/2024 na fundamentação, permanecem literais; não foram corrigidos silenciosamente nem certificados como fatos jurídicos externos. A legenda remete a referências finais, mas o PDF selecionado termina em assinaturas na página 21; nenhuma bibliografia ausente foi inventada.

## Trace e revisão visual

Os 155 fragmentos foram comparados ao trace de glifos das caixas, preservando pontuação/números e ignorando apenas espaços, com **duas exceções específicas documentadas**: o trace inclui dois glifos Symbol/U+F0B7, glyph ID 120, nas linhas da tabela p. 16. Eles estão ausentes do texto nativo e do recorte renderizado de alta resolução. As caixas e a inspeção estão em `verification.json`/`primary-table-crop.png`. A causa exata de renderização/clipping não foi isolada e não é afirmada. Não foi introduzida regra genérica de remoção de PUA nem modificado qualquer texto/código do candidato.

Foram inspecionadas visualmente as páginas 7 (oito postulações), 12 (datas/vigência), 13 (cabeçalho físico do Parecer) e 16 (tabela/notas/Fonte), com imagens pequenas. O recorte da tabela separa os rótulos de coluna inexistentes da legenda de fonte física.

## Controles e repin

Onze corrupções são recusadas: remoção do inciso VIII do art. 10; corrupção textual desse inciso e do último inciso do art. 17; pai incorreto; etapa errada; aprovação substituída pela data de vigência; troca homologação/publicação; Fonte anexada ao relatório; postulação e argumentação promovidas indevidamente a aprendizagem; último inciso deslocado para antes da ordem primária.

O primeiro peer pinou `d5c589d18aa686b57b8db39c2b352de58989efc3c906a47e2374e39d0fe13d82` (667.849 bytes). O produtor alterou somente as duas chaves de metadados de coluna descritas acima. `metadata-only-repin.json` prova que reverter **apenas** essas mudanças reconstrói exatamente os bytes e SHA anteriores; todos os textos, tipos, códigos, pais, ordens, posições e evidências permanecem iguais. O resultado anterior está preservado em `verification-before-descriptive-columns.json`; o verificador foi reexecutado com o pin final.

## Limites e próximos passos

A identidade do cache antigo não coincide com a configuração atual do Source. O import em memória com Source clonado comprova o candidato, **não** é preflight da configuração real depois do binding. Root/NE precisam fazer o binding autorizado e executar a verificação dessa configuração. O peer abrange somente as 21 páginas do artefato fixado; não prova a completude dos demais atos/documentos obrigatórios BA, da UF ou do país. Também não altera a publicação padrão nem certifica direitos de redistribuição de elementos gráficos/terceiros do PDF.
