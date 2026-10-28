# Estrutura integral das normas nacionais 2024/2025

Auditoria e extração documental automatizadas. Os atos normativos, seus dispositivos e marcas editoriais não são classificados como aprendizagens. Nenhuma interpretação jurídica, vigência temporal ou aprovação pedagógica humana é atribuída a esta conferência.

`normative-census.json` fixa primeiro o denominador das três fontes: todos os 28.217 tokens nativos, 2.682 linhas e 59 páginas, com índices físicos, caixas, marcadores e SHA-256 dos PDFs. O censo foi executado antes da construção dos novos sidecars. `structure.py build` constrói a hierarquia a partir dos marcadores literais e da ordem física de leitura em coluna única. Não altera PDFs, manifestos Source, caches, núcleo do pipeline ou publicações.

| Fonte | Páginas | Artigos | Parágrafos | Incisos | Alíneas | Novos nós normativos/contextuais |
|---|---:|---:|---:|---:|---:|---:|
| DCN Ensino Médio 2024 | 22 | 44 | 61 | 152 | 47 | 347 |
| Parâmetros IFA 2025, dispositivos | 16 + cabeçalhos do anexo | 31 | 9 | 99 | 53 | 225 |
| Educação Digital/Midiática 2025 | 13 | 42 | 44 | 43 | 0 | 164 |
| Total | 59 no conjunto completo | 117 | 114 | 294 | 100 | 736 |

Cada nó de artigo contém seu caput; parágrafos, incisos e alíneas conservam a redação própria em filhos ordenados. O artigo completo é sua subárvore, sem duplicar a redação canônica entre pai e filhos. Títulos, capítulos, seções e subseções têm pais explícitos; os rótulos e respectivas legendas permanecem juntos, inclusive quando atravessam a página. As palavras do preâmbulo, identificação do ato, assinatura impressa e marcas da publicação também são preservadas. A presença de nome impresso do signatário não constitui verificação de assinatura digital.

`verify-structure.py` relê todos os tokens dos PDFs vivos e confere identidade, caixa e índice contra o censo. Prova dono único para todas as linhas normativas e para cada ocorrência de palavra do anexo. Confere todo fragmento e todo pai, ausência de ciclos e sequência completa dos 117 artigos; executa o checker literal comum sobre todos os registros. Usa também o adapter real `source_uncoded_items` e valida todos os 846 registros resultantes contra o JSON Schema 1.1.0 imutável. O relatório distingue binding ao manifesto real de eventual Source clonado apenas em memória enquanto o coordenador aplica o novo path.

No anexo IFA 2025, o wrapper mantém os **58 registros anteriores exatamente iguais como valores**, incluindo IDs derivados das chaves, pais, textos, posições e evidências. São 10 competências comuns, 21 objetivos, 21 grupos de capacidades e 6 nós de estrutura. Acrescenta 52 nós `rotulo_documental`: 31 numerações físicas e 21 frases literais “Demonstrando a capacidade de:”. Esses 115 tokens estavam representados parcialmente em metadados de numeração, mas fora dos textos dos 58 nós. A prova agora atribui todas as 4.478 palavras físicas do anexo exatamente uma vez, preservando integralmente os registros anteriores e sem criar aprendizagens adicionais. Os 335 registros do wrapper são 225 normativos/contextuais novos + 58 anteriores + 52 rótulos.

Os três PDFs completos têm 28.217 ocorrências de palavras, todas preservadas exatamente uma vez nos registros normativos/contextuais e no anexo. São 11.184 da DCN, 11.785 dos parâmetros IFA e 5.248 da norma digital. Há 20 nós com continuação física entre páginas: 6 DCN, 8 IFA e 6 Digital. `critical-continuations.png` contém seis recortes limitados usados para conferir os títulos/capítulos partidos e a continuação do artigo 28 dos parâmetros IFA; os demais foram verificados integralmente pelos fragmentos nativos.

Os 15 casos negativos removem o último artigo, duplicam dono de linha, alteram palavra, trocam SHA de fonte e desafiam o checker literal com texto inventado, nas três fontes. Todos são rejeitados. O relatório `structure-verification.json` conserva os resultados e os paths/hashes propostos ao coordenador.

```sh
# Só repetir o censo quando houver motivo explícito para substituir o denominador congelado.
var/venv-pipeline/bin/python docs/evidence/source-audit-br-fidelity/normative-2024-2025/structure.py census
var/venv-pipeline/bin/python docs/evidence/source-audit-br-fidelity/normative-2024-2025/structure.py build
var/venv-pipeline/bin/python docs/evidence/source-audit-br-fidelity/normative-2024-2025/verify-structure.py
```

As propostas Source estão em `structure-verification.json`: DCN usa `br-dcn-2024-normative.json`, Digital usa `br-digital-2025-normative.json` e IFA usa `br-ifa-2025-normative-with-annex.json`. O arquivo `br-ifa-2025-normative-only.json` serve ao confronto independente dos novos dispositivos; não substitui o wrapper em produção. A autoridade que suprime as seções genéricas de página deve cobrir todas as páginas correspondentes, evitando duplicação com o sidecar integral.

O relatório anterior `verification.json` registra o estado dos caches v1.4 antes dos novos sidecars; a ausência então observada de cache digital é histórica e não é uma alegação de omissão nestes novos arquivos. A futura candidata FULL ainda precisa ser processada, confrontada, importada e servida para verificar a integração final. Estes resultados não aprovam a completude nacional das 27 UFs.
