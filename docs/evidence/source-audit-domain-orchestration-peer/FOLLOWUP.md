# Follow-up do peer técnico independente

28/10/2026. Relatório original `README.md` e seus controles foram preservados. Esta revisão cobre somente os três P2 daquele snapshot. Não executou SQL, Docker, build, carga ou import de dados; produto não foi editado. Executou controles com fontes TS transformadas em memória, dependências de SQL/artefatos substituídas, validador real de Source e um subprocesso de teste próprio. Arquivos temporários de helper/PID/módulo foram removidos e o PID próprio foi confirmado ausente.

**Resultado: os três P2 foram tratados no novo snapshot. Nenhum achado novo bloqueante nesse delta; PASS técnico limitado.** Não constitui aprovação nacional/FULL/UF ready nem prova da jornada real de worker/HTTP ou imagem implantada.

## Reavaliação

1. **Gate fechado — PASS.** `src/domain/ingestion-update.ts:107-108` exige o protocolo por presença própria de ambos os campos técnicos. Validação real do Source 1.1.0 e execução do guard com stubs confirmaram `INGESTION_PROVENANCE_REQUIRED` para array vazio, array não vazio, objeto, null e string em cada campo. Ausência permanece no caminho legado. Array vazio exige avaliação que pode produzir zero eventos; o guard não fabrica eventos.
2. **Drift após carga — PASS com limite explícito.** `src/domain/ingestion-provenance.ts:25-26,118` fixa bytes observados no carregamento do módulo e compara com os bytes atuais antes da preparação. Controle com armazenamento de fingerprint em memória confirmou aceitação inicial e rejeição `INGESTION_PROVENANCE_MISMATCH` após mudança; nenhum runtime real foi alterado. O ajuste detecta drift posterior ao carregamento deste módulo. Não é uma atestação criptográfica do código compilado/em memória, de dependências carregadas anteriormente ou da imagem: identidade de build/imagem imutável continua uma prova externa necessária quando se alegar execução de release exato. O Dockerfile atual copia `/app` completo, incluindo as fontes exigidas pela leitura síncrona; não foi feito build para validar imagem.
3. **Cancelamento — PASS das janelas testadas.** `src/domain/ingestion-update.ts:103,106,127,132,151-157` verifica sinal no início, depois do RAW, durante batches/geradores e após writer/antes de commit/import. Controle que abortou dentro do writer confirmou 1 rollback, 0 commits, 0 imports. `src/domain/ingestion-provenance.ts:61-74` removeu o signal automático do spawn, aplica listener próprio e espera `close`. Um helper próprio ignorou SIGTERM: a promise continuou pendente aos 100 ms, encerrou com o motivo de aborto original após **5004 ms**, e o PID estava ausente; isto comprova a escalada SIGKILL no caso exercitado.

Cancelamento durante operação SQL ou import já em voo permanece cooperativo: não cancela instantaneamente uma query nem desfaz um import privado que já tenha concluído. O código verifica sinal após import e não publica por esse caminho. Isso é coerente com o limite aceito no follow-up; não foi apresentado como garantia de zero artefatos privados para qualquer instante de aborto.

## Evidências reproduzíveis

- `followup-controls.mjs`, executado por `node_modules/.bin/tsx docs/evidence/source-audit-domain-orchestration-peer/followup-controls.mjs`.
- Resultado estruturado: `followup-controls.json`. As fontes avaliadas e seus hashes estão registrados nele. SQL e verificação de artefatos foram isolados; isto não substitui testes de banco.
- Log existente relido: `docs/evidence/domain-orchestration-verification/sql-tests-after-peer.log`, **10/10 aprovados, zero skips/falhas**, e remoção do container owned ao final. SHA-256 do log: `08642096bb89a133d43f9099535d56f271eb7a19aebfcf3d4a4dd6c90984d66c`.

## Snapshot revisto

```
8d37ab39c750d87f93e4fac77221433418774f06d85b7779bf151f54ccabe94c  src/domain/ingestion-provenance.ts
6315fbebdd40eff7696cdcb37c7ed031145e4cc1c04ea2fc4cb589b20127b1ab  src/domain/ingestion-update.ts
eebaf49eaaaead66de8c2a8499e94fbba3ef9d9acea594582b762a6ab361ea14  tests/domain.ingestion-provenance.test.ts
107d13c3d7e3030fec70b533306b16314e491fa68acb1783fa5905b1cf555318  tests/domain.ingestion-update.test.ts
```
