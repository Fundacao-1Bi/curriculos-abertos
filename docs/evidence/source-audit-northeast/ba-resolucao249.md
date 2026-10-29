# Bahia — Resolução CEE249/2026: estruturação e verificação

Revisor automatizado: `codex:al_current_materials`. Fonte `ba-resolucao-249-2026`, SHA-256 `c108df4fe4cb56dc0eb9290803025a84b4fa7c72c587d7ea00e6a3e59cee2573`. Foram lidas integralmente as sete páginas e conferida a [página oficial do Conselho Estadual de Educação da Bahia](https://www.ba.gov.br/conselhodeeducacao/publicacoes/1849/resolucao-cee-no-249-de-07-de-julho-de-2026).

O documento completo foi particionado em 45 registros normativos: ato/título, ementa, preâmbulo, nove considerandos, dispositivo deliberativo, oito capítulos, 22 artigos, assinatura e registro de homologação/publicação. O denominador foi fixado pela leitura do original, antes dos outputs do parser. As 237 linhas não vazias do texto nativo foram atribuídas exatamente uma vez: nenhuma linha sem destino ou com múltipla atribuição. O texto concatenado das partes coincide com o texto integral dessas linhas.

O sidecar `data/manifests/uncoded/ba-resolucao-249-items.json` preserva códigos nulos, números oficiais dos capítulos/artigos, pais estruturais e escopo Ensino Médio, sem inventar série ou período letivo. Os artigos2,5,9 e12 atravessam páginas; cada trecho mantém sua página/bbox e as evidências completas recompõem o artigo. Parágrafos e incisos permanecem integralmente no texto do artigo. Nenhum artigo foi classificado como aprendizagem.

Foi executado `ingest.extract_pdf(force=True)` da revisão `page-cell-v1.4.0` com PyMuPDF1.26.7 no runtime pinado: sete páginas, sete seções documentais, zero warnings e `ocr_pending:false`. Em seguida, `source_uncoded_items` e `finalize_items` reais validaram os 45 registros contra esse cache e os PDFs: IDs finais coincidiram com as chaves previstas independentemente, todas as evidências passaram, e o grafo de pais ficou sem órfãos ou ciclos.

A página7 foi renderizada e inspecionada visualmente em `ba-resolucao249-p7.png`: art16 determina implementação a partir do ano letivo2027; art22 determina entrada em vigor na publicação; o rodapé informa homologação26/08/2026 e publicação DOE27/08/2026. Data do ato, homologação, publicação e implementação foram mantidas separadas. Logotipos, marca d'água e endereço institucional repetido em elementos gráficos não foram transformados em disposições normativas.

Evidências principais:

- `ba-resolucao249-inventory.json`: inventário independente, contagens, hierarquia e quatro continuações.
- `ba-resolucao249-verification.json`: execução real da extração, importação e finalização, versão do runtime e cache/configuração.
- `ba-resolucao249-reconciliation-proposal.json`: conjunto esperado/verificado derivado das partes originais; entregue ao responsável Nordeste para integração.
- `ba-resolucao249-extract.py` e `ba-resolucao249-verify.py`: comandos reproduzíveis abaixo.

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-northeast/ba-resolucao249-extract.py
var/venv-pipeline/bin/python docs/evidence/source-audit-northeast/ba-resolucao249-verify.py
```

Esta verificação cobre o ato de sete páginas. Ele adota o DCRB-EM2026 revisado, mas não contém o referencial curricular completo. A reconciliação desse ato não resolve a indisponibilidade do arquivo revisado, não aceita a UF e não comprova publicação integrada nem jornadas portal/API/MCP. A integração do manifesto/reconciliação e a reconstrução do bundle são conduzidas pelo responsável Nordeste/pipeline. Não houve revisão pedagógica humana.
