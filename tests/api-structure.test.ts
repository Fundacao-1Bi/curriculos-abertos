/** Contract fixtures only. No invented hierarchy enters the published corpus. */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { LearningSchema, StructureResultSchema, QuerySchema, parseQuery } from '../src/mcp/contracts';
import { openapi } from '../src/mcp/openapi';
const node={id:'isolated:document:unit',parent_id:null as string|null,code:null,text:'Unidade temática transcrita da fixture isolada.',kind:'unidade_tematica',source_id:'isolated:source',positions:[],evidence:[{source_id:'isolated:source',page:2,printed_page:'1',section:'Unidade temática',excerpt:'Unidade temática transcrita da fixture isolada.'}],child_count:3,learning_child_count:2};
function response(){return{publication:'isolated-publication',data:[{stage:'EF',component:'Matemática',area:null,item_count:12,kinds:['unidade_tematica','habilidade'],year_labels:['6º ao 9º'],age_groups:[]}],total:1,curriculum:{id:'isolated:curriculum'},hierarchy:{nodes:[{...node}],total:1,origin:'preserved_from_published_parent_id',methodology:'Contagens de filhos diretos, sem inferir pré-requisitos.',pending_reason:null as string|null}};}

test('estrutura preserva agrupamento antigo, evidências e hierarquia sem confundir seus denominadores',()=>{
 const original=response();original.hierarchy.nodes[0]={...original.hierarchy.nodes[0],source_number:'03',source_order:2,document_order:'2.1'} as typeof node;const result=StructureResultSchema.parse(original);assert.equal(result.hierarchy.nodes[0].source_number,'03');assert.equal(result.hierarchy.nodes[0].source_order,2);assert.equal(result.hierarchy.nodes[0].document_order,'2.1');assert.equal(result.data[0].item_count,12);assert.equal(result.total,1);assert.equal(result.hierarchy.total,1);assert.equal(result.hierarchy.nodes[0].child_count,3);assert.equal(result.hierarchy.nodes[0].learning_child_count,2);assert.equal(result.hierarchy.nodes[0].code,null);assert.deepEqual(result.hierarchy.nodes[0].evidence,node.evidence);
 const empty=response();empty.hierarchy={...empty.hierarchy,nodes:[],total:0,pending_reason:'Fonte ainda não estruturada.'};assert.ok(StructureResultSchema.safeParse(empty).success);
});
test('contrato impede contagens falsas, ID duplicado e perda do localizador na hierarquia',()=>{
 const inflated=response();inflated.hierarchy.total=99;assert.ok(!StructureResultSchema.safeParse(inflated).success);
 const negative=response();negative.hierarchy.nodes[0].child_count=-1;assert.ok(!StructureResultSchema.safeParse(negative).success);
 const impossible=response();impossible.hierarchy.nodes[0].learning_child_count=4;assert.ok(!StructureResultSchema.safeParse(impossible).success);
 const duplicate=response();duplicate.hierarchy.nodes.push({...node});duplicate.hierarchy.total=2;assert.ok(!StructureResultSchema.safeParse(duplicate).success);
 const self=response();self.hierarchy.nodes[0].parent_id=node.id;assert.ok(!StructureResultSchema.safeParse(self).success);
 const missing=response();Reflect.deleteProperty(missing.hierarchy.nodes[0],'evidence');assert.ok(!StructureResultSchema.safeParse(missing).success);
});
test('filtro parent_id preserva ID opaco; aliases de busca nunca substituem código canônico',()=>{
 assert.ok(QuerySchema.safeParse({publication:'p'.repeat(160)}).success);assert.ok(!QuerySchema.safeParse({publication:'p'.repeat(161)}).success);const parent='ca:source:section:identificador-escopado*';assert.equal(parseQuery(new URLSearchParams({parent_id:parent,publication:'p1'})).parent_id,parent);assert.ok(!QuerySchema.safeParse({parent_id:{sql:'unsafe'}}).success);assert.ok(!QuerySchema.safeParse({parent_id:''}).success);
 const learning={id:'isolated:item',curriculum_id:'isolated:curriculum',source_id:node.source_id,uf:'BR',code:'EF05CO011',code_aliases:['EF05CO11'],text:'Texto canônico isolado.',normalized_text:'texto canonico isolado',editorial_note:null,kind:'habilidade',parent_id:node.id,positions:[],evidence:node.evidence,extraction_revision:'isolated-test'};
 const result=LearningSchema.parse(learning);assert.equal(result.code,'EF05CO011');assert.deepEqual(result.code_aliases,['EF05CO11']);assert.equal(result.parent_id,node.id);assert.ok(!LearningSchema.safeParse({...learning,code_aliases:[5]}).success);assert.ok(!LearningSchema.safeParse({...learning,code_aliases:['']}).success);
});
test('OpenAPI declara resposta estrutural e parent_id em busca, preservando aliases na saída',()=>{
 const operation=openapi.paths['/curriculos/{id}/estrutura'].get;assert.equal(operation.responses[200].content['application/json'].schema.$ref,'#/components/schemas/StructureResult');assert.ok('StructureNode'in openapi.components.schemas);assert.ok(openapi.paths['/aprendizagens'].get.parameters.some(p=>p.name==='parent_id'));assert.ok('code_aliases'in openapi.components.schemas.Learning.properties!);
});
