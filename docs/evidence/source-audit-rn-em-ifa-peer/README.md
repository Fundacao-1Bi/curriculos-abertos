# RN EM — peer independente da seção 7.2 IFA

**PASS no recorte**, automatizado, sem revisão pedagógica humana. O peer não aprova as 570 páginas, FGB, RN inteira ou o lançamento nacional.

## Identidade e método

PDF oficial do MF: `data/raw/RN/rn-referencial-oficial.pdf`, SHA256 `5f894abaa0309169597c7c9b7841aebaa9faaeb45e4cb759e5058b359e2ed845`, 5.137.039 bytes/570 páginas. Sidecar: `data/manifests/uncoded/rn-em-ifa-items.json`, SHA256 `c864aa82be21d66613a25b31e23fed253c14bd2ab87c61776447ccdb556255f5`, 618.581 bytes.

O nome inicialmente sugerido `rn-referencial-em.pdf` existe como outro arquivo de SHA diferente. A conferência de pin detectou a ambiguidade antes do censo; **todo o censo, imagens e replay retidos usam exclusivamente o arquivo oficial do MF**. Leituras incidentais da outra cópia não são evidência deste resultado.

`primary-census.py` leu todas as páginas originais 545–558 e escreveu `primary-census.json` antes de abrir registros candidatos/ledger do autor. As expectativas recebidas na tarefa eram conhecidas: o recount é independente, não cego. `audit.py` reconstruiu dois fluxos de células por geometria nativa e comparou cada texto/código ao par correto, sem usar `source_body_native_line_refs` do candidato como oráculo. `independent-cell-census.json` guarda essas 120 unidades.

O primeiro desenvolvimento do checker supôs incorretamente que cada quebra de linha do leitor de glifos seria idêntica à linha de `get_text(dict)`. Uma conjunção isolada por run mostrou a diferença. O teste final compara todo o fragmento da caixa e toda a célula, preservando letras, caixa, pontuação e acentos, normalizando somente whitespace; a cobertura física continua exata. Não houve correção do sidecar nem relaxamento da correspondência código/texto.

## Censo e estrutura

- 14 páginas do recorte, 1.380 linhas nativas em escopo e 14 rodapés físicos preservados como contexto.
- Quatro áreas e um grupo de Formação Técnica e Profissional, quatro eixos por grupo, 20 eixos no total; FTP não é uma quinta área nacional inventada.
- Duas colunas distintas: habilidades associadas às competências gerais e habilidades específicas dos eixos/área. Proximidade de linha não cria equivalência.
- 120 ocorrências documentais, **72 códigos distintos**: CG01–12 repetidos nos cinco grupos e 12 específicos de LGG/CHSA/MAT/CNT/FTP. Não são 120 aprendizagens nacionais únicas.
- 146 nós: raiz da seção, cinco grupos, vinte eixos e120habilidades;145pais, semórfãos/ciclos;275fragmentos.
- As duas colunas e a série dos códigos são conferidas por ocorrência contextual, não por uma regex nacional simples ou deduplicação do código.

`ids-receipt.json` lista146IDsesperados derivados do censo próprio e o conjunto verificado no replay de produção. Ele referencia o SHA do `verification.json` final e serve como recibo de parte, nunca de SourceWhole.

## Continuações e fidelidade

Nove habilidades têm texto em duas páginas: LGG02, LGG06, CG11/LGG11 do grupo Linguagens, CHSA08, CG10/MAT10 do grupo Matemática, CNT03 e CNT08. Além disso, CG01 e MAT01 da Matemática possuem **código na página550 e prosa somente na551**; os dois localizadores permanecem distintos.

As páginas552/553 mantêm MAT07, MAT08, MAT09 e CG08 nas colunas corretas e as duas continuações de CG10/MAT10. A comparação independente abrange todos os120pares, não somente esses exemplos.

Os cinco CG06 das páginas546/549/551/554/557 terminam visivelmente em **“soluções por meio de difere”**. O peer inspecionou seus próprios cinco recortes ampliados, produzidos do PDF pinado; nenhum texto nacional foi usado para completar a frase ou acrescentar pontuação. As outras seis imagens pequenas conferem limites7.1/7.2/7.3 e as passagens matemáticas.

Não se inferem série, ano ou idade da prosa anterior7.1, da ordem das tabelas ou dos códigos. Os grupos e eixos preservam os títulos originais, inclusive variações tipográficas da fonte; os códigos CHSA não foram convertidos em CHS.

## Replay real sem mutação

Executado em memória com `var/venv-pipeline/bin/python`: páginas nativas `sort=True`, leitor de glifos por caixa, `source_uncoded_items`, `finalize_items` e JSON Schema1.1.0 para Source/146Learning. Source clonado com:

```json
{"coded_learning_pages":[545,558],"uncoded_page_sections_pages":[546,557]}
```

Resultado:146registros específicos,275fragmentos conferidos, nenhum código genérico concorrente dentro da autoridade. Foram comparados/preservados os656registros genéricos fora do recorte e os dois contêineres sem código nas páginas545/558. Estes preservam os contextos7.1/7.3 das bordas; não se suprimiu a página inteira por conter parte do adaptador. O estado de literalidade da FGB fora do recorte não foi aprovado por essa comparação de preservação.

Seis negativos foram recusados: códigoMAT08troçado porMAT07; pai deCG08noeixo errado; perda da continuaçãoCG10; perda da prosa551deMAT01; completarCG06comtexto nacional; e a mesma corrupção submetida ao checker de produção. `verification.json` contém execução, hashes e resultados, com recibo visual automatizado e sem reclassificação como humano.

O cache correspondia ao Source real anterior ao binding na hora do replay. O Source **clonado** tem configuração diferente; binding/refresh da configuração real continuam sendo etapa própria da equipe. Não se executaram nova extração, OCR, escrita de MF/sidecar/cache, banco, build ou publicação.

Para reproduzir tecnicamente, `audit.py` escreve um novo resultado técnico com visual pendente; a inspeção das imagens precisa ser executada e identificada separadamente. Preserve os recibos finais pinados antes de repetir qualquer comando que sobrescreva seus arquivos. A única publicação aprovada pelo peer é a identidade documental deste recorte e sidecar, não uma publicação nacional de dados.
