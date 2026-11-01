/** Real official-source ingestion → prepared inspection → technical validation → publication/rollback.
 * A job-scoped QA trigger synchronizes the pause with atomic candidate persistence; restart and API resume
 * exercise recovery against the same job artifact without relying on an intermediate progress event.
 */
import assert from 'node:assert/strict';
import {randomBytes,randomUUID} from 'node:crypto';
import {spawn} from 'node:child_process';
import {basename} from 'node:path';
import type {PoolClient} from 'pg';
import {mkdir,writeFile} from 'node:fs/promises';
import {pool} from '../src/db/client';
import {setDefaultPublication} from '../src/domain/publication';
import {assertPreparedNotPublic,assertPublishedVisible} from './qa-prepared-boundary';
import {assertGlobalUpdatePreservation} from './ops-ingestion-preservation';
import {withQaRun,currentQaRun} from './qa-executor';
import {pauseOwnedQaIngestion,type QaIngestionGuardProof} from './qa-executor-job-guard';
const base=process.env.VERIFY_URL || process.env.PUBLIC_URL || 'http://localhost:3000';
const origin=new URL(process.env.PUBLIC_URL || base).origin;
const source=process.env.INGESTION_TEST_SOURCE || 'pe-historia-pernambuco-2026';
const project=process.env.INGESTION_TEST_COMPOSE_PROJECT || process.env.QA_COMPOSE_PROJECT || ''; // A mutating harness must never default to the principal project.
const cachedOnly=process.env.INGESTION_TEST_CACHED_ONLY==='true';
// National-scale global composition + private import takes minutes per stage; bound waits by an explicit deadline.
const stageTimeout=Number(process.env.INGESTION_TEST_TIMEOUT_MS||3_600_000);
const started_at=new Date().toISOString(),token=randomUUID().slice(0,8),password=randomBytes(30).toString('base64url'),email=`qa-ingestion-${token}@example.invalid`;
const checks:{name:string;passed:boolean;detail?:unknown}[]=[];
let account:string|null=null,original:string|null=null,publication:string|null=null,rawPublication:string|null=null,alternatePublication:string|null=null,exportJob:string|null=null,jobId:string|null=null;
const pauseTriggerName=`qa_ingestion_pause_${randomUUID().replaceAll('-','')}`,pauseFunctionName=`qa_ingestion_pause_fn_${randomUUID().replaceAll('-','')}`;
let pauseTriggerInstalled=false,pauseFunctionInstalled=false;
let ingestionRequested=false;
const ingestionEnqueueAbort=new AbortController();
function pass(name:string,detail?:unknown){checks.push({name,passed:true,detail});console.log(JSON.stringify({event:'ingestion_qa_check',name,...(detail?{detail}:{})}));}
function sleep(ms:number){return new Promise<void>(r=>setTimeout(r,ms));}
async function run(args:string[],input?:string){currentQaRun().checkpoint();const p=spawn(args[0],args.slice(1),{stdio:['pipe','pipe','pipe'],env:process.env});currentQaRun().trackChild(p);p.stdin.end(input);let out='',err='';p.stdout.on('data',(b:Buffer)=>out+=b.toString());p.stderr.on('data',(b:Buffer)=>err=(err+b.toString()).slice(-3000));const code=await new Promise<number|null>((done,reject)=>{p.once('close',done);p.once('error',reject);});assert.equal(code,0,`${args[0]} ${args[1]}: ${err.replaceAll(password,'[redacted]')}`);assert(!out.includes(password));return out;}
async function request(path:string,body?:unknown,cookie?:string,expected=200){currentQaRun().checkpoint();const enqueue=path==='/api/admin/jobs'&&!!body&&typeof body==='object'&&'type' in body&&body.type==='ingest';if(enqueue)ingestionRequested=true;const response=await fetch(new URL(path,base),{method:body===undefined?'GET':'POST',headers:{Origin:origin,...(body===undefined?{}:{'Content-Type':'application/json'}),...(cookie?{Cookie:cookie}:{})},...(body===undefined?{}:{body:JSON.stringify(body)}),signal:AbortSignal.any([AbortSignal.timeout(180000),currentQaRun().signal,...(enqueue?[ingestionEnqueueAbort.signal]:[])])});const json=await response.json();assert.equal(response.status,expected,`${path}: ${JSON.stringify(json)}`);return{response,json};}
async function job(){currentQaRun().checkpoint();return(await pool.query('SELECT id,type,status,pause_requested,payload,result,progress,error,attempts FROM jobs WHERE id=$1',[jobId])).rows[0];}
async function armPreparedCandidatePause(){
 assert.match(source,/^[a-zA-Z0-9_.:-]{1,200}$/,'Fonte fora do contrato de identificador.');
 const active=(await pool.query("SELECT count(*)::int AS n FROM jobs WHERE type='ingest' AND status IN ('queued','running') AND payload->>'source'=$1",[source])).rows[0].n;
 assert.equal(active,0,'A sincronização da pausa exige uma QA sem outras ingestões ativas para esta fonte.');
 currentQaRun().registerResource({kind:'database-object',id:pauseFunctionName,owned:true,disposition:'disposable'});currentQaRun().registerResource({kind:'database-object',id:pauseTriggerName,owned:true,disposition:'disposable'});currentQaRun().checkpoint();
 const literal=source.replaceAll("'","''");
 await pool.query(`CREATE FUNCTION ${pauseFunctionName}() RETURNS trigger LANGUAGE plpgsql AS $qa$
 BEGIN
   IF OLD.type='ingest' AND OLD.payload->>'source'='${literal}'
      AND OLD.result IS NULL AND NEW.result IS NOT NULL
      AND NEW.progress->>'stage'='prepared_global_candidate' THEN
     NEW.pause_requested:=true;
   END IF;
   RETURN NEW;
 END;
 $qa$`);pauseFunctionInstalled=true;currentQaRun().markResource(pauseFunctionName,'created');
 await pool.query(`CREATE TRIGGER ${pauseTriggerName} BEFORE UPDATE OF progress ON jobs FOR EACH ROW EXECUTE FUNCTION ${pauseFunctionName}()`);pauseTriggerInstalled=true;currentQaRun().markResource(pauseTriggerName,'created');
}
async function disarmPreparedCandidatePause(){
 const qa=currentQaRun(),ids=[...(pauseTriggerInstalled?[pauseTriggerName]:[]),...(pauseFunctionInstalled?[pauseFunctionName]:[])];if(!ids.length)return;
 await qa.guardCleanup(ids,async()=>{if(pauseTriggerInstalled){await pool.query(`DROP TRIGGER IF EXISTS ${pauseTriggerName} ON jobs`);pauseTriggerInstalled=false;qa.markResource(pauseTriggerName,'cleaned');}
 if(pauseFunctionInstalled){await pool.query(`DROP FUNCTION IF EXISTS ${pauseFunctionName}()`);pauseFunctionInstalled=false;qa.markResource(pauseFunctionName,'cleaned');}});
}
async function candidateCounts(id:string){return(await pool.query('SELECT (SELECT count(*)::int FROM publications WHERE id=$1) AS publications,(SELECT count(*)::int FROM items WHERE publication_id=$1) AS items,(SELECT count(*)::int FROM relations WHERE publication_id=$1) AS relations,(SELECT status FROM publication_visibility WHERE publication_id=$1) AS visibility',[id])).rows[0];}
async function main(){try{await withQaRun({kind:'ingestion',purpose:'Isolated official-source ingestion and publication/rollback QA',requiresDocker:true,project,inputs:{base:new URL(base).origin,source,cached_only:cachedOnly}},async qa=>{
 const query=(statement:string)=>pool.query(statement);
 await qa.assertQaDatabase(query,project,base);
 const guardedCluster=String((await pool.query('SELECT system_identifier::text AS id FROM pg_control_system()')).rows[0].id);
 const measured=Number((await pool.query('SELECT pg_database_size(current_database()) AS bytes')).rows[0].bytes);assert.ok(Number.isSafeInteger(measured)&&measured>0);
 const reserve=2*1024**3;qa.reserve({stage:'ingestion',required_free_bytes:Math.ceil(measured*4.25)+reserve,reserve_bytes:reserve});
 await qa.assertPublicationLimit(query,1);
 const accountResource=qa.registerResource({kind:'account',id:'ingestion-account-'+token,owned:true,disposition:'disposable'});
 const ingestionResource=qa.registerResource({kind:'job',id:'ingestion-request-'+token,owned:true,disposition:'retain'});
 const publicationResource=qa.registerResource({kind:'publication',id:'ingestion-candidate-'+token,owned:true,disposition:'retain'});
 const pointer=qa.registerResource({kind:'publication-pointer',id:'ingestion-default-'+token,owned:true,disposition:'disposable'});
 let exportResource:string|undefined,exportCreated=false;
 let flowFailed=true,containmentWork:Promise<void>|undefined;
 let containmentProof:Pick<QaIngestionGuardProof,'quiesced'|'retention_blocked'|'reason'>|undefined;
 const containOwnedIngestion=()=>containmentWork??=(async()=>{
  ingestionEnqueueAbort.abort();
  const deadline=Date.now()+15_000;
  const bounded=async<T>(promise:Promise<T>,maximumMs:number):Promise<T>=>{
   let timer:NodeJS.Timeout|undefined;
   try{return await Promise.race([promise,new Promise<never>((_,reject)=>{timer=setTimeout(()=>reject(new Error('Ingestion containment deadline reached')),Math.max(1,maximumMs));})]);}
   finally{if(timer)clearTimeout(timer);}
  };
  let client:PoolClient|undefined;
  try{
   if(!ingestionRequested){containmentProof={quiesced:true,retention_blocked:false,reason:'No ingestion request was issued by this run'};return;}
   assert.ok(account,'Ingestion account ownership is unavailable; preserve resources');
   const acquiring=pool.connect();
   try{client=await bounded(acquiring,Math.min(5_000,deadline-Date.now()));}
   catch(error){void acquiring.then(late=>late.release(true),()=>{});throw error;}
   const direct=async(statement:string,params:unknown[]=[])=>{
    const remaining=deadline-Date.now();assert.ok(remaining>0,'Ingestion containment deadline reached');
    return bounded(client!.query(statement,params),Math.min(2_000,remaining));
   };
   await direct("SET statement_timeout='2s'");
   const identity=(await direct('SELECT current_database() AS name,system_identifier::text AS cluster FROM pg_control_system()')).rows[0];
   assert.equal(identity.name,'curriculos_qa');assert.equal(String(identity.cluster),guardedCluster,'Containment connection points at another PostgreSQL cluster');
   let knownJob=jobId;
   while(!knownJob&&Date.now()<deadline){
    const candidates=(await direct("SELECT id FROM jobs WHERE type='ingest' AND payload->'requested_by'->>'id'=$1 AND payload->'requested_by'->>'actor_type'='automated' AND payload->>'source'=$2 ORDER BY created_at LIMIT 2",[account,source])).rows;
    assert.ok(candidates.length<2,'Multiple matching ingestion jobs; ownership is ambiguous');
    if(candidates.length===1){knownJob=String(candidates[0].id);jobId=knownJob;qa.markResource(ingestionResource,'created',{allocated_id:knownJob});break;}
    await sleep(Math.min(250,Math.max(0,deadline-Date.now())));
   }
   assert.ok(knownJob,'Request was issued but no owned job was identified before the deadline; late allocation remains possible');
   const remaining=deadline-Date.now();assert.ok(remaining>0,'Containment deadline reached before ownership confirmation');
   containmentProof=await pauseOwnedQaIngestion({jobId:knownJob,accountId:account,runId:basename(qa.directory),query:direct,timeoutMs:remaining});
  }catch(error){containmentProof={quiesced:false,retention_blocked:true,reason:error instanceof Error?error.message:String(error)};}
  finally{
   client?.release(true);
   containmentProof??={quiesced:false,retention_blocked:true,reason:'Containment did not produce a terminal proof'};
   qa.recordReport('ingestion-capacity-containment.json',{...containmentProof,job_id:jobId,source,deadline_ms:15_000,worker_containers_stopped:false,foreign_jobs_mutated:false,account_preserved:!containmentProof.quiesced});
   qa.updateResource(ingestionResource,{metadata:{guard_quiesced:containmentProof.quiesced,retention_blocked:containmentProof.retention_blocked}});
   if(!containmentProof.quiesced)throw new Error('Owned ingestion did not quiesce; retain account/job and reconcile before continuing');
  }
 })();
 qa.onGuardFailure(containOwnedIngestion);
try{
 const originalRow=(await pool.query('SELECT p.id,p.sha256 FROM current_publication c JOIN publications p ON p.id=c.publication_id WHERE c.singleton=true')).rows[0];original=originalRow?.id;assert(original);qa.markResource(pointer,'created');
 assert.match(project,/^curriculos-abertos-clean-[a-z0-9-]+$/,'Ingestion QA requires an explicitly selected isolated QA project');
 const artifactProof=JSON.parse(await run(['docker','compose','-p',project,'exec','-T','worker','node','-e',`
  const fs=require('fs'),path=require('path'),crypto=require('crypto');
  const id=process.argv[1];let source;
  for(const file of fs.readdirSync('data/manifests').filter(file=>file.endsWith('.json'))){const value=JSON.parse(fs.readFileSync(path.join('data/manifests',file),'utf8'));const sources=Array.isArray(value)?value:value.sources;const found=Array.isArray(sources)?sources.find(row=>row.id===id):null;if(found)source=found;}
  if(!source||typeof source.local_path!=='string'||!/^[a-f0-9]{64}$/.test(source.sha256||''))throw Error('Fonte oficial local com checksum registrado é obrigatória.');
  const root=path.resolve('data/raw'),file=path.resolve(source.local_path);if(!file.startsWith(root+path.sep))throw Error('Artefato fora do cache de fontes.');
  const hash=crypto.createHash('sha256');const input=fs.createReadStream(file);input.on('data',chunk=>hash.update(chunk));input.on('error',error=>{throw error});input.on('end',()=>{const actual=hash.digest('hex');if(actual!==source.sha256)throw Error('SHA do PDF oficial local diverge do manifesto.');console.log(JSON.stringify({source_id:id,path:source.local_path,sha256:actual,bytes:fs.statSync(file).size,network_acquisition_required:false}));});
 `,source]));
 assert.equal(artifactProof.source_id,source);assert.equal(artifactProof.network_acquisition_required,false);pass('official_local_artifact_sha256_verified_inside_worker',artifactProof);
 const created=JSON.parse((await run([process.execPath,'--import','tsx','scripts/admin-create.ts','--email',email,'--role','administrator','--actor-type','automated'],password+'\n')).trim());account=created.id;qa.markResource(accountResource,'created',{account_uuid:account!});
 const auth=await request('/api/auth/sign-in/email',{email,password});const cookie=auth.response.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');assert(cookie);pass('temporary_automated_administrator_logged_in');
 await armPreparedCandidatePause();
 await qa.assertPublicationLimit(query,1);
 const queued=await request('/api/admin/jobs',{type:'ingest',source,cached_only:cachedOnly},cookie);jobId=queued.json.data.id;assert(jobId);qa.markResource(ingestionResource,'created',{allocated_id:jobId!});pass('official_source_enqueued_through_authenticated_api',{job_id:jobId,source,cached_only:cachedOnly,method:cachedOnly?'reuse exact-runtime extraction cache':'parse verified local official artifact in current worker runtime'});
 assert.equal(queued.json.data.payload.base_publication,original);assert.equal(queued.json.data.payload.base_publication_sha256,originalRow.sha256);assert.deepEqual(queued.json.data.payload.target_sources,[source]);pass('ingestion_job_pins_published_base_sha256_and_explicit_target_sources',{base_publication:original,base_publication_sha256:originalRow.sha256,target_source_ids:[source]});
 let importing=false,previousStage='';
 for(const deadline=Date.now()+stageTimeout;Date.now()<deadline;){
  const current=await job();assert.notEqual(current.status,'failed',`Job falhou antes do candidato preparado: ${current.error}`);
  if(current.progress?.event==='fatal'){
   await request(`/api/admin/jobs/${jobId}/pause`,{},cookie);
   throw new Error(`Pipeline real recusou montar o candidato: ${String(current.progress.error || current.error || 'falha sem diagnóstico')}`);
  }
  const stage=String(current.progress?.stage || current.progress?.event || 'queued');if(stage!==previousStage){console.log(JSON.stringify({event:'ingestion_qa_progress',job_id:jobId,status:current.status,stage}));previousStage=stage;}
  if(stage==='prepared_global_candidate'&&current.result?.publication){importing=true;rawPublication=current.result.raw_receipt?.publication;break;}
  assert.notEqual(current.status,'succeeded','O worker concluiu sem persistir o checkpoint privado observado pelo harness.');
  assert.notEqual(current.status,'paused','Job foi pausado fora do checkpoint privado preparado.');
  await sleep(250);
 }
 assert(importing&&rawPublication,'Worker deve persistir o candidato global e o recibo RAW do mesmo job.');
 for(const deadline=Date.now()+stageTimeout;Date.now()<deadline;){const state=await job();if(state.status==='paused')break;assert.notEqual(state.status,'failed',state.error);await sleep(500);}
 const paused=await job();assert.equal(paused.status,'paused');assert.equal(paused.pause_requested,true);pass('real_ingestion_paused_during_prepared_import',{job_id:jobId,stage:paused.progress?.stage,pause_synchronization:'qa_pause_trigger'});assert(paused.result?.publication,paused.error || 'Recibo global privado deve persistir antes da pausa.');publication=paused.result.publication;qa.markResource(publicationResource,'created',{allocated_id:publication!});assert.notEqual(publication,rawPublication);assert.equal(paused.result.raw_receipt.publication,rawPublication);assert.equal(paused.result.update_scope.mode,'base-plus-source-update');assert.equal(paused.result.update_scope.base_publication,original);assert.deepEqual(paused.result.update_scope.target_source_ids,[source]);assert.equal((await pool.query('SELECT count(*)::int n FROM publications WHERE id=$1',[rawPublication])).rows[0].n,0);pass('raw_partial_artifact_never_imported_or_promoted',{raw_publication:rawPublication,global_publication:publication});assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,original);
 const before=await candidateCounts(publication!);assert.equal(before.publications,1);assert.equal(before.visibility,'prepared');assert(before.items>0);pass('private_candidate_persisted_before_job_completion_without_default_change',before);
 await disarmPreparedCandidatePause();
 await run(['docker','compose','-p',project,'restart','worker']);assert.equal((await job()).status,'paused');pass('actual_compose_worker_restart_preserved_paused_job_and_prepared_snapshot');
 await request(`/api/admin/jobs/${jobId}/resume`,{},cookie);
 for(const deadline=Date.now()+stageTimeout;Date.now()<deadline;){const current=await job();if(current.status==='succeeded')break;assert.notEqual(current.status,'failed',current.error);await sleep(500);}
 const completed=await job();assert.equal(completed.status,'succeeded');assert.equal(completed.result.publication,publication);assert.equal(completed.result.import_receipt.id,publication);assert.equal(completed.result.import_receipt.already_imported,true);assert.equal(completed.result.resume_method,'verified_global_provenance_replay');assert.equal(completed.result.actor_type,'automated');assert.match(completed.result.artifact_sha256,/^[a-f0-9]{64}$/);assert.equal(completed.result.artifact_sha256,paused.result.artifact_sha256);assert.equal(completed.result.raw_receipt.artifact_sha256,paused.result.raw_receipt.artifact_sha256);assert.equal(completed.result.base_receipt.artifact_sha256,paused.result.base_receipt.artifact_sha256);assert.deepEqual(completed.payload,paused.payload);assert.deepEqual(await candidateCounts(publication!),before);pass('resume_reused_same_job_artifact_and_imported_idempotently_without_duplicate_records',{job_id:jobId,publication,attempts:completed.attempts,artifact:completed.result.artifact,sha256:completed.result.artifact_sha256});
 const independentPreservation=await assertGlobalUpdatePreservation({basePublication:original,candidatePublication:publication!,targetSourceIds:[source]});pass('independent_sql_proves_full_outside_source_item_relation_and_coverage_preservation',independentPreservation);
 const preview=(await request(`/api/admin/candidates/${encodeURIComponent(publication!)}`,undefined,cookie)).json.data;assert.equal(preview.publication,publication);assert.equal(preview.visibility,'prepared');assert(preview.counts.items>0);assert(preview.sources.some((row:{id:string})=>row.id===source));assert(preview.ingestion_jobs.some((row:{id:string})=>row.id===jobId));
 const realItem=(await pool.query('SELECT id,payload FROM items WHERE publication_id=$1 AND source_id=$2 ORDER BY id LIMIT 1',[publication,source])).rows[0];assert(realItem);const itemResult=(await request(`/api/admin/candidates/${encodeURIComponent(publication!)}/items/${encodeURIComponent(realItem.id)}`,undefined,cookie)).json;assert.equal(itemResult.publication,publication);assert.equal(itemResult.data.text,realItem.payload.text);assert(itemResult.data.evidence.length>0);pass('authenticated_preview_contains_real_official_source_and_learning_evidence');
 exportJob=randomUUID();exportResource=qa.registerResource({kind:'job',id:exportJob,owned:true,disposition:'disposable'});qa.checkpoint();await pool.query("INSERT INTO jobs(id,type,status,pause_requested,payload) VALUES($1,'export','paused',true,$2::jsonb)",[exportJob,JSON.stringify({query:{publication},format:'json'})]);qa.markResource(exportResource,'created');exportCreated=true;await assertPreparedNotPublic({base,publication:publication!,itemId:realItem.id,sourceId:source,exportJobId:exportJob});pass('real_ingestion_candidate_hidden_from_public_api_mcp_and_export_cache');
 await request('/api/admin/publications/rollback',{publication,reason:'Verificação: rollback não deve publicar candidato de ingestão preparado.'},cookie,409);await request(`/api/admin/candidates/${encodeURIComponent(publication!)}/publish`,{reason:'Verificação: publicação exige validação técnica anterior.'},cookie,409);pass('prepared_candidate_cannot_publish_through_rollback_or_without_validation');
 const validation=(await request(`/api/admin/candidates/${encodeURIComponent(publication!)}/validate`,{reason:'Validação técnica automatizada de ingestão oficial real e referências.'},cookie)).json.data;assert.equal(validation.valid,true);assert.equal(validation.actor_type,'automated');assert.equal(validation.human_pedagogical_approval,false);assert.equal(validation.global_update_verified,true);pass('candidate_validated_without_fake_transcription_change_or_human_review');
 alternatePublication=(await pool.query("SELECT p.id FROM publications p JOIN publication_visibility v ON v.publication_id=p.id AND v.status='published' WHERE p.id<>$1 AND p.id<>$2 ORDER BY p.created_at DESC LIMIT 1",[original,publication])).rows[0]?.id;assert(alternatePublication,'O ensaio CAS exige histórico real publicado; execute ops-verify --admin antes desta jornada.');
 await request('/api/admin/publications/rollback',{publication:alternatePublication,reason:'Ensaio automatizado de concorrência: alteração explícita do padrão para histórico real.'},cookie);
 try{const stale=await request(`/api/admin/candidates/${encodeURIComponent(publication!)}/publish`,{reason:'Ensaio automatizado: base desatualizada deve impedir promoção global.'},cookie,409);assert.equal(stale.json.error.code,'STALE_INGESTION_BASE');assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,alternatePublication);assert.equal((await candidateCounts(publication!)).visibility,'prepared');pass('publish_rejects_stale_pinned_base_without_promoting_candidate',{base_publication:original,competing_default:alternatePublication,status:409});}
 finally{await request('/api/admin/publications/rollback',{publication:original,reason:'Retorno à base fixada após ensaio de concorrência, antes da publicação explícita.'},cookie);}
 const published=(await request(`/api/admin/candidates/${encodeURIComponent(publication!)}/publish`,{reason:'Publicação temporária explícita para verificar atualização global delimitada de fonte oficial.'},cookie)).json.data;assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,publication);assert.equal(published.previous_id,original);assert.equal(typeof published.publication_event?.id,'string');const publicationEvent=(await pool.query('SELECT publication_id,previous_id,actor_id,actor_type FROM publication_events WHERE id=$1',[published.publication_event.id])).rows[0];assert.equal(publicationEvent.publication_id,publication);assert.equal(publicationEvent.previous_id,original);assert.equal(publicationEvent.actor_id,account);assert.equal(publicationEvent.actor_type,'automated');await assertPublishedVisible({base,publication:publication!,itemId:realItem.id});pass('ingested_candidate_explicitly_published_through_authenticated_administration',{publication_event_id:published.publication_event.id});
 await request('/api/admin/publications/rollback',{publication:original,reason:'Retorno ao snapshot anterior após ensaio automatizado de ingestão, preservando histórico.'},cookie);assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,original);await assertPublishedVisible({base,publication:publication!,itemId:realItem.id});pass('rollback_restored_original_default_and_retained_published_history');
 const report={schema_version:1,actor_type:'automated',started_at,completed_at:new Date().toISOString(),source,job_id:jobId,publication,raw_publication:rawPublication,original_default:original,artifact_precondition:artifactProof,cached_only:cachedOnly,checks,passed:true,update_scope:{...completed.result.update_scope,publication_event:published.publication_event},independent_sql_proof:independentPreservation,global_update_verified:true,national_release_asserted:false,pause_synchronization:'QA-only BEFORE UPDATE trigger scoped to the selected source; it sets pause_requested atomically when the same job persists its prepared global candidate. The worker restart and API resume remain real.',method:'SHA-verified official local artifact, pinned base/scope, real worker/subprocess/global merge, independent SQL preservation, deterministic private-candidate pause, worker restart/API resume, private preview, API/MCP boundary, technical validation, CAS and explicit publication/rollback'};qa.recordReport('ingestion-admin-flow.json',report);await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/ingestion-admin-flow.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));flowFailed=false;
}catch(error){const report={schema_version:1,actor_type:'automated',started_at,completed_at:new Date().toISOString(),source,job_id:jobId,publication,original_default:original,checks,passed:false,error:error instanceof Error?error.message:String(error)};qa.recordReport('ingestion-admin-flow.json',report);await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/ingestion-admin-flow.json',JSON.stringify(report,null,2)+'\n');console.error(error instanceof Error?error.message:String(error));process.exitCode=1;}
finally{
 qa.stopMonitor();
 if(flowFailed)await containOwnedIngestion().catch(()=>{});
 await qa.waitForGuardHandlers();
 if(containmentProof?.retention_blocked){
  qa.updateResource(accountResource,{disposition:'retain',metadata:{retention_blocked:true,guard_quiesced:false}});qa.markResource(accountResource,'retained');
  throw new Error('Ingestion containment remains unproven; account, job and diagnostic resources retained for explicit reconciliation');
 }
 if(pauseTriggerInstalled||pauseFunctionInstalled)await disarmPreparedCandidatePause().catch(()=>{});
 if(original)await qa.guardCleanup([pointer],async()=>{if(original){const current=(await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id;if((publication&&current===publication)||(alternatePublication&&current===alternatePublication))await setDefaultPublication(original,{id:'ingestion-qa-cleanup',actor_type:'automated',reason:'Restauração auditada do default após ensaio local de ingestão.'});}
 qa.markResource(pointer,'cleaned');});
 if(exportCreated&&exportJob&&exportResource)await qa.guardCleanup([exportResource],async()=>{
  const expected={query:{publication},format:'json'},before=(await pool.query('SELECT type,status,pause_requested,payload FROM jobs WHERE id=$1',[exportJob])).rows;
  assert.equal(before.length,1,'Owned export probe is missing; preserve its cleanup record for review');assert.equal(before[0].type,'export');assert.equal(before[0].status,'paused');assert.equal(before[0].pause_requested,true);assert.deepEqual(before[0].payload,expected,'Export probe ownership payload changed');
  const deleted=await pool.query("DELETE FROM jobs WHERE id=$1 AND type='export' AND status='paused' AND pause_requested=true AND payload=$2::jsonb RETURNING id",[exportJob,JSON.stringify(expected)]);assert.equal(deleted.rowCount,1,'Owned export probe changed during cleanup; preserve for review');
  assert.equal(Number((await pool.query('SELECT count(*) AS n FROM jobs WHERE id=$1',[exportJob])).rows[0].n),0,'Owned export probe remains after deletion');qa.markResource(exportResource!,'cleaned');
 });
 if(account)await qa.guardCleanup([accountResource],async()=>{
  const before=(await pool.query('SELECT u.id,u.email,r.actor_type,r.role FROM "user" u JOIN admin_roles r ON r.user_id=u.id WHERE u.id=$1',[account])).rows;
  assert.equal(before.length,1,'Owned account is missing or role changed; preserve its cleanup record');assert.equal(before[0].email,email);assert.equal(before[0].actor_type,'automated');assert.equal(before[0].role,'administrator');
  const deleted=await pool.query(`DELETE FROM "user" u WHERE u.id=$1 AND u.email=$2 AND EXISTS(SELECT 1 FROM admin_roles r WHERE r.user_id=u.id AND r.actor_type='automated' AND r.role='administrator') RETURNING u.id`,[account,email]);assert.equal(deleted.rowCount,1,'Owned account identity changed; preserve for review');
  assert.equal(Number((await pool.query('SELECT count(*) AS n FROM "user" WHERE id=$1',[account])).rows[0].n),0,'Owned account remains after deletion');assert.equal(Number((await pool.query('SELECT count(*) AS n FROM session WHERE "userId"=$1',[account])).rows[0].n),0,'Owned account sessions remain after deletion');qa.markResource(accountResource,'cleaned');
 });
}

});}finally{await pool.end();}}
if(process.argv.includes('--help'))console.log('Usage: INGESTION_TEST_COMPOSE_PROJECT=<isolated QA project> VERIFY_URL=<QA URL> node --import tsx scripts/qa-ingestion-admin.ts; DATABASE_URL must target that curriculos_qa cluster. Official source artifacts are checked before the bounded ingestion experiment.');else await main();
