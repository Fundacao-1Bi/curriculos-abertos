# Maranhão — fontes curriculares atuais

Pesquisa de `agent:rs_adapter:ma-current-inventory`, ator automatizado. Arquivos originais e renders permanecem privados, fora do versionamento. Não há declaração de prontidão do Maranhão ou de completude de aprendizagens.

A notícia oficial [sobre a formação dos GAEMs](https://www.educacao.ma.gov.br/seduc-realiza-formacao-dos-gaems-para-fortalecer-o-planejamento-do-ano-letivo-2026/) foi publicada em **15/01/2026** e relata atividades iniciadas no dia 13. Ela informa revisão de matrizes e guias por componente; não identifica sozinha a edição, adoção ou vigência dos arquivos encontrados depois. A notícia [de 03/11/2025](https://www.educacao.ma.gov.br/seduc-realiza-2o-ciclo-de-escutas-e-dialogos-pedagogicos-com-professores-de-todo-o-maranhao/) também descreve a preparação dos organizadores para 2026. Os snapshots públicos estão preservados por hash em cache privado.

O índice de busca do SUGEDA apresenta **21 rótulos de PDFs** nas páginas Ensino Médio/componentes: 20 candidatos novos e um candidato ao DCTMA volume II já registrado. O mesmo título de matrizes aparece em Gestão Escolar; não foi contado novamente. Esse inventário foi estabelecido por grupos e nomes visíveis antes da aquisição, sem usar códigos como denominador. **Rótulos não provam identidade dos PDFs, obrigação ou datas editoriais.**

Os acessos diretos às três páginas do Google Site consultadas redirecionam para autenticação. O script interrompe nesse ponto, sem credenciais. Não foram obtidos os IDs embutidos ou bytes dos quatro GPD, matrizes e demais recursos desse catálogo. As consultas de páginas e busca pública da SEDUC localizaram notícias e materiais antigos, mas não uma cadeia de hyperlink governamental explícita até o Site SUGEDA. A ausência nessas consultas não prova que os arquivos não existam.

A Resolução **CEE/MA 211/2026** foi adquirida no [Diário Oficial estadual](https://diariooficial.ma.gov.br/download.php?arq=EX20260731): documento de 21/07/2026, publicado em 31/07/2026, edição 136 do Executivo. O original possui 38 páginas; somente as regiões curriculares nas páginas 20–21 pertencem à fonte proposta. O recorte conserva seis artigos e todas as assinaturas, inclusive a continuação no topo da coluna direita da página 21. A conferência visual e geométrica independente excluiu os atos de Meio Ambiente/Cultura e demais matérias alheias.

O ato aprova o DCTMA de Educação Digital e Midiática como complemento normativo para a Educação Básica. Sua vigência na publicação e a adequação progressiva das redes são fatos distintos dos prazos operacionais que o artigo 5 remete a ato posterior. O **documento curricular integral continua obrigatório e pendente de localização**; o ato não o substitui. Não foi demonstrada identidade entre esse complemento e o arquivo de orientações de Educação Digital do catálogo específico do Ensino Médio.

Evidências principais:

- `catalogue-access-and-government-chain.json`: 13 consultas públicas, snapshots por hash, redirecionamentos de autenticação e links encontrados.
- `indexed-catalogue-inventory.json`: os 21 rótulos e sua tipologia provisória; sem URLs de PDF ou datas inventadas.
- `acts/`: aquisição, recortes e proposta de cinco atos originais: três curriculares obrigatórios propostos e dois programáticos com tipologia pendente. São 638 páginas de diário originais, não 638 páginas curriculares.
- `region-peer-review.json`, `region-peer-review-162-181.json`: segunda conferência automatizada de três atos adquiridos, com 41 artigos e anexo da recomposição preservados.
- `complement-location-search.json`: busca do complemento integral, distinguindo citações oficiais de aquisição do currículo.
- `checkpoint.json`, `proposal-schema-check.json`: contagens, hashes e validação das seis propostas Source em schema 1.1.0.

Comandos executados:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ma-current/catalogue_probe.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ma-current/build_inventory.py
var/venv-pipeline/bin/python docs/evidence/source-audit-ma-current/build_proposal.py
```

A proposta de fontes fica em suplemento fora do carregamento automático. A frente Nordeste integrou a Resolução 211 e o registro obrigatório pendente do complemento, além da Portaria 181. A confirmação somente-leitura dos metadados, hashes e regiões está em `northeast-metadata-recheck.json`. Os três atos de tipologia pendente continuam visíveis no suplemento. A integração única ao manifesto é responsabilidade da frente Nordeste. Permanecem abertas a aquisição dos referenciais atuais, a tipologia dos materiais de apoio e a reconciliação integral das aprendizagens.

Na revisão de tipologia, a Resolução 162 foi preservada entre as pendências: ESC02 não torna automaticamente obrigatória a coleta de documentos específicos de modalidades. A condição de parte indispensável do referencial selecionado ainda precisa de decisão documental pela frente Nordeste. As datas e o recorte já verificados permanecem preservados.

Os dois atos curriculares acessíveis foram posteriormente estruturados integralmente em 95 nós, 118 fragmentos e 726 linhas, com importador/finalizador reais e peer automatizado aprovados. A metodologia, hashes e comandos estão em `ma-normative-adapter.md`; as referências a matrizes/materiais de recomposição ainda não adquiridos estão em `reference-materials-gap.json`. Esses resultados não abrangem os GPD ou o complemento digital integral.
