# 003 — Publicação particionada e exportação por streaming

A extração real ultrapassou 89 mil candidatos e 614 MiB de cache antes de terminar as fontes. Montar um JSON nacional em uma única string ultrapassaria limites de memória/string do V8 e tornaria o bootstrap frágil. A abrangência curricular não será cortada para caber.

A distribuição `curriculos-abertos/sharded-v1` usa um manifesto JSON pequeno e partes JSONL compactadas. Cada parte registra tipo (items/relations), caminho relativo seguro, tamanho/contagem e SHA-256 dos bytes compactados e descompactados. Cada linha é um registro canônico completo; IDs/relações/evidências são preservados. O manifesto contém metadados da publicação, fontes, cobertura, schema, contagens e lista das partes.

O importador valida artefatos e referências antes da promoção transacional. Publicações novas guardam metadados no cabeçalho e registros imutáveis nas tabelas canônicas. Bundles monolíticos anteriores continuam suportados. A publicação não pode ser promovida parcialmente.

O worker gera JSON/CSV nacional por streaming para arquivo persistente, com chave de publicação resolvida uma vez, ordenação estável e checksum incremental. O contrato REST/MCP permanece inalterado. Verificações de downloads também precisam de parsing incremental; não podem aprovar só os primeiros registros.

Esta é uma decisão de operação/memória, não uma exceção de escopo ou de completude. Os adaptadores documentais e a reconciliação continuam obrigatórios.
