# Adaptadores dos dois atos curriculares MA

Implementados e executados por `agent:rs_adapter:ma-normative-adapter`; conferidos por verificador e peer automatizados. Nenhuma revisão pedagógica humana foi atribuída.

| Fonte selecionada | Nós | Fragmentos | Linhas originais |
| --- | ---: | ---: | ---: |
| Resolução CEE/MA 211/2026 | 19 | 20 | 107 |
| Portaria SEDUC/MA 181/2026 e anexo | 76 | 98 | 619 |
| Total | 95 | 118 | 726 |

O censo independente foi produzido do PDF antes da leitura dos sidecars: oito/dez considerandos, seis/25 artigos, nove capítulos da Portaria, 17 seções do anexo e um quadro de oito linhas por três colunas, com sete etapas de fluxo pedagógico. Todas as linhas foram atribuídas exatamente uma vez. Os 95 registros e suas evidências passam no importador e finalizador compartilhados reais; 570 comparações de campos preservam texto, código, tipo, posições, evidências e contexto. Pais foram conferidos por chave estrutural, sem órfãos ou ciclos.

O adaptador reaproveita o contrato de partição normativa dos atos BA249 e RN11123. Lê as regiões da Source na ordem declarada de colunas; usa limites reais de `find_tables` para as 24 células do quadro. As continuidades entre páginas e colunas viram fragmentos distintos da mesma parte. A assinatura da Resolução 211 continua no topo direito da página 21. A seção 5 do anexo da Portaria começa na página 34 e continua na 35. Nenhuma matéria vizinha dos diários entra no conjunto.

Artigos são `artigo_normativo`; capítulos, considerandos e anexo têm tipos próprios. Os sete passos do quadro são `etapa_fluxo_pedagogico`, pois descrevem planejamento e acompanhamento docente. Expressões como “Habilidades prioritárias” nesse quadro não foram transformadas em habilidades de estudantes. Todos os códigos são nulos; números oficiais permanecem no texto e a numeração de artigos/seções/etapas usa `source_number`.

A Resolução tem âmbito da Educação Básica (EI/EF/EM) e faceta Computação, preservando o título Educação Digital e Midiática. A Portaria tem âmbito explícito dos componentes Língua Portuguesa e Matemática no Ensino Médio Regular parcial. O peer identificou a perda desse recorte quando as posições usavam componente nulo; os 76 nós foram corrigidos para as duas posições e o ciclo completo foi reexecutado. Não foram atribuídos anos escolares ou períodos letivos com base nas datas legais.

A revisão independente `acts/adapter-peer-review.json` confrontou todos os textos, fragmentos, linhas, células e pais, sem importar o parser do autor. Passou com zero falhas. As caixas tipográficas da Resolução ultrapassam o limite geométrico declarado em até 0,471 pt; o peer documentou tolerância de 0,5 pt, sem permitir palavras ou matéria externa. O quadro foi também inspecionado visualmente em render privado ampliado. Reexecução produziu bytes e IDs idênticos.

Sidecars finais:

- `data/manifests/uncoded/ma-211-items.json`: SHA `7e62414648b4172dcf6eae4d3f028046ab0eb0351ec93f7f28d9fe3963bfdc64`.
- `data/manifests/uncoded/ma-181-items.json`: SHA `e3e12025f883a2468ee8e15e03cc1dc9ccef9317c7a7e3bfd1f609146e4ab296`.

Comandos executados:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ma-current/ma-normative-census.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ma-current/ma-normative-extract.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ma-current/ma-normative-verify.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ma-current/build-normative-reconciliation.py
```

O último comando exige peer aprovado antes de gravar as duas reconciliações. Seus IDs esperados são gerados de um plano fixo de chaves por artigos/capítulos/seções do documento; não são coletados de todas as saídas genéricas do pipeline. A Resolução possui uma parte; a Portaria, duas: ato com 50 nós e anexo com 26. Os nomes coincidem com `normative_parts` das Sources.

A integração dos paths e da autoridade para suprimir seções genéricas é responsabilidade da frente Nordeste. Esses testes não comprovam incorporação no candidato nacional ou banco. A completude destes atos não adquire o complemento digital aprovado, os GPD/matrizes atuais ou os materiais SEDUC/Eureka citados no anexo. As lacunas continuam documentadas separadamente; nenhuma prontidão de MA é declarada.
