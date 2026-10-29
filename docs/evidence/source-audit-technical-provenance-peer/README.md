# Peer de proveniência técnica

Revisão read-only do produtor `pipeline/technical_provenance.py` e de seus testes. Não houve alteração de core, manifesto, cache, corpus ou banco; nenhum import, build, parser global ou novo scan dos shards nacionais foi executado. As saídas persistentes deste peer ficam somente neste diretório.

## Achados priorizados

1. **P1 para promoção automática — um terceiro texto existente no BASE não bloqueia a correção de mesmo ID.** Em `contextualize`, linhas236–245, tanto a ausência do ID quanto um texto existente diferente de `before` e `after` recebem `documented_historical_text_correction`. O controle contrafactual preservou o mesmo ID e Source da captura real, trocou apenas o texto em memória e a chamada foi aceita. Isso não descreve o BASE real, que contém o `before` esperado. Antes de usar o resultado como autorização para substituir registros, exigir `before`, permitir `after` como idempotência e diferenciar/rejeitar conflito presente com terceiro texto. Uma correção histórica com ID ausente pode continuar explicitamente histórica. O produtor atualmente é somente diagnóstico e não escreveu esse controle em publicação alguma.

2. **P2 — colisão de payload em relações não é verificada pelo helper.** `evaluate`, linhas191–206, compara payloads de itens com o mesmo ID, mas para relações verifica somente membros que apontam para IDs supersedidos. Duplicar uma relação real com o mesmo ID e `relation_type` divergente foi aceito, incrementando `relations_checked`. A validação integral de schema/unicidade pode existir no compositor/importador; esse peer não afirma que o helper seja o único gate. Para uma interface de avaliação que declara verificar os records efetivos, aplicar a mesma guarda de colisão às relações ou explicitar e comprovar a pré-condição no chamador. O teste atual de colisão cobre itens RAW e itens do BASE, não relações.

3. **P2 na fronteira de identidade — o SHA do BASE é validado por comprimento, sem gramática nem verificação dos bytes do manifesto.** `contextualize`, linhas221–223, aceitou `z` repetido64 vezes. `global_id` também depende de pins previamente conferidos pelo chamador. Validar64 hexadecimais e exigir que o integrador confronte o manifesto capturado antes de contextualizar. Os pins reais usados neste peer são válidos e seus bytes foram verificados; a entrada inválida foi somente um controle em memória.

## Resultado e identidade observados

- Os14 testes existentes passaram, zero falhas/skips, em12,479s, com o runtime fixado do projeto. Incluem deriva do produtor/dependências/runtime, mudança de prova durante iteração, scope/targets, histórico versus remoção, texto same-ID e colisões de itens.
- Reprodução real:15.276 itens,3.037 relações, captura pinada de19 registros do BASE. Os18 IDs supersedidos existem no BASE e estão ausentes do RAW; os18 replacements existem na Source correta. O same-ID possui exatamente o `before` no BASE e o `after` no RAW. Nenhum desses resultados é contrafactual.
- A captura do BASE, todas as evidências nomeadas em `real-verification.json`, os shards RAW e o manifesto RAW tiveram seus hashes conferidos pelo loader da prova. Os200.724 itens nacionais são um censo histórico relatado pela prova anterior; este peer não repetiu aquele scan nacional.
- O produtor atual inclui bytes próprios, dependências e runtime na identidade. Portanto o digest atual `c2eb1a2b33b6a51dc3c43b0fc0f7634c636069873dcf100052e1f082e6414045` difere corretamente do legado `6145647e6eb772dfe2c8f475d34efaccc06a58e9c611d931c220e68e3494c0c7`. O ID diagnóstico atual `ca-update-fa01cad5a62f15da814c1101bd8b75a0` usa o ator explícito deste peer; não é publicação criada/importada e não deve substituir o ID legado em evidência histórica.
- Eventos e provas são copiados, efeitos são contextualizados na identidade pinada do BASE, fontes fora dos targets falham e ordem de targets/captura não altera o resultado. A identidade não é alegação de emenda oficial, equivalência pedagógica ou revisão humana.

## Drift e limite da prova histórica

Foram relidos os99 pins de `input-pins.json`.98 permanecem iguais. `pipeline/raster_review_scoped.py` mudou de `419a4d06b40d8099b6684b0f04dc3bc614d03b8d5b4099d9d5bec84cf3817cab` para `3808cc1a5ab930bfac8edeebc853bc6f5716e1abd394fd0352de792c13eda2b3`. O coordenador está revisando essa frente em paralelo; este peer não atribui causa nem altera o arquivo. O resultado anterior “99 pins preservados” continua sendo evidência daquela execução, não uma certificação dos99 bytes atuais. Uma integração com o código novo precisa de checkpoint/pins próprios e de sua verificação correspondente.

O helper permanece standalone: a busca por `technical_provenance`/`contextualize`/`global_id` não encontrou import/chamada pelo ingest ou compositor de produção, somente o módulo e seus testes. Assim, não observei mudança no comportamento de fontes fora do escopo ou no caminho de bypass existente. Isso é inspeção de código, não uma execução de compositor/publicação de produção. O integrador deverá preservar esse bypass explicitamente quando fizer o wiring.

## Reprodução

```sh
env PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python -m unittest discover -s pipeline/tests -p test_technical_provenance.py -v
env PYTHONDONTWRITEBYTECODE=1 var/venv-pipeline/bin/python docs/evidence/source-audit-technical-provenance-peer/verify_peer.py
```

`verification.json` contém hashes dos arquivos inspecionados, pins reais, fingerprint, contagens e os três controles em memória. O script não altera a captura nem prova canônica. Os controles adicionais são exemplos diagnósticos, não dados de produção. O peer não autoriza publicação enquanto o tratamento de conflito same-ID para promoção automática permanecer indefinido.
