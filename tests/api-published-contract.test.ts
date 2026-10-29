import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { z } from 'zod';
import { EvidenceSchema, LearningSchema, PositionSchema, SourceSchema } from '../src/mcp/contracts';
import { openapi } from '../src/mcp/openapi';

const schemaPath=new URL('../data/schema/1.1.0.json',import.meta.url);
const published=JSON.parse(readFileSync(schemaPath,'utf8')) as {$defs:Record<string,{required?:string[]}>};
const omitted=['component','area','years','year_label','age_group','period'] as const;

test('published 1.1 Position requires only stage; absence is retained without defaults',()=>{
 assert.deepEqual(published.$defs.Position.required,['stage']);
 const sparse={stage:'EF',source_column:'explicit source metadata'};
 assert.deepEqual(PositionSchema.parse(sparse),sparse);
 for(const key of omitted)assert.equal(Object.hasOwn(PositionSchema.parse(sparse),key),false,key);
 const explicitNull={stage:'EF',...Object.fromEntries(omitted.map(key=>[key,null]))};
 assert.deepEqual(PositionSchema.parse(explicitNull),explicitNull);
 assert.deepEqual(z.toJSONSchema(PositionSchema,{unrepresentable:'any'}).required,['stage']);
 assert.deepEqual(openapi.components.schemas.Position.required,['stage']);
});

test('published field types and inclusive school-year limits remain enforced',()=>{
 for(const invalid of [{},{stage:null},{stage:'EJA'},{stage:'EF',area:2},{stage:'EF',years:'6'},...[[0],[13],[1.5]].map(years=>({stage:'EF',years}))])assert.ok(!PositionSchema.safeParse(invalid).success,JSON.stringify(invalid));
 for(const valid of [{stage:'EI'},{stage:'EF',years:[1,12]},{stage:'EM',years:[]},{stage:'EF',area:null,age_group:null}])assert.ok(PositionSchema.safeParse(valid).success);
});

test('Evidence optional printed_page/section follow the published contract without losing localizability',()=>{
 const page={source_id:'fixture-source',page:1,excerpt:'Literal source text.'};
 assert.deepEqual(EvidenceSchema.parse(page),page);
 assert.deepEqual(EvidenceSchema.parse({...page,page:null,section:'Quadro de objetivos'}),{...page,page:null,section:'Quadro de objetivos'});
 assert.deepEqual(z.toJSONSchema(EvidenceSchema,{unrepresentable:'any'}).required,published.$defs.Evidence.required);
 for(const invalid of [{...page,page:0},{...page,page:null},{...page,page:null,section:''},{...page,excerpt:''},{...page,bbox:[0,1,2]}])assert.ok(!EvidenceSchema.safeParse(invalid).success,JSON.stringify(invalid));
});

test('optional published Source dates and identifiers remain absent in transport',()=>{
 const source={id:'fixture-source',uf:'PE',title:'Fonte de teste isolado',issuer:'SEDUC',official_url:'https://example.invalid/document',artifact_url:null,stages:['EF'],components:[],document_type:'currículo',normative_parts:[],redistribution:'source_link',status:'fixture'};
 assert.deepEqual(SourceSchema.parse(source),source);
 assert.deepEqual([...z.toJSONSchema(SourceSchema,{unrepresentable:'any'}).required!].sort(),[...published.$defs.Source.required!].sort());
});

test('Learning round-trip accepts a legitimately sparse PE-style position and retains its exact payload',()=>{
 const item={id:'fixture-item',source_id:'fixture-source',curriculum_id:'fixture-source',uf:'PE',code:null,text:'Texto literal de fixture.',normalized_text:'texto literal',editorial_note:null,kind:'habilidade',parent_id:null,positions:[{stage:'EM',component:'Arte',years:[1],year_label:'1º ano',period:'1º trimestre'}],evidence:[{source_id:'fixture-source',page:1,excerpt:'Texto literal de fixture.'}],extraction_revision:'fixture-contract'};
 assert.deepEqual(LearningSchema.parse(item),item);
});

test('immutable published schema bytes were not changed by the transport correction',()=>{
 assert.equal(createHash('sha256').update(readFileSync(schemaPath)).digest('hex'),'cfe3c8cf165f34faa7aa29fda55245df4ce1bfa47d3b4c8bde15eec6f588d5df');
});
