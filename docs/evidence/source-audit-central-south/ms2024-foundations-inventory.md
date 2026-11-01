# MS Projeto de Vida 2024 — partes narrativas ainda pendentes

Inventário automatizado original, sem consultar o adaptador ou seus IDs: páginas 1–49 e 126–127, 51 páginas, 67.025 glifos visíveis. Fonte SHA256 `eff8fcd19d69b1f5d614cbb2ca1599d98e11c697772084b56694a142fecf7048`.

`ms2024-foundations-original-inventory.json` registra as linhas visíveis, coordenadas, blocos nativos, imagens e quadros. O fluxo de glifos por baseline é diagnóstico: **não foi aprovado como ordem canônica de páginas inteiras**. Quarenta e sete páginas diferem na sequência de leitura nativa/visível; dez diferem também no multiconjunto exato de tokens, incluindo união/separação de marcadores de rodapé e palavras. Essas métricas não provam corrupção em todas as páginas. A política de cor preta validada nos quadros curriculares não foi aplicada à abertura colorida.

O sumário original separa apresentação (8), concepção (12), pilares (15), estratégias (24), planejamento/práticas (28), redes de apoio (35), canais (41), etapas de ensino (42), organizadores (50) e referências (126). Os três organizadores já têm outro recibo V2 completo de parte, com 681 registros. As páginas 4 e 127 são arte gráfica, não folhas brancas.

O render de nove páginas confirma uma pendência material na página 30: a figura que relaciona competências gerais da BNCC e pilares é raster e tem texto fora do fluxo de glifos. O original embutido possui 1.422×800 pixels; foi extraído sem alteração para cache privado, com hash e região em `ms2024-foundations-p30-figure-raw-ocr.json`. O OCR real encontrou 292 palavras, com erros e ordem inadequada em múltiplas colunas: **esse texto bruto não foi incluído como transcrição canônica nem prova de reconciliação**. O painel esquerdo é uma reprodução pequena do infográfico de competências gerais e exige revisão por regiões e resolução das partes pouco legíveis. Figuras dos capítulos 15/24 e seus usos como marca de fundo também contêm rótulos que devem ser distinguidos do corpo nativo.

Próximas verificações necessárias:

- Inventariar cada região/figura e determinar ordem de leitura por coluna e caixa, antes de juntar texto.
- Confrontar integralmente os blocos narrativos com glifos visíveis e renders, preservando referências, exemplos e papéis pedagógicos.
- Transcrever os rótulos raster por regiões com prova primária, mantendo as ambiguidades que não puderem ser resolvidas. Não substituir o infográfico por texto presumido da BNCC.
- Tipar contextos/figuras/referências; os códigos citados como exemplos permanecem referências, sem novas habilidades locais.
- Derivar denominadores e hashes dos textos primários, juntar aos 681 organizadores preservados e somente então executar o gate de fonte inteira.

Nenhum input, código do parser, cache nacional ou status de fonte inteira foi alterado nesta investigação. Revisão pedagógica humana e prontidão da UF não foram declaradas.

## Complemento visual — 2026-10-31

A revisão visual de acompanhamento agora cobre todas as 51 páginas do escopo (pp.1–49 e 126–127). A revisão cruzou o PDF original com o inventário fonte-a-fonte e o sidecar de 681 itens, que cobre os três organizadores das pp.50–125 e tem zero registros nas pp.16–49 e 126–127. Evidência reprodutível: `ms2024-followup-visual-review-20261031.json`.

- Pp.35–37 e 42–49 são texto narrativo/orientações docentes; não presumir resultados de aprendizagem dos estudantes. A p.38 tem uma caixa azul com aviso e URL da SED/MS; a p.39 tem outra caixa de aviso e nota de rodapé, cujo corpo não está na linha inventariada e contribui para diferença no multiconjunto de tokens.
- Pp.16–23 são fundamentos pedagógicos (autoconhecimento, emoção, cidadania, comunicação e mundo do trabalho), não parte dos 681 registros dos organizadores. As cinco caixas de exemplo nas pp.17, 19, 21, 22 e 23 citam habilidades de outros currículos de MS, não resultados de aprendizagem deste guia. Após a correção geométrica, todas as caixas estão delimitadas e a saída final preserva cada uma como `referencia_no_documento`, sem rodapé ou texto adjacente. A geometria e o papel final dessas cinco citações estão verificados; o denominador narrativo e a reconciliação SourceWhole continuam pendentes.
- P.41 mostra quatro canais (Telegram, PodVida, Sementes de Vida e WebSed), contatos e o título de um PDF compilado de materiais de 2023. O texto da página não prova que esse compilado seja a ementa do Núcleo Integrador de 2023 que está indisponível.
- P.126 tem 11 referências bibliográficas e não possui registros no sidecar curricular; tipar como referências/contexto ou declarar denominador zero de aprendizagem. P.127 é contracapa geométrica sem texto visível, três imagens, portanto unidade decorativa com zero texto.
- P.10 requer separar o texto de primeiro plano da arte sobreposta; p.6 tem ordem cacheada de palavras quebrada apesar de sequência visual coerente; a citação da p.8 requer revisão do fragmento. A figura raster da p.30 segue com somente OCR bruto (292 palavras) e sem transcrição regional aceita. A cache atual está pinada à configuração p19/p23, mas mantém `ocr_transcription_review_pending=true` e não tem regiões tipadas.

Este complemento fecha a revisão visual registrada para as páginas do escopo, mas não os denominadores narrativos nem a reconciliação SourceWhole. A classificação final das cinco citações externas foi posteriormente verificada como `referencia_no_documento`; a transcrição regional e o recibo V2 continuam pendentes.


### Correção das caixas de exemplos — 2026-10-31

As regras geométricas do manifesto agora delimitam as cinco caixas externas das pp.17, 19, 21, 22 e 23. A cache regenerada com OCR executado contém cada literal uma vez, sem número de página ou texto adjacente. O finalizador os representa como `referencia_no_documento` no conjunto final de 735 itens; o sidecar dos 681 itens dos organizadores não foi alterado. Verificação: `ms-pv-example-callout-geometry-verification.json` (cache SHA `39da3fe328a3828ec8946393b68b18b0e5e5dd2ea75601f40b6fee9533d19c0a`, configuração SHA `807292c26bb89f36408c86de1c385b37ebe7fc9e5b2a147366f7c65ddb573b63`).

Isso corrige os limites e o papel final dessas cinco citações; não fecha a reconciliação documental da fonte. Seguem pendentes o denominador do texto narrativo, as regiões/contextos restantes, a figura raster da p.30, as decisões de leitura das pp.6/8/10, a dependência de 2023 e o recibo V2/runtime atual. O gate isolado continua em 0/27 UFs, com 274 erros ING-03; nenhum recibo, bundle publicado ou default foi atualizado por esta correção.
