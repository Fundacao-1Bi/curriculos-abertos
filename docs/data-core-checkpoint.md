# Checkpoint do pipeline — 28/10/2026

Estado de retomada: integração documental em andamento; **não é aceite nacional**. O último corpus servido pelo portal foi fixado pelo integrador separadamente. `latest.json` identifica apenas o candidato técnico validado, sem promoção implícita.

## Executado nesta retomada

- Pré-validação agregada: 162.867 registros, zero falhas de esquema, NUL, identidade, pais e provas literais de todos os adaptadores então vinculados. Evidência `docs/evidence/data-preflight.json`. Esse relatório inclui caches antigos para diagnóstico e declara fontes stale/pending; não transforma esses caches em atuais.
- GO EM: reextração integral de 1.397 páginas; 1.454 registros codificados, 1.458 fragmentos de evidência literais, zero âncoras faltantes, zero prefixos danificados ou duplicatas extras. Evidência `source-audit-go-em/extraction-comparison-summary.json`.
- MT EI: reextração integral de 76 páginas, 93 de 93 códigos únicos do inventário independente recuperados; reconciliação textual integral permanece separada.
- AM EM: reextração de 292 páginas confirmou o avanço da ordenação por linhas TSV; inspeção identificou um corte na linha do código seguinte. Helper raster/TSV próprio está sendo validado para todas as organizações do AM.
- NE: probes isolados sem alterar caches nacionais passaram 27 verificações: três referências CE não promovidas, 14 células PE com identificadores conjuntos, uma célula SE completa e nove âncoras BA recuperadas.
- PR: a fração bidimensional da página 858 mantém a redação e usa sete fragmentos com caixas próprias. O adaptador real passou 3.971 de 3.971 registros.
- PB: adaptador de 2.008 registros vinculado pelo proprietário da fonte, após verificação independente e prova de importação; inclui objetivos locais e referências separadas.
- DF/SC: hierarquias reais enriquecidas foram vinculadas e verificadas pelos proprietários. Anexos OCR SC usam a ordem TSV original comprovada por hash, sem reordenação por altura dos acentos.
- 52 testes de contratos e o caso negativo de remoção de um componente passaram. A fixture negativa é isolada e não altera corpus publicado.

## Estado atual após o FULL 1.5

O FULL `national-extraction-v150-20261028` já terminou: 285 fontes extraídas entre 286 tentadas, 56.705 páginas e 155.620 registros brutos. O parser congelado permanece no fingerprint `541aa3377fd409f9c172e1580ae988f5869b25e5331c98528ab68fb9a09360db`. A falha única é o original `ap-rca-em`, com árvore de páginas malformada. Os refreshes seletivos `national-extraction-v150-refresh-20261028`, `national-extraction-v150-refresh2-20261028` e `national-extraction-v150-refresh3-20261028` terminaram com sucesso.

O preflight literal integral terminou: 200.620 registros, 141.967 provas nativas, zero falhas de esquema/NUL/IDs/pais/ciclos, mas **3.012 falhas literais em 69 fontes**. Relatório: `docs/evidence/data-preflight-native-v150.json`; routing completo dos IDs e registros: `docs/evidence/literal-preflight-v150-routing/summary.json`. Essas falhas continuam pendentes, sem normalização ou retirada para limpar o gate. O processo levou 1.409 segundos, com RSS máximo de 3.914.891.264 bytes.

O refresh final `national-extraction-v150-refresh4-20261028` passou nas fontes `sc-cb-eief-2019-atual` e `ro-rcro-ef`: 1.083 páginas e 2.854 registros brutos. O pin `docs/evidence/base-full-v150-input-pin.json` fixou 303 fontes e zero configurações stale. Os candidatos ainda sem binding MS EI 197, PE EI 135 e RN IFA 146, além das correções de corpo MG/RJ/ES em elaboração, permanecem explicitamente fora dessa fotografia e exigem integração posterior comprovada.

O job `national-base-full-v150-20261028` concluiu com exit 0 e gerou o **intermediário diagnosticado** `ca-7d302a9c674a97b83278`, manifesto `data/bundles/ca-7d302a9c674a97b83278.manifest.json`, SHA256 `be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d`. São 200.724 registros e 57.425 relações em 75 shards, com integridade de schema, hashes, contagens, referências e hierarquia verificada. As 3.012 falhas literais continuam presentes com status pendentes; não houve exclusão para limpar o diagnóstico. `national_release_ready=false`; a publicação padrão do banco não foi alterada.

A matriz do BASE contabiliza 284 caches atuais, 12 fontes não elegíveis e sete fontes faltantes; zero stale. Dez fontes passaram WholeSourceV2 e 16 passaram OwnSourceV2; nenhum recorte UF/etapa está pronto. O delta de 104 registros em relação ao preflight é documental: RO EF acrescentou 167 entradas do wrapper e suprimiu 63 genéricos substituídos, conforme `docs/evidence/base-full-v150-count-delta.json`.

A montagem levou 469,47 segundos. O kernel mediu RSS máximo de 4.178.444.288 bytes; os shards totalizam 127.292.150 bytes comprimidos e 1.402.879.768 bytes decodificados. Esses números descrevem a execução técnica, não completude curricular.

O cache incorpora fingerprint do parser e versões reais do runtime; o worker rejeita mudanças de código durante a extração. O batch histórico `page-cell-v1.4.0` terminou com 251 fontes/54.459 páginas, mas carregou código anterior a várias correções e não comprova o algoritmo final. Seus arquivos continuam disponíveis aos leitores históricos.

## Pendências distintas

