// Review-only controls. The reviewed module is evaluated with artifact reads and
// SQL entry replaced by in-memory stubs. No repository input or DB is mutated.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import ts from 'typescript';
const root=process.cwd(), filename=path.resolve('src/domain/ingestion-update.ts');
let reviewed=await fs.readFile(filename,'utf8');
reviewed=reviewed.replace("import {pool} from '../db/client';",'const pool=globalThis.__peer.pool;')
 .replace("import {loadBundleFile} from './bundle-file';",'const loadBundleFile=globalThis.__peer.load;')
 .replace("import {importShardedManifest,shardRecords,verifyShardedManifest,type ShardedManifest} from './shards';",'type ShardedManifest=any; const {importShardedManifest,shardRecords,verifyShardedManifest}=globalThis.__peer.shards;');
reviewed=reviewed.replace(/from '(\.\.?\/[^']+)'/g,(_,relative)=>"from '"+pathToFileURL(path.resolve(path.dirname(filename),relative+'.ts')).href+"'");
const compiled=ts.transpileModule(reviewed,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
const raw={id:'peer-raw',publication_kind:'source_update_receipt',base_publication:'peer-base',base_artifact_sha256:'a'.repeat(64),target_source_ids:['peer-SP'],sources:[]};
globalThis.__peer={pool:{connect:async()=>{throw Object.assign(new Error('Reached SQL entry'),{code:'PEER_SQL_ENTRY'});}},load:async()=>({bundle:raw}),shards:{verifyShardedManifest:async()=>{},importShardedManifest:()=>{throw Error('Forbidden');},shardRecords:()=>{throw Error('Forbidden');}}};
const {prepareGlobalIngestionUpdate}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));
const {verifyPublicationSchema}=await import(pathToFileURL(path.resolve('src/domain/schema-pin.ts')).href);
const schema=await verifyPublicationSchema({schema_version:'1.1.0',schema_path:'data/schema/1.1.0.json',schema_sha256:'cfe3c8cf165f34faa7aa29fda55245df4ce1bfa47d3b4c8bde15eec6f588d5df'});
const baseSource={id:'peer-SP',uf:'SP',title:'TEST ONLY',issuer:'Peer fixture',official_url:'https://example.org/peer',artifact_url:null,stages:['EF'],components:[],document_type:'test_fixture',normative_parts:[],redistribution:'Test only',status:'test'};
const cases=[];
for(const [label,value] of [['absent',undefined],['empty-array',[]],['object',{}],['null',null],['string','pin-required'],['nonempty-array',[{}]]]){
 raw.sources=[{...baseSource,...(label==='absent'?{}:{technical_supersessions:value})}];
 schema.validate('Source',raw.sources[0]);
 let code;try{await prepareGlobalIngestionUpdate({base_publication:'peer-base',target_source_ids:['peer-SP'],raw_artifact:'unused',raw_artifact_sha256:'b'.repeat(64),base_artifact_sha256:'a'.repeat(64),actor_id:'peer',output_directory:'unused'});}catch(error){code=error.code;}
 cases.push({label,source_schema:'accepted',code});
}
assert.equal(cases.find(c=>c.label==='nonempty-array').code,'INGESTION_PROVENANCE_REQUIRED');
assert.equal(cases.find(c=>c.label==='object').code,'PEER_SQL_ENTRY');
assert.equal(cases.find(c=>c.label==='null').code,'PEER_SQL_ENTRY');
assert.equal(cases.find(c=>c.label==='string').code,'PEER_SQL_ENTRY');
console.log(JSON.stringify({scope:'pure-stub-control; no SQL/artifact writes; artifact verification stubbed to isolate gate',cases},null,2));
