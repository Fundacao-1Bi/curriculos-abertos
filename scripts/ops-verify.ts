import assert from 'node:assert/strict';
import { randomBytes,randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { mkdir,writeFile } from 'node:fs/promises';
import { pool } from '../src/db/client';
import { setDefaultPublication } from '../src/domain/publication';
import { assertPreparedNotPublic,assertPublishedVisible } from './qa-prepared-boundary';
import { enqueueJob,claimJob,controlJob,getJob } from '../src/worker/jobs';
import {withQaRun,currentQaRun} from './qa-executor';
const base=process.env.VERIFY_URL || process.env.PUBLIC_URL || 'http://localhost:3000';
const origin=new URL(process.env.PUBLIC_URL || base).origin;
const checks:{name:string;result:'passed';detail?:unknown}[]=[];
function passed(name:string,detail?:unknown){checks.push({name,result:'passed',detail});}
async function request(path:string,body?:unknown,cookie?:string,withOrigin=true){
 currentQaRun().checkpoint();
 const response=await fetch(new URL(path,base),{method:body===undefined?'GET':'POST',headers:{...(body===undefined?{}:{'Content-Type':'application/json'}),...(withOrigin?{Origin:origin}:{}),...(cookie?{Cookie:cookie}:{})},...(body===undefined?{}:{body:JSON.stringify(body)}),redirect:'manual',signal:AbortSignal.any([AbortSignal.timeout(180_000),currentQaRun().signal])});
 const json=await response.json();return{response,json};
}
async function createAccount(email:string,password:string,role:string){
 currentQaRun().checkpoint();
 const child=spawn(process.execPath,['--import','tsx','scripts/admin-create.ts','--email',email,'--role',role,'--actor-type','automated'],{stdio:['pipe','pipe','pipe'],env:process.env});
 currentQaRun().trackChild(child);child.stdin.end(password+'\n');let stdout='',stderr='';child.stdout.on('data',chunk=>{stdout+=chunk.toString();});child.stderr.on('data',chunk=>{stderr+=chunk.toString();});
 const code=await new Promise<number|null>((resolve,reject)=>{child.on('error',reject);child.on('close',resolve);});
 assert.equal(code,0,`CLI criação conta deve terminar com sucesso; ${stderr.replace(password,'[redacted]')}`);
 assert(!stdout.includes(password),'CLI não pode expor a senha.');return JSON.parse(stdout.trim()).id as string;
}
async function login(email:string,password:string){const {response}=await request('/api/auth/sign-in/email',{email,password});assert.equal(response.status,200,'login Better Auth real');const cookies=response.headers.getSetCookie();assert(cookies.length>0,'Cookie de sessão emitido.');return cookies.map(c=>c.split(';')[0]).join('; ');}
async function mutation(path:string,body:unknown,cookie:string){const {response,json}=await request(path,body,cookie);assert.equal(response.status,200,`${path}: ${JSON.stringify(json)}`);return json.data;}
const stamp=randomUUID().slice(0,8);const adminEmail=`qa-${stamp}@example.invalid`,curatorEmail=`qa-curator-${stamp}@example.invalid`;const password=randomBytes(30).toString('base64url');
let adminId:string|null=null,curatorId:string|null=null;let originalPublication:string|null=null;let preparedPublication:string|null=null;let preparedExportJob:string|null=null;
async function main(){try{await withQaRun({kind:'admin',purpose:'Real isolated administrative publication and rollback QA',requiresDocker:true,project:process.env.QA_COMPOSE_PROJECT,inputs:{base:new URL(base).origin}},async qa=>{
 const query=(statement:string)=>pool.query(statement);
 await qa.assertQaDatabase(query,process.env.QA_COMPOSE_PROJECT,base);
 const measured=Number((await pool.query('SELECT pg_database_size(current_database()) AS bytes')).rows[0].bytes);
 assert.ok(Number.isSafeInteger(measured)&&measured>0,'Tamanho PostgreSQL obrigatório para QA administrativo.');
 const reserve=2*1024**3;
 qa.reserve({stage:'admin',required_free_bytes:Math.ceil(measured*3.25)+reserve,reserve_bytes:reserve});
 const accounts=new Map<string,string>(),ownedJobs=new Map<string,{resource:string;type:'export'|'validate';payload:Record<string,unknown>}>();
 const pointer=qa.registerResource({kind:'publication-pointer',id:'admin-default-'+stamp,owned:true,disposition:'disposable'});
try{
 const current=await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true');originalPublication=current.rows[0]?.publication_id;assert(originalPublication,'Publicação real carregada.');qa.markResource(pointer,'created');
 const item=(await pool.query('SELECT id,payload FROM items WHERE publication_id=$1 ORDER BY id LIMIT 1',[originalPublication])).rows[0];assert(item,'Corpus real precisa conter aprendizagem.');
 const relation=(await pool.query('SELECT id,payload FROM relations WHERE publication_id=$1 ORDER BY id LIMIT 1',[originalPublication])).rows[0];
 assert.equal((await request('/api/admin/overview')).response.status,401);passed('admin_denies_anonymous');
 assert.equal((await request('/api/metrics')).response.status,401);passed('metrics_denies_anonymous');
 const adminResource=qa.registerResource({kind:'account',id:'admin-account-'+stamp,owned:true,disposition:'disposable'});adminId=await createAccount(adminEmail,password,'administrator');qa.markResource(adminResource,'created',{account_uuid:adminId!});accounts.set(adminId!,adminResource);
 const curatorResource=qa.registerResource({kind:'account',id:'curator-account-'+stamp,owned:true,disposition:'disposable'});curatorId=await createAccount(curatorEmail,password,'curator');qa.markResource(curatorResource,'created',{account_uuid:curatorId!});accounts.set(curatorId!,curatorResource);passed('cli_creates_unique_accounts_without_password_output');
 const cookie=await login(adminEmail,password);const curatorCookie=await login(curatorEmail,password);passed('better_auth_real_login');
 const overview=await request('/api/admin/overview',undefined,cookie);assert.equal(overview.response.status,200);assert.equal(overview.json.data.actor.actor_type,'automated');passed('actor_type_preserved_automated');
 assert.equal((await request('/api/admin/jobs',{type:'source-check'},cookie,false)).response.status,403);passed('mutations_require_same_origin');
 assert.equal((await request('/api/admin/publications/rollback',{publication:originalPublication,reason:'Ensaio automatizado de autorização.'},curatorCookie)).response.status,403);passed('curator_cannot_publish');
 const protectedJob=randomUUID();const protectedResource=qa.registerResource({kind:'job',id:protectedJob,owned:true,disposition:'disposable'});qa.checkpoint();await pool.query("INSERT INTO jobs(id,type,status,pause_requested,payload,run_after) VALUES($1,'ingest','paused',true,'{}',now()+interval '1 hour')",[protectedJob]);qa.markResource(protectedResource,'created');
 try{for(const action of ['pause','resume','retry'])assert.equal((await request(`/api/admin/jobs/${protectedJob}/${action}`,{},curatorCookie)).response.status,403);passed('curator_cannot_control_ingestion_jobs');}finally{await qa.guardCleanup([protectedResource],async()=>{
  const before=(await pool.query('SELECT type,status,pause_requested,payload FROM jobs WHERE id=$1',[protectedJob])).rows;assert.equal(before.length,1,'Owned protected probe is missing; preserve cleanup record');assert.equal(before[0].type,'ingest');assert.equal(before[0].status,'paused');assert.equal(before[0].pause_requested,true);assert.deepEqual(before[0].payload,{});
  const deleted=await pool.query("DELETE FROM jobs WHERE id=$1 AND type='ingest' AND status='paused' AND pause_requested=true AND payload='{}'::jsonb RETURNING id",[protectedJob]);assert.equal(deleted.rowCount,1,'Owned protected probe changed during cleanup; preserve for review');assert.equal(Number((await pool.query('SELECT count(*) AS n FROM jobs WHERE id=$1',[protectedJob])).rows[0].n),0);qa.markResource(protectedResource,'cleaned');
 });}

 const contributionResource=qa.registerResource({kind:'contribution',id:'admin-contribution-'+stamp,owned:true,disposition:'retain'});
 const contribution=await request('/api/v1/contribuicoes',{kind:'error',record_id:item.id,record_url:`/aprendizagens/${encodeURIComponent(item.id)}`,description:'Verificação automatizada de fluxo administrativo, sem alteração do texto curricular.',evidence_url:'https://example.invalid/qa'});
 assert([200,201,202].includes(contribution.response.status),JSON.stringify(contribution.json));
 const contributionData=contribution.json.data || contribution.json;assert(contributionData.id);qa.markResource(contributionResource,'created',{allocated_id:contributionData.id});passed('public_contribution_persisted');
 await mutation(`/api/admin/contributions/${contributionData.id}/decide`,{status:'accepted',reason:'Contribuição de verificação automatizada aceita para ensaio do fluxo.'},cookie);
 const decided=(await pool.query('SELECT status,decided_by FROM contributions WHERE id=$1',[contributionData.id])).rows[0];assert.equal(decided.status,'accepted');assert.equal(decided.decided_by,adminId);passed('authenticated_contribution_decision');
 const draftResource=qa.registerResource({kind:'draft',id:'admin-draft-'+stamp,owned:true,disposition:'retain'});
 const draft=await mutation('/api/admin/drafts',{base_publication:originalPublication,title:`Verificação técnica automatizada ${stamp}`},cookie);
 qa.markResource(draftResource,'created',{allocated_id:draft.id});
 await mutation(`/api/admin/drafts/${draft.id}/changes`,{entity:'item',record_id:item.id,text:item.payload.text,reason:'Ensaio automatizado de revisão de transcrição, mantendo integralmente o texto oficial.'},cookie);
 assert(relation,'Corpus real precisa conter relação para revisão.');
 await mutation(`/api/admin/drafts/${draft.id}/changes`,{entity:'relation',record_id:relation.id,decision:'accept',actor_type:'human',reason:'Ensaio automatizado de decisão de publicação; preserva origem e não afirma homologação pedagógica humana.'},cookie);
 const validation=await mutation(`/api/admin/drafts/${draft.id}/validate`,{},cookie);assert.equal(validation.valid,true);assert.equal(validation.human_pedagogical_approval,false);passed('draft_schema_and_references_validated');
 await qa.assertPublicationLimit(query,1);
 const publicationResource=qa.registerResource({kind:'publication',id:'admin-revision-'+stamp,owned:true,disposition:'retain'});
 const prepared=await mutation(`/api/admin/drafts/${draft.id}/prepare`,{reason:'Snapshot técnico de verificação automatizada, com textos oficiais preservados.'},cookie);preparedPublication=prepared.id;qa.markResource(publicationResource,'created',{allocated_id:prepared.id});assert(prepared.id!==originalPublication);passed('immutable_snapshot_prepared');
 preparedExportJob=randomUUID();const preparedJobResource=qa.registerResource({kind:'job',id:preparedExportJob,owned:true,disposition:'disposable'});qa.checkpoint();
 await pool.query("INSERT INTO jobs(id,type,status,pause_requested,payload) VALUES($1,'export','paused',true,$2::jsonb)",[preparedExportJob,JSON.stringify({query:{publication:prepared.id},format:'json'})]);qa.markResource(preparedJobResource,'created');ownedJobs.set(preparedExportJob,{resource:preparedJobResource,type:'export',payload:{query:{publication:prepared.id},format:'json'}});
 const preparedPrivate=(await pool.query('SELECT v.status,p.item_count FROM publications p JOIN publication_visibility v ON v.publication_id=p.id WHERE p.id=$1',[prepared.id])).rows[0];assert.equal(preparedPrivate?.status,'prepared');assert(preparedPrivate.item_count>0);
 const preparedJob=(await pool.query('SELECT type,status,payload FROM jobs WHERE id=$1',[preparedExportJob])).rows[0];assert.equal(preparedJob.type,'export');assert.equal(preparedJob.status,'paused');assert.equal(preparedJob.payload.query.publication,prepared.id);passed('private_preconditions_exist_before_public_visibility_probes');
 assert.equal((await request('/api/admin/publications/rollback',{publication:prepared.id,reason:'Ensaio automatizado: reversão não pode publicar um candidato preparado.'},cookie)).response.status,409);assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,originalPublication);passed('rollback_cannot_publish_prepared_revision');
 await assertPreparedNotPublic({base,publication:prepared.id,itemId:item.id,sourceId:item.payload.source_id,exportJobId:preparedExportJob});
 passed('prepared_snapshot_and_cached_export_unavailable_to_public_api_and_real_mcp');
 await mutation(`/api/admin/drafts/${draft.id}/publish`,{reason:'Publicação temporária para verificar integração e reversão em ambiente local.'},cookie);
 assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,prepared.id);passed('atomic_default_publication_changed');
 await assertPublishedVisible({base,publication:prepared.id,itemId:item.id});passed('published_revision_visible_to_public_api_and_real_mcp');
 const snapshots=await pool.query('SELECT publication_id,payload FROM items WHERE publication_id=ANY($1::text[]) AND id=$2 ORDER BY publication_id',[[originalPublication,prepared.id],item.id]);assert.equal(snapshots.rows.length,2);for(const row of snapshots.rows)assert.equal(row.payload.text,item.payload.text);passed('original_and_revision_preserve_official_text');
 const reviewed=(await pool.query('SELECT payload FROM relations WHERE publication_id=$1 AND id=$2',[prepared.id,relation.id])).rows[0].payload;assert.equal(reviewed.origin,relation.payload.origin);assert.equal(reviewed.pedagogical_review_status,relation.payload.pedagogical_review_status);assert.equal(reviewed.review_events.at(-1).review_type,'publication');assert.equal(reviewed.review_events.at(-1).actor_type,'automated');passed('relation_origin_and_pedagogical_status_preserved_on_publication_decision');
 await mutation('/api/admin/publications/rollback',{publication:originalPublication,reason:'Retorno à publicação original após ensaio automatizado com histórico preservado.'},cookie);
 assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,originalPublication);passed('default_rollback_preserves_history');
 await assertPublishedVisible({base,publication:prepared.id,itemId:item.id});passed('published_history_remains_public_after_default_rollback');
 const audit=(await pool.query('SELECT actor_type,action FROM audit_events WHERE actor_id=$1',[adminId])).rows;assert(audit.length>=8);assert(audit.every(row=>row.actor_type==='automated'));passed('admin_audit_trail_automated',{events:audit.length});
 const rotatedPassword=randomBytes(30).toString('base64url');
 qa.checkpoint();const reset=spawn(process.execPath,['--import','tsx','scripts/admin-reset.ts','--email',adminEmail],{stdio:['pipe','pipe','pipe'],env:process.env});
 qa.trackChild(reset);reset.stdin.end(rotatedPassword+'\n');let resetOutput='';reset.stdout.on('data',chunk=>{resetOutput+=chunk.toString();});reset.stderr.on('data',()=>{});
 const resetCode=await new Promise<number|null>((resolve,reject)=>{reset.on('close',resolve);reset.on('error',reject);});assert.equal(resetCode,0);assert(!resetOutput.includes(rotatedPassword));
 assert.equal((await request('/api/admin/overview',undefined,cookie)).response.status,401,'Rotação deve revogar sessão existente.');
 assert.equal((await request('/api/auth/sign-in/email',{email:adminEmail,password})).response.status,401,'Senha antiga não pode autenticar.');
 await login(adminEmail,rotatedPassword);passed('local_password_recovery_revokes_sessions_and_rotates_credentials_without_logging_secret');
 // Queue checks run on real persistent jobs while holding a future run_after so the worker cannot race the assertions.
 const queueResource=qa.registerResource({kind:'job',id:'admin-queue-'+stamp,owned:true,disposition:'disposable'});qa.checkpoint();
 const job=await enqueueJob('validate',{draft_id:draft.id},`qa-queue-${stamp}`);qa.markResource(queueResource,'created',{allocated_id:job.id});ownedJobs.set(job.id,{resource:queueResource,type:'validate',payload:{draft_id:draft.id}});await pool.query("UPDATE jobs SET run_after=now()+interval '1 hour' WHERE id=$1",[job.id]);
 await controlJob(job.id,'pause');assert.equal((await getJob(job.id))?.status,'paused');await controlJob(job.id,'resume');await pool.query("UPDATE jobs SET run_after=now()+interval '1 hour' WHERE id=$1",[job.id]);assert.equal((await getJob(job.id))?.status,'queued');passed('persistent_job_pause_resume');
 await pool.query("UPDATE jobs SET status='failed',attempts=max_attempts WHERE id=$1",[job.id]);await controlJob(job.id,'retry');await pool.query("UPDATE jobs SET run_after=now()+interval '1 hour' WHERE id=$1",[job.id]);assert.equal((await getJob(job.id))?.attempts,0);passed('persistent_job_retry_resets_failed_attempts');
 await pool.query("UPDATE jobs SET status='paused',pause_requested=true WHERE id=$1",[job.id]);
 // Lease claim uses a transaction with SKIP LOCKED. Only the explicit verification job is made ready; choose its created_at first.
 const leaseResource=qa.registerResource({kind:'job',id:'admin-lease-'+stamp,owned:true,disposition:'disposable'});qa.checkpoint();
 const leased=await enqueueJob('validate',{draft_id:draft.id},`qa-lease-${stamp}`);qa.markResource(leaseResource,'created',{allocated_id:leased.id});ownedJobs.set(leased.id,{resource:leaseResource,type:'validate',payload:{draft_id:draft.id}});await pool.query("UPDATE jobs SET status='running',lease_owner='dead-verifier',lease_until=now()-interval '1 second',created_at='2000-01-01' WHERE id=$1",[leased.id]);
 const claimed=await claimJob(`verifier-${stamp}`);assert.equal(claimed?.id,leased.id);assert.equal(claimed?.status,'running');assert.equal(claimed?.lease_owner,`verifier-${stamp}`);passed('expired_job_lease_reclaimed');
 await pool.query("UPDATE jobs SET status='paused',pause_requested=true,lease_owner=NULL,lease_until=NULL WHERE id=$1",[leased.id]);
 const report={kind:'admin',at:new Date().toISOString(),base_publication:originalPublication,checks,result:'passed',scope:'HTTP real, Better Auth, CLI stdin, PostgreSQL real; não atesta cobertura nacional, restore ou revisão pedagógica humana.'};
 qa.recordReport('admin-operations.json',report);await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/admin-operations.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}catch(error){
 const message=error instanceof Error?error.message:'Falha de verificação.';
 const report={kind:'admin',at:new Date().toISOString(),base_publication:originalPublication,checks,result:'failed',error:message};
 qa.recordReport('admin-operations.json',report);await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/admin-operations.json',JSON.stringify(report,null,2)+'\n');
 console.error(message);process.exitCode=1;
}finally{
 if(originalPublication)await qa.guardCleanup([pointer],async()=>{if(originalPublication&&preparedPublication){const current=(await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id;if(current===preparedPublication)await setDefaultPublication(originalPublication,{id:'ops-verification-cleanup',actor_type:'automated',reason:'Restauração auditada do default original após ensaio administrativo local.'});}
 qa.markResource(pointer,'cleaned');});
 for(const [id,proof] of ownedJobs)await qa.guardCleanup([proof.resource],async()=>{
  const before=(await pool.query('SELECT type,status,pause_requested,payload FROM jobs WHERE id=$1',[id])).rows;assert.equal(before.length,1,'Owned technical job is missing; preserve cleanup record');assert.equal(before[0].type,proof.type);assert.equal(before[0].status,'paused');assert.equal(before[0].pause_requested,true);assert.deepEqual(before[0].payload,proof.payload,'Technical job ownership payload changed');
  const result=await pool.query("DELETE FROM jobs WHERE id=$1 AND type=$2 AND status='paused' AND pause_requested=true AND payload=$3::jsonb RETURNING id",[id,proof.type,JSON.stringify(proof.payload)]);assert.equal(result.rowCount,1,'Owned technical job changed during cleanup; preserve for review');assert.equal(Number((await pool.query('SELECT count(*) AS n FROM jobs WHERE id=$1',[id])).rows[0].n),0);qa.markResource(proof.resource,'cleaned');
 });
 // Revoke test accounts after execution. Audit events retain UUID and actor type, without authentication secrets.
 for(const id of [adminId,curatorId])if(id){const resource=accounts.get(id);assert.ok(resource);await qa.guardCleanup([resource],async()=>{
  const expectedEmail=id===adminId?adminEmail:curatorEmail,expectedRole=id===adminId?'administrator':'curator';
  const before=(await pool.query('SELECT u.id,u.email,r.actor_type,r.role FROM "user" u JOIN admin_roles r ON r.user_id=u.id WHERE u.id=$1',[id])).rows;assert.equal(before.length,1,'Owned account is missing or role changed; preserve cleanup record');assert.equal(before[0].email,expectedEmail);assert.equal(before[0].actor_type,'automated');assert.equal(before[0].role,expectedRole);
  const deleted=await pool.query(`DELETE FROM "user" u WHERE u.id=$1 AND u.email=$2 AND EXISTS(SELECT 1 FROM admin_roles r WHERE r.user_id=u.id AND r.actor_type='automated' AND r.role=$3) RETURNING u.id`,[id,expectedEmail,expectedRole]);assert.equal(deleted.rowCount,1,'Owned account identity changed; preserve it for review');assert.equal(Number((await pool.query('SELECT count(*) AS n FROM "user" WHERE id=$1',[id])).rows[0].n),0);assert.equal(Number((await pool.query('SELECT count(*) AS n FROM session WHERE "userId"=$1',[id])).rows[0].n),0);qa.markResource(resource,'cleaned');
 });}

}

});}finally{await pool.end();}}
if(process.argv.includes('--help'))console.log('Usage: QA_COMPOSE_PROJECT=<isolated project> VERIFY_URL=<QA URL> node --import tsx scripts/ops-verify.ts --admin; DATABASE_URL must target the same isolated curriculos_qa cluster. The common executor reserves disk and limits full publications before mutations.');else await main();
