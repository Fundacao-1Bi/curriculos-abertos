/** Runs unit/integration tests in a fresh owned database, never in the public data database. */
import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { readdir } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { basename } from 'node:path';
import pg from 'pg';
import { withQaRun } from './qa-executor';

async function readDatabaseRuntime(client:pg.Client){return(await client.query("SELECT current_setting('server_version') AS server_version,current_setting('server_version_num') AS server_version_num,d.datcollate AS lc_collate,d.datctype AS lc_ctype FROM pg_database d WHERE d.datname=current_database()")).rows[0] as Record<string,unknown>;}

await withQaRun({kind:'tests',purpose:'Run the complete test suite in one owned, bounded PostgreSQL fixture',requiresDocker:true},async qa=>{
 const started_at=new Date().toISOString(),suffix=randomBytes(6).toString('hex');
 const container=`ca-tests-${suffix}`,volume=`ca-tests-data-${suffix}`,database=`curriculum_test_${suffix}`,password=randomBytes(32).toString('hex');
 const GiB=1024**3;
 // These fixtures are synthetic tests, not the national corpus. Admit at most
 // 1GiB DB + 1GiB WAL + 1GiB indexes/workspace, keeping an independent 2GiB reserve.
 qa.reserve({stage:'isolated-tests',required_free_bytes:5*GiB,reserve_bytes:2*GiB});
 const report:Record<string,unknown>={kind:'tests',started_at,database,fixture_policy:'Owned synthetic fixture only; no published corpus import',capacity:{database_bytes:GiB,wal_bytes:GiB,index_and_workspace_bytes:GiB,reserve_bytes:2*GiB,required_free_bytes:5*GiB},passed:false};
 let createdContainer=false,createdDatabase=false,createdVolume=false,containerRemoved=false,testsCompleted=false;
 let containerId:string|undefined,containerResource:string|undefined,databaseResource:string|undefined,volumeResource:string|undefined,volumeCreatedAt:string|undefined;
 let admin:pg.Client|undefined,databaseRuntime:Record<string,unknown>|undefined;
 const secrets=[password,process.env.TEST_DATABASE_ADMIN_URL,process.env.DATABASE_URL,process.env.POSTGRES_PASSWORD].filter((s):s is string=>Boolean(s));
 function safe(message:string){let value=message;for(const secret of secrets)value=value.split(secret).join('[redacted]');return value.replace(/postgres(?:ql)?:\/\/[^\s"']+/g,'[private database]');}
 function run(command:string,args:string[],env:NodeJS.ProcessEnv=process.env,capture=false,cleanup=false):Promise<string> {
  if(!cleanup)qa.checkpoint();
  // The intent is written before spawn; trackChild then records the actual PID
  // and identity. Arguments/env can contain connection secrets and stay private.
  const intent=qa.registerResource({kind:'process',id:`test-command-${randomBytes(8).toString('hex')}`,owned:true,disposition:'disposable',metadata:{executable:basename(command)}});
  return new Promise((resolveRun,reject)=>{
   const child=spawn(command,args,{env,stdio:['ignore',capture?'pipe':'inherit',capture?'pipe':'inherit']});
   let output='',settled=false;
   if(capture){const consume=(chunk:Buffer)=>{output=(output+chunk.toString()).slice(-64*1024);};child.stdout?.on('data',consume);child.stderr?.on('data',consume);}
   child.once('error',error=>{if(settled)return;settled=true;qa.markResource(intent,'cleaned');reject(new Error(safe(error.message)));});
   child.once('close',code=>{if(settled)return;settled=true;qa.markResource(intent,'cleaned');if(code===0)resolveRun(output);else reject(new Error(`${basename(command)} exited ${code}. ${capture?safe(output.slice(-1200)):''}`));});
   if(child.pid){
    qa.markResource(intent,'created');
    try{qa.trackChild(child);}catch(error){child.kill('SIGTERM');reject(error);}
   }
  });
 }
 try {
  let url:string;
  if(process.env.TEST_DATABASE_ADMIN_URL) {
   assert.match(database,/^curriculum_test_[a-f0-9]{12}$/,'Generated test database identifier invalid');
   const parsed=new URL(process.env.TEST_DATABASE_ADMIN_URL);
   assert.ok(['postgres:','postgresql:'].includes(parsed.protocol),'TEST_DATABASE_ADMIN_URL must use PostgreSQL');
   assert.ok(['localhost','127.0.0.1','[::1]'].includes(parsed.hostname),'TEST_DATABASE_ADMIN_URL must address a loopback Docker PostgreSQL; remote/native servers have no verified disk budget');
   const hostPort=parsed.port||'5432';assert.ok(/^\d+$/.test(hostPort)&&Number(hostPort)>0&&Number(hostPort)<=65535,'Invalid administration port');
   admin=new pg.Client({connectionString:process.env.TEST_DATABASE_ADMIN_URL,connectionTimeoutMillis:5000});await admin.connect();databaseRuntime=await readDatabaseRuntime(admin);
   const actualCluster=String((await admin.query('SELECT system_identifier::text AS id FROM pg_control_system()')).rows[0]?.id??'');assert.match(actualCluster,/^\d+$/,'Cannot identify the PostgreSQL administration cluster');
   const published=(await run('docker',['ps','-q','--no-trunc','--filter',`publish=${hostPort}`],process.env,true)).trim().split(/\s+/).filter(Boolean);
   const matching:string[]=[];
   for(const id of published){
    const bindings=JSON.parse(await run('docker',['inspect',id,'--format','{{json .NetworkSettings.Ports}}'],process.env,true)) as Record<string,{HostIp:string;HostPort:string}[]|null>;
    if(!bindings['5432/tcp']?.some(binding=>binding.HostPort===hostPort&&['127.0.0.1','0.0.0.0','::1','::',''].includes(binding.HostIp)))continue;
    const expected=(await run('docker',['exec',id,'sh','-c','exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -v ON_ERROR_STOP=1 -c "SELECT system_identifier::text FROM pg_control_system()"'],process.env,true)).trim();
    if(expected===actualCluster)matching.push(id);
   }
   assert.equal(matching.length,1,'Administration connection must match exactly one running local Docker PostgreSQL with a verified 5432 host binding and cluster identity');
   qa.registerResource({kind:'container',id:matching[0],owned:false,disposition:'retain',metadata:{server_host:parsed.hostname,server_port:hostPort,system_identifier:actualCluster}});
   report.admin_server={container_id:matching[0],host:parsed.hostname,port:hostPort,system_identifier:actualCluster};
   assert.equal((await admin.query('SELECT count(*)::int AS n FROM pg_database WHERE datname=$1',[database])).rows[0].n,0,'Test database must not preexist');
   databaseResource=qa.registerResource({kind:'database',id:database,owned:true,disposition:'disposable',metadata:{server_host:parsed.hostname,server_port:parsed.port||'5432',fixture:true}});
   qa.checkpoint();await admin.query(`CREATE DATABASE "${database}"`);createdDatabase=true;qa.markResource(databaseResource,'created');
   parsed.pathname='/'+database;url=parsed.toString();secrets.push(url);report.mode='explicit_admin_connection';
  }else {
   await run('docker',['info','--format','{{.ServerVersion}}'],process.env,true);
   const image=process.env.TEST_POSTGRES_IMAGE??'postgres:17.11-bookworm';
   assert.match(image,/^[A-Za-z0-9][A-Za-z0-9._/:@-]*$/,'Invalid fixture image reference');
   const imageProof=(await run('docker',['image','inspect',image,'--format','{{.Id}}|{{json .Config.Volumes}}'],process.env,true)).trim();
   const separator=imageProof.indexOf('|'),imageId=imageProof.slice(0,separator);assert.match(imageId,/^sha256:[a-f0-9]{64}$/,'A pre-provisioned local fixture image is required');
   const declaredVolumes=JSON.parse(imageProof.slice(separator+1)) as Record<string,unknown>|null;
   assert.ok(Object.keys(declaredVolumes??{}).every(path=>path==='/var/lib/postgresql/data'),'Fixture image declares an unregistered volume; review its data mount before using it');
   assert.equal((await run('docker',['ps','-a','--filter',`name=^/${container}$`,'--format','{{.ID}}'],process.env,true)).trim(),'','Test container must not preexist');
   const existingVolumes=(await run('docker',['volume','ls','--format','{{.Name}}'],process.env,true)).trim().split('\n');assert.ok(!existingVolumes.includes(volume),'Test data volume must not preexist');
   volumeResource=qa.registerResource({kind:'volume',id:volume,owned:true,disposition:'disposable',metadata:{fixture:true,driver:'local',ownership_marker:suffix}});
   assert.equal((await run('docker',['volume','create','--driver','local','--label',`org.curriculos-abertos.test-token=${suffix}`,volume],process.env,true)).trim(),volume,'Fixture data volume creation returned another name');
   createdVolume=true;qa.markResource(volumeResource,'created');
   const volumeProof=(await run('docker',['volume','inspect',volume,'--format','{{.Name}}|{{.Driver}}|{{.CreatedAt}}|{{index .Labels "org.curriculos-abertos.test-token"}}'],process.env,true)).trim().split('|');
   assert.equal(volumeProof.length,4);assert.equal(volumeProof[0],volume);assert.equal(volumeProof[1],'local');assert.equal(volumeProof[3],suffix);assert.ok(volumeProof[2],'Fixture data volume creation identity is required');
   volumeCreatedAt=volumeProof[2];qa.markResource(volumeResource,'created',{created_at:volumeCreatedAt});report.volume=volume;report.volume_created_at=volumeCreatedAt;
   containerResource=qa.registerResource({kind:'container',id:container,owned:true,disposition:'disposable',metadata:{fixture:true,image,image_id:imageId,ownership_marker:suffix,data_volume:volume}});
   containerId=(await run('docker',['run','-d','--rm','--pull=never','--name',container,'--mount',`type=volume,source=${volume},target=/var/lib/postgresql/data`,'--memory','1g','--cpus','2','--pids-limit','128','--stop-timeout','30','--label',`org.curriculos-abertos.test-token=${suffix}`,'-p','127.0.0.1::5432','-e','POSTGRES_USER=curriculum_test','-e',`POSTGRES_DB=${database}`,'-e','POSTGRES_PASSWORD',imageId],{...process.env,POSTGRES_PASSWORD:password},true)).trim();
   assert.match(containerId,/^[a-f0-9]{64}$/,'Disposable container ID is required');createdContainer=true;qa.markResource(containerResource,'created');report.mode='disposable_container';report.container=container;report.container_id=containerId;
   const portOutput=await run('docker',['port',containerId,'5432/tcp'],process.env,true);
   const port=portOutput.match(/127\.0\.0\.1:(\d+)/)?.[1];if(!port)throw Error('Disposable PostgreSQL port not found.');
   url=`postgresql://curriculum_test:${password}@127.0.0.1:${port}/${database}`;secrets.push(url);
  }
  let ready=false,lastReadinessError='No connection attempt completed.';
  for(let attempt=0;attempt<40;attempt++){
   qa.checkpoint();const client=new pg.Client({connectionString:url,connectionTimeoutMillis:1000});
   try{await client.connect();databaseRuntime=await readDatabaseRuntime(client);ready=true;break;}
   catch(error){lastReadinessError=safe((error as Error).message);await new Promise(r=>setTimeout(r,250));}
   finally{await client.end().catch(()=>{});}
  }
  if(!ready){
   const logs=createdContainer?await run('docker',['logs','--tail','60',containerId!],process.env,true).catch(error=>`Unable to read disposable PostgreSQL logs: ${safe((error as Error).message)}`):'';
   throw Error(`Disposable PostgreSQL failed readiness. Last attempt: ${lastReadinessError}${logs?`\nContainer logs:\n${safe(logs)}`:''}`);
  }
  const files=(await readdir('tests')).filter(n=>n.endsWith('.test.ts')).sort().map(n=>'tests/'+n);
  if(!files.length)throw Error('No test files found.');report.files=files.length;report.database_runtime=databaseRuntime;report.node_runtime=process.version;
  console.log(JSON.stringify({event:'test_database_ready',mode:report.mode,container:createdContainer?container:undefined,database,database_runtime:databaseRuntime,node_runtime:process.version,files:files.length,fixture_policy:report.fixture_policy}));
  // This child runs the tests only; it cannot acquire a second executor lease.
  // Helpers imported by unit tests do not receive the parent's executor token.
  await run(process.execPath,['--import','tsx','--test','--test-concurrency=1',...files],{...process.env,DATABASE_URL:url,DOMAIN_INTEGRATION_TEST:'1',OPTIONAL_CONTRACT_INTEGRATION:'1'});
  qa.checkpoint();testsCompleted=true;report.passed=true;
 }catch(error){report.error=safe((error as Error).message);console.error(report.error);process.exitCode=1;}
 finally{
  // Persist the outcome before any removal. Failure fixtures are deliberately
  // retained for diagnosis, with the executor recording the unresolved resources.
  report.tests_completed=testsCompleted;report.completed_at=new Date().toISOString();qa.recordReport('test-all-before-cleanup',report);
  if(testsCompleted){
   if(createdDatabase&&admin&&databaseResource){try{
    await qa.guardCleanup([databaseResource],async()=>{
     assert.match(database,/^curriculum_test_[a-f0-9]{12}$/);
     const connections=(await admin!.query('SELECT count(*)::int AS n FROM pg_stat_activity WHERE datname=$1',[database])).rows[0].n;
     assert.equal(connections,0,'Test database still has connections; preserve it');
     // Do not FORCE-disconnect a connection that appeared after the proof.
     await admin!.query(`DROP DATABASE "${database}"`);qa.markResource(databaseResource!,'cleaned');
    });
   }catch(error){report.cleanup_error=safe((error as Error).message);report.passed=false;process.exitCode=1;}}
   if(createdContainer&&containerId&&containerResource){try{
    await qa.guardCleanup([containerResource],async()=>{
     const proof=await run('docker',['inspect',containerId!,'--format','{{.Id}}|{{index .Config.Labels "org.curriculos-abertos.test-token"}}'],process.env,true,true);
     assert.equal(proof.trim(),containerId+'|'+suffix,'Fixture container ownership changed');
     await run('docker',['stop',containerId!],process.env,true,true);
     const removalDeadline=Date.now()+3000;
     do{
      const existing=(await run('docker',['ps','-aq','--no-trunc','--filter',`id=${containerId!}`],process.env,true,true)).trim();
      if(!existing){containerRemoved=true;break;}
      await new Promise(resolveWait=>setTimeout(resolveWait,100));
     }while(Date.now()<removalDeadline);
     assert.ok(containerRemoved,'Fixture container is not fully removed; retain its named data volume');
     qa.markResource(containerResource!,'cleaned');report.fixture_container_removed=true;
    });
   }catch(error){report.cleanup_error=safe((error as Error).message);report.passed=false;process.exitCode=1;}}
   if(createdVolume&&volumeResource&&volumeCreatedAt){try{
    assert.ok(containerRemoved,'Fixture container removal must be proved before data-volume cleanup');
    await qa.guardCleanup([volumeResource],async()=>{
     const proof=(await run('docker',['volume','inspect',volume,'--format','{{.Name}}|{{.Driver}}|{{.CreatedAt}}|{{index .Labels "org.curriculos-abertos.test-token"}}'],process.env,true,true)).trim();
     assert.equal(proof,[volume,'local',volumeCreatedAt,suffix].join('|'),'Fixture data-volume identity or ownership changed');
     await run('docker',['volume','rm',volume],process.env,true,true);qa.markResource(volumeResource!,'cleaned');report.fixture_data_volume_removed=true;
    });
   }catch(error){qa.markResource(volumeResource,'retained');report.cleanup_error=safe((error as Error).message);report.passed=false;process.exitCode=1;}}
  }else{
   if(createdDatabase&&databaseResource)qa.markResource(databaseResource,'retained');
   if(createdContainer&&containerResource)qa.markResource(containerResource,'retained');
   if(createdVolume&&volumeResource)qa.markResource(volumeResource,'retained');
   report.retention_reason='Test failure or interruption; preserve owned fixture for diagnosis and explicit reconciliation before another allocation';
  }
  await admin?.end().catch(()=>{});report.finished_at=new Date().toISOString();qa.recordReport('test-all',report);
 }
});
