import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readdir,readFile} from 'node:fs/promises';
import {ITEM_KIND_GROUPS,LEARNING_KINDS,isLearningKind,itemKindCategory,summarizeKindCategories} from '../src/domain/item-kinds';
test('documented uncoded expectations differ from formation purposes, rights, assessment and reference context',()=>{
 for(const kind of ['competencia_comum_ifa','competencia_geral_computacao','capacidade','aprendizagem_especifica','habilidade_componente_sem_codigo','competencia_profissional','competencia_geral_docente','objetivo_curso_especifico','conjunto_capacidades_demonstradas','sintese_aprendizagem'])assert.equal(isLearningKind(kind),true,kind);
 for(const kind of ['objetivo_curso_geral','objetivo_trilha','objetivo_formativo'])assert.equal(itemKindCategory(kind),'formative_purpose');
 assert.equal(itemKindCategory('experiencia_aprendizagem'),'experience');assert.equal(isLearningKind('experiencia_aprendizagem'),false);assert.equal(itemKindCategory('objetivo_normativo'),'normative');assert.equal(itemKindCategory('organizador_curricular'),'context');assert.equal(itemKindCategory('campo_sintese_aprendizagem'),'context');assert.equal(itemKindCategory('direito_aprendizagem'),'rights');assert.equal(itemKindCategory('criterio_avaliacao'),'assessment');
 for(const kind of ['referencia_no_documento','palavra_chave_habilidade','ementa','objeto_conhecimento'])assert.equal(itemKindCategory(kind),'context');
 assert.equal(itemKindCategory('artigo_normativo'),'normative');assert.equal(itemKindCategory('habilidade_nova_nao_classificada'),'unclassified');assert.equal(isLearningKind('habilidade_nova_nao_classificada'),false);
 const all=Object.values(ITEM_KIND_GROUPS).flat();assert.equal(new Set(all).size,all.length);assert.equal(LEARNING_KINDS.length,22);
 assert.deepEqual(summarizeKindCategories([{value:'capacidade',count:2},{value:'objetivo_formativo',count:3},{value:'direito_aprendizagem',count:4},{value:'tipo_novo',count:1}]),{learning:2,formative_purpose:3,experience:0,rights:4,assessment:0,normative:0,context:0,unclassified:1});
});
test('every kind in the real uncoded sidecar inventory has an explicit reviewed category',async()=>{
 const kinds=new Set<string>();for(const name of(await readdir('data/manifests/uncoded')).filter(name=>name.endsWith('.json'))){const value=JSON.parse(await readFile('data/manifests/uncoded/'+name,'utf8'));const rows=Array.isArray(value)?value:value.items??[];for(const row of rows)if(typeof row.kind==='string')kinds.add(row.kind);}
 assert.ok(kinds.has('competencia_comum_ifa'));assert.ok(kinds.has('competencia_geral_computacao'));assert.ok(kinds.has('capacidade'));assert.deepEqual([...kinds].filter(kind=>itemKindCategory(kind)==='unclassified').sort(),[],'A new documentary role needs an explicit policy decision, not a substring guess.');
});

test('experience counts preserve a disjoint exhaustive decomposition without inflating learning outcomes',()=>{
 const rows=[{value:'experiencia_aprendizagem',count:465},{value:'objetivo_aprendizagem',count:93},{value:'objetivo_normativo',count:8},{value:'tipo_novo_sem_revisao',count:2}];
 const summary=summarizeKindCategories(rows);assert.equal(summary.experience,465);assert.equal(summary.learning,93);assert.equal(summary.normative,8);assert.equal(summary.unclassified,2);assert.equal(Object.values(summary).reduce((sum,count)=>sum+count,0),568);
});


test('reviewed ES component purposes, teacher guidance and observation indicators retain distinct documentary roles',async()=>{
 const expected={formative_purpose:['objetivo_curricular'],assessment:['indicador_observacao','orientacao_avaliacao'],context:['acao_docente','contexto_curricular','contexto_observacao','contexto_planejamento','contexto_temas_integradores','orientacao_implementacao','orientacao_transicao','pilar_matriz_saberes','reflexao_docente','rotulo_direito','saber_curricular','tema_integrador','valor_principio']};
 for(const[category,kinds]of Object.entries(expected))for(const kind of kinds){assert.equal(itemKindCategory(kind),category,kind);assert.equal(isLearningKind(kind),false,kind);}
 const sidecar=JSON.parse(await readFile('data/manifests/uncoded/es-ei-items.json','utf8')),rows=Array.isArray(sidecar)?sidecar:sidecar.items;
 const observations=rows.filter((row:{kind:string})=>row.kind==='indicador_observacao');assert.ok(observations.length>0);for(const row of observations)assert.equal(row.source_context.column_title,'Vale Observar Se');
 const actions=rows.filter((row:{kind:string;source_context?:{column_title?:string}})=>row.kind==='acao_docente'&&row.source_context?.column_title);assert.ok(actions.length>0);for(const row of actions)assert.equal(row.source_context.column_title,'Dicas para o Planejamento');
 const purposes=JSON.parse(await readFile('data/manifests/uncoded/es-ef-competencies-prose-items.json','utf8'));const purposesRows=(Array.isArray(purposes)?purposes:purposes.items).filter((row:{kind:string})=>row.kind==='objetivo_curricular');assert.equal(purposesRows.length,8);for(const row of purposesRows){assert.equal(row.source_context.source_typology,'objetivos_do_componente_curricular');assert.equal(row.code,null);}
 assert.equal(LEARNING_KINDS.length,22);const summary=summarizeKindCategories(Object.values(expected).flat().map(value=>({value,count:1})));assert.equal(summary.learning,0);assert.equal(Object.values(summary).reduce((sum,count)=>sum+count,0),16);
});


