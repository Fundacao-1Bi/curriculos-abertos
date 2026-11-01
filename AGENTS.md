# Diretrizes operacionais para agentes

Antes de criar candidatos ou executar testes com banco, build, extração,
composição, exportação, reimportação ou restauração, leia
[docs/storage-policy.md](docs/storage-policy.md). A política define orçamento,
exclusividade, registro antecipado e encerramento dos recursos. Os fluxos de QA
TypeScript listados na política agora entram obrigatoriamente em
`scripts/qa-executor.ts`, com lock entre sessões, orçamento, registro e
reconciliação explícita de interrupções. Não contorne uma recusa chamando o
worker, Docker ou SQL diretamente. Builds, extrações Python e operações manuais
fora desses fluxos ainda exigem as verificações explícitas abaixo.

## Recursos e preservação

O projeto mantém dados curriculares, publicações, evidências, backups e ambientes de QA que podem não estar no Git ou no remoto. Trate-os como dados de trabalho, inclusive `data/raw`, `data/extracted`, `data/bundles`, `var`, volumes Docker e artefatos de falhas. Não apague um diretório de QA inteiro por ser antigo, grande, ignorado ou ter nome temporário.

Antes de um build, extração, exportação, reimportação ou restauração: execute `python3 scripts/ops-resource-inventory.py` e confira espaço disponível, processos e containers. Para build, aplique também `node --import tsx scripts/ops-preflight.ts --disk-only` (guarda padrão de 15 GiB); não reduza o limite para contorná-lo. Para QA nacional, calcule a capacidade com `scripts/qa-capacity.ts` para o cenário real e reserve espaço para os arquivos simultâneos e o banco; 40 GiB livres é um ponto de planejamento, não garantia. Não inicie tarefas pesadas com capacidade insuficiente ou sem estimativa de pico.

Para extração longa, use `scripts/data-monitor-resources.py --job-id ID` com limite de disco adequado à consolidação; ele pode suspender o batch identificado quando a guarda for atingida e exige retomada explícita e conferida dos PIDs. Registre espaço mínimo, duração, workers e versão dos inputs. Faça atualizações incrementais e não crie cópias completas por fonte quando uma atualização limitada e validada bastar. Considere os arquivos simultâneos, incluindo bases, candidatos, downloads, imagens, bancos e WAL, antes de estimar o pico.

Após cada QA, registre identidade, proprietário, entradas, saídas, hashes e status. Em sucesso, use o fluxo de limpeza específico da própria execução, como `cleanupVerifiedReimport` em `scripts/qa-own-cleanup.ts`, somente depois das provas e recibos exigidos. Em falha, preserve o material necessário ao diagnóstico e registre caminhos, tamanho e decisão de retenção; reavalie-o depois, em vez de deixá-lo acumular sem dono. Evite gerar repetidamente exports nacionais e bancos integrais para alterações pequenas. Reutilize apenas ambientes compatíveis com o fingerprint e sem comprometer isolamento, integridade ou rastreabilidade.

Antes de uma limpeza posterior, apresente uma lista exata de caminhos ou IDs, tamanhos, uso/montagens, provas de duplicação e impacto em retomada, rollback e evidência. Verifique novamente processos, `lsof`, estado Docker e montagens imediatamente antes da operação; se uma verificação falhar, não exclua. Não remova dados únicos, backups, volumes, imagens de rollback ou recursos de outro projeto sem autorização para esse escopo. Nunca use `docker system prune` global nem apague `Docker.raw`. Não inicie/reinicie Docker ou interrompa serviços apenas para limpeza sem considerar impactos e a autorização existente.

`du`, tamanhos de imagens/caches Docker e volumes podem se sobrepor ou incluir blocos compartilhados APFS; não os some como espaço recuperável. Anote `df` antes e depois e reporte o delta observado com ressalva de atividade concorrente. Se Docker estiver indisponível, a rotina informa a falha e não o inicia.

## Consolidação de experimentos

Consulte `docs/experiment-consolidation-20261101.md` antes de derivar outro candidato. A base publicada e o candidato de continuação são papéis distintos; só altere sua designação com identidade, hashes, lista de deltas incorporados e prova de preservação fora do alvo. Não deduza linhagem apenas de recência, contagem ou `parent_publication`.

Use recibos/deltas por fonte e relatórios pequenos contra bundles imutáveis para os ensaios. Acumule os deltas validados antes de uma composição nacional. Não gere outro corpus, export ou banco nacional apenas para atualizar recibos ou diagnóstico de gate. Uma rodada deve ter um responsável pela integração e no máximo uma operação pesada por vez, inclusive entre agentes/sessões.

Antes de criar recursos de QA, registre em `var/jobs/<run-id>/retention.json` o proprietário, propósito, hashes de código/inputs/base, recursos exatos, orçamento de pico e estado. Mantenha relatórios imutáveis por execução; ponteiros como `qa-clean-state.json` não substituem o registro. Na conclusão ou interrupção, acrescente resultado, sucessor ou motivo de retenção e decisão de revisão/limpeza. Não declare um ambiente reutilizado como prova de instalação vazia.

O inventário detalhado pode ser salvo com `python3 scripts/ops-resource-inventory.py --details --minimum-free-gib 15 --output <caminho-novo.json>`. Ele inclui processos, montagens e identidades Docker sem argumentos de processo ou variáveis de ambiente; falhas de leitura não são prova de ausência de uso. Para o passivo existente, consulte `docs/qa-retention-audit-20261101.md` e os planos/recibos em `docs/evidence/storage-*` e `docs/evidence/qa-retirement-*`. Planos preparados não autorizam execução, e tamanhos de duplicatas APFS não equivalem a ganho físico.
