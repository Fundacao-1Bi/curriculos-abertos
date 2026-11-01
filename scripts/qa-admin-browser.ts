/** Real admin-browser QA. Credentials exist in memory/child env only; no trace, HAR or token state. */
import assert from 'node:assert/strict';
import { randomBytes,randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { chmod,mkdir,readFile,readdir,writeFile,rm } from 'node:fs/promises';
import { resolve,join,relative } from 'node:path';
import { pool } from '../src/db/client';
import { redactAdminBrowser } from './qa-admin-browser-reporter';
import {withQaRun,currentQaRun} from './qa-executor';

const base=process.env.TEST_BASE_URL??process.env.PUBLIC_URL??'http://localhost:3000';
const runId=randomUUID(),privateDir=resolve('var/qa-admin-browser',runId),statePath=join(privateDir,'state.json');
const reportPath=resolve('docs/evidence/admin-browser',runId,'results.json');
const email=`qa-browser-${runId}@example.invalid`,password=randomBytes(32).toString('base64url'),wrongPassword=randomBytes(32).toString('base64url');
const secrets=[password,wrongPassword];
const browserCli=resolve('node_modules/@playwright/test/cli.js');
function browserEnvironment():NodeJS.ProcessEnv {
 const allowed=new Set(['PATH','HOME','USER','LOGNAME','TMPDIR','TMP','TEMP','LANG','TERM','CI','SYSTEMROOT','WINDIR','XDG_CACHE_HOME']);
 return {...Object.fromEntries(Object.entries(process.env).filter(([key,value])=>value!==undefined&&(allowed.has(key)||key.startsWith('PLAYWRIGHT_')||key.startsWith('LC_')))),NODE_ENV:process.env.NODE_ENV??'test'};
}
function safe(value:string){let output=value;for(const secret of secrets)output=output.split(secret).join('[REDACTED]');return redactAdminBrowser(output);}
function run(command:string,args:string[],env:NodeJS.ProcessEnv,input?:string):Promise<{code:number|null;stdout:string;stderr:string}>{
 return new Promise((resolveRun,reject)=>{
  if(!process.argv.includes('--list'))currentQaRun().checkpoint();
  const child=spawn(command,args,{env,stdio:['pipe','pipe','pipe']});if(!process.argv.includes('--list'))currentQaRun().trackChild(child);let stdout='',stderr='';
  child.stdin.on('error',()=>{});child.stdin.end(input??'');
  child.stdout.on('data',(chunk:Buffer)=>{stdout=(stdout+chunk.toString()).slice(-4*1024*1024);});child.stderr.on('data',(chunk:Buffer)=>{stderr=(stderr+chunk.toString()).slice(-4*1024*1024);});
  child.on('error',reject);child.on('close',code=>resolveRun({code,stdout,stderr}));
 });
}
async function files(path:string):Promise<string[]>{const out:string[]=[];for(const entry of await readdir(path,{withFileTypes:true})){const p=join(path,entry.name);if(entry.isDirectory())out.push(...await files(p));else out.push(p);}return out;}
async function main(){
 if(process.argv.includes('--list')){const listed=await run(process.execPath,[browserCli,'test','--config','scripts/qa-admin-browser.config.ts','--list','--reporter','list'],browserEnvironment());process.stdout.write(safe(listed.stdout+listed.stderr));process.exitCode=listed.code===0?0:1;await pool.end();return;}
 try{await withQaRun({kind:'browser',purpose:'Isolated administrative browser QA',requiresDocker:true,project:process.env.QA_COMPOSE_PROJECT,inputs:{base:new URL(base).origin}},async qa=>{
 await qa.assertQaDatabase(statement=>pool.query(statement),process.env.QA_COMPOSE_PROJECT,base);
 qa.reserve({stage:'browser',required_free_bytes:1024**3,reserve_bytes:512*1024**2});
 const privateResource=qa.registerResource({kind:'directory',id:'browser-private-'+runId,path:privateDir,owned:true,disposition:'retain'});
 const stateResource=qa.registerResource({kind:'file',id:'browser-state-'+runId,path:statePath,owned:true,disposition:'disposable'});
 const reportResource=qa.registerResource({kind:'directory',id:'browser-report-'+runId,path:resolve('docs/evidence/admin-browser',runId),owned:true,disposition:'retain'});
 const accountResource=qa.registerResource({kind:'account',id:'browser-account-'+runId,owned:true,disposition:'disposable'});
 process.umask(0o077);
 let stateCreated=false;
 let actorId:string|null=null,publication:string|null=null,item:{id:string;payload:{text:string;source_id:string;evidence:unknown[]}}|undefined;
 const checks:Record<string,unknown>[]=[],report:Record<string,unknown>={kind:'admin-browser',actor_type:'automated',run_id:runId,base,started_at:new Date().toISOString(),checks,trace:'off',video:'off',password_transport:'CLI stdin; browser child memory environment; never saved',result:'failed'};
 let failure:Error|undefined;
 try{
  const ready=await fetch(base+'/api/ready',{signal:AbortSignal.any([AbortSignal.timeout(15_000),qa.signal])});assert.equal(ready.status,200,'Aplicação de produção precisa estar pronta antes do ensaio.');
  const current=await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true');publication=process.env.TEST_PUBLICATION??current.rows[0]?.publication_id;assert.ok(publication,'Publicação real obrigatória.');report.publication=publication;
  const published=await pool.query('SELECT status FROM publication_visibility WHERE publication_id=$1',[publication]);assert.equal(published.rows[0]?.status,'published','Browser QA usa publicação pública fixada.');
  item=(await pool.query("SELECT id,payload FROM items WHERE publication_id=$1 AND kind IN ('habilidade','objetivo_aprendizagem') AND length(text) BETWEEN 1 AND 90000 ORDER BY id LIMIT 1",[publication])).rows[0];assert.ok(item,'Aprendizagem real com redação editável necessária.');report.real_item_id=item.id;
  qa.checkpoint();await mkdir(privateDir,{recursive:true,mode:0o700});qa.markResource(privateResource,'created');await chmod(privateDir,0o700);await mkdir(resolve('docs/evidence/admin-browser',runId),{recursive:true});qa.markResource(reportResource,'created');
  const account=await run(process.execPath,['--import','tsx','scripts/admin-create.ts','--email',email,'--name','QA de navegador automatizada','--role','administrator','--actor-type','automated'],process.env,password+'\n');
  assert.equal(account.code,0,'CLI de criação administrativa falhou: '+safe(account.stderr));assert.ok(!account.stdout.includes(password)&&!account.stderr.includes(password),'CLI não deve emitir senha.');actorId=JSON.parse(account.stdout.trim()).id;assert.ok(actorId);report.actor_id=actorId;qa.markResource(accountResource,'created',{account_uuid:actorId});
  const state={run_id:runId,actor_id:actorId,publication,item:{id:item.id,text:item.payload.text,source_id:item.payload.source_id,evidence:item.payload.evidence}};await writeFile(statePath,JSON.stringify(state),{mode:0o600});qa.markResource(stateResource,'created');stateCreated=true;
  checks.push({name:'temporary_automated_account_created_by_secure_cli',passed:true});
  const result=await run(process.execPath,[browserCli,'test','--config','scripts/qa-admin-browser.config.ts','--trace','off'],{...browserEnvironment(),TEST_BASE_URL:base,QA_ADMIN_RUN_ID:runId,QA_ADMIN_PRIVATE_DIR:privateDir,QA_ADMIN_STATE_FILE:statePath,QA_ADMIN_REPORT_FILE:reportPath,QA_ADMIN_EMAIL:email,QA_ADMIN_PASSWORD:password,QA_ADMIN_WRONG_PASSWORD:wrongPassword});
  await writeFile(join('docs/evidence/admin-browser',runId,'runner.log'),safe(result.stdout+result.stderr),{mode:0o600});
  const browserResults=JSON.parse(await readFile(reportPath,'utf8'));report.browser_results=relative(process.cwd(),reportPath);report.browser_summary=browserResults;
  assert.equal(result.code,0,'Jornadas reais de navegador falharam; veja evidência sanitizada.');assert.equal(browserResults.status,'passed');assert.equal(browserResults.tests.length,2);assert.ok(browserResults.tests.every((t:{status:string})=>t.status==='passed'),'Desktop e mobile devem passar sem skip.');
  checks.push({name:'desktop_and_mobile_real_browser_journeys',passed:true});
  const drafts=await pool.query('SELECT id,base_publication,status,changes,prepared_publication FROM drafts WHERE created_by=$1',[actorId]);assert.equal(drafts.rows.length,1,'Validação de rascunho ocorre uma única vez no desktop.');const draft=drafts.rows[0];assert.equal(draft.base_publication,publication);assert.equal(draft.status,'validated');assert.equal(draft.prepared_publication,null);assert.equal(draft.changes.length,1);assert.equal(draft.changes[0].text,item.payload.text);assert.equal(draft.changes[0].actor_type,'automated');report.draft_id=draft.id;
  const original=(await pool.query('SELECT text FROM items WHERE publication_id=$1 AND id=$2',[publication,item.id])).rows[0];assert.equal(original.text,item.payload.text);
  const audit=await pool.query('SELECT actor_type,action FROM audit_events WHERE actor_id=$1',[actorId]);assert.ok(audit.rows.length>=3);assert.ok(audit.rows.every(row=>row.actor_type==='automated'));assert.ok(audit.rows.some(row=>row.action==='validate_draft'));assert.ok(!audit.rows.some(row=>['publish_default','publish_ingestion_candidate','rollback_default','prepare_publication'].includes(row.action)));
  checks.push({name:'official_text_unchanged_and_draft_validated_once_without_prepare_or_publish',passed:true},{name:'audit_retains_automated_actor',passed:true,events:audit.rows.length});
  const artifacts=await files(resolve('docs/evidence/admin-browser',runId));for(const path of artifacts){const raw=await readFile(path);for(const secret of secrets)assert.ok(!raw.includes(Buffer.from(secret)),'Segredo encontrado em artefato próprio.');assert.ok(!/\.(zip|webm|har)$/i.test(path),'Artefato de autenticação proibido.');}
  for(const path of await files(privateDir))assert.ok(!/\.(zip|webm|har)$/i.test(path),'Trace, vídeo ou HAR não podem registrar autenticação.');
  report.artifacts=artifacts.map(path=>relative(process.cwd(),path));checks.push({name:'no_password_token_trace_har_or_video_artifacts',passed:true});report.result='passed';
 }catch(error){failure=error instanceof Error?error:new Error('Falha de QA administrativa.');report.error=safe(failure.message);}
 finally{
  try{
   if(!actorId){const lookup=await pool.query('SELECT u.id FROM "user" u JOIN admin_roles r ON r.user_id=u.id WHERE u.email=$1 AND r.actor_type=\'automated\'',[email]);actorId=lookup.rows[0]?.id??null;}
   if(actorId){qa.markResource(accountResource,'created',{account_uuid:actorId});await qa.guardCleanup([accountResource],async()=>{const removed=await pool.query('DELETE FROM "user" u WHERE u.id=$1 AND u.email=$2 AND EXISTS(SELECT 1 FROM admin_roles r WHERE r.user_id=u.id AND r.actor_type=\'automated\') RETURNING u.id',[actorId,email]);assert.equal(removed.rowCount,1,'Cleanup deve remover somente a identidade QA criada pelo harness.');const sessions=await pool.query('SELECT count(*)::int AS n FROM session WHERE "userId"=$1',[actorId]);assert.equal(sessions.rows[0].n,0);checks.push({name:'only_owned_temporary_account_removed_and_sessions_revoked',passed:true});qa.markResource(accountResource,'cleaned');});}
  }catch(error){report.cleanup_error=safe(error instanceof Error?error.message:'Falha de cleanup.');report.result='failed';failure??=new Error('Cleanup da conta QA falhou.');}
  if(stateCreated)await qa.guardCleanup([stateResource],async()=>{await rm(statePath,{force:true});qa.markResource(stateResource,'cleaned');});else{qa.updateResource(stateResource,{disposition:'retain',metadata:{not_created:true}});qa.markResource(stateResource,'retained');}report.finished_at=new Date().toISOString();qa.recordReport('admin-browser-verification.json',JSON.parse(safe(JSON.stringify(report))));await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/admin-browser-verification.json',safe(JSON.stringify(report,null,2))+'\n',{mode:0o600});console.log(safe(JSON.stringify(report,null,2)));if(failure)process.exitCode=1;
 }
 });}finally{await pool.end();}
}
if(process.argv.includes('--help'))console.log('Usage: QA_COMPOSE_PROJECT=<isolated project> TEST_BASE_URL=<QA URL> node --import tsx scripts/qa-admin-browser.ts [--list]; DATABASE_URL must target the same curriculos_qa cluster. --list only enumerates Playwright tests.');else await main();
