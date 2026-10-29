/** Synthetic fixtures are confined to the harness-owned disposable test DB. */
import {after,before,test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdir,mkdtemp,readFile,readdir,rm,stat,writeFile} from 'node:fs/promises';
import {relative,resolve} from 'node:path';
import {pool} from '../src/db/client';
import {migrate} from '../scripts/migrate';
import {testDatabaseName} from './domain-safety';
import {importBundle,setDefaultPublication} from '../src/domain/publication';
import {canonicalProvenance,captureTechnicalBaseRecords,evaluateIngestionProvenance,provenanceDigest} from '../src/domain/ingestion-provenance';
import {exportIngestionBase,prepareGlobalIngestionUpdate,revalidatePreparedIngestionProvenance} from '../src/domain/ingestion-update';
import {resolvePublication} from '../src/domain/service';
import {writeShardedArtifact} from '../src/domain/shard-writer';
import type {Bundle,Learning,Source} from '../src/shared/contracts';

const allowed=process.env.DOMAIN_INTEGRATION_TEST==='1';
const sha=(value:string|Buffer)=>createHash('sha256').update(value).digest('hex');
const fixtureSource:Source={id:'provenance-source-SP',uf:'SP',title:'TEST ONLY provenance capture',issuer:'Synthetic isolated fixture',official_url:'https://example.org/provenance',artifact_url:'https://example.org/provenance.pdf',stages:['EF'],components:['Matemática'],edition:'fixture-1',document_date:null,homologation_date:null,application_period:null,document_type:'test_fixture',normative_parts:['part'],redistribution:'Test only',collected_at:null,sha256:null,local_path:null,status:'test'};
const fixtureItem=(id:string):Learning=>({id,curriculum_id:fixtureSource.id,source_id:fixtureSource.id,uf:'SP',code:null,text:'Synthetic literal text '+id+' — ação\nsegunda linha.',normalized_text:'producer form preserved',editorial_note:null,kind:'habilidade',parent_id:null,positions:[{stage:'EF',component:'Matemática',area:null,years:[6,7],year_label:'6º e 7º',age_group:null,period:null}],evidence:[{source_id:fixtureSource.id,page:2,printed_page:null,section:'Fixture',excerpt:'Synthetic literal text '+id+' — ação\nsegunda linha.'}],extraction_revision:'fixture-1',extraction_flags:[]});
const fixture:Bundle={id:'provenance-capture-source-fixture',schema_version:'1.1.0',schema_path:'data/schema/1.1.0.json',schema_sha256:'cfe3c8cf165f34faa7aa29fda55245df4ce1bfa47d3b4c8bde15eec6f588d5df',created_at:'2026-10-28T00:00:00Z',extraction_revision:'fixture-1',mapping_revision:'fixture-1',sources:[fixtureSource],items:[fixtureItem('capture-a'),fixtureItem('capture-b')],relations:[],coverage:[],changelog:[{type:'test_fixture'}]};
const numericPublication='provenance-exact-jsonb-fixture';
const numericSha='1'.repeat(64);
let directory='';

before(async()=>{
 if(!allowed)return;
 const owned=testDatabaseName(process.env.DATABASE_URL);
 assert.equal((await pool.query('SELECT current_database() AS name')).rows[0].name,owned);
 await pool.query('DROP SCHEMA public CASCADE');await pool.query('CREATE SCHEMA public');await migrate();
 await importBundle(fixture,{makeDefault:true});
 // A separate adversarial fixture is inserted once. No immutable row is updated
 // and no canonical numeric payload passes through JS's Number representation.
 await pool.query(`INSERT INTO publications(id,schema_version,created_at,extraction_revision,mapping_revision,sha256,item_count,source_count,relation_count,payload,storage_format)
 SELECT $1,schema_version,created_at,extraction_revision,mapping_revision,$3,item_count,source_count,relation_count,jsonb_set(payload,'{id}',to_jsonb($1::text)),storage_format FROM publications WHERE id=$2`,[numericPublication,fixture.id,numericSha]);
 await pool.query('INSERT INTO sources(publication_id,id,uf,payload) SELECT $1,id,uf,payload FROM sources WHERE publication_id=$2',[numericPublication,fixture.id]);
 await pool.query(`INSERT INTO items(publication_id,id,uf,curriculum_id,source_id,code,text,normalized_text,kind,positions,evidence,payload)
 SELECT $1,id,uf,curriculum_id,source_id,code,text,normalized_text,kind,positions,evidence,
 payload||'{"test_exact_numeric":{"large_integer":9007199254740993,"precise_decimal":1234567890.123456789012345678901234567890}}'::jsonb FROM items WHERE publication_id=$2`,[numericPublication,fixture.id]);
 await setDefaultPublication(numericPublication,{id:'isolated-test',actor_type:'automated',reason:'Publish a synthetic owned-test fixture for SQL-authority capture checks.'});
 await mkdir('var',{recursive:true});directory=await mkdtemp(resolve('var','domain-provenance-test-'));
});
after(async()=>{if(directory)await rm(directory,{recursive:true,force:true});await pool.end();});

