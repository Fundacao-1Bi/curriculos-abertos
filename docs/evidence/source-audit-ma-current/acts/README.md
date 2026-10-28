# Maranhão — atos oficiais atuais

Pesquisa e conferência documental por `agent:ma_acts`, ator automatizado. Não houve revisão humana, alteração do manifesto ou publicação. Originais e renders permanecem em diretórios privados ignorados pelo Git.

O catálogo público do [Diário Oficial](https://diariooficial.ma.gov.br/acervo/) permite consultar os cadernos por tipo, mês e ano. Os endpoints de consulta e download abaixo são os mesmos declarados pelo cliente público; foram acessados por GET comum, sem credenciais ou contorno de controle de acesso. O espelho Mural Público e as referências municipais serviram apenas de pistas. Os documentos usados como prova foram obtidos diretamente do diário estadual.

| Documento | Data escrita no ato | Publicação observada | Recorte do PDF original | Escopo documental |
| --- | --- | --- | --- | --- |
| Resolução CEE/MA 211/2026 | 21/07/2026 | 31/07/2026 | p20 direita após SEMA; p21 esquerda e assinaturas na direita superior | Aprova DCTMA Educação Digital e Midiática como complemento normativo da Educação Básica; seis artigos |
| Resolução CEE/MA 162/2025 | 29/06/2025 | 06/08/2026 | p48 direita inferior; p49 ambas; p50 esquerda até assinaturas | Política de Educação Integral em Tempo Integral; dez artigos; não se presume primeira publicação em 2026 |
| Portaria SEDUC/MA 181/2026 | 26/08/2026 | 31/08/2026 | p31–35 ambas; p36 esquerda e direita superior | 25 artigos, nove capítulos e Anexo Único com 17 seções; recomposição no Ensino Médio Regular parcial |
| Decreto MA 42.532/2026 | 29/07/2026 | 29/07/2026 | p45 direita desde o decreto; p46 ambas até assinaturas | Regulamenta Ensino Médio de Verdade em substituição ao Mais IDEB; sete artigos; tipologia no corpus pendente |
| Portaria SEDUC/MA 167/2026 | 03/08/2026 | 11/08/2026 | p24–25 ambas; p26 esquerda superior | Doze artigos e Anexo Único sobre governança, monitoramento e IDE-EM; tipologia no corpus pendente |

As URLs e os SHA-256 completos estão em `source-proposals.json`. São **cinco arquivos de diário, 638 páginas originais**, não 638 páginas curriculares. Somente as regiões declaradas pertencem a estes recortes. A verificação automática confirmou 60 marcadores de artigo, em sequência e uma vez por ato, e reconferiu hashes, bytes e páginas de todos os arquivos.

A Resolução 211 é vigente na publicação segundo o art.6. Seu art.5 reserva a ato posterior diretrizes operacionais sobre transição, formação, governança e proteção da infância. Portanto, essa resolução não comprova um calendário completo de implantação do complemento. Não contém anexo curricular, URL ou QR que entregue seu conteúdo. O documento curricular aprovado permanece como Source separado obrigatório `research_pending`, com edição editorial, data do documento e aplicação detalhada nulas. As orientações de um componente Educação Digital do Ensino Médio não foram equiparadas a esse complemento de toda a Educação Básica.

A Portaria 181 determina uma hora-aula semanal de Língua Portuguesa e uma de Matemática para recomposição, dentro dos respectivos componentes e de sua carga horária. O art.2 incorpora o Anexo Único. O art.25 dá vigência na publicação com efeitos retroativos a 05/08/2026. O art.1, §2, e a seção16 do anexo preservam a matriz e os componentes; o ato não cria um catálogo paralelo de habilidades. A matriz aprovada é referenciada, sem seu conteúdo integral ser reproduzido. O anexo define uma matriz de fluxo pedagógico, que não deve ser confundida com matriz curricular ou de habilidades.

A Resolução 162 tem numeração e data de 2025, embora o exemplar adquirido seja de 2026. Essa diferença foi preservada, sem alegar republicação, erro ou revogação. O âmbito são as escolas de tempo integral, não todas as ofertas do estado automaticamente.

O Decreto 42.532 e a Portaria 167 são mantidos como documentos de apoio normativo com tipologia pendente. A natureza administrativa/programática exige decisão da frente Nordeste sobre seu lugar no corpus; não foram silenciosamente excluídos nem declarados matriz curricular. O anexo da Portaria 167 contém fórmulas em imagem, e qualquer extração integral futura deverá preservar essa representação.

Pesquisa de continuidade: o índice público do diário foi consultado por DCTMA, Educação Digital e matrizes curriculares entre 2025 e 28/10/2026. Seus resultados são pistas por arquivo/página, não denominador de completude. Não foi localizado nesta pesquisa o ato operacional posterior referido no art.5 da Resolução 211. Isso não prova que ele não exista. O Parecer CEE/MA 242/2026 é citado pelo ato, mas seu texto integral não foi adquirido.

Comando executado:

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-ma-current/acts/verify-acquisitions.py
```

Resultado: cinco hashes/paginações corretos, 60 artigos em sequência nos recortes, zero falhas. Isso não substitui extração estruturada integral, reconciliação do complemento curricular ou prova de prontidão de MA.
