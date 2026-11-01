import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn,type ChildProcess} from 'node:child_process';
import {statfsSync} from 'node:fs';
import {mkdtemp,mkdir,writeFile,readFile,rm,readdir,symlink,access,realpath} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve,basename,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {QaExecutor,assertQaChildContext,processIdentity,type DockerContainer} from '../scripts/qa-executor';

const fixture=fileURLToPath(new URL('./fixtures/qa-executor-process.ts',import.meta.url));
const GiB=1024**3;
const runOptions={kind:'unit',purpose:'Small isolated executor contract test',requiresDocker:false};

function executor(root:string,extra:Record<string,unknown>={}){
 return new QaExecutor({root,probes:{
  inventory:()=>({fixture:true}),
  snapshot:()=>({host_free_bytes:100*GiB,docker_free_bytes:100*GiB,projects:[]}),
  cleanupGuards:()=>{},runtimeFingerprint:()=>({image_id:'sha256:'+'a'.repeat(64),source_tree_sha256:'b'.repeat(64)}),sourceFingerprint:()=> 'b'.repeat(64),...extra,
 }});
}
function bindingContainers():DockerContainer[]{
 const make=(id:string,project:string,service:string,port?:string):DockerContainer=>({
  Id:id,Name:'/'+id,State:{Running:true},Config:{Labels:{'com.docker.compose.project':project,'com.docker.compose.service':service}},Mounts:[],
  NetworkSettings:{Ports:port?{'3000/tcp':[{HostIp:'127.0.0.1',HostPort:port}]}:{}},
 });
 return[make('principal-app','curriculos-abertos','app','3000'),make('qa-app','curriculos-abertos-clean-unit','app','3107'),make('qa-worker','curriculos-abertos-clean-unit','worker'),make('qa-db','curriculos-abertos-clean-unit','db'),make('other-qa-app','curriculos-abertos-clean-other','app','3108'),make('other-qa-db','curriculos-abertos-clean-other','db')];
}
async function temporary(body:(root:string)=>Promise<void>){
 const root=await realpath(await mkdtemp(join(tmpdir(),'curriculos-executor-unit-')));
 try{await body(root);}finally{await rm(root,{recursive:true,force:true});}
}
async function records(root:string){
 const entries:{path:string;value:Record<string,unknown>}[]=[];
 async function walk(path:string){for(const e of await readdir(path,{withFileTypes:true}).catch(()=>[])){
  const file=join(path,e.name);if(e.isDirectory())await walk(file);
  else if(e.isFile()&&e.name==='retention.json')entries.push({path:file,value:JSON.parse(await readFile(file,'utf8'))});
 }}
 await walk(join(root,'var','jobs'));return entries;
}
function child(root:string,mode:string,env:NodeJS.ProcessEnv=process.env){
 const process=spawn(globalThis.process.execPath,['--import','tsx',fixture,root,mode],{env,stdio:['ignore','pipe','pipe']});
 let stdout='',stderr='';process.stdout?.on('data',(chunk:Buffer)=>stdout+=chunk.toString());process.stderr?.on('data',(chunk:Buffer)=>stderr+=chunk.toString());
 const exited=new Promise<number|null>((done,reject)=>{process.once('error',reject);process.once('close',done);});
 const acquired=new Promise<{pid:number;path:string}>((done,reject)=>{
  let buffer='';process.stdout?.on('data',(chunk:Buffer)=>{buffer+=chunk.toString();for(const line of buffer.split('\n')){try{const value=JSON.parse(line);if(value.event==='acquired')done(value);}catch{}}});
  process.once('error',reject);process.once('close',()=>reject(new Error('Process exited before acquiring: '+stderr)));
 });
 // Some modes intentionally reject before allocation; consume the unused waiter.
 void acquired.catch(()=>{});
 function event(name:string){return new Promise<Record<string,unknown>>((done,reject)=>{
  const scan=()=>{for(const line of stdout.split('\n')){try{const row=JSON.parse(line);if(row.event===name)done(row);}catch{}}};scan();
  process.stdout?.on('data',scan);process.once('close',()=>reject(new Error('Process exited before '+name+': '+stderr)));
 });}
 return {process,exited,acquired,event,output:()=>({stdout,stderr})};
}
async function killAndWait(child:{process:ChildProcess;exited:Promise<number|null>}){
 if(child.process.exitCode===null&&child.process.signalCode===null)child.process.kill('SIGKILL');
 await child.exited;
}