test('canonical provenance hashes bounded envelopes and rejects numeric corpus coercion',()=>{
 const value={z:[true,null,'ação'],a:{count:3,path:'docs/evidence/proof.json'}};
 const expected='{"a":{"count":3,"path":"docs/evidence/proof.json"},"z":[true,null,"ação"]}';
 assert.equal(canonicalProvenance(value),expected);assert.equal(provenanceDigest(value),sha(expected));
 assert.equal(provenanceDigest(value),provenanceDigest({a:{path:'docs/evidence/proof.json',count:3},z:[true,null,'ação']}));
 // Python sort_keys sorts Unicode codepoints; JS's default UTF-16 sort does
 // the opposite for these keys. Real proof paths may contain Unicode.
 assert.equal(canonicalProvenance({'\u{10000}':2,'\uE000':1}),'{'+'"\uE000":1,"\u{10000}":2}');
 for(const malformed of [undefined,NaN,Infinity,-Infinity,1.5,9007199254740992,1n])assert.throws(()=>canonicalProvenance({malformed}));
});

test('same-ID technical ingestion replays the real CLI against SQL authority and pins events, proofs and candidate identity',{skip:!allowed},async()=>{
 await mkdir('data/bundles',{recursive:true});await mkdir('docs/evidence',{recursive:true});
 const bundleDirectory=await mkdtemp(resolve('data/bundles','domain-provenance-flow-'));
 const proofDirectory=await mkdtemp(resolve('docs/evidence','domain-provenance-proof-'));
 const records=<T>(values:T[])=>(async function*(){yield* values;})();
 try{
  const nationalSource:Source={...fixtureSource,id:'provenance-source-BR',uf:'BR',title:'TEST ONLY national context'};
  const national:Learning={...fixtureItem('provenance-national'),source_id:nationalSource.id,curriculum_id:nationalSource.id,uf:'BR',evidence:[{source_id:nationalSource.id,page:2,printed_page:null,section:'Fixture',excerpt:'Synthetic national context'}]};
  const targetSource:Source={...fixtureSource,sha256:'a'.repeat(64)};
  const target=fixtureItem('capture-a'),corrected={...target,text:'Corrected synthetic body, with no official amendment.',evidence:target.evidence.map(e=>({...e,excerpt:'Corrected synthetic body, with no official amendment.'}))};
  const base={...fixture,id:'provenance-technical-flow-base',sources:[nationalSource,targetSource],items:[national,target]};
  await importBundle(base,{makeDefault:true});
  const before=(await pool.query('SELECT sha256 FROM publications WHERE id=$1',[base.id])).rows[0].sha256;
  const context=await exportIngestionBase({base_publication:base.id,directory:resolve(bundleDirectory,'context')});
  assert.equal(context.base_publication_sha256,before);
  const proofFile=resolve(proofDirectory,'transcription.json');
  const proofBytes=JSON.stringify({scope:'synthetic-isolated-test-only',source_id:targetSource.id,source_sha256:targetSource.sha256,item_id:target.id,before_text:target.text,after_text:corrected.text});
  await writeFile(proofFile,proofBytes,{flag:'wx',mode:0o600});
  const proofPin={path:relative(process.cwd(),proofFile),sha256:sha(proofBytes)};
  const ledger={format:'record_text_corrections_v1',source_id:targetSource.id,source_sha256:targetSource.sha256,actor_type:'automated',actor_id:'isolated-provenance-test',previous_publications_immutable:true,official_curriculum_edition_changed:false,records:[{item_id:target.id,before_text:target.text,before_text_sha256:sha(target.text),after_text:corrected.text,after_text_sha256:sha(corrected.text),reason:'Synthetic isolated exact-body technical correction; not an official or pedagogical amendment.',proofs:[proofPin]}]};
  const ledgerFile=resolve(proofDirectory,'ledger.json'),ledgerBytes=JSON.stringify(ledger);await writeFile(ledgerFile,ledgerBytes,{flag:'wx',mode:0o600});
  const effectiveSource={...targetSource,technical_extraction_corrections:[{path:relative(process.cwd(),ledgerFile),sha256:sha(ledgerBytes),format:'record_text_corrections_v1',scope:'technical_extraction_correction'}]};
  const rawHeader={id:'raw-provenance-technical-fixture',schema_version:fixture.schema_version,schema_path:fixture.schema_path,schema_sha256:fixture.schema_sha256,created_at:'2026-10-28T01:00:00Z',extraction_revision:'fixture-2',mapping_revision:'fixture-2',sources:[nationalSource,effectiveSource],coverage:[],changelog:[],publication_kind:'source_update_receipt',base_publication:base.id,base_publication_sha256:before,base_artifact_sha256:context.artifact_sha256,target_source_ids:[targetSource.id],context_source_ids:[nationalSource.id],national_release_ready:false};
  const raw=await writeShardedArtifact(rawHeader,{items:records([national,corrected]),relations:records([])},{directory:resolve(bundleDirectory,'raw')});
  const rawReceipt={publication:raw.manifest.id,artifact:relative(process.cwd(),raw.filename),artifact_sha256:raw.sha256};
  const receiptDirectory=relative(process.cwd(),resolve(directory,'flow-receipts'));
  const jobScope={base_publication:base.id,base_publication_sha256:before,base_artifact_sha256:context.artifact_sha256,target_source_ids:[targetSource.id],context_source_ids:[nationalSource.id]};
  const evaluation=await evaluateIngestionProvenance({effective_raw_receipt:rawReceipt,job_scope:jobScope,receipt_directory:receiptDirectory});
  const input={base_publication:base.id,target_source_ids:[targetSource.id],raw_artifact:raw.filename,raw_artifact_sha256:raw.sha256,base_artifact_sha256:context.artifact_sha256,output_directory:resolve(bundleDirectory,'candidate'),actor_id:'ingestion-job:synthetic-provenance',provenance:{original_raw_receipt:rawReceipt,raster_stage_receipt:null,technical_evaluation_receipt:evaluation,receipt_directory:receiptDirectory}};
  const prepared=await prepareGlobalIngestionUpdate(input);assert.ok(prepared.provenance_receipt);
  assert.equal(await resolvePublication(),base.id);assert.notEqual(prepared.publication,raw.manifest.id);
  const candidate=(await pool.query('SELECT payload,sha256 FROM publications WHERE id=$1',[prepared.publication])).rows[0];
  const metadata=candidate.payload,technical=metadata.changelog.find((event:{same_id?:boolean})=>event.same_id);
  assert.equal(technical.item_id,target.id);assert.equal(technical.source_id,targetSource.id);assert.equal(technical.observed_effect,'corrects_text_in_pinned_base');assert.equal(technical.effect_base_publication,base.id);assert.equal(technical.effect_base_publication_sha256,before);assert.equal(technical.actor_type,'automated');assert.equal(technical.official_curriculum_edition_changed,false);
  assert.equal(metadata.orchestration_sha256,provenanceDigest(metadata.orchestration_provenance));assert.equal(metadata.technical_events_sha256,provenanceDigest(metadata.technical_identity_payload));
  assert.deepEqual(metadata.orchestration_provenance.original_raw_receipt,rawReceipt);assert.deepEqual(metadata.orchestration_provenance.effective_raw_receipt,rawReceipt);assert.equal(metadata.orchestration_provenance.raster_stage,null);assert.equal(metadata.orchestration_provenance.technical_stage.sql_authority,'domain_postgresql_repeatable_read');
  assert.equal((await pool.query('SELECT text FROM items WHERE publication_id=$1 AND id=$2',[base.id,target.id])).rows[0].text,target.text);
  assert.equal((await pool.query('SELECT text FROM items WHERE publication_id=$1 AND id=$2',[prepared.publication,target.id])).rows[0].text,corrected.text);
  assert.equal((await pool.query('SELECT sha256 FROM publications WHERE id=$1',[base.id])).rows[0].sha256,before);
  const replay=await prepareGlobalIngestionUpdate(input);assert.equal(replay.publication,prepared.publication);assert.equal(replay.artifact_sha256,prepared.artifact_sha256);assert.equal(replay.import_receipt.already_imported,true);
  const resumed=await revalidatePreparedIngestionProvenance(input,prepared.publication);assert.equal(resumed.orchestration_sha256,metadata.orchestration_sha256);
  await assert.rejects(()=>importBundle({...base,id:prepared.publication},{makeDefault:false}),error=>error instanceof Error&&'code'in error&&error.code==='IMMUTABLE_PUBLICATION');
  await writeFile(proofFile,proofBytes+'\n');
  await assert.rejects(()=>revalidatePreparedIngestionProvenance(input,prepared.publication),error=>error instanceof Error&&'code'in error&&['INGESTION_PROVENANCE_MISMATCH','TECHNICAL_PROVENANCE_REPLAY_FAILED'].includes(String(error.code)));
  assert.equal((await pool.query('SELECT sha256 FROM publications WHERE id=$1',[prepared.publication])).rows[0].sha256,candidate.sha256);
  assert.equal(await resolvePublication(),base.id);
 }finally{await rm(bundleDirectory,{recursive:true,force:true});await rm(proofDirectory,{recursive:true,force:true});}
});

