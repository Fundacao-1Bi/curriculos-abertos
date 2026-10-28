# Verificação documental independente — Centro-Oeste e Sul

Ator `agent:data_central_south`, tipo `automated`. A amostra visual cobre EI, EF e EM de DF, GO, MT, MS, PR, RS e SC. Há renderizações reais, estrutura observada, hash da imagem e confronto com o cache em `stratified-page-audit.json`. Uma amostra não comprova a completude do documento.

## Achados que exigiram processamento adicional

* DF EI/EF não usa códigos nos objetivos: foram extraídos 2.659 objetivos das colunas oficiais, sendo 653 EI e 2.006 EF, com 127 continuações e nenhum prefixo órfão. O sumário, as colunas e os grupos/anos definem o denominador; `CONTEÚDOS` não entra. `df-adapter-audit.json`, `df-all-fragment-check.json` e `df-sample-selection.json` fixam a prova: 2.785 fragmentos conferidos por palavras e um desacordo de ordem nativa resolvido por renderização da página EF 88. São 91 estratos e 273 amostras de início/meio/fim. A ausência de código oficial é preservada.
* DF EM possui objetivos de Projeto de Vida PV01 etc.; não é todo sem código. A página 39 mostra semestres e dimensões explícitos.
* MT EI: o original contém 93 códigos distintos de objetivos; o cache v1.3 continha 89, omitindo a terceira coluna da página 43 e objetivo na borda da página 57 com texto continuado.
* GO EM: códigos locais `GO-EMLGG101A` etc. não seguem a forma nacional `EM13...`; sua ausência no parser eliminava objetivos. A fonte usa fontes Type3 com caracteres sem Unicode apropriado: o inventário documenta 4.822 ocorrências U+001C e 613 U+001D, além de outros controles. Texto corrompido não é aceito como texto oficial.
* MS EI: espaços no código impresso (`MS.EI01EO00. n. 07`) faziam perder os sufixos e colapsar quatro objetivos novos. MS EF página 155 tem três habilidades reais e o cache v1.3 tinha zero. MS EM página 85 é quadro de seriação com códigos apenas; o cache atribuía listas de outros códigos como texto de habilidades.
* PR EI/EF possui objetivos estaduais sem código além do objetivo nacional em negrito. A frente `pr_adapter` trata o conjunto, preserva ocorrências repetidas no documento e usa o ano explicitado no cabeçalho.
* RS EI página 88 contém nove objetivos: o cache v1.3 tinha duplicações e omitia o sexto objetivo RS. Deduplicar sozinho não recupera a coluna. RS EF Arte declara desdobramentos nos blocos 1–2, 3–5, 6–7 e 8–9; o quadro prevalece sobre o bloco sugerido pelo código nacional. RS EM inclui objetivos locais sem código e posicionamento anual em colunas próprias, tratados em frente independente.
* SC EF tem grande parte das habilidades sem código; cadernos EM incluem objetivos sem código de consulta pública, cursos, unidades e trilhas. Os adaptadores e a auditoria ficam em `../source-audit-sc/`.

Os achados sistemáticos foram enviados à frente de pipeline para corrigir os métodos e reprocessar o conjunto. Os caches v1.3 arquivados neste diretório servem como evidência do problema e não confirmam o comportamento final v1.4.

## MS 2023: bloqueio externo específico

A ementa Projeto de Vida/Núcleo Integrador 2023 v1.0, media oficial WordPress 80798, possui metadado de 63.530.818 bytes e continua vinculada pela página oficial do Novo Ensino Médio. O endereço oficial e a tentativa ordinária `?download=1` devolveram HTTP 200 com a página inicial HTML em lugar de PDF. Isso não comprova causa por CAPTCHA ou WAF, e nenhuma tentativa de contornar controle de acesso foi realizada.

`ms2023-public-media-search.json` registra buscas públicas por Projeto de Vida, Núcleo Integrador e 2023. Uma alternativa oficial, media 56144, foi baixada e inspecionada: é portfólio escolar de 49 páginas de produção de alunos do 7º ano em 2022, não a ementa curricular. Foi excluída do corpus; a classificação e a renderização da página 2 estão registradas. Ela não substitui a fonte faltante. `ms2023-alternatives.json` e `ms2023-media56144-attempt.json` guardam URLs, resultados, hashes e a limitação factual.

Não há declaração de prontidão das sete UFs baseada na simples obtenção de PDFs, contagem de códigos ou amostragem. As partes normativas sem denominador e conferência completos continuam pendentes.