test('capacity refusal happens before caller can allocate a QA resource',()=>temporary(async root=>{
 let allocated=false;
 const qa=executor(root,{snapshot:()=>({host_free_bytes:256,docker_free_bytes:100*GiB,projects:[]})});
 await assert.rejects(()=>qa.run(runOptions,async run=>{
  run.reserve({required_free_bytes:1024,reserve_bytes:256});
  allocated=true;await writeFile(join(root,'should-not-exist'),'unexpected');
 }));
 assert.equal(allocated,false);await assert.rejects(()=>access(join(root,'should-not-exist')));
}));

test('a resource cannot be allocated without a recorded budget or claimed from an existing path',()=>temporary(async root=>{
 const present=join(root,'var','preexisting.tmp');await mkdir(dirname(present),{recursive:true});await writeFile(present,'preexisting');
 await executor(root).run(runOptions,async qa=>{
  assert.throws(()=>qa.registerResource({kind:'file',id:'no-budget',path:join(root,'var','no-budget'),owned:true,disposition:'disposable'}),/Reserve|budget|capacity/i);
  qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});
  assert.throws(()=>qa.registerResource({kind:'file',id:present,path:present,owned:true,disposition:'disposable'}),/Existing|claim/i);
 });
 assert.equal(await readFile(present,'utf8'),'preexisting');await assert.rejects(()=>access(join(root,'var','no-budget')));
}));

test('unregistered, uncreated, traversing and symlink resources cannot authorize cleanup',()=>temporary(async root=>{
 const outside=join(root,'foreign');await mkdir(outside);await writeFile(join(outside,'keep'),'foreign');await mkdir(join(root,'var'));await symlink(outside,join(root,'var','redirect'));
 await symlink(join(outside,'not-created'),join(root,'var','dangling'));
 await executor(root).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});
  assert.throws(()=>qa.registerResource({kind:'file',id:'redirect',path:join(root,'var','redirect','future'),owned:true,disposition:'disposable'}),/Symlink/i);
  assert.throws(()=>qa.registerResource({kind:'file',id:'dangling',path:join(root,'var','dangling'),owned:true,disposition:'disposable'}),/Symlink/i,'A dangling link still cannot be claimed as an unallocated own path');
  assert.throws(()=>qa.registerResource({kind:'file',id:'outside',path:join(root,'..','outside'),owned:true,disposition:'disposable'}),/inside|workspace/i);
  let called=false;await assert.rejects(()=>qa.guardCleanup(['not-registered'],async()=>{called=true;}));assert.equal(called,false);
  const planned=qa.registerResource({kind:'file',id:'planned-only',path:join(root,'var','not-created'),owned:true,disposition:'retain'});
  await assert.rejects(()=>qa.guardCleanup([planned],async()=>{called=true;}));assert.equal(called,false);
 });
 assert.equal(await readFile(join(outside,'keep'),'utf8'),'foreign');
}));

test('existing project and publication limits block another national allocation',()=>temporary(async root=>{
 const projects=[{name:'curriculos-abertos-clean-first'},{name:'curriculos-abertos-clean-second'}];
 await assert.rejects(()=>executor(root,{snapshot:()=>({host_free_bytes:100*GiB,docker_free_bytes:100*GiB,projects})}).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:GiB,reserve_bytes:GiB/4});
  assert.throws(()=>qa.registerResource({kind:'publication',id:'third-national',owned:true,disposition:'retain'}),/Too many QA|consolidate/i);
 }),/Too many QA|consolidate/i);
 const fresh=await realpath(await mkdtemp(join(tmpdir(),'curriculos-executor-limits-')));
 try{await executor(fresh).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:GiB,reserve_bytes:GiB/4});
  let count=2;
  const query=async(statement:string)=>{assert.match(statement,/SELECT count\(\*\).*publications/i);return{rows:[{n:count}]};};
  await qa.assertPublicationLimit(query,1);count=3;
  await assert.rejects(()=>qa.assertPublicationLimit(query,1),/publication limit|consolidate/i);
 });}finally{await rm(fresh,{recursive:true,force:true});}
}));

