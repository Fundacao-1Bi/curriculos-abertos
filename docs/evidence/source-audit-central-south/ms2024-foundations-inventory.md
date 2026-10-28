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