test('SQL technical capture preserves precise JSONB numbers, absent IDs, atomic bytes and replay',{skip:!allowed},async()=>{
 const client=await pool.connect();
 try{
  await client.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');
  const output=relative(process.cwd(),resolve(directory,'capture.json'));
  const request={base_publication:numericPublication,base_publication_sha256:numericSha,queried_item_ids:['capture-b','missing-id','capture-a'],output_file:output};
  const captured=await captureTechnicalBaseRecords(client,request),bytes=await readFile(output),text=bytes.toString('utf8');
  assert.equal(captured.pin.path,output);assert.equal(captured.pin.sha256,sha(bytes));assert.deepEqual(captured.queried_item_ids,['capture-a','capture-b','missing-id']);
  assert.deepEqual([...captured.observed.keys()],['capture-a','capture-b']);assert.equal(captured.observed.has('missing-id'),false);
  assert.equal(captured.observed.get('capture-a')?.text_sha256,sha(fixture.items[0].text));assert.equal(captured.observed.get('capture-a')?.source_id,fixtureSource.id);
  assert.match(text,/"large_integer": 9007199254740993/);assert.doesNotMatch(text,/9007199254740992/);
  assert.match(text,/"precise_decimal": 1234567890\.123456789012345678901234567890/);
  const sql=(await client.query('SELECT id,payload::text AS exact FROM items WHERE publication_id=$1 ORDER BY id',[numericPublication])).rows;
  assert.equal(text.slice(text.indexOf('"records":[')+11,-2),sql.map(row=>row.exact).join(','));
  const parsed=JSON.parse(text) as {queried_item_ids:string[];records:Learning[]};assert.deepEqual(parsed.queried_item_ids,captured.queried_item_ids);assert.deepEqual(parsed.records.map(item=>item.id),['capture-a','capture-b']);
  assert.equal((await stat(output)).mode&0o777,0o600);assert.equal((await readdir(directory)).some(name=>name.includes('.tmp-')),false);
  const replay=await captureTechnicalBaseRecords(client,{...request,queried_item_ids:[...request.queried_item_ids].reverse()});
  assert.deepEqual(replay.pin,captured.pin);assert.deepEqual(await readFile(output),bytes);
  // Publication hashes and canonical numeric payloads remain exactly untouched.
  assert.equal((await client.query('SELECT sha256 FROM publications WHERE id=$1',[numericPublication])).rows[0].sha256,numericSha);
  assert.deepEqual((await client.query('SELECT id,payload::text AS exact FROM items WHERE publication_id=$1 ORDER BY id',[numericPublication])).rows,sql);
  await client.query('ROLLBACK');
 }finally{await client.query('ROLLBACK').catch(()=>{});client.release();}
});