test('retained test containers or volumes block another test allocation before creating resources',()=>temporary(async root=>{
 for(const kind of ['container','volume'] as const){
  const fixture={kind,id:kind==='container'?'old-container-id':'ca-tests-data-old',name:kind==='container'?'ca-tests-old':'ca-tests-data-old'};
  let allocated=false;
  await assert.rejects(()=>executor(root,{snapshot:()=>({host_free_bytes:100*GiB,docker_free_bytes:100*GiB,projects:[],test_fixtures:[fixture]})}).run({...runOptions,kind:'tests'},async qa=>{
   qa.reserve({required_free_bytes:GiB,reserve_bytes:GiB/4});
   qa.registerResource({kind:'file',id:'next-test-allocation-'+kind,path:join(root,'var','new-test-'+kind),owned:true,disposition:'disposable'});
   allocated=true;
  }),/retained test fixture|fixture.*exists/i);
  assert.equal(allocated,false);await assert.rejects(()=>access(join(root,'var','new-test-'+kind)));
 }
}));

test('mutating QA rejects the principal database before touching Docker or any mutation',()=>temporary(async root=>{
 const statements:string[]=[];
 await executor(root).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:GiB,reserve_bytes:GiB/4});
  await assert.rejects(()=>qa.assertQaDatabase(async statement=>{statements.push(statement);return{rows:[{name:'curriculos'}]};},'curriculos-abertos','http://localhost:3000'),/isolated curriculos_qa/i);
 });
 assert.deepEqual(statements,['SELECT current_database() AS name']);
}));

test('read-only admission correlates the QA endpoint port and actual SQL cluster before reserving',()=>temporary(async root=>{
 const statements:string[]=[],clusterChecks:string[]=[];
 await executor(root,{containers:bindingContainers,databaseCluster:(id:string)=>{clusterChecks.push(id);return'111111111111';}}).run(runOptions,async qa=>{
  const project=await qa.assertQaDatabase(async statement=>{
   statements.push(statement);
   if(statement==='SELECT current_database() AS name')return{rows:[{name:'curriculos_qa'}]};
   if(statement.startsWith('SELECT count(*)::int AS n FROM jobs'))return{rows:[{n:0}]};
   assert.equal(statement,'SELECT system_identifier::text AS id FROM pg_control_system()');return{rows:[{id:'111111111111'}]};
  },undefined,'http://127.0.0.1:3107');
  assert.equal(project,'curriculos-abertos-clean-unit');
  qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});
 });
 assert.deepEqual(clusterChecks,['qa-db']);assert.equal(statements.length,3);
}));

test('a QA database name does not authorize the principal endpoint or another QA cluster',()=>temporary(async root=>{
 await executor(root,{containers:bindingContainers,databaseCluster:()=> '111111111111'}).run(runOptions,async qa=>{
  const query=async(statement:string)=>({rows:statement==='SELECT current_database() AS name'?[{name:'curriculos_qa'}]:[{id:'222222222222'}]});
  await assert.rejects(()=>qa.assertQaDatabase(query,undefined,'http://localhost:3000'),/No isolated QA app/);
  await assert.rejects(()=>qa.assertQaDatabase(query,'curriculos-abertos-clean-unit','http://localhost:3108'),/No isolated QA app/);
  await assert.rejects(()=>qa.assertQaDatabase(query,'curriculos-abertos-clean-unit','http://localhost:3107'),/different PostgreSQL clusters/);
  await assert.rejects(()=>qa.assertQaDatabase(query,undefined,'https://external.example:3107'),/local isolated app/);
  await assert.rejects(()=>qa.assertQaDatabase(query,undefined,'http://username:password@127.0.0.1:3107'),/Credentials/);
 });
}));

