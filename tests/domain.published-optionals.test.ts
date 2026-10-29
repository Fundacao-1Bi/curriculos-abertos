/** Synthetic contract fixtures are isolated to an owned disposable *_test database. */
import {test,before,after} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';
import {resolve,relative} from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {validateBundle,importBundle} from '../src/domain/publication';
import {verifyShardedManifest,importShardedManifest,type ShardedManifest} from '../src/domain/shards';
import {verifyPublicationSchema,PUBLICATION_SCHEMAS} from '../src/domain/schema-pin';
import {validEvidence} from '../src/domain/record-contract';
import {pool} from '../src/db/client';
import {migrate} from '../scripts/migrate';
import {testDatabaseName} from './domain-safety';
import type {Bundle,Learning,Source} from '../src/shared/contracts';

const source:Source={id:'fixture-optionals-PE',uf:'PE',title:'TEST FIXTURE — optional metadata',issuer:'Isolated automated fixture',official_url:'https://example.invalid/fixture',artifact_url:null,stages:['EF'],components:[],document_type:'test_fixture',normative_parts:[],redistribution:'fixture_only',status:'test'};
const first:Learning={id:'fixture-sparse-item',curriculum_id:source.id,source_id:source.id,uf:'PE',code:null,text:'TEST FIXTURE — sparse source position.',normalized_text:'producer form retained',editorial_note:null,kind:'habilidade',parent_id:null,positions:[{stage:'EF'}],evidence:[{source_id:source.id,page:1,excerpt:'TEST FIXTURE — sparse source position.'}],extraction_revision:'test-contract'};
const second:Learning={...first,id:'fixture-null-item',text:'TEST FIXTURE — explicit null retained.',parent_id:first.id,positions:[{stage:'EF',component:null,area:null,years:null,year_label:null,age_group:null,period:null}]};
function fixture(id='optional-contract-unit'):Bundle{return{id,schema_version:'1.1.0',schema_path:'data/schema/1.1.0.json',schema_sha256:PUBLICATION_SCHEMAS['1.1.0'],created_at:'2026-10-28T00:00:00Z',extraction_revision:'fixture-contract',mapping_revision:'fixture-contract',sources:structuredClone([source]),items:structuredClone([first,second]),relations:[{id:'fixture-relation',members:[{item_id:second.id,role:'source',scope:'fixture'},{item_id:first.id,role:'target',scope:'fixture'}],relation_type:'fixture_reference',origin:'fixture_only',technical_validation_status:'fixture',pedagogical_review_status:'not_reviewed',publication_status:'fixture',method:'Isolated fixture',evidence:[{source_id:source.id,page:null,section:'Fixture section',excerpt:'TEST FIXTURE — relation proof.'}]}],coverage:[],changelog:[]};}

test('all published optional fields remain absent under both manual and pinned-schema validation',async()=>{
 const value=fixture(),before=JSON.stringify(value);validateBundle(value);const schema=await verifyPublicationSchema(value);
 for(const row of value.sources)schema.validate('Source',row);for(const row of value.items)schema.validate('Learning',row);for(const row of value.relations)schema.validate('Relation',row);
 assert.equal(JSON.stringify(value),before);assert.deepEqual(value.items[0].positions,[{stage:'EF'}]);assert.equal(Object.hasOwn(value.sources[0],'sha256'),false);assert.equal(Object.hasOwn(value.items[0].evidence[0],'printed_page'),false);
});

test('manual guards reject wrong supplied values and required-field loss without coercion',()=>{
 for(const mutate of [
  (b:Bundle)=>{b.sources[0].sha256='bad';},(b:Bundle)=>{(b.sources[0] as unknown as Record<string,unknown>).edition=4;},
  (b:Bundle)=>{delete (b.sources[0] as unknown as Record<string,unknown>).artifact_url;},
  (b:Bundle)=>{(b.items[0].positions[0] as unknown as Record<string,unknown>).area=3;},
  (b:Bundle)=>{b.items[0].positions[0].years=[0];},(b:Bundle)=>{b.items[0].positions[0].years=[13];},
  (b:Bundle)=>{delete (b.items[0].positions[0] as unknown as Record<string,unknown>).stage;},
  (b:Bundle)=>{delete (b.items[0].evidence[0] as unknown as Record<string,unknown>).page;},
  (b:Bundle)=>{b.items[0].evidence[0].page=null;},
  (b:Bundle)=>{(b.items[0].evidence[0] as unknown as Record<string,unknown>).printed_page=2;},
  (b:Bundle)=>{(b.relations[0].evidence[0] as unknown as Record<string,unknown>).printed_page=2;},
  (b:Bundle)=>{(b.relations[0].evidence[0] as unknown as Record<string,unknown>).bbox=[1,2,3];},
 ]){const value=fixture();mutate(value);const before=JSON.stringify(value);assert.throws(()=>validateBundle(value));assert.equal(JSON.stringify(value),before);}
 assert.ok(validEvidence({source_id:source.id,page:1,excerpt:'Proof.'},new Set([source.id])));
 assert.equal(validEvidence({source_id:source.id,page:null,excerpt:'Proof.'},new Set([source.id])),false);
});

