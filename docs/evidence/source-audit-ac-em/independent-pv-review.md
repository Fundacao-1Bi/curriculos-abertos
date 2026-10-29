# Revisão independente — AC EM Projeto de Vida e Pós-Médio

Fonte primária imutável `ac-cru-em`,459 páginas físicas, SHA256 `9ff75d1d5d9397aa145dccedd8023a01ed3b862692f58bb7d2cb2c84fc7602ad`. Recorte integral desta revisão: páginas físicas61–73 e452–459. As páginas impressas observadas são as físicas menos3. O sumário não foi usado para localizar quadros.

O denominador foi produzido diretamente dos marcadores e linhas nativas das colunas físicas, antes da leitura do sidecar candidato. Nenhum arquivo do censo do implementador, pipeline ou saída de extração foi usado como esperado. Depois de congelado o denominador, a comparação leu o sidecar apenas como candidato.

| Parte física | Série explícita | Habilidades | Marcador | Competências próprias |
|---|---:|---:|---|---:|
| Corpo61–66, Projeto de Vida | 1ª |32|bullet|0|
| Corpo66–70, Projeto de Vida | 2ª |20|bullet|0|
| Corpo71–73, Pós-Médio | 3ª |21|1..21|0|
| Anexo452–455, Projeto de Vida | 1ª |32|1..32|3|
| Anexo455–457, Projeto de Vida | 2ª |20|1..20|2|
| Anexo457–459, Pós-Médio | 3ª |21|1..21|1|
| Total | |146| |6|

São6 quadros lógicos. O quadro PV2 do corpo abre com título no fim da66, enquanto a primeira habilidade aparece67. O anexo PV1 abre452 e as habilidades começam453. Não contar segmentos de página como quadros ou competências novas.

Os ordinais são marcadores documentais; não são códigos oficiais de habilidades. O anexo e o corpo têm ocorrências paralelas e11 pares apresentam diferenças literais depois de normalizar apenas espaços/marcadores. Há84 textos distintos nessa normalização, o que não significa84 habilidades semanticamente diferentes. Preservar146 ocorrências e sua parte documental evita apagar variantes por deduplicação silenciosa.

Continuações de habilidades no corpo: PV1 itens5(61→62),11(62→63),22(64→65); PV2 item20(69→70); Pós-Médio itens4(71→72),13(72→73). As listas do anexo atravessam páginas, mas suas habilidades individuais não atravessam. Competências: PV1 terceira célula454→455; PV2 primeira455→456; Pós-Médio457→458.

Papéis físicos: no corpo, Semestre/Dimensão/Conteúdo(s)/Habilidades; no anexo, Competência/Objetos de Conhecimento/Habilidades. Conteúdos nominais e dimensões não são habilidades. As seis células de competência são preserváveis como `competencia`, com sua formulação literal, inclusive orientações à oferta docente em “Estimular”, “Contribuir” e “Possibilitar”; não as reclassificar como habilidade individual do aluno. Semestres no corpo: PV1 habilidades1–16 no1º e17–32 no2º; PV2 habilidades1–10 no1º e11–20 no2º; Pós-Médio1–9 no1º e10–21 no2º. O anexo não explicita semestres. Esses metadados de semestre, dimensão e objeto não foram exigidos como campos do candidato nesta comparação e sua ausência no sidecar não deve ser confundida com transcrição dessas colunas.

## Verificação executada

- 21 páginas renderizadas e efetivamente vistas em imagem, com achados/hash em `independent-pv-visual.json`; imagens privadas em `var/private-evidence/source-audit-ac-em/independent-pv-*.png`.
- 768 fragmentos de linha nativa do denominador de habilidades relidos na região original:768 iguais,0 falhas.
- Candidato `data/manifests/uncoded/ac-em-pv-items.json`, SHA256 `535611af0023abffda03e3b4cc899e5a4b02b286a224303d99f8cfde26114909`:158 registros,146 habilidades+6 competências+6 seções.
- 146/146 textos completos de habilidades iguais ao denominador independente.
- 161/161 excertos por página de habilidades/competências iguais às linhas primárias correspondentes.
- 2.335/2.335 centros de palavras primárias cobertos pelas caixas de evidência candidatas.
- 6/6 competências com texto integral e conjunto de páginas iguais ao censo próprio.
- Série/etapa/componente declarados conferidos para todos os152 registros de aprendizagem/competência, sem códigos inventados.

Comandos reexecutáveis:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ac-em/independent-pv-census.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ac-em/independent-pv-compare.py
```

## Limites e lacunas

No recorte das colunas Habilidades/Competência dos seis quadros, não restou divergência de texto, quantidade, localização ou ano. O resultado não cobre competências gerais/de área ou demais IF em outras páginas e não constitui prontidão global AC/EM nem validação pedagógica humana.

A459 termina com o título “Anexo2 – Rotas de Aprofundamento Propedêuticas”. O arquivo fornecido termina nessa mesma página, sem as rotas anunciadas. É lacuna de conteúdo no artefato publicado disponível, sem demonstrar bloqueio de rede, intenção editorial ou que outra edição seja equivalente. PyMuPDF abriu o documento completo com459 páginas e o SHA256 esperado; a página459 contém o fim do quadro Pós-Médio e esse título, sem páginas subsequentes. A reconciliação global precisa investigar eventual fonte oficial complementar.

PDF/manifesto/sidecar/pipeline não foram alterados por esta revisão; apenas os artefatos `independent-*` e imagens privadas foram criados.