test('queued or running work must be reconciled before another mutating QA starts',()=>temporary(async root=>{
 await executor(root,{containers:bindingContainers,databaseCluster:()=> '111111111111'}).run(runOptions,async qa=>{
  for(const active of [1,3])await assert.rejects(()=>qa.assertQaDatabase(async statement=>{
   if(statement==='SELECT current_database() AS name')return{rows:[{name:'curriculos_qa'}]};
   if(statement==='SELECT system_identifier::text AS id FROM pg_control_system()')return{rows:[{id:'111111111111'}]};
   assert.match(statement,/FROM jobs WHERE status IN \('queued','running'\)/);return{rows:[{n:active}]};
  },undefined,'http://127.0.0.1:3107'),/queued\/running jobs/);
 });
}));

test('an app or worker from an older checkout cannot produce current-code QA evidence',()=>temporary(async root=>{
 const query=async(statement:string)=>({rows:statement==='SELECT current_database() AS name'?[{name:'curriculos_qa'}]:statement.startsWith('SELECT count(*)')?[{n:0}]:[{id:'111111111111'}]});
 for(const variant of ['app','worker','image']){
  await executor(root,{containers:bindingContainers,databaseCluster:()=> '111111111111',runtimeFingerprint:(id:string)=>({
   image_id:'sha256:'+(variant==='image'&&id==='qa-worker'?'c':'a').repeat(64),
   source_tree_sha256:(variant==='app'&&id==='qa-app'||variant==='worker'&&id==='qa-worker'?'c':'b').repeat(64),
  })}).run(runOptions,async qa=>{
   await assert.rejects(()=>qa.assertQaDatabase(query,undefined,'http://127.0.0.1:3107'),/fingerprint|different image IDs/);
  });
 }
}));

test('invalid or missing Docker free-space measurements cannot reserve capacity',()=>temporary(async root=>{
 for(const value of [Number.NaN,-1,Number.POSITIVE_INFINITY]){
  await assert.rejects(()=>executor(root,{snapshot:()=>({host_free_bytes:value,docker_free_bytes:100*GiB,projects:[]})}).run(runOptions,async qa=>{
   qa.reserve({required_free_bytes:1024,reserve_bytes:256});
  }));
 }
 await assert.rejects(()=>executor(root,{snapshot:()=>({host_free_bytes:100*GiB,projects:[]})}).run({...runOptions,requiresDocker:true},async qa=>{
  qa.reserve({required_free_bytes:1024,reserve_bytes:256});
 }));
}));

test('intent is durable before allocation and existing/retained resources cannot be cleaned',()=>temporary(async root=>{
 const owned=join(root,'var','owned-output.json'),foreign=join(root,'var','foreign-output.json');
 await mkdir(join(root,'var'),{recursive:true});await writeFile(foreign,'foreign');
 await executor(root).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});
  const id=qa.registerResource({kind:'file',id:owned,path:owned,owned:true,disposition:'disposable'});
  const persisted=JSON.stringify((await records(root))[0].value);
  assert.ok(persisted.includes(owned),'Intent exists before a file is allocated');
  await assert.rejects(()=>access(owned));
  await writeFile(owned,'owned');qa.markResource(id,'created');
  const existing=qa.registerResource({kind:'file',id:foreign,path:foreign,owned:false,disposition:'retain'});
  qa.markResource(existing,'retained');
  let deleted=false;
  await assert.rejects(()=>qa.guardCleanup([existing],async()=>{deleted=true;await rm(foreign);}));
  assert.equal(deleted,false);assert.equal(await readFile(foreign,'utf8'),'foreign');
  await qa.guardCleanup([id],async()=>{await rm(owned);});
 });
 assert.equal(await readFile(foreign,'utf8'),'foreign');await assert.rejects(()=>access(owned));
}));

