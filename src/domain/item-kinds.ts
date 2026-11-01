/** Documentary roles, not semantic equivalence. No canonical kind or text is rewritten. */
export const ITEM_KIND_POLICY_VERSION='documentary-item-roles-2026-10-28-v6';
export const ITEM_KIND_GROUPS={
 learning:[
  'habilidade','objetivo_aprendizagem','competencia_geral','competencia_especifica','habilidade_ifa','habilidade_projeto_vida',
  'competencia_comum_ifa','competencia_geral_computacao','competencia','competencia_profissional','competencia_geral_docente',
  'capacidade','aprendizagem_especifica','conjunto_capacidades_demonstradas','objetivo_geral','objetivo_curso_especifico',
  'habilidade_local_sem_codigo','habilidade_componente','habilidade_componente_sem_codigo','habilidade_eixo','habilidade_eixo_sem_codigo','sintese_aprendizagem',
 ],
 formative_purpose:['objetivo_curso_geral','objetivo_trilha','objetivo_formativo','objetivo_curricular'],
 experience:['experiencia_aprendizagem','experiencia_sugerida'],
 rights:['direito_aprendizagem'],
 assessment:['criterio_avaliacao','sugestao_avaliacao_processual','indicador_observacao','orientacao_avaliacao'],
 normative:['dispositivo_normativo_alterado','referencia_normativa_preambular','secao_normativa_ato','postulacao_curricular','parecer_normativo','registro_aprovacao','voto_parecer','preambulo','considerando','marcador_normativo','assinatura_documental','homologacao','objetivo_normativo','ato_normativo','preambulo_normativo','considerando_normativo','dispositivo_deliberativo','artigo_normativo','comando_publicacao','assinatura_normativa','capitulo_normativo','anexo_normativo','secao_anexo_normativo','quadro_normativo','registro_homologacao_publicacao','ementa_normativa','titulo_normativo','paragrafo_normativo','inciso_normativo','alinea_normativa','secao_ato_normativo','subsecao_normativa','assinatura_ato_normativo'],
 context:[
  'grupo_direitos_aprendizagem','oferta_trilha','trilha_curricular',
  'relatorio_parecer','fundamentacao_parecer','nota_documental','quadro_documental','linha_quadro_documental','fonte_quadro_documental',
  'campo_sintese_aprendizagem','acao_docente','contexto_curricular','contexto_observacao','contexto_planejamento','contexto_temas_integradores','orientacao_implementacao','orientacao_transicao','pilar_matriz_saberes','saber_curricular','reflexao_docente','rotulo_direito','tema_integrador','valor_principio',
  'anexo_curricular','grupo_competencias','area_conhecimento','secao_normativa','principio_curricular','objeto_conhecimento','estrutura_curricular','palavra_chave_habilidade',
  'referencial','grupo_curricular','etapa','componente_curricular','campo_experiencias','descricao_campo_experiencias','grupo_etario','unidade_tematica','eixo','campo_atuacao','pratica_linguagem',
  'orientacao_docente','campo_experiencia','ciclo_escolar','ano_escolar','linguagem_artistica','curso_tecnico','itinerario_formativo','unidade_curricular','eixo_estruturante','orientacao_metodologica',
  'apresentacao','secao_curricular','abordagem_interdisciplinar','periodo_curricular','tematica','desdobramento','tema_transversal','producao_sugerida','volume_documental','quadro_curricular',
  'autenticacao_documental',
  'eixo_computacao','etapa_curricular','pilar_estruturante','etapa_fluxo_pedagogico','referencia_no_documento','mencao_codigo','ementa','narrativa_curricular','credito_documental','rotulo_documental','organizador_curricular','metadado_documental','registro_documental','detalhamento_objetivo','orientacao_didatica','cartao_referencias_eixo','documento_curricular','ementa_curricular','entrada_indice_curricular','formacao_docente','grupo_areas_conhecimento','grupo_objetivos','grupo_referencias_eixos','indice_unidades_curriculares','matriz_curricular','modulo_curricular','problematica_curricular','quadro_habilidades_eixos','referencia_bibliografica','sugestao_didatico_metodologica','tema_contemporaneo_transversal','titulo_trilha','trilha_aprofundamento',
 ],
} as const;
export const LEARNING_KINDS=ITEM_KIND_GROUPS.learning;
export type ItemKindCategory=keyof typeof ITEM_KIND_GROUPS|'unclassified';
const categories=new Map<string,ItemKindCategory>(Object.entries(ITEM_KIND_GROUPS).flatMap(([category,kinds])=>kinds.map(kind=>[kind,category as ItemKindCategory] as const)));
export function itemKindCategory(kind:string):ItemKindCategory{return categories.get(kind)??'unclassified';}
export function isLearningKind(kind:string){return itemKindCategory(kind)==='learning';}
export const ITEM_KIND_CATEGORY_LABELS:Record<ItemKindCategory,string>={learning:'expectativa de aprendizagem ou qualificação',formative_purpose:'finalidade de formação ou organização curricular',experience:'experiência ou proposta pedagógica local',rights:'direito de aprendizagem',assessment:'avaliação e observação pedagógica',normative:'ato ou dispositivo normativo',context:'contexto estrutural ou documental',unclassified:'tipo documental ainda não classificado'};
export function summarizeKindCategories(rows:readonly {value:string;count:number}[]){
 const counts:Record<ItemKindCategory,number>={learning:0,formative_purpose:0,experience:0,rights:0,assessment:0,normative:0,context:0,unclassified:0};
 for(const row of rows)counts[itemKindCategory(row.value)]+=row.count;
 return counts;
}
export const ITEM_KIND_POLICY={version:ITEM_KIND_POLICY_VERSION,unit:'unique_canonical_item_record',categories:ITEM_KIND_GROUPS,definition:'Aprendizagens são expectativas de aprendizagem ou qualificação explicitamente rotuladas pela fonte. Competências, capacidades, objetivos e habilidades mantêm tipos e granularidades diferentes. Blocos de capacidades contam como um registro; não se inventam subitens. Sínteses de aprendizagem EI são expectativas documentais heterogêneas, nunca pré-requisitos para EF nem evidência do desenvolvimento de um estudante. Classificação não valida a transcrição OCR nem substitui revisão documental. Experiências/propostas pedagógicas locais, finalidades de curso/trilha/componente, direitos, avaliação, contextos e normas são contados separadamente e continuam consultáveis. Tipos desconhecidos não são promovidos automaticamente a aprendizagens.',legacy_complement:'structural_or_documentary_items é o complemento histórico de learning_items; inclui também experiências/propostas pedagógicas, finalidades, direitos, avaliação e tipos não classificados, sem os rebatizar como estrutura ou normas.'} as const;
