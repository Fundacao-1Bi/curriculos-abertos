# Auditoria independente PB EI/EF

Resultado técnico: **passou**, com zero divergências e zero células com palavras descobertas no adaptador de 2.008 registros. Execução final: `2026-10-28T14:00:02.526393+00:00`. Esta conclusão se limita ao adaptador e ao artefato especificados; não aprova a UF como completa, não comprova distribuição e não substitui revisão pedagógica humana.

## Identidade e independência

- Fonte: `pb-proposta-ei-ef`, PDF oficial adquirido em `data/raw/PB/pb-proposta-ei-ef.pdf`, 635 páginas físicas.
- SHA-256 do PDF: `b55786376874ab6a46064c44726d578d37f550a99a702069fe7065946ce26383`.
- Adaptador auditado: `data/manifests/uncoded/pb-eief-items.json`.
- SHA-256 do adaptador: `b64de254205f8d9700baafa3c7efde58808fff6da01398e6c5e7e652f882a514`.
- Runtime executado: `var/venv-pipeline/bin/python`, PyMuPDF `1.26.7`.
- Auditor: agente separado `/root/data_north/pb_independent`; denominadores gerados diretamente das palavras, desenhos e tabelas do PDF, sem importar o extrator principal. Inventários EI, células e modalidades foram fechados antes do confronto com os registros correspondentes. A descoberta posterior de direitos de Arte e objetivos gerais EJA também partiu da fonte literal.
- O verificador lê um snapshot e rejeita mudança do sidecar durante a execução. A coleta de palavras é novamente realizada no PDF, usando centros geométricos e caixas físicas. O cache de palavras existe somente na execução atual.

## Denominadores documentais

As contagens abaixo descrevem grãos diferentes e **não devem ser somadas** como cobertura.

| Denominador independente | Esperado | Representado |
| --- | ---: | ---: |
| Objetivos EI em 15 caixas preenchidas, 3 faixas/5 campos | 103 | 103 |
| Células físicas não vazias nas colunas de objetivos/aprendizagens EI/EF/EJA | 1.157 | 1.157 |
| Âncoras individuais explícitas de lista/código, evitando objetivos colapsados | 823 | 823 |
| Objetivos, competências e critérios da Educação Escolar Indígena | 138 | 138 |
| Direitos de aprendizagem e princípios curriculares | 34 | 34 |
| Objetivos gerais EJA explicitamente rotulados | 3 | 3 |

O inventário geométrico cobre todas as 635 páginas, com 291 tabelas estritas em 230 páginas e zero falhas de leitura. O recorte de colunas de aprendizagem examinou 281 tabelas. Seis falsos quadros de radar em Dança/Música/Teatro foram excluídos explicitamente; não são objetivos. As 1.157 células são ocorrências físicas e podem conter vários objetivos ou somente uma continuação. Doze células vazias no topo de página foram conservadas separadamente para contexto; onze contêm continuação real de referências. Não entram no denominador de células de aprendizagem.

O censo de continuidade registra 115 candidatos geométricos e 38 ligações documentadas: 27 ligações com texto de objetivos e 11 que continuam apenas referências/conteúdos na página seguinte. Grupos de linhas fornecem referências documentais aos objetivos separados; não afirmam equivalência ou identidade com a BNCC.

As 823 âncoras individuais incluem 284 marcadores em Inglês, 234 códigos literais próprios em Matemática, 177 marcadores em História, 34 em ER EF, 33 em ER EI e 61 em ER EJA. O caso sem marcador em ER440 foi incluído como ocorrência explícita de parágrafo. A lista indígena contém 63 objetivos, 54 competências e 21 critérios; os 42 nós estruturais adicionais foram verificados por seus fragmentos literais e pais, totalizando os 180 registros indígenas presentes no sidecar. As duas expectativas narrativas indígenas foram conservadas porque a própria fonte as chama de objetivos.

## Verificação executada

- 3,532 verificações de fragmento nativo por página/caixa, incluindo 1,245 fragmentos de referência e localizadores de códigos. A repetição de uma caixa para o localizador de código não amplia cobertura.
- 2,008 textos confrontados com os fragmentos semânticos e, separadamente, com os fragmentos originais do PDF; somente espaços, marcadores de lista declarados e o código próprio delimitado podem ser retirados.
- 397 cabeçalhos distintos confrontados com o texto nativo; 103 posições EI conferidas contra os campos e as faixas do denominador independente.
- 1,560 posições com ano conferidas contra cabeçalho literal e sua ordem física.
- 1,452 conjuntos de referências confrontados com células/grupos inventariados independentemente; códigos da coluna BNCC permanecem referências, sem promoção a código local.
- Todas as chaves são únicas e todos os pais existem. O componente de cada célula coberta corresponde ao seu escopo documental. Não há códigos locais inventados na EI.
- 21 páginas renderizadas e examinadas visualmente pelo agente automatizado: 48, 49, 50, 52, 54, 60, 65, 84, 139, 192, 221, 265, 310, 344, 376, 413, 435, 451, 459, 588 e 622. Matrizes, faixas EI, nove componentes EF, ER EI/EJA, modalidades, códigos próprios, referências e mudanças de contexto na mesma página estão representados. A evidência visual não é revisão humana.

