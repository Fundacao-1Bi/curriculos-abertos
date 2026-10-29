# Compositor com proveniência técnica e autoridade SQL

A implementação está em `src/domain/ingestion-provenance.ts`, integrada a `src/domain/ingestion-update.ts`. Ela não altera parser nativo, Source, cache, BASE ou RAW original. O candidato global continua privado até publicação explícita com CAS da base.

## Contrato para o worker

1. Preserve o checkpoint RAW original. Execute o estágio raster versionado e guarde o recibo de transição imutável com seu SHA externo. RN/não AM mantém original e efetivo exatamente iguais por caminho/ID/SHA; AM pode produzir outro RAW efetivo sem substituir o original.
2. Chame `evaluateIngestionProvenance({effective_raw_receipt, job_scope, receipt_directory, signal?})`. `job_scope` contém `base_publication`, `base_publication_sha256`, `base_artifact_sha256`, `target_source_ids` e `context_source_ids`. O helper executa a CLI pinada em `evaluate`, com arquivos de entrada completos e imutáveis, e retorna `{path,sha256}` do recibo de avaliação.
3. Passe o RAW **efetivo** ao `prepareGlobalIngestionUpdate` e acrescente:

```ts
provenance: {
  original_raw_receipt: {publication, artifact, artifact_sha256},
  raster_stage_receipt: {path, sha256}, // ou null quando não houve etapa raster
  technical_evaluation_receipt: {path, sha256},
  receipt_directory: `var/jobs/${jobId}.provenance`
}
```

Os caminhos são relativos ao workspace; artefatos ficam em `data/bundles/` e recibos em `var/`. A etapa raster AM é obrigatória para os quatro Sources AM reconhecidos. A presença de qualquer campo de ledger técnico, mesmo vazio ou malformado, exige o protocolo; a CLI então valida o formato sem fabricar eventos. Chamadas legadas para fontes sem esse contrato continuam possíveis.

4. O retorno possui `raw_receipt` do efetivo e `provenance_receipt`, além do artefato global e prova de preservação já existentes. Guarde também os inputs `provenance` no resultado privado do job. Não compare o efetivo AM ao checkpoint original como se fossem o mesmo artefato.
5. Na retomada, valide a cadeia original/estágio/efetivo e chame `revalidatePreparedIngestionProvenance(input, candidatePublication)`. Esse helper revalida os recibos, código, provas, RAW e captura SQL, confrontando os digests com o cabeçalho salvo, sem recompor o grafo global. A verificação independente de preservação fora do alvo e o CAS de publicação continuam necessários.

## Autoridade da captura

O compositor lê os IDs procurados na avaliação, confronta-os com os eventos e consulta **a publicação PostgreSQL pinada e publicada**. Nenhuma captura JSON fornecida pelo chamador é aceita como prova de SQL. O recibo declara todos os IDs efetivamente consultados, inclusive ausentes, e somente os registros retornados.

A captura usa `payload::text` em lotes de até oito itens, sem converter números JSONB em `Number` de JavaScript. Inteiros acima de 2^53 e decimais precisos permanecem exatos. O arquivo é limitado a 64 MiB, escrito com modo 0600, sincronizado e publicado por link exclusivo; um destino existente com bytes diferentes é conflito, nunca sobrescrito.

A CLI `contextualize` é executada pelo domínio e reavalia RAW, ledgers e provas reais antes de produzir identidade. O domínio confere novamente efeitos de presença/ausência/Source/hash do texto contra sua consulta SQL. Antes e depois documentados são distintos: ID ausente permite correção histórica; texto atual igual ao before permite correção; igual ao after é idempotente; um terceiro texto presente é conflito e falha fechado.

## Identidade e imutabilidade

`orchestration_provenance` guarda recibos original/efetivo, pins do estágio raster, SHA externo e digest interno separados, identidade/produtor/CLI técnicos, avaliação, captura SQL e inventário de código/dependências. Os digests `orchestration_sha256` e `technical_events_sha256` entram no ID global e no cabeçalho. Eventos de `extraction_correction` são acrescentados ao changelog com base e efeito observados, sem representar alteração oficial ou equivalência curricular.

Os hashes dos arquivos de runtime são observados quando o módulo é carregado e comparados antes/depois do trabalho. Uma edição em disco anterior à chamada não pode rotular o código antigo em memória com o hash novo. São pins dos Sources de execução observados; a correspondência entre imagem compilada e Source depende adicionalmente do fingerprint de build/distribuição verificado por operações. As dependências de validação/serialização e os arquivos de lock também entram na identidade. Código alterado exige processo/imagem correta e nova identidade; não se relaxa a checagem para retomar.

Recibos/provas/código/RAW são reconferidos antes de concluir a composição. BASE e publicações anteriores ficam imutáveis; os checks fora do alvo, referências, cobertura atribuída por Source, relações muitos-para-muitos e CAS continuam ativos.

## Cancelamento e limites

`signal` opcional é propagado à CLI e aos limites de fase/lotes/geradores do compositor. Cancelamento da CLI aguarda `close`, envia SIGTERM e mantém escalada para SIGKILL após cinco segundos. Aborto durante a escrita do artefato impede commit/import posteriores; arquivos concluídos ou snapshots privados já importados podem existir se a solicitação chegar depois dessas fronteiras, mas o cancelamento não publica o candidato. A transação de importação já em curso não recebe cancelamento assíncrono por registro. O worker precisa ligar seu mecanismo de parada/pausa ao `signal` e reconferir lease antes de finalizar o resultado.

Os envelopes de identidade usam apenas contagens inteiras seguras; payloads numéricos do corpus não passam pelo canonizador desses envelopes. A ordenação das chaves usa Unicode por codepoint, compatível com Python, inclusive caminhos de prova não ASCII. Até 10.000 IDs podem compor o denominador de uma captura; excedentes são rejeitados explicitamente.

## Verificação executada

Dez testes passaram sem skips em PostgreSQL 17.11 descartável próprio, com cleanup confirmado. Cobrem captura numérica precisa, ausentes, SHA/base publicada, replay, conflitos de arquivo/publicação, mutação e repin de prova, ID global, changelog, preservação externa, muitos-para-muitos e CAS. `typecheck`, ESLint dos arquivos alterados e interoperabilidade dos dois recibos reais Python↔TypeScript passaram. Logs e runner reproduzível: `docs/evidence/domain-orchestration-verification/`.

O peer inicial encontrou três P2; todos foram corrigidos e o follow-up está registrado separadamente em `docs/evidence/source-audit-domain-orchestration-peer/`. Instalação nacional, ensaio HTTP/worker AM/RN/PI real, full suite depois do freeze e prontidão nacional não são cobertos por esses testes pequenos. Nenhum banco QA/principal ou default foi acessado por este ensaio.
