# Contrato de augmentação de referências AM na atualização por fonte

Revisão de domínio acordada com pipeline em 28/10/2026. Documento de contrato para implementação/ensaio posteriores; não afirma que worker, QA, imagem atual ou servidor já executam essa etapa. Nenhuma alteração de TS/parser, schema ou banco foi feita para aprová-lo.

## Ordem e identidade

O fluxo futuro de job é `original_raw_receipt` → produtor de augmentação → `effective_raw_receipt` → `prepareGlobalIngestionUpdate` → candidato global privado. O RAW original e seu checkpoint não são reescritos para fingir que já continham referências. Há recibo separado de transição por job:

- `original_raw_receipt`: ID, caminho e SHA originais imutáveis.
- `augmentation_receipt`: versão/fingerprint do produtor, pin do overlay/provas, fontes-alvo, invariâncias e contagens reais.
- `effective_raw_receipt`: artefato passado ao domínio. Em AM recebe ID/SHA novos derivados do conteúdo; sem alvo AM é o **mesmo** caminho/ID/SHA original, sem recompressão ou mudança de metadata.

Uma augmentação de BASE completa é um modo diferente de recibo parcial de atualização. Não rotular um BASE com todas as fontes como se fosse `source_update_receipt`, nem passá-lo ao helper de substituição parcial.

No modo de atualização, conservar exatamente `publication_kind=source_update_receipt`, `base_publication`, `base_publication_sha256`, `base_artifact_sha256`, `target_source_ids` e `context_source_ids`. `base_publication_sha256` é o checksum da publicação fixada no PostgreSQL; **`base_artifact_sha256` é o SHA do artefato de contexto nacional BR pinado no job e pode ser diferente**. Os dois não são intercambiáveis.

O domínio retorna `raw_receipt` para o artefato **efetivo** que recebeu. Worker/QA atualmente comparavam esse ID ao RAW Python original; a integração precisa guardar a cadeia e comparar o efetivo depois da augmentação, preservando o original. Em RN/bypass a igualdade original=efetivo continua válida. Nenhuma troca de recibo pode promover dados automaticamente.

## Escopo e registros

Só acrescentar referências dos `target_source_ids` explicitamente fixados que pertençam aos Sources AM esperados e cujo hash de artefato seja igual ao da prova primária. Um overlay de outra fonte/revisão é erro fechado, não permissão para preencher por similaridade de código. Em RN ou outro alvo sem AM, devolver o RAW original sem alteração.

Referências exclusivamente de código não são novas habilidades:

- `kind=referencia_no_documento`, `positions=[]`, sem relações criadas, sem pai inventado.
- Código/literal comprovados por glifo; o texto canônico é o identificador/trecho realmente impresso, não uma narrativa fabricada. Explicações do projeto pertencem a `editorial_note`/metadados.
- Evidência de fonte/página/região/trecho e pin do artefato/prova; método e revisão de código por ator automatizado. Código conferido não equivale a texto de habilidade revisado ou revisão pedagógica humana.
- IDs técnicos estáveis e escopados por fonte/localizador/ocorrência. Colisão com payload diferente deve falhar; só deduplicar o mesmo ID se o payload completo for idêntico.

Preservar todos os registros originais do RAW, Sources e contexto BR, inclusive texto, evidência, posições, grupos/revisões e números. O overlay é aditivo no escopo autorizado. Não atribuir etapa, ano, idade ou equivalência pela gramática de um código. O conjunto `LEARNING_KINDS` permanece sem referências de código.

## Manifesto, repetição e cobertura

Produzir artefato novo em partes limitadas, validar todos os pins e schema, recomputar contagens, checksums e identidade das coleções. Não herdar `content_identity` antigo como atual. Citar o RAW anterior como proveniência, sem alterá-lo. Registrar a versão do produtor e as provas de modo reproduzível; replay do mesmo job/inputs precisa conservar a mesma identidade efetiva.

Contagens de referências sem posicionamento ficam explícitas. Não distribuí-las por todas as etapas/componentes do documento nem promover completude editorial. Partes esperadas/reconciliadas e pendências sem texto de aprendizagem permanecem como estão; eventuais totais derivados afetados devem ser recalculados conforme o modelo, não somados cegamente. Nenhuma condição de pronto/SourceWhole/UF/nacional nasce do número de códigos reconhecidos.

## Ensaios necessários

Primeiro validar em arquivos/var, sem mutar o runtime congelado. Depois, em banco/instalação descartável coordenados com operações, nunca no padrão principal:

1. AM alvo: referências legítimas presentes e schema/localizadores válidos; todos os dados não afetados preservados.
2. Mesmo job/replay: sem duplicação nem troca da base pinada; RAW original e transição reproduzíveis.
3. RN alvo sobre BASE com AM augmentado: bypass exato e preservação independente de todas as referências AM fora do alvo.
4. Negativos: pin de fonte divergente; item fora dos alvos; contexto BR alterado; colisão de ID/payload; troca de base/CAS concorrente.
5. Conferir publicação privada, cadeia de recibos e `verifyGlobalIngestionPreservation`; somente ação autorizada posterior pode publicar.

Uma chamada de domínio isolada não comprova o novo caminho de worker/HTTP. Para J11 será necessário alinhar worker/checkpoints/QA, construir a imagem correspondente e executar a jornada real. A instalação diagnóstica do BASE parcial não substitui esse aceite, reconciliação nacional ou desempenho final.