test('cleanup aborts closed when process/mount/Docker inspection fails',()=>temporary(async root=>{
 const path=join(root,'var','keep.json');let attempted=false,guardCalls=0;
 await assert.rejects(()=>executor(root,{cleanupGuards:()=>{guardCalls++;throw new Error('lsof or Docker verification failed');}}).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});
  const id=qa.registerResource({kind:'file',id:path,path,owned:true,disposition:'disposable'});
  await mkdir(dirname(path),{recursive:true});await writeFile(path,'evidence');qa.markResource(id,'created');
  await assert.rejects(()=>qa.guardCleanup([id],async()=>{attempted=true;await rm(path);}),/lsof|Docker/);
  qa.markResource(id,'retained');
 }),/close|disposable/i);
 assert.ok(guardCalls>0);assert.equal(attempted,false);assert.equal(await readFile(path,'utf8'),'evidence');
}));

test('protected originals and backups cannot be registered as disposable own paths',()=>temporary(async root=>{
 await executor(root).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});
  for(const relative of ['data/raw/original.pdf','data/bundles/canonical.json','var/backups/rollback.dump']){
   const path=join(root,relative);
   assert.throws(()=>qa.registerResource({kind:'file',id:path,path,owned:true,disposition:'disposable'}));
  }
 });
}));

test('growth violation blocks subsequent allocations while verified cleanup remains possible',()=>temporary(async root=>{
 let free=10*GiB;
 const path=join(root,'var','bounded.tmp');
 await assert.rejects(()=>executor(root,{snapshot:()=>({host_free_bytes:free,docker_free_bytes:free,projects:[]})}).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:GiB,reserve_bytes:GiB/4});
  const id=qa.registerResource({kind:'file',id:path,path,owned:true,disposition:'disposable'});
  await mkdir(dirname(path),{recursive:true});await writeFile(path,'own temporary data');qa.markResource(id,'created');
  free=GiB/8;
  assert.throws(()=>qa.checkpoint());
  assert.throws(()=>qa.registerResource({kind:'file',id:'not-allocated',path:join(root,'var','next'),owned:true,disposition:'disposable'}));
  await qa.guardCleanup([id],async()=>{await rm(path);});
 }),/reserve|growth/i);
 await assert.rejects(()=>access(path));await assert.rejects(()=>access(join(root,'var','next')));
}));

test('reports are immutable and failures leave a durable unsuccessful receipt',()=>temporary(async root=>{
 await assert.rejects(()=>executor(root).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});
  qa.recordReport('bounded-proof',{version:1});
  assert.throws(()=>qa.recordReport('bounded-proof',{version:2}),'A second report must not overwrite the first');
  throw new Error('intentional isolated failure');
 }),/intentional isolated failure/);
 const retained=await records(root);assert.equal(retained.length,1);
 assert.match(String(retained[0].value.status),/failed|interrupted/);
 const reports:string[]=[];async function walk(path:string){for(const e of await readdir(path,{withFileTypes:true})){const p=join(path,e.name);if(e.isDirectory())await walk(p);else if(e.name.includes('bounded-proof'))reports.push(p);}}
 await walk(dirname(retained[0].path));assert.equal(reports.length,1);assert.equal(JSON.parse(await readFile(reports[0],'utf8')).version,1);
}));

test('private metadata keys are refused and the child capability is never serialized',()=>temporary(async root=>{
 let capability='';
 await executor(root).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});
  for(const key of ['password','cookie','authorization','access_token','session_token']){
   assert.throws(()=>qa.setInputs({[key]:'never-persist-this-value'}),/private|secret|ledger/i);
   assert.throws(()=>qa.registerResource({kind:'job',id:'private-'+key,owned:true,disposition:'retain',metadata:{[key]:'never-persist-this-value'}}),/private|secret|ledger/i);
  }
  capability=String(qa.childEnvironment().QA_EXECUTOR_TOKEN);assert.ok(capability.length>10);
 });
 async function verify(path:string){for(const e of await readdir(path,{withFileTypes:true})){const p=join(path,e.name);if(e.isDirectory())await verify(p);else if(e.isFile()){const raw=await readFile(p,'utf8');assert.ok(!raw.includes(capability));assert.ok(!raw.includes('never-persist-this-value'));}}}
 await verify(join(root,'var','jobs'));
}));

