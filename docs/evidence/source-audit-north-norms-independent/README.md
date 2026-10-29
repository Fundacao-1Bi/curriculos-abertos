# Auditoria independente dos atos AC667 e AP043/001

Resultado técnico: **PASS para os recortes integrais dos atos**, com 425 verificações, 28 registros, 283 fragmentos nativos e 16.248 glifos não brancos reconciliados uma única vez. Dez mutações negativas foram rejeitadas. Este resultado não aceita os currículos/planos externos referidos, não comprova vigência atual nem conclui a cobertura de qualquer UF.

## Método e preservação

O censo foi fixado diretamente nos cinco originais, antes de consultar os candidatos: [pin fonte-only](source-only-pin.json), inventários `*-source-only.json` e partições semânticas `*-structure-source-only.json`. Todas as páginas foram vistas em imagens primárias privadas em `var/private-evidence/source-audit-north-norms-independent/`; não há imagem primária pública neste diretório. Não houve aquisição, OCR, extração de corpus, atualização de cache, manifestação no banco ou alteração de manifesto/core nesta auditoria.

O primeiro inventário usa texto nativo ordenado por região, palavras com identidades físicas e partição independente de todas as linhas não vazias. O confronto usa essa partição como expectativa semântica; separadamente, enumera os caracteres nativos e verifica as provas de cada registro. O adapter não fornece o denominador. O checker de produção recebeu `get_text(sort=True)`. Loader, finalizer e JSON Schema foram executados com a Source e os campos propostos em memória. Todos os arquivos Python do pipeline e o manifesto permaneceram idênticos durante a execução.

| Fonte | Recorte físico | Unidades independentes | Registros | Fragmentos | Glifos não brancos | Resultado |
|---|---|---:|---:|---:|---:|---|
| AC667/2025 | 39–40, regiões declaradas | 38 | 12 | 94 | 9.630 | PASS 150 checks |
| AP043/2025 +001/2026 | 80–82, regiões/colunas declaradas | 28, em 31 fragmentos | 16 | 189 | 6.618 | PASS 275 checks |

Unidade semântica, registro, linha nativa e glifo são grãos diferentes. A partição independente detalha preâmbulo, considerandos, caputs e subdispositivos; o adapter pode preservar esses subdispositivos dentro do artigo sem perda. O formulário inicial do parecer AP é lido por suas células físicas: o `sort=True` intercala o texto da última linha de três colunas, enquanto o candidato preserva a leitura de cada célula. Todo glifo e as oito células foram conferidos.

Há três marcadores editoriais nativos AP `<#E.G.B#...>`, invisíveis nas páginas renderizadas. São preservados em registros técnicos separados. Dois deles, com fonte 2pt, sobrepõem geometricamente o limite inferior do bbox de assinaturas. Uma contagem ingênua por retângulo produziu 52 aparentes duplicações; a identidade de baseline + literal resolve os proprietários sem excluir caracteres ou alterar os candidatos. As 176 linhas do texto `sort=True` AP e as189 linhas/baselines do rawdict não são contagens contraditórias.

## Estrutura e ordem conferidas

AC: emissor, título, ementa, preâmbulo, seis considerandos, fórmula de promulgação, artigos 1–10, §§1–3 do Art.1, incisos I–III do Art.2, incisosI–IV do Art.4, parágrafo único do Art.5, §§1–2 do Art.7, fórmulas de fecho, local/data, assinatura e aprovação colegiada. O inciso III do Art.2 começa na página 40 e conserva o artigo da página 39. A Resolução 468 subsequente e o ato anterior ficaram fora do escopo. O texto declara implementação em 2026 e entrada em vigor na data da publicação; não se extrai conclusão de vigência atual. O Art.8 deixa a adesão/emissão de ato próprio a critério dos sistemas municipais; não cabe substituir essa ressalva por obrigação municipal universal.

AP: formulário de tramitação, seções I–IV do Parecer 043/2025, nove conselheiros, assinatura/protocolo; título, ementa, preâmbulo, RESOLVE, quatro artigos próprios da Resolução 001/2026, incisos I–III do Art.2, assinatura/decreto de designação e protocolo. O Art.13 caput/I–III/parágrafo único é **citação externa dentro do Mérito**, com metadado explícito; não é dispositivo próprio do parecer/resolução nem habilidade discente. Seu antecedente literal não permite uma identidade normativa mais específica por suposição.

Ordem AP 80: coluna esquerda completa antes da direita. A seção III atravessa80 direita→81 esquerda; o Art.2 III atravessa81 direita→82 esquerda. A Resolução 002/2026, inserida entre as partes selecionadas, e os atos fazendários seguintes não vazam para o pacote. A divergência literal de datas da Res.120 é preservada: 30/12/2024 no Histórico e 13/12/2024 no Mérito.

## Dependências documentais continuam abertas

**AC:** o sexto considerando descreve um documento separado, “Currículo de Educação Digital, Midiática e Computacional do Estado do Acre”. O corpo não está nos recortes do ato, nem aparece como Source curricular própria no manifesto consultado. O ato explicita partes cuja obtenção/reconciliação ainda é necessária: Apresentação, Introdução, Função Social do Currículo, Concepção, detalhamento por etapas/modalidades, Campos de Experiências e Premissas, três eixos e Quadros Organizadores com conteúdos, competências/habilidades e componentes relacionados. Os três incisos descritivos dos eixos não substituem esses quadros. O escopo referido inclui EI/EF/EM e EJA/Especial/Campo-Águas-Florestas/Indígena.

**AP:** o Plano de Ação aprovado também é externo aos recortes. O Parecer remete a “Tabelas 1, 2 e 3 nas páginas 29 a 36” e “Tabela 1, página 25 a 53 do Plano de Ação”; nenhuma dessas tabelas foi demonstrada como anexo presente. O texto descreve arquitetura/matrizes de transição, orientações de oferta, acesso/permanência, infraestrutura/pessoal, formação e monitoramento. As partes são expectativas documentais abertas. A aprovação em 2026 não estabelece edição 2026 do Plano: o Histórico/Mérito fala de transição 2025 e versão final recebida em julho 2025. Não há equivalência demonstrada com o referencial EM de 414p corrompido, nem a Res.001 o substitui.

Essas são pendências de aquisição/reconciliação externa; esta auditoria local não tentou recuperá-las nem diagnosticou bloqueio HTTP novo. Não se excluem as exigências para ocultar a falta.

## Reprodução e pins aceitos

```sh
var/venv-pipeline/bin/python docs/evidence/source-audit-north-norms-independent/verify.py
```

O verificador somente lê os cinco originais e os candidatos pinados, executa os controles em memória e escreve evidências neste diretório. Não invoca o extrator central ou OCR.

- AC sidecar: `922089eaab340e35dc5379ff23a7536be3382f4bc1ca82d0a883f1f96569d9c4`.
- AP sidecar: `f9a016239ece1a6d4886bc77501987dbef444c3a6fcc426b45cc8718041ae008`.
- [Resumo executado](verification-summary.json), verificações completas `*-verification.json`, censos e SHA dos originais nos inventários fixados.

Os negativos testam texto inventado, duplicação, pai falso que ainda resolve internamente, omissão de linha com prova também truncada, promoção do Art.13 citado a artigo próprio e truncamento do Art.2III na troca de página. Todos foram barrados. Não houve necessidade de corrigir os candidatos. A integração serial/refresh OwnSourceV2 é responsabilidade da frente principal e não foi executada por este peer.
