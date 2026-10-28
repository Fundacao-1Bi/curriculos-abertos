# Contrato de reconciliação documental

Revisão automatizada é identificada como tal. Conferir amostra não é conferir o conjunto inteiro. A extração de páginas é uma etapa; a reconciliação exige confrontar os componentes e partes do inventário independente com os itens estruturados, verificando perda/duplicação/troca de código e texto.

As fontes permanecem em `data/manifests/{lote}.json`. O denominador usa `normative_parts`, `stages`, `components`, `inventory_evidence` e tipologia. Artefatos alternativos e modalidades fora do escopo podem usar `mandatory:false` com `exclusion_reason`/`replacement_source_id` documental; a omissão de uma parte necessária não pode ser excluída assim. `include_in_corpus:false` guarda metadados, sem duplicar registros de uma apresentação alternativa do mesmo conteúdo.

O parser gera `data/extracted/{sha256}-page-cell-v1.4.0.json`: `pages` com texto literal e hash; `items` com fonte, código completo, tipo, página, tabela/linha/célula e caixa; `warnings` e contagens. O array `code_mentions` é diagnóstico de todas as menções, incluindo citações. Não é o denominador de habilidades. Itens `secao_normativa` preservam contexto documental e não são contados como habilidades. Partes sem código precisam hierarquia/tipo próprios e não podem ser apagadas para atingir uma contagem.

Cada fonte pode ter registro de revisão em `data/manifests/reconciliation/{source_id}.json`:

```json
{
  "source_id":"source-id",
  "artifact_sha256":"64-hex",
  "extraction_revision":"page-cell-v1.4.0",
  "actor_type":"automated",
  "actor_id":"agent:source-reviewer",
  "method":"Conferência independente do sumário, contagem dos itens nas tabelas e amostragem estratificada de células",
  "parts":[{
    "name":"Nome exato de normative_parts",
    "expected_item_ids":["IDs derivados do inventário documental, não simplesmente copiados de todos os itens extraídos"],
    "verified_item_ids":["IDs cujo contexto/código/texto/localização foi verificado"],
    "expected_components":["Componente conforme documento"],
    "page_ranges":[[1,20]],
    "sample_item_ids":["ID amostrado"],
    "evidence":[{"page":5,"section":"Sumário","excerpt":"Trecho literal","verification":"O que foi efetivamente conferido"}],
    "findings":[]
  }]
}
```

Os IDs esperados e verificados precisam coincidir sem conjunto vazio, hash e revisão devem corresponder à extração e evidências devem ser localizáveis. Problema sistemático bloqueia a parte e exige reprocessar o conjunto, sem corrigir só a amostra. Quando ainda não existe denominador suficiente para atestar completude, registre a inspeção em `docs/sources-{lote}.md`/`inventory_evidence` e mantenha a reconciliação pendente. Não fabricar listas ou marcar prontidão para contornar o gate.

Comandos:

```sh
scripts/data-ingest.sh --source fonte-id --job-id revisao-fonte
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python pipeline/batch.py --workers 4 --skip-ocr
scripts/data-ingest.sh --cached-only --job-id empacotar-cache
var/venv-pipeline/bin/python pipeline/release_check.py --json
```

`--skip-ocr` deixa páginas digitalizadas pendentes; a execução posterior sem esse sinalizador precisa processá-las com OCR antes da reconciliação.
