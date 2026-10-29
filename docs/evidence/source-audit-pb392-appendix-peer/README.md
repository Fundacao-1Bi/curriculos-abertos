# PB392 — revisão independente do anexo185–188

Revisão documental automática, sem revisão pedagógica humana. Fonte exclusiva `pb-proposta-ei-ef-cedoc`, PDF392p SHA-256 `af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453`. O PDF635p e seu adaptador2008 permanecem separados. O arquivo1946 original tem SHA `4336a71d0676c2b48f1e363e06f4ef0368c0eba9e2980ff3fc3c79f2865f998b` e foi preservado.

O título do original declara **ANEXO: HABILIDADES PARA O ENSINO DE EDUCAÇÃO FÍSICA CONFORME O DOCUMENTO FINAL DA BASE NACIONAL CURRICULAR COMUM (BNCC,2017,pp225–237)**. A correção conserva o texto integral citado como `referencia_no_documento`; não o transforma em nova habilidade estadual ou equivalência pedagógica. Quatro cabeçalhos explícitos sustentam os anos1–2/3–5/6–7/8–9 do EF. Não há posição EM nesse recorte.

## Denominador primário e diagnóstico

Antes de ler o candidato, o auditor obteve o texto nativo e as coordenadas das páginas184–189, confirmou que não há tabelas com réguas no anexo e leu os quatro renders185–188. Os renders permanecem privados em `var/private-evidence/source-audit-pb392-appendix-peer/`.

O anexo tem69 enunciados (12+15+21+21), quatro cabeçalhos de ciclo e um título. O censo de glifos independente cobre11.632 caracteres não brancos nos69 corpos, incluindo seus identificadores. A ordem é coluna esquerda inteira, depois direita inteira, página por página. `EF35EF11` começa no fim da coluna esquerda186 e termina no alto da direita186; `EF89EF03` começa no fim da direita187 e termina na esquerda188. Páginas184 e189 delimitam o anexo e não foram incorporadas.

O frame original contém64 IDs com falha literal, todos dentro dessas páginas. Os69 registros genéricos do recorte têm texto incompleto ou contaminado; cinco passam o teste literal anterior sem representar o corpo completo. Exemplos: `EF35EF11` terminava em “estratégias PROPOSTA”, incluindo o rodapé; `EF89EF03` perdia a continuação188. O diagnóstico conserva o frame, o cache e seus hashes, sem editar nenhum deles.

## Provas e reprodução

- `blind-primary-inventory.json`: obtenção nativa inicial e limites184–189 antes de ler o candidato.
- `independent-glyph-unit-inventory.json`:69 unidades independentes com todas as linhas, limites, ciclos e ordem.
- `original64-to-primary69-diagnostic.json`: rastreio dos64 IDs originais e dos cinco registros adicionais.
- `candidate-verification.json`: leitura integral do candidato74, cobertura geométrica dos glifos, hierarquia/ordem/anos e nove mutações negativas rejeitadas.
- `independent-integration-replay.json`: carregador/finalizador/schema reais e linhagem dos69 registros, com pins preservados.

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-pb392-appendix-peer/verify_appendix.py
var/venv-pipeline/bin/python docs/evidence/source-audit-pb392-appendix-peer/diagnose_original.py
var/venv-pipeline/bin/python docs/evidence/source-audit-pb392-appendix-peer/verify_appendix.py --candidate data/manifests/uncoded/pb-cedoc-392-with-appendix-items.json
var/venv-pipeline/bin/python docs/evidence/source-audit-pb392-appendix-peer/replay_integration.py --combined data/manifests/uncoded/pb-cedoc-392-with-appendix-items.json
```

O extrator do autor não foi importado pelo auditor. Ambos usam PyMuPDF, portanto o teste não representa independência entre engines PDF. Censo, leitura dos pixels e comparação de todos os corpos são distintos da mera aceitação de substrings pelo checker central. A política de tipos confirmou `referencia_no_documento`, `ciclo_escolar` e `anexo_curricular` como tipos de contexto já existentes; não foi necessário alterar enum ou core.

O agregado final2020 conserva exatamente os1946 payloads e todos os campos originais do wrapper de autoria/método/escopo. Acrescenta somente74 itens e o metadado `appendix_extension`. Seu SHA é `fc939a0bdc6aeb243acc8a86c18e071e0a7f3697d9942012aa4e776a9f33c27e`. O probe inicial de uma lista privada sem wrapper foi marcado `superseded_unbound_probe`; não houve binding desse probe. Os testes finais exigem o wrapper original e o novo hash.

Este pacote não é um recibo WholeSource, não declara a PB/UF ou produção concluída, nem confirma vigência, cadeia primária do catálogo ou identidade editorial com a fonte635p. A instalação do novo sidecar agregado, a mudança serial de Source e o refresh seletivo pertencem aos proprietários Nordeste/pipeline e possuem provas próprias.
