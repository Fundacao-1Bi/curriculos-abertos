/** Synthetic fixtures only; never connects to the national QA database. */
import {after,before,test} from 'node:test';
import assert from 'node:assert/strict';
import {pool} from '../src/db/client';
import {migrate} from '../scripts/migrate';
import {importBundle,setDefaultPublication} from '../src/domain/publication';
import {itemFilter,searchLearnings} from '../src/domain/service';
import {normalize} from '../src/domain/normalize';
import {PUBLICATION_SCHEMAS} from '../src/domain/schema-pin';
import type {Bundle,Learning,Query,Source} from '../src/shared/contracts';
import {testDatabaseName} from './domain-safety';

const enabled=process.env.DOMAIN_INTEGRATION_TEST==='1',publication='union-search-fixture';
const source:Source={id:'union-source-sp',uf:'SP',title:'Synthetic search regression fixture',issuer:'Automated fixture',official_url:'https://example.invalid/search',artifact_url:null,stages:['EF'],components:['Matemática'],edition:'fixture-edition',document_type:'test_fixture',normative_parts:[],redistribution:'fixture_only',status:'test'};
const position={stage:'EF' as const,component:'Matemática',area:'Matemática',years:[5],year_label:'5º ano',age_group:null,period:'anual'};
const make=(id:string,code:string|null,text:string,extra:Partial<Learning>={}):Learning=>({id,code,text,curriculum_id:source.id,source_id:source.id,uf:'SP',normalized_text:'',editorial_note:null,kind:'habilidade',parent_id:'union-parent',positions:[position],evidence:[{source_id:extra.source_id??source.id,page:1,excerpt:text}],extraction_revision:'fixture',...extra});
const items:Learning[]=[
 make('union-parent',null,'Synthetic parent',{parent_id:null,kind:'unidade_tematica',positions:[]}),
 make('numeric-exact','1.1','Explorar números e proporção.'),
 make('numeric-prefix','1.10','Observar números.'),
 make('numeric-body','ABC','Localizar a referência 1.1 no texto.'),
 make('alias','EF05CO011','Explorar algoritmos.',{code_aliases:['EF 05 CO 11']}),
 make('pdf','PDF','Explorar a proporção e des-\ncrever processos matemáticos.'),
 make('compound','COMPOUND','Preservar guarda-chuva e pré-escola.'),
 make('accent','ACCENT','Analisar ação, descrição e proporções.'),
 make('literal','LIT_%\\Z','Marcadores literais: 100% e sub_linha.'),
 make('other-year','1.11','Explorar números.',{positions:[{...position,years:[6]}]}),
 make('other-period','1.12','Explorar números.',{positions:[{...position,period:'semestral'}]}),
 make('other-parent','1.13','Explorar números.',{parent_id:null}),
 make('other-uf','1.14','Explorar números.',{uf:'RJ',source_id:'union-source-rj',curriculum_id:'union-source-rj'}),
 make('national','NATIONAL','National fixture',{uf:'BR',source_id:'union-source-br',curriculum_id:'union-source-br',parent_id:null}),
];
function bundle(id=publication):Bundle{return{id,schema_version:'1.1.0',schema_path:'data/schema/1.1.0.json',schema_sha256:PUBLICATION_SCHEMAS['1.1.0'],created_at:'2026-10-28T00:00:00Z',extraction_revision:'fixture',mapping_revision:'fixture',sources:[source,{...source,id:'union-source-rj',uf:'RJ'},{...source,id:'union-source-br',uf:'BR'}],items:structuredClone(items),relations:[{id:'union-relation',members:[{item_id:'numeric-exact',role:'source',scope:'fixture'},{item_id:'national',role:'target',scope:'fixture'}],relation_type:'explicit_reference',origin:'source_declaration',technical_validation_status:'verified',pedagogical_review_status:'not_reviewed',publication_status:'published',method:'Synthetic fixture',evidence:[{source_id:source.id,page:1,excerpt:'Fixture relation'}]}],coverage:[],changelog:[]};}

