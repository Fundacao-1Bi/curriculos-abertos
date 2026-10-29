// No real SQL, corpus writes or edits to product files.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import ts from 'typescript';
const evidence=path.resolve('docs/evidence/source-audit-domain-orchestration-peer');
const updateFile=path.resolve('src/domain/ingestion-update.ts');
const bridgeFile=path.resolve('src/domain/ingestion-provenance.ts');
const sourceUpdate=await fs.readFile(updateFile,'utf8'),sourceBridge=await fs.readFile(bridgeFile,'utf8');
const hashes={};for(const f of [updateFile,bridgeFile])hashes[path.relative(process.cwd(),f)]=createHash('sha256').update(await fs.readFile(f)).digest('hex');
function localImports(source,filename){return source.replace(/from '(\.\.?\/[^']+)'/g,(_,relative)=>"from '"+pathToFileURL(path.resolve(path.dirname(filename),relative+'.ts')).href+"'");}
function compile(source){return ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;}
let changedUpdate=sourceUpdate.replace("import {pool} from '../db/client';",'const pool=globalThis.__followup.pool;')
 .replace("import {loadBundleFile} from './bundle-file';",'const loadBundleFile=globalThis.__followup.load;')
 .replace("import {importShardedManifest,shardRecords,verifyShardedManifest,type ShardedManifest} from './shards';",'type ShardedManifest=any; const {importShardedManifest,shardRecords,verifyShardedManifest}=globalThis.__followup.shards;')
 .replace("import {writeShardedArtifact} from './shard-writer';",'const writeShardedArtifact=(...args:any[])=>globalThis.__followup.write(...args);')
 .replace("import {mergeIngestionCoverage} from './ingestion-coverage';",'const mergeIngestionCoverage=async()=>[];');