const integration=process.env.OPTIONAL_CONTRACT_INTEGRATION==='1';
before(async()=>{if(!integration)return;const expected=testDatabaseName(process.env.DATABASE_URL);const current=await pool.query('SELECT current_database() AS name');assert.equal(current.rows[0].name,expected);await migrate();});
after(async()=>{await pool.end();});
async function exactStored(bundle:Bundle){
 for(const table of ['sources','items','relations'] as const){const rows=await pool.query(`SELECT payload FROM ${table} WHERE publication_id=$1 ORDER BY id`,[bundle.id]);assert.deepEqual(rows.rows.map(row=>row.payload),[...bundle[table]].sort((a,b)=>a.id.localeCompare(b.id)));}
 const row=(await pool.query("SELECT payload->'positions'->0 ? 'area' AS area_present,payload->'positions'->0 ? 'period' AS period_present,payload->'evidence'->0 ? 'printed_page' AS printed_page_present FROM items WHERE publication_id=$1 AND id=$2",[bundle.id,first.id])).rows[0];assert.deepEqual(row,{area_present:false,period_present:false,printed_page_present:false});
}

test('real PostgreSQL embedded import preserves sparse and explicit-null records exactly',{skip:!integration},async()=>{
 const bundle=fixture('optional-contract-embedded');await importBundle(bundle,{makeDefault:false});await exactStored(bundle);assert.equal((await importBundle(bundle)).already_imported,true);
});

test('real PostgreSQL sharded import checks the same optional contract and rejects malformed supplied metadata',{skip:!integration},async()=>{
 await mkdir('var',{recursive:true});const root=await mkdtemp(resolve('var','optional-contract-shards-'));const bundle=fixture('optional-contract-sharded');
 const hash=(b:Buffer)=>createHash('sha256').update(b).digest('hex');
 try{
  const part=async(kind:'items'|'relations',rows:unknown[],label:string)=>{const decoded=Buffer.from(rows.map(row=>JSON.stringify(row)).join('\n')+'\n'),compressed=gzipSync(decoded),path=resolve(root,label+'.jsonl.gz');await writeFile(path,compressed);return{kind,path:relative(process.cwd(),path),sha256:hash(compressed),bytes:compressed.length,decoded_sha256:hash(decoded),decoded_bytes:decoded.length,records:rows.length};};
  const {items,relations,...header}=bundle;const manifest={...header,format:'curriculos-abertos/sharded-v1',item_count:items.length,relation_count:relations.length,source_count:bundle.sources.length,parts:[await part('items',items,'items'),await part('relations',relations,'relations')]} as unknown as ShardedManifest;
  const verified=await verifyShardedManifest(manifest,root);assert.equal(verified.item_count,2);assert.equal(verified.relation_count,1);
  await importShardedManifest(manifest,hash(Buffer.from(JSON.stringify(manifest))),{root,makeDefault:false});await exactStored(bundle);
  const bad=structuredClone(relations);(bad[0].evidence[0] as unknown as Record<string,unknown>).printed_page=2;
  const malformed={...manifest,id:'optional-contract-sharded-rejected',parts:[manifest.parts[0],await part('relations',bad,'bad-relations')]};
  await assert.rejects(()=>importShardedManifest(malformed,hash(Buffer.from(JSON.stringify(malformed))),{root,makeDefault:false}));assert.equal((await pool.query('SELECT count(*)::int AS n FROM publications WHERE id=$1',[malformed.id])).rows[0].n,0);
 }finally{await rm(root,{recursive:true,force:true});}
});
