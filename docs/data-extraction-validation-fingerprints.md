# Extração congelada e validação primária raster

A revisão `page-cell-v1.5.0` e seus caches preservam o fingerprint do código que realmente os produziu. Não se deve trocar esse fingerprint nem o hash de configuração para simular uma reextração.

## Contrato entregue

`pipeline/raster_review.py` é um verificador de produtor isolado. Recebe o handoff pinado, as fontes e os arquivos de revisão. Recalcula o hash do PDF, extrai a imagem embutida por xref e reproduz transformação, caixa, pixels e recorte. O pin da raiz aprovada ancora ledger, revisões e propostas. O próprio verificador é fixado por SHA e sua execução rejeita mudança do arquivo durante a produção.

A saída permite somente referências documentais com `code == text` literal confirmado, `positions=[]`, `parent_id=null`, ator automatizado e `body_not_verified`. O recorte rejeitado de EI não produz item. Essa verificação não certifica o corpo em OCR, equivalência, posicionamento ou Source inteira. Não é uma prova OCR e não deve usar `ocr_reference_path` como disfarce.

## Integração proposta, ainda não executada

1. Produzir e validar o BASE nacional técnico com a extração1.5 e sidecars já suportados, preservando sua identidade e todos os erros/pendências documentais.
2. Um produtor de augmentação separado recebe o manifesto BASE e seu SHA, o handoff e seu SHA e o verificador pinado. Verifica o BASE integralmente e gera novo artefato imutável: mesmos itens/relações do BASE mais somente as referências primárias aprovadas. Provar invariância dos IDs, códigos, textos, pais, posições e evidências do BASE.
3. Registrar no novo manifesto a identidade e SHA do BASE, revisão de validação/augmentação, SHA do verificador, runtime e pins de todos os inputs. Manter o fingerprint de extração1.5 como proveniência dos registros reutilizados, sem alegar que foram reextraídos pelo novo produtor.
4. As novas referências não recebem corpo, posição ou equivalência por aproximação. Nenhum indicador `whole_source` aumenta por essa adição; qualquer recibo integral anterior de fonte afetada deve ser reavaliado contra a união completa de registros.
5. O fluxo administrativo que atualizar uma fonte AM deverá executar o mesmo estágio de validação/augmentação antes de produzir o recibo PREPARED. Caso contrário, um delta removeria referências existentes. Esse requisito impede ligar o suplemento ao manifesto de fontes antes de o caminho administrativo suportá-lo.

O BASE é um intermediário verificável. A proposta não é uma autorização para omitir a integração final nem para apresentar o suplemento como currículo concluído. A adoção exige revisão e novo freeze do produtor, com testes negativos de identidade/pins e invariância do BASE, sem editar ou relabelar os caches da extração.

## Separação durável

Mudanças futuras de validação devem ter fingerprint e revisão próprios. A configuração da extração identifica decisões que alteram o texto bruto e sua geometria; inputs de sidecars, revisão e mapeamentos pertencem também à proveniência do produtor/validador. Uma eventual refatoração dessa fronteira deve manter os metadados originais dos caches e produzir prova explícita de reutilização, em vez de atualizar hashes antigos.
