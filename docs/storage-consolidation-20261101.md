# Disco e consolidação — 01/11/2026

Intervenção concluída após autorização explícita do usuário para aposentar os
cinco QAs nomeados. Foram removidos 15 containers e dez volumes; principal,
QA `a3f8cd`, dados do host, candidatos, backups, imagens e outros projetos
foram preservados. O delta observado foi **+85,998 GiB**, com **86,329 GiB
livres** ao final, sujeito à atividade concorrente. O preflight de disco passou.
Isto não é aceite nacional; QA nacional ainda exige estimativa de pico própria.

## Diagnóstico e ponto de continuação

- Existem seis ambientes QA, cinco ativos, além do principal. O maior QA tem
  24 publicações nacionais no mesmo banco, que mede 45,93 GB. As versões não
  são equivalentes apenas por terem contagens semelhantes.
- `var` mede aproximadamente 61 GiB aparentes; quatro árvores QA têm cerca de
  10 GiB cada. Esses tamanhos incluem blocos APFS compartilhados.
- Foram encontrados 5.284 arquivos idênticos aos canônicos, totalizando
  20.107.036.559 bytes lógicos, em duas árvores sem montagem Docker.
- O ensaio de compartilhamento APFS foi interrompido após 188 arquivos e
  6.127.950.536 bytes: o delta livre observado foi só +5.935.104 bytes, sujeito
  à atividade concorrente. Não há evidência de recuperação material. Não
  executar o restante do plano esperando recuperar 18,7 GiB físicos.
- Todos os 188 arquivos foram relidos e verificados: SHA, tamanho, modo,
  proprietário/grupo, mtime, flags, atributos e ausência de ACL, além de inode
  distinto do canônico. Caminhos e conteúdo foram preservados; inode, ctime
  e eventualmente birthtime podem mudar. Não restaram intents pendentes.
- O preflight de build retornou bloqueio com 0,61 GiB disponíveis, contra o
  mínimo de 15 GiB. Nenhum build, extração ou exportação nacional foi iniciado.

O [mapa de experimentos](experiment-consolidation-20261101.md) identifica a
base `ca-7d302a9c674a97b83278` e designa a candidata privada
`ca-41c0553542d47d558786` para continuação. A designação não promove o
candidato. Recibos e diagnósticos devem ser reavaliados incrementalmente,
sem produzir outro corpus completo por alteração documental.

## Limpeza de maior impacto, executada

O plano imutável `docs/evidence/qa-retirement-plan-20261101.json` identifica exatamente
15 containers e dez volumes de cinco QAs históricos: `f517a7`, `b6fa71`,
`a1f735`, `a65573` e `toei`. Os nomes/IDs completos estão no JSON e na
[auditoria de retenção](qa-retention-audit-20261101.md). Os volumes representam
cerca de 89 GB nominais, não uma promessa de ganho físico.

O plano preserva o principal, o QA `a3f8cd`, todos os caminhos do host,
candidatos, dados curriculares, backups, evidências e imagens. Não inclui
ContentiZAP nem recursos anônimos/de terceiros. Remover os volumes elimina
a retomada direta dos bancos e dados administrativos de teste históricos.

O estado único recebeu retenção explícita: a revisão administrativa
publicada no f517a7 não tem bundle standalone, há alterações de curadoria,
eventos e jobs pausados. O índice
`docs/evidence/qa-f517-candidate-retention-map-20261101.json` distingue as 23
publicações com manifesto correspondente desse estado único. Presença e
tamanho de shards não equivalem à sua verificação integral por hash.

O usuário autorizou os cinco projetos nomeados. Antes de executar, foram
conferidos os pacotes privados de curadoria, contribuições, jobs e históricos,
com hashes e permissões restritas. Os índices públicos estão em
`docs/evidence/qa-f517-private-retention-index-20261101.json` e
`docs/evidence/qa-retention-metadata-index-20261101.json`. São aproximadamente
14,2 MB de pacotes selecionados, **não** backups integrais de banco ou uma
restauração integral testada. Os sete jobs pausados foram preservados como
metadados e tiveram sua retomada direta abandonada com os bancos autorizados;
nenhum handler foi retomado/cancelado. O QA `a1f735` permaneceu parado até sua
remoção autorizada, sem ser iniciado para inspeção SQL.

As guardas de identidade, referências, processos, `lsof` do host e montagens
foram repetidas antes das remoções. Referências e uso dos volumes dentro da VM
foram verificados pelo Docker; seus caminhos não são caminhos do host macOS.
Os containers app/worker foram parados antes dos bancos. O recibo completo é
`docs/evidence/qa-retirement-receipt-20261101.json`, com intents e journal.

O descarte assíncrono do Docker devolveu espaço ao host: de 355.192.832 bytes
livres imediatamente antes da aposentadoria para 92.695.064.576 bytes após a
devolução. A alocação observada de `Docker.raw` passou de 213.756.637.184 para
121.426.325.504 bytes, sem manipular esse arquivo. Os volumes Docker passaram
de 104,5 GB para 15,29 GB. Esses números não devem ser somados.

Também foram removidos somente `.next/cache/turbopack` e
`.next/cache/webpack`, caches regeneráveis sem leitores/montagens. O delta
imediato dessa etapa foi negativo por atividade concorrente; não contabilizar
seus 322 MiB aparentes como recuperação adicional.

Principal (`3000`) e QA preservado (`3107`) passaram nos quatro GETs de
`/api/health` e `/api/ready` com HTTP 200. Seus seis containers permanecem
saudáveis; containers do ContentiZAP mantiveram o estado. Todas as imagens
foram preservadas e `latest.json` manteve o SHA original. Evidência final:
`docs/evidence/storage-consolidation-completion-20261101.json`.

## Controles entregues

- `AGENTS.md` passou a exigir ponto de continuação explícito, deltas por fonte,
  uma operação pesada por rodada, dono, hashes, orçamento e decisão de retenção.
- `scripts/ops-resource-inventory.py --details --output <arquivo-novo.json>`
  inclui tamanhos de `var`/`tmp`, processos sem argumentos, montagens e
  identidades efetivas dos containers. Saída exclusiva e privada evita
  sobrescrever evidências e expor `Env` do Docker.
- `scripts/ops-consolidate-storage.py` separa plano e aplicação por SHA, limita
  escopo a duas árvores não montadas e verifica bytes/metadados antes de trocar
  cada arquivo. A execução desta intervenção é **parcial e encerrada**, com
  recibo e verificação próprios; o plano antigo não deve ser retomado.
- 33 testes direcionados passaram, sem skips; `git diff --check` passou.

Registro de propriedade e retenção desta intervenção:
`var/jobs/storage-consolidation-20261101/retention.json`.

Evidências desta intervenção:

- `docs/evidence/storage-resource-inventory-20261101.json`;
- `docs/evidence/storage-build-preflight-20261101.json`;
- `docs/evidence/storage-consolidation-plan-20261101-v2.json`;
- `docs/evidence/storage-consolidation-receipt-20261101.json` e journal;
- `docs/evidence/storage-consolidation-final-verification-20261101.json`;
- `docs/evidence/qa-retirement-plan-20261101.json`;
- `docs/evidence/qa-retirement-receipt-20261101.json`;
- `docs/evidence/storage-next-cache-cleanup-completed-20261101.json`;
- `docs/evidence/storage-resource-inventory-after-20261101.json`;
- `docs/evidence/storage-build-preflight-after-20261101.json`;
- `docs/evidence/storage-consolidation-completion-20261101.json`.