test('real processes contend for the same lock through a symlink alias',()=>temporary(async root=>{
 const alias=root+'-alias';await symlink(root,alias);
 const owner=child(root,'hold');
 try{
  await owner.acquired;
  const competitor=child(alias,'once');assert.notEqual(await competitor.exited,0);
  assert.match(competitor.output().stderr,/lock|ocup|execu|active|ativa/i);
  owner.process.kill('SIGUSR2');assert.equal(await owner.exited,0);
  const successor=child(alias,'once');assert.equal(await successor.exited,0,successor.output().stderr);
 }finally{await killAndWait(owner);await rm(alias,{force:true});}
}));

test('SIGKILL leaves evidence and cannot silently steal lock; explicit retain reconciliation preserves files',()=>temporary(async root=>{
 const owner=child(root,'hold');const acquired=await owner.acquired;await killAndWait(owner);
 const marker=await readFile(acquired.path,'utf8');
 const blocked=child(root,'once');assert.notEqual(await blocked.exited,0);
 const retained=await records(root);assert.ok(retained.length>=1);
 const crashed=retained.find(r=>JSON.stringify(r.value).includes(String(acquired.pid)));assert.ok(crashed);
 const runId=basename(dirname(crashed.path));
 executor(root).reconcile({runId,decision:'retain',reason:'Owned fixture process is confirmed dead; preserve all evidence'});
 assert.equal(await readFile(acquired.path,'utf8'),marker);
 const successor=child(root,'once');assert.equal(await successor.exited,0,successor.output().stderr);
}));

test('an admission crash before the ledger exists is listed and requires explicit reconciliation',()=>temporary(async root=>{
 const runId='qa-unit-orphaned-admission',owner=processIdentity(process.pid);assert.ok(owner);
 await mkdir(join(root,'var','jobs'),{recursive:true});const lock=join(root,'var','qa-executor.lock.json');
 // Reused PID with a different start identity represents the old owner's death
 // without relying on a platform-specific out-of-range process identifier.
 await writeFile(lock,JSON.stringify({schema:'curriculos/qa-lock-v1',run_id:runId,root,process:{...owner,start:'confirmed dead historical admission fixture'},token_sha256:'a'.repeat(64)}),{mode:0o600});
 const retained=join(root,'unique-diagnostic');await writeFile(retained,'keep');
 const qa=executor(root),listed=qa.list();assert.equal(listed.length,1);assert.equal(listed[0].status,'orphaned-admission');assert.equal((await records(root)).length,0,'Listing must not synthesize or erase the old ledger');
 let entered=false;await assert.rejects(()=>qa.run(runOptions,async()=>{entered=true;}),/lock|reconcile/i);assert.equal(entered,false);
 const interrupted=await records(root);assert.equal(interrupted.length,1);assert.equal(interrupted[0].value.status,'interrupted');
 qa.reconcile({runId,decision:'retain',reason:'Explicitly retain interrupted admission; original owner is dead'});
 assert.equal(await readFile(retained,'utf8'),'keep');await assert.rejects(()=>access(lock));
 await qa.run(runOptions,async()=>{entered=true;});assert.equal(entered,true);
}));

test('a retained backup blocks another recovery until its review is explicitly recorded',()=>temporary(async root=>{
 const previous=child(root,'backup');const allocated=await previous.acquired;assert.equal(await previous.exited,0,previous.output().stderr);
 const original=await readFile(allocated.path,'utf8'),retained=await records(root);assert.equal(retained.length,1);assert.equal(retained[0].value.status,'passed');
 const runId=basename(dirname(retained[0].path));let entered=false;
 await assert.rejects(()=>executor(root).run({...runOptions,kind:'recovery'},async()=>{entered=true;}),/retained QA backups/);assert.equal(entered,false);
 executor(root).reconcile({runId,decision:'retain',reason:'Keep this small backup fixture after reviewing its retention need'});
 assert.equal(await readFile(allocated.path,'utf8'),original);
 await executor(root).run({...runOptions,kind:'recovery'},async qa=>{entered=true;qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});});assert.equal(entered,true);
}));

