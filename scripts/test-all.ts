/** Runs unit/integration tests in a fresh owned database, never in the public data database. */
import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { readdir } from 'node:fs/promises';
import pg from 'pg';
const suffix=randomBytes(6).toString('hex');
const container=`ca-tests-${suffix}`;
const database=`curriculum_test_${suffix}`;
const password=randomBytes(32).toString('hex');
let createdContainer=false,createdDatabase=false;
let admin:pg.Client|undefined;
function run(command:string,args:string[],env:NodeJS.ProcessEnv=process.env,capture=false):Promise<string> {
 return new Promise((resolve,reject)=>{const child=spawn(command,args,{env,stdio:['ignore',capture?'pipe':'inherit',capture?'pipe':'inherit']});let output='';if(capture){child.stdout?.on('data',c=>output+=c.toString());child.stderr?.on('data',c=>output+=c.toString());}child.on('error',reject);child.on('close',code=>code===0?resolve(output):reject(new Error(`${command} exited ${code}. ${capture?output.slice(-1200):''}`)));});
}
try {
 let url:string;
 if(process.env.TEST_DATABASE_ADMIN_URL) {
  // Explicitly configured administration capability; the generated identifier cannot target an existing application DB.
  if(!/^curriculum_test_[a-f0-9]{12}$/.test(database))throw Error('Generated test database identifier invalid.');
  admin=new pg.Client({connectionString:process.env.TEST_DATABASE_ADMIN_URL,connectionTimeoutMillis:5000});await admin.connect();
  await admin.query(`CREATE DATABASE "${database}"`);createdDatabase=true;
  const parsed=new URL(process.env.TEST_DATABASE_ADMIN_URL);parsed.pathname='/'+database;url=parsed.toString();
 }else {
  await run('docker',['info','--format','{{.ServerVersion}}'],process.env,true);
  const image=process.env.TEST_POSTGRES_IMAGE??'postgres:17';
  await run('docker',['run','-d','--rm','--name',container,'-p','127.0.0.1::5432','-e','POSTGRES_USER=curriculum_test','-e',`POSTGRES_DB=${database}`,'-e','POSTGRES_PASSWORD',image],{...process.env,POSTGRES_PASSWORD:password},true);createdContainer=true;
  const portOutput=await run('docker',['port',container,'5432/tcp'],process.env,true);
  const port=portOutput.match(/127\.0\.0\.1:(\d+)/)?.[1];if(!port)throw Error('Disposable PostgreSQL port not found.');
  url=`postgresql://curriculum_test:${password}@127.0.0.1:${port}/${database}`;
 }
 let ready=false;for(let attempt=0;attempt<40;attempt++){const client=new pg.Client({connectionString:url,connectionTimeoutMillis:500});try{await client.connect();await client.query('SELECT 1');ready=true;break;}catch{await new Promise(r=>setTimeout(r,250));}finally{await client.end().catch(()=>{});}}
 if(!ready)throw Error('Disposable PostgreSQL failed readiness.');
 const files=(await readdir('tests')).filter(n=>n.endsWith('.test.ts')).sort().map(n=>'tests/'+n);
 if(!files.length)throw Error('No test files found.');
 console.log(JSON.stringify({event:'test_database_ready',mode:createdDatabase?'explicit_admin_connection':'disposable_container',container:createdContainer?container:undefined,database,files:files.length,fixture_policy:'Isolated owned test database only; published data untouched.'}));
 await run(process.execPath,['--import','tsx','--test','--test-concurrency=1',...files],{...process.env,DATABASE_URL:url,DOMAIN_INTEGRATION_TEST:'1'});
}catch(error){console.error((error as Error).message);process.exitCode=1;}finally{
 if(createdDatabase&&admin){try{await admin.query(`DROP DATABASE "${database}" WITH (FORCE)`);}catch{console.error('Owned test database cleanup failed: '+database);process.exitCode=1;}}
 await admin?.end().catch(()=>{});
 if(createdContainer)await run('docker',['stop',container],process.env,true).catch(()=>{console.error('Disposable test container cleanup failed: '+container);process.exitCode=1;});
}
