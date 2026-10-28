/** Real official-source ingestion → prepared inspection → technical validation → publication/rollback.
 * Controlled API pause and actual worker restart exercise recovery against the same job artifact.
 */
import assert from 'node:assert/strict';
import {randomBytes,randomUUID} from 'node:crypto';
import {spawn} from 'node:child_process';
import {mkdir,writeFile} from 'node:fs/promises';
import {pool} from '../src/db/client';
import {setDefaultPublication} from '../src/domain/publication';
import {assertPreparedNotPublic,assertPublishedVisible} from './qa-prepared-boundary';
const base=process.env.VERIFY_URL || process.env.PUBLIC_URL || 'http://localhost:3000';
const origin=new URL(process.env.PUBLIC_URL || base).origin;
const source=process.env.INGESTION_TEST_SOURCE || 'pe-historia-pernambuco-2026';
const started_at=new Date().toISOString(),token=randomUUID().slice(0,8),password=randomBytes(30).toString('base64url'),email=`qa-ingestion-${token}@example.invalid`;
const checks:{name:string;passed:boolean;detail?:unknown}[]=[];
let account:string|null=null,original:string|null=null,publication:string|null=null,exportJob:string|null=null,jobId:string|null=null;
function pass(name:string,detail?:unknown){checks.push({name,passed:true,detail});console.log(JSON.stringify({event:'ingestion_qa_check',name,...(detail?{detail}:{})}));}
function sleep(ms:number){return new Promise<void>(r=>setTimeout(r,ms));}
async function run(args:string[],input?:string){const p=spawn(args[0],args.slice(1),{stdio:['pipe','pipe','pipe'],env:process.env});p.stdin.end(input);let out='',err='';p.stdout.on('data',(b:Buffer)=>out+=b.toString());p.stderr.on('data',(b:Buffer)=>err=(err+b.toString()).slice(-3000));const code=await new Promise<number|null>((done,reject)=>{p.once('close',done);p.once('error',reject);});assert.equal(code,0,`${args[0]} ${args[1]}: ${err.replaceAll(password,'[redacted]')}`);assert(!out.includes(password));return out;}
async function request(path:string,body?:unknown,cookie?:string,expected=200){const response=await fetch(new URL(path,base),{method:body===undefined?'GET':'POST',headers:{Origin:origin,...(body===undefined?{}:{'Content-Type':'application/json'}),...(cookie?{Cookie:cookie}:{})},...(body===undefined?{}:{body:JSON.stringify(body)}),signal:AbortSignal.timeout(180000)});const json=await response.json();assert.equal(response.status,expected,`${path}: ${JSON.stringify(json)}`);return{response,json};}
async function job(){return(await pool.query('SELECT id,type,status,payload,result,progress,error,attempts FROM jobs WHERE id=$1',[jobId])).rows[0];}
async function candidateCounts(id:string){return(await pool.query('SELECT (SELECT count(*)::int FROM publications WHERE id=$1) AS publications,(SELECT count(*)::int FROM items WHERE publication_id=$1) AS items,(SELECT count(*)::int FROM relations WHERE publication_id=$1) AS relations,(SELECT status FROM publication_visibility WHERE publication_id=$1) AS visibility',[id])).rows[0];}
try{
 original=(await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id;assert(original);
 const created=JSON.parse((await run([process.execPath,'--import','tsx','scripts/admin-create.ts','--email',email,'--role','administrator','--actor-type','automated'],password+'\n')).trim());account=created.id;
 const auth=await request('/api/auth/sign-in/email',{email,password});const cookie=auth.response.headers.getSetCookie().map(v=>v.split(';')[0]).join('; ');assert(cookie);pass('temporary_automated_administrator_logged_in');
 const queued=await request('/api/admin/jobs',{type:'ingest',source,cached_only:true},cookie);jobId=queued.json.data.id;assert(jobId);pass('official_cached_source_enqueued_through_authenticated_api',{job_id:jobId,source});
 let importing=false,previousStage='';
 for(let attempt=0;attempt<3600;attempt++){
  const current=await job();assert(!['failed','succeeded','paused'].includes(current.status),`Job terminou antes da pausa controlada: ${JSON.stringify({status:current.status,error:current.error})}`);
  if(current.progress?.event==='fatal'){
   await request(`/api/admin/jobs/${jobId}/pause`,{},cookie);
   throw new Error(`Pipeline real recusou montar o candidato: ${String(current.progress.error || current.error || 'falha sem diagnóstico')}`);
  }
  const stage=String(current.progress?.stage || current.progress?.event || 'queued');if(stage!==previousStage){console.log(JSON.stringify({event:'ingestion_qa_progress',job_id:jobId,status:current.status,stage}));previousStage=stage;}
  if(stage==='importing_prepared_candidate'){importing=true;publication=current.progress.publication;break;}await sleep(250);
 }
 assert(importing&&publication,'Worker deve atingir importação do candidato específico.');
 await request(`/api/admin/jobs/${jobId}/pause`,{},cookie);pass('real_ingestion_paused_during_prepared_import');
 for(let n=0;n<600;n++){const state=await job();if(state.status==='paused')break;assert.notEqual(state.status,'failed',state.error);await sleep(500);}
 assert.equal((await job()).status,'paused');assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,original);
 const before=await candidateCounts(publication!);assert.equal(before.publications,1);assert.equal(before.visibility,'prepared');assert(before.items>0);pass('private_candidate_persisted_before_job_completion_without_default_change',before);
 const project=process.env.INGESTION_TEST_COMPOSE_PROJECT || 'curriculos-abertos';assert.match(project,/^curriculos-abertos(?:-clean-[a-z0-9-]+)?$/);await run(['docker','compose','-p',project,'restart','worker']);assert.equal((await job()).status,'paused');pass('actual_compose_worker_restart_preserved_paused_job_and_prepared_snapshot');
 await request(`/api/admin/jobs/${jobId}/resume`,{},cookie);
 for(let n=0;n<1200;n++){const current=await job();if(current.status==='succeeded')break;assert.notEqual(current.status,'failed',current.error);await sleep(500);}
 const completed=await job();assert.equal(completed.status,'succeeded');assert.equal(completed.result.publication,publication);assert.equal(completed.result.import_receipt.id,publication);assert.equal(completed.result.import_receipt.already_imported,true);assert.equal(completed.result.actor_type,'automated');assert.match(completed.result.artifact_sha256,/^[a-f0-9]{64}$/);assert.deepEqual(await candidateCounts(publication!),before);pass('resume_reused_same_job_artifact_and_imported_idempotently_without_duplicate_records',{job_id:jobId,publication,attempts:completed.attempts,artifact:completed.result.artifact,sha256:completed.result.artifact_sha256});
 const preview=(await request(`/api/admin/candidates/${encodeURIComponent(publication!)}`,undefined,cookie)).json.data;assert.equal(preview.publication,publication);assert.equal(preview.visibility,'prepared');assert(preview.counts.items>0);assert(preview.sources.some((row:{id:string})=>row.id===source));assert(preview.ingestion_jobs.some((row:{id:string})=>row.id===jobId));
 const realItem=(await pool.query('SELECT id,payload FROM items WHERE publication_id=$1 AND source_id=$2 ORDER BY id LIMIT 1',[publication,source])).rows[0];assert(realItem);const itemResult=(await request(`/api/admin/candidates/${encodeURIComponent(publication!)}/items/${encodeURIComponent(realItem.id)}`,undefined,cookie)).json;assert.equal(itemResult.publication,publication);assert.equal(itemResult.data.text,realItem.payload.text);assert(itemResult.data.evidence.length>0);pass('authenticated_preview_contains_real_official_source_and_learning_evidence');
 exportJob=randomUUID();await pool.query("INSERT INTO jobs(id,type,status,pause_requested,payload) VALUES($1,'export','paused',true,$2::jsonb)",[exportJob,JSON.stringify({query:{publication},format:'json'})]);await assertPreparedNotPublic({base,publication:publication!,itemId:realItem.id,sourceId:source,exportJobId:exportJob});pass('real_ingestion_candidate_hidden_from_public_api_mcp_and_export_cache');
 await request('/api/admin/publications/rollback',{publication,reason:'Verificação: rollback não deve publicar candidato de ingestão preparado.'},cookie,409);await request(`/api/admin/candidates/${encodeURIComponent(publication!)}/publish`,{reason:'Verificação: publicação exige validação técnica anterior.'},cookie,409);pass('prepared_candidate_cannot_publish_through_rollback_or_without_validation');
 const validation=(await request(`/api/admin/candidates/${encodeURIComponent(publication!)}/validate`,{reason:'Validação técnica automatizada de ingestão oficial real e referências.'},cookie)).json.data;assert.equal(validation.valid,true);assert.equal(validation.actor_type,'automated');assert.equal(validation.human_pedagogical_approval,false);pass('candidate_validated_without_fake_transcription_change_or_human_review');
 await request(`/api/admin/candidates/${encodeURIComponent(publication!)}/publish`,{reason:'Publicação temporária explícita para verificar fluxo real de atualização curricular local.'},cookie);assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,publication);await assertPublishedVisible({base,publication:publication!,itemId:realItem.id});pass('ingested_candidate_explicitly_published_through_authenticated_administration');
 await request('/api/admin/publications/rollback',{publication:original,reason:'Retorno ao snapshot anterior após ensaio automatizado de ingestão, preservando histórico.'},cookie);assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,original);await assertPublishedVisible({base,publication:publication!,itemId:realItem.id});pass('rollback_restored_original_default_and_retained_published_history');
 const report={schema_version:1,actor_type:'automated',started_at,completed_at:new Date().toISOString(),source,job_id:jobId,publication,original_default:original,checks,passed:true,national_release_asserted:false,method:'official cached source, real worker/subprocess/import, API pause/restart/resume, private preview, API/MCP boundary, technical validation and explicit publication/rollback'};await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/ingestion-admin-flow.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}catch(error){await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/ingestion-admin-flow.json',JSON.stringify({schema_version:1,actor_type:'automated',started_at,completed_at:new Date().toISOString(),source,job_id:jobId,publication,original_default:original,checks,passed:false,error:error instanceof Error?error.message:String(error)},null,2)+'\n');console.error(error instanceof Error?error.message:String(error));process.exitCode=1;}
finally{
 if(original&&publication&&(await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id===publication)await setDefaultPublication(original,{id:'ingestion-qa-cleanup',actor_type:'automated',reason:'Restauração auditada do default após ensaio local de ingestão.'});
 if(exportJob)await pool.query('DELETE FROM jobs WHERE id=$1',[exportJob]);if(account)await pool.query('DELETE FROM "user" WHERE id=$1',[account]);await pool.end();
}
