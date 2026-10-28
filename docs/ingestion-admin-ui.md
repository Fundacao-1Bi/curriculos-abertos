# Administração: candidatos de ingestão

Implementado em `src/app/admin/ui.tsx` e `admin.css`, sob a frente `/root/admin_ops/ingestion_admin_ui`.

## Fluxo entregue

- Seção **Candidatos de ingestão**, lista autenticada e seleção **Candidato ingerido**.
- Prévia administrativa de candidato preparado ou publicado, com identificação fixa da publicação, contagens, metadados, recibos de jobs, arquivo/hash e tipo de ator.
- Fontes oficiais/artefatos, emissor, edição, etapa, disponibilidade e direitos.
- Itens reais paginados (25 por página), com texto integral, inspeção de posicionamentos e evidências localizáveis. Paginação fixa a publicação selecionada.
- Ações de administrador **Validar candidato** e **Publicar candidato**, com justificativa obrigatória, estado de carregamento e atualização após resposta do servidor.
- Validação técnica e prontidão nacional apresentadas separadamente; nenhuma revisão pedagógica humana é atribuída pelo frontend.
- Resultado do job de ingestão mostra recibo e botão para abrir o candidato na área autenticada.
- Formulário **Fontes e registros** agora possui seletor **Publicação consultada**. Consulta publicada usa API pública com `publication` fixada; consulta preparada usa a rota administrativa interna.
- Rollback lista somente versões com `visibility=published`.

## Contratos consumidos

`GET /api/admin/candidates`, `GET /api/admin/candidates/{id}`, `GET /api/admin/candidates/{id}/items`, `GET /api/admin/candidates/{id}/items/{itemId}`, `POST /api/admin/candidates/{id}/validate`, `POST /api/admin/candidates/{id}/publish`. O backend permanece responsável por sessão, papéis, origem, validação, publicação e auditoria.

## Verificação real desta frente

- ESLint direcionado ao arquivo de UI: executado, exit0.
- Typecheck: executado na árvore compartilhada, exit0.
- Browser/E2E: não executado por esta frente. A aplicação permanece parada durante a integração do backend/migration008; a frente API/MCP executará QA de navegador após liberação da coordenação.
- Não foram executados Docker, DDL ou mutações em dados por esta frente.

## Labels para QA

`Publicação consultada`, `Candidatos de ingestão`, `Candidato ingerido`, `Justificativa para o candidato`, `Validar candidato`, `Publicar candidato`, `Inspecionar candidato ingerido`, `Página anterior de registros`, `Próxima página de registros`.