const raw={id:'peer-raw',publication_kind:'source_update_receipt',base_publication:'peer-base',base_publication_sha256:'c'.repeat(64),base_artifact_sha256:'a'.repeat(64),target_source_ids:['peer-SP'],context_source_ids:['peer-BR'],sources:[],parts:[],coverage:[]};
let imports=0,queries=[],writerCalls=0;
globalThis.__followup={pool:{connect:async()=>{throw Object.assign(new Error('Reached SQL entry'),{code:'PEER_SQL_ENTRY'});}},load:async()=>({bundle:raw}),shards:{verifyShardedManifest:async()=>{},importShardedManifest:async()=>{imports++;return{};},shardRecords:()=>{throw Error('Unexpected shard iteration');}},write:()=>{throw Error('Unexpected writer');}};
const {prepareGlobalIngestionUpdate}=await import('data:text/javascript;base64,'+Buffer.from(compile(localImports(changedUpdate,updateFile))).toString('base64'));
const {verifyPublicationSchema}=await import(pathToFileURL(path.resolve('src/domain/schema-pin.ts')).href);
const schema=await verifyPublicationSchema({schema_version:'1.1.0',schema_path:'data/schema/1.1.0.json',schema_sha256:'cfe3c8cf165f34faa7aa29fda55245df4ce1bfa47d3b4c8bde15eec6f588d5df'});
const source={id:'peer-SP',uf:'SP',title:'TEST ONLY',issuer:'Peer fixture',official_url:'https://example.org/peer',artifact_url:null,stages:['EF'],components:[],document_type:'test_fixture',normative_parts:[],redistribution:'Test only',status:'test'};
const input={base_publication:'peer-base',target_source_ids:['peer-SP'],raw_artifact:'unused',raw_artifact_sha256:'b'.repeat(64),base_artifact_sha256:'a'.repeat(64),actor_id:'peer',output_directory:'unused'};
const gate=[];
for(const field of ['technical_supersessions','technical_extraction_corrections'])for(const [label,value] of [['absent',undefined],['empty-array',[]],['object',{}],['null',null],['string','pin-required'],['nonempty-array',[{}]]]){
 raw.sources=[{...source,...(label==='absent'?{}:{[field]:value})}];schema.validate('Source',raw.sources[0]);
 let code;try{await prepareGlobalIngestionUpdate(input);}catch(error){code=error.code;}
 assert.equal(code,label==='absent'?'PEER_SQL_ENTRY':'INGESTION_PROVENANCE_REQUIRED');gate.push({field,label,code});
}
// Exercise the real post-writer branch with all earlier SQL reads isolated.
const national={...source,id:'peer-BR',uf:'BR'};raw.sources=[national,source];
const aborter=new AbortController(),abortReason=new Error('peer-post-writer-abort');
globalThis.__followup.pool.connect=async()=>({release(){},query:async(sql)=>{
 queries.push(sql);let rows=[];
 if(sql.includes('SELECT p.id,p.sha256'))rows=[{id:'peer-base',sha256:'c'.repeat(64),metadata:{},schema_version:'1.1.0'}];
 else if(sql==='SELECT payload FROM sources WHERE publication_id=$1 ORDER BY id')rows=[{payload:national},{payload:source}];
 else if(sql.includes('SELECT $1::jsonb=$2::jsonb AS equal'))rows=[{equal:true}];
 else if(sql.includes('AS expected,')&&sql.includes('AS supplied,'))rows=[{expected:1,supplied:1,equal:1}];
 else if(sql.includes('count(*)::int count FROM ingestion_raw_items'))rows=[{count:1}];
 return{rows,rowCount:rows.length};
}});
globalThis.__followup.write=async()=>{writerCalls++;aborter.abort(abortReason);return{manifest:{},sha256:'d'.repeat(64),root:'unused'};};
await assert.rejects(()=>prepareGlobalIngestionUpdate({...input,signal:aborter.signal}),e=>e===abortReason);
assert.equal(writerCalls,1);assert.equal(imports,0);assert.equal(queries.includes('COMMIT'),false);assert.equal(queries.includes('ROLLBACK'),true);
const postWriter={writerCalls,imports,commits:queries.filter(q=>q==='COMMIT').length,rollbacks:queries.filter(q=>q==='ROLLBACK').length};
// Isolate runtime pin storage in memory; exercise the actual guard and canonicalizer.
globalThis.__runtimeFixture='loaded-runtime-bytes';
let changedBridge=sourceBridge.replace('createReadStream,existsSync,readFileSync','createReadStream,existsSync')
 .replace("const CLI='scripts/technical-ingestion-provenance.py';","const readFileSync=()=>Buffer.from(globalThis.__runtimeFixture); const CLI='scripts/technical-ingestion-provenance.py';")
 .replace(/const RUNTIME_FILES=\[[^\n]+;/,"const RUNTIME_FILES=['src/peer-in-memory-runtime-fixture.ts'];")
 .replace(/async function fileHash\(path:string\)\{[^\n]+\}/,"async function fileHash(path:string){return createHash('sha256').update(globalThis.__runtimeFixture).digest('hex');}");
const locatedStart=changedBridge.indexOf('async function located('),locatedEnd=changedBridge.indexOf('async function pinned(',locatedStart);
changedBridge=changedBridge.slice(0,locatedStart)+"async function located(path:string){return path;}\n"+changedBridge.slice(locatedEnd);
changedBridge=localImports(changedBridge,bridgeFile)+'\nexport {runtimePins,runTechnical};\n';
const moduleFile=path.join(evidence,'.followup-module.mjs');await fs.writeFile(moduleFile,compile(changedBridge));
let childPid;
try{
 const {runtimePins,runTechnical}=await import(pathToFileURL(moduleFile).href+'?peer='+Date.now());
 await runtimePins();globalThis.__runtimeFixture='changed-after-module-load';
 await assert.rejects(()=>runtimePins(),e=>e.code==='INGESTION_PROVENANCE_MISMATCH');
 const runtimeGuard={initial:'accepted',changedAfterLoad:'INGESTION_PROVENANCE_MISMATCH',storage:'in-memory; no runtime files mutated'};
 // A child owned solely by this control ignores SIGTERM; verify escalation and wait-for-close.
 const helper=path.join(evidence,'.followup-child.mjs'),marker=path.join(evidence,'.followup-child.pid');
 await fs.writeFile(helper,"#!/usr/bin/env node\nimport fs from 'node:fs';\nprocess.on('SIGTERM',()=>{});\nfs.writeFileSync(process.env.PEER_CHILD_MARKER,String(process.pid));\nsetInterval(()=>{},1000);\n",{mode:0o700});
 const previousPython=process.env.PIPELINE_PYTHON;process.env.PIPELINE_PYTHON=helper;process.env.PEER_CHILD_MARKER=marker;
 try{
  const childAborter=new AbortController(),reason=new Error('peer-child-abort');let settled=false;
  const outcome=runTechnical([],childAborter.signal).then(()=>{settled=true;return{resolved:true};},error=>{settled=true;return{reasonMatched:error===reason};});
  for(let i=0;i<200;i++){try{childPid=Number(await fs.readFile(marker,'utf8'));break;}catch{await new Promise(r=>setTimeout(r,10));}}
  assert.ok(childPid);const started=Date.now();childAborter.abort(reason);
  await new Promise(r=>setTimeout(r,100));assert.equal(settled,false);
  const result=await outcome,elapsedMs=Date.now()-started;assert.equal(result.reasonMatched,true);assert.ok(elapsedMs>=4900&&elapsedMs<10000);
  let alive=true;try{process.kill(childPid,0);}catch(error){if(error.code==='ESRCH')alive=false;else throw error;}assert.equal(alive,false);childPid=undefined;
  console.log(JSON.stringify({scope:'followup-pure-controls; SQL/artifact inputs stubbed; actual schema validation; owned child only',hashes,gate,postWriter,runtimeGuard,childCancellation:{reasonMatched:true,promiseStayedPendingBeforeClose:true,elapsedMs,aliveAfterClose:alive}},null,2));
 }finally{if(previousPython===undefined)delete process.env.PIPELINE_PYTHON;else process.env.PIPELINE_PYTHON=previousPython;delete process.env.PEER_CHILD_MARKER;await fs.rm(helper,{force:true});await fs.rm(marker,{force:true});}
}finally{if(childPid){try{process.kill(childPid,'SIGKILL');}catch{}}await fs.rm(moduleFile,{force:true});}