Internas: a extração e os helpers já estão congelados em 1.5.0. Falta fechar o preflight, os últimos refreshes e o BASE para QA independente. BR passou 1.721/1.721 habilidades no checker comum, com 394 locadores corrigidos e oito correções documentadas de pontuação primária, preservando texto upstream. Existem omissões documentadas ainda em tratamento por dados, incluindo PE EI, RN EM e uma redação de Energias ES; zero falhas literais não significa ausência de omissões. As referências raster AM confirmadas têm verificador separado e pinado, ainda sem binding ou integração no produtor nacional; elas não comprovam o corpo OCR. A reconciliação integral de cada fonte e suas dependências continua necessária.

Externas documentadas: original EM/AP com árvore de páginas corrompida; referência PB EM protegida por HTML/challenge; edição BA 2026 ainda não localizada; material MS 2023 cujo link oficial não entrega PDF; currículo computacional AC incorporado por norma sem artefato integral obtido; cópia AL Computação sem cadeia primária demonstrada permanece privada. Esses casos não justificam omitir documentos acessíveis e não são convertidos em ausência pedagógica.

Para retomar: leia este arquivo, `docs/data-pipeline.md`, `docs/data-reconciliation.md`, os manifests atuais e os relatórios de `docs/evidence/`. Não redefina publicações antigas, não use o `.venv` legado e não promova candidatos incompletos por sucesso de integridade técnica.

## Atualização incremental sem perda do corpus

`ingest --base-artifact caminho --base-publication ID --target-source-id fonte` gera um **recibo de atualização**, sem alterar `latest.json`. O contexto BR é validado com schema/hash/contagens e reaproveitado com IDs e conteúdo da publicação-base, sem fingir que caches de outro runtime foram reprocessados. O domínio faz o merge global limitado à fonte-alvo e preserva itens/fontes/relações/cobertura fora do alvo; promoção é separada.

Teste real `receipt-host-context-20261028`: publicação `ca-1570c340fa33b9a527f3`, SHA `14774517994bb804d890ebf48dbef8fea8c3113e6f99bb749d397d5b08827dd3`, 1.767 registros BR da base + 99 registros da fonte PE. O replay do mesmo job revalidou o mesmo artefato e não reprocessou nem alterou o ponteiro. Evidência: `docs/evidence/data-ingestion-context-e2e.json`. Isso não é o próximo corpus FULL e não foi promovido como nacional pronto.

Novas distribuições fixam `data/schema/1.1.0.json` (URL de artefato pode ser nula explicitamente quando não localizada), preservando o schema histórico 1.0.0 byte a byte. Fingerprints dos adaptadores são específicos das fontes que os usam; modificar um helper AM não valida nem invalida silenciosamente as extrações de outra UF.

A validação de position_contexts rejeita formatos silenciosamente ignorados (`pages`/`item_positions`), escopos de página inválidos, etapa ausente e anos inválidos. A varredura de 301 fontes encontrou quatro configurações legadas no Norte, encaminhadas ao proprietário para conversão documental. Provas por `pymupdf-native-glyph-cluster-v1` exigem região e source_id exatos e não alegam certificação de visibilidade.

Contextos genéricos por página/código não sobrescrevem posições de document_specific_adapter. O teste assimétrico preserva duas células do mesmo código/página em anos distintos e mantém o fallback para extrações genéricas. Não foi criado override sem prova.

Freeze final1.5.0/mapping1.2.0 registrado em docs/evidence/pipeline-core-freeze-v150-final.json. O freeze provisório foi preservado e nenhuma extração1.5 ocorreu antes do hook forte de reconciliação. Prontidão integral exige inventário, IDs/textos exatos, escopo completo e dependências de fontes verificadas; recibos parciais permanecem informativos. As associações de códigoOCR não conferido são candidatas automáticas, nunca declarações da fonte.

## Execução1.5 factual e atualização seletiva

O FULL real `national-extraction-v150-20261028` terminou em28/10/2026 às17:56:04UTC:286fontes tentadas,285extraídas,56.705páginas,155.620registros brutos. A única falha foi `ap-rca-em`, original com `code=7: malformed page tree`; o bloqueio não se estende às demais fontes. O espelho ES dos referenciaisIF foi deduplicado emmetadados, com prova binária idêntica aoBR14p; raw e conteúdoBR foram preservados.

O parser final permaneceu imutável (fingerprint541aa3377fd409f9c172e1580ae988f5869b25e5331c98528ab68fb9a09360db). O gate de reconciliação, separado doparser, ganhou proteção a identificadoresOCR explicitamente pendentes; partes textuais podem ser comprovadas sem falsamente declararSourceinteira pronta.53testes passaram.

Após integraçõesdata-only,29Sources/8.329páginas ficaram stale. O plano exato está em `docs/evidence/pipeline-refresh-plan-v150.json`; job `national-extraction-v150-refresh-20261028`, log `var/pipeline-national-v150-refresh.log`, sessão deexecução37674. Esse job contém somente os alvos do refresh e não substitui o checkpointFULL anterior. A lista deve ser recalculada contra Source/sidecars atuais antesdo empacotamento.

Monitor leve de árvore deprocessos/RSS e disco: `scripts/data-monitor-resources.py`. O refresh usa reserva de5GiB para suspensão reversível antes deEIO. Root/ops recuperaram espaço via compressão APFS transparente, mantendo paths/bytes/SHA dos JSONs. Não foram arquivados/removidos caches1.4. O rollbackantigo843MB deve permanecer.

O BASE sharded 1.5 já foi consolidado, como registrado no estado atual acima, sem promoção. Próximos: QA dos proprietários no manifesto pinado, diagnóstico das falhas literais, integração dos candidatos de dados ainda sem binding e inventário source-first de omissões. A auditoria NE detectou lacunas reais PE EI/RN EM; elas não são bloqueios externos e não permitem afirmar que todas as 159 amostras foram resolvidas.
