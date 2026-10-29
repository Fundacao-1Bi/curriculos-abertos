# Portal público — implementação e verificação

Responsável: subagente automatizado `portal`. Implementação em execução. Design editorial de atlas documental: verde escuro, papel marfim e laranja; Georgia/Trebuchet locais, sem download obrigatório de fontes.

## Rotas implementadas

- `/`: catálogo com contadores obtidos do domínio, 27 UFs, aviso de prontidão calculado.
- `/buscar`: código/texto/tema e filtros persistidos na URL, paginação com publicação fixada.
- `/ufs/[uf]`: referenciais, cobertura, etapas e itens reais de cada jurisdição.
- `/curriculos/[id]`: metadados, estrutura e navegação até itens.
- `/aprendizagens/[id]`: redação integral, contextos, evidências, relações, cópia, compartilhamento e contestação.
- `/panorama/[id]`: estados das 27 UFs, vínculos e expansão por UF.
- `/comparar`: quaisquer 2/3 UFs, referências por coluna, filtros, redações, referências comuns e diferenças textuais identificadas.
- `/analises`: matriz nacional paginada, relações por tipo/origem/revisão, organização por ano/etapa/componente, recortes de particularidades, exploração textual e cobertura editorial.
- `/fontes`: edição/datas distintas/direitos/checksum/localizadores de origem.
- `/publicacoes`: snapshots imutáveis, revisões e changelogs.
- `/downloads`: JSON/CSV completos ou recortes por job persistente.
- `/desenvolvedores`: contrato REST navegável, OpenAPI, exemplos reais, MCP e interpretação dos campos.
- `/contribuir`: envio sem GitHub e sem dados pessoais, com honeypot.

## Contratos

Consulta via `src/domain/service.ts`. Campos extraídos ainda sem reconciliação têm aviso explícito de extração candidata. Ausência de vínculos não é ausência pedagógica. Componentes client limitados a clipboard, impressão, exportação assíncrona e contribuições. Nenhum array de aprendizagens de demonstração é usado.

Exportações: POST `/api/v1/exportacoes`, consulta GET por ID, `download_url` somente quando arquivo pronto. Contribuições: POST `/api/v1/contribuicoes` com record_url, description, evidence_url opcional e website honeypot.

## Qualidade

Implementados foco visível, skip link, navegação sem JS nas consultas, rótulos, estados loading/error/empty, textos longos preservados, rolagem restrita às tabelas e modo de impressão. Verificação executada será registrada após integração com banco e corpus reais; existência destes controles ainda não comprova a jornada de navegador.

## QA executada em 2026-10-28 (sessão Playwright `portal`)

- `npm run typecheck`: executado com saída 0 após integração dos contratos.
- Portal real em `http://localhost:3000`, PostgreSQL e worker ativos; publicação observada inicialmente `ca-64e60bb2c92be368dcd7`, com 2.108 itens locais em SP e prontidão 0/27. Esses números descrevem esta execução intermediária, não uma declaração de cobertura final.
- Desktop: início e busca SP renderizados e capturados em `output/playwright/portal-desktop.png` e `output/playwright/portal-search-desktop.png`. Imagens inspecionadas: sem sobreposição e com redação integral, filtros rotulados, contagens reais e badge de extração candidata.
- Busca interativa: digitação de `EF01AR01` e envio dos filtros retornaram 1 item, mantendo UF e publicação na URL.
- Navegação desse resultado para a ficha revelou erro de ID codificado em rota dinâmica. Correção: `canonicalParam` decodifica o parâmetro uma vez antes da consulta, conforme contrato de ID. Reexecução de navegador depende do próximo build integrado; a falha não foi marcada resolvida por mera edição.
- Console da primeira navegação: um erro `/favicon.ico` 404. Adicionado ícone SVG da própria aplicação; efeito depende do próximo build.
- Comparador: diferença entre itens arbitrários removida. O usuário precisa selecionar explicitamente dois IDs para marcar diferenças lexicais. Referenciais são filtrados pela UF selecionada. Não há inferência de equivalência pedagógica.
- Análises: matriz usa a resposta agregada real do domínio, evitando uma consulta por linha. Estados em português e denominador estruturado são tratados.

A inspeção de celular da ficha registrou o estado de erro anterior à correção; `output/playwright/portal-detail-mobile.png` não constitui prova da ficha corrigida. O coordenador executa as jornadas E2E e a verificação visual final da distribuição reconstruída.

## Checkpoint de integração final do portal

Código do portal estabilizado: `canonicalParam` nas rotas de ficha/currículo/panorama, filtros avançados de relação/origem/revisão com valores PT canônicos usados pelo corpus, exportações com entradas sanitizadas para o schema público, comparação de redações somente após seleção explícita de dois IDs, opções de referencial filtradas por UF. A matriz foi vinculada diretamente a `analyses.data.matrix`, com contagens e estados reais. O título inicial foi ajustado para “Uma leitura aberta” para não sugerir lançamento nacional completo quando a cobertura real é parcial.

Próxima ação: reconstruir a aplicação em produção e repetir ficha ID codificado, teclado/axe, exports/contribuição e telas de celular no estado integrado. O coordenador foi informado do ponto de retomada e do erro observado antes da correção.

### Ajuste de integração configurável

`/desenvolvedores` constrói exemplos API e MCP a partir da origem de `PUBLIC_URL`, validada como http(s) e sem credenciais. Links de download e publicações conservam o snapshot escolhido. Limites de leitura/MCP, exportações e contribuições são lidos do ambiente efetivo e explicam o escopo compartilhado/por cliente e a resposta 429. OpenAPI foi alinhado pelo agente API/MCP; o explorador é dinâmico para não congelar limites durante o build. Typecheck e ESLint da página passaram após essa alteração. Nova verificação HTTP requer o próximo build integrado.
