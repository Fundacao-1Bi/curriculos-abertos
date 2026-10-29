import { test } from 'node:test';
import assert from 'node:assert/strict';
import { PositionSchema, QuerySchema, CompareSchema, ExportSchema, parseQuery } from '../src/mcp/contracts';
import { openapi } from '../src/mcp/openapi';

const base={stage:'EI',component:null,area:null,years:null,year_label:null,age_group:'Bebês',period:null};
const evidence={source_id:'isolated:source',page:4,printed_page:null,section:'Bebês de zero a seis meses',excerpt:'Bebês de zero a seis meses'};
const documented={...base,age_label:evidence.excerpt,age_min_months:0,age_max_months:6,age_evidence:[evidence],age_interval_origin:'explicit_source_header_units_to_months'};
test('consulta etária aceita somente inteiro ou faixa crescente inclusiva 0–1800',()=>{
 for(const age_months of ['0','0-6','6-6','1800','0-1800'])assert.equal(QuerySchema.parse({age_months}).age_months,age_months);
 for(const age_months of ['','-1','1.5','6-0','1801','0-1801','0,6','0–6',' 6 ','1-2-3'])assert.ok(!QuerySchema.safeParse({age_months}).success,age_months);
 const parsed=parseQuery(new URLSearchParams('age_months=0-6&age_group=Beb%C3%AAs&include_unknown_positions=true&publication=isolated'));
 assert.equal(parsed.age_months,'0-6');assert.equal(parsed.age_group,'Bebês');assert.equal(parsed.include_unknown_positions,true);assert.equal(parsed.publication,'isolated');
 assert.ok(CompareSchema.safeParse({age_months:'0-6',ufs:['SP','PE']}).success);assert.ok(ExportSchema.safeParse({age_months:'0-6',format:'csv'}).success);
 assert.ok(!QuerySchema.safeParse({age_months:6}).success);
});
test('posição preserva limites explícitos e evidência sem inferir idade de rótulos',()=>{
 assert.deepEqual(PositionSchema.parse(documented),documented);
 const labelOnly=PositionSchema.parse({...base,age_label:'Crianças pequenas',age_unknown_reason:'Fonte não explicita limites em unidades.'});
 assert.equal(labelOnly.age_min_months,undefined);assert.equal(labelOnly.age_max_months,undefined);
 assert.ok(PositionSchema.safeParse({...base,age_min_months:null,age_max_months:null}).success);
 assert.ok(PositionSchema.safeParse({...documented,age_evidence:[{...evidence,page:null,section:'Grupo explicitado pela fonte'}]}).success);
 for(const patch of [{age_max_months:undefined},{age_max_months:null},{age_min_months:-1},{age_min_months:1.5},{age_max_months:1801},{age_min_months:7},{age_evidence:[]},{age_evidence:[{...evidence,excerpt:'  '}]},{age_evidence:[{...evidence,page:null,section:null}]},{age_evidence:{...evidence}},{age_interval_origin:'inferred_from_code'}])assert.ok(!PositionSchema.safeParse({...documented,...patch}).success,JSON.stringify(patch));
});
test('OpenAPI expõe faixa documental nos inputs e posição com evidência na saída',()=>{
 const query=openapi.components.schemas.Query.properties!;assert.ok('age_months'in query);
 assert.ok(openapi.paths['/aprendizagens'].get.parameters.some(p=>p.name==='age_months'));
 const position=openapi.components.schemas.Position.properties!;for(const key of ['age_label','age_min_months','age_max_months','age_evidence','age_interval_origin','age_unknown_reason'])assert.ok(key in position,key);
 assert.match(openapi.info.description,/limites etários documentados com evidência/);
});
