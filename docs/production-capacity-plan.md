# Capacidade para produção — inventário e plano

Atualizado em 2026-10-28T18:48:19.979195+00:00. Ator automatizado; inventário de leitura e preparação de código. Nenhum build, up, restart, prune, arquivamento ou alteração do runtime foi executado nesta rodada.

## Limite observado

O inventário mediu 7,163,904,000 bytes livres (6.67 GiB). O build continua exigindo 15 GiB; faltavam 8.33 GiB. O negativo real de `ops-preflight --disk-only` recusou o estado atual em `capacity-preflight-current.json`. O host tem swap alocado de 15 GiB, com aproximadamente 13,38 GiB usados, mas swap e processos globais não pertencem ao espaço recuperável autorizado do projeto. Não há volume externo de dados montado com capacidade útil: apenas um DMG de aplicativo.

## Recuperação reversível dentro do projeto

| Candidato | Alocação observada | Ganho possível e condições |
| --- | ---: | --- |
| JSONs privados de auditoria | 1.552.674.816 bytes | Maior grupo southeast-fidelity tem 1.352.007.680 bytes; owner pr_adapter/es_positions confirmou ausência de escrita e apenas leitura dos finalized. Compressão APFS transparente, com o mesmo protocolo de SHA/FD/temp/replace, pode liberar aproximadamente 1,1 GiB; estimativa, não resultado executado. Demais subárvores exigem coordenação de seus owners. |
| Caches v1.1 | 259.420.160 bytes | 98 derivados. Pipeline não os utiliza; auditorias externas ainda precisam ser alinhadas. Preferir compressão transparente para manter caminhos. Ganho estimado abaixo de 0,25 GiB. |
| Caches v1.4 | 244.125.696 bytes | 1.123.818.067 bytes lógicos já foram compactados por APFS. Pipeline não mantém leitor, mas outras frentes podem depender de caminhos. Gzip adicional tem ganho pequeno; não considerar 1,12GB como espaço recuperável, nem arquivar sem todos os leitores coordenados. |
| Outros JSONs de extração | cerca de 251MB | Incluem caches customizados e sidecars de auditorias ainda ativos. Não são candidatos até identificar ownership/fingerprint e encerrar escritores. |
| Evidências recentes e menores | residual pequeno | A rodada anterior já reduziu 1.525.456.896 bytes alocados entre caches1.4 e provas. Repetir somente em arquivos estáticos não abre margem de vários GiB. |

Essas alternativas reversíveis não cobrem o déficit de aproximadamente 8,3 GiB para o build. Raw, atuais1.5, manifests, backups, volumes, Git e artefatos publicados não entram no cálculo de liberação. Em particular, caches1.5 usam 1.302.913.024 bytes e estão protegidos; backups privados usam cerca de916MiB, incluindo rollback PostgreSQL e filesystem do runtime já restaurado em teste.

## BuildKit comprovadamente próprio restante

| ID | Tamanho informado pelo Docker | Estado/decisão |
| --- | ---: | --- |
| r6ldlil6v76qvwhrmrbxo6yyc | 331,7MB | Filho de lzn; snapshot técnico antigo protegido. |
| lznmgx833qprpv6b37g7y6tn4 | 2,231GB | COPY produção14:54; protegido junto ao runtime c2eb em uso. |
| motzs2fb1c99tek718ra86fkn | 443,4MB | Pai de lzn, ferramentas do runtime antigo; protegido. |
| frj56tl6ndn3lc8um7i9nzmkd | 443,5MB | Camada recente de ferramentas, reutilizável no próximo build. |

`reclaimable=true` e `shared=false` não são autorização para apagar snapshots protegidos. A remoção desses registros não foi executada. Os demais caches grandes são de outros projetos ou têm ownership não demonstrada. Não há prune global no plano. Mesmo a soma nominal desses quatro registros (~3,45GB) com a compressão restante não garante atingir15GiB; liberação real exigiria confirmar referências e capacidade física, sem sacrificar rollback.

## Pico por etapa: código preparado, execução FULL pendente

Os três scripts QA passaram a verificar a imagem real antes de criar ambiente ou recursos. Produção confere todos os shards e calcula um orçamento inicial; após importar, mede o PostgreSQL e os bytes completos dos registros. J09 escolhe a maior UF por bytes SQL e não presume que seu grafo de suporte seja pequeno: membros diretos e ancestrais podem atingir a base nacional.

J09 contabiliza duas cópias de export no servidor, duas no cliente, shards de conversão, banco nacional+recorte, WAL, índices e reserva de no mínimo2GiB ou20%. Recovery mede banco, arquivos de dados e storage; inclui dump+restauração, extrações e WAL. Host e filesystem Docker são conferidos. O antigo limite fixo3GiB foi removido. A reserva de build15GiB NÃO foi reduzida.

O artefato FULL final ainda não existe nesta evidência. O cenário de provisionamento em `production-capacity-planning-scenario.json` usa 200mil itens, JSON nacional até1,5GiB, banco limpo2GiB, bundle decodificado1,5GiB e metadados4MiB. Esses valores são entradas explícitas de planejamento, não uma medição do corpus final. Resultados do modelo:

| Etapa | Folga incremental no início |
| --- | ---: |
| Instalação limpa, com estimativa conservadora antes do primeiro banco | 16.20 GiB |
| Reimportação nacional + maior UF, PG já medido | 18.68 GiB |
| Backup e restore isolado | 10.70 GiB |

A instalação, J11 e o build deixam arquivos/bancos que reduzem a folga antes de J09. Para provisionamento, reservar **40GiB livres** no ambiente de execução permite um build final, snapshots principal/J11 e QA em sequência, com margem sobre o cenário. Isso não é um limiar universal nem prova de que FULL precisa exatamente40GiB; os guards recalculam o necessário com o bundle congelado e o PG efetivo. O mínimo comprovado neste momento é15GiB apenas para iniciar o build, ainda indisponível.

## Redução de pico e retomada

- `data/bundles` foi excluído do contexto padrão e do fallback: atualmente cerca de214MiB por cópia evitada; artefatos continuam no host, montados por Compose. Manifests, schemas e provas do parser continuam incluídos. Não foi executado build para medir o novo pico.
- Ordem planejada: produção limpa → J09 → recovery. J09 só remove exports novos desta rodada e temporários após hashes e confronto integral com SQL; banco descartável tem nome aleatório e é removido em finally. Jobs preexistentes e artefatos de falha são preservados.
- Recovery só remove seu banco restaurado aleatório e cópias extraídas após prova completa. Backups privados e volumes permanecem. Cleanup tem recibos e intenção registrada antes de apagar temporários; SQL delete de job precede unlink para não deixar job succeeded apontando arquivo removido em falha de SQL.
- Não executar J11 fresh enquanto imagem/tag/default não estiverem congelados e verificados. Os jobs históricos pausados e o defaultca77 continuam preservados.

## Verificação desta preparação

Typecheck/lint passaram. Três testes passaram: orçamento FULL não aceita3GiB nem usa tamanho gzip para downloads; maiores dados elevam o pico e tamanhos inválidos são recusados; cleanup real em diretório temporário mantém irmãos, recusa SHA divergente, traversal e symlink. O negativo REAL de produção com tag inexistente terminou antes de criar qualquer env/volume/serviço (`qa-image-guard-before-env-negative.json`). Nenhuma execução positiva de produção/reimport/restore ou J11 foi realizada nesta rodada; dependem de dados/imagem congelados e capacidade.