## Achados materiais reconciliados

1. Foram encontradas 22 omissões de objetivos LP em linhas com células de conteúdo/referência mescladas verticalmente. O produtor corrigiu o critério de cabeçalho para usar largura física real e coletou referências das células que sobrepõem cada objetivo.
2. Cabeçalhos LP de ano sem ordinal foram reconhecidos por formato estrito. O segundo organizador em LP104 não exibe ano no PDF; as páginas seguintes desse bloco preservam ano desconhecido, sem inferir o 7º ano por lacuna ou por códigos BNCC.
3. Continuidade física História/ER e células vazias de LP foram reconciliadas sem concatenar objetivos separados. A numeração duplicada da própria fonte foi mantida.
4. Três omissões reais de referências foram detectadas e corrigidas: EF35LP06 em LP98, EF07CI03 em Ciências346 e EF08CI06 em Ciências348. A linha nativa misturava palavras das colunas de conteúdo e referência; a seleção final usa palavras contidas na célula de referência.
5. Em Matemática310, “Frações.” permanece conteúdo da coluna vizinha; não vira descrição de EF06MA07. Os 234 códigos locais de Matemática permanecem ancorados ao próprio texto anterior ao código.
6. Direitos de Arte fora das tabelas foram incluídos: Visuais135–136 (10), Dança152 (4), Música163 (4), Teatro173 (4). Seis direitos e seis princípios da Educação Física185–186 foram conferidos separadamente. EJA458–459/460/463 contém três objetivos gerais; não foi fabricado um quarto.
7. O marcador literal `3--` em EJA459 é preservado no fragmento original; sua pontuação de lista foi removida do texto sem alterar palavras. Fragmentos semânticos e originais são verificados separadamente.
8. Irregularidades da fonte, como `EF12LPO1`, `EF697P06`, `EF01HI0` e `EF39AR33`, não foram corrigidas por suposição. Os fragmentos partidos `(EF04GE 08/10/11)` permanecem evidência literal; o auditor não junta partes para inventar códigos completos nem trata o prefixo incompleto EF04GE como código.

## Reprodução e evidências

Confronto integral do sidecar final:

```sh
var/venv-pipeline/bin/python data/manifests/uncoded/pb-eief-verify.py
```

Os scripts `pb-independent-inventory.py`, `pb-independent-ei.py`, `pb-independent-cells.py`, `pb-independent-row-groups.py`, `pb-independent-indigenous.py`, `pb-independent-rights.py`, `pb-independent-eja-general.py` e `pb-independent-unit-anchors.py`, nesta pasta, regeneram os denominadores a partir da fonte e do inventário físico. O confronto não importa o extrator que está auditando.

- [Resumo verificável](pb-independent-verification-summary.json)
- [Todos os confrontos, células, âncoras e referências](pb-independent-all-fragment-results.json)
- [Inventário físico integral](pb-independent-physical-inventory.json)
- [Denominador das células](pb-independent-cell-denominator.json)
- [Continuidade e grupos de linhas](pb-independent-row-groups.json)
- [Amostras visuais e hashes](pb-independent-visual-samples.json)

## Limites e pendências

Não há divergência técnica pendente no snapshot acima. A auditoria abrange o PDF EI/EF adquirido e as expectativas explícitas nele identificadas, incluindo ER EI/EJA e organizadores indígenas. A leitura geométrica e literal de 635 páginas não converte todo parágrafo teórico, instrução docente, conteúdo nominal ou avaliação exemplificativa em habilidade. Contextos e trechos excluídos estão registrados nos inventários.

Revisão pedagógica humana permanece não realizada. O Ensino Médio da Paraíba e seu bloqueio externo pertencem à aquisição/fonte correspondente, fora deste sidecar. Vigência normativa, completude da UF no produto, reconciliação de documentos complementares, incorporação no bundle, API, portal e distribuição de produção exigem suas próprias evidências e não são declarados concluídos por este relatório.
