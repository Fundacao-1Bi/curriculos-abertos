# Referência histórica dos itinerários: livreto MEC hospedado pela SEDU/ES

O sidecar `data/manifests/uncoded/br-if-2019-structure.json` contém 217 registros: 72 habilidades codificadas, 16 objetivos formativos e 129 registros de estrutura/contexto. O `2019` do caminho e do identificador da fonte é técnico: não confirma a data de edição do livreto.

A fonte primária é o PDF de 14 páginas com SHA-256 `7304b865546b86326dbc2991c111068f0c0784b920075d0cf2716979ae391431`, adquirido do endereço oficial da [SEDU/ES](https://curriculo.sedu.es.gov.br/curriculo/wp-content/uploads/2023/01/Referenciais-Curriculares-para-Elaboracao-de-Itinerarios-Formativos-1-1.pdf). O original não foi alterado. Não se afirma vigência atual nem substituição dos parâmetros nacionais de 2025. A data de criação presente nos metadados PDF não prova data de publicação.

O denominador independente é de 72 habilidades: 12 de cada prefixo `CG`, `LGG`, `MAT`, `CNT`, `CHSA` e `FTP`. A Tabela 1 contém quatro células de habilidades gerais; a Tabela 2 contém cinco células por eixo, em quatro páginas. Todas as 24 células e os 72 textos foram cotejados, incluindo acentos, sinais, espaços internos, quebras de linha e hifens impressos. Os códigos `EMIFCHSA01` a `EMIFCHSA12` permanecem como impressos, sem alias para `CHS`.

As quatro finalidades da página 4 e as três finalidades de cada eixo nas páginas 6–9 são `objetivo_formativo`, com código nulo. Esses 16 registros preservam as finalidades da organização curricular e pertencem à categoria `formative_purpose`; não aumentam o denominador da matriz de aprendizagens dos estudantes. Textos, evidências, identificadores técnicos e hierarquia foram preservados nessa classificação.

Os contextos das páginas introdutórias, de implementação e dos quatro eixos foram mantidos, assim como os títulos e cabeçalhos das tabelas. A hierarquia explicita referencial, capítulos, eixos, áreas/grupos e itens. Posições registram EM, sem inventar ano escolar; a área ou a formação técnica corresponde à coluna impressa. A verificação automática de evidência não constitui revisão pedagógica humana.

As reproduções correlatas da Portaria MEC 1432/2018 hospedadas por MG e TO foram cotejadas quanto ao inventário literal de códigos: ambas contêm `EMIFCHS`, enquanto o livreto contém `EMIFCHSA`. Não se estabeleceu identidade de edição entre esses documentos, nem se copiou redação das reproduções para substituir a fonte primária.

## Reprodução e evidências

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-br-if-2018/build_sidecar.py
var/venv-pipeline/bin/python docs/evidence/source-audit-br-if-2018/verify_sidecar.py
```

O builder reproduz o sidecar com o timestamp técnico observado `2026-10-28T15:46:02+00:00`. O verificador lê o arquivo salvo e reabre todas as células, sem chamar o builder. Ambos executam o `evidence_check` real do pipeline sobre todos os 217 registros; o builder também executa `source_uncoded_items` integralmente.

- `complete-primary-audit.json`: inventários, segmentos de todas as habilidades, todas as células físicas, cobertura dos caracteres das 14 páginas e execução do contrato de ingestão.
- `independent-verification.json`: releitura dos 217 registros em passagem separada; comparação exata dos 72 textos e verificação de todos os pais, sem ciclos.
- `adversarial-verification.json`: rejeição de seis corrupções em cópias temporárias, incluindo omissão/alteração do último item e alias indevido CHSA → CHS.
- `private-evidence-inventory.json`: caminhos e hashes das imagens locais de conferência. Os PNGs foram movidos para `var/private-evidence/source-audit-br-if-2018/`, fora da distribuição versionada, porque direitos de redistribuição das imagens não foram estabelecidos.

SHA-256 do sidecar final: `92e202363a9ef23f735bf227a8205616e978140f9e0b497531354485461f623d`.

O `acquisition.json` anterior foi preservado. A vinculação da fonte no inventário nacional e a importação/publicação integradas são responsabilidade da frente coordenadora; este sidecar não declara conclusão nacional nem reconciliação dos currículos das UFs.

Runtime de verificação observado: Python 3.11.15 / PyMuPDF 1.26.7, em `var/venv-pipeline/bin/python`. Para conferir a reprodução sem regravar o sidecar, execute o builder com `--verify-existing`. As duas passagens compartilham o detector geométrico `find_tables`; não se afirma independência absoluta de engine. A comparação exata dos 72 textos e o censo completo de caracteres `rawdict` acrescentam verificações distintas à releitura.
