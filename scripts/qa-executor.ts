/** Host-side QA admission, ownership and lifecycle. Never collects resources by age. */
import assert from 'node:assert/strict';
import {AsyncLocalStorage} from 'node:async_hooks';
import {createHash,randomUUID} from 'node:crypto';
import {spawnSync,type ChildProcess} from 'node:child_process';
import {existsSync,mkdirSync,openSync,closeSync,fsyncSync,writeFileSync,readFileSync,renameSync,unlinkSync,readdirSync,lstatSync,realpathSync,statfsSync} from 'node:fs';
import {resolve,relative,dirname,isAbsolute,join} from 'node:path';
import {hostname} from 'node:os';
import {fileURLToPath} from 'node:url';
import {sourceTreeHash} from './release-check';

export interface QaProcessIdentity {pid:number;start:string;host:string;}
export interface QaResource {
 kind:string;id:string;owned:boolean;disposition:'retain'|'disposable';path?:string;project?:string;
 metadata?:Record<string,string|number|boolean>;status?:'planned'|'created'|'cleaned'|'retained';
}
export interface QaSnapshot {host_free_bytes:number;docker_free_bytes?:number;projects:{name:string;containers?:string[]}[];test_fixtures?:{kind:'container'|'volume';id:string;name:string}[];}
export interface QaProbes {
 snapshot(requiresDocker:boolean):QaSnapshot;
 inventory(root:string,requiresDocker:boolean):unknown;
 processIdentity(pid:number):QaProcessIdentity|null;
 cleanupGuards(resources:QaResource[]):void;
 containers():DockerContainer[];
 databaseCluster(containerId:string):string;
 runtimeFingerprint(containerId:string):{image_id:string;source_tree_sha256:string};
 sourceFingerprint(root:string):string;
 activeJobs(project:string):{id:string;status:string}[];
}
export interface QaRunOptions {kind:string;purpose:string;owner?:string;requiresDocker?:boolean;project?:string;inputs?:Record<string,string|number|boolean>;}
interface Budget {required_free_bytes:number;reserve_bytes?:number;stage?:string;}
export interface QaCommandOptions {input?:string|Buffer;env?:Record<string,string|undefined>;binary?:boolean;timeout?:number;ownedContainerName?:string;ownedDatabaseOperation?:{container_id:string;project:string;database:string;application_name:string};}
interface RunRecord {
 schema:'curriculos/qa-run-v1';id:string;kind:string;purpose:string;owner:string;root:string;
 created_at:string;updated_at:string;process:QaProcessIdentity;token_sha256:string;
 status:'admitting'|'running'|'passed'|'failed'|'interrupted'|'retained';
 inputs:Record<string,string|number|boolean>;resources:QaResource[];
 budget?:Budget;baseline?:QaSnapshot;last_snapshot?:QaSnapshot;error?:string;
 retention?:{reason:string;review_event:string};reports:string[];children:QaProcessIdentity[];
}
const context=new AsyncLocalStorage<QaRun>();
const cleanupContext=new AsyncLocalStorage<boolean>();
const GiB=1024**3;
const lockName='var/qa-executor.lock.json';
const idPattern=/^qa-[a-z0-9-]+$/;
const now=()=>new Date().toISOString();
const hash=(value:string|Buffer)=>createHash('sha256').update(value).digest('hex');
function cleanError(error:unknown){return String(error instanceof Error?error.message:error).replace(/postgres(?:ql)?:\/\/[^\s"'`]+/gi,'[private database]').replace(/(Bearer\s+)[^\s"']+/gi,'$1[redacted]').slice(0,2000);}
function safeRecord(values:Record<string,string|number|boolean>={}){
 const output:Record<string,string|number|boolean>={};
 for(const[key,value]of Object.entries(values)){
  assert.ok(!/(password|secret|cookie|credential|authorization|access_token|session_token|(^|_)session($|_)|(^|_)token($|_)|database_url|(^|_)env($|_))/i.test(key),'Private configuration cannot enter QA ledger');
  assert.ok(['string','number','boolean'].includes(typeof value),'QA metadata must be scalar');
  if(typeof value==='number')assert.ok(Number.isFinite(value));
  output[key]=typeof value==='string'?cleanError(value):value;
 }
 return output;
}
function command(command:string,args:string[],timeout=20000){
 const result=spawnSync(command,args,{encoding:'utf8',timeout,maxBuffer:16*1024**2});
 assert.equal(result.status,0,`${command} read/check failed: ${cleanError(result.stderr||result.error?.message||'no diagnosis')}`);
 return result.stdout.trim();
}
export function processIdentity(pid:number):QaProcessIdentity|null{
 assert.ok(Number.isSafeInteger(pid)&&pid>0);
 const p=spawnSync('ps',['-p',String(pid),'-o','lstart='],{encoding:'utf8',timeout:5000});
 if(p.status===1&&!p.stdout.trim()&&!p.stderr.trim())return null;
 assert.equal(p.status,0,'Cannot verify QA process identity');assert.ok(p.stdout.trim());
 return{pid,start:p.stdout.trim(),host:hostname()};
}
function sameProcess(a:QaProcessIdentity|null,b:QaProcessIdentity){return !!a&&a.pid===b.pid&&a.start===b.start&&a.host===b.host;}
function watchdogChildren(record:RunRecord,root:string,probe:(pid:number)=>QaProcessIdentity|null){
 const children:QaProcessIdentity[]=[];const directory=join(root,'var/jobs',record.id);
 for(const resource of record.resources)for(const key of ['watchdog_ready_path','watchdog_child_path']){
  const value=resource.metadata?.[key];if(typeof value!=='string')continue;const path=resolve(value);assert.ok(within(directory,path));noSymlinkPath(root,path);
  if(!existsSync(path))continue;const ready=JSON.parse(readFileSync(path,'utf8'));assert.equal(ready.run_id,record.id);
  if(!ready.process){assert.ok(Number.isSafeInteger(ready.child_pid)&&ready.child_pid>0);assert.equal(probe(ready.child_pid),null,'A child exited before identity capture but a live process still occupies its PID');continue;}
  assert.ok(ready.process.pid&&ready.process.start&&ready.process.host);children.push(ready.process);
 }
 return children;
}
function exclusive(path:string,value:unknown){
 const fd=openSync(path,'wx',0o600);try{writeFileSync(fd,JSON.stringify(value,null,2)+'\n');fsyncSync(fd);}finally{closeSync(fd);}
}
function atomic(path:string,value:unknown){
 const temp=path+'.'+randomUUID()+'.tmp';exclusive(temp,value);
 try{renameSync(temp,path);}finally{if(existsSync(temp))unlinkSync(temp);}
}
function within(root:string,path:string){const r=relative(root,path);return !!r&&!r.startsWith('..')&&!isAbsolute(r);}
function pathEntry(path:string){try{return lstatSync(path);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return undefined;throw error;}}
function noSymlinkPath(root:string,path:string){
 assert.ok(within(root,path),'Resource must stay inside workspace');
 let current=root;for(const part of relative(root,path).split('/')){current=join(current,part);assert.ok(!pathEntry(current)?.isSymbolicLink(),'Symlink QA resource refused');}
}
function codeHash(root:string){
 const h=createHash('sha256');
 function walk(path:string){if(!existsSync(path))return;const s=lstatSync(path);if(s.isSymbolicLink())return;
  if(s.isDirectory()){for(const name of readdirSync(path).sort())if(!['node_modules','__pycache__','.git'].includes(name))walk(join(path,name));}
  else if(s.isFile()&&!path.endsWith('.pyc'))h.update(relative(root,path)).update('\0').update(readFileSync(path));
 }
 for(const path of ['src','scripts','pipeline','package.json','package-lock.json','Dockerfile','compose.yaml'])walk(join(root,path));return h.digest('hex');
}
export interface DockerContainer {Id:string;Name:string;State:{Running:boolean};Config:{Labels?:Record<string,string>};Mounts:{Type:string;Name?:string;Source:string;Destination:string}[];NetworkSettings:{Ports?:Record<string,{HostIp:string;HostPort:string}[]|null>};}
function dockerContainers():DockerContainer[]{const ids=command('docker',['ps','-aq']).split(/\s+/).filter(Boolean);assert.ok(ids.length<=500,'Too many containers for bounded QA inspection');return ids.length?JSON.parse(command('docker',['inspect',...ids])):[];}
function defaultSnapshot(requiresDocker:boolean):QaSnapshot{
 const s=statfsSync('.'),result:QaSnapshot={host_free_bytes:s.bavail*s.bsize,projects:[]};
 if(!requiresDocker)return result;
 const containers=dockerContainers(),projects=new Map<string,string[]>();
 for(const c of containers){const name=c.Config.Labels?.['com.docker.compose.project'];if(name?.startsWith('curriculos-abertos-clean-'))projects.set(name,[...(projects.get(name)||[]),c.Id]);}
 result.projects=[...projects].map(([name,containers])=>({name,containers}));
 result.test_fixtures=containers.filter(c=>c.Name.startsWith('/ca-tests-')).map(c=>({kind:'container' as const,id:c.Id,name:c.Name.slice(1)}));
 const fixtureVolumes=command('docker',['volume','ls','-q','--filter','name=ca-tests-data-']).split(/\s+/).filter(Boolean);for(const name of fixtureVolumes)result.test_fixtures.push({kind:'volume',id:name,name});
 const app=containers.find(c=>c.State.Running&&c.Config.Labels?.['com.docker.compose.service']==='app'&&c.Config.Labels?.['com.docker.compose.project']?.startsWith('curriculos-abertos'));
 if(app){const disk=JSON.parse(command('docker',['exec',app.Id,'node','-e',"const fs=require('fs');const d=fs.statfsSync('/app/var');console.log(JSON.stringify({bytes:d.bavail*d.bsize}))"]));result.docker_free_bytes=disk.bytes;}
 else {
  const db=containers.find(c=>c.State.Running&&c.Config.Labels?.['com.docker.compose.service']==='db');
  assert.ok(db,'A running container is required for a read-only measurement of Docker disk; no container will be started');
  const lines=command('docker',['exec',db.Id,'df','-Pk','/var/lib/postgresql/data']).split('\n');result.docker_free_bytes=Number(lines.at(-1)!.trim().split(/\s+/)[3])*1024;
 }
 assert.ok(Number.isSafeInteger(result.docker_free_bytes)&&result.docker_free_bytes!>=0,'Invalid Docker free space measurement');return result;
}
function defaultCleanupGuards(resources:QaResource[]){
 command('ps',['-axo','pid,ppid,state,etime,comm']);const mounts=command('mount',[]),containers=dockerContainers();
 const opened=spawnSync('lsof',['-nP','-Fpn'],{encoding:'utf8',timeout:30000,maxBuffer:32*1024**2});
 assert.equal(opened.status,0,'lsof check failed');assert.equal(opened.stderr.trim(),'','Incomplete lsof check');
 const openPaths=opened.stdout.split('\n').filter(line=>line.startsWith('n')).map(line=>line.slice(1));
 for(const r of resources){
  if(r.path){const path=resolve(r.path);for(const p of openPaths)assert.ok(!(p===path||p.startsWith(path+'/')),'Resource is open; cleanup refused');
   for(const c of containers)for(const m of c.Mounts)if(m.Type==='bind'){const src=m.Source.replace(/^\/host_mnt(?=\/)/,'');assert.ok(!(src===path||within(path,src)||within(src,path)),'Resource is mounted; cleanup refused');}
   assert.ok(!mounts.split('\n').some(line=>line.includes(' on '+path+' ')||line.includes(' on '+path+'/')),'Resource has filesystem mount');
  }
  if(r.kind==='volume')for(const c of containers)assert.ok(!c.Mounts.some(m=>m.Name===r.id),'Volume is referenced by a container');
 }
}
const defaultProbes:QaProbes={snapshot:defaultSnapshot,processIdentity,cleanupGuards:defaultCleanupGuards,containers:dockerContainers,sourceFingerprint:sourceTreeHash,activeJobs(project){
 assert.match(project,/^curriculos-abertos-clean-[a-z0-9-]+$/);const containers=dockerContainers().filter(c=>c.Config.Labels?.['com.docker.compose.project']===project);if(!containers.length)return[];
 const db=containers.find(c=>c.Config.Labels?.['com.docker.compose.service']==='db'&&c.State.Running);assert.ok(db,'Cannot reconcile jobs in an unavailable QA database');
 const text=command('docker',['exec',db.Id,'psql','-U','curriculos_qa','-d','curriculos_qa','-At','-v','ON_ERROR_STOP=1','-c',"SELECT coalesce(json_agg(row_to_json(j)),'[]'::json) FROM (SELECT id,status FROM jobs WHERE status IN ('queued','running'))j"]);return JSON.parse(text);
 },runtimeFingerprint(id){return{image_id:command('docker',['inspect',id,'--format','{{.Image}}']),source_tree_sha256:command('docker',['exec',id,'node','--import','tsx','scripts/release-check.ts','fingerprint'],60000)};},databaseCluster(id){return command('docker',['exec',id,'psql','-U','curriculos_qa','-d','curriculos_qa','-At','-v','ON_ERROR_STOP=1','-c','SELECT system_identifier::text FROM pg_control_system()']);},inventory(root,requiresDocker){
 const script=fileURLToPath(new URL('./ops-resource-inventory.py',import.meta.url));
 const report=JSON.parse(command('python3',[script,'--details'],120000));
 assert.equal(report.root,root,'QA inventory must inspect the same workspace');
 assert.equal(report.processes?.ok,true,'Process inventory failed');assert.equal(report.mounts?.ok,true,'Mount inventory failed');
 if(requiresDocker){assert.equal(report.docker_disk?.ok,true,'Docker inventory failed');assert.equal(report.docker_inventory?.ok,true,'Docker mount inventory failed');}
 return report;
}};

export class QaExecutor {
 readonly root:string;readonly probes:QaProbes;
 constructor(options:{root?:string;probes?:Partial<QaProbes>}={}){this.root=realpathSync(options.root??process.cwd());this.probes={...defaultProbes,...options.probes};}
 private runPath(id:string){assert.match(id,idPattern);const path=join(this.root,'var/jobs',id,'retention.json');noSymlinkPath(this.root,path);return path;}
 private lock(){return join(this.root,lockName);}
 async run<T>(options:QaRunOptions,body:(run:QaRun)=>Promise<T>|T):Promise<T>{
  assert.ok(!context.getStore(),'Nested heavy QA must use the existing context, not acquire a second lock');
  assert.match(options.kind,/^[a-z][a-z0-9-]*$/);assert.ok(options.purpose.trim());
  if(!this.probes.inventory||!this.probes.snapshot)throw Error('QA admission probes missing');
  // A container-local copy of var cannot serialize other host sessions.
  if(existsSync('/.dockerenv')&&this.probes.inventory===defaultProbes.inventory)throw Error('Run heavy QA on the host; a container-local lock cannot protect the workspace');
  noSymlinkPath(this.root,join(this.root,'var/jobs'));mkdirSync(join(this.root,'var/jobs'),{recursive:true,mode:0o700});
  if(existsSync(this.lock())){
   const lease=JSON.parse(readFileSync(this.lock(),'utf8')) as {run_id:string;process:QaProcessIdentity};
   const live=this.probes.processIdentity(lease.process.pid);
   if(!sameProcess(live,lease.process))this.noteInterrupted(lease.run_id,'Owner no longer matches; explicit reconciliation required');
   throw Error(`QA lock held by ${lease.run_id}; ${sameProcess(live,lease.process)?'owner active':'interrupted; reconcile explicitly'}`);
  }
  const id='qa-'+options.kind+'-'+randomUUID(),token=randomUUID(),identity=this.probes.processIdentity(process.pid);assert.ok(identity);
  exclusive(this.lock(),{schema:'curriculos/qa-lock-v1',run_id:id,root:this.root,process:identity,token_sha256:hash(token)});
  let run:QaRun|undefined;
  try{
   const directory=dirname(this.runPath(id));mkdirSync(directory,{mode:0o700});
   const record:RunRecord={schema:'curriculos/qa-run-v1',id,kind:options.kind,purpose:options.purpose,owner:options.owner??'workspace QA operator',root:this.root,created_at:now(),updated_at:now(),process:identity,token_sha256:hash(token),status:'admitting',inputs:{code_sha256:codeHash(this.root),...safeRecord(options.inputs)},resources:[],reports:[],children:[]};
   run=new QaRun(this,record,token,options);run.persist();run.event('registered_before_admission');
   return await context.run(run,async()=>{
    const inventory=this.probes.inventory(this.root,options.requiresDocker!==false);run!.recordReport('inventory',inventory);
    const pending=this.pendingRuns(id);assert.equal(pending.length,0,`Unreconciled QA runs: ${pending.join(', ')}`);
    if(options.kind==='recovery'){
     const backups=this.list().filter(r=>r.id!==id&&r.status==='passed').filter(r=>{
      const previous=JSON.parse(readFileSync(this.runPath(r.id),'utf8')) as RunRecord;
      return previous.resources.some(resource=>resource.kind==='backup'&&resource.status!=='cleaned');
     });assert.equal(backups.length,0,`Review retained QA backups before another full backup: ${backups.map(r=>r.id).join(', ')}`);
    }
    run!.start();
    run!.installSignals();
    try{const result=await body(run!);run!.throwIfAborted();assert.ok(!process.exitCode,'QA reported a nonzero process.exitCode');run!.finish('passed');assert.equal(run!.record.status,'passed','QA did not close its disposable resources');return result;}
    catch(error){await run!.waitForGuardHandlers();if(!['failed','interrupted'].includes(run!.record.status))run!.finish(run!.interrupted?'interrupted':'failed',error);throw error;}
    finally{run!.removeSignals();run!.stopMonitor();}
   });
  }catch(error){if(run&&!['failed','interrupted','passed'].includes(run.record.status))run.finish('failed',error);throw error;}
  finally{
   // Never release the lock while a recorded child is still running.
   if(!run||!run.liveChildren().length){const lease=JSON.parse(readFileSync(this.lock(),'utf8'));if(lease.run_id===id&&lease.token_sha256===hash(token))unlinkSync(this.lock());}
  }
 }
 private pendingRuns(except?:string){
  const root=join(this.root,'var/jobs');return readdirSync(root).filter(id=>idPattern.test(id)&&id!==except).filter(id=>{
   const p=this.runPath(id);if(!existsSync(p))return false;const row=JSON.parse(readFileSync(p,'utf8')) as RunRecord;if(row.schema!=='curriculos/qa-run-v1')return false;
   return !['passed','retained'].includes(row.status)&&(row.status!=='failed'||row.children.length>0||row.resources.some(r=>r.status!=='cleaned'));
  });
 }
 private noteInterrupted(id:string,reason:string){
  const p=this.runPath(id);
  if(!existsSync(p)){
   const lease=JSON.parse(readFileSync(this.lock(),'utf8')) as {run_id:string;root:string;process:QaProcessIdentity;token_sha256:string};
   assert.equal(lease.run_id,id);assert.equal(lease.root,this.root);assert.match(lease.token_sha256,/^[a-f0-9]{64}$/);
   assert.equal(lease.process.host,this.probes.processIdentity(process.pid)?.host,'Cannot verify a lease from another host');
   assert.ok(!sameProcess(this.probes.processIdentity(lease.process.pid),lease.process),'Admission owner is active');
   mkdirSync(dirname(p),{recursive:true,mode:0o700});
   exclusive(p,{schema:'curriculos/qa-run-v1',id,kind:'interrupted-admission',purpose:'Admission interrupted before the initial ledger was persisted; no data disposal authorized',owner:'Recorded lease owner',root:this.root,created_at:now(),updated_at:now(),process:lease.process,token_sha256:lease.token_sha256,status:'interrupted',inputs:{},resources:[],reports:[],children:[],error:reason} satisfies RunRecord);
   exclusive(join(dirname(p),'admission-recovery-'+randomUUID()+'.json'),{at:now(),reason,lease_recovered:true,data_removed:false});
  }
  const record=JSON.parse(readFileSync(p,'utf8')) as RunRecord;
  if(record.schema!=='curriculos/qa-run-v1')throw Error('Unknown lock owner record');
  if(['admitting','running'].includes(record.status)){record.status='interrupted';record.updated_at=now();record.error=reason;atomic(p,record);exclusive(join(dirname(p),'interruption-'+randomUUID()+'.json'),{at:now(),reason});}
 }
 reconcile(input:{runId:string;decision:'retain';reason:string}){
  assert.ok(input.reason.trim().length>=10,'An explicit retention reason is required');assert.equal(input.decision,'retain');
  const p=this.runPath(input.runId);if(!existsSync(p))this.noteInterrupted(input.runId,'Explicit reconciliation of interrupted admission');
  const record=JSON.parse(readFileSync(p,'utf8')) as RunRecord;
  assert.equal(record.schema,'curriculos/qa-run-v1');assert.equal(record.root,this.root);
  assert.equal(record.process.host,this.probes.processIdentity(process.pid)?.host,'Cannot reconcile a run owned by another host');
  assert.ok(!sameProcess(this.probes.processIdentity(record.process.pid),record.process),'Owner is still active');
  for(const child of [...record.children,...watchdogChildren(record,this.root,this.probes.processIdentity)])assert.ok(!sameProcess(this.probes.processIdentity(child.pid),child),'Owned child is still active');
  if(typeof record.inputs.project==='string'&&record.inputs.project.startsWith('curriculos-abertos-clean-'))assert.equal(this.probes.activeJobs(record.inputs.project).length,0,'QA jobs are queued/running; reconcile their work before releasing the lease');
  // Serialize two operators reviewing the same dead lease. A crash during this
  // short review leaves evidence and blocks another review; it never deletes data.
  const reviewLock=join(dirname(p),'reconciliation.lock.json'),reviewOwner=randomUUID();
  exclusive(reviewLock,{owner:reviewOwner,process:this.probes.processIdentity(process.pid),at:now()});
  try{
  const lease=existsSync(this.lock())?JSON.parse(readFileSync(this.lock(),'utf8')):undefined;
  if(lease)assert.equal(lease.run_id,record.id,'Another run owns the workspace lock');
  this.probes.cleanupGuards(record.resources.filter(r=>r.path&&r.status!=='cleaned'));
  record.status='retained';record.retention={reason:input.reason,review_event:'Before reuse or disposal of retained resources'};record.updated_at=now();
  atomic(p,record);exclusive(join(dirname(p),'reconciliation-'+randomUUID()+'.json'),{at:now(),decision:input.decision,reason:input.reason,resources_preserved:true});
  if(lease){const current=JSON.parse(readFileSync(this.lock(),'utf8'));assert.equal(current.run_id,record.id);assert.equal(current.token_sha256,record.token_sha256);unlinkSync(this.lock());}
  }finally{const review=JSON.parse(readFileSync(reviewLock,'utf8'));if(review.owner===reviewOwner)unlinkSync(reviewLock);}
 }
 list(){const root=join(this.root,'var/jobs');if(!existsSync(root))return[];const rows=readdirSync(root).filter(id=>idPattern.test(id)&&existsSync(this.runPath(id))).map(id=>JSON.parse(readFileSync(this.runPath(id),'utf8')) as RunRecord).filter(r=>r.schema==='curriculos/qa-run-v1').map(r=>({id:r.id,status:r.status as string,kind:r.kind,resources:r.resources.length,retention:r.retention}));if(existsSync(this.lock())){const lease=JSON.parse(readFileSync(this.lock(),'utf8'));if(!rows.some(r=>r.id===lease.run_id))rows.push({id:lease.run_id,status:'orphaned-admission',kind:'interrupted-admission',resources:0,retention:undefined});}return rows;}
}

export class QaRun {
 readonly directory:string;interrupted=false;private violation?:Error;private monitor?:NodeJS.Timeout;private checking=false;private guardHandlers:(()=>Promise<void>|void)[]=[];private guardWork:Promise<void>[]=[];
 private readonly abortController=new AbortController();
 private signalHandlers?:{SIGINT:()=>void;SIGTERM:()=>void};
 constructor(readonly executor:QaExecutor,readonly record:RunRecord,private token:string,private options:QaRunOptions){this.directory=dirname(join(executor.root,'var/jobs',record.id,'retention.json'));}
 persist(){this.record.updated_at=now();atomic(join(this.directory,'retention.json'),this.record);}
 event(name:string,detail:unknown={}){exclusive(join(this.directory,'event-'+Date.now()+'-'+randomUUID()+'.json'),{at:now(),event:name,detail});}
 start(){this.record.status='running';this.persist();}
 installSignals(){this.signalHandlers={SIGINT:()=>this.interrupt('SIGINT'),SIGTERM:()=>this.interrupt('SIGTERM')};for(const signal of ['SIGINT','SIGTERM'] as const)process.on(signal,this.signalHandlers[signal]);}
 removeSignals(){if(this.signalHandlers)for(const signal of ['SIGINT','SIGTERM'] as const)process.off(signal,this.signalHandlers[signal]);}
 setInputs(values:Record<string,string|number|boolean>){Object.assign(this.record.inputs,safeRecord(values));this.persist();}
 reserve(plan:Budget,dockerAvailableBytes?:number){
  assert.ok(Number.isSafeInteger(plan.required_free_bytes)&&plan.required_free_bytes>=0);const reserve=plan.reserve_bytes??Math.min(plan.required_free_bytes,2*GiB);
  assert.ok(Number.isSafeInteger(reserve)&&reserve>=0&&reserve<=plan.required_free_bytes);
  assert.ok(!this.record.resources.some(r=>r.status==='created'),'Set budget before allocating resources');
  const snap=this.executor.probes.snapshot(this.options.requiresDocker!==false);
  this.validateSnapshot(snap);
  const available=Math.min(snap.host_free_bytes,snap.docker_free_bytes??Infinity,dockerAvailableBytes??Infinity);
  assert.ok(available>=plan.required_free_bytes,`QA capacity insufficient: requires ${plan.required_free_bytes}, available ${available}`);
  this.record.budget={...plan,reserve_bytes:reserve};this.record.baseline=snap;this.record.last_snapshot=snap;this.persist();this.event('capacity_reserved',{plan:this.record.budget,available});
  if(!this.monitor){this.monitor=setInterval(()=>{try{this.checkpoint();}catch(error){this.tripGuard(error);}},5000);this.monitor.unref();}
 }
 checkpoint(){
  this.throwIfAborted();assert.ok(this.record.budget,'Reserve capacity before allocating QA resources');
  if(this.checking)return;this.checking=true;
  try{
   const snap=this.executor.probes.snapshot(this.options.requiresDocker!==false),budget=this.record.budget,baseline=this.record.baseline!;this.validateSnapshot(snap);
   const free=Math.min(snap.host_free_bytes,snap.docker_free_bytes??Infinity);assert.ok(free>=budget.reserve_bytes!,'QA safety reserve reached');
   const growth=Math.max(0,baseline.host_free_bytes-snap.host_free_bytes,(baseline.docker_free_bytes??Infinity)-(snap.docker_free_bytes??Infinity)||0);
   assert.ok(growth<=budget.required_free_bytes-budget.reserve_bytes!,'QA growth budget exceeded');
   const max=this.record.kind==='production'?0:1;
   if(this.record.kind==='production')assert.ok(snap.projects.every(p=>p.name===this.options.project||this.record.resources.some(r=>r.kind==='compose-project'&&r.id===p.name)),'An integration QA already exists; retire/classify it before creating another');
   else assert.ok(snap.projects.length<=max,'Too many QA projects; consolidate before allocating');
   if(this.record.kind==='tests')assert.ok((snap.test_fixtures??[]).every(f=>this.record.resources.some(r=>r.kind===f.kind&&r.owned&&(r.id===f.name||r.id===f.id))),'A retained test fixture already exists; resolve it before creating another');
   this.record.last_snapshot=snap;
  }catch(error){this.tripGuard(error);throw error;}finally{this.checking=false;}
 }
 private validateSnapshot(snap:QaSnapshot){
  assert.ok(Number.isSafeInteger(snap.host_free_bytes)&&snap.host_free_bytes>=0,'Invalid host free space');
  if(this.options.requiresDocker!==false)assert.ok(Number.isSafeInteger(snap.docker_free_bytes)&&snap.docker_free_bytes!>=0,'Docker capacity was not measured');
  if(snap.docker_free_bytes!==undefined)assert.ok(Number.isSafeInteger(snap.docker_free_bytes)&&snap.docker_free_bytes>=0,'Invalid Docker free space');
 }
 throwIfAborted(){if(this.violation)throw this.violation;if(this.interrupted)throw Error('QA interrupted; owned resources retained for review');}
 get signal(){return this.abortController.signal;}
 onGuardFailure(handler:()=>Promise<void>|void){this.guardHandlers.push(handler);if(this.violation)this.guardWork.push(this.runGuardHandler(handler));}
 private runGuardHandler(handler:()=>Promise<void>|void){return cleanupContext.run(true,async()=>{try{await handler();this.event('guard_handler_completed');}catch(cause){this.event('guard_handler_failed',{error:cleanError(cause)});}});}
 private tripGuard(error:unknown){
  if(this.violation)return;this.violation=error instanceof Error?error:new Error(String(error));this.abortController.abort(this.violation);this.event('capacity_guard_failed',{error:cleanError(error)});this.stopMonitor();
  for(const child of this.record.children)if(sameProcess(this.executor.probes.processIdentity(child.pid),child))process.kill(child.pid,'SIGTERM');
  for(const handler of this.guardHandlers)this.guardWork.push(this.runGuardHandler(handler));
 }
 async waitForGuardHandlers(){await Promise.all(this.guardWork);}
 registerResource(resource:QaResource){
  if(!cleanupContext.getStore())this.checkpoint();
  assert.match(resource.kind,/^[a-z][a-z0-9-]*$/);assert.ok(resource.id&&resource.id.length<=500);assert.ok(!this.record.resources.some(r=>r.id===resource.id),'QA resource ID already registered');
  assert.ok(resource.owned||resource.disposition==='retain','Preexisting resources must be retained');
  const row:QaResource={...resource,metadata:safeRecord(resource.metadata),status:'planned'};
  if(row.path){row.path=resolve(this.executor.root,row.path);noSymlinkPath(this.executor.root,row.path);
   if(row.disposition==='disposable'){
    assert.ok(within(join(this.executor.root,'var'),row.path),'Only private var paths can be disposable');
    for(const protectedRoot of ['var/backups','var/runtime-images','var/private-evidence'])assert.ok(!(row.path===join(this.executor.root,protectedRoot)||within(join(this.executor.root,protectedRoot),row.path)),'Protected path cannot be disposable');
   }
   if(row.owned)assert.ok(!pathEntry(row.path),'Existing path cannot be claimed by this run');
  }
  this.record.resources.push(row);this.persist();this.event('resource_intent',{id:row.id,kind:row.kind});return row.id;
 }
 markResource(id:string,status:'created'|'cleaned'|'retained',metadata?:Record<string,string|number|boolean>){const r=this.record.resources.find(r=>r.id===id);assert.ok(r,'QA resource not registered');r.status=status;Object.assign(r.metadata??={},safeRecord(metadata));this.persist();this.event('resource_'+status,{id});}
 updateResource(id:string,update:{metadata?:Record<string,string|number|boolean>;disposition?:'retain'|'disposable'}){const r=this.record.resources.find(r=>r.id===id);assert.ok(r);if(update.disposition){assert.ok(r.owned||update.disposition==='retain');assert.ok(update.disposition!=='disposable'||r.disposition==='disposable','Cannot make retained resources disposable');r.disposition=update.disposition;}Object.assign(r.metadata??={},safeRecord(update.metadata));this.persist();}
 recordReport(name:string,value:unknown){assert.match(name,/^[a-zA-Z0-9_.-]+$/);const filename=name.endsWith('.json')?name:name+'.json';exclusive(join(this.directory,filename),value);this.record.reports.push(filename);this.persist();return join(this.directory,filename);}
 async guardCleanup<T>(ids:string[],action:()=>Promise<T>|T):Promise<T>{
  assert.ok(ids.length);const resources=ids.map(id=>{const r=this.record.resources.find(r=>r.id===id);assert.ok(r&&r.owned&&r.disposition==='disposable'&&r.status==='created','Cleanup requires a created, owned, disposable resource');if(r.path)noSymlinkPath(this.executor.root,r.path);return r;});
  this.executor.probes.cleanupGuards(resources);this.event('cleanup_verified',{ids});
  try{const result=await cleanupContext.run(true,action);for(const r of resources)this.markResource(r.id,'cleaned');return result;}
  catch(error){this.event('cleanup_failed',{ids,error:cleanError(error)});throw error;}
 }
 childEnvironment():NodeJS.ProcessEnv{return{...process.env,QA_EXECUTOR_RUN_ID:this.record.id,QA_EXECUTOR_TOKEN:this.token,QA_EXECUTOR_ROOT:this.executor.root,QA_EXECUTOR_PARENT_PID:String(process.pid)};}
 commandSync(executable:string,args:string[],options:QaCommandOptions={}):string|Buffer{
  this.checkpoint();const id='command-'+randomUUID(),control=join(this.directory,id+'.control.json'),event=join(this.directory,id+'.result.json'),ready=join(this.directory,id+'.ready.json'),child=join(this.directory,id+'.child.json');
  const processResource=this.registerResource({kind:'process',id,owned:true,disposition:'disposable',metadata:{watchdog_ready_path:ready,watchdog_child_path:child}});
  const budget=this.record.budget!,baseline=this.record.baseline!,containers=this.options.requiresDocker===false?[]:this.executor.probes.containers();
  const probe=containers.find(c=>c.State.Running&&c.Config.Labels?.['com.docker.compose.service']==='app');
  if(this.options.requiresDocker!==false)assert.ok(probe,'A running app is required for the independent Docker capacity monitor');
  if(options.ownedContainerName)assert.ok(this.record.resources.some(r=>r.kind==='container'&&r.id===options.ownedContainerName&&r.owned&&r.disposition==='disposable'),'One-off container must be registered before monitored launch');
  if(options.ownedDatabaseOperation)assert.ok(this.record.resources.some(r=>r.kind==='database'&&r.id===options.ownedDatabaseOperation!.database&&r.owned&&r.status==='created'&&r.project===options.ownedDatabaseOperation!.project),'Backend cancellation requires a created owned database');
  const commandControl={root:this.executor.root,run_id:this.record.id,parent:this.record.process,required_free_bytes:budget.required_free_bytes,reserve_bytes:budget.reserve_bytes,baseline_host_bytes:baseline.host_free_bytes,...(probe?{baseline_docker_bytes:baseline.docker_free_bytes,docker_probe_container:probe.Id}:{}),timeout_ms:options.timeout??300000,event_path:event,ready_path:ready,child_path:child,...(options.ownedContainerName?{owned_container:{name:options.ownedContainerName,label_key:'org.curriculos-abertos.qa-run',label_value:this.record.id}}:{}),...(options.ownedDatabaseOperation?{owned_database_operation:options.ownedDatabaseOperation}:{})};
  exclusive(control,commandControl);this.event('command_intent',{id,control,ready,child});
  const script=fileURLToPath(new URL('./qa-command-watchdog.py',import.meta.url));
  // The independent supervisor monitors disk while this Node thread is blocked.
  // Its two PID receipts were registered above, so reconciliation can find it.
  // JS signal callbacks cannot run during spawnSync. Let the default signal
  // terminate this owner instead: the independent watchdog detects its death,
  // contains the owned work, and leaves a lease for explicit reconciliation.
  this.removeSignals();
  let result:ReturnType<typeof spawnSync>;
  try{result=spawnSync('python3',[script,'--control',control,'--',executable,...args],{cwd:this.executor.root,env:{...process.env,...options.env},input:options.input,encoding:options.binary?undefined:'utf8',maxBuffer:32*1024**2});}
  finally{if(this.signalHandlers)for(const signal of ['SIGINT','SIGTERM'] as const)process.on(signal,this.signalHandlers[signal]);}
  const proof=existsSync(event)?JSON.parse(readFileSync(event,'utf8')):undefined;
  if(proof){this.record.reports.push(relative(this.directory,event));this.persist();}
  if(proof&&proof.exit_code!==124&&!this.liveChildren().some(p=>p.pid===proof.watchdog?.pid||p.pid===proof.child_pid))this.markResource(processResource,'cleaned');
  else if(proof&&proof.exit_code===124)this.markResource(processResource,'retained',{guard_failed:true});
  if(result.status!==0||!proof||proof.exit_code!==0){const error=new Error(`QA command failed/contained (${proof?.reason??'missing watchdog receipt'}): ${cleanError(String(result.stderr||result.error?.message||'no diagnosis'))}`);this.tripGuard(error);throw error;}
  this.checkpoint();return options.binary?Buffer.from(result.stdout):String(result.stdout);
 }
 trackChild(child:ChildProcess){
  assert.ok(child.pid);const identity=this.executor.probes.processIdentity(child.pid);assert.ok(identity,'Child process identity unavailable');this.record.children.push(identity);this.persist();
  child.once('exit',()=>{this.record.children=this.record.children.filter(p=>!sameProcess(p,identity));this.persist();});
 }
 liveChildren(){return [...this.record.children,...watchdogChildren(this.record,this.executor.root,this.executor.probes.processIdentity)].filter(p=>sameProcess(this.executor.probes.processIdentity(p.pid),p));}
 interrupt(signal:string){this.interrupted=true;this.record.status='interrupted';this.record.error=signal;this.persist();this.event('interrupted',{signal});this.tripGuard(new Error(signal));}
 stopMonitor(){if(this.monitor)clearInterval(this.monitor);this.monitor=undefined;}
 finish(status:'passed'|'failed'|'interrupted',error?:unknown){
  this.stopMonitor();if(this.liveChildren().length){status='interrupted';error='Tracked children remain active; lock retained';}
  if(status==='passed'&&this.record.resources.some(r=>r.owned&&r.disposition==='disposable'&&r.status!=='cleaned')){status='failed';error='Disposable QA resources lack verified closure';}
  this.record.status=status;if(error)this.record.error=cleanError(error);
  const retained=this.record.resources.filter(r=>r.status!=='cleaned');
  if(retained.length)this.record.retention={reason:status==='passed'?'Explicitly retained evidence/resources; review before another allocation':'Failure/interruption diagnostics; review before another allocation',review_event:'Before next heavy QA or disposal'};
  this.persist();this.recordReport('completion-'+randomUUID(),{at:now(),id:this.record.id,status:this.record.status,error:this.record.error,resources:this.record.resources,retention:this.record.retention});
 }
 async assertPublicationLimit(query:(sql:string)=>Promise<{rows:Record<string,unknown>[]}>,additional:number){this.checkpoint();assert.ok(Number.isSafeInteger(additional)&&additional>=0);const n=Number((await query('SELECT count(*)::int AS n FROM publications')).rows[0]?.n);assert.ok(Number.isSafeInteger(n)&&n+additional<=3,'QA publication limit (3) reached; consolidate/retire instead of adding another full corpus');this.setInputs({publication_limit:3,publications_before:n});}
 async assertQaDatabase(query:(sql:string)=>Promise<{rows:Record<string,unknown>[]}>,project?:string,baseUrl?:string){
  this.throwIfAborted();const db=(await query('SELECT current_database() AS name')).rows[0];assert.equal(db?.name,'curriculos_qa','Mutating QA must use the isolated curriculos_qa database');
  const containers=this.executor.probes.containers(),base=baseUrl?new URL(baseUrl):undefined;
  if(base){assert.ok(!base.username&&!base.password,'Credentials cannot be embedded in QA endpoint');assert.ok(['http:','https:'].includes(base.protocol)&&['localhost','127.0.0.1','[::1]'].includes(base.hostname),'QA endpoint must be a local isolated app');}
  const apps=containers.filter(c=>c.State.Running&&c.Config.Labels?.['com.docker.compose.service']==='app'&&c.Config.Labels?.['com.docker.compose.project']?.startsWith('curriculos-abertos-clean-'));
  const app=apps.find(c=>(!project||c.Config.Labels?.['com.docker.compose.project']===project)&&(!base||Object.values(c.NetworkSettings.Ports??{}).flat().some(p=>p&&p.HostPort===(base.port||'80')&&['127.0.0.1','::1'].includes(p.HostIp))));assert.ok(app,'No isolated QA app matches project/endpoint');
  const name=app.Config.Labels!['com.docker.compose.project'];assert.match(name,/^curriculos-abertos-clean-[a-z0-9-]+$/);
  const database=containers.find(c=>c.State.Running&&c.Config.Labels?.['com.docker.compose.service']==='db'&&c.Config.Labels?.['com.docker.compose.project']===name);assert.ok(database);
  const actual=String((await query('SELECT system_identifier::text AS id FROM pg_control_system()')).rows[0]?.id);
  const expected=this.executor.probes.databaseCluster(database.Id);assert.match(actual,/^\d+$/,'Invalid database cluster identifier');assert.equal(actual,expected,'SQL connection and QA endpoint target different PostgreSQL clusters');
  const active=Number((await query("SELECT count(*)::int AS n FROM jobs WHERE status IN ('queued','running')")).rows[0]?.n);assert.ok(Number.isSafeInteger(active)&&active===0,'QA has queued/running jobs; reconcile existing work before another mutation');
  const expectedFingerprint=this.executor.probes.sourceFingerprint(this.executor.root),appProof=this.executor.probes.runtimeFingerprint(app.Id);
  assert.equal(appProof.source_tree_sha256,expectedFingerprint,'QA app fingerprint differs from current checkout; do not attribute old runtime evidence to new code');
  const worker=containers.find(c=>c.State.Running&&c.Config.Labels?.['com.docker.compose.service']==='worker'&&c.Config.Labels?.['com.docker.compose.project']===name);assert.ok(worker,'QA worker must be running');
  const workerProof=this.executor.probes.runtimeFingerprint(worker.Id);assert.equal(workerProof.source_tree_sha256,expectedFingerprint,'QA worker fingerprint differs from current checkout');assert.equal(workerProof.image_id,appProof.image_id,'QA app/worker use different image IDs');
  const migrations=join(this.executor.root,'src/db/migrations');if(existsSync(migrations)){
   const files=readdirSync(migrations).filter(n=>n.endsWith('.sql')).sort(),rows=(await query('SELECT name,sha256 FROM schema_migrations ORDER BY name')).rows;
   assert.deepEqual(rows.map(r=>({name:r.name,sha256:r.sha256})),files.map(name=>({name,sha256:hash(readFileSync(join(migrations,name)))})),'QA migrations differ from current checkout');
  }
  this.setInputs({project:name,database:'curriculos_qa',runtime_image_id:appProof.image_id,runtime_source_tree_sha256:expectedFingerprint});return name;
 }
}

export function currentQaRun(){const run=context.getStore();assert.ok(run,'Heavy QA mutation requires the common executor');return run;}
export function withQaRun<T>(options:QaRunOptions,body:(run:QaRun)=>Promise<T>|T){return new QaExecutor().run(options,body);}
export function assertQaChildContext(){
 const root=realpathSync(process.env.QA_EXECUTOR_ROOT??process.cwd()),id=process.env.QA_EXECUTOR_RUN_ID,token=process.env.QA_EXECUTOR_TOKEN,parent=Number(process.env.QA_EXECUTOR_PARENT_PID);
 assert.ok(id&&idPattern.test(id)&&token&&parent===process.ppid,'Missing authenticated QA parent context');
 const record=JSON.parse(readFileSync(join(root,'var/jobs',id,'retention.json'),'utf8')) as RunRecord,lease=JSON.parse(readFileSync(join(root,lockName),'utf8'));
 assert.equal(record.root,root);assert.equal(record.id,lease.run_id);assert.equal(record.token_sha256,hash(token));assert.equal(lease.token_sha256,hash(token));assert.equal(record.status,'running');assert.equal(record.process.pid,parent);assert.ok(sameProcess(processIdentity(parent),record.process),'QA parent is no longer active');assert.ok(record.children.some(child=>sameProcess(processIdentity(process.pid),child)),'Worker is not registered by its QA parent');
 return{root,run_id:id,resources:record.resources,inputs:record.inputs};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const executor=new QaExecutor(),[action,id,...reason]=process.argv.slice(2);
 if(action==='list')console.log(JSON.stringify(executor.list(),null,2));
 else if(action==='reconcile'&&id&&reason.length){executor.reconcile({runId:id,decision:'retain',reason:reason.join(' ')});console.log(JSON.stringify({id,decision:'retain',resources_removed:false}));}
 else {console.log('Usage: node --import tsx scripts/qa-executor.ts list | reconcile <run-id> <retention reason>');if(action&&action!=='--help')process.exitCode=1;}
}
