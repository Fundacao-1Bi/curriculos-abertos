# Pipeline documental e distribuição

O corpus é construído de fontes identificadas em `data/manifests/*.json`. A aquisição de um PDF, sua extração, a conferência literal e a reconciliação de todas as partes são estados diferentes. Uma fonte obrigatória indisponível continua no denominador. `include_in_corpus:false` ou `publication_eligible:false` impedem a emissão de registros; somente uma exclusão documental explícita com `mandatory:false` retira uma fonte do requisito.

## Execução

Use Python 3.11 e as versões de `pipeline/requirements.txt`. O ambiente local verificado é `var/venv-pipeline/bin/python`; o antigo `.venv` Python 3.9 não é o ambiente de produção.

```sh
python3.11 -m venv var/venv-pipeline
var/venv-pipeline/bin/pip install -r pipeline/requirements.txt
var/venv-pipeline/bin/python -m unittest discover -s pipeline/tests -v
TESSDATA_PREFIX="$PWD/var/tessdata" scripts/data-ingest.sh --source fonte-id --job-id revisao-fonte
TESSDATA_PREFIX="$PWD/var/tessdata" var/venv-pipeline/bin/python pipeline/batch.py --workers 4
var/venv-pipeline/bin/python pipeline/preflight.py
scripts/data-ingest.sh --cached-only --job-id empacotamento-consolidado
var/venv-pipeline/bin/python pipeline/release_check.py --json
```

`--cached-only` não adquire nem extrai documentos faltantes. O empacotamento enumera também as fontes não processadas. `--skip-ocr` é uma opção diagnóstica e deixa digitalizações pendentes. Cada job mantém checkpoint próprio em `var/jobs/{id}.json`; falhas preservam o último ponteiro válido. O worker importa o artefato desse checkpoint como preparado, usando seu hash. A promoção administrativa é uma ação separada.

## Segurança e procedência

O downloader permite HTTPS nos hosts registrados, verifica cada redirecionamento, limita tamanho/tempo/tentativas e fixa a conexão ao endereço público validado. PDFs são dados não confiáveis; o worker não executa seu conteúdo. Os originais e caches privados ficam fora do Git. Evidências públicas identificam fonte, hash, página e caixa; não redistribuem automaticamente todos os PDFs ou suas imagens.

O parser usa PyMuPDF 1.26.7. O OCR registra versão real do Tesseract, hash do modelo português e de orientação, configuração e rasterizador. Modelos Debian e tessdata_fast podem diferir: a chave de cache incorpora esses dados, sem reutilização silenciosa entre ambientes distintos. A instalação do portal consome o corpus distribuído; reconstruir a partir dos PDFs é um processamento explícito e auditável.

Os direitos das fontes permanecem com seus titulares. O conjunto reutilizado `bncc-dev/bncc-dados` é atribuído sob CC BY 4.0. A biblioteca PyMuPDF tem licenciamento AGPL/comercial; os avisos e obrigações de distribuição da dependência não são substituídos pela licença MIT do código próprio.

## Texto, códigos e estruturas

Texto canônico conserva redação, grafia e pontuação. Normalização de busca é um campo derivado. Códigos locais, sufixos e anomalias impressas são preservados. Uma convenção de código não demonstra equivalência curricular. Regras documentadas produzem relações com origem e evidência próprias; sugestões lexicais automáticas permanecem candidatas sem validação pedagógica.

Adaptadores de documentos sem código conservam tipos, hierarquia, posição explícita e fragmentos multipágina. Relações de parentesco estrutural não se transformam em pré-requisitos pedagógicos. Um `secao_normativa` conserva contexto e não conta como habilidade estruturada. Revisores automatizados são identificados como automatizados.

Controles NUL no texto canônico, código ou evidência bloqueiam a publicação. Quando aparecem apenas em contexto técnico secundário de um PDF com codificação defeituosa, são transportados por escape literal reversível, com caminho, original UTF-8 em base64 e SHA-256. Isso conserva a informação original e não declara uma interpretação de glifo oficial.

## Artefato imutável

O formato `curriculos-abertos/sharded-v1` usa um manifesto JSON e partes JSONL gzip. Cada parte contém no máximo 5.000 registros e 20 MiB decodificados; um registro não pode ultrapassar 8 MiB. Gzip usa `mtime=0`. O manifesto fixa schema e hash, fontes, cobertura, contagens e hashes compactados/decodificados. Itens precedem relações. A identidade é calculada a partir dos metadados e hashes das coleções, sem criar uma string nacional gigante.

Antes de atualizar `data/bundles/latest.json`, o validador verifica schema, todos os hashes/contagens, identidades, referências e ausência de ciclos. Esse sucesso é integridade técnica; o gate nacional continua exigindo inventário independente, todas as partes reconciliadas e amostras por recorte. `pipeline/preflight.py` agrega falhas sem escrever publicação ou esconder fontes inválidas.

## Contratos de posição e papel documental

`position_contexts` usa `page` ou `page_start`/`page_end`, etapa explícita e anos válidos quando documentados. Formatos não suportados, como `pages` e `item_positions`, bloqueiam o processamento em vez de serem ignorados. Esses contextos são fallback de itens genéricos: não sobrescrevem posições de adaptadores documentais que já identificaram a célula original.

`document_role_adapter` seleciona um enum do registry interno `pipeline/document_roles.py`; o manifesto não fornece caminhos Python ou expressões executáveis. Cada handler vincula regras geométricas a IDs e hashes de artefato conhecidos. As regras declarativas de PE FGB em `layout_rules` exigem hash, largura, limites e evidência literal do cabeçalho, inclusive sua semântica. Habilidades nacionais impressas na coluna de aprendizagem permanecem aprendizagens; articulações e citações em colunas secundárias conservam seu papel de referência e a redação integral em contexto.

A identidade do cache contém a revisão de extração, configuração da fonte, sidecars e revisão de posição, arquivos efetivos do parser e dependências transitivas do handler, Python, PyMuPDF e Pillow. Uma mudança durante o processamento é rejeitada. O cache OCR possui identidade própria com engine e modelos efetivamente usados. Uma extração encerrada sem erro de OCR ainda pode ter códigos impressos não transcritos e revisão literal pendente.

O inventário de lacunas `pipeline/denominator.py` parte dos glifos e células do PDF, compara definições, referências e papéis desconhecidos ao artefato informado e mantém páginas raster sem denominador independente como pendência. Seu diagnóstico compartilha parte da geometria com o parser e não substitui reconciliação editorial independente. Ausência de ocorrências reconhecidas nunca comprova ausência de aprendizagens.

O manifesto também fixa `producer_fingerprint`, separado do cache por fonte: hashes do parser, associações, writer, leitor de contexto, validador e schema. Alterar o writer não exige fingir uma nova extração de itens, mas o novo artefato identifica os bytes do gerador usado.
