# Pernambuco — inventário atual do Ensino Médio

Inventário e aquisição executados por `agent:rs_adapter:pe-current-inventory`, ator automatizado. Nenhuma prontidão de UF, reconciliação de aprendizagens ou publicação nacional é declarada.

O [portal oficial](https://portal.educacao.pe.gov.br/ensino-medio/) separa painéis 2026, 2025 e 2022–2024. O primeiro contém 12 organizadores trimestrais FGB, dois Cadernos IFA dos anexos I/II, História de Pernambuco e Atividades Complementares. A área antiga se apresenta como Histórico de Material 2022–2024. Isso identifica a organização do catálogo; não estabelece, sozinho, edição editorial, revogação ou aplicação jurídica de cada PDF.

Foram adquiridos e reconferidos **15 PDFs, 605 páginas**, em cache privado por SHA. Os 12 FGB totalizam 481 páginas; os dois IFA têm 37/45 páginas; Atividades Complementares tem 42 páginas. Os 14 primeiros foram incorporados pela frente Nordeste ao manifesto, com nova conferência de hashes/bytes/páginas. O caderno de Atividades Complementares permanece explícito como tipologia pendente, sem exclusão presumida.

As capas dos 12 FGB foram inspecionadas e não exibem ano editorial. As datas de edição/publicação/aplicação permanecem nulas. O título técnico dos metadados de Língua Portuguesa menciona 2026, guardado apenas como metadado. Os cadernos IFA citam a IN SEE/PE 03/2026 e a Resolução CNE/CEB 4/2025; seus anexos ilustrativos indicam produção assistida por NotebookLM em 18/19 mar 2026. Essas datas pertencem às partes identificadas, sem atribuição automática de uma data ao documento inteiro.

Os FGB distinguem habilidades nacionais, redações locais dos componentes, objetos e articulação com a BNCC Computação. Os códigos de Computação não são novos códigos locais nem prova de equivalência. Arte/Educação Física e outros componentes preservam sufixos próprios, inclusive minúsculos. O inventário registra cabeçalhos explícitos de ano/trimestre; a quantidade de menções a códigos é apenas diagnóstico e não denominador de completude.

O caderno de Atividades Complementares é mais específico que uma simples coleção de exemplos: a página 5 contém duas matrizes em imagem para escolas 35 h/45 h. A matriz 35 h distingue anos para Cultura Digital/Midiática e PTS; a 45 h apresenta os oito componentes nos três anos. A imagem precisa de OCR/transcrição própria: a camada nativa contém somente títulos. A classificação de obrigação e abrangência continua dependendo da conferência do ato/matriz integral, preservando a pendência.

A referência original **IN SEE/PE 03/2026** foi registrada e incorporada ao manifesto Nordeste como `research_pending` obrigatório, com as duas citações oficiais e tentativas verificáveis; o PDF original continua ausente. O frontend público CEPE entregou aplicação Angular; duas consultas GET do serviço público observado retornaram 403. O fallback de navegador local está desativado no ambiente. A pesquisa de mídia e notícias oficiais não localizou o PDF original. Nenhum controle foi contornado, e datas de buscas candidatas não são tratadas como datas de publicação. Texto integral, anexos, possíveis republicações e vigência do ato continuam abertos.

A cadeia governamental até o Google Site usado para o arquivo de Educação Infantil também não foi comprovada nesta investigação. Há referência institucional à existência do currículo EI no volume EF oficial, mas isso não é prova de autenticação daquele arquivo/URL específico. O arquivo EI existente não foi substituído ou duplicado.

Artefatos verificáveis:

- `data/manifests/pe-current-supplement.json`: 14 fontes incorporadas, uma tipologia pendente e uma referência normativa em pesquisa, fora do carregamento automático para evitar IDs duplicados.
- `portal-inventory.json`: hierarquia DOM, painéis e links oficiais, com hash do snapshot privado.
- `acquisition-results.json`, `inventory-validation.json`: origens HTTP, hashes, páginas e conferências dos 15 arquivos.
- `document-part-inventory.json`: componentes, partes, cabeçalhos e candidatos a OCR.
- `northeast-metadata-recheck.json`: confirmação somente-leitura dos 14 registros incorporados.
- `normative-act-attempts.json`, `official-media-search.json`, `official-posts-search.json`: tentativas e limites da busca normativa.
- `visual-scope-observations.json`: locadores e achados da inspeção; os renders/PDFs permanecem em caminhos gitignored.
- `ei-official-chain-search.json`: pesquisa da cadeia EI sem alegar vínculo que não foi encontrado.
- `cedim-official-folder-chain.json`: consulta da pasta pública exata ligada no portal, com único arquivo CEDIM já registrado; datas do Drive não são datas de edição ou adoção.

Comandos executados:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-pe-current/acquire_inventory.py
var/venv-pipeline/bin/python docs/evidence/source-audit-pe-current/build_proposal.py
```

O segundo comando reconstrói a proposta de inventário; não reconstrói os campos de confirmação posterior da integração. PDF e previews estão em `data/raw/PE/`; renders e capturas completas em `var/private-evidence/source-audit-pe-current/`. A integração única no manifesto é da frente Nordeste.