// Historical combined-OR oracle, deliberately retained independently of the
// new branch layout. It exercises the old semantics on the same PostgreSQL.
function legacy(q:Query,pub=publication){
 const base=itemFilter({...q,q:undefined},pub),values=[...base.values];
 const bind=(v:unknown)=>{values.push(v);return '$'+values.length;};
 const needle=normalize(String(q.q??'')),compact=needle.replace(/[\p{White_Space}\uFEFF]/gu,'');
 const like=bind('%'+needle.replace(/[\\%_]/g,'\\$&')+'%'),term=bind(needle),code=bind(compact),codeLike=bind('%'+compact.replace(/[\\%_]/g,'\\$&')+'%'),aliases=bind(JSON.stringify([compact]));
 const pdf="i.normalized_text ~ '[[:alpha:]]-[[:space:]]+[[:alpha:]]'";
 const where=`${base.where} AND (curriculum_search_code(i.code)=${code} OR curriculum_search_code(i.code) LIKE ${codeLike} ESCAPE '\\' OR i.normalized_text LIKE ${like} ESCAPE '\\' OR i.search_vector @@ plainto_tsquery('portuguese',${term}) OR curriculum_search_aliases(i.payload->'code_aliases') @> ${aliases}::jsonb OR (${pdf} AND (public.curriculum_join_pdf_hyphens(i.normalized_text) LIKE ${like} ESCAPE '\\' OR pg_catalog.to_tsvector('pg_catalog.portuguese'::pg_catalog.regconfig,public.curriculum_join_pdf_hyphens(i.normalized_text)) @@ pg_catalog.plainto_tsquery('pg_catalog.portuguese'::pg_catalog.regconfig,${term}))))`;
 const rank=`CASE WHEN curriculum_search_code(i.code)=${code} THEN 100 WHEN curriculum_search_aliases(i.payload->'code_aliases') @> ${aliases}::jsonb THEN 90 WHEN curriculum_search_code(i.code) LIKE (${code} || '%') THEN 80 WHEN i.normalized_text LIKE ${like} ESCAPE '\\' THEN 20 WHEN ${pdf} AND public.curriculum_join_pdf_hyphens(i.normalized_text) LIKE ${like} ESCAPE '\\' THEN 18 ELSE 1 END`;
 return{where,rank,values};
}
async function ids(filter:ReturnType<typeof itemFilter>){return(await pool.query(`SELECT i.id FROM items i WHERE ${filter.where} ORDER BY ${filter.rank} DESC,i.code NULLS LAST,i.id`,filter.values)).rows.map(r=>r.id as string);}

before(async()=>{if(!enabled)return;const expected=testDatabaseName(process.env.DATABASE_URL);assert.equal((await pool.query('SELECT current_database() AS name')).rows[0].name,expected);await migrate();await importBundle(bundle(),{makeDefault:true});const other=bundle('union-other-publication');other.items=other.items.map(i=>({...i,text:i.id==='numeric-exact'?'Different publication only.':i.text}));other.items.push(make('other-publication-only','1.15','Only in other publication.'));await importBundle(other,{makeDefault:true});await setDefaultPublication(publication,{id:'union-search-test',actor_type:'automated',reason:'Restore primary fixture after publishing the isolated alternate fixture.'});});
after(async()=>{await pool.end();});

