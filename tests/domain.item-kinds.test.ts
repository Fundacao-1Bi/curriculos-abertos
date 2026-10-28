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