test('a small synchronous command is independently supervised and leaves a closed process receipt',()=>temporary(async root=>{
 const snapshot=()=>{const disk=statfsSync(root);return{host_free_bytes:disk.bavail*disk.bsize,projects:[]};};
 await executor(root,{snapshot}).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:GiB,reserve_bytes:GiB/4});
  const output=qa.commandSync(process.execPath,['-e','process.stdout.write("small-proof\\n")'],{timeout:5000});assert.equal(output,'small-proof\n');
  const commands=qa.record.resources.filter(resource=>resource.kind==='process');assert.equal(commands.length,1);assert.equal(commands[0].status,'cleaned');assert.equal(qa.liveChildren().length,0);
  const proofs=qa.record.reports.filter(path=>path.endsWith('.result.json'));assert.equal(proofs.length,1);
  const proof=JSON.parse(await readFile(join(qa.directory,proofs[0]),'utf8'));assert.equal(proof.exit_code,0);assert.equal(proof.reason,'command_completed');assert.equal(proof.command_arguments_recorded,false);assert.equal(proof.data_removed,false);
 });
}));

test('the independent command deadline stops only the owned command and retains its failed proof',()=>temporary(async root=>{
 const snapshot=()=>{const disk=statfsSync(root);return{host_free_bytes:disk.bavail*disk.bsize,projects:[]};};
 await assert.rejects(()=>executor(root,{snapshot}).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:GiB,reserve_bytes:GiB/4});
  qa.commandSync(process.execPath,['-e','setInterval(()=>{},1000)'],{timeout:50});
 }),/command failed\/contained|timeout/i);
 const retained=await records(root);assert.equal(retained.length,1);assert.equal(retained[0].value.status,'failed');
 const resources=retained[0].value.resources as {kind:string;status:string;metadata:Record<string,string>}[];
 assert.equal(resources.filter(resource=>resource.kind==='process'&&resource.status==='retained').length,1);
 const directory=dirname(retained[0].path),result=(await readdir(directory)).find(name=>name.endsWith('.result.json'));assert.ok(result);
 const proof=JSON.parse(await readFile(join(directory,result),'utf8'));assert.equal(proof.exit_code,124);assert.equal(proof.reason,'command_timeout');assert.equal(proof.data_removed,false);
 assert.equal(processIdentity(proof.child_pid),null);assert.equal(processIdentity(proof.watchdog.pid),null);
}));

test('the independent monitor catches a growth discrepancy before launching the command',()=>temporary(async root=>{
 // Inject only the Node-side baseline. The Python supervisor measures real
 // free space, so this exercises the guard without allocating large files.
 const snapshot=()=>{const disk=statfsSync(root);return{host_free_bytes:disk.bavail*disk.bsize+64*GiB,projects:[]};};
 const marker=join(root,'unexpected-command-output');
 await assert.rejects(()=>executor(root,{snapshot}).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:GiB,reserve_bytes:GiB/4});
  qa.commandSync(process.execPath,['-e','require("fs").writeFileSync(process.argv[1],"must not execute")',marker],{timeout:5000});
 }),/growth_budget_exceeded|command failed\/contained/i);
 await assert.rejects(()=>access(marker));
 const retained=await records(root),directory=dirname(retained[0].path),result=(await readdir(directory)).find(name=>name.endsWith('.result.json'));assert.ok(result);
 const proof=JSON.parse(await readFile(join(directory,result),'utf8'));assert.equal(proof.exit_code,124);assert.equal(proof.reason,'growth_budget_exceeded');assert.equal(proof.child_pid,null);assert.equal(proof.data_removed,false);
}));

test('a live owner cannot be reconciled away merely because a caller asks',()=>temporary(async root=>{
 const owner=child(root,'hold');
 try{
  await owner.acquired;const retained=await records(root);assert.equal(retained.length,1);
  assert.throws(()=>executor(root).reconcile({runId:basename(dirname(retained[0].path)),decision:'retain',reason:'No age-based override'}));
  const blocked=child(root,'once');assert.notEqual(await blocked.exited,0);
  owner.process.kill('SIGUSR2');assert.equal(await owner.exited,0);
 }finally{await killAndWait(owner);}
}));

