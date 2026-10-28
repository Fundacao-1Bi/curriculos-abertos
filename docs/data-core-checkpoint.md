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

## Etapa corrente

O cache agora incorpora fingerprint de todos os arquivos do parser e versões reais do runtime. O worker rejeita mudanças de código durante a extração e preserva o cache anterior. Isso exige uma nova execução completa após congelar os helpers MA, AM e RS/MS. O batch anterior `page-cell-v1.4.0` terminou com 251 fontes/54.459 páginas, mas carregou código anterior a várias correções e não será apresentado como evidência do algoritmo final.

O preflight opcional `--native-literal` agrega também falhas literais de todos os registros nativos, incluindo os caches antigos para diagnóstico. Ele não exclui uma fonte que falha para aparentar sucesso.

## Pendências distintas

Internas: os leitores MA, ES, RN, PE, tabelas RS/MS e limites raster AM já estão integrados. A integração de posições físicas AM também está presente, aguardando os últimos vínculos de revisão no manifesto. BR já passou 1.721/1.721 habilidades no checker comum, com 394 locadores corrigidos e oito correções documentadas de pontuação primária, preservando texto upstream. As 12 continuações físicas ES estão no hook, sem append duplicado. O registry confiável de papéis documentais agora inclui RN, PE CEDIM, AL e as 12 novas fontes PE FGB; exige enum conhecido e guards de artefato nos handlers. Falta concluir as provas dos últimos vínculos, congelar o código como revisão 1.5.0, reprocessar todas as fontes acessíveis, executar preflight integral e consolidar shards para os verificadores independentes. Há pausa de novas escritas pesadas por pouco espaço em disco, em recuperação pelo responsável de operações; nenhum PDF/evidência foi apagado pelo pipeline.

Externas documentadas: original EM/AP com árvore de páginas corrompida; referência PB EM protegida por HTML/challenge; edição BA 2026 ainda não localizada; material MS 2023 cujo link oficial não entrega PDF; currículo computacional AC incorporado por norma sem artefato integral obtido; cópia AL Computação sem cadeia primária demonstrada permanece privada. Esses casos não justificam omitir documentos acessíveis e não são convertidos em ausência pedagógica.

Para retomar: leia este arquivo, `docs/data-pipeline.md`, `docs/data-reconciliation.md`, os manifests atuais e os relatórios de `docs/evidence/`. Não redefina publicações antigas, não use o `.venv` legado e não promova candidatos incompletos por sucesso de integridade técnica.

## Atualização incremental sem perda do corpus

`ingest --base-artifact caminho --base-publication ID --target-source-id fonte` gera um **recibo de atualização**, sem alterar `latest.json`. O contexto BR é validado com schema/hash/contagens e reaproveitado com IDs e conteúdo da publicação-base, sem fingir que caches de outro runtime foram reprocessados. O domínio faz o merge global limitado à fonte-alvo e preserva itens/fontes/relações/cobertura fora do alvo; promoção é separada.

Teste real `receipt-host-context-20261028`: publicação `ca-1570c340fa33b9a527f3`, SHA `14774517994bb804d890ebf48dbef8fea8c3113e6f99bb749d397d5b08827dd3`, 1.767 registros BR da base + 99 registros da fonte PE. O replay do mesmo job revalidou o mesmo artefato e não reprocessou nem alterou o ponteiro. Evidência: `docs/evidence/data-ingestion-context-e2e.json`. Isso não é o próximo corpus FULL e não foi promovido como nacional pronto.

Novas distribuições fixam `data/schema/1.1.0.json` (URL de artefato pode ser nula explicitamente quando não localizada), preservando o schema histórico 1.0.0 byte a byte. Fingerprints dos adaptadores são específicos das fontes que os usam; modificar um helper AM não valida nem invalida silenciosamente as extrações de outra UF.

A validação de position_contexts rejeita formatos silenciosamente ignorados (`pages`/`item_positions`), escopos de página inválidos, etapa ausente e anos inválidos. A varredura de 301 fontes encontrou quatro configurações legadas no Norte, encaminhadas ao proprietário para conversão documental. Provas por `pymupdf-native-glyph-cluster-v1` exigem região e source_id exatos e não alegam certificação de visibilidade.

Contextos genéricos por página/código não sobrescrevem posições de document_specific_adapter. O teste assimétrico preserva duas células do mesmo código/página em anos distintos e mantém o fallback para extrações genéricas. Não foi criado override sem prova.

Freeze final1.5.0/mapping1.2.0 registrado em docs/evidence/pipeline-core-freeze-v150-final.json. O freeze provisório foi preservado e nenhuma extração1.5 ocorreu antes do hook forte de reconciliação. Prontidão integral exige inventário, IDs/textos exatos, escopo completo e dependências de fontes verificadas; recibos parciais permanecem informativos. As associações de códigoOCR não conferido são candidatas automáticas, nunca declarações da fonte.
