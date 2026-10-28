

## 2026-10-28 — preservação na atualização e fidelidade documental

- Rejeitado usar ingestão PE parcial como prova de atualização global: diferenças de runtime tornam caches incompatíveis e poderiam eliminar fontes não relacionadas. Decidido fixar base+escopo no enqueue, compor artefato global, verificar retenção completa e publicar por CAS. O padrão principal permaneceu preservado durante as falhas de ensaio.
- Mantido schema1.0.0 imutável e introduzido1.1.0 para endereço de arquivo desconhecido. Rejeitado inventar URL de PDF a partir da página de procedência. Importadores verificam pins e registros antes de SQL; sem dependência nova.
- Confirmados os hashes e páginas fornecidos para AP/PB CEDOC. AP alternativo não duplica conteúdo; PB392 não substitui635, pois existem mudanças reais de objetivos e partes. A solicitação do usuário torna o processamento392 obrigatório, independentemente da incerteza de vigência. EM continua separado.
- Código impresso não resolvido por OCR permanece nulo com razão, separado de item originalmente sem código. A interface não apresenta um candidato OCR como código oficial. Datas parciais não recebem dia/mês inventados.
- Verificação literal de registros existentes foi complementada por denominadores físicos de todas as tabelas afetadas, pois um checker de substring não detectava códigos locais truncados nem células inteiras omitidas. Sucesso de schema, OCR ou amostra não será tratado como aceite nacional.
