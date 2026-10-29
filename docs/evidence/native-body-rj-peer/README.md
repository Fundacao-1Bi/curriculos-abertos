# Peer independente: correções técnicas RJ EM e EF p383

Aceite técnico automatizado dos14IDs duplicados propostos em `native-body-rj-em/binding-proposal.json` e da divisão explícita de `(EF07CI15Interpretar` na fonte EF p383. Não é mudança curricular oficial, reconciliação da Source/UF, avaliação pedagógica humana ou publicação executada.

`review.json` registra cada ocorrência, pins conferidos, coordenadas da âncora errada e real, ID retido e hash do corpo integral. Os14fantasmas carregavam o código local RJ, mas começavam na âncora de outro identificador nacional. Em todos os14casos há um único identificador local real: seu ID/locator/posição/pai foram preservados. Cada corpo foi comparado por leitura independente dos spans primários até o próximo cabeçalho literal de objetos de conhecimento. A revisão não chama o extractor do produtor para obter seu texto esperado. O finalizador compartilhado é usado somente para comparar as posições atuais do cache com as posições do candidato; âncoras e corpos vêm diretamente do PDF.

A página383 realmente imprime `(EF07CI15Interpretar` sem separador ou parêntese final. O candidato reconhece os oito glifos de `EF07CI15` e devolve `Interpretar` ao início do corpo. Código+corpo conservam todos os caracteres da célula, sem reformar a redação; o token completo, código/texto/ID anteriores e proveniência permanecem explícitos. Os identificadores vizinhos `(EF07CI14)` e `(EF07CI16)` e os glifos nativos foram conferidos. O novo ID técnico é `ca:rj-doc-eief-2019:6eb5db5e20d78b7496e9`; não deve substituir silenciosamente o histórico da publicação antiga. As posições foram comparadas com o finalizador atual, que conserva ano local desconhecido; o ano7inferido do código no cache bruto não foi promovido como prova documental.

Os16controles passaram. Quatro recortes pequenos de EM e um da célula EF383 foram examinados; ficam privados em `var/private-evidence/native-body-rj-peer/`, com pins em `private-primary-crops.json` (~297KB), sem redistribuir PDF/raster aqui. Caixas de glifos podem se sobrepor verticalmente; o peer seleciona caracteres pela linha real e centro de glifo dentro da caixa do código, sem aceitar letras incidentais da linha vizinha como parte do identificador.

Há doisP2de metadados no checkpoint revisado: o proposal EM dizia237páginas onde seus ranges abrangem238(o produtor identificou a p195nativa sem registros no cache); e o motivo EF383 dizia nove glifos de identificador, quando `EF07CI15` tem oito. O parêntese de abertura é o nono caractere do token, não parte do código. Os donos foram avisados para corrigir após o freeze. Os dados técnicos conferidos não dependem desses erros descritivos. Rechecar os pins de metadados depois dessa revisão é distinto de refazer uma correção curricular.

A próxima extração/distribuição deve guardar a lista pinada `invalid_duplicate_id → superseded_by_id`, este aceite e a revisão técnica no changelog/proveniência. O sidecar retém o upstream do ID verdadeiro; a relação dos fantasmas supersedidos está no proposal/recovery-report. Publicações anteriores permanecem imutáveis.

Comando, apenas leitura de fontes/cache/candidatos; escreve resultado em `var/`:

```sh
var/venv-pipeline/bin/python docs/evidence/native-body-rj-peer/review.py
```

Nenhum MF, núcleo, cache, banco ou publicação foi alterado pelo peer. O checkpoint foi produzido em `var/` durante o congelamento e copiado para esta pasta após sua liberação.

Atualização após a liberação: `metadata-recheck.json` confirma os doisP2corrigidos. O novo proposalEM usa238páginas e um ledger pinado com os14pares e hashes individuais. No EI/EF, trocar de volta a única expressão `eight identifier glyphs` para `nine identifier glyphs` reconstrói exatamente o SHA antigo7451417…: prova criptográfica de que nenhum outro byte dos200registros mudou. `review-current.json` refez o peer com os pins novos e passou novamente, sem achados pendentes. O checkpoint inicial `review.json` continua imutável, pois é referenciado pela proveniência do produtor.
