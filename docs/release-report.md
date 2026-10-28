# Relatório de entrega — integração em execução

Atualizado em 28/10/2026, 02:42 BRT. O MVP nacional **não está concluído**. O aceite é ACE-01/ACE-02 de [requirements.md](requirements.md): todas as partes obrigatórias das 27 UFs devem estar estruturadas, reconciliadas e verificadas. Ter fontes, registros ou interfaces não satisfaz esse critério.

## Produto implementado

Portal Next.js com busca, navegação por currículo e hierarquia, fichas com evidências, panorama nacional, comparação de duas/três UFs, análises, fontes, histórico e downloads. API REST em `/api/v1`, documentação em `/desenvolvedores/openapi`, MCP oficial Streamable HTTP em `/mcp` e transporte stdio. Administração autenticada, fila de contribuições, revisão com auditoria, preparação privada de publicações, publicação e rollback. Worker PostgreSQL persistente com checkpoint, pausa e retomada.

A distribuição utiliza Docker Compose, Node 22.23.4 e PostgreSQL 17.11. Um build padrão já foi executado e seu runtime foi conferido. App, worker e banco estão ativos e saudáveis na imagem técnica reconstruída. A imagem final ainda precisará incorporar os últimos ajustes de domínio, recuperação e interface administrativa. Não há implantação remota executada nem alvo remoto configurado. Endereços locais ativos: portal `http://localhost:3000`, administração `/admin`, API `/api/v1` e MCP `/mcp`.

## Dados efetivamente disponíveis

O inventário reúne 275 fontes, abrangendo as 27 UFs e a referência nacional BR; 269 entradas possuem arquivo local. Uma fonte de pesquisa com procedência pendente está explicitamente impedida de publicação. Materiais excluídos do corpus permanecem documentados; não preenchem o denominador obrigatório.

A publicação principal preservada no banco é `ca-77fb8076598b567e1ba3`, com **38.322 itens, 13.007 relações e 247 fontes**. O artefato gzip entregue possui checksum e foi reimportado de forma idempotente com comparação integral dos registros. Ela é uma publicação técnica incompleta, não um lançamento nacional aprovado.

O ponteiro `data/bundles/latest.json` identifica neste checkpoint uma candidata parcial no novo formato sharded, `ca-9d9b45e82947bd8fe35c`: **20.612 itens, 2.851 relações e 269 fontes**, sete partes com hashes comprimidos e descomprimidos. A inspeção integral dessas partes passou; a candidata não foi promovida ao padrão porque reduziria a cobertura carregada. O pipeline integra os novos adaptadores e prepara outra candidata consolidada. **Nenhuma UF foi declarada pronta.**

## Verificações executadas e limites

- TypeScript e lint passaram em sucessivos checkpoints. A suíte de domínio/contratos teve 39 testes reais aprovados, sem skips, antes dos últimos ajustes da matriz e busca; a execução final será repetida sobre o código integrado. A frente de domínio concluiu depois 48/48 testes, sem skips, cobrindo também a matriz projetada e a busca por palavras quebradas.
- API e MCP passaram sobre a publicação principal, incluindo cliente oficial HTTP e stdio, todas as dez ferramentas, erros controlados, lote, paginação, panorama de 27 UFs e paridade com a API. Cinco exportações completas foram baixadas e conferidas por streaming. Essas evidências anteriores não validam automaticamente alterações posteriores.
- Administração passou por 20 verificações de autenticação/autorização, contribuição, revisão automatizada explicitamente identificada, publicação e rollback. O fluxo novo de ingestão até preparação privada/publicação e os testes de navegador administrativo foram executados e encontraram uma associação de rótulo de seletor que precisa ajuste; não foram aprovados.
- Jornadas públicas selecionadas passaram em desktop/mobile. A execução diagnóstica integral atual teve 2/8 testes aprovados: AM ainda não possui registros na publicação antiga, e os nós nacionais de hierarquia ainda não estão incorporados nela. Um teste que voltava antes de a navegação terminar foi corrigido. A suíte será repetida sobre a candidata consolidada, sem retirar esses requisitos.
- Benchmark diagnóstico com dez clientes e 200 requisições cumpriu os limites, sem erros, no corpus de 38 mil itens em runtime host. O benchmark de aceite será executado no runtime Docker entregue, com a publicação final identificada.
- Backup lógico e restauração da base principal foram conferidos antes do cutover para PostgreSQL 17.11: contagens/digests duráveis iguais, collation correta e nenhum índice inválido. O volume antigo e o rollback foram preservados. Instalação limpa do produto completo, persistência após reinício e recuperação integral de banco/artefatos/storage ainda exigem execução de aceite.
- Sete dependências Python fixadas foram consultadas no PyPI em 28/10/2026: nenhuma vulnerabilidade ativa informada para essas versões. O relatório tem escopo explícito e não equivale a uma auditoria completa da imagem/OS.

Os resultados ficam em [evidence/](evidence/); publicação, comando, ator, timestamp e fingerprint são vinculados pelos gates. A existência de um script não prova sua execução. O release-check deve permanecer reprovado enquanto houver dados ou verificações obrigatórios pendentes.

## Bloqueios externos comprovados

| Parte afetada | Impedimento observado | Retomada necessária |
|---|---|---|
| AP, documento de EM | Duas aquisições oficiais completas produziram o mesmo PDF com árvore de páginas corrompida; leitores e tentativa de reparo não recuperaram conteúdo válido | Cópia oficial íntegra ou alternativa primária verificável |
| PB, documento de EM | Endpoint público retorna HTML/CAPTCHA em vez do PDF em acesso anônimo | Acesso legítimo ao documento íntegro ou cópia oficial alternativa |
| AC, Computação | Ato de aprovação adquirido; currículo integral obrigatório referido pelo ato ainda não localizado | Localizar e adquirir o anexo curricular oficial |
| MS, Núcleo Integrador/ementas 2023 | URL oficial de mídia retorna página inicial HTML, não o PDF esperado | Arquivo oficial íntegro ou novo endereço primário |
| AL, Computação | Cópia de pesquisa existe, mas a cadeia de procedência oficial ainda não foi confirmada | Confirmar a fonte primária antes de publicar os registros |
| BA, novo referencial de EM | Resolução de aprovação adquirida, com aplicação em 2027; texto integral do novo referencial não localizado | Obter a edição integral; preservar a distinção de vigência com 2022 |

Evidências e alternativas tentadas estão em `sources-*.md` e nos respectivos relatórios documentais. Esta tabela não transforma falhas internas em bloqueios externos: há extrações, hierarquias, correspondências explícitas e reconciliações acessíveis ainda em execução.

## Execução e retomada

```sh
npm ci
make bootstrap
make admin-create EMAIL=seu-email NAME='Seu nome' ACTOR_TYPE=human
make verify
make release-check
```

A senha é lida por stdin, sem valor padrão. `make bootstrap` usa o artefato entregue; não depende de recoletar as fontes. Configuração e segredos locais ficam fora do Git. Consulte [operations.md](operations.md) para backup, restauração, importação e limites operacionais.

O checkpoint de coordenação está em [progress.md](progress.md); o de processamento em [data-progress.md](data-progress.md) e `var/jobs/national-extraction.json`. Próximos passos: consolidar o artefato real após as correções documentais, conferir a incorporação integral dos adaptadores, importar como preparado, executar publicação administrativa e todas as jornadas de aceite, instalação limpa, reinício, reimportação dos downloads, recuperação, performance e auditoria final. Partes obrigatórias ausentes mantêm o aceite nacional aberto.
