import assert from 'node:assert/strict';
import { randomBytes,randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { mkdir,writeFile } from 'node:fs/promises';
import { pool } from '../src/db/client';
import { enqueueJob,claimJob,controlJob,getJob } from '../src/worker/jobs';
const base=process.env.VERIFY_URL || process.env.PUBLIC_URL || 'http://localhost:3000';
const origin=new URL(process.env.PUBLIC_URL || base).origin;
const checks:{name:string;result:'passed';detail?:unknown}[]=[];
function passed(name:string,detail?:unknown){checks.push({name,result:'passed',detail});}
async function request(path:string,body?:unknown,cookie?:string,withOrigin=true){
 const response=await fetch(new URL(path,base),{method:body===undefined?'GET':'POST',headers:{...(body===undefined?{}:{'Content-Type':'application/json'}),...(withOrigin?{Origin:origin}:{}),...(cookie?{Cookie:cookie}:{})},...(body===undefined?{}:{body:JSON.stringify(body)}),redirect:'manual'});
 const json=await response.json();return{response,json};
}
async function createAccount(email:string,password:string,role:string){
 const child=spawn(process.execPath,['--import','tsx','scripts/admin-create.ts','--email',email,'--role',role,'--actor-type','automated'],{stdio:['pipe','pipe','pipe'],env:process.env});
 child.stdin.end(password+'\n');let stdout='',stderr='';child.stdout.on('data',chunk=>{stdout+=chunk.toString();});child.stderr.on('data',chunk=>{stderr+=chunk.toString();});
 const code=await new Promise<number|null>((resolve,reject)=>{child.on('error',reject);child.on('close',resolve);});
 assert.equal(code,0,`CLI criação conta deve terminar com sucesso; ${stderr.replace(password,'[redacted]')}`);
 assert(!stdout.includes(password),'CLI não pode expor a senha.');return JSON.parse(stdout.trim()).id as string;
}
async function login(email:string,password:string){const {response}=await request('/api/auth/sign-in/email',{email,password});assert.equal(response.status,200,'login Better Auth real');const cookies=response.headers.getSetCookie();assert(cookies.length>0,'Cookie de sessão emitido.');return cookies.map(c=>c.split(';')[0]).join('; ');}
async function mutation(path:string,body:unknown,cookie:string){const {response,json}=await request(path,body,cookie);assert.equal(response.status,200,`${path}: ${JSON.stringify(json)}`);return json.data;}
const stamp=randomUUID().slice(0,8);const adminEmail=`qa-${stamp}@example.invalid`,curatorEmail=`qa-curator-${stamp}@example.invalid`;const password=randomBytes(30).toString('base64url');
let adminId:string|null=null,curatorId:string|null=null;let originalPublication:string|null=null;let preparedPublication:string|null=null;
try{
 const current=await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true');originalPublication=current.rows[0]?.publication_id;assert(originalPublication,'Publicação real carregada.');
 const item=(await pool.query('SELECT id,payload FROM items WHERE publication_id=$1 ORDER BY id LIMIT 1',[originalPublication])).rows[0];assert(item,'Corpus real precisa conter aprendizagem.');
 const relation=(await pool.query('SELECT id,payload FROM relations WHERE publication_id=$1 ORDER BY id LIMIT 1',[originalPublication])).rows[0];
 assert.equal((await request('/api/admin/overview')).response.status,401);passed('admin_denies_anonymous');
 assert.equal((await request('/api/metrics')).response.status,401);passed('metrics_denies_anonymous');
 adminId=await createAccount(adminEmail,password,'administrator');curatorId=await createAccount(curatorEmail,password,'curator');passed('cli_creates_unique_accounts_without_password_output');
 const cookie=await login(adminEmail,password);const curatorCookie=await login(curatorEmail,password);passed('better_auth_real_login');
 const overview=await request('/api/admin/overview',undefined,cookie);assert.equal(overview.response.status,200);assert.equal(overview.json.data.actor.actor_type,'automated');passed('actor_type_preserved_automated');
 assert.equal((await request('/api/admin/jobs',{type:'source-check'},cookie,false)).response.status,403);passed('mutations_require_same_origin');
 assert.equal((await request('/api/admin/publications/rollback',{publication:originalPublication,reason:'Ensaio automatizado de autorização.'},curatorCookie)).response.status,403);passed('curator_cannot_publish');
 const protectedJob=randomUUID();await pool.query("INSERT INTO jobs(id,type,status,pause_requested,payload,run_after) VALUES($1,'ingest','paused',true,'{}',now()+interval '1 hour')",[protectedJob]);
 try{for(const action of ['pause','resume','retry'])assert.equal((await request(`/api/admin/jobs/${protectedJob}/${action}`,{},curatorCookie)).response.status,403);passed('curator_cannot_control_ingestion_jobs');}finally{await pool.query('DELETE FROM jobs WHERE id=$1',[protectedJob]);}

 const contribution=await request('/api/v1/contribuicoes',{kind:'error',record_id:item.id,record_url:`/aprendizagens/${encodeURIComponent(item.id)}`,description:'Verificação automatizada de fluxo administrativo, sem alteração do texto curricular.',evidence_url:'https://example.invalid/qa'});
 assert([200,201,202].includes(contribution.response.status),JSON.stringify(contribution.json));
 const contributionData=contribution.json.data || contribution.json;assert(contributionData.id);passed('public_contribution_persisted');
 await mutation(`/api/admin/contributions/${contributionData.id}/decide`,{status:'accepted',reason:'Contribuição de verificação automatizada aceita para ensaio do fluxo.'},cookie);
 const decided=(await pool.query('SELECT status,decided_by FROM contributions WHERE id=$1',[contributionData.id])).rows[0];assert.equal(decided.status,'accepted');assert.equal(decided.decided_by,adminId);passed('authenticated_contribution_decision');
 const draft=await mutation('/api/admin/drafts',{base_publication:originalPublication,title:`Verificação técnica automatizada ${stamp}`},cookie);
 await mutation(`/api/admin/drafts/${draft.id}/changes`,{entity:'item',record_id:item.id,text:item.payload.text,reason:'Ensaio automatizado de revisão de transcrição, mantendo integralmente o texto oficial.'},cookie);
 assert(relation,'Corpus real precisa conter relação para revisão.');
 await mutation(`/api/admin/drafts/${draft.id}/changes`,{entity:'relation',record_id:relation.id,decision:'accept',actor_type:'human',reason:'Ensaio automatizado de decisão de publicação; preserva origem e não afirma homologação pedagógica humana.'},cookie);
 const validation=await mutation(`/api/admin/drafts/${draft.id}/validate`,{},cookie);assert.equal(validation.valid,true);assert.equal(validation.human_pedagogical_approval,false);passed('draft_schema_and_references_validated');
 const prepared=await mutation(`/api/admin/drafts/${draft.id}/prepare`,{reason:'Snapshot técnico de verificação automatizada, com textos oficiais preservados.'},cookie);preparedPublication=prepared.id;assert(prepared.id!==originalPublication);passed('immutable_snapshot_prepared');
 await mutation(`/api/admin/drafts/${draft.id}/publish`,{reason:'Publicação temporária para verificar integração e reversão em ambiente local.'},cookie);
 assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,prepared.id);passed('atomic_default_publication_changed');
 const snapshots=await pool.query('SELECT publication_id,payload FROM items WHERE publication_id=ANY($1::text[]) AND id=$2 ORDER BY publication_id',[[originalPublication,prepared.id],item.id]);assert.equal(snapshots.rows.length,2);for(const row of snapshots.rows)assert.equal(row.payload.text,item.payload.text);passed('original_and_revision_preserve_official_text');
 const reviewed=(await pool.query('SELECT payload FROM relations WHERE publication_id=$1 AND id=$2',[prepared.id,relation.id])).rows[0].payload;assert.equal(reviewed.origin,relation.payload.origin);assert.equal(reviewed.pedagogical_review_status,relation.payload.pedagogical_review_status);assert.equal(reviewed.review_events.at(-1).review_type,'publication');assert.equal(reviewed.review_events.at(-1).actor_type,'automated');passed('relation_origin_and_pedagogical_status_preserved_on_publication_decision');
 await mutation('/api/admin/publications/rollback',{publication:originalPublication,reason:'Retorno à publicação original após ensaio automatizado com histórico preservado.'},cookie);
 assert.equal((await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id,originalPublication);passed('default_rollback_preserves_history');
 const audit=(await pool.query('SELECT actor_type,action FROM audit_events WHERE actor_id=$1',[adminId])).rows;assert(audit.length>=8);assert(audit.every(row=>row.actor_type==='automated'));passed('admin_audit_trail_automated',{events:audit.length});
 const rotatedPassword=randomBytes(30).toString('base64url');
 const reset=spawn(process.execPath,['--import','tsx','scripts/admin-reset.ts','--email',adminEmail],{stdio:['pipe','pipe','pipe'],env:process.env});
 reset.stdin.end(rotatedPassword+'\n');let resetOutput='';reset.stdout.on('data',chunk=>{resetOutput+=chunk.toString();});reset.stderr.on('data',()=>{});
 const resetCode=await new Promise<number|null>((resolve,reject)=>{reset.on('close',resolve);reset.on('error',reject);});assert.equal(resetCode,0);assert(!resetOutput.includes(rotatedPassword));
 assert.equal((await request('/api/admin/overview',undefined,cookie)).response.status,401,'Rotação deve revogar sessão existente.');
 assert.equal((await request('/api/auth/sign-in/email',{email:adminEmail,password})).response.status,401,'Senha antiga não pode autenticar.');
 await login(adminEmail,rotatedPassword);passed('local_password_recovery_revokes_sessions_and_rotates_credentials_without_logging_secret');
 // Queue checks run on real persistent jobs while holding a future run_after so the worker cannot race the assertions.
 const job=await enqueueJob('validate',{draft_id:draft.id},`qa-queue-${stamp}`);await pool.query("UPDATE jobs SET run_after=now()+interval '1 hour' WHERE id=$1",[job.id]);
 await controlJob(job.id,'pause');assert.equal((await getJob(job.id))?.status,'paused');await controlJob(job.id,'resume');await pool.query("UPDATE jobs SET run_after=now()+interval '1 hour' WHERE id=$1",[job.id]);assert.equal((await getJob(job.id))?.status,'queued');passed('persistent_job_pause_resume');
 await pool.query("UPDATE jobs SET status='failed',attempts=max_attempts WHERE id=$1",[job.id]);await controlJob(job.id,'retry');await pool.query("UPDATE jobs SET run_after=now()+interval '1 hour' WHERE id=$1",[job.id]);assert.equal((await getJob(job.id))?.attempts,0);passed('persistent_job_retry_resets_failed_attempts');
 await pool.query("UPDATE jobs SET status='paused',pause_requested=true WHERE id=$1",[job.id]);
 // Lease claim uses a transaction with SKIP LOCKED. Only the explicit verification job is made ready; choose its created_at first.
 const leased=await enqueueJob('validate',{draft_id:draft.id},`qa-lease-${stamp}`);await pool.query("UPDATE jobs SET status='running',lease_owner='dead-verifier',lease_until=now()-interval '1 second',created_at='2000-01-01' WHERE id=$1",[leased.id]);
 const claimed=await claimJob(`verifier-${stamp}`);assert.equal(claimed?.id,leased.id);assert.equal(claimed?.status,'running');assert.equal(claimed?.lease_owner,`verifier-${stamp}`);passed('expired_job_lease_reclaimed');
 await pool.query("UPDATE jobs SET status='paused',pause_requested=true,lease_owner=NULL,lease_until=NULL WHERE id=$1",[leased.id]);
 const report={kind:'admin',at:new Date().toISOString(),base_publication:originalPublication,checks,result:'passed',scope:'HTTP real, Better Auth, CLI stdin, PostgreSQL real; não atesta cobertura nacional, restore ou revisão pedagógica humana.'};
 await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/admin-operations.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}catch(error){
 const message=error instanceof Error?error.message:'Falha de verificação.';
 const report={kind:'admin',at:new Date().toISOString(),base_publication:originalPublication,checks,result:'failed',error:message};
 await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/admin-operations.json',JSON.stringify(report,null,2)+'\n');
 console.error(message);process.exitCode=1;
}finally{
 if(originalPublication&&preparedPublication)await pool.query('UPDATE current_publication SET publication_id=$1 WHERE singleton=true AND publication_id=$2',[originalPublication,preparedPublication]);
 // Revoke test accounts after execution. Audit events retain UUID and actor type, without authentication secrets.
 for(const id of [adminId,curatorId])if(id)await pool.query('DELETE FROM "user" WHERE id=$1',[id]);
 await pool.end();
}
