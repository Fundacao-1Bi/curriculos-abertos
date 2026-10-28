# Relatório de entrega — em execução

Este relatório não declara MVP nacional concluído. O critério é ACE-02 da especificação integral, não a existência de código, UFs no catálogo ou PDFs baixados.

## Produto integrado

Portal Next.js em modo de produção local executado em http://localhost:3000; API /api/v1, documentação /desenvolvedores/openapi e MCP Streamable HTTP /mcp. PostgreSQL dedicado em localhost:55437 e worker persistente. Administração autenticada /admin. Não foi indicado alvo remoto autorizado e não houve implantação remota.

A primeira publicação técnica `ca-64e60bb2c92be368dcd7` contém2.108 itens extraídos reais de SP,131 fontes inventariadas naquele snapshot e zero relações; é candidata e não atende ao lançamento nacional. Publicações posteriores serão descritas após importação e verificação; o ponteiro concreto é data/bundles/latest.json.

## Verificação executada até este checkpoint

- Builds de produção locais, TypeScript e lint executados. Fonte continua sendo integrada, portanto evidências finais serão vinculadas ao fingerprint final.
-12/12 testes de contrato/domínio/release, PostgreSQL descartável real, zero skips.
- Cliente MCP oficial negociou Streamable HTTP e descobriu dez ferramentas; busca/lote/paginação comparados comAPI. Teste completo permanece reprovado semBNCC no piloto.
-54 verificações HTTP iniciais passaram nos recortes existentes, incluindo contribuições persistentes e exportaçõesJSON/CSV realmente geradas/download/checksum. Resultado global reprovado pela ausência deBNCC.
- E2E desktop/mobile da jornada de busca e páginas públicas passou após corrigir encodedIDs e acessibilidade da marca. Jornadas nacionais completas ainda não executadas sobre o corpus final.
- Administração/autorização/contribuição/draft parcialmente verificadas. Revisão de relação/publicação/rollback dependem do novo corpus com relações.
- Compose clean install, backup/restore e desempenho final ainda não verificados neste checkpoint. Scripts existem, o que não comprova execução.

## Dados e bloqueios

Pesquisa e aquisição das27UFs em andamento com manifestos por lote. Reprocessamento nacional v1.3 corrige códigos locais/LP/EMIF e fronteiras de células. Aquisição, extração, reconciliação e prontidão são estados distintos. Fontes indisponíveis específicas e alternativas tentadas constam nos relatórios docs/sources-*.md; implementações/validações pendentes não são reclassificadas como bloqueios externos.

Distribuição Docker em execução de testes; pulls/builds de imagens nesta instalação têm mostrado espera sem progresso apesar de execução de containers oficiais locais e conectividade interna funcionando. O caminho alternativo legítimo é construir uma imagem a partir do runtime oficial cacheado por comandosDocker normais, sem reiniciar o daemon nem alterar o serviçoContentiZAP alheio. Resultado final ainda pendente.

Próximo passo reproduzível: docs/progress.md, docs/data-progress.md e var/jobs/national-extraction.json. `make release-check` deve recusar o estado incompleto; o resultado final será registrado em docs/verification.md e docs/evidence/release-check.json.