test('ES learning synthesis keeps its source warning, pending OCR and unknown ages while remaining distinct from conceptual exposition',async()=>{
 const value=JSON.parse(await readFile('data/manifests/uncoded/es-ei-items.json','utf8')),rows=Array.isArray(value)?value:value.items;
 const summaries=rows.filter((row:{kind:string})=>row.kind==='sintese_aprendizagem');assert.equal(summaries.length,19);
 for(const row of summaries){assert.equal(itemKindCategory(row.kind),'learning');assert.equal(row.code,null);assert.equal(row.source_context.source_table,'SÍNTESE DAS APRENDIZAGENS');assert.equal(row.source_context.learning_prerequisite,false);assert.match(row.source_context.source_warning,/não como condição ou pré-requisito/);assert.equal(row.source_context.ocr_transcription_review_pending,true);for(const position of row.positions){assert.equal(position.stage,'EI');assert.equal(position.age_min_months??null,null);assert.equal(position.age_max_months??null,null);}}
 const headings=rows.filter((row:{kind:string})=>row.kind==='campo_sintese_aprendizagem');assert.equal(headings.length,5);for(const row of headings)assert.equal(itemKindCategory(row.kind),'context');
 for(const kind of ['saber_curricular','pilar_matriz_saberes','valor_principio','objetivo_curricular','indicador_observacao'])assert.equal(isLearningKind(kind),false,kind);
});


test('BA266 legal propositions and historical Parecer material remain legal/documentary roles without invented learning codes',async()=>{
 const normative=['referencia_normativa_preambular','secao_normativa_ato','postulacao_curricular','parecer_normativo','registro_aprovacao','voto_parecer'];const context=['relatorio_parecer','fundamentacao_parecer','nota_documental','quadro_documental','linha_quadro_documental','fonte_quadro_documental'];
 for(const kind of normative){assert.equal(itemKindCategory(kind),'normative',kind);assert.equal(isLearningKind(kind),false,kind);}for(const kind of context){assert.equal(itemKindCategory(kind),'context',kind);assert.equal(isLearningKind(kind),false,kind);}
 const rows=JSON.parse(await readFile('data/manifests/uncoded/ba-resolucao-266-items.json','utf8'));assert.equal(rows.length,141);assert.ok(rows.every((row:{code:null;kind:string})=>row.code===null&&!isLearningKind(row.kind)));
 const propositions=rows.filter((row:{kind:string})=>row.kind==='postulacao_curricular');assert.equal(propositions.length,8);for(const row of propositions){assert.match(row.key,/^article-10-inciso-/);assert.equal(row.parent_key,'article-10');assert.deepEqual(row.positions.map((p:{stage:string})=>p.stage),['EI']);}
 const source=rows.find((row:{key:string})=>row.key==='parecer-table-source');assert.match(source.text,/^Fonte: Barcelos e Moll, 2021/);const tableRows=rows.filter((row:{kind:string})=>row.kind==='linha_quadro_documental');assert.equal(tableRows.length,2);for(const row of tableRows){assert.equal(row.source_context.printed_table_column_headers_present,false);assert.ok(Array.isArray(row.source_context.table_columns_descriptive_not_printed));}
 assert.equal(LEARNING_KINDS.length,22);
});


test('amended legal quotations differ from outer articles and rights/trail headings differ from student expectations',async()=>{
 assert.equal(itemKindCategory('dispositivo_normativo_alterado'),'normative');for(const kind of ['grupo_direitos_aprendizagem','oferta_trilha','trilha_curricular'])assert.equal(itemKindCategory(kind),'context');
 const readRows=async(path:string)=>{const value=JSON.parse(await readFile(path,'utf8'));return Array.isArray(value)?value:value.items;};
 const amended=(await readRows('data/manifests/uncoded/ba-resolucao-125-items.json')).filter((row:{kind:string})=>row.kind==='dispositivo_normativo_alterado');assert.equal(amended.length,1);assert.equal(amended[0].parent_key,'article-1');assert.match(amended[0].text,/^Art\. 19\./);assert.equal(amended[0].source_context.quoted_amended_article_not_seventh_outer_article,true);
 for(const path of ['data/manifests/uncoded/sp-eief-rights-items.json','data/manifests/uncoded/mg-eief-rights-items.json']){const groups=(await readRows(path)).filter((row:{kind:string})=>row.kind==='grupo_direitos_aprendizagem');assert.equal(groups.length,1);assert.equal(groups[0].source_context.learning_objective_claim,false);assert.equal(groups[0].source_context.source_role,'Original general EI rights heading');}
 const trails=await readRows('data/manifests/uncoded/rj-itinerarios-objectives-items.json');assert.equal(trails.filter((row:{kind:string})=>row.kind==='oferta_trilha').length,54);assert.equal(trails.filter((row:{kind:string})=>row.kind==='trilha_curricular').length,13);for(const row of trails.filter((row:{kind:string})=>['oferta_trilha','trilha_curricular'].includes(row.kind))){assert.equal(row.code,null);assert.equal(isLearningKind(row.kind),false);}
 assert.equal(LEARNING_KINDS.length,22);assert.equal(itemKindCategory('tipo_novo_sem_revisao'),'unclassified');
});
