/** J09: real HTTP downloads, streaming conversion and complete reimport into an owned disposable QA database. */
import assert from 'node:assert/strict';
import {randomBytes} from 'node:crypto';
import {mkdir,readFile,writeFile,statfs} from 'node:fs/promises';
import {resolve} from 'node:path';
import {spawn} from 'node:child_process';
import pg from 'pg';
import {loadCleanState,isolatedEnvironment,sql,snapshotSql,waitReady,verifyRuntimeImage} from './qa-production';
import {sourceTreeHash} from './release-check';
import {downloadAndHash,validatePublishedJsonFile} from './api-export-stream';
import {canonical,digestValue,openAuditArtifact,inspectAuditArtifact} from './audit-artifact';
import {artifactFootprint,measureDatabaseFootprint,reimportBudget,assertCapacityAvailable} from './qa-capacity';
import {cleanupVerifiedReimport} from './qa-own-cleanup';
import type {CleanState} from './qa-production';
import type {ShardedManifest} from '../src/domain/shards';
import type {Learning,Relation,Source} from '../src/shared/contracts';

type Download={path:string;bytes:number;sha256:string;publication:string;items:number;relations:number;sources:number;job_id:string;created_by_this_run:boolean};
type Task={publication:string;database:string;root:string;downloads:{national:Download;slice:Download};source_tree_sha256:string};
const object=(value:unknown):Record<string,unknown>=>value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};
const physical=new Set(['items','relations','sources','parts','format','storage_format','content_identity','source_content_identity','export_source_content_identity','transcode_provenance','item_count','relation_count','source_count']);
function metadata(value:Record<string,unknown>){return Object.fromEntries(Object.entries(value).filter(([key])=>!physical.has(key)));}
function databaseName(value:string){assert.match(value,/^curriculum_reimport_[a-f0-9]{12}$/,'Nome de banco fora do isolamento J09');return value;}
async function worker(taskPath:string){
 const task=JSON.parse(await readFile(taskPath,'utf8')) as Task;databaseName(task.database);
 assert.equal(task.source_tree_sha256,sourceTreeHash());assert.equal(decodeURIComponent(new URL(process.env.DATABASE_URL!).pathname.slice(1)),task.database);
 const {pool}=await import('../src/db/client');const {migrate}=await import('./migrate');
 const {convertSnapshotFileToShards}=await import('../src/domain/json-snapshot-file');const {importArtifactFile,shardRecords}=await import('../src/domain/shards');
 try{
  assert.equal((await pool.query('SELECT current_database() AS name')).rows[0].name,task.database);await migrate();
  assert.equal((await pool.query('SELECT count(*)::int n FROM publications')).rows[0].n,0,'Reimportação começa com banco vazio');
  const results:Record<string,unknown>={};let nationalManifest:ShardedManifest|undefined;
  for(const scope of ['national','slice'] as const){
   const download=task.downloads[scope],converted=await convertSnapshotFileToShards(download.path,{root:task.root,cacheRoot:resolve(task.root,'shards')});
   const manifest=converted.manifest;assert.equal(manifest.id,download.publication);if(scope==='national'){assert.equal(manifest.id,task.publication);nationalManifest=manifest;}else{assert.notEqual(manifest.id,task.publication);assert.equal(manifest.parent_publication,task.publication);assert.equal(manifest.publication_kind,'filtered_export');assert.equal(manifest.national_release_ready,false);}
   const imported=await importArtifactFile(download.path,{root:task.root,cacheRoot:resolve(task.root,'shards'),streamSnapshot:true,makeDefault:false});assert.equal(imported.already_imported,false);assert.equal(imported.id,manifest.id);
   const stored=(await pool.query('SELECT item_count,source_count,relation_count,payload,storage_format FROM publications WHERE id=$1',[manifest.id])).rows[0];
   assert.equal(stored.storage_format,'relational-v1');assert.equal(stored.item_count,manifest.item_count);assert.equal(stored.source_count,manifest.sources.length);assert.equal(stored.relation_count,manifest.relation_count);assert.equal(digestValue(metadata(stored.payload)),digestValue(metadata(manifest)),'Metadados curriculares/versionais alterados na reimportação');
   const counts={items:0,relations:0,sources:0};
   async function compareRows(table:'items'|'relations'|'sources',batch:(Learning|Relation|Source)[]){
    const rows=(await pool.query(`SELECT id,payload FROM ${table} WHERE publication_id=$1 AND id=ANY($2::text[])`,[manifest.id,batch.map(row=>row.id)])).rows;assert.equal(rows.length,batch.length);const byId=new Map(rows.map(row=>[row.id,row.payload]));for(const row of batch)assert.equal(digestValue(byId.get(row.id)),digestValue(row),`${scope}/${table}/${row.id}: JSONB diverge do download`);counts[table]+=batch.length;
    if(scope==='slice'){const national=(await pool.query(`SELECT id,payload FROM ${table} WHERE publication_id=$1 AND id=ANY($2::text[])`,[task.publication,batch.map(row=>row.id)])).rows;assert.equal(national.length,batch.length,'Todo registro do recorte deve existir na publicação de origem');const originals=new Map(national.map(row=>[row.id,row.payload]));for(const row of batch)assert.equal(digestValue(originals.get(row.id)),digestValue(row),`Recorte alterou ${table}/${row.id}`);}
   }
   for(let offset=0;offset<manifest.sources.length;offset+=100)await compareRows('sources',manifest.sources.slice(offset,offset+100));
   for(const part of manifest.parts){let batch:(Learning|Relation)[]=[];for await(const row of shardRecords(part,converted.root)){batch.push(row);if(batch.length>=50){await compareRows(part.kind,batch);batch=[];}}if(batch.length)await compareRows(part.kind,batch);}
   assert.equal(counts.items,download.items);assert.equal(counts.relations,download.relations);assert.equal(counts.sources,download.sources);
   const coverage=(await pool.query('SELECT payload FROM publication_coverage WHERE publication_id=$1 ORDER BY row_index',[manifest.id])).rows.map(row=>row.payload);assert.equal(digestValue(coverage),digestValue(manifest.coverage),'Cobertura mudou na reimportação');
   const again=await importArtifactFile(download.path,{root:task.root,cacheRoot:resolve(task.root,'shards'),streamSnapshot:true,makeDefault:false});assert.equal(again.already_imported,true);assert.equal((await pool.query('SELECT count(*)::int n FROM current_publication')).rows[0].n,0,'Importação de QA não promove publicação');
   results[scope]={publication:manifest.id,...counts,download_sha256:download.sha256,download_bytes:download.bytes,parts_verified:manifest.parts.length,metadata_verified:true,records_verified:true,reimported:true,idempotent:true,passed:true};
  }
  assert.ok(nationalManifest);
  // Compare national download with the delivered artifact, independently of the export/import implementation.
  const delivered=await openAuditArtifact(task.publication),inspection=await inspectAuditArtifact(delivered);assert.equal(inspection.passed,true);assert.equal(inspection.items,nationalManifest.item_count);assert.equal(inspection.relations,nationalManifest.relation_count);assert.equal(inspection.sources,nationalManifest.sources.length);
  assert.equal(canonical(metadata(delivered.header)),canonical(metadata(nationalManifest)),'Download nacional alterou metadados curriculares/versionais da distribuição');
  for(const source of delivered.header.sources){const actual=(await pool.query('SELECT payload FROM sources WHERE publication_id=$1 AND id=$2',[task.publication,source.id])).rows[0];assert.equal(digestValue(actual?.payload),digestValue(source));}
  for(const kind of ['items','relations'] as const){let batch:(Learning|Relation)[]=[];const compare=async()=>{const rows=(await pool.query(`SELECT id,payload FROM ${kind} WHERE publication_id=$1 AND id=ANY($2::text[])`,[task.publication,batch.map(row=>row.id)])).rows;assert.equal(rows.length,batch.length);const byId=new Map(rows.map(row=>[row.id,row.payload]));for(const row of batch)assert.equal(digestValue(byId.get(row.id)),digestValue(row),`Distribuição/download/reimportação divergem: ${row.id}`);batch=[];};for await(const row of delivered.records(kind)){batch.push(row);if(batch.length>=50)await compare();}if(batch.length)await compare();}
  await writeFile(resolve(task.root,'worker-result.json'),JSON.stringify({...results,delivered:{manifest_sha256:inspection.manifest_sha256,parts_verified:inspection.parts_verified},passed:true},null,2)+'\n',{mode:0o600});
 }finally{await pool.end();}
}
async function runWorker(taskPath:string,databaseUrl:string){return new Promise<void>((done,reject)=>{const child=spawn(process.execPath,['--import','tsx','scripts/qa-reimport.ts','--import-worker',taskPath],{env:{...process.env,DATABASE_URL:databaseUrl,DATABASE_POOL_SIZE:'3'},stdio:['ignore','pipe','pipe']});let tail='';const consume=(chunk:Buffer)=>{tail=(tail+chunk.toString()).slice(-3000);};child.stdout.on('data',consume);child.stderr.on('data',consume);child.once('error',reject);child.once('close',code=>code===0?done():reject(new Error(`Reimport worker exit ${code}: ${tail.replaceAll(databaseUrl,'[private database]')}`)));});}
async function main(){
 const started_at=new Date().toISOString(),code=sourceTreeHash(),checks:{name:string;passed:boolean;detail?:unknown}[]=[];let admin:pg.Client|undefined,created=false,database:string|undefined;let report:Record<string,unknown>={actor_type:'automated',producer:'scripts/qa-reimport.ts',started_at,source_tree_sha256:code,checks,passed:false};let error:Error|undefined;let cleanupState:CleanState|undefined,cleanupRoot:string|undefined,cleanupDownloads:Download[]=[];
 try{
  const state=loadCleanState();assert.equal(state.source_tree_sha256,code,'Instalação limpa precisa corresponder ao código atual');const imageProof=verifyRuntimeImage(state.image);await waitReady(state.base_url);const before=JSON.parse(sql(state,snapshotSql));assert.deepEqual(before,state.snapshot);
  const artifact=await openAuditArtifact(state.publication),footprint=state.capacity?.artifact||await artifactFootprint(artifact);
  const databaseFootprint=measureDatabaseFootprint(state.publication,statement=>sql(state,statement)),capacity=reimportBudget(databaseFootprint,footprint);
  const disk=await statfs('.'),available=assertCapacityAvailable(capacity,{host:disk.bavail*disk.bsize,docker:imageProof.image_files.filesystem_free_bytes});
  report={...report,capacity:{footprint,database:databaseFootprint,budget:capacity,available}};checks.push({name:'orçamento J09 medido antes de criar downloads, exportações ou banco',passed:true,detail:report.capacity});
  const existingExports=new Set(JSON.parse(sql(state,"SELECT coalesce(json_agg(id),'[]'::json) FROM jobs WHERE type='export';")) as string[]);
  const env=isolatedEnvironment(state),root=resolve('var/qa-reimport',randomBytes(6).toString('hex'));await mkdir(root,{recursive:true,mode:0o700});report={...report,publication:state.publication,project:state.project,base:state.base_url,workdir:root};cleanupState=state;cleanupRoot=root;
  const base=state.base_url.replace(/\/$/,'');
  async function request(path:string,init?:RequestInit){const response=await fetch(base+'/api/v1/'+path,{...init,signal:AbortSignal.timeout(120000)});assert.ok(response.ok,`HTTP ${response.status} ${path}`);return response;}
  const ufs=object(await(await request('ufs?publication='+encodeURIComponent(state.publication))).json()).data;assert.ok(Array.isArray(ufs));const uf=databaseFootprint.largest_uf;assert.ok(ufs.map(object).some(row=>row.uf===uf&&Number(row.item_count)>0),'Maior UF medida precisa existir publicamente');
  async function download(scope:'national'|'slice'):Promise<Download>{const body={publication:state.publication,format:'json',...(scope==='slice'?{uf}:{})};const queued=object(await(await request('exportacoes',{method:'POST',headers:{'Content-Type':'application/json',Origin:new URL(base).origin},body:JSON.stringify(body)})).json());assert.equal(queued.publication,state.publication);assert.equal(typeof queued.id,'string');let job:Record<string,unknown>={};for(let attempt=0;attempt<1200;attempt++){job=object(await(await request('exportacoes/'+queued.id)).json());assert.equal(job.publication,state.publication);if(job.status==='succeeded')break;assert.notEqual(job.status,'failed','Exportação real falhou');await new Promise(resolveWait=>setTimeout(resolveWait,500));}assert.equal(job.status,'succeeded','Worker precisa concluir download');const response=await request('exportacoes/'+queued.id+'/arquivo');assert.equal(response.headers.get('x-data-publication'),state.publication);const path=resolve(root,scope+'.json'),saved=await downloadAndHash(response,path);assert.equal(saved.sha256,job.sha256);assert.equal(saved.bytes,job.size);await writeFile(path+'.sha256',saved.sha256+'\n',{mode:0o600});
   // Conversion provides bounded metadata, including the derived slice identity, without parsing a national string.
   const {convertSnapshotFileToShards}=await import('../src/domain/json-snapshot-file');const converted=await convertSnapshotFileToShards(path,{root,cacheRoot:resolve(root,'shards')});const manifest=converted.manifest;
   const validated=await validatePublishedJsonFile(path,{publication:manifest.id,...(scope==='national'?{record_count:Number(job.record_count)}:{})});assert.equal(validated.items,manifest.item_count);assert.equal(validated.relations,manifest.relation_count);if(scope==='slice'){assert.equal(manifest.parent_publication,state.publication);assert.ok(Number(object(manifest.export_manifest).matched_item_count)>0);}
   checks.push({name:'real_http_download_'+scope,passed:true,detail:{job_id:queued.id,publication:manifest.id,sha256:saved.sha256,bytes:saved.bytes,items:validated.items,relations:validated.relations}});return{...saved,publication:manifest.id,items:validated.items,relations:validated.relations,sources:validated.sources,job_id:queued.id as string,created_by_this_run:!existingExports.has(queued.id as string)};}
  const downloads={national:await download('national'),slice:await download('slice')};cleanupDownloads=Object.values(downloads);database=databaseName('curriculum_reimport_'+randomBytes(6).toString('hex'));
  const connection=new URL(`postgresql://curriculos_qa:${env.POSTGRES_PASSWORD}@127.0.0.1:${state.database_port}/curriculos_qa`);admin=new pg.Client({connectionString:connection.toString(),connectionTimeoutMillis:10000});await admin.connect();assert.equal((await admin.query('SELECT current_database() AS name')).rows[0].name,'curriculos_qa');await admin.query(`CREATE DATABASE "${database}"`);created=true;connection.pathname='/'+database;
  const task:Task={publication:state.publication,database,root,downloads,source_tree_sha256:code},taskPath=resolve(root,'task.json');await writeFile(taskPath,JSON.stringify(task),{mode:0o600});await runWorker(taskPath,connection.toString());
  const result=object(JSON.parse(await readFile(resolve(root,'worker-result.json'),'utf8')));assert.equal(result.passed,true);assert.equal(sourceTreeHash(),code,'Código mudou durante J09');assert.deepEqual(JSON.parse(sql(state,snapshotSql)),before,'Reimportação não pode alterar instalação QA em execução');checks.push({name:'complete_records_metadata_relations_and_idempotence_verified_in_owned_disposable_database',passed:true},{name:'running_clean_installation_unchanged',passed:true});report={...report,...result,database,slice_uf:uf,method:'Real HTTP national+UF downloads; streaming parser+shards; all canonical records and curricular/version metadata compared to SQL and delivered artifact; isolated disposable database; no default promotion',passed:true};
 }catch(cause){error=cause instanceof Error?cause:new Error(String(cause));report.error=error.message;report.passed=false;}
 finally{if(created&&admin&&database){try{databaseName(database);await admin.query(`DROP DATABASE "${database}" WITH (FORCE)`);checks.push({name:'only_owned_disposable_database_removed',passed:true});}catch{report.cleanup_error='Não foi possível remover o banco descartável próprio';report.passed=false;}}await admin?.end().catch(()=>{});if(report.passed===true&&cleanupState&&cleanupRoot){try{report.cleanup=await cleanupVerifiedReimport(cleanupState,cleanupRoot,cleanupDownloads);checks.push({name:'somente temporários e exports próprios removidos após prova integral e rechecagem SHA',passed:true});}catch(cause){report.cleanup_error=cause instanceof Error?cause.message:String(cause);report.passed=false;}}else report.failure_artifacts_preserved=true;report.completed_at=new Date().toISOString();await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/reimport.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(error||report.passed!==true)process.exitCode=1;}
}
if(process.argv[2]==='--import-worker'){worker(process.argv[3]).catch(error=>{console.error(error instanceof Error?error.message:String(error));process.exitCode=1;});}else await main();