test('SQL capture rejects false publication authority, duplicate IDs, unsafe output and immutable collisions',{skip:!allowed},async()=>{
 const hidden={...fixture,id:'provenance-unpublished-fixture'};await importBundle(hidden,{makeDefault:false});
 const client=await pool.connect();
 try{
  const output=relative(process.cwd(),resolve(directory,'negative.json'));
  const request={base_publication:numericPublication,base_publication_sha256:numericSha,queried_item_ids:['capture-a'],output_file:output};
  const mismatch=(error:unknown)=>error instanceof Error&&'code'in error&&error.code==='INGESTION_PROVENANCE_MISMATCH';
  await assert.rejects(()=>captureTechnicalBaseRecords(client,{...request,base_publication_sha256:'2'.repeat(64)}),mismatch);
  const hiddenSha=(await client.query('SELECT sha256 FROM publications WHERE id=$1',[hidden.id])).rows[0].sha256;
  await assert.rejects(()=>captureTechnicalBaseRecords(client,{...request,base_publication:hidden.id,base_publication_sha256:hiddenSha}),mismatch);
  await assert.rejects(()=>captureTechnicalBaseRecords(client,{...request,base_publication:'nonexistent-publication'}),mismatch);
  await assert.rejects(()=>captureTechnicalBaseRecords(client,{...request,queried_item_ids:['capture-a','capture-a']}),mismatch);
  await assert.rejects(()=>captureTechnicalBaseRecords(client,{...request,output_file:'var/../data/bundles/forged-capture.json'}),mismatch);
  await assert.rejects(()=>captureTechnicalBaseRecords(client,{...request,output_file:resolve(directory,'absolute.json')}),mismatch);
  const marker=Buffer.from('Existing immutable receipt');await writeFile(output,marker,{flag:'wx',mode:0o600});
  await assert.rejects(()=>captureTechnicalBaseRecords(client,request),mismatch);assert.deepEqual(await readFile(output),marker);
  assert.equal((await readdir(directory)).some(name=>name.includes('.tmp-')),false);
 }finally{client.release();}
});