test('UNION retains all seven independent indexed branches and every contextual predicate',()=>{
 const filter=itemFilter({q:'1.1',uf:'SP',stage:'EF',component:'Matemática',year:'5',parent_id:'union-parent',source_id:source.id,publication_status:'published'},publication);
 assert.equal((filter.where.match(/SELECT i.id FROM items i WHERE/g)??[]).length,7);
 assert.equal((filter.where.match(/i.publication_id=\$1/g)??[]).length,8);
 for(const predicate of ['i.uf=ANY','i.source_id=','i.payload->>\'parent_id\'=','jsonb_array_elements(i.positions)','relation_members rm JOIN relations rr'])assert.equal(filter.where.split(predicate).length-1,8,predicate);
 assert.match(filter.where,/i\.positions @> \$\d+::jsonb/);
 assert.ok(filter.values.includes('[{"stage":"EF"}]'));
 assert.match(filter.where,/EXISTS\(SELECT 1 FROM jsonb_array_elements\(i\.positions\) p WHERE p->>\'stage\'=\$\d+/);
 const unknownPositions=itemFilter({stage:'EF',include_unknown_positions:true},publication);
 assert.doesNotMatch(unknownPositions.where,/i\.positions @>/);
 assert.match(unknownPositions.where,/jsonb_array_length\(i\.positions\)=0/);
 assert.equal(itemFilter({},publication).where,'i.publication_id=$1');
});

test('real PostgreSQL old OR and UNION return identical complete ordered IDs for short, accented, hyphenated and escaped terms',{skip:!enabled},async()=>{
 for(const q of ['1.1','1','a','ação','ACAO','proporção','descrever','guarda-chuva','guardachuva','pré-escola','EF\u00a005\u2003CO 11','LIT_%\\Z','100%','sub_linha','inexistente']){
  const query={q};assert.deepEqual(await ids(itemFilter(query,publication)),await ids(legacy(query)),q);
 }
 assert.deepEqual(await ids(itemFilter({q:'EF\u00a005 CO 11'},publication)),['alias']);
 assert.deepEqual(await ids(itemFilter({q:'descrever'},publication)),['pdf']);
 assert.deepEqual(await ids(itemFilter({q:'guardachuva'},publication)),[]);
 assert.deepEqual(await ids(itemFilter({q:'LIT_%\\Z'},publication)),['literal']);
 assert.deepEqual(await ids(itemFilter({q:'100%'},publication)),['literal']);
 assert.equal((await pool.query('SELECT payload FROM items WHERE publication_id=$1 AND id=$2',[publication,'pdf'])).rows[0].payload.text,items.find(i=>i.id==='pdf')!.text);
});

test('real PostgreSQL stage prefilter preserves exact matches and unknown-position fallback',{skip:!enabled},async()=>{
 const expected=items.filter(item=>item.positions.some(position=>position.stage==='EF')).map(item=>item.id).sort();
 assert.deepEqual((await ids(itemFilter({stage:'EF'},publication))).sort(),expected);
 const unknownExpected=[...expected,'union-parent'].sort();
 assert.deepEqual((await ids(itemFilter({stage:'EF',include_unknown_positions:true},publication))).sort(),unknownExpected);
});

test('real PostgreSQL combined filters and origin aliases apply identically in every branch',{skip:!enabled},async()=>{
 const filters:Query[]=[
  {uf:'SP',stage:'EF',component:'matematica',year:'5',period:'anual',parent_id:'union-parent',source_id:source.id,curriculum:source.id,edition:'fixture-edition',kind:'habilidade'},
  {uf:'SP',stage:'EF',area:'matemática',year:'5-6',national_id:'national',relation_type:'explicit_reference',origin:'declaracao_fonte',technical_validation_status:'verified',pedagogical_review_status:'not_reviewed',publication_status:'published'},
  {uf:'RJ',year:'5'}, {year:'6'}, {period:'semestral'}, {source_id:'union-source-br'},
 ];
 for(const f of filters){const query={...f,q:'1.1'};assert.deepEqual(await ids(itemFilter(query,publication)),await ids(legacy(query)));}
 assert.deepEqual(await ids(itemFilter({...filters[1],q:'1.1'},publication)),['numeric-exact']);
 assert.deepEqual(await ids(itemFilter({...filters[0],q:'1.1'},publication)),['numeric-exact','numeric-prefix','numeric-body']);
});

test('real service pagination is stable, deduplicated, pinned and keeps filters in next links',{skip:!enabled},async()=>{
 const query={q:'1.1',publication,uf:'SP',year:'5',period:'anual',parent_id:'union-parent',limit:2};
 const expected=await ids(legacy(query));assert.equal(expected.length,3);
 const first=await searchLearnings(query),second=await searchLearnings({...query,page:2});
 assert.equal(first.total,3);assert.equal(second.total,3);assert.equal(second.next,null);
 assert.deepEqual([...first.data,...second.data].map(i=>i.id),expected);
 assert.equal(new Set([...first.data,...second.data].map(i=>i.id)).size,expected.length);
 const next=new URL(String(first.next),'https://example.invalid');for(const[k,v]of Object.entries({...query,page:2}))assert.equal(next.searchParams.get(k),String(v),k);
 const pinned=await searchLearnings({q:'Different publication only',publication});assert.equal(pinned.total,0);
 const other=await searchLearnings({q:'Different publication only',publication:'union-other-publication'});assert.deepEqual(other.data.map(i=>i.id),['numeric-exact']);
 assert.equal((await searchLearnings({q:'1.1',publication,limit:100})).data.some(i=>i.id==='other-publication-only'),false);
});