test('a dead parent cannot release its lock while a recorded child is still alive',()=>temporary(async root=>{
 const owner=child(root,'hold-child');let childPid:number|undefined;
 try{
  const tracked=await owner.event('tracked-child');childPid=Number(tracked.pid);assert.ok(childPid>0);
  await killAndWait(owner);
  const retained=await records(root);assert.equal(retained.length,1);const runId=basename(dirname(retained[0].path));
  assert.throws(()=>executor(root).reconcile({runId,decision:'retain',reason:'Preserve evidence but do not overtake a live owned child'}),/child.*active|filho/i);
  const blocked=child(root,'once');assert.notEqual(await blocked.exited,0);
  process.kill(childPid,'SIGKILL');
  for(let attempt=0;attempt<40&&processIdentity(childPid);attempt++)await new Promise(done=>setTimeout(done,25));
  assert.equal(processIdentity(childPid),null,'Owned fixture child must terminate before reconciliation');
  childPid=undefined;
  executor(root).reconcile({runId,decision:'retain',reason:'Owned parent and child are confirmed dead; retain evidence'});
  const successor=child(root,'once');assert.equal(await successor.exited,0,successor.output().stderr);
 }finally{await killAndWait(owner);if(childPid&&processIdentity(childPid))process.kill(childPid,'SIGKILL');}
}));

test('nonzero process.exitCode is recorded as failure even without a thrown exception',()=>temporary(async root=>{
 const result=child(root,'exit-code');assert.notEqual(await result.exited,0);
 const retained=await records(root);assert.equal(retained.length,1);assert.match(String(retained[0].value.status),/failed|interrupted/);
}));

test('repeated verified runs remove owned outputs and retain unrelated evidence',()=>temporary(async root=>{
 const foreign=join(root,'keep-evidence');await writeFile(foreign,'unchanged');
 for(let attempt=0;attempt<3;attempt++)await executor(root).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});const path=join(root,'var',`output-${attempt}.json`);
  const id=qa.registerResource({kind:'file',id:path,path,owned:true,disposition:'disposable'});await mkdir(dirname(path),{recursive:true});await writeFile(path,'owned');qa.markResource(id,'created');
  await qa.guardCleanup([id],async()=>{await rm(path);});
 });
 assert.equal(await readFile(foreign,'utf8'),'unchanged');
 assert.deepEqual((await readdir(join(root,'var'))).filter(name=>name.startsWith('output-')),[]);
 assert.equal((await records(root)).length,3,'Each execution keeps its compact provenance');
}));

test('worker flag or forged environment cannot create a delegated context',()=>temporary(async root=>{
 assert.throws(()=>assertQaChildContext());
 const unauthenticated=child(root,'child',Object.fromEntries(Object.entries(process.env).filter(([key])=>!key.startsWith('QA_EXECUTOR_'))) as NodeJS.ProcessEnv);
 assert.notEqual(await unauthenticated.exited,0);
 const forged=child(root,'child',{...process.env,QA_EXECUTOR_RUN_ID:'qa-forged',QA_EXECUTOR_TOKEN:'not-a-parent-capability',QA_EXECUTOR_ROOT:resolve(root)});
 assert.notEqual(await forged.exited,0);
 await assert.rejects(()=>access(join(root,'var','fixture-child-marker')));
}));

test('delegation accepts only a child recorded by the live owner',()=>temporary(async root=>{
 await executor(root).run(runOptions,async qa=>{
  qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});
  const untracked=child(root,'child',qa.childEnvironment());assert.notEqual(await untracked.exited,0);
  assert.match(untracked.output().stderr,/not registered|unregistered|registrad/i);
  const tracked=child(root,'child',qa.childEnvironment());qa.trackChild(tracked.process);
  assert.equal(await tracked.exited,0,tracked.output().stderr);assert.match(tracked.output().stdout,/child-accepted/);
  const wrongToken=child(root,'child',{...qa.childEnvironment(),QA_EXECUTOR_TOKEN:'forged-even-with-real-run-id'});qa.trackChild(wrongToken.process);
  assert.notEqual(await wrongToken.exited,0);
 });
}));
